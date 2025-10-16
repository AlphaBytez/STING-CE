import React, { useState, useRef, useEffect, useContext } from 'react';
import { ArrowUp, Trash, RefreshCw, AlertCircle } from 'lucide-react';
import { nanoid } from 'nanoid';

// Utility function to get user ID
const getUserId = () => {
  // In a real implementation, this would come from authentication
  // For now we'll generate a random ID or get from session storage
  let userId = sessionStorage.getItem('chat_user_id');
  if (!userId) {
    userId = `user_${nanoid(8)}`;
    sessionStorage.setItem('chat_user_id', userId);
  }
  return userId;
};

const EnhancedChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [activeTools, setActiveTools] = useState([]);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Focus on input field on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    const userId = getUserId();
    const userMessage = {
      id: Date.now(),
      sender: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);
    
    try {
      // Get API endpoint from environment or fallback to chatbot service URL
      const apiUrl = 'http://localhost:8081';
      console.log("Sending chat message to:", apiUrl);
      
      const response = await fetch(`${apiUrl}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          user_id: userId,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Track tools if they're being used
      if (data.tools_used && data.tools_used.length > 0) {
        setActiveTools(data.tools_used.map(tool => tool.name));
        
        // Add tool activity messages
        data.tools_used.forEach(tool => {
          const toolMessage = {
            id: `tool_${Date.now()}_${Math.random()}`,
            sender: 'system',
            content: `Using tool: ${tool.name}`,
            tool: tool,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, toolMessage]);
        });
      } else {
        setActiveTools([]);
      }
      
      // Check if response is an error message from fallback mode
      let content = data.response;
      let isError = false;
      
      if (content === "I apologize, but an unexpected error occurred.") {
        content = "Sorry, the chatbot service is experiencing technical difficulties. The LLM model may not be loaded. This is a known issue in the demo version. You can continue using the interface, but responses will be limited.";
        isError = true;
      }
      
      // Add bot response
      const botMessage = {
        id: `bot_${Date.now()}`,
        sender: 'assistant',
        content: content,
        isError: isError,
        filtered: data.filtered,
        filterReason: data.filter_reason,
        timestamp: data.timestamp,
      };
      
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message);
      
      // Add error message
      const errorMessage = {
        id: `error_${Date.now()}`,
        sender: 'system',
        content: `Error: ${err.message}`,
        isError: true,
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  const clearChat = async () => {
    const userId = getUserId();
    setMessages([]);
    
    try {
      // Call API to clear conversation on the server
      const apiUrl = 'http://localhost:8081';
      console.log("Clearing chat history at:", apiUrl);
      await fetch(`${apiUrl}/chat/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
        }),
      });
      
      // Add system message
      const systemMessage = {
        id: Date.now(),
        sender: 'system',
        content: 'Chat history cleared',
        timestamp: new Date().toISOString(),
      };
      
      setMessages([systemMessage]);
    } catch (err) {
      console.error('Error clearing chat:', err);
      setError(err.message);
    }
  };
  
  // Render each message with appropriate styling
  const renderMessage = (message) => {
    const isUser = message.sender === 'user';
    const isAssistant = message.sender === 'assistant';
    const isSystem = message.sender === 'system';
    
    // Base classes
    let containerClasses = 'my-2 px-3 py-2 rounded-lg max-w-[80%] ';
    let textClasses = '';
    
    // Add conditional classes based on sender
    if (isUser) {
      containerClasses += 'ml-auto bg-yellow-400 text-gray-900';
    } else if (isAssistant) {
      containerClasses += 'mr-auto bg-gray-100 text-gray-900';
      if (message.filtered) {
        containerClasses += ' border-l-4 border-yellow-500';
      }
      if (message.isError) {
        containerClasses += ' bg-orange-50 text-orange-800 border-l-4 border-orange-500';
      }
    } else if (isSystem) {
      containerClasses += 'mx-auto bg-gray-200 text-gray-700 text-sm italic max-w-[70%]';
      if (message.isError) {
        containerClasses += ' bg-red-900 text-red-300 border border-red-700';
      }
    }
    
    return (
      <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={containerClasses}>
          {message.isError && (
            <div className="flex items-center mb-1">
              <AlertCircle size={14} className="text-orange-500 mr-1" />
              <span className="font-semibold">System Note</span>
            </div>
          )}
          
          {message.tool && (
            <div className="flex items-center mb-1">
              <span className="text-xs bg-blue-900 text-blue-300 px-1 rounded mr-1">
                {message.tool.name}
              </span>
            </div>
          )}
          
          <div>{message.content}</div>
          
          {message.filtered && (
            <div className="text-xs mt-1 text-yellow-700">
              Content was filtered: {message.filterReason || 'Matched content policy'}
            </div>
          )}
          
          <div className="text-xs text-gray-500 mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };
  
  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">Bee Chat</h2>
          {isLoading && (
            <div className="text-sm text-gray-500 flex items-center">
              <RefreshCw size={14} className="animate-spin mr-1" /> 
              Working on it...
            </div>
          )}
        </div>
        <button 
          onClick={clearChat}
          className="p-2 rounded-full hover:bg-gray-100"
          title="Clear chat history"
        >
          <Trash size={18} className="text-gray-500" />
        </button>
      </div>
      
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400 italic">
            Start a conversation with Bee
          </div>
        ) : (
          messages.map(renderMessage)
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Active Tools Indicator */}
      {activeTools.length > 0 && (
        <div className="px-4 py-1 bg-blue-50 text-blue-700 text-sm flex items-center gap-2">
          <RefreshCw size={14} className="animate-spin" />
          <span>Using tools: {activeTools.join(', ')}</span>
        </div>
      )}
      
      {/* Input Area */}
      <div className="p-3 border-t">
        <div className="flex items-center gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="flex-1 border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-yellow-400 min-h-[50px] max-h-[150px] resize-none"
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !input.trim()}
            className={`p-3 rounded-full ${
              isLoading || !input.trim() 
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                : 'bg-yellow-400 text-white hover:bg-yellow-500'
            }`}
          >
            <ArrowUp size={18} />
          </button>
        </div>
        
        {error && (
          <div className="mt-2 text-sm text-red-500">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedChat;