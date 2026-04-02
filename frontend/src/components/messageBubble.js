import React from "react";
import "../Styles/chat.css";

/**
 * Converts markdown text to clean HTML.
 * Handles: headings, bold, italic, code blocks, inline code,
 * bullet lists, numbered lists, blockquotes, horizontal rules, paragraphs.
 */
function parseMarkdown(text) {
  if (!text) return "";

  // 1. Protect code blocks from further processing
  const codeBlocks = [];
  let html = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="lang-${lang || "text"}">${escHtml(code.trim())}</code></pre>`);
    return `%%CODEBLOCK_${idx}%%`;
  });

  // 2. Escape HTML in remaining text (outside code blocks)
  html = html.replace(/%%CODEBLOCK_\d+%%|[&<>"]/g, (m) => {
    if (m.startsWith("%%")) return m;
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m];
  });

  // 3. Inline code
  html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  // 4. Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.+?)\*\*/g,     "<strong>$1</strong>");
  html = html.replace(/\*([^*\n]+)\*/g,      "<em>$1</em>");

  // 5. Process line by line
  const lines = html.split("\n");
  const out = [];
  let inUl = false, inOl = false;

  function closeList() {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  }

  for (const rawLine of lines) {
    const line = rawLine;

    // Restore code blocks
    if (/^%%CODEBLOCK_\d+%%$/.test(line.trim())) {
      closeList();
      const idx = parseInt(line.match(/(\d+)/)[1]);
      out.push(codeBlocks[idx]);
      continue;
    }

    // Headings
    if (/^### (.+)$/.test(line)) { closeList(); out.push(line.replace(/^### (.+)$/, "<h3>$1</h3>")); continue; }
    if (/^## (.+)$/.test(line))  { closeList(); out.push(line.replace(/^## (.+)$/, "<h2>$1</h2>")); continue; }
    if (/^# (.+)$/.test(line))   { closeList(); out.push(line.replace(/^# (.+)$/, "<h1>$1</h1>")); continue; }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) { closeList(); out.push("<hr/>"); continue; }

    // Blockquote
    if (/^&gt; (.+)$/.test(line)) {
      closeList();
      out.push(line.replace(/^&gt; (.+)$/, "<blockquote>$1</blockquote>"));
      continue;
    }

    // Unordered list
    const ulMatch = line.match(/^[\*\-] (.+)$/);
    if (ulMatch) {
      if (inOl) { out.push("</ol>"); inOl = false; }
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li>${ulMatch[1]}</li>`);
      continue;
    }

    // Ordered list
    const olMatch = line.match(/^\d+\. (.+)$/);
    if (olMatch) {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (!inOl) { out.push("<ol>"); inOl = true; }
      out.push(`<li>${olMatch[1]}</li>`);
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      closeList();
      continue;
    }

    // Regular paragraph
    closeList();
    out.push(`<p>${line}</p>`);
  }

  closeList();
  return out.join("\n");
}

function escHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── Component ──────────────────────────────────────────────────

function MessageBubble({ sender, text, loading, userName }) {
  const isUser = sender === "user";
  const initials = userName ? userName.slice(0, 2).toUpperCase() : "U";

  return (
    <div className={`msg-row ${isUser ? "user-row" : "bot-row"}`}>
      <div className={`msg-avatar ${isUser ? "avatar-user" : "avatar-bot"}`}>
        {isUser ? initials : "AI"}
      </div>
      <div className="msg-content">
        <div className="msg-sender">{isUser ? (userName || "You") : "revAi"}</div>
        {loading ? (
          <div className="typing-dots"><span /><span /><span /></div>
        ) : isUser ? (
          <div className="msg-body"><p>{text}</p></div>
        ) : (
          <div className="msg-body"
            dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }} />
        )}
      </div>
    </div>
  );
}

export default MessageBubble;