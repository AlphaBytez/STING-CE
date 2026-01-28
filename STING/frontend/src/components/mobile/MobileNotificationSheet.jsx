import React, { useState, useEffect } from 'react';
import { Drawer, Badge } from 'antd';
import { BellOutlined, CheckCircleOutlined } from '@ant-design/icons';
import apiClient from '../../utils/apiClient';
import '../../styles/mobile.css';

/**
 * MobileNotificationSheet - Bottom sheet notification panel
 * Accessed via bell icon in header
 */
const MobileNotificationSheet = ({ open, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch notifications
  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open]);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/notifications');
      setNotifications(response.data || []);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
      // Use mock data for development
      setNotifications([
        {
          id: '1',
          title: 'Welcome to STING',
          message: 'Your account has been set up successfully.',
          timeAgo: 'Just now',
          read: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Mark notification as read
  const handleMarkAsRead = async (notificationId) => {
    try {
      await apiClient.patch(`/api/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n => (n.id === notificationId ? { ...n, read: true } : n))
      );
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  // Mark all as read
  const handleMarkAllAsRead = async () => {
    try {
      await apiClient.post('/api/notifications/mark-all-read');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  // Get unread count
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <Drawer
      placement="bottom"
      open={open}
      onClose={onClose}
      height="70%"
      className="mobile-notification-sheet"
      styles={{ body: { padding: 0 } }}
      closable={false}
      headerStyle={{ display: 'none' }}
    >
      {/* Handle bar */}
      <div className="mobile-sheet-handle">
        <div className="mobile-sheet-handle-bar" />
      </div>

      {/* Header */}
      <div className="mobile-sheet-header">
        <h3>
          Notifications
          {unreadCount > 0 && (
            <Badge
              count={unreadCount}
              style={{ marginLeft: 8, backgroundColor: 'var(--mobile-primary)' }}
              size="small"
            />
          )}
        </h3>
        {unreadCount > 0 && (
          <button onClick={handleMarkAllAsRead}>
            Mark all read
          </button>
        )}
      </div>

      {/* Notification List */}
      <div className="mobile-notification-list">
        {notifications.length === 0 ? (
          <div className="mobile-notification-empty">
            <BellOutlined className="mobile-notification-empty-icon" />
            <p>No notifications</p>
          </div>
        ) : (
          notifications.map(notification => (
            <button
              key={notification.id}
              className={`mobile-notification-item ${notification.read ? '' : 'unread'}`}
              onClick={() => handleMarkAsRead(notification.id)}
            >
              <div className="mobile-notification-content">
                <div className="mobile-notification-title">{notification.title}</div>
                {notification.message && (
                  <div className="mobile-notification-body">{notification.message}</div>
                )}
                <div className="mobile-notification-time">
                  {notification.timeAgo || notification.createdAt || 'Recently'}
                </div>
              </div>
              {!notification.read && (
                <div className="mobile-notification-dot" title="Unread" />
              )}
              {notification.read && (
                <CheckCircleOutlined
                  style={{ color: 'var(--mobile-text-tertiary)', fontSize: 12 }}
                />
              )}
            </button>
          ))
        )}
      </div>
    </Drawer>
  );
};

export default MobileNotificationSheet;
