import React, { useState, useMemo, useRef, useEffect } from "react";
import UserProfile from "./UserProfile";
import "../Styles/SideBar.css";

function SessionMenu({ session, onRename, onStar, onDelete, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div className="session-menu" ref={ref} onClick={e => e.stopPropagation()}>
      <button className="session-menu-item" onClick={() => { onStar(session.id); onClose(); }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill={session.starred ? "currentColor" : "none"}
          stroke="currentColor" strokeWidth="2">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
        {session.starred ? "Unstar" : "Star"}
      </button>
      <button className="session-menu-item" onClick={() => { onRename(session); onClose(); }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        Rename
      </button>
      <div className="session-menu-divider"/>
      <button className="session-menu-item danger" onClick={() => { onDelete(session.id); onClose(); }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6M14 11v6"/>
        </svg>
        Delete
      </button>
    </div>
  );
}

function Sidebar({
  sessions, activeId, onSelect, onNew, onDelete, onRename, onStar,
  visible, onClose, user, profile, onSignInClick, onOpenSettings,
}) {
  const [query, setQuery]         = useState("");
  const [menuFor, setMenuFor]     = useState(null);   // session id with open menu
  const [renaming, setRenaming]   = useState(null);   // session being renamed
  const [renameVal, setRenameVal] = useState("");

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    let list = q
      ? sessions.filter(s =>
          s.title?.toLowerCase().includes(q) ||
          s.repo_url?.toLowerCase().includes(q))
      : sessions;

    // Starred sessions first
    return [...list].sort((a, b) => (b.starred ? 1 : 0) - (a.starred ? 1 : 0));
  }, [sessions, query]);

  function startRename(session) {
    setRenaming(session.id);
    setRenameVal(session.title || "");
  }

  function commitRename(id) {
    if (renameVal.trim()) onRename(id, renameVal.trim());
    setRenaming(null);
  }

  return (
    <aside className={`sidebar ${visible ? "" : "hidden"}`}>

      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <span className="brand-hex">⬡</span>
          <span className="brand-name">revAi</span>
        </div>
        <button className="sidebar-close-btn" onClick={onClose} title="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>

      {/* New chat */}
      <button className="new-chat-btn" onClick={onNew}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        New chat
      </button>

      {/* Search */}
      <div className="sidebar-search-wrap">
        <svg className="sidebar-search-icon" width="13" height="13"
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input className="sidebar-search" type="text" placeholder="Search chats…"
          value={query} onChange={e => setQuery(e.target.value)}/>
        {query && <button className="sidebar-search-clear" onClick={() => setQuery("")}>✕</button>}
      </div>

      {/* Sessions */}
      <div className="sidebar-section">
        {filtered.length === 0 ? (
          <p className="sidebar-empty">{query ? "No chats found" : "No chats yet"}</p>
        ) : (
          <>
            {filtered.some(s => s.starred) && (
              <p className="sidebar-label">Starred</p>
            )}
            {filtered.map((s, i) => {
              const showRecentsLabel =
                !s.starred &&
                (i === 0 || filtered[i - 1]?.starred) &&
                filtered.some(x => x.starred);

              return (
                <React.Fragment key={s.id}>
                  {showRecentsLabel && <p className="sidebar-label">Recents</p>}

                  <div className={`session-item ${s.id === activeId ? "active" : ""}`}
                    onClick={() => { if (renaming !== s.id) onSelect(s.id); }}>

                    {/* Star icon (visible if starred) */}
                    {s.starred && (
                      <span className="session-star-icon">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                      </span>
                    )}

                    {/* Title or rename input */}
                    {renaming === s.id ? (
                      <input
                        className="session-rename-input"
                        value={renameVal}
                        autoFocus
                        onChange={e => setRenameVal(e.target.value)}
                        onBlur={() => commitRename(s.id)}
                        onKeyDown={e => {
                          if (e.key === "Enter") commitRename(s.id);
                          if (e.key === "Escape") setRenaming(null);
                        }}
                        onClick={e => e.stopPropagation()}
                      />
                    ) : (
                      <span className="session-label" title={s.title}>{s.title}</span>
                    )}

                    {/* ··· menu button */}
                    <div className="session-menu-wrap" style={{ position: "relative" }}>
                      <button className="session-dots"
                        title="More options"
                        onClick={e => {
                          e.stopPropagation();
                          setMenuFor(menuFor === s.id ? null : s.id);
                        }}>
                        ···
                      </button>

                      {menuFor === s.id && (
                        <SessionMenu
                          session={s}
                          onRename={startRename}
                          onStar={onStar}
                          onDelete={onDelete}
                          onClose={() => setMenuFor(null)}
                        />
                      )}
                    </div>
                  </div>
                </React.Fragment>
              );
            })}
          </>
        )}
      </div>

      {/* User profile */}
      <UserProfile
        user={user} profile={profile}
        onSignInClick={onSignInClick}
        onOpenSettings={onOpenSettings}
      />
    </aside>
  );
}

export default Sidebar;