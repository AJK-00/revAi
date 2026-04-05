import React, { useState, useEffect, useRef } from "react";
import { upsertProfile, signOut } from "./supabaseDb";
import "./SettingsModal.css";

const NAV = [
  { id: "general",    label: "General",    icon: "⚙" },
  { id: "appearance", label: "Appearance", icon: "🎨" },
  { id: "account",    label: "Account",    icon: "👤" },
  { id: "privacy",    label: "Privacy",    icon: "🔒" },
];

const COLOR_MODES = [
  { id: "light", label: "Light" },
  { id: "auto",  label: "Auto"  },
  { id: "dark",  label: "Dark"  },
];

const FONTS = [
  { id: "default",  label: "Default",           family: "'DM Sans', system-ui, sans-serif"      },
  { id: "sans",     label: "Sans",              family: "'Inter', 'Helvetica Neue', sans-serif"  },
  { id: "mono",     label: "Mono",              family: "'JetBrains Mono', monospace"            },
  { id: "dyslexic", label: "Dyslexia-friendly", family: "'Comic Sans MS', cursive, sans-serif"  },
];

export default function SettingsModal({
  user, profile, onClose, onProfileUpdate,
  appearance, onAppearanceChange, messages = [], activeSessionTitle = "",
}) {
  const [tab, setTab]           = useState("general");
  const [displayName, setName]  = useState(profile?.display_name || "");
  const [bio, setBio]           = useState(profile?.bio || "");
  const [saving, setSaving]     = useState(false);
  const [msg, setMsg]           = useState(null);
  const fileRef = useRef(null);

  const [colorMode, setColorMode] = useState(appearance?.colorMode || "dark");
  const [fontId, setFontId]       = useState(appearance?.fontId    || "default");

  useEffect(() => {
    setName(profile?.display_name || "");
    setBio(profile?.bio || "");
  }, [profile]);

  useEffect(() => {
    const h = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  // ── Apply appearance immediately ──
  function applyColorMode(mode) {
    setColorMode(mode);
    const next = { colorMode: mode, fontId };
    onAppearanceChange?.(next);
    localStorage.setItem("revai_appearance", JSON.stringify(next));
    const root = document.documentElement;
    if (mode === "auto") {
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", dark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", mode);
    }
  }

  function applyFont(id) {
    setFontId(id);
    const next = { colorMode, fontId: id };
    onAppearanceChange?.(next);
    localStorage.setItem("revai_appearance", JSON.stringify(next));
    const fam = FONTS.find(f => f.id === id)?.family || FONTS[0].family;
    document.documentElement.style.setProperty("--font-body", fam);
  }

  // ── Save profile ──
  async function handleSaveGeneral() {
    setSaving(true); setMsg(null);
    try {
      const updated = await upsertProfile(user.id, {
        display_name: displayName.trim(),
        bio: bio.trim(),
      });
      onProfileUpdate(updated);
      setMsg({ type: "success", text: "Profile saved successfully." });
    } catch (e) {
      setMsg({ type: "error", text: e.message });
    } finally { setSaving(false); }
  }

  // ── Export chat (from messages prop) ──
  function exportChat(format) {
    if (!messages.length) {
      setMsg({ type: "error", text: "No messages to export in the current chat." });
      return;
    }
    const title = activeSessionTitle || "revai-chat";
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

    const ext  = format === "json" ? "json" : format === "md" ? "md" : "txt";
    const mime = format === "json" ? "application/json" : "text/plain";
    const blob = new Blob([content], { type: mime });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${title}.${ext}`; a.click();
    URL.revokeObjectURL(url);
    setMsg({ type: "success", text: `Exported as ${ext.toUpperCase()}.` });
  }

  async function handleSignOut() {
    await signOut();
    onClose();
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
              <span className="snav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button className="settings-nav-item danger" onClick={handleSignOut}>
            <span className="snav-icon">↪</span>Sign out
          </button>
        </nav>

        {/* ── Right content ── */}
        <div className="settings-content">

          {/* ════ GENERAL ════ */}
          {tab === "general" && (
            <>
              <h2 className="settings-section-title">Profile</h2>

              <div className="avatar-row">
                <div className="avatar-large">{initials}</div>
                <div className="avatar-actions">
                  <button className="avatar-upload-btn"
                    onClick={() => fileRef.current?.click()}>
                    Change photo
                  </button>
                  <input ref={fileRef} type="file" accept="image/*"
                    style={{ display: "none" }}
                    onChange={() => setMsg({ type: "error", text: "Avatar upload via Supabase Storage — coming soon." })}
                  />
                </div>
              </div>

              <div className="settings-field-row">
                <div className="settings-field">
                  <label>Display name</label>
                  <input type="text" value={displayName}
                    onChange={e => setName(e.target.value)}
                    placeholder="Your name" />
                </div>
                <div className="settings-field">
                  <label>Email</label>
                  <input type="email" value={email} disabled />
                </div>
              </div>

              <div className="settings-field">
                <label>Bio (optional)</label>
                <textarea value={bio} onChange={e => setBio(e.target.value)}
                  placeholder="Tell us a bit about yourself…" />
              </div>

              {msg && <div className={`settings-msg ${msg.type}`}>{msg.text}</div>}
              <button className="settings-save-btn"
                onClick={handleSaveGeneral} disabled={saving}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            </>
          )}

          {/* ════ APPEARANCE ════ */}
          {tab === "appearance" && (
            <>
              <h2 className="settings-section-title">Appearance</h2>

              {/* Color mode */}
              <div className="settings-group-label">Color mode</div>
              <div className="appearance-cards">
                {COLOR_MODES.map(m => (
                  <button key={m.id}
                    className={`appearance-card ${colorMode === m.id ? "selected" : ""}`}
                    onClick={() => applyColorMode(m.id)}>
                    <div className={`theme-preview theme-preview-${m.id}`}>
                      <div className="tp-sidebar" />
                      <div className="tp-main">
                        <div className="tp-bar" />
                        <div className="tp-bubble" />
                        <div className="tp-dot" />
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
                    className={`font-card ${fontId === f.id ? "selected" : ""}`}
                    style={{ fontFamily: f.family }}
                    onClick={() => applyFont(f.id)}>
                    <span className="font-sample">Aa</span>
                    <span className="font-label" style={{ fontFamily: "var(--font-body)" }}>
                      {f.label}
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* ════ ACCOUNT ════ */}
          {tab === "account" && (
            <>
              <h2 className="settings-section-title">Account</h2>

              {/* Signed-in card */}
              <div className="account-card">
                <div className="avatar-large" style={{ width: 40, height: 40, fontSize: "0.9rem" }}>
                  {initials}
                </div>
                <div>
                  <div className="account-name">
                    {profile?.display_name || email.split("@")[0]}
                  </div>
                  <div className="account-email">{email}</div>
                </div>
              </div>

              <hr className="settings-divider" />

              <div className="settings-group-label">Active sessions</div>
              <div className="session-row">
                <div>
                  <div className="session-row-device">This browser</div>
                  <div className="session-row-meta">Current session</div>
                </div>
                <span className="session-current-tag">Current</span>
              </div>

              <hr className="settings-divider" />

              <div className="danger-zone">
                <div className="danger-zone-title">Danger zone</div>
                <div className="danger-zone-desc">
                  Deleting your account is permanent. All chats and data will be removed.
                </div>
                <button className="danger-btn"
                  onClick={() => setMsg({ type: "error", text: "Contact support to delete your account." })}>
                  Delete account
                </button>
                {msg && <div className={`settings-msg ${msg.type}`} style={{ marginTop: 12 }}>{msg.text}</div>}
              </div>
            </>
          )}

          {/* ════ PRIVACY ════ */}
          {tab === "privacy" && (
            <>
              <h2 className="settings-section-title">Privacy</h2>

              <div className="privacy-info-card">
                <span className="privacy-shield">🔒</span>
                <div>
                  <div className="privacy-heading">Your data is protected</div>
                  <div className="privacy-sub">
                    revAi uses Supabase with Row-Level Security. Only you can access
                    your chats. Files you upload are processed in memory and not stored permanently.
                  </div>
                </div>
              </div>

              <hr className="settings-divider" />
              <div className="settings-group-label">Privacy settings</div>

              {/* Export data */}
              <div className="privacy-row">
                <div>
                  <div className="privacy-row-label">Export data</div>
                  <div className="privacy-row-sub">
                    Download your current chat conversation.
                  </div>
                </div>
                <div className="privacy-export-btns">
                  <button className="privacy-action-btn" onClick={() => exportChat("md")}>
                    Markdown
                  </button>
                  <button className="privacy-action-btn" onClick={() => exportChat("txt")}>
                    Text
                  </button>
                  <button className="privacy-action-btn" onClick={() => exportChat("json")}>
                    JSON
                  </button>
                </div>
              </div>

              <hr className="settings-divider" />

              <div className="privacy-row">
                <div>
                  <div className="privacy-row-label">Conversation memory</div>
                  <div className="privacy-row-sub">
                    Older turns are automatically summarized to maintain context
                    without hitting token limits.
                  </div>
                </div>
                <span className="privacy-badge">Enabled</span>
              </div>

              <hr className="settings-divider" />

              <div className="privacy-row">
                <div>
                  <div className="privacy-row-label">Session data</div>
                  <div className="privacy-row-sub">
                    Uploaded files are stored temporarily in memory and cleared when
                    the server restarts. Chat history is saved to Supabase, encrypted at rest.
                  </div>
                </div>
                <span className="privacy-badge">Secure</span>
              </div>

              {msg && <div className={`settings-msg ${msg.type}`} style={{ marginTop: 16 }}>{msg.text}</div>}
            </>
          )}

        </div>
      </div>
    </div>
  );
}