from repo_fetcher import fetch_repo_files
from analyzer import analyze_code

def main():
    repo_url = input("Enter GitHub repository URL: ").strip()

    print("\nFetching repository data...")
    repo_data = fetch_repo_files(repo_url)

    if not repo_data:
        print("Failed to fetch repository data.")
        return

    print("\nRepository loaded successfully.")
    print("You can now ask questions about this repository.")
    print("Type 'exit' to quit.\n")

    while True:
        user_prompt = input(">>> ").strip()

        if user_prompt.lower() == "exit":
            print("Exiting workspace.")
            break

        print("\nAnalyzing...\n")
        result = analyze_code(repo_data, user_prompt)

        print(result)
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()