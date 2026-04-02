from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from repo_fetcher import fetch_repo_files
from analyzer import analyze_code

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # tighten from "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_sessions = {}
MAX_SESSIONS = 50  # prevent unbounded memory growth

class ChatRequest(BaseModel):
    chat_id: str
    repo_url: str
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    print("Incoming request:", request)
    try:
        if request.chat_id not in chat_sessions:
            if len(chat_sessions) >= MAX_SESSIONS:
                oldest = next(iter(chat_sessions))
                del chat_sessions[oldest]

            print("Fetching repository...")
            repo_data = fetch_repo_files(request.repo_url)
            chat_sessions[request.chat_id] = {"repo_data": repo_data, "history": []}

        session = chat_sessions[request.chat_id]
        print("Running analysis...")
        response = analyze_code(session["repo_data"], request.message, session["history"])
        session["history"].append({"user": request.message, "assistant": response})
        return {"response": response}

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{chat_id}")
async def clear_session(chat_id: str):
    chat_sessions.pop(chat_id, None)
    return {"status": "cleared"}