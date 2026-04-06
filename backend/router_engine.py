"""
router_engine.py
----------------
Agentic RAG orchestrator.
Uses TF-IDF (sklearn) instead of sentence-transformers to keep image size small.
No FAISS needed — cosine similarity is fast enough for typical doc sizes.
"""

import os
import base64
from dotenv import load_dotenv

from web_search_tool import web_search
from memory_manager  import build_memory_block
from rag_engine      import retrieve_relevant_chunks

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
    return any(sig in question.lower() for sig in _WEB_SIGNALS)


# ── Local RAG ─────────────────────────────────────────────────

def _local_rag(question: str, chunks: list, history: list = None) -> tuple:
    relevant = retrieve_relevant_chunks(question, chunks, top_k=5)
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
        relevant   = retrieve_relevant_chunks(question, chunks, top_k=3)
        doc_section = "\nDocument Context:\n" + "\n\n".join(relevant)

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

    return _llm.generate_content(prompt).text.strip(), sources


# ── Streaming ─────────────────────────────────────────────────

def stream_router_engine(
    question:   str,
    doc_chunks: list = None,
    history:    list = None,
):
    chunks  = doc_chunks or []
    use_web = _needs_web(question, chunks)
    memory  = build_memory_block(history or [])

    if use_web:
        web_context, sources = web_search(question, max_results=5)
        doc_section = ""
        if chunks:
            relevant    = retrieve_relevant_chunks(question, chunks, top_k=3)
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
        relevant = retrieve_relevant_chunks(question, chunks, top_k=5)
        context  = "\n\n".join(relevant)
        sources  = []
        source   = "local_rag"

        prompt = f"""You are an expert document analyst.

{memory['full_prompt']}

Document Context:
{context}

Question: {question}

Answer:"""

    response  = _llm.generate_content(prompt, stream=True)
    full_text = ""
    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            yield {"type": "text", "content": chunk.text}

    yield {"type": "done", "source": source, "sources": sources, "full": full_text}


# ── Non-streaming ─────────────────────────────────────────────

def run_router_engine(
    question:   str,
    doc_chunks: list = None,
    history:    list = None,
) -> dict:
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
    print(f"[vision] mime={mime_type} q='{question[:60]}'")

    image_part = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
    }

    vision_prompt = f"""Analyze this image thoroughly.
User question: {question}
1. Describe what you see.
2. Identify specific items, products, brands, objects.
3. Answer the user's question directly.
4. List items that could be searched (shopping, info, etc.)"""

    vision_text = _vision_llm.generate_content([vision_prompt, image_part]).text.strip()

    sources = []
    if do_web_search:
        q = question if len(question) > 5 else vision_text[:200]
        web_context, sources = web_search(q, max_results=4)
        final_prompt = f"""You analyzed an image and searched the web.

Image Analysis:
{vision_text}

Web Results:
{web_context}

User Question: {question}

Provide a comprehensive answer combining both."""
        final_answer = _llm.generate_content(final_prompt).text.strip()
    else:
        final_answer = vision_text

    return {
        "answer":  final_answer,
        "source":  "vision_web" if do_web_search else "vision",
        "sources": sources,
    }