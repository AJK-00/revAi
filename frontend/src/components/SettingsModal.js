import React, { useState, useEffect, useRef } from "react";
import { upsertProfile, signOut } from "./supabaseDb";
import "./SettingsModal.css";

const NAV = [
  {
    id: "general", label: "General",
    icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
  },
  {
    id: "account", label: "Account",
    icon: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
  },
];

function SettingsModal({ user, profile, onClose, onProfileUpdate }) {
  const [tab, setTab]           = useState("general");
  const [displayName, setName]  = useState(profile?.display_name || "");
  const [bio, setBio]           = useState(profile?.bio || "");
  const [saving, setSaving]     = useState(false);
  const [msg, setMsg]           = useState(null); // {type:'success'|'error', text}
  const fileRef                 = useRef(null);

  useEffect(() => {
    setName(profile?.display_name || "");
    setBio(profile?.bio || "");
  }, [profile]);

  // Close on Escape
  useEffect(() => {
    const h = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  async function handleSaveGeneral() {
    setSaving(true); setMsg(null);
    try {
      const updated = await upsertProfile(user.id, {
        display_name: displayName.trim(),
        bio: bio.trim(),
      });
      onProfileUpdate(updated);
      setMsg({ type: "success", text: "Profile saved." });
    } catch (e) {
      setMsg({ type: "error", text: e.message });
    } finally {
      setSaving(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    onClose();
  }

  const initials    = (profile?.display_name || user?.email || "U").slice(0, 2).toUpperCase();
  const email       = user?.email || "";

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-shell" onClick={e => e.stopPropagation()}>

        {/* ── Left nav ── */}
        <nav className="settings-nav">
          <div className="settings-nav-title">Settings</div>
          {NAV.map(n => (
            <button
              key={n.id}
              className={`settings-nav-item ${tab === n.id ? "active" : ""}`}
              onClick={() => { setTab(n.id); setMsg(null); }}
            >
              {n.icon}{n.label}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button className="settings-nav-item danger" onClick={handleSignOut}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign out
          </button>
        </nav>

        {/* ── Right content ── */}
        <div className="settings-content">

          {/* ── GENERAL ── */}
          {tab === "general" && (
            <>
              <div className="settings-section-title">Profile</div>

              {/* Avatar */}
              <div className="avatar-row">
                <div className="avatar-large">
                  {profile?.avatar_url
                    ? <img src={profile.avatar_url} alt={displayName} />
                    : initials}
                </div>
                <div className="avatar-actions">
                  <button className="avatar-upload-btn" onClick={() => fileRef.current?.click()}>
                    Change photo
                  </button>
                  <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
                    onChange={() => setMsg({ type: "error", text: "Avatar upload requires Supabase Storage — coming soon." })}
                  />
                </div>
              </div>

              <div className="settings-field-row">
                <div className="settings-field">
                  <label>Display name</label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setName(e.target.value)}
                    placeholder="Your name"
                  />
                </div>
                <div className="settings-field">
                  <label>Email</label>
                  <input type="email" value={email} disabled />
                </div>
              </div>

              <div className="settings-field">
                <label>Bio (optional)</label>
                <textarea
                  value={bio}
                  onChange={e => setBio(e.target.value)}
                  placeholder="Tell us a bit about yourself…"
                />
              </div>

              {msg && <div className={`settings-msg ${msg.type}`}>{msg.text}</div>}
              <button className="settings-save-btn" onClick={handleSaveGeneral} disabled={saving}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            </>
          )}

          {/* ── ACCOUNT ── */}
          {tab === "account" && (
            <>
              <div className="settings-section-title">Account</div>

              <div className="settings-group-label" style={{ fontSize: "0.9rem", fontWeight: 500, color: "var(--text-secondary)", marginBottom: 12 }}>
                Signed in as
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px",
                background: "var(--surface-2)", borderRadius: 10, border: "1px solid var(--border)",
                marginBottom: 24 }}>
                <div className="avatar-large" style={{ width: 40, height: 40, fontSize: "0.9rem" }}>
                  {initials}
                </div>
                <div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {profile?.display_name || email.split("@")[0]}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{email}</div>
                </div>
              </div>

              <hr className="settings-divider" />

              <div className="settings-group-label">Active sessions</div>
              <div className="session-row">
                <div className="session-row-info">
                  <div className="session-row-device">This browser</div>
                  <div className="session-row-meta">Current session</div>
                </div>
                <span className="session-current-tag">Current</span>
              </div>

              <hr className="settings-divider" />

              <div className="danger-zone">
                <div className="danger-zone-title">Danger zone</div>
                <div className="danger-zone-desc">
                  Deleting your account is permanent. All your chats and data will be removed and cannot be recovered.
                </div>
                <button className="danger-btn"
                  onClick={() => setMsg({ type: "error", text: "Contact support to delete your account." })}>
                  Delete account
                </button>
                {msg && <div className={`settings-msg ${msg.type}`} style={{ marginTop: 12 }}>{msg.text}</div>}
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
}

export default SettingsModal;