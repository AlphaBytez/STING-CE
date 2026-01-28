import React, { useState } from 'react';
import ProfileAvatar from '../common/ProfileAvatar';
import NotificationIcon from '../icons/NotificationIcon';

const Header = ({ pageTitle }) => {
  const [isHovered, setIsHovered] = useState(false);
  const hasNotifications = true; // You can connect this to actual notification state
  
  return (
    <header className="dashboard-card p-4 flex justify-between items-center mb-6">
      <h2 className="text-xl font-semibold text-white">{pageTitle}</h2>
      <div className="flex items-center gap-4">
        <button 
          className="p-2 rounded-lg hover:bg-gray-700 transition-all duration-200 relative group"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {/* Notification icon - change variant to 'bee', 'honeycomb', 'hexagon', or 'classic' */}
          <NotificationIcon 
            variant="bee"  // Try: 'bee', 'honeycomb', 'hexagon', or 'classic'
            className="w-6 h-6 text-gray-400 hover:text-yellow-400 transition-colors" 
            isActive={isHovered}
            hasNotifications={hasNotifications}
          />
          
          {/* Notification badge - enhanced with bee theme */}
          {hasNotifications && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-gradient-to-br from-amber-500 to-yellow-600 shadow-lg shadow-amber-500/50 rounded-full border border-amber-400/30 flex items-center justify-center animate-pulse">
              <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
            </span>
          )}
        </button>
        <ProfileAvatar />
      </div>
    </header>
  );
};

export default Header;