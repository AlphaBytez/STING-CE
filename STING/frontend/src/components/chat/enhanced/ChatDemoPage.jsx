import React from 'react';
import EnhancedChat from './EnhancedChat';

const ChatDemoPage = () => {
  return (
    <div className="container mx-auto p-4 h-screen">
      <div className="flex flex-col h-full max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">STING Bee Chat Demo</h1>
        <div className="flex-1">
          <EnhancedChat />
        </div>
      </div>
    </div>
  );
};

export default ChatDemoPage;