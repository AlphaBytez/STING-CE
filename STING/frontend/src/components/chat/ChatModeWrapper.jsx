import React from 'react';
import BeeChat from './BeeChat';
// SimpleBeeChat removed - BeeChat now has built-in simple mode
// ChatModeSelector removed - BeeChat has built-in toggle buttons

const ChatModeWrapper = () => {
  // ChatModeWrapper is now just a simple wrapper
  // BeeChat manages its own simple/advanced mode internally
  return (
    <div className="h-full atmospheric-vignette p-4">
      <div className="max-w-7xl mx-auto h-full flex flex-col">
        {/* BeeChat handles both simple and advanced modes internally */}
        {/* Mode toggle buttons are in BeeChat's header */}
        <BeeChat isEmbedded={true} />
      </div>
    </div>
  );
};

export default ChatModeWrapper;