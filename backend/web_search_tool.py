"""
web_search_tool.py
Returns (context_string, sources_list) tuple.
sources_list = [{ title, url, domain, favicon }]
"""
import os
from dotenv import load_dotenv
load_dotenv()


def web_search(query: str, max_results: int = 5) -> tuple:
    from tavily import TavilyClient
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Web search unavailable: TAVILY_API_KEY not set.", []

    client = TavilyClient(api_key=api_key)
    print(f"[web_search] Query: '{query}'")

    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
    except Exception as e:
        return f"Web search failed: {str(e)}", []

    parts, sources = [], []

    if response.get("answer"):
        parts.append(f"Web Summary: {response['answer']}")

    for i, r in enumerate(response.get("results", []), 1):
        title   = r.get("title", "Source")
        url     = r.get("url", "")
        content = r.get("content", "")[:400]
        try:
            domain = url.split("/")[2]
        except Exception:
            domain = url

        parts.append(f"[Web Source {i}] {title}\nURL: {url}\nExcerpt: {content}")
        sources.append({
            "title":   title,
            "url":     url,
            "domain":  domain,
            "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=16",
        })

    context = "\n\n---\n\n".join(parts) if parts else "No web results found."
    print(f"[web_search] {len(sources)} results returned.")
    return context, sources