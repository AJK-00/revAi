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

    code_contents = []

    def fetch_contents(url):
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("GitHub API Error:", response.text)
            return

        items = response.json()

        if not isinstance(items, list):
            print("Unexpected GitHub response:", items)
            return

        for item in items:
            if item["type"] == "file" and item["name"].endswith((
                ".py", ".js", ".ts", ".java",
                ".jsx", ".tsx", ".html", ".css"
            )):
                file_data = requests.get(item["download_url"]).text
                code_contents.append(file_data)

            elif item["type"] == "dir":
                fetch_contents(item["url"])

    fetch_contents(api_url)

    return "\n".join(code_contents[:5])