import React, { useState, useEffect } from "react";
import axios from "axios";

import Sidebar       from "./components/sidebar";
import ChatWindow    from "./components/Chatwindow";
import InputBox      from "./components/InputBox";
import AuthModal     from "./components/AuthModal";
import SettingsModal from "./components/SettingsModal";


import {
  onAuthChange,
  getProfile,
  getAllSessions,
  getSession,
  getMessages,
  createSession,
  updateSession,
  deleteSession,
  appendMessage,
} from "./components/supabaseDb";

import "./Styles/layout.css";
import "./Styles/chat.css";
import "./Styles/input.css";
import "./Styles/SideBar.css";
import "./components/AuthModal.css";
import "./components/UserProfile.css";
import "./components/SettingsModal.css";
import "./App.css";

const GITHUB_URL_RE = /https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/i;

function repoName(url) {
  if (!url) return "";
  return url.replace(/https?:\/\/github\.com\//i, "").replace(/\.git$/, "").split("/").slice(0, 2).join("/");
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function App() {
  // ── Auth ──
  const [user, setUser]           = useState(null);
  const [profile, setProfile]     = useState(null);
  const [showAuth, setShowAuth]   = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // ── Chat ──
  const [sessions, setSessions]   = useState([]);
  const [activeId, setActiveId]   = useState(null);
  const [messages, setMessages]   = useState([]);
  const [repoUrl, setRepoUrl]     = useState("");
  const [message, setMessage]     = useState("");
  const [loading, setLoading]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // ── Auth listener ──
  useEffect(() => {
    const unsub = onAuthChange(async (u) => {
      setUser(u);
      if (u) {
        const p = await getProfile(u.id);
        setProfile(p);
        await refreshSessions(u.id);
      } else {
        setProfile(null);
        setSessions([]);
        setActiveId(null);
        setMessages([]);
        setRepoUrl("");
      }
    });
    return unsub;
  }, []);

  async function refreshSessions(userId) {
    const uid = userId || user?.id;
    if (!uid) return [];
    const all = await getAllSessions(uid);
    setSessions(all);
    return all;
  }

  async function loadSession(id) {
    const sess = await getSession(id);
    if (!sess) return;
    setActiveId(id);
    setRepoUrl(sess.repo_url || "");
    const msgs = await getMessages(id);
    setMessages(msgs);
  }

  async function handleNew() {
    if (!user) { setShowAuth(true); return; }
    const sess = await createSession(user.id, "");
    await refreshSessions();
    setActiveId(sess.id);
    setMessages([]);
    setRepoUrl("");
    setMessage("");
  }

  async function handleDelete(id) {
    await deleteSession(id);
    const remaining = await refreshSessions();
    if (id === activeId) {
      if (remaining?.length > 0) await loadSession(remaining[0].id);
      else { setActiveId(null); setMessages([]); setRepoUrl(""); }
    }
  }

  async function handleSend() {
    if (!message.trim() || loading) return;
    if (!user) { setShowAuth(true); return; }

    const urlMatch = message.match(GITHUB_URL_RE);
    let currentRepo = repoUrl;
    if (urlMatch) { currentRepo = urlMatch[0]; setRepoUrl(currentRepo); }

    let sessionId = activeId;
    if (!sessionId) {
      const sess = await createSession(user.id, currentRepo);
      sessionId = sess.id;
      setActiveId(sessionId);
    } else if (currentRepo && currentRepo !== repoUrl) {
      await updateSession(sessionId, { repo_url: currentRepo });
    }

    const userMsg = { sender: "user", text: message };
    setMessages(prev => [...prev, userMsg]);
    await appendMessage(sessionId, "user", message);
    await refreshSessions();

    setMessage("");
    setLoading(true);

    try {
      const res = await axios.post("http://127.0.0.1:8000/chat", {
        chat_id:  sessionId,
        repo_url: currentRepo,
        message:  message,
      });
      const botMsg = { sender: "bot", text: res.data.response };
      setMessages(prev => [...prev, botMsg]);
      await appendMessage(sessionId, "bot", res.data.response);
      await refreshSessions();
    } catch (err) {
      console.error(err);
      const errMsg = { sender: "bot", text: "⚠ Backend error — make sure the server is running." };
      setMessages(prev => [...prev, errMsg]);
      await appendMessage(sessionId, "bot", errMsg.text);
    } finally {
      setLoading(false);
    }
  }

  // ── Top bar title logic ──
  // If repo loaded → show "owner/repo"
  // Else if messages exist → show session title
  // Else → show "Good morning, Name"
  const activeSession = sessions.find(s => s.id === activeId);
  const displayName   = profile?.display_name || user?.email?.split("@")[0] || "";

  const isGreeting    = !repoUrl && messages.length === 0;
  const topBarContent = repoUrl
    ? repoName(repoUrl)
    : activeSession?.title && messages.length > 0
      ? activeSession.title
      : null; // will show greeting

  return (
    <div className="app-shell">
      {showAuth     && <AuthModal onClose={() => setShowAuth(false)} />}
      {showSettings && (
        <SettingsModal
          user={user}
          profile={profile}
          onClose={() => setShowSettings(false)}
          onProfileUpdate={(updated) => setProfile(updated)}
        />
      )}

      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={loadSession}
        onNew={handleNew}
        onDelete={handleDelete}
        visible={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        user={user}
        profile={profile}
        onSignInClick={() => setShowAuth(true)}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="main-content">
        {/* ── Top Bar ── */}
        <div className="top-bar">
          {!sidebarOpen && (
            <button className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen(true)} title="Open sidebar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="6"  x2="21" y2="6"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          )}

          {topBarContent ? (
            <span className="top-bar-session-name">{topBarContent}</span>
          ) : (
            <span className="top-bar-greeting">
              {displayName ? `${getGreeting()}, ${displayName}` : "revAi"}
            </span>
          )}

          <button className="new-chat-icon-btn" onClick={handleNew} title="New chat">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
          </button>
        </div>

        {/* ── Chat or Welcome ── */}
        {messages.length === 0 && !loading ? (
          <div className="welcome-screen">
            <div className="welcome-icon">⬡</div>
            <p className="welcome-title">
              {displayName ? `${getGreeting()}, ${displayName}` : "Welcome to revAi"}
            </p>
            <p className="welcome-sub">
              {user
                ? "Paste a GitHub URL or ask anything about a loaded repo."
                : "Sign in to save your chats, or start exploring a repo."}
            </p>
          </div>
        ) : (
          <ChatWindow messages={messages} loading={loading} userName={displayName} />
        )}

        {/* ── Input (no keyboard hint) ── */}
        <div className="bottom-bar">
          <InputBox
            message={message}
            setMessage={setMessage}
            onSend={handleSend}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  );
}