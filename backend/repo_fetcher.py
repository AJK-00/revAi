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

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"

    response = requests.get(tree_url, headers=headers, timeout=10)

    if response.status_code != 200:
        print("GitHub API Error:", response.text)
        return {}

    tree = response.json().get("tree", [])

    readme_content = ""
    code_contents = []
    file_list = []

    for item in tree:

        path = item["path"]

        if item["type"] != "blob":
            continue

        file_list.append(path)

        # README
        if "readme" in path.lower():

            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"

            try:
                readme_content = requests.get(raw_url, timeout=10).text
            except:
                pass

        # Code files
        if path.endswith((
            ".py",".js",".ts",".java",".cpp",".c",".go",
            ".rb",".php",".html",".css",".ipynb"
        )):

            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"

            try:
                code = requests.get(raw_url, timeout=10).text
                code_contents.append(code[:2000])
            except:
                continue

        if len(code_contents) >= 5:
            break

    return {
        "readme": readme_content,
        "files": file_list[:50],
        "code_snippets": code_contents
    }