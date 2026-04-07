"""
app.py
------
FastAPI backend for revAi.

Endpoints:
  POST   /chat              → repo-based chat (+ web fallback)
  POST   /chat/stream       → streaming version of /chat
  POST   /upload            → upload ONE file into a session
  POST   /upload/multi      → upload MULTIPLE files into a session
  POST   /file-chat         → chat with uploaded file(s)
  POST   /file-chat/stream  → streaming version
  POST   /image-chat        → Gemini Vision + web
  GET    /repo/tree         → list branches + file tree
  GET    /repo/branches     → list branches only
  DELETE /session/{id}      → clear any session
  GET    /health
"""

import os
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from repo_fetcher   import fetch_repo_files, list_repo_tree, list_branches
from analyzer       import analyze_code
from file_processor import save_upload, extract_text_chunks
from router_engine  import run_router_engine, stream_router_engine, analyze_image
from memory_manager import append_turn

# ── Rate limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="revAi API", version="2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────
_raw = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = ["*"] if _raw.strip() == "*" else [o.strip() for o in _raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Session stores ───────────────────────────────────────────
chat_sessions: dict = {}
file_sessions: dict = {}
MAX_SESSIONS = 50


def _evict(store: dict):
    if len(store) >= MAX_SESSIONS:
        del store[next(iter(store))]


# ─────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    chat_id:     str
    repo_url:    str
    message:     str
    branch:      Optional[str] = "HEAD"
    target_path: Optional[str] = ""

class FileChatRequest(BaseModel):
    chat_id: str
    message: str


# ─────────────────────────────────────────────────────────────
# /chat — repo analysis
# ─────────────────────────────────────────────────────────────

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    print(f"[/chat] '{body.message[:60]}'")
    try:
        if not body.repo_url or not body.repo_url.strip():
            result = run_router_engine(question=body.message, doc_chunks=[], history=[])
            return {
                "response": result["answer"],
                "source":   result["source"],
                "sources":  result.get("sources", []),
            }

        # Load repo once per session (or reload if branch/path changed)
        session     = chat_sessions.get(body.chat_id)
        needs_fetch = (
            session is None
            or session.get("branch")      != body.branch
            or session.get("target_path") != body.target_path
        )

        if needs_fetch:
            _evict(chat_sessions)
            print(f"[/chat] Fetching repo branch={body.branch} path='{body.target_path}'")
            repo_data = fetch_repo_files(
                body.repo_url,
                branch=body.branch,
                target_path=body.target_path,
            )
            chat_sessions[body.chat_id] = {
                "repo_data":   repo_data,
                "history":     [],
                "branch":      body.branch,
                "target_path": body.target_path,
            }

        session  = chat_sessions[body.chat_id]
        response = analyze_code(session["repo_data"], body.message, session["history"])

        # Persist with memory manager
        session["history"] = append_turn(session["history"], body.message, response)

        return {"response": response, "source": "repo", "sources": []}

    except Exception as e:
        print(f"ERROR [/chat]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# /chat/stream — streaming repo/web chat
# ─────────────────────────────────────────────────────────────

@app.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, body: FileChatRequest):
    """
    Server-Sent Events streaming endpoint.
    Streams tokens as they arrive from Gemini.
    """
    session = file_sessions.get(body.chat_id)
    chunks  = session["chunks"]  if session else []
    history = session["history"] if session else []

    async def event_generator():
        full_text = ""
        source    = "web_search"
        sources   = []

        for chunk in stream_router_engine(body.message, doc_chunks=chunks, history=history):
            if chunk["type"] == "text":
                full_text += chunk["content"]
                # SSE format
                yield f"data: {json.dumps({'type': 'text', 'content': chunk['content']})}\n\n"
            elif chunk["type"] == "done":
                source  = chunk["source"]
                sources = chunk["sources"]
                yield f"data: {json.dumps({'type': 'done', 'source': source, 'sources': sources})}\n\n"

        # Persist after streaming completes
        if session:
            session["history"] = append_turn(session["history"], body.message, full_text)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ─────────────────────────────────────────────────────────────
# /upload — single file
# ─────────────────────────────────────────────────────────────

@app.post("/upload")
@limiter.limit("5/minute")
async def upload_file(
    request: Request,
    file:    UploadFile = File(...),
    chat_id: str        = Form(...),
):
    print(f"[/upload] '{file.filename}' chat_id='{chat_id}'")
    try:
        file_bytes = await file.read()
        saved_path = save_upload(file_bytes, file.filename)
        chunks     = extract_text_chunks(saved_path)

        _evict(file_sessions)

        # Initialize or replace session
        file_sessions[chat_id] = {
            "files":   [{"filename": file.filename, "chunks": len(chunks)}],
            "chunks":  chunks,
            "history": [],
        }

        return {
            "filename":    file.filename,
            "chunk_count": len(chunks),
            "message":     f"File '{file.filename}' parsed into {len(chunks)} chunks.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"ERROR [/upload]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# /upload/multi — multiple files (merged into one chunk pool)
# ─────────────────────────────────────────────────────────────

@app.post("/upload/multi")
@limiter.limit("5/minute")
async def upload_multi(
    request: Request,
    files:   List[UploadFile] = File(...),
    chat_id: str              = Form(...),
    replace: str              = Form(default="false"),
):
    """
    Upload multiple files at once.
    If replace=false, ADDS to existing session files.
    If replace=true, REPLACES the session.
    """
    print(f"[/upload/multi] {len(files)} files chat_id='{chat_id}' replace={replace}")
    try:
        all_chunks   = []
        file_records = []

        # Keep existing if not replacing
        if replace.lower() != "true" and chat_id in file_sessions:
            existing = file_sessions[chat_id]
            all_chunks   = existing.get("chunks", [])
            file_records = existing.get("files", [])

        for f in files:
            file_bytes = await f.read()
            saved_path = save_upload(file_bytes, f.filename)
            chunks     = extract_text_chunks(saved_path)
            all_chunks.extend(chunks)
            file_records.append({"filename": f.filename, "chunks": len(chunks)})
            print(f"[/upload/multi] '{f.filename}' → {len(chunks)} chunks")

        _evict(file_sessions)

        existing_history = file_sessions.get(chat_id, {}).get("history", [])
        file_sessions[chat_id] = {
            "files":   file_records,
            "chunks":  all_chunks,
            "history": existing_history,
        }

        return {
            "files":        file_records,
            "total_chunks": len(all_chunks),
            "message":      f"{len(files)} file(s) added. Total {len(all_chunks)} chunks ready.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"ERROR [/upload/multi]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# /file-chat — chat with uploaded files
# ─────────────────────────────────────────────────────────────

@app.post("/file-chat")
@limiter.limit("20/minute")
async def file_chat(request: Request, body: FileChatRequest):
    print(f"[/file-chat] '{body.message[:60]}'")
    try:
        session = file_sessions.get(body.chat_id)
        chunks  = session["chunks"]  if session else []
        history = session["history"] if session else []

        result = run_router_engine(
            question=body.message,
            doc_chunks=chunks,
            history=history,
        )

        if session:
            session["history"] = append_turn(
                session["history"], body.message, result["answer"]
            )

        return {
            "response": result["answer"],
            "source":   result["source"],
            "sources":  result.get("sources", []),
        }

    except Exception as e:
        print(f"ERROR [/file-chat]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# /file-chat/stream — streaming file chat
# ─────────────────────────────────────────────────────────────

@app.post("/file-chat/stream")
@limiter.limit("20/minute")
async def file_chat_stream(request: Request, body: FileChatRequest):
    session = file_sessions.get(body.chat_id)
    chunks  = session["chunks"]  if session else []
    history = session["history"] if session else []

    async def event_generator():
        full_text = ""
        for chunk in stream_router_engine(body.message, doc_chunks=chunks, history=history):
            if chunk["type"] == "text":
                full_text += chunk["content"]
                yield f"data: {json.dumps({'type': 'text', 'content': chunk['content']})}\n\n"
            elif chunk["type"] == "done":
                yield f"data: {json.dumps(chunk)}\n\n"
        if session:
            session["history"] = append_turn(session["history"], body.message, full_text)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ─────────────────────────────────────────────────────────────
# /image-chat
# ─────────────────────────────────────────────────────────────

@app.post("/image-chat")
@limiter.limit("10/minute")
async def image_chat(
    request:    Request,
    image:      UploadFile = File(...),
    chat_id:    str        = Form(...),
    question:   str        = Form(default="What is in this image? Identify all items."),
    web_search: str        = Form(default="true"),
):
    print(f"[/image-chat] '{question[:60]}'")
    try:
        image_bytes = await image.read()
        mime_type   = image.content_type or "image/jpeg"
        do_web      = web_search.lower() == "true"

        result = analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            question=question,
            do_web_search=do_web,
        )

        return {
            "response": result["answer"],
            "source":   result["source"],
            "sources":  result.get("sources", []),
        }

    except Exception as e:
        print(f"ERROR [/image-chat]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# /repo/tree — branch + file tree for selector UI
# ─────────────────────────────────────────────────────────────

@app.get("/repo/tree")
@limiter.limit("10/minute")
async def repo_tree(request: Request, repo_url: str, branch: str = "HEAD"):
    """Returns folder tree + branches for the repo selector UI."""
    try:
        tree = list_repo_tree(repo_url, branch=branch)
        return tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repo/branches")
@limiter.limit("10/minute")
async def repo_branches(request: Request, repo_url: str):
    """Returns list of branch names."""
    try:
        branches = list_branches(repo_url)
        return {"branches": branches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────────────────────

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    chat_sessions.pop(session_id, None)
    file_sessions.pop(session_id, None)
    return {"status": "cleared"}

@app.get("/session/{session_id}/files")
async def session_files(session_id: str):
    """List files currently loaded in a file session."""
    session = file_sessions.get(session_id)
    if not session:
        return {"files": [], "total_chunks": 0}
    return {
        "files":        session.get("files", []),
        "total_chunks": len(session.get("chunks", [])),
    }


# ─────────────────────────────────────────────────────────────
# /health
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":        "ok",
        "chat_sessions": len(chat_sessions),
        "file_sessions": len(file_sessions),
    }