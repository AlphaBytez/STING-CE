import React from 'react';
import { Send } from 'lucide-react';

const ChatInput = ({ value, onChange, onSend }) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="mt-4 flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={onChange}
        onKeyPress={handleKeyPress}
        placeholder="Type a message..."
        className="flex-grow border rounded-lg px-3 py-2 focus:outline-none focus:border-yellow-400"
      />
      <button
        onClick={onSend}
        className="bg-amber-500 p-2 rounded-lg hover:bg-amber-600 active:bg-yellow-400 transition-colors"
      >
        <Send className="w-5 h-5" />
      </button>
    </div>
  );
};

export default ChatInput;
