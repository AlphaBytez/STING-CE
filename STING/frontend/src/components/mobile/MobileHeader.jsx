import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Badge, Avatar } from 'antd';
import {
  MenuOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import { useTheme } from '../theme/ThemeManager';
import MobileProfileDrawer from './MobileProfileDrawer';
import MobileNotificationSheet from './MobileNotificationSheet';
import '../../styles/mobile.css';

/**
 * Page title mapping for header display
 */
const PAGE_TITLES = {
  '/m/': 'Dashboard',
  '/m/chat': 'Bee Chat',
  '/m/basket': 'Basket',
  '/m/search': 'Search',
  '/m/reports': 'Reports',
  '/m/reports/': 'Report Detail',
  '/m/templates': 'Templates',
  '/m/templates/': 'Template Editor',
  '/m/honey-jars': 'Honey Jars',
  '/m/honey-jars/': 'Honey Jar',
  '/m/settings': 'Settings',
  '/m/settings/profile': 'Profile',
  '/m/settings/security': 'Security',
  '/m/admin': 'Admin',
  '/m/admin/pending': 'Pending Approvals',
  '/m/admin/users': 'User Management',
};

/**
 * MobileHeader - Top navigation bar
 * Contains hamburger menu, logo, page title, notifications, and avatar
 * Theme-aware: Uses CSS variables for seamless theme integration
 */
const MobileHeader = () => {
  const location = useLocation();
  const { user } = useUnifiedAuth();
  const { currentTheme } = useTheme();

  // Drawer/sheet state
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  // Get primary color based on theme (CSS variable handles this automatically)
  const getPrimaryColor = () => {
    // CSS variable will resolve to the correct theme color
    return 'var(--mobile-primary)';
  };

  // Get page title from path
  const getPageTitle = () => {
    const path = location.pathname;

    // Check for dynamic routes
    if (path.startsWith('/m/reports/') && path.split('/').length > 3) {
      return PAGE_TITLES['/m/reports/'];
    }
    if (path.startsWith('/m/templates/') && path.split('/').length > 3) {
      return PAGE_TITLES['/m/templates/'];
    }
    if (path.startsWith('/m/honey-jars/') && path.split('/').length > 3) {
      return PAGE_TITLES['/m/honey-jars/'];
    }

    // Return exact match or default
    return PAGE_TITLES[path] || '';
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.name) {
      return user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return user?.email?.[0]?.toUpperCase() || '?';
  };

  // Mock notification count (replace with actual hook)
  const unreadCount = 3;

  // DEBUG: Inline styles for iOS Safari
  const headerStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: '48px',
    background: '#1a1f2e',
    borderBottom: '1px solid #3a4356',
    display: 'flex',
    alignItems: 'center',
    paddingLeft: '8px',
    paddingRight: '8px',
    zIndex: 1000,
  };

  const buttonStyle = {
    background: 'transparent',
    border: 'none',
    color: '#f1f5f9',
    padding: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const logoStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    textDecoration: 'none',
    color: '#f1f5f9',
    fontWeight: 600,
    fontSize: '14px',
  };

  const spacerStyle = {
    flex: 1,
  };

  return (
    <header className="mobile-header" style={headerStyle}>
      {/* Left section - Hamburger menu */}
      <button
        className="mobile-header-hamburger"
        style={buttonStyle}
        onClick={() => setProfileOpen(true)}
        aria-label="Open menu"
      >
        <MenuOutlined />
      </button>

      {/* Logo and title */}
      <Link to="/m/" className="mobile-header-logo" style={logoStyle}>
        <span style={{ fontSize: 20 }}>🐝</span>
        <span>Hive</span>
      </Link>

      {/* Page title */}
      {getPageTitle() && (
        <span className="mobile-header-title" style={{ color: '#94a3b8', marginLeft: '4px', fontSize: '14px' }}>| {getPageTitle()}</span>
      )}

      {/* Spacer */}
      <div className="mobile-header-spacer" style={spacerStyle} />

      {/* Right section - Notifications and avatar */}
      <button
        className="mobile-header-notifications"
        style={buttonStyle}
        onClick={() => setNotificationsOpen(true)}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Badge
          count={unreadCount}
          size="small"
          style={{ backgroundColor: 'var(--mobile-primary)' }}
        >
          <BellOutlined />
        </Badge>
      </button>

      <button
        className="mobile-header-avatar"
        style={buttonStyle}
        onClick={() => setProfileOpen(true)}
        aria-label="Open profile"
      >
        <Avatar
          src={user?.avatar}
          size={32}
          style={{ backgroundColor: 'var(--mobile-primary)' }}
        >
          {getUserInitials()}
        </Avatar>
      </button>

      {/* Drawers and Sheets */}
      <MobileProfileDrawer
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
      />
      <MobileNotificationSheet
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
      />
    </header>
  );
};

export default MobileHeader;
