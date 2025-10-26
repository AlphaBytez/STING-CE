import React from 'react';

const ChatMessage = ({ message }) => (
  <div
    className={`mb-3 flex ${
      message.sender === "User" ? "justify-end" : "justify-start"
    }`}
  >
    <div
      className={`p-3 rounded-lg max-w-xs ${
        message.sender === "User"
          ? "bg-yellow-400 text-gray-900"
          : "bg-gray-200 text-gray-800"
      }`}
    >
      <p>{message.text}</p>
      <small className="block text-xs text-gray-600">
        {message.timestamp.toLocaleTimeString()}
      </small>
    </div>
  </div>
);

export default ChatMessage;