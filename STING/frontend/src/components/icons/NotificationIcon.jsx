import React from 'react';
import { Bell } from 'lucide-react';
import BeeAlertIcon from './BeeAlertIcon';
import HoneycombBellIcon from './HoneycombBellIcon';
import HexagonAlertIcon from './HexagonAlertIcon';

/**
 * NotificationIcon - Wrapper component for different notification icon styles
 * Allows easy switching between different icon designs
 * 
 * @param {string} variant - Icon variant: 'bee', 'honeycomb', 'hexagon', or 'classic'
 * @param {string} className - CSS classes
 * @param {boolean} isActive - Whether the icon is in active/hover state
 * @param {boolean} hasNotifications - Whether there are unread notifications
 */
const NotificationIcon = ({ 
  variant = 'bee', 
  className = "w-5 h-5", 
  isActive = false, 
  hasNotifications = false 
}) => {
  switch (variant) {
    case 'bee':
      return (
        <BeeAlertIcon 
          className={className} 
          isActive={isActive} 
          hasNotifications={hasNotifications} 
        />
      );
    
    case 'honeycomb':
      return (
        <HoneycombBellIcon 
          className={className} 
          isActive={isActive} 
        />
      );
    
    case 'hexagon':
      return (
        <HexagonAlertIcon 
          className={className} 
          isActive={isActive} 
          hasNotifications={hasNotifications} 
        />
      );
    
    case 'classic':
    default:
      return (
        <Bell className={`${className} ${isActive ? 'text-yellow-400' : 'text-gray-400'} transition-colors`} />
      );
  }
};

export default NotificationIcon;