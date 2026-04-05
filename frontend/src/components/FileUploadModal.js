import React, { useState, useEffect, useRef } from "react";
import { upsertProfile, signOut } from "./supabaseDb";
import "./SettingsModal.css";

const COLOR_MODES = [
  { id: "light", label: "Light" },
  { id: "auto",  label: "Auto"  },
  { id: "dark",  label: "Dark"  },
];

const FONTS = [
  { id: "default",  label: "Default",           family: "'DM Sans',sans-serif"                   },
  { id: "sans",     label: "Sans",              family: "'Inter','Helvetica Neue',sans-serif"     },
  { id: "mono",     label: "System",            family: "system-ui,sans-serif"                   },
  { id: "dyslexic", label: "Dyslexia-friendly", family: "'Comic Sans MS',cursive"                },
];

const NAV = [
  { id: "general",    label: "General"    },
  { id: "account",    label: "Account"    },
  { id: "appearance", label: "Appearance" },
  { id: "privacy",    label: "Privacy"    },
];

function SettingsModal({
  user, profile, onClose, onProfileUpdate,
  appearance = { colorMode: "dark", fontId: "default" },
  onAppearanceChange,
  messages = [], sessions = [], activeId = null,
}) {
  const [tab, setTab]           = useState("general");
  const [displayName, setName]  = useState(profile?.display_name || "");
  const [bio, setBio]           = useState(profile?.bio || "");
  const [saving, setSaving]     = useState(false);
  const [msg, setMsg]           = useState(null);
  const fileRef                 = useRef(null);

  useEffect(() => {
    setName(profile?.display_name || "");
    setBio(profile?.bio || "");
  }, [profile]);

  useEffect(() => {
    const h = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  async function handleSaveGeneral() {
    setSaving(true); setMsg(null);
    try {
      const updated = await upsertProfile(user.id, {
        display_name: displayName.trim(), bio: bio.trim(),
      });
      onProfileUpdate(updated);
      setMsg({ type: "success", text: "Profile saved." });
    } catch (e) {
      setMsg({ type: "error", text: e.message });
    } finally { setSaving(false); }
  }

  function updateAppearance(patch) {
    const next = { ...appearance, ...patch };
    onAppearanceChange(next);
    localStorage.setItem("revai_appearance", JSON.stringify(next));
  }

  function exportChat(format) {
    if (!messages.length) return;
    const title = sessions.find(s => s.id === activeId)?.title || "chat";
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
    const mime = format === "json" ? "application/json" : "text/plain";
    const blob = new Blob([content], { type: mime });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${title}.${format}`; a.click();
    URL.revokeObjectURL(url);
    setMsg({ type: "success", text: `Exported as .${format}` });
  }

  const initials = (profile?.display_name || user?.email || "U").slice(0, 2).toUpperCase();
  const email    = user?.email || "";

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-shell" onClick={e => e.stopPropagation()}>

        {/* ── Left nav ── */}
        <nav className="settings-nav">
          <div className="settings-nav-title">Settings</div>
          {NAV.map(n => (
            <button key={n.id}
              className={`settings-nav-item ${tab === n.id ? "active" : ""}`}
              onClick={() => { setTab(n.id); setMsg(null); }}>
              {n.label}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button className="settings-nav-item danger"
            onClick={() => { signOut(); onClose(); }}>
            Sign out
          </button>
        </nav>

        {/* ── Right content ── */}
        <div className="settings-content">

          {/* GENERAL */}
          {tab === "general" && (
            <>
              <div className="settings-section-title">Profile</div>
              <div className="avatar-row">
                <div className="avatar-large">{initials}</div>
                <div className="avatar-actions">
                  <button className="avatar-upload-btn" onClick={() => fileRef.current?.click()}>
                    Change photo
                  </button>
                  <input ref={fileRef} type="file" accept="image/*" style={{ display:"none" }}
                    onChange={() => setMsg({ type:"error", text:"Avatar upload coming soon." })} />
                </div>
              </div>
              <div className="settings-field-row">
                <div className="settings-field">
                  <label>Display name</label>
                  <input type="text" value={displayName}
                    onChange={e => setName(e.target.value)} placeholder="Your name" />
                </div>
                <div className="settings-field">
                  <label>Email</label>
                  <input type="email" value={email} disabled />
                </div>
              </div>
              <div className="settings-field">
                <label>Bio</label>
                <textarea value={bio} onChange={e => setBio(e.target.value)}
                  placeholder="Tell us about yourself…" />
              </div>
              {msg && <div className={`settings-msg ${msg.type}`}>{msg.text}</div>}
              <button className="settings-save-btn" onClick={handleSaveGeneral} disabled={saving}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            </>
          )}

          {/* ACCOUNT */}
          {tab === "account" && (
            <>
              <div className="settings-section-title">Account</div>
              <div className="account-card">
                <div className="avatar-large" style={{ width:40, height:40, fontSize:"0.9rem" }}>
                  {initials}
                </div>
                <div>
                  <div className="account-name">{profile?.display_name || email.split("@")[0]}</div>
                  <div className="account-email">{email}</div>
                </div>
              </div>
              <hr className="settings-divider"/>
              <div className="settings-group-label">Active sessions</div>
              <div className="session-row">
                <div className="session-row-info">
                  <div className="session-row-device">This browser</div>
                  <div className="session-row-meta">Current session</div>
                </div>
                <span className="session-current-tag">Current</span>
              </div>
              <hr className="settings-divider"/>
              <div className="danger-zone">
                <div className="danger-zone-title">Danger zone</div>
                <div className="danger-zone-desc">
                  Deleting your account is permanent and cannot be undone.
                </div>
                <button className="danger-btn"
                  onClick={() => setMsg({ type:"error", text:"Contact support to delete your account." })}>
                  Delete account
                </button>
                {msg && <div className={`settings-msg ${msg.type}`} style={{ marginTop:12 }}>{msg.text}</div>}
              </div>
            </>
          )}

          {/* APPEARANCE */}
          {tab === "appearance" && (
            <>
              <div className="settings-section-title">Appearance</div>

              {/* Color mode */}
              <div className="settings-group-label">Color mode</div>
              <div className="appearance-cards">
                {COLOR_MODES.map(m => (
                  <button key={m.id}
                    className={`appearance-card ${appearance.colorMode === m.id ? "selected" : ""}`}
                    onClick={() => updateAppearance({ colorMode: m.id })}>
                    <div className={`color-preview cp-${m.id}`}>
                      <div className="cp-bar" />
                      <div className="cp-body">
                        <div className="cp-line" /><div className="cp-line short" />
                        <div className="cp-bubble" />
                      </div>
                    </div>
                    <span className="appearance-label">{m.label}</span>
                  </button>
                ))}
              </div>

              <hr className="settings-divider" />

              {/* Chat font */}
              <div className="settings-group-label">Chat font</div>
              <div className="font-cards">
                {FONTS.map(f => (
                  <button key={f.id}
                    className={`font-card ${appearance.fontId === f.id ? "selected" : ""}`}
                    onClick={() => updateAppearance({ fontId: f.id })}>
                    <span className="font-sample" style={{ fontFamily: f.family }}>Aa</span>
                    <span className="font-label">{f.label}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* PRIVACY */}
          {tab === "privacy" && (
            <>
              <div className="settings-section-title">Privacy</div>

              <div className="privacy-hero">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="1.5" style={{ color:"var(--accent)", flexShrink:0 }}>
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                <div>
                  <div className="privacy-hero-title">Your data is private</div>
                  <div className="privacy-hero-sub">
                    Chats are stored securely in your own Supabase database with row-level security.
                  </div>
                </div>
              </div>

              <hr className="settings-divider" />

              <div className="settings-group-label">Export data</div>
              <p className="settings-field-hint">
                Download your current conversation in your preferred format.
              </p>

              {messages.length === 0 ? (
                <p className="settings-field-hint" style={{ fontStyle:"italic", marginTop:6 }}>
                  No messages in the current chat to export.
                </p>
              ) : (
                <div className="export-buttons">
                  {["md","txt","json"].map(fmt => (
                    <button key={fmt} className="export-btn" onClick={() => exportChat(fmt)}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="12" y1="18" x2="12" y2="12"/>
                        <line x1="9" y1="15" x2="15" y2="15"/>
                      </svg>
                      {fmt === "md" ? "Markdown (.md)" : fmt === "txt" ? "Plain text (.txt)" : "JSON (.json)"}
                    </button>
                  ))}
                </div>
              )}

              {msg && <div className={`settings-msg ${msg.type}`} style={{ marginTop:12 }}>{msg.text}</div>}

              <hr className="settings-divider" />

              <div className="privacy-row">
                <div>
                  <div className="privacy-row-title">How we protect your data</div>
                  <div className="privacy-row-sub">
                    All data is stored in your Supabase project. Anthropic Gemini API processes queries but does not store chat history.
                  </div>
                </div>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
}

export default SettingsModal;