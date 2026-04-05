"""
repo_fetcher.py
---------------
Fetches GitHub repository content.
Supports:
  - Specific branch selection
  - Specific file/folder selection
  - Concurrent file fetching
  - Full file tree listing
"""

import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

CODE_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".cpp", ".c", ".go", ".rb",
    ".php", ".html", ".css", ".ipynb", ".rs",
    ".swift", ".kt", ".scala", ".r", ".m",
)
MAX_FILES       = 20
CHARS_PER_FILE  = 3000


# ─────────────────────────────────────────────
# Public: fetch full repo
# ─────────────────────────────────────────────

def fetch_repo_files(
    repo_url:    str,
    branch:      str = "HEAD",
    target_path: str = "",
) -> dict:
    """
    Fetch repository content.

    Args:
        repo_url:    Full GitHub URL e.g. https://github.com/owner/repo
        branch:      Branch name (default: HEAD = default branch)
        target_path: Optional subfolder/file path to limit scope

    Returns:
        {
          readme:        str,
          files:         list[str],
          code_snippets: list[str],
          branch:        str,
          target_path:   str,
        }
    """
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo  = parts[-1].replace(".git", "")

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(tree_url, headers=headers, timeout=15)

    if response.status_code != 200:
        print(f"[repo_fetcher] GitHub API error: {response.status_code} {response.text[:200]}")
        return {}

    tree      = response.json().get("tree", [])
    file_list = [item["path"] for item in tree if item["type"] == "blob"]

    # Filter to target path if specified
    if target_path:
        file_list = [p for p in file_list if p.startswith(target_path)]

    readme_paths = [p for p in file_list if "readme" in p.lower()]
    code_paths   = [
        p for p in file_list
        if p.endswith(CODE_EXTENSIONS)
    ][:MAX_FILES]

    base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"

    def fetch_raw(path):
        try:
            r = requests.get(f"{base_url}/{path}", headers=headers, timeout=10)
            return r.text if r.status_code == 200 else None
        except Exception:
            return None

    # Concurrent fetch
    all_paths = list(dict.fromkeys(readme_paths + code_paths))
    results   = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        future_map = {ex.submit(fetch_raw, p): p for p in all_paths}
        for future in as_completed(future_map):
            path = future_map[future]
            results[path] = future.result()

    readme_content = next(
        (results[p] for p in readme_paths if results.get(p)), ""
    )
    code_snippets = [
        results[p][:CHARS_PER_FILE]
        for p in code_paths
        if results.get(p)
    ]

    return {
        "readme":        readme_content,
        "files":         file_list[:100],
        "code_snippets": code_snippets,
        "branch":        branch,
        "target_path":   target_path,
    }


# ─────────────────────────────────────────────
# Public: list branches
# ─────────────────────────────────────────────

def list_branches(repo_url: str) -> list:
    """Returns list of branch names for the repo."""
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo  = parts[-1].replace(".git", "")

    url = f"https://api.github.com/repos/{owner}/{repo}/branches"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return [b["name"] for b in r.json()]
    except Exception as e:
        print(f"[repo_fetcher] list_branches error: {e}")
    return []


# ─────────────────────────────────────────────
# Public: list files/folders at a path
# ─────────────────────────────────────────────

def list_repo_tree(
    repo_url: str,
    branch:   str = "HEAD",
) -> dict:
    """
    Returns the full file tree organized by folder.
    Used by the frontend file selector.

    Returns:
        {
          folders: list[str],   — unique directory paths
          files:   list[str],   — all file paths
          branches: list[str],  — all branches
        }
    """
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo  = parts[-1].replace(".git", "")

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    try:
        r = requests.get(tree_url, headers=headers, timeout=15)
        if r.status_code != 200:
            return {"folders": [], "files": [], "branches": []}

        tree      = r.json().get("tree", [])
        all_files = [item["path"] for item in tree if item["type"] == "blob"]

        # Extract unique folders
        folders = sorted(set(
            "/".join(p.split("/")[:-1])
            for p in all_files
            if "/" in p
        ))

        branches = list_branches(repo_url)

        return {
            "folders":  folders,
            "files":    all_files,
            "branches": branches,
        }
    except Exception as e:
        print(f"[repo_fetcher] list_repo_tree error: {e}")
        return {"folders": [], "files": [], "branches": []}


# ─────────────────────────────────────────────
# Public: fetch a single file's content
# ─────────────────────────────────────────────

def fetch_single_file(repo_url: str, file_path: str, branch: str = "HEAD") -> str:
    """Fetch content of a specific file from the repo."""
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo  = parts[-1].replace(".git", "")

    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""