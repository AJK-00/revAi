import os
from dotenv import load_dotenv
import json
import re

from rag_engine import chunk_text, embed_chunks, build_faiss_index, retrieve_relevant_chunks

load_dotenv()
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = genai.GenerativeModel("models/gemini-2.5-flash")  # or gemini-1.5-pro


def analyze_code(repo_data, user_prompt, history=None):
    if not repo_data:
        return "No repository data found."

    # Combine README + code snippets
    full_text = repo_data.get("readme", "") + "\n" + "\n".join(repo_data.get("code_snippets", []))

    if not full_text.strip():
        return "No content available for analysis."

    # 🔥 RAG PIPELINE
    chunks = chunk_text(full_text)
    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)

    # Retrieve relevant context based on USER query
    relevant_chunks = retrieve_relevant_chunks(
        user_prompt,
        chunks,
        index,
        top_k=5
    )

    context = "\n\n".join(relevant_chunks)
    history_text = ""
    if history:
        for turn in history[-4:]:  # last 4 turns
            history_text += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"

    # 🔥 Dynamic Prompt
    prompt = f"""
You are a senior software engineer analyzing a GitHub repository.

User Question:
{user_prompt}

Previous conversation:
{history_text}
User Question:
{user_prompt}


Repository Context:
{context}
Rules:
- Only use information present in the provided context.
- Do not assume external details.
- If the answer is not available in context, clearly say so.
- Provide technical and structured explanation.
-When describing file structure, only mention files that explicitly appear in the repository context.
-Do not infer additional folders or files.
-If exact structure is unclear, describe at a high level without fabricating paths.

Answer:
"""

    response = client.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=8192,
        )
    )
    return response.text.strip()