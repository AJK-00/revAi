import React, { useRef, useState, useEffect } from "react";
import "../Styles/input.css";

const SLASH_COMMANDS = [
  { cmd: "/search",  icon: "🌐", desc: "Search the web"          },
  { cmd: "/analyze", icon: "⬡", desc: "Analyze a GitHub repo"   },
  { cmd: "/upload",  icon: "📎", desc: "Upload a file"           },
  { cmd: "/image",   icon: "🖼", desc: "Upload & analyze image"  },
  { cmd: "/clear",   icon: "🗑", desc: "Clear current chat"      },
  { cmd: "/export",  icon: "⬇", desc: "Export chat as markdown" },
  { cmd: "/help",    icon: "❓", desc: "Show all commands"        },
];

const ATTACH_MENU = [
  { id: "file",  icon: "📎", label: "Upload file",  hint: "PDF, DOCX, PPTX, XLSX, TXT"   },
  { id: "image", icon: "🖼", label: "Upload image", hint: "JPG, PNG, GIF, WEBP"           },
];

function InputBox({
  message, setMessage, onSend, disabled,
  onUploadFile, onUploadImage, uploadedFile,
  onSlashCommand,
}) {
  const textareaRef  = useRef(null);
  const fileInputRef = useRef(null);
  const imgInputRef  = useRef(null);
  const menuRef      = useRef(null);

  const [showAttach, setShowAttach] = useState(false);
  const [slashHints, setSlashHints] = useState([]);  // filtered slash commands
  const [slashIdx, setSlashIdx]     = useState(0);   // keyboard selection

  // ── Ctrl+U shortcut ──
  useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "u") {
        e.preventDefault();
        setShowAttach(v => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ── Close attach dropdown on outside click ──
  useEffect(() => {
    function handler(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowAttach(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ── Slash command filtering ──
  useEffect(() => {
    if (message.startsWith("/")) {
      const q = message.toLowerCase();
      const filtered = SLASH_COMMANDS.filter(c => c.cmd.startsWith(q));
      setSlashHints(filtered);
      setSlashIdx(0);
    } else {
      setSlashHints([]);
    }
  }, [message]);

  function autoResize() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  }

  function handleKeyDown(e) {
    // Slash command navigation
    if (slashHints.length > 0) {
      if (e.key === "ArrowDown")  { e.preventDefault(); setSlashIdx(i => (i+1) % slashHints.length); return; }
      if (e.key === "ArrowUp")    { e.preventDefault(); setSlashIdx(i => (i-1+slashHints.length) % slashHints.length); return; }
      if (e.key === "Tab" || (e.key === "Enter" && slashHints.length > 0)) {
        e.preventDefault();
        selectSlash(slashHints[slashIdx]);
        return;
      }
      if (e.key === "Escape") { setSlashHints([]); return; }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  }

  function selectSlash(item) {
    setSlashHints([]);
    setMessage("");
    onSlashCommand?.(item.cmd);
  }

  function pickAttach(id) {
    setShowAttach(false);
    if (id === "file")  fileInputRef.current?.click();
    if (id === "image") imgInputRef.current?.click();
  }

  return (
    <div className="input-outer" ref={menuRef}>

      {/* File badge */}
      {uploadedFile && (
        <div className="input-file-badge">
          <span className="input-file-icon">📄</span>
          <span className="input-file-name">{uploadedFile}</span>
          <span className="input-file-mode">file mode</span>
        </div>
      )}

      {/* Slash command palette */}
      {slashHints.length > 0 && (
        <div className="slash-palette">
          {slashHints.map((c, i) => (
            <button
              key={c.cmd}
              className={`slash-item ${i === slashIdx ? "slash-selected" : ""}`}
              onClick={() => selectSlash(c)}
              onMouseEnter={() => setSlashIdx(i)}
            >
              <span className="slash-icon">{c.icon}</span>
              <span className="slash-cmd">{c.cmd}</span>
              <span className="slash-desc">{c.desc}</span>
            </button>
          ))}
        </div>
      )}

      {/* Attach dropdown */}
      {showAttach && (
        <div className="input-dropdown">
          {ATTACH_MENU.map(m => (
            <button key={m.id} className="dropdown-item" onClick={() => pickAttach(m.id)}>
              <span>{m.icon}</span>
              <div>
                <div className="dropdown-label">{m.label}</div>
                <div className="dropdown-hint">{m.hint}</div>
              </div>
            </button>
          ))}
          <div className="dropdown-divider"/>
          <button className="dropdown-item disabled-item">
            <span>📸</span>
            <div>
              <div className="dropdown-label">Take screenshot</div>
              <div className="dropdown-hint">Coming soon</div>
            </div>
          </button>
        </div>
      )}

      {/* Hidden file inputs */}
      <input ref={fileInputRef} type="file"
        accept=".pdf,.pptx,.ppt,.docx,.doc,.txt,.csv,.md,.xlsx"
        style={{ display:"none" }}
        onChange={e => { if(e.target.files[0]) onUploadFile(e.target.files[0]); }} />
      <input ref={imgInputRef} type="file" accept="image/*"
        style={{ display:"none" }}
        onChange={e => { if(e.target.files[0]) onUploadImage(e.target.files[0]); }} />

      {/* Main input box */}
      <div className={`input-box-wrapper ${disabled ? "input-disabled" : ""}`}>

        {/* + button */}
        <button
          className={`plus-btn ${showAttach ? "plus-active" : ""}`}
          onClick={() => setShowAttach(v => !v)}
          title="Add file or image (Ctrl+U)"
          type="button" disabled={disabled}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>

        <textarea
          ref={textareaRef}
          className="input-textarea"
          placeholder={uploadedFile
            ? `Ask about "${uploadedFile}"… or type / for commands`
            : "Ask anything, paste a GitHub URL, or type / for commands…"}
          value={message}
          onChange={e => { setMessage(e.target.value); autoResize(); }}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />

        <button
          className={`send-btn ${message.trim() ? "send-active" : ""}`}
          onClick={onSend}
          disabled={disabled || !message.trim()}
          title="Send"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  );
}

export default InputBox;