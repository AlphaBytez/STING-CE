import React, { createContext, useContext, useState, useCallback } from 'react';
import { notification } from 'antd';

const NotificationContext = createContext();

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [api, contextHolder] = notification.useNotification();

  const showNotification = useCallback((type, message, description = null, duration = 4.5) => {
    api[type]({
      message,
      description,
      duration,
      placement: 'topRight',
      style: {
        marginTop: '70px', // Account for floating header
      },
    });
  }, [api]);

  const value = {
    showNotification,
    success: (message, description) => showNotification('success', message, description),
    error: (message, description) => showNotification('error', message, description),
    warning: (message, description) => showNotification('warning', message, description),
    info: (message, description) => showNotification('info', message, description),
  };

  return (
    <NotificationContext.Provider value={value}>
      {contextHolder}
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;