import React from "react";
import UserProfile from "./UserProfile";
import "../Styles/SideBar.css";

function Sidebar({ sessions, activeId, onSelect, onNew, onDelete, visible, onClose,
                   user, profile, onSignInClick, onOpenSettings }) {
  return (
    <aside className={`sidebar ${visible ? "" : "hidden"}`}>

      {/* ── Header ── */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <span className="brand-hex">⬡</span>
          <span className="brand-name">revAi</span>
        </div>
        <button className="sidebar-close-btn" onClick={onClose} title="Close sidebar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>

      {/* ── New Chat ── */}
      <button className="new-chat-btn" onClick={onNew}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        New chat
      </button>

      {/* ── Sessions list ── */}
      <div className="sidebar-section">
        {sessions.length === 0 ? (
          <p className="sidebar-empty">No chats yet</p>
        ) : (
          <>
            <p className="sidebar-label">Recents</p>
            {sessions.map(s => (
              <div
                key={s.id}
                className={`session-item ${s.id === activeId ? "active" : ""}`}
                onClick={() => onSelect(s.id)}
              >
                <span className="session-icon">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </span>
                <span className="session-label" title={s.title}>{s.title}</span>
                <button
                  className="session-delete"
                  title="Delete"
                  onClick={e => { e.stopPropagation(); onDelete(s.id); }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                    <path d="M10 11v6M14 11v6"/>
                  </svg>
                </button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* ── User Profile (bottom) ── */}
      <UserProfile
        user={user}
        profile={profile}
        onSignInClick={onSignInClick}
        onOpenSettings={onOpenSettings}
      />
    </aside>
  );
}

export default Sidebar;