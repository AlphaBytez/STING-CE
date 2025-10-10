import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, 
  Bell, 
  Search, 
  Filter, 
  MoreVertical, 
  Check, 
  CheckCheck,
  Clock, 
  AlertTriangle,
  Info,
  Shield,
  Star,
  Trash2,
  Archive,
  Eye,
  EyeOff,
  Volume2,
  VolumeX,
  Settings
} from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';

/**
 * Bee Dances - Communication and Notifications Hub
 * The hive's communication center where bees share important information
 */
const BeeDancesPage = () => {
  const { identity } = useKratos();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [filter, setFilter] = useState('all'); // all, unread, starred, system
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [notifications, setNotifications] = useState({
    sound: true,
    desktop: true,
    email: false
  });
  
  // Auto-detect theme from document or context
  const [currentTheme, setCurrentTheme] = useState('modern');
  
  useEffect(() => {
    // Detect theme from document data attribute or class
    const theme = document.documentElement.getAttribute('data-theme') || 
                 (document.body.className.includes('retro-terminal') ? 'retro-terminal' :
                  document.body.className.includes('retro-performance') ? 'retro-performance' : 'modern');
    setCurrentTheme(theme);
    
    // Load messages
    loadMessages();
    
    // Set up real-time updates
    const interval = setInterval(loadMessages, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  const loadMessages = async () => {
    try {
      setLoading(true);
      
      // Mock data for now - will integrate with your messaging service
      const mockMessages = [
        {
          id: 'bee_dance_001',
          type: 'system',
          priority: 'high',
          title: '🛡️ Security Alert: New Login Detected',
          content: 'A new login was detected from Chrome on Windows. If this wasn\'t you, please secure your account immediately.',
          timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          read: false,
          starred: false,
          category: 'security',
          actions: [
            { type: 'secure_account', label: 'Secure Account', variant: 'danger' },
            { type: 'dismiss', label: 'This was me', variant: 'secondary' }
          ]
        },
        {
          id: 'bee_dance_002',
          type: 'system',
          priority: 'medium',
          title: '📊 Weekly Report Ready',
          content: 'Your security analytics report for this week is ready. It includes 3 new findings and 7 resolved issues.',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          read: false,
          starred: true,
          category: 'reports',
          actions: [
            { type: 'view_report', label: 'View Report', variant: 'primary' },
            { type: 'download', label: 'Download', variant: 'secondary' }
          ]
        },
        {
          id: 'bee_dance_003',
          type: 'bee_ai',
          priority: 'medium',
          title: '🐝 Bee discovered patterns in your data',
          content: 'I found some interesting patterns in your honey jar "Financial_Q4_2024". Would you like me to create a summary?',
          timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          read: true,
          starred: false,
          category: 'ai_insights',
          actions: [
            { type: 'create_summary', label: 'Create Summary', variant: 'primary' },
            { type: 'view_patterns', label: 'Show Patterns', variant: 'secondary' }
          ]
        },
        {
          id: 'bee_dance_004',
          type: 'system',
          priority: 'low',
          title: '⚡ Performance Update',
          content: 'STING performance has been optimized. Query response times improved by 23% and search accuracy increased.',
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          read: true,
          starred: false,
          category: 'system',
          actions: [
            { type: 'view_metrics', label: 'View Metrics', variant: 'secondary' }
          ]
        },
        {
          id: 'bee_dance_005',
          type: 'collaborative',
          priority: 'medium',
          title: '👥 New Honey Jar Shared',
          content: 'Sarah shared "Project_Apollo_Documents" honey jar with you. It contains 47 documents and 3 analysis reports.',
          timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
          read: false,
          starred: false,
          category: 'sharing',
          actions: [
            { type: 'view_jar', label: 'View Honey Jar', variant: 'primary' },
            { type: 'accept', label: 'Accept', variant: 'success' },
            { type: 'decline', label: 'Decline', variant: 'danger' }
          ]
        }
      ];
      
      setMessages(mockMessages);
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const getThemeClasses = () => {
    const baseClasses = {
      container: "min-h-screen p-6",
      card: "rounded-lg shadow-lg border backdrop-blur-sm",
      text: {
        primary: "text-white",
        secondary: "text-gray-300",
        muted: "text-gray-400"
      },
      button: {
        primary: "font-semibold py-2 px-4 rounded transition-colors",
        secondary: "font-medium py-1 px-3 rounded transition-colors text-sm"
      }
    };

    switch (currentTheme) {
      case 'retro-terminal':
        return {
          ...baseClasses,
          container: baseClasses.container + " bg-black font-mono",
          card: "bg-black border-2 border-green-500 rounded-none shadow-lg",
          text: {
            primary: "text-green-400",
            secondary: "text-green-300",
            muted: "text-green-600"
          },
          button: {
            primary: baseClasses.button.primary + " bg-green-600 text-black hover:bg-green-500 border border-green-500",
            secondary: baseClasses.button.secondary + " bg-transparent border border-green-500 text-green-400 hover:bg-green-900"
          },
          accent: "text-green-300",
          bg: "bg-black",
          border: "border-green-500"
        };
        
      case 'retro-performance':
        return {
          ...baseClasses,
          container: baseClasses.container + " bg-gray-900",
          card: "bg-gray-800 border border-yellow-500 rounded-lg shadow-lg",
          text: {
            primary: "text-yellow-100",
            secondary: "text-yellow-200",
            muted: "text-yellow-600"
          },
          button: {
            primary: baseClasses.button.primary + " bg-yellow-600 text-black hover:bg-yellow-500",
            secondary: baseClasses.button.secondary + " bg-transparent border border-yellow-500 text-yellow-400 hover:bg-yellow-900"
          },
          accent: "text-yellow-400",
          bg: "bg-gray-800",
          border: "border-yellow-500"
        };
        
      default: // modern
        return {
          ...baseClasses,
          container: baseClasses.container + " bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900",
          card: "sting-glass-card sting-glass-strong",
          text: {
            primary: "text-white",
            secondary: "text-gray-300",
            muted: "text-gray-400"
          },
          button: {
            primary: baseClasses.button.primary + " bg-blue-600 text-white hover:bg-blue-700",
            secondary: baseClasses.button.secondary + " bg-gray-700 text-gray-300 hover:bg-gray-600"
          },
          accent: "text-blue-400",
          bg: "bg-gray-800/50",
          border: "border-gray-600"
        };
    }
  };

  const theme = getThemeClasses();

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'high': return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'medium': return <Info className="w-4 h-4 text-yellow-400" />;
      case 'low': return <Clock className="w-4 h-4 text-gray-400" />;
      default: return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'security': return <Shield className="w-4 h-4" />;
      case 'reports': return <MessageSquare className="w-4 h-4" />;
      case 'ai_insights': return <span className="text-sm">🐝</span>;
      case 'system': return <Settings className="w-4 h-4" />;
      case 'sharing': return <span className="text-sm">👥</span>;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  const formatTime = (timestamp) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return time.toLocaleDateString();
  };

  const filteredMessages = messages.filter(message => {
    const matchesFilter = filter === 'all' || 
                         (filter === 'unread' && !message.read) ||
                         (filter === 'starred' && message.starred) ||
                         (filter === 'system' && message.type === 'system');
    
    const matchesSearch = !searchQuery || 
                         message.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         message.content.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesFilter && matchesSearch;
  });

  const unreadCount = messages.filter(m => !m.read).length;

  const handleMarkAsRead = (messageId) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, read: true } : msg
    ));
  };

  const handleToggleStar = (messageId) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, starred: !msg.starred } : msg
    ));
  };

  const handleActionClick = (action, message) => {
    console.log(`Action ${action.type} clicked for message ${message.id}`);
    
    // Handle different action types
    switch (action.type) {
      case 'secure_account':
        // Navigate to security settings
        break;
      case 'view_report':
        // Navigate to reports page
        break;
      case 'create_summary':
        // Trigger AI summary creation
        break;
      case 'view_jar':
        // Navigate to honey jar
        break;
      // Add more action handlers as needed
    }
    
    // Mark as read when action is taken
    handleMarkAsRead(message.id);
  };

  return (
    <div className={theme.container}>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className={`text-3xl ${theme.accent}`}>
            {currentTheme === 'retro-terminal' ? '▶' : '🐝'}
          </div>
          <h1 className={`text-3xl font-bold ${theme.text.primary}`}>
            {currentTheme === 'retro-terminal' ? 'COMMUNICATIONS' : 'Bee Dances'}
          </h1>
          {unreadCount > 0 && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
              currentTheme === 'retro-terminal' 
                ? 'bg-green-600 text-black' 
                : currentTheme === 'retro-performance'
                  ? 'bg-yellow-600 text-black'
                  : 'bg-blue-600 text-white'
            }`}>
              {unreadCount} new
            </span>
          )}
        </div>
        <p className={theme.text.secondary}>
          {currentTheme === 'retro-terminal' 
            ? 'SYSTEM MESSAGES AND ALERTS' 
            : 'Stay informed with important updates and insights from your hive'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className={theme.card + " p-6"}>
            {/* Search */}
            <div className="mb-6">
              <div className="relative">
                <Search className={`w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 ${theme.text.muted}`} />
                <input
                  type="text"
                  placeholder="Search messages..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full pl-10 pr-4 py-2 ${theme.bg} ${theme.border} border rounded ${theme.text.primary} placeholder-${theme.text.muted.split('-')[1]}-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                />
              </div>
            </div>

            {/* Filters */}
            <div className="space-y-2 mb-6">
              {[
                { key: 'all', label: 'All Messages', icon: MessageSquare },
                { key: 'unread', label: 'Unread', icon: Bell },
                { key: 'starred', label: 'Starred', icon: Star },
                { key: 'system', label: 'System', icon: Settings }
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded transition-colors ${
                    filter === key 
                      ? currentTheme === 'retro-terminal'
                        ? 'bg-green-900 text-green-300'
                        : currentTheme === 'retro-performance'
                          ? 'bg-yellow-900 text-yellow-300'
                          : 'bg-blue-900 text-blue-300'
                      : `${theme.text.secondary} hover:${theme.bg}`
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                  {key === 'unread' && unreadCount > 0 && (
                    <span className={`ml-auto px-2 py-1 rounded text-xs ${
                      currentTheme === 'retro-terminal' 
                        ? 'bg-green-600 text-black' 
                        : currentTheme === 'retro-performance'
                          ? 'bg-yellow-600 text-black'
                          : 'bg-blue-600 text-white'
                    }`}>
                      {unreadCount}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Settings */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded transition-colors ${theme.text.secondary} hover:${theme.bg}`}
            >
              <Settings className="w-4 h-4" />
              <span>Notification Settings</span>
            </button>

            {showSettings && (
              <div className={`mt-4 p-4 ${theme.bg} rounded border ${theme.border}`}>
                <h4 className={`font-medium mb-3 ${theme.text.primary}`}>Notifications</h4>
                <div className="space-y-3">
                  {Object.entries(notifications).map(([key, enabled]) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => setNotifications(prev => ({ ...prev, [key]: e.target.checked }))}
                        className="rounded"
                      />
                      <span className={`text-sm ${theme.text.secondary} capitalize`}>
                        {key} notifications
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Messages List */}
        <div className="lg:col-span-3">
          <div className={theme.card + " p-6"}>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${
                  currentTheme === 'retro-terminal' 
                    ? 'border-green-500' 
                    : currentTheme === 'retro-performance'
                      ? 'border-yellow-500'
                      : 'border-blue-500'
                }`}></div>
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className={`w-16 h-16 mx-auto mb-4 ${theme.text.muted}`} />
                <p className={theme.text.secondary}>
                  {searchQuery || filter !== 'all' ? 'No messages match your criteria' : 'No messages yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`p-4 rounded-lg border transition-all hover:shadow-md cursor-pointer ${
                      message.read 
                        ? `${theme.bg} ${theme.border} opacity-75` 
                        : `${theme.bg} ${
                            currentTheme === 'retro-terminal' 
                              ? 'border-green-400 shadow-green-900/20' 
                              : currentTheme === 'retro-performance'
                                ? 'border-yellow-400 shadow-yellow-900/20'
                                : 'border-blue-400 shadow-blue-900/20'
                          } shadow-lg`
                    }`}
                    onClick={() => !message.read && handleMarkAsRead(message.id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <div className="flex items-center gap-2 mt-1">
                          {getCategoryIcon(message.category)}
                          {getPriorityIcon(message.priority)}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className={`font-semibold ${theme.text.primary} ${!message.read ? 'font-bold' : ''}`}>
                              {message.title}
                            </h3>
                            {!message.read && (
                              <div className={`w-2 h-2 rounded-full ${
                                currentTheme === 'retro-terminal' 
                                  ? 'bg-green-400' 
                                  : currentTheme === 'retro-performance'
                                    ? 'bg-yellow-400'
                                    : 'bg-blue-400'
                              }`} />
                            )}
                          </div>
                          
                          <p className={`${theme.text.secondary} mb-3 line-clamp-2`}>
                            {message.content}
                          </p>
                          
                          {message.actions && message.actions.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                              {message.actions.map((action, index) => (
                                <button
                                  key={index}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleActionClick(action, message);
                                  }}
                                  className={`${
                                    action.variant === 'primary' ? theme.button.primary :
                                    action.variant === 'danger' ? 'bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-sm font-medium transition-colors' :
                                    action.variant === 'success' ? 'bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded text-sm font-medium transition-colors' :
                                    theme.button.secondary
                                  }`}
                                >
                                  {action.label}
                                </button>
                              ))}
                            </div>
                          )}
                          
                          <div className={`text-xs ${theme.text.muted}`}>
                            {formatTime(message.timestamp)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleStar(message.id);
                          }}
                          className={`p-1 rounded hover:bg-gray-700 transition-colors ${
                            message.starred ? theme.accent : theme.text.muted
                          }`}
                        >
                          <Star className={`w-4 h-4 ${message.starred ? 'fill-current' : ''}`} />
                        </button>
                        
                        <button className={`p-1 rounded hover:bg-gray-700 transition-colors ${theme.text.muted}`}>
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BeeDancesPage;