import React, { useState } from 'react';
import './ChatInterface.css';

interface Message {
  text: string;
  isUser: boolean;
  sql?: string;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    // Add user message
    const userMessage: Message = {
      text: inputText,
      isUser: true
    };
    setMessages(prev => [...prev, userMessage]);

    // TODO: Replace with actual API call
    const response: Message = {
      text: "Based on your query, here's the SQL statement:",
      isUser: false,
      sql: "SELECT * FROM users WHERE status = 'active';"
    };

    setMessages(prev => [...prev, response]);
    setInputText('');
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.isUser ? 'user' : 'system'}`}>
            <div className="message-content">
              <p>{message.text}</p>
              {message.sql && (
                <pre className="sql-code">
                  <code>{message.sql}</code>
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Describe your SQL query in natural language..."
          className="chat-input"
        />
        <button type="submit" className="send-button">Send</button>
      </form>
    </div>
  );
};

export default ChatInterface;