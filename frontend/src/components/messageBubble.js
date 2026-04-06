import React from "react";
import "../Styles/chat.css";

/* ══════════════════════════════════════════
   Markdown → clean HTML
   Fixes: mixed bullet/numbered lists, nested
   items, spacing between sections
══════════════════════════════════════════ */
function parseMarkdown(text) {
  if (!text) return "";

  // 1. Extract code blocks first (protect from further processing)
  // Use a safe string placeholder instead of control characters
  const PLACEHOLDER = "CODEBLOCK_PLACEHOLDER_";
  const codeBlocks = [];
  let html = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const i = codeBlocks.length;
    codeBlocks.push(
      `<pre><code class="lang-${lang || "text"}">${escHtml(code.trim())}</code></pre>`
    );
    return `${PLACEHOLDER}${i}__`;
  });

  // 2. Escape remaining HTML
  html = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 3. Inline code
  html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  // 4. Bold / italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.+?)\*\*/g,     "<strong>$1</strong>");
  html = html.replace(/\*([^*\n]+)\*/g,      "<em>$1</em>");

  // 5. Process line by line to build proper HTML structure
  const lines  = html.split("\n");
  const output = [];
  let ulOpen   = false;
  let olOpen   = false;

  function closeUl() { if (ulOpen) { output.push("</ul>"); ulOpen = false; } }
  function closeOl() { if (olOpen) { output.push("</ol>"); olOpen = false; } }
  function closeLists() { closeUl(); closeOl(); }

  for (const rawLine of lines) {
    const line = rawLine;

    // Restore code blocks
    if (line.trim().startsWith(PLACEHOLDER) && line.trim().endsWith("__")) {
      closeLists();
      const idx = parseInt(line.trim().replace(PLACEHOLDER, "").replace("__", ""), 10);
      output.push(codeBlocks[idx]);
      continue;
    }

    // Headings
    if (/^### (.+)$/.test(line)) {
      closeLists();
      output.push(line.replace(/^### (.+)$/, "<h3>$1</h3>"));
      continue;
    }
    if (/^## (.+)$/.test(line)) {
      closeLists();
      output.push(line.replace(/^## (.+)$/, "<h2>$1</h2>"));
      continue;
    }
    if (/^# (.+)$/.test(line)) {
      closeLists();
      output.push(line.replace(/^# (.+)$/, "<h1>$1</h1>"));
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      closeLists();
      output.push("<hr/>");
      continue;
    }

    // Blockquote
    if (/^&gt; (.+)$/.test(line)) {
      closeLists();
      output.push(line.replace(/^&gt; (.+)$/, "<blockquote>$1</blockquote>"));
      continue;
    }

    // Unordered list item: *, -, or •
    const ulMatch = line.match(/^[*\-•] (.+)$/);
    if (ulMatch) {
      closeOl();
      if (!ulOpen) { output.push("<ul>"); ulOpen = true; }
      output.push(`<li>${ulMatch[1]}</li>`);
      continue;
    }

    // Ordered list item: 1. 2. etc
    const olMatch = line.match(/^(\d+)\. (.+)$/);
    if (olMatch) {
      closeUl();
      if (!olOpen) { output.push("<ol>"); olOpen = true; }
      output.push(`<li>${olMatch[2]}</li>`);
      continue;
    }

    // Empty line — close lists, add spacing
    if (line.trim() === "") {
      closeLists();
      continue; // don't add empty <p> tags
    }

    // Regular paragraph
    closeLists();
    output.push(`<p>${line}</p>`);
  }

  closeLists();

  // Restore code blocks
  let result = output.join("\n");
  codeBlocks.forEach((block, i) => {
    result = result.replace(`${PLACEHOLDER}${i}__`, block);
  });

  return result;
}

function escHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ── Source mode labels ── */
const SOURCE_INFO = {
  local_rag:   { icon: "📄", label: "Document"          },
  web_search:  { icon: "🌐", label: "Web search"        },
  hybrid:      { icon: "📄🌐", label: "Document + Web"  },
  repo:        { icon: "⬡",  label: "Repository"        },
  vision:      { icon: "👁",  label: "Image analysis"   },
  vision_web:  { icon: "👁🌐", label: "Image + Web"     },
};

/* ── Component ── */
function MessageBubble({ sender, text, loading, userName, sources, source, imagePreview }) {
  const isUser   = sender === "user";
  const initials = userName ? userName.slice(0, 2).toUpperCase() : "U";
  const srcInfo  = SOURCE_INFO[source];

  const rowContent = (
    <div className={`msg-row ${isUser ? "user-row" : "bot-row"}`}>
      <div className={`msg-avatar ${isUser ? "avatar-user" : "avatar-bot"}`}>
        {isUser ? initials : "AI"}
      </div>

      <div className="msg-content">
        <div className="msg-sender">{isUser ? (userName || "You") : "revAi"}</div>

        {imagePreview && (
          <img src={imagePreview} alt="uploaded" className="msg-image" />
        )}

        {loading ? (
          <div className="typing-dots"><span /><span /><span /></div>
        ) : isUser ? (
          <div className="msg-body"><p>{text}</p></div>
        ) : (
          <>
            <div
              className="msg-body"
              dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }}
            />

            {srcInfo && (
              <span className="source-mode-label">
                {srcInfo.icon} {srcInfo.label}
              </span>
            )}

            {sources && sources.length > 0 && (
              <div className="msg-sources">
                {sources.map((s, i) => (
                  <a
                    key={i}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-chip"
                    title={s.title}
                  >
                    <img
                      src={s.favicon} alt=""
                      className="source-favicon"
                      onError={e => { e.target.style.display = "none"; }}
                    />
                    <span className="source-domain">{s.domain}</span>
                  </a>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  // Bot rows get a full-width background stripe
  if (!isUser) {
    return <div className="bot-row-wrap">{rowContent}</div>;
  }
  return <div className="user-row-wrap">{rowContent}</div>;
}

export default MessageBubble;