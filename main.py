from repo_fetcher import fetch_repo_files
from analyzer import analyze_code

try:
    repo_url = input("Enter GitHub repo URL: ")

    code = fetch_repo_files(repo_url)

    if not code:
        print("No valid code files found.")
    else:
        result = analyze_code(code)
        print("\n=== ANALYSIS ===\n")
        print(result)

except Exception as e:
    print("Error occurred:", str(e))