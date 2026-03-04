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

def analyze_code(repo_data):
    if not repo_data:
        return {"error": "No repository data found."}

    # Combine README + code
    full_text = repo_data.get("readme", "") + "\n" + "\n".join(repo_data.get("code_snippets", []))

    if not full_text.strip():
        return {"error": "No content available for analysis."}

    # 🔥 RAG PIPELINE
    chunks = chunk_text(full_text)
    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)

    query = """
Identify:
- Core architecture design
- Primary technologies and frameworks
- Main modules and components
- Any external dependencies explicitly used
"""
    relevant_chunks = retrieve_relevant_chunks(query, chunks, index)

    context = "\n".join(relevant_chunks)

    # 🔥 Send only relevant context to LLM
    prompt = f"""
You are a senior software architect.

Based ONLY on the context below, analyze the repository.

Return STRICTLY valid JSON:

Only include technologies explicitly present in:
- README
- import statements
- dependency files
Do not infer common features of similar frameworks.

Do NOT include:
- Documentation tools
- CI/CD tools
- GitHub workflows
Unless they are core runtime dependencies.

Tech stack rules:
- Only include languages that dominate the repository.
- Ignore small documentation or config scripts.
- Do NOT infer technologies unless explicitly imported or present in source files.
Architecture type must describe:
- Design pattern (e.g., ASGI-based, Event-driven, Middleware-based, MVC)
Not just the runtime library name.

{{
  "project_summary": "...",
  "tech_stack": ["..."],
  "architecture_type": "...",
  "core_features": ["..."],
  "improvements": ["..."]
}}

Context:
{context}

Only return JSON.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=1000
    )

    raw_output = response.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", raw_output, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format", "raw_output": raw_output}

    return {"error": "No JSON found", "raw_output": raw_output}