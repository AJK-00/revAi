import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {

  const [repoUrl, setRepoUrl] = useState("");
  const [chatId] = useState(Date.now().toString());
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);

  const sendMessage = async () => {

    if (!message) return;

    const userMessage = { sender: "user", text: message };
    setMessages(prev => [...prev, userMessage]);

    try {

      const response = await axios.post(
        "http://127.0.0.1:8000/chat",
        {
          chat_id: chatId,
          repo_url: repoUrl,
          message: message
        }
      );

      const botMessage = {
        sender: "bot",
        text: response.data.response
      };

      setMessages(prev => [...prev, botMessage]);

    } catch (error) {

      console.error("API Error:", error);

      setMessages(prev => [
        ...prev,
        { sender: "bot", text: "Backend error occurred." }
      ]);
    }

    setMessage("");
  };

  return (
    <div className="container">

      <h2>revAi Workspace</h2>

      <input
        type="text"
        placeholder="Enter GitHub Repo URL"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
      />

      <div className="chat-window">

        {messages.map((msg, index) => (
          <div key={index} className={msg.sender}>
            {msg.text}
          </div>
        ))}

      </div>

      <div className="input-area">

        <input
          type="text"
          placeholder="Ask something..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />

        <button onClick={sendMessage}>Send</button>

      </div>

    </div>
  );
}

export default App;