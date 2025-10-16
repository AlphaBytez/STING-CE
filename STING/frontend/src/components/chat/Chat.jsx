import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Trash, RefreshCw, AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react';
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

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [activeTools, setActiveTools] = useState([]);
  const [serviceStatus, setServiceStatus] = useState({
    chatbot: 'unknown', // 'available', 'unavailable', 'unknown'
    llmGateway: 'unknown'
  });
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Focus on input field on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  
  // Check service availability on load
  useEffect(() => {
    const checkServices = async () => {
      try {
        console.log('Checking LLM Gateway health...');
        const res = await fetch('/api/llm/health');
        if (res.ok) {
          console.log('LLM Gateway is available');
          setServiceStatus(prev => ({ ...prev, llmGateway: 'available' }));
        } else {
          console.log('LLM Gateway health check failed');
          setServiceStatus(prev => ({ ...prev, llmGateway: 'unavailable' }));
        }
      } catch (err) {
        console.error('Error checking LLM Gateway:', err);
        setServiceStatus(prev => ({ ...prev, llmGateway: 'unavailable' }));
      }

      try {
        console.log('Checking Chatbot service health...');
        const res = await fetch('/api/chat/health');
        if (res.ok) {
          console.log('Chatbot service is available');
          setServiceStatus(prev => ({ ...prev, chatbot: 'available' }));
        } else {
          console.log('Chatbot service health check failed');
          setServiceStatus(prev => ({ ...prev, chatbot: 'unavailable' }));
        }
      } catch (err) {
        console.error('Error checking Chatbot service:', err);
        setServiceStatus(prev => ({ ...prev, chatbot: 'unavailable' }));
      }
    };

    checkServices();
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
    
    // Check which services are available
    const useChatbot = serviceStatus.chatbot === 'available';
    const useLLMGateway = serviceStatus.llmGateway === 'available';
    
    // If either service is available, try to use it
    if (useChatbot || useLLMGateway) {
      try {
        if (useChatbot) {
          // Try the chatbot service first
          console.log('Using chatbot service');
          const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              message: input,
              user_id: userId,
            }),
          });
          
          if (response.ok) {
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
            
            // Add bot response
            const botMessage = {
              id: `bot_${Date.now()}`,
              sender: 'assistant',
              content: data.response,
              filtered: data.filtered,
              filterReason: data.filter_reason,
              timestamp: data.timestamp || new Date().toISOString(),
            };
            
            setMessages((prev) => [...prev, botMessage]);
            setIsLoading(false);
            return;
          } else {
            console.log('Chatbot service returned an error, falling back to LLM Gateway');
          }
        }
        
        if (useLLMGateway) {
          // Fall back to the LLM Gateway
          console.log('Using LLM Gateway');
          const response = await fetch('/api/llm/generate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              message: input
            }),
          });
          
          if (response.ok) {
            const data = await response.json();
            
            // Add bot response
            const botMessage = {
              id: `bot_${Date.now()}`,
              sender: 'assistant',
              content: data.response,
              filtered: data.filtered || false,
              filterReason: data.filter_reason,
              timestamp: new Date().toISOString(),
            };
            
            setMessages((prev) => [...prev, botMessage]);
            setIsLoading(false);
            return;
          } else {
            console.log('LLM Gateway returned an error');
          }
        }
        
        // If we get here, both services failed
        throw new Error('Both services failed to respond');
        
      } catch (err) {
        console.error('Error sending message:', err);
        setError(err.message);
        
        // Fall back to mock responses
        console.log('Falling back to mock responses');
      }
    }
    
    // Use mock responses if no services are available or if the API calls failed
    const mockResponses = [
      `I'm in development mode right now. The AI services aren't running, but I can pretend to answer! You asked about "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
      `This is a simulated response from Bee. The AI services aren't available currently. Your message was: "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
      `[Development Mode] Both chatbot and LLM services are offline. When running, I would provide a real answer to: "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
      `I'm sorry, the AI services are currently unavailable. This is a mock response for testing purposes. Try starting the services with ./start-chatbot.sh`
    ];
    
    // Randomly select a response
    const randomResponse = mockResponses[Math.floor(Math.random() * mockResponses.length)];
    
    // Add a slight delay to simulate processing
    setTimeout(() => {
      const mockResponse = {
        id: `bot_${Date.now()}`,
        sender: 'assistant',
        content: randomResponse,
        timestamp: new Date().toISOString(),
        isMock: true
      };
      
      setMessages((prev) => [...prev, mockResponse]);
      setIsLoading(false);
    }, 500);
    
    /* API calls removed for development - uncomment for actual API usage
    try {
      // First try the chatbot API endpoint
      const chatbotUrl = '/api/chat';
      
      try {
        const chatResponse = await fetch(chatbotUrl + '/message', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: input,
            user_id: userId,
          }),
        });
        
        if (chatResponse.ok) {
          const data = await chatResponse.json();
          
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
          
          // Add bot response
          const botMessage = {
            id: `bot_${Date.now()}`,
            sender: 'assistant',
            content: data.response,
            filtered: data.filtered,
            filterReason: data.filter_reason,
            timestamp: data.timestamp,
          };
          
          setMessages((prev) => [...prev, botMessage]);
          return; // Success, so exit early
        }
      } catch (err) {
        console.log('Chatbot API not available, falling back to LLM gateway: ', err);
        // If chatbot API fails, continue to LLM gateway fallback
      }
      
      try {
        // Fallback to the LLM gateway if chatbot API fails
        const llmUrl = '/api/llm';
        
        const response = await fetch(llmUrl + '/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: input
          }),
        });
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add bot response
        const botMessage = {
          id: `bot_${Date.now()}`,
          sender: 'assistant',
          content: data.response,
          filtered: data.filtered || false,
          filterReason: data.filter_reason,
          timestamp: new Date().toISOString(),
        };
        
        setMessages((prev) => [...prev, botMessage]);
      } catch (err) {
        console.log('LLM Gateway not available either, using mock response: ', err);
        
        // Update service status
        setServiceStatus({
          chatbot: 'unavailable',
          llmGateway: 'unavailable'
        });
        
        // Generate a more helpful mock response
        const mockResponses = [
          `I'm in development mode right now. The AI services aren't running, but I can pretend to answer! You asked about "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
          `This is a simulated response from Bee. The AI services aren't available currently. Your message was: "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
          `[Development Mode] Both chatbot and LLM services are offline. When running, I would provide a real answer to: "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`,
          `I'm sorry, the AI services are currently unavailable. This is a mock response for testing purposes. Try starting the services with ./start-chatbot.sh`
        ];
        
        // Randomly select a response
        const randomResponse = mockResponses[Math.floor(Math.random() * mockResponses.length)];
        
        const mockResponse = {
          id: `bot_${Date.now()}`,
          sender: 'assistant',
          content: randomResponse,
          timestamp: new Date().toISOString(),
          isMock: true
        };
        
        setMessages((prev) => [...prev, mockResponse]);
      }
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
    */
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
    
    // Try to clear the conversation on the server if the chatbot service is available
    if (serviceStatus.chatbot === 'available') {
      try {
        const response = await fetch('/api/chat/clear', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
          }),
        });
        
        if (!response.ok) {
          console.warn('Failed to clear chat history on server');
        }
      } catch (err) {
        console.error('Error clearing chat history on server:', err);
      }
    }
    
    // Add system message about clearing chat
    const systemMessage = {
      id: Date.now(),
      sender: 'system',
      content: 'Chat history cleared',
      timestamp: new Date().toISOString(),
    };
    
    setMessages([systemMessage]);
    
    /* API call removed for development
    try {
      // Call API to clear conversation on the server
      const chatbotUrl = '/api/chat';
      try {
        await fetch(chatbotUrl + '/clear', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
          }),
        });
      } catch (err) {
        console.log('Error clearing chat on server, but UI was cleared: ', err);
      }
      
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
    */
  };
  
  // Render each message with appropriate styling
  const renderMessage = (message) => {
    const isUser = message.sender === 'user';
    const isAssistant = message.sender === 'assistant';
    const isSystem = message.sender === 'system';
    const isMock = message.isMock === true;
    
    // Base classes
    let containerClasses = 'my-2 px-3 py-2 rounded-lg max-w-[80%] ';
    let textClasses = '';
    
    // Add conditional classes based on sender
    if (isUser) {
      containerClasses += 'ml-auto bg-yellow-400 text-gray-900';
    } else if (isAssistant) {
      if (isMock) {
        containerClasses += 'mr-auto bg-amber-50 text-amber-800 border border-amber-200';
      } else {
        containerClasses += 'mr-auto bg-gray-100 text-gray-900';
      }
      
      if (message.filtered) {
        containerClasses += ' border-l-4 border-yellow-500';
      }
    } else if (isSystem) {
      containerClasses += 'mx-auto bg-gray-700 text-gray-300 text-sm italic max-w-[70%]';
      if (message.isError) {
        containerClasses += ' bg-red-900 text-red-300 border border-red-700';
      }
    }
    
    return (
      <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={containerClasses}>
          {message.sender === 'system' && message.isError && (
            <div className="flex items-center mb-1">
              <AlertCircle size={14} className="text-red-500 mr-1" />
              <span className="font-semibold">Error</span>
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
          
          {message.isMock && (
            <div className="text-xs mt-1 text-amber-600 flex items-center">
              <AlertTriangle size={12} className="mr-1" />
              <span>Development mode (services unavailable)</span>
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
    <div className="p-6 h-full flex flex-col">
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
            
            {/* Service Status Indicators */}
            <div className="flex items-center gap-2 mt-1 text-xs">
              <div className="flex items-center" title="Chatbot Service Status">
                {serviceStatus.chatbot === 'available' ? (
                  <CheckCircle size={12} className="text-green-500 mr-1" />
                ) : serviceStatus.chatbot === 'unavailable' ? (
                  <AlertTriangle size={12} className="text-amber-500 mr-1" />
                ) : (
                  <RefreshCw size={12} className="text-gray-400 animate-spin mr-1" />
                )}
                <span className={
                  serviceStatus.chatbot === 'available' ? 'text-green-700' :
                  serviceStatus.chatbot === 'unavailable' ? 'text-amber-700' : 'text-gray-500'
                }>
                  Chatbot
                </span>
              </div>
              
              <div className="flex items-center" title="LLM Gateway Status">
                {serviceStatus.llmGateway === 'available' ? (
                  <CheckCircle size={12} className="text-green-500 mr-1" />
                ) : serviceStatus.llmGateway === 'unavailable' ? (
                  <AlertTriangle size={12} className="text-amber-500 mr-1" />
                ) : (
                  <RefreshCw size={12} className="text-gray-400 animate-spin mr-1" />
                )}
                <span className={
                  serviceStatus.llmGateway === 'available' ? 'text-green-700' :
                  serviceStatus.llmGateway === 'unavailable' ? 'text-amber-700' : 'text-gray-500'
                }>
                  LLM
                </span>
              </div>
            </div>
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
            <div className="h-full flex flex-col items-center justify-center">
              <div className="text-gray-400 italic text-center mb-2">
                Start a conversation with Bee
              </div>
              
              {/* Service status indicators for empty state */}
              {(serviceStatus.chatbot === 'unavailable' && serviceStatus.llmGateway === 'unavailable') && (
                <div className="bg-amber-50 text-amber-700 p-3 rounded-lg max-w-md text-sm">
                  <div className="flex items-center mb-1">
                    <AlertTriangle size={16} className="text-amber-500 mr-2" />
                    <span className="font-semibold">AI Services Unavailable</span>
                  </div>
                  <p>Both the Chatbot and LLM Gateway services are currently unavailable. 
                  Messages will use mock responses for testing until services are restored.</p>
                </div>
              )}
              
              {(serviceStatus.chatbot === 'unavailable' && serviceStatus.llmGateway === 'available') && (
                <div className="bg-blue-50 text-blue-700 p-3 rounded-lg max-w-md text-sm">
                  <div className="flex items-center mb-1">
                    <AlertCircle size={16} className="text-blue-500 mr-2" />
                    <span className="font-semibold">Using Backup LLM</span>
                  </div>
                  <p>The Chatbot service is unavailable, but the LLM Gateway is active. 
                  Basic chat functionality will work without conversation memory or tools.</p>
                </div>
              )}
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
    </div>
  );
};

export default Chat;