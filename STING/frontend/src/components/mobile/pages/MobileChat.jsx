import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Spin } from 'antd';
import { SendOutlined, PlusOutlined } from '@ant-design/icons';
import { externalAiApi } from '../../../services/externalAiApi';
import { chatHistoryApi } from '../../../services/messagingApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Message types for the chat
 */
const MESSAGE_TYPES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
};

/**
 * MobileChat - Mobile chat page (Bee)
 * Full chat experience optimized for mobile with message history and real-time responses
 */
const MobileChat = () => {
  const { conversationId: urlConversationId } = useParams();
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // Check for desktop's active conversation in localStorage
  const getActiveConversationId = () => {
    if (urlConversationId) return urlConversationId;
    // Try to load same conversation as desktop
    const desktopConvId = localStorage.getItem('beeChat_conversationId');
    if (desktopConvId && desktopConvId !== 'null') {
      console.log('Found desktop conversation:', desktopConvId);
      return desktopConvId;
    }
    return null;
  };

  const [currentConversationId, setCurrentConversationId] = useState(getActiveConversationId);

  // State
  const [messages, setMessages] = useState(() => {
    // Try to load desktop messages from localStorage
    const saved = localStorage.getItem('beeChat_messages');
    const savedConvId = localStorage.getItem('beeChat_conversationId');
    if (saved && savedConvId) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          console.log('Loaded', parsed.length, 'messages from desktop localStorage');
          // Map to mobile format
          return parsed.map(msg => ({
            id: msg.id || `msg_${Date.now()}`,
            type: msg.sender === 'user' ? MESSAGE_TYPES.USER : MESSAGE_TYPES.ASSISTANT,
            content: msg.text || msg.content || '',
            timestamp: msg.timestamp || new Date().toISOString(),
          }));
        }
      } catch (e) {
        console.error('Failed to parse desktop messages:', e);
      }
    }
    return [];
  });
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [showConversations, setShowConversations] = useState(false);

  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Fetch conversation history
  const fetchConversations = useCallback(async () => {
    // Try to get user ID from different sources
    const userId = user?.id || localStorage.getItem('beeChat_userId');
    if (!userId) {
      console.log('No user ID available for fetching conversations');
      setConversations([]);
      return;
    }
    try {
      const data = await chatHistoryApi.getChatHistory(userId);
      console.log('Fetched conversations:', data?.conversations?.length || 0);
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
      // On error, show empty state - no mock data
      setConversations([]);
    }
  }, [user?.id]);

  // Fetch messages for current conversation
  const fetchMessages = useCallback(async () => {
    // If we already have messages from localStorage, use them
    if (messages.length > 0 && !urlConversationId) {
      console.log('Using messages from localStorage');
      return;
    }
    
    const convId = currentConversationId || urlConversationId;
    if (!convId || convId.startsWith('temp_')) {
      // New conversation - start with welcome message only if no existing messages
      if (messages.length === 0) {
        setMessages([
          {
            id: 'welcome',
            type: MESSAGE_TYPES.ASSISTANT,
            content: 'Hello! I\'m Bee, your AI assistant. How can I help you today?',
            timestamp: new Date().toISOString(),
          },
        ]);
      }
      return;
    }

    setLoading(true);
    try {
      const data = await chatHistoryApi.getConversationMessages(convId);
      console.log('Fetched messages for conversation:', convId, data?.messages?.length || 0);
      
      // Map messages to component format (handle different API response formats)
      const mappedMessages = (data.messages || []).map(msg => ({
        id: msg.id || msg.message_id || `msg_${Date.now()}`,
        type: msg.sender === 'user' ? MESSAGE_TYPES.USER : MESSAGE_TYPES.ASSISTANT,
        content: msg.content || msg.text || msg.message || '',
        timestamp: msg.timestamp || msg.created_at || new Date().toISOString(),
      }));
      
      setMessages(mappedMessages.length > 0 ? mappedMessages : [
        {
          id: 'welcome',
          type: MESSAGE_TYPES.ASSISTANT,
          content: 'Hello! I\'m Bee, your AI assistant. How can I help you today?',
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      // Show welcome message on error
      setMessages([
        {
          id: 'welcome',
          type: MESSAGE_TYPES.ASSISTANT,
          content: 'Hello! I\'m Bee, your AI assistant. How can I help you today?',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [currentConversationId, urlConversationId, messages.length]);

  // Initial data fetch
  useEffect(() => {
    fetchConversations();
    fetchMessages();
  }, [fetchConversations, fetchMessages]);

  // Send message handler
  const handleSendMessage = async () => {
    if (!inputValue.trim() || sending) return;

    const userMessage = {
      id: `user_${Date.now()}`,
      type: MESSAGE_TYPES.USER,
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setSending(true);

    try {
      // Use current or URL conversation ID
      const convId = currentConversationId || urlConversationId;
      
      // Call Bee chat API
      const response = await externalAiApi.beeChatUnified({
        message: userMessage.content,
        conversation_id: convId?.startsWith('temp_') ? null : convId,
        context: messages.slice(-10), // Send last 10 messages as context
        user_id: user?.id,
      });

      // Add assistant response
      const assistantMessage = {
        id: `assistant_${Date.now()}`,
        type: MESSAGE_TYPES.ASSISTANT,
        content: response.response || response.message || 'I couldn\'t generate a response. Please try again.',
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      message.error('Failed to send message');

      // Add error message
      const errorMessage = {
        id: `error_${Date.now()}`,
        type: MESSAGE_TYPES.SYSTEM,
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setSending(false);
      // Refocus input
      inputRef.current?.focus();
    }
  };

  // Handle input key press (Enter to send)
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Start new conversation
  const handleNewChat = () => {
    navigate('/m/chat');
    setMessages([
      {
        id: 'welcome',
        type: MESSAGE_TYPES.ASSISTANT,
        content: 'Hello! I\'m Bee, your AI assistant. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Select existing conversation
  const handleSelectConversation = (id) => {
    navigate(`/m/chat/${id}`);
    setShowConversations(false);
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: 'calc(100vh - 108px)', // Account for header + nav
      background: '#1a1f2e',
    }}>
      {/* Header Actions - Single row with history toggle and new chat */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'center',
        padding: '8px 0',
        gap: '8px',
      }}>
        <button
          onClick={handleNewChat}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: '#eab308',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 12px',
            color: '#1a1f2e',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <PlusOutlined />
          New Chat
        </button>
      </div>

      {/* Messages Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        WebkitOverflowScrolling: 'touch',
        padding: '0 0 16px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}>
        {messages.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '48px 16px',
            color: '#94a3b8',
          }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>🐝</div>
            <p style={{ margin: 0 }}>Start a conversation with Bee</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                maxWidth: msg.type === MESSAGE_TYPES.USER ? '85%' : '90%',
                marginLeft: msg.type === MESSAGE_TYPES.USER ? 'auto' : '0',
                marginRight: msg.type === MESSAGE_TYPES.USER ? '0' : 'auto',
                padding: '12px 16px',
                borderRadius: msg.type === MESSAGE_TYPES.USER ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                background: msg.type === MESSAGE_TYPES.USER ? '#eab308' : '#2a3142',
                color: msg.type === MESSAGE_TYPES.USER ? '#1a1f2e' : '#f1f5f9',
                fontSize: '14px',
                lineHeight: 1.5,
              }}
            >
              {msg.type === MESSAGE_TYPES.ASSISTANT && (
                <div style={{ marginBottom: '4px', fontSize: '11px', color: '#94a3b8' }}>
                  🐝 Bee
                </div>
              )}
              {msg.content}
            </div>
          ))
        )}
        {sending && (
          <div style={{
            maxWidth: '90%',
            padding: '12px 16px',
            borderRadius: '16px 16px 16px 4px',
            background: '#2a3142',
            color: '#94a3b8',
            fontSize: '14px',
          }}>
            <Spin size="small" /> Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area - Fixed at bottom of chat area */}
      <div style={{
        display: 'flex',
        gap: '8px',
        padding: '12px 0',
        borderTop: '1px solid #3a4356',
        background: '#1a1f2e',
      }}>
        <textarea
          ref={inputRef}
          placeholder="Type a message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={1}
          disabled={sending}
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: '24px',
            border: '1px solid #3a4356',
            background: '#2a3142',
            color: '#f1f5f9',
            fontSize: '14px',
            resize: 'none',
            outline: 'none',
            minHeight: '44px',
            maxHeight: '120px',
          }}
        />
        <button
          onClick={handleSendMessage}
          disabled={!inputValue.trim() || sending}
          aria-label="Send message"
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            border: 'none',
            background: !inputValue.trim() || sending ? '#3a4356' : '#eab308',
            color: !inputValue.trim() || sending ? '#64748b' : '#1a1f2e',
            cursor: !inputValue.trim() || sending ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <SendOutlined style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Conversation History Modal */}
      {showConversations && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 999,
          }}
          onClick={() => setShowConversations(false)}
        >
          <div
            style={{
              position: 'absolute',
              top: '60px',
              left: '16px',
              right: '16px',
              maxHeight: '50vh',
              background: '#1a1f2e',
              borderRadius: '12px',
              overflow: 'auto',
              border: '1px solid #3a4356',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ padding: '16px' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#f1f5f9', fontSize: '16px' }}>
                Conversation History
              </h3>
              {conversations.length === 0 ? (
                <p style={{ color: '#94a3b8', textAlign: 'center', margin: '24px 0' }}>
                  No conversations yet
                </p>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    style={{
                      padding: '12px',
                      marginBottom: '8px',
                      background: '#2a3142',
                      borderRadius: '8px',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 500, color: '#f1f5f9', marginBottom: '4px' }}>
                      {conv.title || 'Untitled Chat'}
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                      {conv.lastMessage?.slice(0, 50)}...
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                      {formatTime(conv.updatedAt)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileChat;
