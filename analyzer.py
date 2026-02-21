from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def analyze_code(code_text):
    if not code_text.strip():
        return "No code content to analyze."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # Stable Groq model
        messages=[
            {
                "role": "system",
                "content": "You are a senior software architect."
            },
            {
                "role": "user",
                "content": f"""
Analyze this project and explain:

1. What the application does
2. Tech stack used
3. Architecture type
4. Core features
5. Possible improvements

Keep the explanation clear and structured.

Code:
{code_text[:12000]}
"""
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content