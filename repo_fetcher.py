import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}"
} if GITHUB_TOKEN else {}

def fetch_repo_files(repo_url):
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"

    readme_content = ""
    file_list = []
    code_contents = []

    def fetch_contents(url):
        nonlocal readme_content

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("GitHub API Error:", response.text)
            return

        items = response.json()

        if not isinstance(items, list):
            return

        for item in items:
            if item["type"] == "file":
                file_list.append(item["name"])

                # Capture README separately
                if item["name"].lower().startswith("readme"):
                    readme_content = requests.get(
                        item["download_url"], headers=headers
                    ).text

                # Capture relevant code files
                if item["name"].endswith((
                    ".py", ".js", ".ts", ".java",
                    ".jsx", ".tsx", ".html", ".css",
                    ".cpp", ".c", ".go", ".rb", ".php"
                )):
                    try:
                        file_data = requests.get(
                            item["download_url"], headers=headers
                        ).text
                        code_contents.append(file_data[:2000])  # limit per file
                    except:
                        continue

            elif item["type"] == "dir":
                fetch_contents(item["url"])

    fetch_contents(api_url)

    return {
        "readme": readme_content,
        "files": file_list[:50],  # limit list size
        "code_snippets": code_contents[:5]  # limit number of files
    }