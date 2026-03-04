from repo_fetcher import fetch_repo_files
from analyzer import analyze_code

from website_fetcher import fetch_website_data
from website_analyzer import analyze_website

import json

def main():
    user_input = input("Enter GitHub repo URL or Website URL: ").strip()

    if "github.com" in user_input:
        print("\nFetching repository data...")
        repo_data = fetch_repo_files(user_input)

        print("Analyzing repository...\n")
        result = analyze_code(repo_data)

    else:
        print("\nFetching website data...")
        site_data = fetch_website_data(user_input)

        print("Analyzing website...\n")
        result = analyze_website(site_data)

    print("\n=== ANALYSIS RESULT ===\n")
    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()