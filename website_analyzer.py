from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def analyze_website(site_data):
    if "error" in site_data:
        return site_data

    prompt = f"""
You are a web technology analyst.

Based only on the metadata below, analyze the website.

Return STRICTLY valid JSON:
The HTML content is fully rendered after JavaScript execution.
Use visible structure and scripts to infer frontend framework.

{{
  "site_purpose": "...",
  "detected_technologies": ["..."],
  "frontend_framework": "...",
  "backend_inference": "...",
  "seo_quality": "...",
  "security_observations": ["..."],
  "improvements": ["..."]
}}

Website Metadata:

Title:
{site_data["title"]}

Meta Tags:
{site_data["meta_tags"]}

Scripts:
{site_data["scripts"]}

Stylesheets:
{site_data["stylesheets"]}

HTML Sample:
{site_data["html_sample"]}

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
        except:
            return {"error": "Invalid JSON", "raw_output": raw_output}

    return {"error": "No JSON found", "raw_output": raw_output}