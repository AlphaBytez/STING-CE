import React, { useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  MessageOutlined,
  DatabaseOutlined,
  SearchOutlined,
  FileTextOutlined,
  SnippetsOutlined,
  AppstoreOutlined,
  SettingOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import '../../styles/mobile.css';

/**
 * Navigation items configuration
 * Icons use Ant Design (navigation convention)
 */
const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: DashboardOutlined, path: '/m/' },
  { key: 'bee', label: 'Bee', icon: MessageOutlined, path: '/m/chat' },
  { key: 'basket', label: 'Basket', icon: DatabaseOutlined, path: '/m/basket' },
  { key: 'search', label: 'Search', icon: SearchOutlined, path: '/m/search' },
  { key: 'report', label: 'Report', icon: FileTextOutlined, path: '/m/reports' },
  { key: 'templates', label: 'Templates', icon: SnippetsOutlined, path: '/m/templates' },
  { key: 'jars', label: 'Jars', icon: AppstoreOutlined, path: '/m/honey-jars' },
  { key: 'settings', label: 'Settings', icon: SettingOutlined, path: '/m/settings' },
  { key: 'admin', label: 'Admin', icon: SafetyOutlined, path: '/m/admin', adminOnly: true },
];

/**
 * MobileBottomNav - Scrollable bottom navigation bar
 * Handles horizontal scrolling for 8-9 navigation items
 */
const MobileBottomNav = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();
  const scrollRef = useRef(null);

  // Check if user is admin
  const isAdmin = user && (user.role === 'admin' || user.role === 'super_admin');

  // Filter nav items based on permissions
  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || isAdmin);

  // Check if a path is active
  const isActive = (path) => {
    if (path === '/m/') {
      return location.pathname === '/m/' || location.pathname === '/m';
    }
    return location.pathname.startsWith(path);
  };

  // Handle navigation
  const handleNavigate = (path) => {
    navigate(path);
  };

  // Inline styles for iOS Safari with safe area support
  const navStyle = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    height: 'calc(60px + env(safe-area-inset-bottom, 0px))',
    paddingBottom: 'env(safe-area-inset-bottom, 0px)',
    background: '#1a1f2e',
    borderTop: '1px solid #3a4356',
    zIndex: 1000,
    display: 'flex',
    alignItems: 'stretch',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
  };

  const scrollStyle = {
    display: 'flex',
    overflowX: 'auto',
    overflowY: 'hidden',
    width: '100%',
    height: '60px',
    WebkitOverflowScrolling: 'touch',
    paddingLeft: 'max(4px, env(safe-area-inset-left, 0px))',
    paddingRight: 'max(4px, env(safe-area-inset-right, 0px))',
    scrollbarWidth: 'none',
  };

  const getNavItemStyle = (active) => ({
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px 12px',
    minWidth: '64px',
    background: 'transparent',
    border: 'none',
    color: active ? '#eab308' : '#94a3b8',
    cursor: 'pointer',
    flexShrink: 0,
  });

  const iconStyle = {
    fontSize: '20px',
    marginBottom: '2px',
  };

  const labelStyle = {
    fontSize: '10px',
    lineHeight: 1,
  };

  return (
    <nav className="mobile-bottom-nav" style={navStyle}>
      <div
        ref={scrollRef}
        className="mobile-bottom-nav-scroll"
        style={scrollStyle}
        role="tablist"
        aria-label="Main navigation"
      >
        {visibleItems.map((item) => (
          <button
            key={item.key}
            className={`mobile-nav-item ${isActive(item.path) ? 'active' : ''}`}
            style={getNavItemStyle(isActive(item.path))}
            onClick={() => handleNavigate(item.path)}
            role="tab"
            aria-selected={isActive(item.path)}
            aria-label={item.label}
          >
            <item.icon style={iconStyle} className="mobile-nav-icon" />
            <span style={labelStyle} className="mobile-nav-label">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
};

export default MobileBottomNav;
