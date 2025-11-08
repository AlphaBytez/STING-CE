import React, { useState, useRef, useEffect } from 'react';
import { Box, Button, TextField, Paper, Typography, Chip, CircularProgress, Alert } from '@mui/material';
import { Send as SendIcon, Psychology, Security, Analytics, Search, History, Settings } from '@mui/icons-material';
import { MessageSquare, Bot, Zap, Cpu, Paperclip, FileText, X, Plus, Trash2, ChevronDown, Database, Shield } from 'lucide-react';
import BeeIcon from '../icons/BeeIcon';
import FlowerIcon from '../icons/FlowerIcon';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkCleanMarkdown from '../../utils/remarkCleanMarkdown';
import Grains from './FloatingActionSuite';
import HoneyJarContextBar from './HoneyJarContextBar';
import './HoneyJarContextBar.css';
import MessageWithPII from './MessageWithPII';
import BeeAuthModal from './BeeAuthModal';
import { externalAiApi } from '../../services/externalAiApi';
import { chatHistoryApi } from '../../services/messagingApi';
import { systemApi } from '../../services/systemApi';
import { useLocation, useNavigate } from 'react-router-dom';
import { resilientGet } from '../../utils/resilientApiClient';
import { usePageVisibilityInterval } from '../../hooks/usePageVisibilityInterval';
import { shouldRetryOperation, getStoredOperationContext, handleReturnFromAuth } from '../../utils/tieredAuth';

// Clean markdown content from LLM responses
const cleanMarkdownContent = (content) => {
  if (!content) return '';

  let cleaned = content;

  // Remove <think> tags and their content (internal reasoning)
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/g, '');

  // Remove explanation/reasoning sections
  cleaned = cleaned.replace(/\n\s*(Explanation|Reasoning):[\s\S]*$/gm, '');

  // Remove User:/Bee: labels that model might echo
  cleaned = cleaned.replace(/^(User|Bee):\s*/gm, '');

  // Remove reference-style link definitions (e.g., [1]: url) that appear without actual links
  cleaned = cleaned.replace(/^\[\d+\]:\s*.+$/gm, '');

  // Clean up stray punctuation marks
  // Remove lines with ONLY punctuation (including periods) - but NOT inside code blocks
  cleaned = cleaned.replace(/(?!```)^\s*[,)}\]\.]+\s*$/gm, '');

  // Remove leading punctuation at start of lines (but not in code blocks)
  cleaned = cleaned.replace(/(?!```)^\s*[,)}\]\.]+\s+/gm, '');

  // Remove trailing commas/periods before newlines (like ". \n" or ", \n")
  // But preserve them in code blocks
  const lines = cleaned.split('\n');
  let inCodeBlock = false;
  cleaned = lines.map(line => {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      return line;
    }
    if (inCodeBlock) return line;
    return line.replace(/\s*[,\.]\s*$/, '');
  }).join('\n');

  // Fix orphaned closing parentheses (but NOT curly braces or square brackets)
  // Curly braces and square brackets are often valid in code
  cleaned = cleaned.replace(/\n\s*\)\s*\n/g, ') ');

  // Fix multiple blank lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  // Trim
  cleaned = cleaned.trim();

  return cleaned;
};

const BeeChat = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Load persisted data from localStorage
  const loadPersistedData = () => {
    const savedMessages = localStorage.getItem('beeChat_messages');
    const savedConversationId = localStorage.getItem('beeChat_conversationId');
    return {
      messages: savedMessages ? JSON.parse(savedMessages) : [],
      conversationId: savedConversationId || null
    };
  };

  const { messages: savedMessages, conversationId: savedConversationId } = loadPersistedData();

  // Simple Mode state - persisted to localStorage
  const [simpleMode, setSimpleMode] = useState(() => {
    const saved = localStorage.getItem('beeChat_simpleMode');
    return saved === 'true';
  });

  const [messages, setMessages] = useState(savedMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(savedConversationId);
  const [beeStatus, setBeeStatus] = useState('checking');
  const [showTools, setShowTools] = useState(false);
  const [selectedTools, setSelectedTools] = useState([]);
  const [requireAuth, setRequireAuth] = useState(false);
  const [showChatHistory, setShowChatHistory] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  // Load persisted honey jar context
  const loadPersistedHoneyJar = () => {
    const saved = localStorage.getItem('beeChat_honeyJarContext');
    return saved ? JSON.parse(saved) : null;
  };
  
  const [honeyJarContext, setHoneyJarContext] = useState(loadPersistedHoneyJar);
  const [isSearchingHoneyJars, setIsSearchingHoneyJars] = useState(false);
  const [showHoneyJarSelector, setShowHoneyJarSelector] = useState(false);
  const [honeyJars, setHoneyJars] = useState([]);

  // Bee authentication modal state
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authOperation, setAuthOperation] = useState('');
  const [authTier, setAuthTier] = useState(2);
  const [authContext, setAuthContext] = useState({});

  // PII Visual Indicator Preferences
  const [piiPreferences, setPiiPreferences] = useState({
    enabled: true,
    show_protection_badge: true,
    badge_position: 'corner',
    colors: {
      low_risk: '#2196F3',
      medium_risk: '#ff9800',
      high_risk: '#ef5350'
    },
    underline_style: 'dotted',
    underline_thickness: 2,
    tooltips: {
      enabled: true,
      show_pii_type: true,
      show_risk_level: true,
      show_protection_icon: true,
      delay_ms: 200
    }
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Persist simple mode preference
  useEffect(() => {
    console.log('🔍 BeeChat simpleMode changed:', simpleMode);
    localStorage.setItem('beeChat_simpleMode', simpleMode.toString());
  }, [simpleMode]);

  // Available tools
  const availableTools = [
    { id: 'search', name: 'Search', icon: <Search />, description: 'Search documents and data' },
    { id: 'history', name: 'Chat History', icon: <History />, description: 'View previous conversations' },
    { id: 'analytics', name: 'Analytics', icon: <Analytics />, description: 'Generate reports' },
  ];

  // Improved scroll behavior - only auto-scroll for new messages, not updates
  const prevMessagesLengthRef = useRef(messages.length);
  useEffect(() => {
    // Only auto-scroll if a new message was added (not just updated)
    if (messages.length > prevMessagesLengthRef.current) {
      // Use setTimeout to ensure DOM has updated
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 100);
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages]);

  // Persist messages and conversation ID to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('beeChat_messages', JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    if (conversationId) {
      localStorage.setItem('beeChat_conversationId', conversationId);
    }
  }, [conversationId]);

  // Persist honey jar context to localStorage
  useEffect(() => {
    if (honeyJarContext) {
      localStorage.setItem('beeChat_honeyJarContext', JSON.stringify(honeyJarContext));
    } else {
      localStorage.removeItem('beeChat_honeyJarContext');
    }
  }, [honeyJarContext]);

  // Handle honey jar context from navigation
  useEffect(() => {
    if (location.state?.honeyJarContext) {
      const context = location.state.honeyJarContext;
      setHoneyJarContext(context);
      
      // If there's an initial message, set it as input
      if (location.state.initialMessage) {
        setInput(location.state.initialMessage);
      }
      
      // Add a system message about the honey jar context
      const contextMessage = {
        id: `context_${context.id}_${Date.now()}`,
        sender: 'system',
        content: `Honey jar context loaded: "${context.name}" - ${context.description}`,
        timestamp: new Date().toISOString(),
        isAction: true
      };
      setMessages(prev => {
        // Check if this context message already exists to prevent duplicates
        const exists = prev.some(msg => msg.content === contextMessage.content && msg.sender === 'system');
        if (!exists) {
          return [...prev, contextMessage];
        }
        return prev;
      });
      
      // Clear the location state to prevent re-triggering
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Check Bee service status with page visibility optimization
  const checkBeeStatus = async () => {
    try {
      // Use resilient API call with fallback data
      const data = await resilientGet(
        '/api/bee/health',
        { status: 'degraded', message: 'Service check unavailable' },
        { timeout: 3000 }
      );
      
      setBeeStatus(data.status === 'healthy' ? 'online' : 'degraded');
    } catch (error) {
      console.warn('Bee health check failed:', error.message);
      setBeeStatus('offline');
    }
  };

  // Use page visibility aware interval - pauses when tab not active (major GPU savings)
  usePageVisibilityInterval(checkBeeStatus, 30000, []);

  // Initial status check
  useEffect(() => {
    checkBeeStatus();
  }, []);

  // Smart loading: Load system jar after authentication is established
  useEffect(() => {
    const loadSystemJarContext = async () => {
      // Only auto-load if no honey jar context is currently set
      if (honeyJarContext) return;
      
      // Check if we already tried to load system context for this session
      const sessionKey = 'beeChat_autoLoadedSystemJar';
      if (sessionStorage.getItem(sessionKey)) return;

      // Wait a moment for authentication to stabilize
      await new Promise(resolve => setTimeout(resolve, 2000));

      try {
        console.log('🍯 Auto-loading STING system jar for BeeChat context...');
        
        // Get system jar configuration
        const jarConfig = await systemApi.getSystemJarConfig();
        
        if (jarConfig.configured && jarConfig.system_jar_id) {
          // Get honey jar details
          const honeyJarDetails = await systemApi.getHoneyJarDetails(jarConfig.system_jar_id);
          
          // Set system jar as default context
          const systemContext = {
            id: honeyJarDetails.id,
            name: honeyJarDetails.name || '🛡️ STING System Knowledge',
            description: honeyJarDetails.description || 'Core STING platform knowledge and documentation',
            isSystemDefault: true
          };
          
          setHoneyJarContext(systemContext);
          
          // Add a subtle welcome message about the system context
          const welcomeMessage = {
            id: `system_welcome_${Date.now()}`,
            sender: 'system',
            content: '🐝 **Welcome to Bee Chat!** I\'m connected to the STING system knowledge base and ready to help you with STING features, security insights, and platform guidance.',
            timestamp: new Date().toISOString(),
            isAction: true
          };
          
          setMessages(prev => {
            // Only add if no messages exist (first visit)
            if (prev.length === 0) {
              return [welcomeMessage];
            }
            return prev;
          });
          
          console.log('✅ System jar auto-loaded:', systemContext.name);
        } else {
          // Set up default STING knowledge context even without configured system jar
          console.log('📚 Setting up default STING knowledge context...');
          const defaultContext = {
            id: 'default_sting_knowledge',
            name: '🛡️ STING Platform Knowledge',
            description: 'Core STING platform features, security guidance, and documentation',
            isSystemDefault: true,
            isBuiltIn: true
          };
          
          setHoneyJarContext(defaultContext);
          
          const welcomeMessage = {
            id: `default_welcome_${Date.now()}`,
            sender: 'system',
            content: '🐝 **Welcome to Bee Chat!** I\'m here to help you with STING platform features, authentication, security guidance, and general support. Ask me anything about STING!',
            timestamp: new Date().toISOString(),
            isAction: true
          };
          
          setMessages(prev => {
            if (prev.length === 0) {
              return [welcomeMessage];
            }
            return prev;
          });
          
          console.log('✅ Default STING knowledge context loaded');
        }
        
        // Mark that we attempted auto-load for this session
        sessionStorage.setItem(sessionKey, 'true');
        
      } catch (error) {
        console.error('Failed to auto-load system jar context:', error);
        // Don't block the UI if system jar loading fails
      }
    };

    loadSystemJarContext();
  }, []); // Only run once on component mount

  // Generate user ID (in production, this would come from auth)
  const getUserId = () => {
    let userId = sessionStorage.getItem('bee_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('bee_user_id', userId);
    }
    return userId;
  };

  // Handle return from authentication flow
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const beeAuthComplete = urlParams.get('bee_auth');

    if (beeAuthComplete === 'complete') {
      console.log('🔄 User returned from Bee authentication');

      // Set a marker so operations know auth is satisfied
      handleReturnFromAuth('BEE_AUTH');

      // Clean up URL
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, '', cleanUrl);

      // Show success message
      const authSuccessMessage = {
        id: `auth_success_${Date.now()}`,
        sender: 'system',
        content: '✅ Authentication successful! You can now continue.',
        timestamp: new Date().toISOString(),
        isAction: true
      };

      setMessages(prev => [...prev, authSuccessMessage]);
    }
  }, []);

  // Helper function to trigger authentication modal
  const requestAuthentication = (operation, tier = 2, context = {}) => {
    setAuthOperation(operation);
    setAuthTier(tier);
    setAuthContext(context);
    setShowAuthModal(true);
  };

  // Export this function so Bee can request authentication
  window.beeRequestAuth = requestAuthentication;

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      content: input,
      timestamp: new Date().toISOString(),
      tools: selectedTools.length > 0 ? selectedTools : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Try unified external AI endpoint first, fallback to legacy
      let data;
      try {
        data = await externalAiApi.beeChatUnified({
          message: userMessage.content,
          user_id: getUserId(),
          conversation_id: conversationId,
          tools_enabled: selectedTools,
          require_auth: requireAuth,
          encryption_required: false,
          honey_jar_id: honeyJarContext?.id || null
        });
      } catch (externalError) {
        console.warn('External AI endpoint failed, falling back to legacy:', externalError);
        // Fallback to legacy endpoint
        const response = await fetch('/api/bee/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            user_id: getUserId(),
            conversation_id: conversationId,
            tools_enabled: selectedTools,
            require_auth: requireAuth,
            encryption_required: false,
            honey_jar_id: honeyJarContext?.id || null
          }),
        });
        
        if (!response.ok) {
          throw new Error('Both external AI and legacy endpoints failed');
        }
        data = await response.json();
      }

      // Update conversation ID
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      // Add Bee's response with enhanced metadata
      const beeMessage = {
        id: `bee_${Date.now()}`,
        sender: 'bee',
        content: data.response,
        timestamp: data.timestamp,
        sentiment: data.sentiment,
        tools_used: data.tools_used,
        personality: data.bee_personality,
        encrypted: data.encrypted,
        processing_time: data.processing_time,
        isReport: data.report_generated || false,
        reportMetadata: data.report_metadata || null,
        pii_protection: data.pii_protection || null  // PII protection metadata
      };

      setMessages(prev => [...prev, beeMessage]);

      // Save both user and bee messages to chat history
      await saveChatMessage(userMessage);
      await saveChatMessage(beeMessage);

      // Clear selected tools after use
      setSelectedTools([]);
    } catch (error) {
      console.error('Error sending message:', error);

      // Try to parse error response for better messaging
      let errorMessage = 'Failed to connect to Bee. Please check if the service is running.';
      let helpUrl = null;

      if (error.response) {
        const errorData = error.response.data;

        // Handle specific error codes from backend
        if (errorData.code === 'MISSING_2FA' || errorData.code === 'SECURITY_SETUP_INCOMPLETE') {
          errorMessage = errorData.message || '🔐 Please complete your security setup (TOTP or passkey) to use Bee chat.';
          helpUrl = errorData.help_url || '/dashboard/settings/security';
        } else if (errorData.code === 'SERVICE_UNAVAILABLE' || errorData.code === 'CHAT_SERVICE_UNAVAILABLE') {
          errorMessage = errorData.message || '🐝 Bee is temporarily unavailable.';
          if (errorData.help_text) {
            errorMessage += ` ${errorData.help_text}`;
          }
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }

      setMessages(prev => [...prev, {
        id: `error_${Date.now()}`,
        sender: 'system',
        content: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true,
        helpUrl: helpUrl
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTool = (toolId) => {
    if (toolId === 'history') {
      handleChatHistory(1, false);
      return;
    }
    
    setSelectedTools(prev => 
      prev.includes(toolId) 
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };


  const formatProcessingTime = (time) => {
  // Handle undefined, null, or non-numeric values
  if (time === undefined || time === null || typeof time !== 'number') {
    return 'N/A';
  }
  
  if (time < 1) return `${Math.round(time * 1000)}ms`;
  return `${time.toFixed(1)}s`;
};

  // Floating Action Suite handlers
  const handleFileUpload = async (file) => {
    const fileMessage = {
      id: `file_${Date.now()}`,
      sender: 'user',
      content: `File uploaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
      timestamp: new Date().toISOString(),
      file: {
        name: file.name,
        size: file.size,
        type: file.type
      }
    };
    
    setMessages(prev => [...prev, fileMessage]);
    
    // Auto-send analysis request
    const analysisPrompt = `Please analyze the uploaded file "${file.name}". Provide insights on its content, structure, and any relevant findings.`;
    setInput(analysisPrompt);
    
    // You could also automatically send the message or show it as a suggested prompt
  };

  const handleCreateHoneyJar = () => {
    const honeyJarMessage = {
      id: `honeyjar_${Date.now()}`,
      sender: 'system',
      content: 'Honey Jar Creation: Navigate to Honey Jars section to create a new knowledge base, or ask me to help you organize information into a honey jar.',
      timestamp: new Date().toISOString(),
      isAction: true
    };
    
    setMessages(prev => [...prev, honeyJarMessage]);
    setInput('Help me create a new honey jar with ');
  };

  const handleSearchKnowledge = () => {
    const searchMessage = {
      id: `search_${Date.now()}`,
      sender: 'system',
      content: 'Knowledge Search: I can search across all accessible honey jars. What would you like me to find?',
      timestamp: new Date().toISOString(),
      isAction: true
    };
    
    setMessages(prev => [...prev, searchMessage]);
    setInput('Search honey jars for: ');
  };

  const handleExportChat = () => {
    const chatData = {
      conversationId,
      exportedAt: new Date().toISOString(),
      messages: messages.map(msg => ({
        ...msg,
        // Remove any sensitive data if needed
      }))
    };
    
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bee-chat-${conversationId || Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    const exportMessage = {
      id: `export_${Date.now()}`,
      sender: 'system',
      content: 'Chat exported successfully! Your conversation has been downloaded as a JSON file.',
      timestamp: new Date().toISOString(),
      isAction: true
    };
    
    setMessages(prev => [...prev, exportMessage]);
  };

  // Chat History Functions
  const handleChatHistory = async (page = 1, append = false) => {
    if (page === 1) {
      setShowChatHistory(true);
      setHistoryPage(1);
    }
    setLoadingHistory(true);
    
    try {
      // For demo purposes, use a mock user ID
      // In production, get this from authentication context
      const userId = 'current_user'; // Replace with actual user ID
      const limit = 20; // Load 20 conversations per page
      
      const historyResponse = await chatHistoryApi.getChatHistory(userId, limit, (page - 1) * limit);
      const newConversations = historyResponse.conversations || [];
      
      if (append) {
        setChatHistory(prev => [...prev, ...newConversations]);
      } else {
        setChatHistory(newConversations);
      }
      
      setHasMoreHistory(newConversations.length === limit);
      
    } catch (error) {
      console.error('Failed to load chat history:', error);
      // Fallback to mock data for demo (generate more for scrolling demo)
      const mockConversations = Array.from({ length: page === 1 ? 15 : 10 }, (_, i) => ({
        conversation_id: `demo_${page}_${i + 1}`,
        title: `Chat Session ${(page - 1) * 20 + i + 1}`,
        created_at: new Date(Date.now() - (i + (page - 1) * 20) * 86400000).toISOString(),
        last_message_at: new Date(Date.now() - (i + (page - 1) * 20) * 3600000).toISOString(),
        message_count: Math.floor(Math.random() * 50) + 5
      }));
      
      if (append) {
        setChatHistory(prev => [...prev, ...mockConversations]);
      } else {
        setChatHistory(mockConversations);
      }
      
      setHasMoreHistory(page < 3); // Demo: show "load more" for first 3 pages
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadMoreHistory = () => {
    if (!loadingHistory && hasMoreHistory) {
      const nextPage = historyPage + 1;
      setHistoryPage(nextPage);
      handleChatHistory(nextPage, true);
    }
  };

  const handleLoadConversation = async (conversationId) => {
    try {
      const response = await chatHistoryApi.getConversationMessages(conversationId);
      
      // Convert messages to the format expected by the chat component
      const loadedMessages = response.messages.map(msg => ({
        id: msg.id,
        text: msg.content,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp),
        type: msg.message_type
      }));
      
      setMessages(loadedMessages);
      setConversationId(conversationId);
      setShowChatHistory(false);
      
      // Update localStorage
      localStorage.setItem('beeChat_messages', JSON.stringify(loadedMessages));
      localStorage.setItem('beeChat_conversationId', conversationId);
      
    } catch (error) {
      console.error('Failed to load conversation:', error);
      // Show error message
      const errorMessage = {
        id: Date.now(),
        text: "Sorry, I couldn't load that conversation. Please try again.",
        sender: 'bee',
        timestamp: new Date(),
        type: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleNewConversation = () => {
    if (window.confirm('Start a new conversation? This will preserve your current chat in history.')) {
      // Clear current messages
      setMessages([]);
      // Clear conversation ID to force creation of new conversation
      setConversationId(null);
      // Clear localStorage for current conversation
      localStorage.removeItem('beeChat_messages');
      localStorage.removeItem('beeChat_conversationId');
      
      // Add a welcome message for new conversation
      const welcomeMessage = {
        id: `new_conversation_${Date.now()}`,
        sender: 'system',
        content: '🐝 **New conversation started!** How can I help you today?',
        timestamp: new Date().toISOString(),
        isAction: true
      };
      setMessages([welcomeMessage]);
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Clear current chat? This will not delete history, just clear the current view.')) {
      setMessages([]);
    }
  };

  const saveChatMessage = async (message) => {
    try {
      if (!conversationId) {
        // Create new conversation if none exists
        const userId = 'current_user'; // Replace with actual user ID
        const newConv = await chatHistoryApi.createChatConversation(userId, 'New Chat');
        setConversationId(newConv.conversation_id);
        localStorage.setItem('beeChat_conversationId', newConv.conversation_id);
      }
      
      // Save message to messaging service
      await chatHistoryApi.saveChatMessage(conversationId, {
        user_id: 'current_user', // Replace with actual user ID
        sender: message.sender,
        content: message.text,
        message_type: message.type || 'text',
        metadata: { timestamp: message.timestamp }
      });
    } catch (error) {
      console.error('Failed to save message:', error);
      // Continue without saving - don't interrupt user experience
    }
  };

  // Simple Mode Header Component
  const SimpleHeader = () => (
    <div className="sticky top-0 z-20 p-4 border-b border-gray-600 rounded-t-2xl bg-gradient-to-br from-gray-800/95 to-gray-900/95 backdrop-blur-md shadow-lg">
      <div className="flex items-center justify-between">
        {/* Left: Title + Status */}
        <div className="flex items-center gap-3">
          <BeeIcon size={24} color="rgb(251 191 36)" className="text-yellow-400" />
          <h2 className="text-lg font-semibold text-white">Bee Chat</h2>
          <span className={`px-2.5 py-1 text-xs rounded-full font-medium shadow-sm ${
            beeStatus === 'online' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
            beeStatus === 'degraded' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' :
            'bg-red-500/20 text-red-300 border border-red-500/30'
          }`}>
            {beeStatus}
          </span>
          {/* Honey Jar Context Badge */}
          {honeyJarContext && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full shadow-sm">
              <Database className="w-3 h-3 text-yellow-400" />
              <span className="text-xs text-yellow-300 font-medium">{honeyJarContext.name}</span>
            </div>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleNewConversation}
            className="px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 bg-gradient-to-br from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white shadow-md transition-all duration-200"
            title="New conversation"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New</span>
          </button>

          <button
            onClick={handleClearChat}
            className="px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-600/30 shadow-md transition-all duration-200"
            title="Clear chat"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Clear</span>
          </button>

          <button
            onClick={() => setSimpleMode(false)}
            className="px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 bg-gradient-to-br from-violet-600 to-violet-700 hover:from-violet-500 hover:to-violet-600 text-white shadow-md transition-all duration-200"
            title="Switch to advanced mode"
          >
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Advanced</span>
          </button>
        </div>
      </div>
    </div>
  );

  // Debug logging for render
  console.log('🎨 BeeChat rendering - simpleMode:', simpleMode, '- Should hide Grains:', simpleMode);

  return (
    <React.Fragment>
      {/* Unified Layout: Simple Mode (wider) or Advanced Mode (with sidebar) */}
      <div className={`flex flex-col lg:flex-row gap-4 lg:gap-6 h-[85vh] lg:h-[85vh] ${simpleMode ? 'max-w-5xl' : 'max-w-6xl'} mx-auto atmospheric-vignette`}>
        {/* Chat Area - Wider in simple mode */}
        <div className={`flex-1 min-w-0 ${simpleMode ? 'w-full' : 'lg:max-w-3xl'} chat-vignette h-full lg:h-auto`}>
          <div className="dashboard-card h-full flex flex-col overflow-hidden relative">
            {/* Conditional Header: Simple or Advanced */}
            {simpleMode ? (
              <SimpleHeader />
            ) : (
              <div className="sticky top-0 z-20 p-4 border-b border-gray-600 rounded-t-2xl bg-gradient-to-br from-gray-800/95 to-gray-900/95 backdrop-blur-md shadow-lg">
                {/* Main Header Row */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <BeeIcon size={24} color="rgb(251 191 36)" className="text-yellow-400" />
                    <h2 className="text-lg font-semibold text-white">
                      Bee Chat
                    </h2>
                    <span className={`px-2.5 py-1 text-xs rounded-full font-medium shadow-sm ${
                      beeStatus === 'online' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                      beeStatus === 'degraded' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' :
                      'bg-red-500/20 text-red-300 border border-red-500/30'
                    }`}>
                      {beeStatus}
                    </span>
                  </div>

                  {/* Primary Actions - Cleaner layout */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleNewConversation}
                      className="px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white shadow-md transition-all duration-200"
                      title="Start a new conversation"
                    >
                      <Plus className="w-4 h-4" />
                      <span className="hidden sm:inline">New</span>
                    </button>
                    <button
                      onClick={() => setShowTools(!showTools)}
                      className={`px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 shadow-md transition-all duration-200 ${
                        showTools
                          ? 'bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] hover:from-amber-400 hover:to-amber-600 text-black'
                          : 'bg-gradient-to-br from-gray-700/90 to-gray-800/90 hover:from-gray-600/90 hover:to-gray-700/90 text-gray-200'
                      }`}
                      title="Toggle tools"
                    >
                      <Psychology className="w-4 h-4" />
                      <span className="hidden sm:inline">Tools</span>
                    </button>
                    <button
                      onClick={() => setSimpleMode(true)}
                      className="px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-2 bg-gradient-to-br from-gray-600 to-gray-700 hover:from-gray-500 hover:to-gray-600 text-white shadow-md transition-all duration-200"
                      title="Switch to simple mode"
                    >
                      <MessageSquare className="w-4 h-4" />
                      <span className="hidden sm:inline">Simple</span>
                    </button>
                  </div>
                </div>

                {/* Secondary Actions Row - Collapsible */}
                {showTools && (
                  <div className="flex items-center gap-2 flex-wrap animate-fade-in">
                    {availableTools.map(tool => (
                      <button
                        key={tool.id}
                        onClick={() => toggleTool(tool.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 shadow-sm transition-all duration-200 ${
                          tool.id === 'history'
                            ? 'bg-gradient-to-br from-orange-600 to-orange-700 hover:from-orange-500 hover:to-orange-600 text-white'
                            : selectedTools.includes(tool.id)
                              ? 'bg-gradient-to-br from-yellow-500 to-amber-600 hover:from-yellow-600 hover:to-amber-700 text-black'
                              : 'bg-gray-700/60 hover:bg-gray-600/60 text-gray-300'
                        }`}
                        title={tool.description}
                      >
                        {tool.icon}
                        {tool.name}
                      </button>
                    ))}
                    <button
                      onClick={handleClearChat}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-600/30 shadow-sm transition-all duration-200"
                      title="Clear current chat view"
                    >
                      <Trash2 className="w-3 h-3" />
                      Clear
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 pt-0 scroll-smooth">
        {messages.length === 0 ? (
          <div className="text-center mt-8">
            <p className="text-gray-400">
              Start a conversation with Bee! I can help with searches, analytics, and more.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex bee-message ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`p-4 max-w-[65%] rounded-2xl ${
                    message.sender === 'user'
                      ? 'bg-gradient-to-br from-yellow-500/90 to-amber-600/90 backdrop-blur-md border-2 border-yellow-400/50 text-white shadow-lg shadow-yellow-500/30'
                      : message.isError
                        ? 'bg-red-600 text-white'
                        : 'bg-gradient-to-br from-emerald-600/90 to-teal-700/90 backdrop-blur-md text-white border-2 border-emerald-400/70 shadow-lg shadow-emerald-400/30'
                  }`}
                >
                  {/* Message Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-bold opacity-80">
                      {message.sender === 'user' ? 'You' : message.sender === 'bee' ? '🐝 Bee' : 'System'}
                    </span>
                    {/* Removed sentiment and personality tags for cleaner UI */}
                    {message.encrypted && (
                      <span className="px-2 py-1 text-xs bg-green-600 text-white rounded-full flex items-center gap-1">
                        <Security className="w-3 h-3" />
                        Encrypted
                      </span>
                    )}
                    {message.isReport && (
                      <span className="px-2 py-1 text-xs bg-amber-600 text-white rounded-full flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        Report Generated
                      </span>
                    )}
                  </div>

                  {/* Message Content */}
                  {message.sender === 'user' ? (
                    <p className="text-sm whitespace-pre-wrap">
                      {message.content}
                    </p>
                  ) : (
                    <div className="text-sm prose prose-invert max-w-none">
                      {message.pii_protection ? (
                        /* Render with PII visual indicators */
                        <MessageWithPII
                          message={message.content}
                          piiProtection={message.pii_protection}
                          preferences={piiPreferences}
                          showBadge={true}
                        />
                      ) : (
                        /* Fallback to standard markdown rendering */
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkCleanMarkdown]}
                          components={{
                          // Custom components for better styling
                          p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                          code: ({inline, children, ...props}) =>
                            inline ? (
                              <code className="px-2 py-1 bg-gray-700 rounded text-yellow-400 text-xs font-mono whitespace-nowrap" {...props}>
                                {children}
                              </code>
                            ) : (
                              <pre className="bg-gray-800 p-4 rounded-lg overflow-x-auto my-3 border border-gray-700">
                                <code className="text-sm text-gray-300 font-mono whitespace-pre block" {...props}>
                                  {children}
                                </code>
                              </pre>
                            ),
                          ul: ({children}) => <ul className="list-disc ml-4 space-y-1 my-2">{children}</ul>,
                          ol: ({children}) => <ol className="list-decimal ml-4 space-y-1 my-2">{children}</ol>,
                          li: ({children}) => <li className="text-sm leading-relaxed">{children}</li>,
                          a: ({href, children}) => {
                            // Handle broken reference links (href is undefined or empty)
                            if (!href || href === '') {
                              // Just render as plain text with slight emphasis
                              return <span className="text-gray-300">{children}</span>;
                            }
                            return (
                              <a href={href} target="_blank" rel="noopener noreferrer"
                                 className="text-yellow-400 hover:text-yellow-300 underline">
                                {children}
                              </a>
                            );
                          },
                          h1: ({children}) => <h1 className="text-xl font-bold mb-2">{children}</h1>,
                          h2: ({children}) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
                          h3: ({children}) => <h3 className="text-base font-bold mb-1">{children}</h3>,
                          blockquote: ({children}) => (
                            <blockquote className="border-l-4 border-yellow-500 pl-3 italic text-gray-300">
                              {children}
                            </blockquote>
                          ),
                          table: ({children}) => (
                            <div className="overflow-x-auto">
                              <table className="min-w-full divide-y divide-gray-600">
                                {children}
                              </table>
                            </div>
                          ),
                          th: ({children}) => (
                            <th className="px-3 py-2 bg-gray-700 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                              {children}
                            </th>
                          ),
                          td: ({children}) => (
                            <td className="px-3 py-2 text-sm text-gray-300 border-t border-gray-600">
                              {children}
                            </td>
                          )
                          }}
                        >
                          {cleanMarkdownContent(message.content)}
                        </ReactMarkdown>
                      )}
                    </div>
                  )}

                  {/* Error Help Link */}
                  {message.isError && message.helpUrl && (
                    <div className="mt-3 pt-3 border-t border-red-600/30">
                      <a
                        href={message.helpUrl}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        <Shield className="w-4 h-4" />
                        Complete Security Setup
                      </a>
                    </div>
                  )}

                  {/* Tools Used */}
                  {message.tools_used && message.tools_used.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs opacity-70 mb-1">
                        Tools used:
                      </p>
                      <div className="flex gap-1 flex-wrap">
                        {message.tools_used.map((tool, index) => (
                          <span
                            key={index}
                            className={`px-2 py-1 text-xs rounded-full ${
                              tool.status === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                            }`}
                          >
                            {tool.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Requested Tools */}
                  {message.tools && message.tools.length > 0 && (
                    <div className="mt-1">
                      <p className="text-xs opacity-70">
                        Using: {message.tools.join(', ')}
                      </p>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex justify-between items-center mt-2 pt-2 border-t border-gray-600 border-opacity-30">
                    <span className="text-xs opacity-70">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                    {message.processing_time && (
                      <span className="text-xs opacity-70">
                        {formatProcessingTime(message.processing_time)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-yellow-500"></div>
                <p className="text-sm text-gray-400">
                  Bee is thinking...
                </p>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
              )}
            </div>

            {/* Honey Jar Context Bar */}
            <div className="sticky bottom-0 z-20">
              <HoneyJarContextBar 
                currentHoneyJar={honeyJarContext}
                onHoneyJarChange={setHoneyJarContext}
                onSearchStateChange={setIsSearchingHoneyJars}
              />
              
              {/* Sticky Input - Hidden when searching honey jars */}
              {!isSearchingHoneyJars && (
                <div className="p-3 sm:p-4 border-t border-gray-600 rounded-b-2xl bg-gray-800/98 backdrop-blur-md">
        {conversationId && (
          <p className="text-xs text-gray-400 mb-2 truncate">
            Conversation: {conversationId}
          </p>
        )}
        <div className="flex flex-col sm:flex-row gap-2">
          <textarea
            ref={inputRef}
            className="flex-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            rows={1}
            disabled={isLoading || beeStatus === 'offline'}
          />
          <button
            className="floating-button bg-yellow-500 hover:bg-yellow-600 text-black px-3 sm:px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed min-w-[80px] sm:min-w-0"
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading || beeStatus === 'offline'}
          >
            <SendIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </div>
              {beeStatus === 'offline' && (
                <div className="mt-2 p-3 bg-red-600 text-white rounded-lg text-sm">
                  Bee is currently offline. Please try again later.
                </div>
              )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Grains Sidebar (Right on desktop) - Hidden in Simple Mode */}
        {(() => {
          console.log('🔍 Desktop Grains conditional: !simpleMode =', !simpleMode, '(simpleMode =', simpleMode, ')');
          return !simpleMode && (
            <div className="hidden lg:block w-80">
              <Grains
                isSidebar={true}
                onFileUpload={handleFileUpload}
                onCreateHoneyJar={handleCreateHoneyJar}
                onSearchKnowledge={handleSearchKnowledge}
                onExportChat={handleExportChat}
                honeyJarContext={honeyJarContext}
                onHoneyJarChange={setHoneyJarContext}
              />
            </div>
          );
        })()}

        {/* Mobile/Tablet Grains - Horizontal bar at bottom - Hidden in Simple Mode */}
        {!simpleMode && (
          <div className="lg:hidden fixed bottom-20 left-0 right-0 z-30 px-4">
            <div className="bg-gray-800/95 backdrop-blur-md rounded-t-2xl shadow-xl border border-gray-600 p-2">
              <Grains
                isSidebar={false}
                isMobile={true}
                onFileUpload={handleFileUpload}
                onCreateHoneyJar={handleCreateHoneyJar}
                onSearchKnowledge={handleSearchKnowledge}
                onExportChat={handleExportChat}
                honeyJarContext={honeyJarContext}
                onHoneyJarChange={setHoneyJarContext}
              />
            </div>
          </div>
        )}
      </div>

      {/* Chat History Modal */}
      {showChatHistory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="backdrop-blur-md bg-gray-800/95 border border-gray-600 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-600">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                  <History className="w-5 h-5 text-yellow-400" />
                  Chat History
                </h3>
                <button
                  onClick={() => setShowChatHistory(false)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[60vh] custom-scrollbar">
              {loadingHistory && historyPage === 1 ? (
                <div className="flex items-center justify-center py-8">
                  <CircularProgress size={24} className="text-yellow-400" />
                  <span className="ml-2 text-gray-300">Loading chat history...</span>
                </div>
              ) : chatHistory.length > 0 ? (
                <div className="space-y-3">
                  {chatHistory.map((conversation, index) => (
                    <div
                      key={conversation.conversation_id}
                      onClick={() => handleLoadConversation(conversation.conversation_id)}
                      className="backdrop-blur-md bg-gray-700/50 border border-gray-600 rounded-xl p-4 hover:bg-gray-600/50 cursor-pointer transition-all duration-200 animate-fade-in-up"
                      style={{ animationDelay: `${(index % 20) * 0.05}s` }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-white mb-1">
                            {conversation.title}
                          </h4>
                          <div className="flex items-center gap-4 text-sm text-gray-400">
                            <span>{conversation.message_count} messages</span>
                            <span>•</span>
                            <span>{new Date(conversation.last_message_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(conversation.created_at).toLocaleDateString()}
                        </div>
                      </div>
          1          </div>
                  ))}
                  
                  {/* Load More Button */}
                  {hasMoreHistory && (
                    <div className="pt-4 border-t border-gray-600 mt-4">
                      <button
                        onClick={loadMoreHistory}
                        disabled={loadingHistory}
                        className="w-full px-4 py-3 backdrop-blur-md bg-gray-600/50 border border-gray-500 text-gray-200 rounded-xl hover:bg-gray-500/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        {loadingHistory ? (
                          <>
                            <CircularProgress size={16} className="text-gray-400" />
                            Loading more...
                          </>
                        ) : (
                          <>
                            <History className="w-4 h-4" />
                            Load More Conversations
                          </>
                        )}
                      </button>
                    </div>
                  )}
                  
                  {/* Scroll Indicator */}
                  {chatHistory.length > 5 && (
                    <div className="text-center text-xs text-gray-500 pt-2">
                      {chatHistory.length} conversations loaded
                      {hasMoreHistory && ' • Scroll or click "Load More" for older chats'}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <History className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                  <p className="text-gray-400 mb-2">No chat history found</p>
                  <p className="text-sm text-gray-500">Start a conversation to see it here!</p>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t border-gray-600 bg-gray-800/50">
              <button
                onClick={() => setShowChatHistory(false)}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded-xl hover:bg-gray-500 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bee Authentication Modal */}
      <BeeAuthModal
        open={showAuthModal}
        operation={authOperation}
        tier={authTier}
        context={authContext}
        onCancel={() => setShowAuthModal(false)}
      />
    </React.Fragment>
  );
};

export default BeeChat;