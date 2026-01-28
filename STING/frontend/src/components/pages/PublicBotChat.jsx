import React, { useState, useRef, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Send as SendIcon, Bot, AlertCircle, Loader } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { resilientGet, resilientPost } from '../../utils/resilientApiClient';
import { getIntelligentTimeout, clearInitCache } from '../../utils/chatServiceUtils';

const PublicBotChat = () => {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const isEmbed = searchParams.get('embed') === 'true' || window.location.pathname.includes('/embed');

  const [bot, setBot] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);
  const [loadingBot, setLoadingBot] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load bot information
  useEffect(() => {
    loadBotInfo();
  }, [slug]);

  const loadBotInfo = async () => {
    try {
      setLoadingBot(true);
      const data = await resilientGet(`/api/nectar-bots/public/${slug}`);
      setBot(data.bot);
      setError(null);

      // Add welcome message
      const welcomeMessage = {
        id: `welcome_${Date.now()}`,
        sender: 'bot',
        content: `👋 Hello! I'm **${data.bot.name}**. ${data.bot.description || 'How can I help you today?'}`,
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
    } catch (err) {
      console.error('Failed to load bot:', err);
      setError('Bot not found or unavailable');
    } finally {
      setLoadingBot(false);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Get intelligent timeout based on chatbot initialization status
      const timeout = await getIntelligentTimeout('chatbot');

      const data = await resilientPost(`/api/nectar-bots/public/${slug}/chat`, {
        message: userMessage.content,
        conversation_id: conversationId
      }, {
        timeout  // Dynamic timeout: 35s if initializing, 10s if ready
      });

      // Update conversation ID
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      // Add bot's response
      const botMessage = {
        id: `bot_${Date.now()}`,
        sender: 'bot',
        content: data.response,
        timestamp: data.timestamp || new Date().toISOString(),
        confidence_score: data.confidence_score
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);

      // Handle rate limiting
      if (error.message?.includes('429') || error.message?.includes('rate limit')) {
        setMessages(prev => [...prev, {
          id: `error_${Date.now()}`,
          sender: 'system',
          content: '⚠️ Rate limit exceeded. Please wait a moment before sending another message.',
          timestamp: new Date().toISOString(),
          isError: true
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: `error_${Date.now()}`,
          sender: 'system',
          content: '❌ Failed to send message. Please try again.',
          timestamp: new Date().toISOString(),
          isError: true
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Loading state
  if (loadingBot) {
    return (
      <div className={`flex items-center justify-center ${isEmbed ? 'h-full' : 'h-screen'} bg-gray-900`}>
        <div className="text-center">
          <Loader className="w-8 h-8 text-yellow-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-400">Loading bot...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`flex items-center justify-center ${isEmbed ? 'h-full' : 'h-screen'} bg-gray-900`}>
        <div className="text-center max-w-md p-6">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h2 className="text-xl font-semibold text-white mb-2">Bot Not Available</h2>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  // Embed mode - minimal UI
  if (isEmbed) {
    return (
      <div className="flex flex-col h-full bg-gray-900">
        {/* Minimal Header */}
        <div className="p-3 border-b border-gray-700 bg-gray-800">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-yellow-500" />
            <h3 className="text-sm font-semibold text-white">{bot.name}</h3>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`p-3 rounded-lg max-w-[80%] ${
                  message.sender === 'user'
                    ? 'bg-yellow-500 text-black'
                    : message.isError
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-700 text-white'
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]} className="text-sm">
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader className="w-4 h-4 animate-spin" />
              <span className="text-sm">Thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-3 border-t border-gray-700 bg-gray-800">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
            <button
              className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
            >
              <SendIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Full page mode
  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* Header */}
      <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-gray-800 to-gray-900">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-yellow-500/20 rounded-xl">
              <Bot className="w-8 h-8 text-yellow-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{bot.name}</h1>
              {bot.description && (
                <p className="text-gray-400 mt-1">{bot.description}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`p-4 rounded-2xl max-w-[70%] ${
                  message.sender === 'user'
                    ? 'bg-gradient-to-br from-yellow-500 to-amber-600 text-black shadow-lg'
                    : message.isError
                      ? 'bg-red-600 text-white'
                      : 'bg-gradient-to-br from-gray-700 to-gray-800 text-white shadow-lg'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold opacity-80">
                    {message.sender === 'user' ? 'You' : message.sender === 'bot' ? '🤖 Bot' : 'System'}
                  </span>
                  {message.confidence_score !== undefined && (
                    <span className="text-xs opacity-70">
                      (Confidence: {(message.confidence_score * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>

                {/* Message Content */}
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                      code: ({inline, children, ...props}) =>
                        inline ? (
                          <code className="px-1 py-0.5 bg-black/20 rounded text-sm" {...props}>
                            {children}
                          </code>
                        ) : (
                          <pre className="bg-black/20 p-3 rounded-lg overflow-x-auto">
                            <code className="text-sm" {...props}>
                              {children}
                            </code>
                          </pre>
                        ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>

                {/* Footer */}
                <div className="mt-2 pt-2 border-t border-gray-600/30 text-xs opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader className="w-5 h-5 animate-spin" />
              <p className="text-sm">Bot is thinking...</p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="p-6 border-t border-gray-700 bg-gray-800">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={1}
              disabled={isLoading}
            />
            <button
              className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-black rounded-xl flex items-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-lg transition-all"
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
            >
              <SendIcon className="w-5 h-5" />
              <span>Send</span>
            </button>
          </div>
          {conversationId && (
            <p className="text-xs text-gray-500 mt-2">
              Conversation ID: {conversationId}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PublicBotChat;
