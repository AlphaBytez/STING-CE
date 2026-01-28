import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Modal, Button, Input, List, Tag, Popconfirm, Switch } from 'antd';
import {
  LockOutlined,
  SafetyCertificateOutlined,
  MobileOutlined,
  DesktopOutlined,
  LogoutOutlined,
  ArrowLeftOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import apiClient from '../../../utils/apiClient';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * MobileSecurity - Mobile security settings page
 * Security options optimized for mobile including password, 2FA, and session management
 */
const MobileSecurity = () => {
  const navigate = useNavigate();
  const { user, logout } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordErrors, setPasswordErrors] = useState({});

  // Fetch security data
  const fetchSecurityData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch 2FA status
      const [twoFactorRes, sessionsRes] = await Promise.all([
        apiClient.get('/api/security/2fa/status').catch(() => ({ data: { enabled: false } })),
        apiClient.get('/api/security/sessions').catch(() => ({ data: [] })),
      ]);

      setTwoFactorEnabled(twoFactorRes.data?.enabled || false);

      if (sessionsRes.data && sessionsRes.data.length > 0) {
        setSessions(sessionsRes.data);
      } else {
        // Fallback mock sessions data
        setSessions([
          {
            id: '1',
            device: 'Chrome on Windows',
            location: 'Current session',
            lastActive: new Date().toISOString(),
            current: true,
          },
          {
            id: '2',
            device: 'Safari on iPhone',
            location: 'Unknown',
            lastActive: new Date(Date.now() - 86400000).toISOString(),
            current: false,
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch security data:', error);
      // Set defaults on error
      setTwoFactorEnabled(false);
      setSessions([
        {
          id: '1',
          device: 'Current browser',
          location: 'Current session',
          lastActive: new Date().toISOString(),
          current: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSecurityData();
  }, [fetchSecurityData]);

  // Validate password form
  const validatePasswordForm = () => {
    const errors = {};

    if (!passwordForm.currentPassword) {
      errors.currentPassword = 'Current password is required';
    }

    if (!passwordForm.newPassword) {
      errors.newPassword = 'New password is required';
    } else if (passwordForm.newPassword.length < 8) {
      errors.newPassword = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(passwordForm.newPassword)) {
      errors.newPassword = 'Password must contain uppercase, lowercase, and number';
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    setPasswordErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle password change
  const handlePasswordChange = async () => {
    if (!validatePasswordForm()) {
      return;
    }

    setPasswordLoading(true);
    try {
      await apiClient.put('/api/security/password', {
        currentPassword: passwordForm.currentPassword,
        newPassword: passwordForm.newPassword,
      });
      message.success('Password changed successfully');
      setShowPasswordModal(false);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (error) {
      console.error('Failed to change password:', error);
      if (error.response?.data?.message) {
        message.error(error.response.data.message);
      } else {
        message.error('Failed to change password');
      }
    } finally {
      setPasswordLoading(false);
    }
  };

  // Handle 2FA toggle
  const handle2FAToggle = async (enabled) => {
    try {
      setTwoFactorEnabled(enabled);
      if (enabled) {
        await apiClient.post('/api/security/2fa/enable');
        message.success('Two-factor authentication enabled');
      } else {
        await apiClient.post('/api/security/2fa/disable');
        message.success('Two-factor authentication disabled');
      }
    } catch (error) {
      console.error('Failed to update 2FA:', error);
      setTwoFactorEnabled(!enabled);
      message.error('Failed to update two-factor authentication');
    }
  };

  // Handle session revocation
  const handleRevokeSession = async (sessionId) => {
    try {
      await apiClient.delete(`/api/security/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      message.success('Session revoked');
    } catch (error) {
      console.error('Failed to revoke session:', error);
      message.error('Failed to revoke session');
    }
  };

  // Handle logout all sessions
  const handleLogoutAll = async () => {
    try {
      await apiClient.post('/api/security/sessions/revoke-all');
      setSessions((prev) => prev.filter((s) => s.current));
      message.success('All other sessions logged out');
    } catch (error) {
      console.error('Failed to logout all sessions:', error);
      message.error('Failed to logout all sessions');
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      await logout();
      message.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      console.error('Failed to logout:', error);
    }
  };

  // Format last active time
  const formatLastActive = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
  };

  // Get device icon
  const getDeviceIcon = (device) => {
    if (device.toLowerCase().includes('mobile') || device.toLowerCase().includes('iphone') || device.toLowerCase().includes('android')) {
      return <MobileOutlined style={{ fontSize: 20, color: 'var(--mobile-primary)' }} />;
    }
    return <DesktopOutlined style={{ fontSize: 20, color: 'var(--mobile-primary)' }} />;
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header with back button */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 'var(--mobile-space-lg)' }}>
        <button
          onClick={() => navigate('/m/settings')}
          style={{
            background: 'none',
            border: 'none',
            padding: 'var(--mobile-space-sm)',
            marginRight: 'var(--mobile-space-sm)',
            cursor: 'pointer',
            color: 'var(--mobile-text-primary)',
          }}
        >
          <ArrowLeftOutlined style={{ fontSize: 18 }} />
        </button>
        <div>
          <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
            Security
          </h1>
          <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
            Manage your account security
          </p>
        </div>
      </div>

      {/* Password Section */}
      <div className="mobile-section" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <h2 className="mobile-section-title">Password</h2>
        <div className="mobile-card mobile-security-card">
          <div className="mobile-security-item">
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
                <LockOutlined />
              </div>
              <div>
                <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                  Password
                </div>
                <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                  Last changed: Unknown
                </div>
              </div>
            </div>
            <Button
              type="primary"
              size="small"
              onClick={() => setShowPasswordModal(true)}
              style={{ borderRadius: 'var(--mobile-radius-md, 8px)' }}
            >
              Change
            </Button>
          </div>
        </div>
      </div>

      {/* Two-Factor Authentication Section */}
      <div className="mobile-section" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <h2 className="mobile-section-title">Two-Factor Authentication</h2>
        <div className="mobile-card mobile-security-card">
          <div className="mobile-security-item">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--mobile-radius-md, 8px)',
                  background: twoFactorEnabled ? 'var(--mobile-success-bg)' : 'var(--mobile-surface)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: twoFactorEnabled ? 'var(--mobile-success)' : 'var(--mobile-primary)',
                }}
              >
                <SafetyCertificateOutlined />
              </div>
              <div>
                <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                  Two-Factor Authentication
                </div>
                <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                  {twoFactorEnabled ? 'Enabled' : 'Add an extra layer of security'}
                </div>
              </div>
            </div>
            <Switch
              checked={twoFactorEnabled}
              onChange={handle2FAToggle}
              checkedChildren={<CheckCircleOutlined />}
              unCheckedChildren={<ExclamationCircleOutlined />}
            />
          </div>
        </div>
      </div>

      {/* Active Sessions Section */}
      <div className="mobile-section" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--mobile-space-sm)' }}>
          <h2 className="mobile-section-title" style={{ marginBottom: 0 }}>Active Sessions</h2>
          {sessions.length > 1 && (
            <Popconfirm
              title="Logout all other sessions?"
              description="This will log out all other devices except this one."
              onConfirm={handleLogoutAll}
              okText="Logout All"
              cancelText="Cancel"
            >
              <Button type="link" size="small" danger>
                <LogoutOutlined /> Logout All
              </Button>
            </Popconfirm>
          )}
        </div>
        <div className="mobile-card mobile-security-card">
          {sessions.map((session, index) => (
            <div
              key={session.id}
              className={`mobile-security-item ${index < sessions.length - 1 ? 'mobile-security-item-border' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}>
                {getDeviceIcon(session.device)}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-xs)' }}>
                    <span style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                      {session.device}
                    </span>
                    {session.current && (
                      <Tag color="green" style={{ fontSize: 'var(--mobile-font-xs)', margin: 0 }}>
                        Current
                      </Tag>
                    )}
                  </div>
                  <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                    {session.location} • Last active: {formatLastActive(session.lastActive)}
                  </div>
                </div>
              </div>
              {!session.current && (
                <Popconfirm
                  title="Logout this session?"
                  onConfirm={() => handleRevokeSession(session.id)}
                  okText="Logout"
                  cancelText="Cancel"
                  okButtonProps={{ danger: true }}
                >
                  <Button type="text" size="small" danger>
                    <LogoutOutlined />
                  </Button>
                </Popconfirm>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Logout Section */}
      <div className="mobile-section">
        <div className="mobile-card mobile-danger-card">
          <Popconfirm
            title="Logout of STING?"
            description="You will need to log in again to access your account."
            onConfirm={handleLogout}
            okText="Logout"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <div className="mobile-danger-item">
              <LogoutOutlined style={{ fontSize: 20, color: 'var(--mobile-danger)' }} />
              <span style={{ fontWeight: 500, color: 'var(--mobile-danger)' }}>Logout</span>
            </div>
          </Popconfirm>
        </div>
      </div>

      {/* Password Change Modal */}
      <Modal
        title="Change Password"
        open={showPasswordModal}
        onCancel={() => setShowPasswordModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setShowPasswordModal(false)}>
            Cancel
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={passwordLoading}
            onClick={handlePasswordChange}
          >
            Change Password
          </Button>,
        ]}
        destroyOnClose
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-md)' }}>
          {/* Current Password */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Current Password</label>
            <Input.Password
              value={passwordForm.currentPassword}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, currentPassword: e.target.value }))}
              placeholder="Enter current password"
              iconRender={(visible) => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
            {passwordErrors.currentPassword && (
              <span className="mobile-form-error">{passwordErrors.currentPassword}</span>
            )}
          </div>

          {/* New Password */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">New Password</label>
            <Input.Password
              value={passwordForm.newPassword}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, newPassword: e.target.value }))}
              placeholder="Enter new password"
              iconRender={(visible) => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
            {passwordErrors.newPassword && (
              <span className="mobile-form-error">{passwordErrors.newPassword}</span>
            )}
          </div>

          {/* Confirm Password */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Confirm New Password</label>
            <Input.Password
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, confirmPassword: e.target.value }))}
              placeholder="Confirm new password"
              iconRender={(visible) => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
            {passwordErrors.confirmPassword && (
              <span className="mobile-form-error">{passwordErrors.confirmPassword}</span>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MobileSecurity;
