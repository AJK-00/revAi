import requests, os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

CODE_EXTENSIONS = (".py",".js",".ts",".java",".cpp",".c",".go",".rb",".php",".html",".css")
MAX_FILES = 15       # was 5
CHARS_PER_FILE = 3000  # was 2000

def _fetch_raw(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.text if r.status_code == 200 else None
    except:
        return None

def fetch_repo_files(repo_url):
    parts = repo_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    response = requests.get(tree_url, headers=headers, timeout=10)
    if response.status_code != 200:
        print("GitHub API Error:", response.text)
        return {}

    tree = response.json().get("tree", [])
    file_list = [item["path"] for item in tree if item["type"] == "blob"]

    code_paths = [p for p in file_list if p.endswith(CODE_EXTENSIONS)][:MAX_FILES]
    readme_paths = [p for p in file_list if "readme" in p.lower()]

    base = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD"

    # Fetch everything concurrently
    urls = {path: f"{base}/{path}" for path in code_paths + readme_paths}
    results = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        future_to_path = {ex.submit(_fetch_raw, url): path for path, url in urls.items()}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            results[path] = future.result()

    readme_content = next((results[p] for p in readme_paths if results.get(p)), "")
    code_snippets = [results[p][:CHARS_PER_FILE] for p in code_paths if results.get(p)]

    return {
        "readme": readme_content,
        "files": file_list[:50],
        "code_snippets": code_snippets
    }