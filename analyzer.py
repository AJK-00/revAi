from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re

from rag_engine import chunk_text, embed_chunks, build_faiss_index, retrieve_relevant_chunks

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def analyze_code(repo_data, user_prompt):
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

    # 🔥 Dynamic Prompt
    prompt = f"""
You are a senior software engineer analyzing a GitHub repository.

User Question:
{user_prompt}

Repository Context:
{context}
Rules:
- Only use information present in the provided context.
- Do not assume external details.
- If the answer is not available in context, clearly say so.
- Provide technical and structured explanation.

Answer:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You analyze repositories accurately and technically."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=1200
    )

    return response.choices[0].message.content.strip()