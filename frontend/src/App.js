import React, { useState, useEffect } from "react";
import axios from "axios";

import Sidebar         from "./components/sidebar";
import ChatWindow      from "./components/Chatwindow";
import InputBox        from "./components/InputBox";
import AuthModal       from "./components/AuthModal";
import SettingsModal   from "./components/SettingsModal";
import FileUploadModal from "./components/FileUploadModal";

import {
  onAuthChange, getProfile,
  getAllSessions, getSession, getMessages,
  createSession, updateSession, deleteSession, appendMessage,
} from "./components/supabaseDb";

import "./Styles/layout.css";
import "./Styles/chat.css";
import "./Styles/input.css";
import "./Styles/SideBar.css";
import "./components/AuthModal.css";
import "./components/UserProfile.css";
import "./components/SettingsModal.css";
import "./components/FileUploadModal.css";
import "./App.css";

const GITHUB_URL_RE = /https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/i;
const API = "https://revai.up.railway.app";

const SUGGESTIONS = [
  { icon: "⬡", text: "Analyze a GitHub repo"          },
  { icon: "📄", text: "Upload & summarize a document"  },
  { icon: "🌐", text: "Search the web"                },
  { icon: "🖼", text: "Analyze an image"              },
];

function repoName(url) {
  return url
    .replace(/https?:\/\/github\.com\//i, "")
    .replace(/\.git$/, "")
    .split("/").slice(0, 2).join("/");
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function loadAppearance() {
  try {
    const s = localStorage.getItem("revai_appearance");
    if (s) return JSON.parse(s);
  } catch (_) {}
  return { colorMode: "dark", fontId: "default" };
}

const FONT_MAP = {
  default:  "'DM Sans', system-ui, sans-serif",
  sans:     "'Inter', 'Helvetica Neue', sans-serif",
  mono:     "'JetBrains Mono', monospace",
  dyslexic: "'Comic Sans MS', cursive, sans-serif",
};

export default function App() {
  // ── Auth ──
  const [user, setUser]                 = useState(null);
  const [profile, setProfile]           = useState(null);
  const [showAuth, setShowAuth]         = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // ── Appearance ──
  const [appearance, setAppearance] = useState(loadAppearance);

  // ── Chat ──
  const [sessions, setSessions]         = useState([]);
  const [activeId, setActiveId]         = useState(null);
  const [messages, setMessages]         = useState([]);
  const [repoUrl, setRepoUrl]           = useState("");
  const [message, setMessage]           = useState("");
  const [loading, setLoading]           = useState(false);
  const [streaming, setStreaming]       = useState(false);
  const [sidebarOpen, setSidebarOpen]   = useState(true);

  // ── File / image ──
  const [showUpload, setShowUpload]       = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [fileMode, setFileMode]           = useState(false);
  const [sessionFiles, setSessionFiles]   = useState([]);

  // ── Apply appearance to DOM ──
  useEffect(() => {
    const root = document.documentElement;
    const mode = appearance.colorMode;
    if (mode === "auto") {
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", dark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", mode);
    }
    root.style.setProperty("--font-body", FONT_MAP[appearance.fontId] || FONT_MAP.default);
  }, [appearance]);

  // ── Auth listener ──
  useEffect(() => {
    const unsub = onAuthChange(async u => {
      setUser(u);
      if (u) {
        const p = await getProfile(u.id);
        setProfile(p);
        await refreshSessions(u.id);
      } else {
        resetState();
      }
    });
    return unsub;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function resetState() {
    setProfile(null); setSessions([]); setActiveId(null);
    setMessages([]); setRepoUrl(""); setUploadedFiles([]);
    setFileMode(false); setSessionFiles([]);
  }

  async function refreshSessions(userId) {
    const uid = userId || user?.id;
    if (!uid) return [];
    const all = await getAllSessions(uid);
    const starred = JSON.parse(localStorage.getItem("revai_starred") || "{}");
    const withStars = all.map(s => ({ ...s, starred: !!starred[s.id] }));
    setSessions(withStars);
    return withStars;
  }

  async function loadSession(id) {
    const sess = await getSession(id);
    if (!sess) return;
    setActiveId(id);
    setRepoUrl(sess.repo_url || "");
    setMessages(await getMessages(id));
    setUploadedFiles([]); setFileMode(false); setSessionFiles([]);
    try {
      const res = await axios.get(`${API}/session/${id}/files`);
      if (res.data.files?.length) {
        setSessionFiles(res.data.files);
        setFileMode(true);
        setUploadedFiles(res.data.files);
      }
    } catch (_) {}
  }

  async function handleNew() {
    if (!user) { setShowAuth(true); return; }
    const sess = await createSession(user.id, "");
    await refreshSessions();
    setActiveId(sess.id); setMessages([]); setRepoUrl(""); setMessage("");
    setUploadedFiles([]); setFileMode(false); setSessionFiles([]);
  }

  async function handleDelete(id) {
    await deleteSession(id);
    try { await axios.delete(`${API}/session/${id}`); } catch (_) {}
    const rem = await refreshSessions();
    if (id === activeId) {
      if (rem?.length > 0) await loadSession(rem[0].id);
      else resetState();
    }
  }

  async function handleRename(id, newTitle) {
    try {
      await updateSession(id, { title: newTitle });
      setSessions(prev => prev.map(s => s.id === id ? { ...s, title: newTitle } : s));
    } catch (e) { console.error(e); }
  }

  function handleStar(id) {
    const starred = JSON.parse(localStorage.getItem("revai_starred") || "{}");
    starred[id] = !starred[id];
    localStorage.setItem("revai_starred", JSON.stringify(starred));
    setSessions(prev => prev.map(s => s.id === id ? { ...s, starred: !!starred[id] } : s));
  }

  async function ensureSession() {
    if (activeId) return activeId;
    if (!user) { setShowAuth(true); return null; }
    const sess = await createSession(user.id, "");
    await refreshSessions();
    setActiveId(sess.id);
    return sess.id;
  }

  // ── Export chat (also used by /export slash command) ──
  function exportChat(format = "md") {
    if (!messages.length) return false;
    const title = sessions.find(s => s.id === activeId)?.title || "revai-chat";
    let content = "";

    if (format === "md") {
      content = `# ${title}\n\n` + messages.map(m =>
        `**${m.sender === "user" ? "You" : "revAi"}**\n\n${m.text}`
      ).join("\n\n---\n\n");
    } else if (format === "txt") {
      content = messages.map(m =>
        `[${m.sender === "user" ? "You" : "revAi"}]\n${m.text}`
      ).join("\n\n---\n\n");
    } else {
      content = JSON.stringify({ title, messages }, null, 2);
    }

    const ext  = format;
    const mime = format === "json" ? "application/json" : "text/plain";
    const blob = new Blob([content], { type: mime });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${title}.${ext}`; a.click();
    URL.revokeObjectURL(url);
    return true;
  }

  // ── File upload ──
  function handleFileUploaded(data) {
    const files = data.files || [{ filename: data.filename, chunks: data.chunk_count }];
    setUploadedFiles(files); setSessionFiles(files); setFileMode(true);
    const names = files.map(f => `**${f.filename}**`).join(", ");
    setMessages(prev => [...prev, {
      sender: "bot",
      text: `✅ ${names} uploaded — ${data.total_chunks || data.chunk_count} chunks ready.\n\nAsk anything about your document(s).`,
      source: "local_rag", sources: [],
    }]);
  }

  // ── Image upload ──
  async function handleUploadImage(file) {
    if (!user) { setShowAuth(true); return; }
    const sessionId = await ensureSession();
    if (!sessionId) return;

    const previewUrl = URL.createObjectURL(file);
    const question   = message.trim() || "What is in this image? Identify all items.";
    setMessages(prev => [...prev, { sender: "user", text: question, imagePreview: previewUrl }]);
    setLoading(true); setMessage("");

    try {
      const form = new FormData();
      form.append("image", file); form.append("chat_id", sessionId);
      form.append("question", question); form.append("web_search", "true");
      const res = await axios.post(`${API}/image-chat`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessages(prev => [...prev, {
        sender: "bot", text: res.data.response,
        source: res.data.source, sources: res.data.sources || [],
      }]);
      await appendMessage(sessionId, "user", question);
      await appendMessage(sessionId, "bot", res.data.response);
      await refreshSessions();
    } catch (err) {
      setMessages(prev => [...prev, { sender: "bot", text: "⚠ Image analysis failed.", source: null, sources: [] }]);
    } finally { setLoading(false); }
  }

  // ── Streaming send ──
  async function handleSendStream(sessionId, endpoint, payload) {
    setStreaming(true);
    setMessages(prev => [...prev, { sender: "bot", text: "", source: null, sources: [], streaming: true }]);

    const res = await fetch(`${API}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = ""; let source = null; let sources = [];

    // Updater functions defined outside the loop to satisfy no-loop-func
    const updateStreamText = (txt) => {
      setMessages(prev => {
        const u = [...prev];
        u[u.length - 1] = { ...u[u.length - 1], text: txt };
        return u;
      });
    };

    const finalizeStream = (txt, src, srcs) => {
      setMessages(prev => {
        const u = [...prev];
        u[u.length - 1] = { sender: "bot", text: txt, source: src, sources: srcs, streaming: false };
        return u;
      });
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split("\n");
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "text") {
            fullText += data.content;
            updateStreamText(fullText);
          } else if (data.type === "done") {
            source = data.source; sources = data.sources || [];
            finalizeStream(fullText, source, sources);
          }
        } catch (_) {} // eslint-disable-line no-empty
      }
    }

    await appendMessage(sessionId, "user", payload.message);
    await appendMessage(sessionId, "bot", fullText);
    await refreshSessions();
    setStreaming(false);
  }

  // ── Slash command handler ──
  async function handleSlashCommand(cmd) {
    switch (cmd) {
      case "/search":
        setMessage("Search the web for: ");
        break;
      case "/analyze":
        setMessage("https://github.com/");
        break;
      case "/upload": {
        const id = await ensureSession();
        if (id) setShowUpload(true);
        break;
      }
      case "/image":
        document.getElementById("img-chip-input")?.click();
        break;
      case "/clear":
        setMessages([]);
        break;
      case "/export": {
        const ok = exportChat("md");
        if (!ok) {
          setMessages(prev => [...prev, {
            sender: "bot", text: "⚠ No messages to export yet. Start a conversation first.", source: null, sources: [],
          }]);
        }
        break;
      }
      case "/help":
        setMessages(prev => [...prev, {
          sender: "bot", source: null, sources: [],
          text:
            "**Available slash commands:**\n\n" +
            "- `/search` — search the web for any topic\n" +
            "- `/analyze` — analyze a GitHub repository\n" +
            "- `/upload` — upload a file (PDF, DOCX, PPTX…)\n" +
            "- `/image` — upload and analyze an image\n" +
            "- `/clear` — clear the current chat\n" +
            "- `/export` — export chat as Markdown\n" +
            "- `/help` — show this help message",
        }]);
        break;
      default:
        break;
    }
  }

  // ── Main send ──
  async function handleSend() {
    if (!message.trim() || loading || streaming) return;
    if (!user) { setShowAuth(true); return; }
    const sessionId = await ensureSession();
    if (!sessionId) return;

    const userMsg = { sender: "user", text: message };
    setMessages(prev => [...prev, userMsg]);
    setMessage("");
    setLoading(true);

    try {
      if (fileMode && uploadedFiles.length > 0) {
        setLoading(false);
        await handleSendStream(sessionId, "/file-chat/stream", {
          chat_id: sessionId, message: userMsg.text,
        });
        return;
      }

      const urlMatch = message.match(GITHUB_URL_RE);
      let currentRepo = repoUrl;
      if (urlMatch) {
        currentRepo = urlMatch[0];
        setRepoUrl(currentRepo);
        await updateSession(sessionId, { repo_url: currentRepo });
      }

      if (currentRepo) {
        const res = await axios.post(`${API}/chat`, {
          chat_id: sessionId, repo_url: currentRepo,
          message: userMsg.text, branch: "HEAD", target_path: "",
        });
        setMessages(prev => [...prev, {
          sender: "bot", text: res.data.response,
          source: res.data.source, sources: res.data.sources || [],
        }]);
        await appendMessage(sessionId, "user", userMsg.text);
        await appendMessage(sessionId, "bot", res.data.response);
        await refreshSessions();
      } else {
        setLoading(false);
        await handleSendStream(sessionId, "/file-chat/stream", {
          chat_id: sessionId, message: userMsg.text,
        });
        return;
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        sender: "bot", text: "⚠ Backend error — check the server.", source: null, sources: [],
      }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleChip(text) {
    if (text.includes("GitHub"))        setMessage("https://github.com/");
    else if (text.includes("document")) { const id = await ensureSession(); if (id) setShowUpload(true); }
    else if (text.includes("image"))    document.getElementById("img-chip-input")?.click();
    else setMessage("Search the web for: ");
  }

  // ── Derived values ──
  const activeSession = sessions.find(s => s.id === activeId);
  const displayName   = profile?.display_name || user?.email?.split("@")[0] || "";
  const fileNames     = uploadedFiles.map(f => f.filename).join(", ");
  const topBarContent = fileMode && fileNames
    ? `📄 ${fileNames}`
    : repoUrl
      ? repoName(repoUrl)
      : activeSession?.title && messages.length > 0
        ? activeSession.title
        : null;

  const isWorking = loading || streaming;

  return (
    <div className="app-shell">

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}

      {showSettings && (
        <SettingsModal
          user={user}
          profile={profile}
          onClose={() => setShowSettings(false)}
          onProfileUpdate={setProfile}
          appearance={appearance}
          onAppearanceChange={setAppearance}
          messages={messages}
          activeSessionTitle={activeSession?.title || ""}
        />
      )}

      {showUpload && activeId && (
        <FileUploadModal
          chatId={activeId}
          existingFiles={sessionFiles}
          onClose={() => setShowUpload(false)}
          onUploaded={data => { handleFileUploaded(data); setShowUpload(false); }}
        />
      )}

      <input id="img-chip-input" type="file" accept="image/*"
        style={{ display: "none" }}
        onChange={e => { if (e.target.files[0]) handleUploadImage(e.target.files[0]); }}
      />

      <Sidebar
        sessions={sessions} activeId={activeId}
        onSelect={loadSession} onNew={handleNew}
        onDelete={handleDelete} onRename={handleRename} onStar={handleStar}
        visible={sidebarOpen} onClose={() => setSidebarOpen(false)}
        user={user} profile={profile}
        onSignInClick={() => setShowAuth(true)}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="main-content">

        {/* Top bar — clean */}
        <div className="top-bar">
          {!sidebarOpen && (
            <button className="sidebar-toggle-btn" onClick={() => setSidebarOpen(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="6"  x2="21" y2="6"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          )}

          {topBarContent
            ? <span className="top-bar-session-name">{topBarContent}</span>
            : <span className="top-bar-greeting">
                {displayName ? `${getGreeting()}, ${displayName}` : "revAi"}
              </span>
          }

          <button className="new-chat-icon-btn" onClick={handleNew} title="New chat">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
          </button>
        </div>

        {/* Chat or welcome */}
        {messages.length === 0 && !isWorking ? (
          <div className="welcome-screen">
            <div className="welcome-logo">✦</div>
            <h1 className="welcome-heading">
              {displayName ? `${getGreeting()}, ${displayName}` : "Welcome to revAi"}
            </h1>
            <p className="welcome-sub">
              Analyze repos · query documents · search the web · analyze images
            </p>
            <div className="welcome-chips">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="welcome-chip" onClick={() => handleChip(s.text)}>
                  <span>{s.icon}</span>{s.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ChatWindow messages={messages} loading={loading} userName={displayName} />
        )}

        {/* Input */}
        <div className="bottom-bar">
          <InputBox
            message={message} setMessage={setMessage}
            onSend={handleSend} disabled={isWorking}
            onUploadFile={() => {
              if (!user) { setShowAuth(true); return; }
              ensureSession().then(id => { if (id) setShowUpload(true); });
            }}
            onUploadImage={handleUploadImage}
            uploadedFile={
              uploadedFiles.length === 1
                ? uploadedFiles[0]?.filename
                : uploadedFiles.length > 1
                  ? `${uploadedFiles.length} files`
                  : null
            }
            onSlashCommand={handleSlashCommand}
          />
        </div>
      </div>
    </div>
  );
}