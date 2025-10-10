import React, { useState } from 'react';
import { X, Bell, MessageSquare, AlertTriangle, CheckCircle, Info, Clock } from 'lucide-react';
import BeeAlertIcon from '../icons/BeeAlertIcon';

/**
 * NotificationDropdown - Demo notification system
 * Shows mock notifications for the open source demo version
 */
const NotificationDropdown = ({ isOpen, onClose, notificationCount = 5, onClearAll }) => {
  // Track read/unread state for demo
  const [notifications, setNotifications] = useState([
    {
      id: 1,
      type: 'info',
      title: 'Welcome to STING!',
      message: 'Your secure AI platform is ready. Start by uploading documents to create your first Honey Jar.',
      time: '2 minutes ago',
      unread: true
    },
    {
      id: 2,
      type: 'success',
      title: 'Bee Chat Enhanced',
      message: 'Your Bee assistant now has access to improved knowledge retrieval capabilities.',
      time: '1 hour ago',
      unread: true
    },
    {
      id: 3,
      type: 'feature',
      title: 'New Grains Available',
      message: 'Check out the updated Action Grains in your Bee Chat sidebar for enhanced workflow.',
      time: '3 hours ago',
      unread: false
    },
    {
      id: 4,
      type: 'warning',
      title: 'Storage Optimization',
      message: 'Consider archiving older documents to optimize your knowledge base performance.',
      time: '1 day ago',
      unread: true
    },
    {
      id: 5,
      type: 'system',
      title: 'System Update',
      message: 'STING platform updated with improved security and glass morphism UI enhancements.',
      time: '2 days ago',
      unread: false
    }
  ]);
  
  // Handle marking all as read
  const handleMarkAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, unread: false })));
    if (onClearAll) {
      onClearAll(); // Clear the count in parent
    }
  };
  
  // Handle clicking individual notification
  const handleNotificationClick = (id) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, unread: false } : n
    ));
    
    // Update parent count
    const unreadCount = notifications.filter(n => n.id !== id && n.unread).length;
    if (onClearAll && unreadCount === 0) {
      onClearAll();
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'feature': return <MessageSquare className="w-4 h-4 text-blue-400" />;
      case 'system': return <Clock className="w-4 h-4 text-purple-400" />;
      default: return <Info className="w-4 h-4 text-gray-400" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="absolute top-full right-0 mt-2 w-96 max-w-sm md:max-w-md z-50">
      {/* Glass morphism floating card */}
      <div className="floating-card bg-gradient-to-br from-gray-800/90 via-gray-900/80 to-black/70 backdrop-blur-2xl rounded-2xl border border-white/20 shadow-2xl shadow-black/50 max-h-96 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <BeeAlertIcon className="w-5 h-5 text-yellow-400" isActive={true} hasNotifications={true} />
            <h3 className="font-semibold text-white">Hive Alerts</h3>
            <span className="px-2 py-0.5 bg-gradient-to-br from-amber-500 to-yellow-600 shadow-sm shadow-amber-500/50 text-white text-xs rounded-full border border-amber-400/30">
              {notificationCount}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white transition-colors duration-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Notifications list */}
        <div className="max-h-80 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-600/50 hover:scrollbar-thumb-gray-500/60 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-600/50 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-500/60">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              onClick={() => handleNotificationClick(notification.id)}
              className={`px-4 py-3 border-b border-white/10 hover:bg-gradient-to-r hover:from-white/10 hover:to-transparent transition-all duration-200 cursor-pointer ${
                notification.unread ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/10' : ''
              }`}
            >
              <div className="flex items-start gap-2">
                {/* Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getNotificationIcon(notification.type)}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between">
                    <h4 className={`text-sm font-medium ${
                      notification.unread ? 'text-white' : 'text-gray-200'
                    }`}>
                      {notification.title}
                    </h4>
                    {notification.unread && (
                      <div className="w-2.5 h-2.5 bg-gradient-to-br from-blue-400 to-purple-500 shadow-lg shadow-blue-500/50 rounded-full flex-shrink-0 mt-0.5 border border-blue-300/50 animate-pulse"></div>
                    )}
                  </div>
                  <p className="text-xs text-gray-300 mt-0.5 leading-snug line-clamp-2">
                    {notification.message}
                  </p>
                  <span className="text-xs text-gray-400 mt-1 block">
                    {notification.time}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-white/10 bg-gradient-to-r from-gray-900/50 to-black/30">
          <div className="flex justify-between items-center text-xs">
            <button 
              onClick={handleMarkAllAsRead}
              className="floating-button px-3 py-1.5 bg-gradient-to-r from-blue-600/80 to-blue-700/80 hover:from-blue-500/80 hover:to-blue-600/80 text-white rounded-lg transition-all duration-200"
            >
              Mark all as read
            </button>
            <button className="text-gray-400 hover:text-white transition-colors duration-200 font-medium">
              View all notifications
            </button>
          </div>
        </div>

        {/* Demo notice with controls */}
        <div className="p-3 bg-gradient-to-r from-black/30 to-gray-900/30 border-t border-white/5">
          <div className="flex flex-col gap-2">
            <p className="text-xs text-gray-400 text-center font-medium">
              📝 Demo notifications - Connect your notification system here
            </p>
            <div className="flex justify-center gap-2">
              <button
                onClick={handleMarkAllAsRead}
                className="floating-button px-3 py-1.5 text-xs bg-gradient-to-r from-amber-600/30 to-yellow-600/30 hover:from-amber-500/40 hover:to-yellow-500/40 text-amber-300 rounded-lg transition-all duration-200 border border-amber-500/20"
              >
                Clear All
              </button>
              <button
                onClick={() => {
                  // Reset demo notifications
                  setNotifications(notifications.map(n => ({ ...n, unread: true })));
                }}
                className="floating-button px-3 py-1.5 text-xs bg-gradient-to-r from-gray-700/30 to-gray-800/30 hover:from-gray-600/40 hover:to-gray-700/40 text-gray-300 rounded-lg transition-all duration-200 border border-gray-600/20"
              >
                Reset Demo
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationDropdown;