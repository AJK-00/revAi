import React, { useRef } from "react";
import "../Styles/input.css";

function InputBox({ message, setMessage, onSend, disabled }) {
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  return (
    <div className={`input-box-wrapper ${disabled ? "input-disabled" : ""}`}>
      <textarea
        ref={textareaRef}
        className="input-textarea"
        placeholder="Paste a GitHub URL or ask a question…"
        value={message}
        onChange={(e) => { setMessage(e.target.value); autoResize(); }}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={disabled}
      />
      <button
        className={`send-btn ${message.trim() ? "send-active" : ""}`}
        onClick={onSend}
        disabled={disabled || !message.trim()}
        title="Send (Enter)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
  );
}

export default InputBox;