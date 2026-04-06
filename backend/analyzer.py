"""
analyzer.py
-----------
Analyzes GitHub repository content using Gemini + TF-IDF RAG.
No sentence-transformers or FAISS — uses lightweight sklearn retrieval.
"""

import os
from dotenv import load_dotenv
from rag_engine     import retrieve_relevant_chunks, chunk_text
from memory_manager import build_memory_block

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


def analyze_code(repo_data: dict, question: str, history: list = None) -> str:
    """
    Analyze a GitHub repository and answer a question about it.

    Args:
        repo_data: Dict with keys: readme, files, code_snippets, branch, target_path
        question:  User's question
        history:   Conversation history list

    Returns:
        Answer string from Gemini
    """
    if not repo_data:
        return "No repository data loaded. Please paste a GitHub URL first."

    # Build a searchable text corpus from repo content
    corpus_parts = []

    # README first (highest priority)
    readme = repo_data.get("readme", "")
    if readme:
        corpus_parts.append(f"[README]\n{readme[:4000]}")

    # Code snippets
    snippets = repo_data.get("code_snippets", [])
    corpus_parts.extend(snippets)

    # File list as context
    files = repo_data.get("files", [])
    if files:
        corpus_parts.append("[File Structure]\n" + "\n".join(files[:80]))

    if not corpus_parts:
        return "The repository appears to be empty or inaccessible."

    # Chunk everything and retrieve relevant pieces
    all_chunks = []
    for part in corpus_parts:
        all_chunks.extend(chunk_text(part, chunk_size=800))

    relevant = retrieve_relevant_chunks(question, all_chunks, top_k=6)
    context  = "\n\n---\n\n".join(relevant)

    # Build memory block
    memory = build_memory_block(history or [])

    branch      = repo_data.get("branch", "HEAD")
    target_path = repo_data.get("target_path", "")
    scope_note  = f"Branch: {branch}" + (f" | Path: {target_path}" if target_path else "")

    prompt = f"""You are a senior software engineer performing a code review and analysis.

{memory['full_prompt']}

Repository Info: {scope_note}
Total files: {len(files)}

Relevant Repository Content:
{context}

Question: {question}

Provide a thorough, well-structured answer. Use markdown formatting.
If referencing specific files or code, mention them by name.
If you cannot find the answer in the provided content, say so clearly."""

    try:
        response = _llm.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[analyzer] Gemini error: {e}")
        return f"Analysis failed: {str(e)}"