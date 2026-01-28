import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Switch, Select } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  BellOutlined,
  BgColorsOutlined,
  InfoCircleOutlined,
  RightOutlined,
  MailOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import { useTheme, THEMES, THEME_CONFIG } from '../../theme/ThemeManager';
import apiClient from '../../../utils/apiClient';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * MobileSettings - Mobile settings hub page
 * Settings navigation optimized for mobile with Account, Preferences, and Security sections
 */
const MobileSettings = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();
  const { currentTheme, switchTheme, availableThemes, themeConfig } = useTheme();

  // State
  const [loading, setLoading] = useState(true);
  const [preferences, setPreferences] = useState({
    notificationsEnabled: true,
    emailNotifications: true,
    compactMode: false,
  });

  // Fetch user preferences
  const fetchPreferences = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/user/preferences').catch(() => ({ data: null }));
      if (response.data) {
        setPreferences({
          notificationsEnabled: response.data.notificationsEnabled ?? true,
          emailNotifications: response.data.emailNotifications ?? true,
          compactMode: response.data.compactMode ?? false,
        });
      }
    } catch (error) {
      console.error('Failed to fetch preferences:', error);
      // Use defaults on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  // Handle preference changes
  const handlePreferenceChange = async (key, value) => {
    try {
      setPreferences((prev) => ({ ...prev, [key]: value }));
      await apiClient.put('/api/user/preferences', { [key]: value });
      message.success('Preference updated');
    } catch (error) {
      console.error('Failed to update preference:', error);
      message.error('Failed to update preference');
      // Revert on error
      setPreferences((prev) => ({ ...prev, [key]: !value }));
    }
  };

  // Handle theme change
  const handleThemeChange = (theme) => {
    switchTheme(theme);
    message.success(`Theme changed to ${themeConfig[theme]?.name || theme}`);
  };

  // Settings sections configuration
  const settingsSections = [
    {
      title: 'Account',
      items: [
        {
          icon: <UserOutlined />,
          label: 'Profile Settings',
          description: 'Edit your profile information',
          onClick: () => navigate('/m/settings/profile'),
        },
        {
          icon: <InfoCircleOutlined />,
          label: 'Account Info',
          description: 'View account details',
          onClick: () => navigate('/m/settings/account'),
        },
      ],
    },
    {
      title: 'Preferences',
      items: [
        {
          icon: <BgColorsOutlined />,
          label: 'Theme',
          description: themeConfig[currentTheme]?.name || 'Modern Glass',
          onClick: () => {}, // Handled by dropdown below
          isThemeSelector: true,
        },
        {
          icon: <BellOutlined />,
          label: 'Notifications',
          description: preferences.notificationsEnabled ? 'Enabled' : 'Disabled',
          action: (
            <Switch
              size="small"
              checked={preferences.notificationsEnabled}
              onChange={(checked) => handlePreferenceChange('notificationsEnabled', checked)}
            />
          ),
        },
        {
          icon: <MailOutlined />,
          label: 'Email Notifications',
          description: 'Receive updates via email',
          action: (
            <Switch
              size="small"
              checked={preferences.emailNotifications}
              onChange={(checked) => handlePreferenceChange('emailNotifications', checked)}
              disabled={!preferences.notificationsEnabled}
            />
          ),
        },
      ],
    },
    {
      title: 'Security',
      items: [
        {
          icon: <LockOutlined />,
          label: 'Security Settings',
          description: 'Password, 2FA, sessions',
          onClick: () => navigate('/m/settings/security'),
        },
      ],
    },
  ];

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-settings-header" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
          Settings
        </h1>
        <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
          Manage your account preferences
        </p>
      </div>

      {/* Settings Sections */}
      {settingsSections.map((section, sectionIndex) => (
        <div key={section.title} className="mobile-section" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
          <h2 className="mobile-section-title">{section.title}</h2>
          <div className="mobile-card mobile-settings-card">
            {section.items.map((item, itemIndex) => (
              <div
                key={item.label}
                className={`mobile-settings-item ${itemIndex < section.items.length - 1 ? 'mobile-settings-item-border' : ''}`}
                onClick={item.onClick}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 'var(--mobile-radius-md, 8px)',
                      background: 'var(--mobile-surface)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--mobile-primary)',
                    }}
                  >
                    {item.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 2 }}>
                      {item.label}
                    </div>
                    <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                      {item.description}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)' }}>
                  {item.isThemeSelector ? (
                    <Select
                      value={currentTheme}
                      onChange={handleThemeChange}
                      style={{ width: 140, fontSize: 'var(--mobile-font-xs)' }}
                      size="small"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {Object.entries(availableThemes).map(([key, value]) => (
                        <Select.Option key={key} value={value}>
                          {themeConfig[value]?.name || key}
                        </Select.Option>
                      ))}
                    </Select>
                  ) : item.action ? (
                    item.action
                  ) : (
                    <RightOutlined style={{ color: 'var(--mobile-text-tertiary)', fontSize: 12 }} />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* App Info */}
      <div className="mobile-section">
        <h2 className="mobile-section-title">About</h2>
        <div className="mobile-card mobile-settings-card">
          <div className="mobile-settings-item" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--mobile-radius-md, 8px)',
                  background: 'var(--mobile-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--mobile-text-inverse)',
                  fontWeight: 600,
                }}
              >
                ST
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                  STING CE
                </div>
                <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                  Community Edition
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MobileSettings;
