from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from repo_fetcher import fetch_repo_files
from analyzer import analyze_code

app = FastAPI()

# Allow React frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_sessions = {}

class ChatRequest(BaseModel):
    chat_id: str
    repo_url: str
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    print("Incoming request:", request)

    try:
        # Load repo only once per chat session
        if request.chat_id not in chat_sessions:
            print("Fetching repository...")
            repo_data = fetch_repo_files(request.repo_url)

            chat_sessions[request.chat_id] = {
                "repo_data": repo_data,
                "history": []
            }

        session = chat_sessions[request.chat_id]

        print("Running analysis...")

        response = analyze_code(
            session["repo_data"],
            request.message
        )

        session["history"].append({
            "user": request.message,
            "assistant": response
        })

        return {"response": response}

    except Exception as e:
        print("ERROR:", str(e))
        return {"response": f"Backend error: {str(e)}"}