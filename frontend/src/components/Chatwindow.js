import React, { useEffect, useRef } from "react";
import MessageBubble from "./messageBubble";
import "../Styles/chat.css";

function ChatWindow({ messages, loading, userName }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="chat-window">
      {messages.map((msg, i) => (
        <MessageBubble key={i} sender={msg.sender} text={msg.text} userName={userName} />
      ))}
      {loading && <MessageBubble sender="bot" loading />}
      <div ref={bottomRef} />
    </div>
  );
}

export default ChatWindow;