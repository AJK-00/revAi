# revAi - AI-Powered Code & Website Analyzer

An intelligent analysis tool that leverages RAG (Retrieval-Augmented Generation) and LLMs to analyze GitHub repositories and websites, providing comprehensive insights into architecture, tech stack, and improvement suggestions.

## 🚀 Features

- **GitHub Repository Analysis**: Automatically fetches and analyzes repository structure, code, and documentation
- **Website Technology Detection**: Analyzes websites to detect frontend/backend technologies, frameworks, and security practices
- **RAG-Powered Intelligence**: Uses semantic search with FAISS and sentence transformers for accurate context retrieval
- **LLM Integration**: Powered by Groq's Llama 3.1 for intelligent analysis and recommendations
- **Dual Analysis Mode**: Supports both GitHub repos and live websites

## 🛠️ Tech Stack

- **Python 3.13**
- **OpenAI SDK** (Groq API)
- **FAISS** - Vector similarity search
- **Sentence Transformers** - Text embeddings
- **Playwright** - Web scraping with JavaScript rendering
- **BeautifulSoup4** - HTML parsing
- **NumPy** - Numerical operations

## 📋 Prerequisites

- Python 3.13+
- GitHub Personal Access Token (optional, for higher API rate limits)
- Groq API Key

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/revAi.git
cd revAi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
python -m playwright install
```

4. Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_token_here
```

## 🎯 Usage

Run the main script:
```bash
python main.py
```

Enter either:
- A GitHub repository URL (e.g., `https://github.com/user/repo`)
- A website URL (e.g., `https://example.com`)

The tool will automatically detect the input type and perform the appropriate analysis.

## 📊 Output

### For GitHub Repositories:
- Project summary
- Tech stack identification
- Architecture type
- Core features
- Improvement suggestions

### For Websites:
- Site purpose
- Detected technologies
- Frontend framework
- Backend inference
- SEO quality assessment
- Security observations
- Improvement recommendations

## 🏗️ Architecture

- **repo_fetcher.py**: Fetches GitHub repository data via GitHub API
- **website_fetcher.py**: Scrapes website data using Playwright
- **rag_engine.py**: Implements RAG pipeline with chunking, embedding, and retrieval
- **analyzer.py**: Analyzes code repositories using LLM
- **website_analyzer.py**: Analyzes websites using LLM
- **main.py**: Entry point and orchestration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

MIT License

## 👤 Author

Created with ❤️ by [Your Name]
