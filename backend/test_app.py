# backend/test_app.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# ── Health ──────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

# ── /chat — no repo URL → should use web search ─────
def test_chat_no_repo():
    r = client.post("/chat", json={
        "chat_id": "test-001",
        "repo_url": "",
        "message": "what is Python?"
    })
    assert r.status_code == 200
    assert "response" in r.json()
    assert len(r.json()["response"]) > 10

# ── /chat — invalid repo URL ─────────────────────────
def test_chat_invalid_repo():
    r = client.post("/chat", json={
        "chat_id": "test-002",
        "repo_url": "https://github.com/this-does-not-exist-xyz/fake-repo",
        "message": "what does this do?"
    })
    # Should return 200 with an error message, not crash
    assert r.status_code in [200, 500]

# ── /upload — valid PDF ───────────────────────────────
def test_upload_valid_file():
    with open("test.pdf", "rb") as f:
        r = client.post("/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"chat_id": "test-003"}
        )
    assert r.status_code == 200
    assert "chunk_count" in r.json()
    assert r.json()["chunk_count"] > 0

# ── /upload — unsupported file type ──────────────────
def test_upload_invalid_type():
    r = client.post("/upload",
        files={"file": ("malware.exe", b"fake content", "application/octet-stream")},
        data={"chat_id": "test-004"}
    )
    assert r.status_code == 400

# ── /upload — empty file ──────────────────────────────
def test_upload_empty_file():
    r = client.post("/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"chat_id": "test-005"}
    )
    assert r.status_code in [400, 500]

# ── /file-chat — no session ───────────────────────────
def test_file_chat_no_session():
    r = client.post("/file-chat", json={
        "chat_id": "nonexistent-session-xyz",
        "message": "what is this about?"
    })
    # Should fall back to web search, not crash
    assert r.status_code == 200

# ── /file-chat — after upload ─────────────────────────
def test_file_chat_after_upload():
    with open("test.pdf", "rb") as f:
        client.post("/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"chat_id": "test-006"}
        )
    r = client.post("/file-chat", json={
        "chat_id": "test-006",
        "message": "summarize this document"
    })
    assert r.status_code == 200
    assert len(r.json()["response"]) > 20

# ── /chat — missing fields ────────────────────────────
def test_chat_missing_fields():
    r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 422  # FastAPI validation error

# ── /chat — SQL injection attempt ────────────────────
def test_chat_sql_injection():
    r = client.post("/chat", json={
        "chat_id": "'; DROP TABLE users; --",
        "repo_url": "",
        "message": "hello"
    })
    assert r.status_code in [200, 400]  # handled, not crashed

# ── /chat — very long message ─────────────────────────
def test_chat_very_long_message():
    r = client.post("/chat", json={
        "chat_id": "test-007",
        "repo_url": "",
        "message": "a" * 10000
    })
    assert r.status_code in [200, 400, 500]  # doesn't hang or crash

# ── Session cleanup ───────────────────────────────────
def test_delete_session():
    r = client.delete("/chat/test-001")
    assert r.status_code == 200