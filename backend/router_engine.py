"""
router_engine.py
----------------
Agentic RAG orchestrator with:
  - Conversation memory (via memory_manager)
  - Multi-file document support
  - Web search (Tavily)
  - Image vision (Gemini Vision)
  - Streaming generator support
"""

import os
import base64
import numpy as np
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from web_search_tool import web_search
from memory_manager  import build_memory_block

load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_llm = genai.GenerativeModel(
    "models/gemini-2.5-flash",
    generation_config=genai.types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=8192,
    )
)

_vision_llm = genai.GenerativeModel("models/gemini-2.5-flash")
_embedder   = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

_WEB_SIGNALS = [
    "latest", "current", "recent", "today", "news", "update",
    "what is", "who is", "define", "explain", "how does", "why does",
    "compare", "difference", "example", "real world", "industry",
    "research", "paper", "price", "buy", "cost", "best", "review",
    "where", "when", "which", "recommend",
]


# ── Router ────────────────────────────────────────────────────

def _needs_web(question: str, chunks: list) -> bool:
    if not chunks:
        return True
    q = question.lower()
    return any(sig in q for sig in _WEB_SIGNALS)


# ── FAISS helpers ─────────────────────────────────────────────

def _build_index(chunks: list):
    embs = _embedder.encode(chunks).astype("float32")
    idx  = faiss.IndexFlatL2(embs.shape[1])
    idx.add(embs)
    return idx

def _retrieve(question: str, chunks: list, idx, top_k: int = 5) -> list:
    q = _embedder.encode([question]).astype("float32")
    _, indices = idx.search(q, min(top_k, len(chunks)))
    return [chunks[i] for i in indices[0] if i < len(chunks)]


# ── Local RAG ─────────────────────────────────────────────────

def _local_rag(question: str, chunks: list, history: list = None) -> tuple:
    idx      = _build_index(chunks)
    relevant = _retrieve(question, chunks, idx)
    context  = "\n\n".join(relevant)

    memory   = build_memory_block(history or [])

    prompt = f"""You are an expert document analyst.

{memory['full_prompt']}

Answer the question using ONLY the document context below.
If the answer is not in the context, say so clearly.

Document Context:
{context}

Question: {question}

Answer (structured and thorough):"""

    return _llm.generate_content(prompt).text.strip(), []


# ── Web answer ────────────────────────────────────────────────

def _web_answer(question: str, chunks: list = None, history: list = None) -> tuple:
    web_context, sources = web_search(question, max_results=5)
    memory = build_memory_block(history or [])

    doc_section = ""
    if chunks:
        idx      = _build_index(chunks)
        relevant = _retrieve(question, chunks, idx, top_k=3)
        doc_section = f"\nDocument Context:\n" + "\n\n".join(relevant)

    prompt = f"""You are an expert research assistant.

{memory['full_prompt']}

Web Search Results:
{web_context}
{doc_section}

Question: {question}

Instructions:
- Use web results for current/general knowledge.
- Use document context as supporting evidence where relevant.
- Be clear, structured, and thorough.

Answer:"""

    answer = _llm.generate_content(prompt).text.strip()
    return answer, sources


# ── Streaming generator ───────────────────────────────────────

def stream_router_engine(
    question:   str,
    doc_chunks: list = None,
    history:    list = None,
) -> "Generator":
    """
    Streaming version of run_router_engine.
    Yields text chunks as they arrive from Gemini.
    Also yields a final JSON metadata chunk.
    """
    chunks   = doc_chunks or []
    use_web  = _needs_web(question, chunks)
    memory   = build_memory_block(history or [])

    if use_web:
        web_context, sources = web_search(question, max_results=5)
        doc_section = ""
        if chunks:
            idx      = _build_index(chunks)
            relevant = _retrieve(question, chunks, idx, top_k=3)
            doc_section = "\nDocument Context:\n" + "\n\n".join(relevant)

        source = "hybrid" if chunks else "web_search"
        prompt = f"""You are an expert research assistant.

{memory['full_prompt']}

Web Search Results:
{web_context}
{doc_section}

Question: {question}

Answer:"""
    else:
        idx      = _build_index(chunks)
        relevant = _retrieve(question, chunks, idx)
        context  = "\n\n".join(relevant)
        sources  = []
        source   = "local_rag"

        prompt = f"""You are an expert document analyst.

{memory['full_prompt']}

Document Context:
{context}

Question: {question}

Answer:"""

    # Stream from Gemini
    response = _llm.generate_content(prompt, stream=True)
    full_text = ""
    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            yield {"type": "text", "content": chunk.text}

    # Final metadata chunk
    yield {
        "type":    "done",
        "source":  source,
        "sources": sources,
        "full":    full_text,
    }


# ── Main non-streaming API ────────────────────────────────────

def run_router_engine(
    question:   str,
    doc_chunks: list = None,
    history:    list = None,
) -> dict:
    """
    Main orchestrator (non-streaming).
    Supports multiple files — doc_chunks is the merged pool from all files.
    """
    chunks  = doc_chunks or []
    use_web = _needs_web(question, chunks)

    if use_web and chunks:
        print("[router] HYBRID")
        answer, sources = _web_answer(question, chunks=chunks, history=history)
        source = "hybrid"
    elif use_web:
        print("[router] WEB SEARCH")
        answer, sources = _web_answer(question, history=history)
        source = "web_search"
    else:
        print("[router] LOCAL RAG")
        answer, sources = _local_rag(question, chunks, history=history)
        source = "local_rag"

    return {"answer": answer, "source": source, "sources": sources}


# ── Image vision ──────────────────────────────────────────────

def analyze_image(
    image_bytes:   bytes,
    mime_type:     str,
    question:      str,
    do_web_search: bool = True,
) -> dict:
    print(f"[vision] mime={mime_type} question='{question[:60]}'")

    image_part = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
    }

    vision_prompt = f"""Analyze this image thoroughly.

User question: {question}

1. Describe what you see.
2. Identify specific items, products, brands, or objects.
3. Answer the user's question directly.
4. List items that could be searched for (shopping, info, etc.)"""

    vision_response = _vision_llm.generate_content([vision_prompt, image_part])
    vision_text     = vision_response.text.strip()

    sources = []
    if do_web_search:
        search_query         = question if len(question) > 5 else vision_text[:200]
        web_context, sources = web_search(search_query, max_results=4)

        final_prompt = f"""You analyzed an image and searched the web for more info.

Image Analysis:
{vision_text}

Web Search Results:
{web_context}

User Question: {question}

Provide a comprehensive answer combining both sources."""

        final_answer = _llm.generate_content(final_prompt).text.strip()
    else:
        final_answer = vision_text

    return {
        "answer":  final_answer,
        "source":  "vision_web" if do_web_search else "vision",
        "sources": sources,
    }