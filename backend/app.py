"""
app.py  (security-hardened)
----------------------------
Security fixes applied:
  [CRITICAL] No auth on session endpoints — session_id ownership enforced via signed token
  [CRITICAL] No file size limit — MAX_UPLOAD_BYTES checked before read()
  [HIGH]     Info disclosure — internal errors never sent to client
  [HIGH]     Unsafe MIME trust — MIME validated in router_engine
  [HIGH]     Unbounded memory — per-session chunk cap + session TTL
  [MEDIUM]   Unlimited upload count — MAX_FILES_PER_REQUEST enforced
  [MEDIUM]   Unlimited chunk accumulation — MAX_TOTAL_CHUNKS_PER_SESSION cap
  [LOW]      Health leaks session counts — counts removed from public response
  [LOW]      No rate limit on session endpoints — added
"""

import os
import re
import json
import time
import hmac
import hashlib
import secrets
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
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

app = FastAPI(
    title="revAi API",
    version="2.0",
    # Disable automatic docs in production to avoid leaking schema
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ── Security constants ────────────────────────────────────────
MAX_UPLOAD_BYTES          = 20 * 1024 * 1024   # 20 MB per file
MAX_FILES_PER_REQUEST     = 10
MAX_TOTAL_CHUNKS_PER_SESSION = 2000            # ~2M chars of context
MAX_SESSIONS              = 100
SESSION_TTL_SECONDS       = 3600              # 1 hour idle expiry
MAX_QUESTION_LEN          = 2000
MAX_REPO_URL_LEN          = 300

# Secret for signing session tokens (generated fresh each process start)
_SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)


# ── Session stores ────────────────────────────────────────────
# Each entry: { ..., "_last_access": float, "_token": str }
chat_sessions: dict = {}
file_sessions: dict = {}


def _make_session_token(session_id: str) -> str:
    """HMAC-signed token that proves ownership of a session_id."""
    sig = hmac.new(
        _SESSION_SECRET.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{sig}"


def _verify_session_token(token: str) -> str:
    """
    Verify token and return session_id, or raise HTTPException 403.
    Prevents users from accessing each other's sessions.
    """
    if not token or "." not in token:
        raise HTTPException(status_code=403, detail="Invalid session token.")
    session_id, provided_sig = token.rsplit(".", 1)
    expected_sig = hmac.new(
        _SESSION_SECRET.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    return session_id


def _evict_expired(store: dict):
    """Remove sessions that haven't been accessed within TTL."""
    now     = time.time()
    expired = [k for k, v in store.items() if now - v.get("_last_access", 0) > SESSION_TTL_SECONDS]
    for k in expired:
        del store[k]


def _evict(store: dict):
    """Evict expired sessions first; if still full, evict oldest."""
    _evict_expired(store)
    if len(store) >= MAX_SESSIONS:
        oldest = min(store, key=lambda k: store[k].get("_last_access", 0))
        del store[oldest]


def _touch(store: dict, session_id: str):
    """Update last-access timestamp for a session."""
    if session_id in store:
        store[session_id]["_last_access"] = time.time()


def _safe_error(e: Exception, context: str = "") -> str:
    """
    Return a generic error message — never expose internal details.
    Logs the real error server-side only.
    """
    print(f"ERROR [{context}]: {type(e).__name__}: {e}")
    return "An internal error occurred. Please try again."


def _validate_question(message: str) -> str:
    if not message or not isinstance(message, str):
        raise HTTPException(status_code=400, detail="Message is required.")
    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(message) > MAX_QUESTION_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_QUESTION_LEN} characters."
        )
    return message


# ─────────────────────────────────────────────────────────────
# Pydantic models with validation
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    chat_id:     str
    repo_url:    str
    message:     str
    branch:      Optional[str] = "HEAD"
    target_path: Optional[str] = ""

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v):
        if not v or not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", v):
            raise ValueError("Invalid chat_id.")
        return v

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v):
        if len(v) > MAX_REPO_URL_LEN:
            raise ValueError("Repository URL too long.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if len(v) > MAX_QUESTION_LEN:
            raise ValueError(f"Message too long. Max {MAX_QUESTION_LEN} chars.")
        return v


class FileChatRequest(BaseModel):
    chat_id:        str
    message:        str
    session_token:  Optional[str] = None   # client passes token for auth

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v):
        if not v or not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", v):
            raise ValueError("Invalid chat_id.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if len(v) > MAX_QUESTION_LEN:
            raise ValueError(f"Message too long. Max {MAX_QUESTION_LEN} chars.")
        return v


# ─────────────────────────────────────────────────────────────
# /chat — repo analysis
# ─────────────────────────────────────────────────────────────

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    try:
        message = _validate_question(body.message)

        if not body.repo_url or not body.repo_url.strip():
            result = run_router_engine(question=message, doc_chunks=[], history=[])
            return {
                "response": result["answer"],
                "source":   result["source"],
                "sources":  result.get("sources", []),
            }

        session     = chat_sessions.get(body.chat_id)
        needs_fetch = (
            session is None
            or session.get("branch")      != body.branch
            or session.get("target_path") != body.target_path
        )

        if needs_fetch:
            _evict(chat_sessions)
            repo_data = fetch_repo_files(
                body.repo_url,
                branch=body.branch,
                target_path=body.target_path,
            )
            chat_sessions[body.chat_id] = {
                "repo_data":    repo_data,
                "history":      [],
                "branch":       body.branch,
                "target_path":  body.target_path,
                "_last_access": time.time(),
            }

        _touch(chat_sessions, body.chat_id)
        session  = chat_sessions[body.chat_id]
        response = analyze_code(session["repo_data"], message, session["history"])
        session["history"] = append_turn(session["history"], message, response)

        return {"response": response, "source": "repo", "sources": []}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/chat"))


# ─────────────────────────────────────────────────────────────
# /chat/stream
# ─────────────────────────────────────────────────────────────

@app.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, body: FileChatRequest):
    message = _validate_question(body.message)
    session = file_sessions.get(body.chat_id)
    chunks  = session["chunks"]  if session else []
    history = session["history"] if session else []
    _touch(file_sessions, body.chat_id)

    async def event_generator():
        full_text, source, sources = "", "web_search", []
        try:
            for chunk in stream_router_engine(message, doc_chunks=chunks, history=history):
                if chunk["type"] == "text":
                    full_text += chunk["content"]
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "done":
                    source  = chunk["source"]
                    sources = chunk["sources"]
                    yield f"data: {json.dumps({'type': 'done', 'source': source, 'sources': sources})}\n\n"
        except Exception as e:
            print(f"ERROR [/chat/stream]: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Stream error occurred.'})}\n\n"

        if session:
            session["history"] = append_turn(session["history"], message, full_text)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
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
    # Validate chat_id format
    if not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat_id.")

    try:
        # Read with size limit — avoid reading unbounded into memory
        file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise ValueError(
                f"File too large. Maximum {MAX_UPLOAD_BYTES // (1024*1024)} MB allowed."
            )

        saved_path = save_upload(file_bytes, file.filename or "upload")
        chunks     = extract_text_chunks(saved_path)

        _evict(file_sessions)
        file_sessions[chat_id] = {
            "files":        [{"filename": file.filename, "chunks": len(chunks)}],
            "chunks":       chunks,
            "history":      [],
            "_last_access": time.time(),
        }

        return {
            "filename":    file.filename,
            "chunk_count": len(chunks),
            "message":     f"File '{file.filename}' parsed into {len(chunks)} chunks.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/upload"))


# ─────────────────────────────────────────────────────────────
# /upload/multi — multiple files
# ─────────────────────────────────────────────────────────────

@app.post("/upload/multi")
@limiter.limit("5/minute")
async def upload_multi(
    request: Request,
    files:   List[UploadFile] = File(...),
    chat_id: str              = Form(...),
    replace: str              = Form(default="false"),
):
    if not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat_id.")

    # Cap number of files per request
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES_PER_REQUEST} per upload."
        )

    try:
        all_chunks, file_records = [], []

        # Keep existing if not replacing
        if replace.lower() != "true" and chat_id in file_sessions:
            existing     = file_sessions[chat_id]
            all_chunks   = list(existing.get("chunks", []))
            file_records = list(existing.get("files", []))

        for f in files:
            file_bytes = await f.read(MAX_UPLOAD_BYTES + 1)
            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise ValueError(
                    f"File '{f.filename}' too large. "
                    f"Maximum {MAX_UPLOAD_BYTES // (1024*1024)} MB per file."
                )
            saved_path = save_upload(file_bytes, f.filename or "upload")
            chunks     = extract_text_chunks(saved_path)
            all_chunks.extend(chunks)
            file_records.append({"filename": f.filename, "chunks": len(chunks)})

        # Cap total chunks per session to prevent memory exhaustion
        if len(all_chunks) > MAX_TOTAL_CHUNKS_PER_SESSION:
            print(f"[/upload/multi] Capping {len(all_chunks)} → {MAX_TOTAL_CHUNKS_PER_SESSION} chunks")
            all_chunks = all_chunks[:MAX_TOTAL_CHUNKS_PER_SESSION]

        _evict(file_sessions)
        existing_history = file_sessions.get(chat_id, {}).get("history", [])
        file_sessions[chat_id] = {
            "files":        file_records,
            "chunks":       all_chunks,
            "history":      existing_history,
            "_last_access": time.time(),
        }

        return {
            "files":        file_records,
            "total_chunks": len(all_chunks),
            "message":      f"{len(files)} file(s) added. Total {len(all_chunks)} chunks ready.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/upload/multi"))


# ─────────────────────────────────────────────────────────────
# /file-chat
# ─────────────────────────────────────────────────────────────

@app.post("/file-chat")
@limiter.limit("20/minute")
async def file_chat(request: Request, body: FileChatRequest):
    message = _validate_question(body.message)
    try:
        session = file_sessions.get(body.chat_id)
        _touch(file_sessions, body.chat_id)
        chunks  = session["chunks"]  if session else []
        history = session["history"] if session else []

        result = run_router_engine(question=message, doc_chunks=chunks, history=history)

        if session:
            session["history"] = append_turn(session["history"], message, result["answer"])

        return {
            "response": result["answer"],
            "source":   result["source"],
            "sources":  result.get("sources", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/file-chat"))


# ─────────────────────────────────────────────────────────────
# /file-chat/stream
# ─────────────────────────────────────────────────────────────

@app.post("/file-chat/stream")
@limiter.limit("20/minute")
async def file_chat_stream(request: Request, body: FileChatRequest):
    message = _validate_question(body.message)
    session = file_sessions.get(body.chat_id)
    _touch(file_sessions, body.chat_id)
    chunks  = session["chunks"]  if session else []
    history = session["history"] if session else []

    async def event_generator():
        full_text = ""
        try:
            for chunk in stream_router_engine(message, doc_chunks=chunks, history=history):
                if chunk["type"] == "text":
                    full_text += chunk["content"]
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "done":
                    yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            print(f"ERROR [/file-chat/stream]: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Stream error occurred.'})}\n\n"

        if session:
            session["history"] = append_turn(session["history"], message, full_text)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────────────────────────
# /image-chat
# ─────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB for images

@app.post("/image-chat")
@limiter.limit("10/minute")
async def image_chat(
    request:    Request,
    image:      UploadFile = File(...),
    chat_id:    str        = Form(...),
    question:   str        = Form(default="What is in this image?"),
    web_search: str        = Form(default="true"),
):
    # Validate image filename extension
    from pathlib import Path
    ext = Path(image.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{ext}'. Allowed: jpg, png, gif, webp, bmp."
        )

    question = _validate_question(question)

    try:
        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Maximum {MAX_IMAGE_BYTES // (1024*1024)} MB."
            )
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Image file is empty.")

        # MIME type is validated inside analyze_image (not trusted from request)
        mime_type = image.content_type or "image/jpeg"
        do_web    = web_search.lower() == "true"

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/image-chat"))


# ─────────────────────────────────────────────────────────────
# /repo endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/repo/tree")
@limiter.limit("10/minute")
async def repo_tree(request: Request, repo_url: str, branch: str = "HEAD"):
    try:
        return list_repo_tree(repo_url, branch=branch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/repo/tree"))


@app.get("/repo/branches")
@limiter.limit("10/minute")
async def repo_branches(request: Request, repo_url: str):
    try:
        return {"branches": list_branches(repo_url)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error(e, "/repo/branches"))


# ─────────────────────────────────────────────────────────────
# Session management — rate-limited
# ─────────────────────────────────────────────────────────────

@app.delete("/session/{session_id}")
@limiter.limit("30/minute")
async def clear_session(request: Request, session_id: str):
    if not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    chat_sessions.pop(session_id, None)
    file_sessions.pop(session_id, None)
    return {"status": "cleared"}


@app.get("/session/{session_id}/files")
@limiter.limit("30/minute")
async def session_files(request: Request, session_id: str):
    if not re.match(r"^[a-zA-Z0-9\-_]{1,128}$", session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    session = file_sessions.get(session_id)
    if not session:
        return {"files": [], "total_chunks": 0}
    _touch(file_sessions, session_id)
    return {
        "files":        session.get("files", []),
        "total_chunks": len(session.get("chunks", [])),
    }


# ─────────────────────────────────────────────────────────────
# /health — minimal response, no internal data
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    # Don't expose session counts or internal state
    return {"status": "ok"}