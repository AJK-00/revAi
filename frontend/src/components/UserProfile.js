import React, { useState, useEffect, useRef } from "react";
import { signOut } from "./supabaseDb";
import "./UserProfile.css";

function UserProfile({ user, profile, onSignInClick, onOpenSettings }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handler(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleSignOut() {
    setOpen(false);
    await signOut();
  }

  function handleSettings() {
    setOpen(false);
    onOpenSettings?.();
  }

  // ── Not logged in ──
  if (!user) {
    return (
      <div className="user-profile">
        <button className="profile-signin-btn" onClick={onSignInClick}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
            <polyline points="10 17 15 12 10 7"/>
            <line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          Sign in
        </button>
      </div>
    );
  }

  const displayName = profile?.display_name || user.email?.split("@")[0] || "User";
  const email       = user.email || "";
  const initials    = displayName.slice(0, 2).toUpperCase();

  return (
    <div className="user-profile" ref={menuRef}>
      {open && (
        <div className="profile-menu">
          <div className="profile-menu-header">
            <div className="profile-menu-name">{displayName}</div>
            <div className="profile-menu-email">{email}</div>
          </div>

          <button className="profile-menu-item" onClick={handleSettings}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
            </svg>
            Settings
          </button>

          <button className="profile-menu-item danger" onClick={handleSignOut}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign out
          </button>
        </div>
      )}

      <div className={`profile-row ${open ? "open" : ""}`} onClick={() => setOpen(!open)}>
        <div className="profile-avatar">
          {profile?.avatar_url
            ? <img src={profile.avatar_url} alt={displayName} />
            : initials}
        </div>
        <div className="profile-info">
          <div className="profile-name">{displayName}</div>
          <div className="profile-email">{email}</div>
        </div>
        <span className="profile-chevron">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2">
            <polyline points="18 15 12 9 6 15"/>
          </svg>
        </span>
      </div>
    </div>
  );
}

export default UserProfile;