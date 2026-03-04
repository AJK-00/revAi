# revAi - AI-Powered GitHub Repository Analyzer

An intelligent analysis tool that leverages RAG (Retrieval-Augmented Generation) and LLMs to analyze GitHub repositories, providing comprehensive insights into architecture, tech stack, and improvement suggestions.

## 🚀 Features

- **GitHub Repository Analysis**: Automatically fetches and analyzes repository structure, code, and documentation
- **RAG-Powered Intelligence**: Uses semantic search with FAISS and sentence transformers for accurate context retrieval
- **LLM Integration**: Powered by Groq's Llama 3.1 for intelligent analysis and recommendations
- **Interactive Q&A**: Ask questions about the repository after loading

## 🛠️ Tech Stack

- **Python 3.13**
- **OpenAI SDK** (Groq API)
- **FAISS** - Vector similarity search
- **Sentence Transformers** - Text embeddings
- **NumPy** - Numerical operations

## 📋 Prerequisites

- Python 3.13+
- GitHub Personal Access Token (optional, for higher API rate limits)
- Groq API Key

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/AJK-00/revAi.git
cd revAi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_token_here
```

## 🎯 Usage

Run the main script:
```bash
python main.py
```

Enter a GitHub repository URL (e.g., `https://github.com/user/repo`)

The tool will load the repository and allow you to ask questions about it.

## 📊 Output

- Project summary
- Tech stack identification
- Architecture type
- Core features
- Improvement suggestions
- Custom queries about the codebase

## 🏗️ Architecture

- **repo_fetcher.py**: Fetches GitHub repository data via GitHub API
- **rag_engine.py**: Implements RAG pipeline with chunking, embedding, and retrieval
- **analyzer.py**: Analyzes code repositories using LLM
- **main.py**: Entry point and orchestration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

MIT License

## 👤 Author

Created with ❤️ by AJK-00
