import React, { useState } from 'react';
import { Drawer, Avatar, Switch } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  BgColorsOutlined,
  DesktopOutlined,
  LogoutOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import '../../styles/mobile.css';

/**
 * Profile drawer navigation items
 */
const DRAWER_ITEMS = [
  { key: 'profile', label: 'Profile Settings', icon: UserOutlined, path: '/m/settings/profile' },
  { key: 'security', label: 'Security', icon: LockOutlined, path: '/m/settings/security' },
  { key: 'theme', label: 'Theme & Appearance', icon: BgColorsOutlined, path: '/m/settings' },
];

/**
 * MobileProfileDrawer - Slide-out profile/account drawer
 * Accessed via hamburger menu or avatar in header
 */
const MobileProfileDrawer = ({ open, onClose }) => {
  const navigate = useNavigate();
  const { user, logout } = useUnifiedAuth();

  // Local state for toggles
  const [preferDesktop, setPreferDesktop] = useState(
    typeof window !== 'undefined' && localStorage.getItem('sting-prefer-desktop') === '1'
  );

  // Handle navigation
  const handleNavigate = (path) => {
    navigate(path);
    onClose();
  };

  // Handle desktop site toggle
  const handleDesktopToggle = (checked) => {
    setPreferDesktop(checked);
    if (checked) {
      localStorage.setItem('sting-prefer-desktop', '1');
      // Redirect to desktop version
      window.location.href = '/dashboard';
    } else {
      localStorage.removeItem('sting-prefer-desktop');
    }
  };

  // Handle logout
  const handleLogout = async () => {
    await logout();
    onClose();
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.name) {
      return user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return user?.email?.[0]?.toUpperCase() || '?';
  };

  return (
    <Drawer
      placement="left"
      open={open}
      onClose={onClose}
      width="80%"
      className="mobile-profile-drawer"
      styles={{ body: { padding: 0 } }}
      closable={false}
    >
      {/* User Header */}
      <div className="mobile-drawer-user-header">
        <Avatar
          src={user?.avatar}
          size={56}
          style={{ backgroundColor: 'var(--mobile-primary)' }}
        >
          {getUserInitials()}
        </Avatar>
        <div className="mobile-drawer-user-info">
          <div className="mobile-drawer-user-name">{user?.name || 'User'}</div>
          <div className="mobile-drawer-user-email">{user?.email || ''}</div>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="mobile-drawer-section">
        {DRAWER_ITEMS.map(item => (
          <button
            key={item.key}
            className="mobile-drawer-item"
            onClick={() => handleNavigate(item.path)}
          >
            <item.icon className="mobile-drawer-item-icon" />
            <span>{item.label}</span>
            <RightOutlined className="mobile-drawer-item-arrow" />
          </button>
        ))}
      </div>

      {/* Toggles */}
      <div className="mobile-drawer-section">
        <div className="mobile-drawer-toggle">
          <DesktopOutlined className="mobile-drawer-item-icon" />
          <span>View Desktop Site</span>
          <Switch
            checked={preferDesktop}
            onChange={handleDesktopToggle}
            size="small"
          />
        </div>
      </div>

      {/* Logout */}
      <div className="mobile-drawer-footer">
        <button className="mobile-drawer-logout" onClick={handleLogout}>
          <LogoutOutlined className="mobile-drawer-item-icon" />
          <span>Sign Out</span>
        </button>
      </div>
    </Drawer>
  );
};

export default MobileProfileDrawer;
