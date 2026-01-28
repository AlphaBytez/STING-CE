import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Upload, Button } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  CameraOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import apiClient from '../../../utils/apiClient';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * MobileProfile - Mobile profile settings page
 * Profile editing optimized for mobile with name, email, and avatar management
 */
const MobileProfile = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    avatar: null,
    bio: '',
    phone: '',
  });
  const [originalProfile, setOriginalProfile] = useState({});
  const [errors, setErrors] = useState({});

  // Fetch user profile data
  const fetchProfile = useCallback(async () => {
    if (!user?.id) {
      // Use user from auth context as fallback
      setProfile({
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.avatar || null,
        bio: user?.bio || '',
        phone: user?.phone || '',
      });
      setOriginalProfile({
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.avatar || null,
        bio: user?.bio || '',
        phone: user?.phone || '',
      });
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.get('/api/user/profile').catch(() => ({ data: null }));

      const profileData = response.data || {
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.avatar || null,
        bio: user?.bio || '',
        phone: user?.phone || '',
      };

      setProfile(profileData);
      setOriginalProfile(profileData);
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      // Use auth context data as fallback
      setProfile({
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.avatar || null,
        bio: user?.bio || '',
        phone: user?.phone || '',
      });
      setOriginalProfile({
        name: user?.name || '',
        email: user?.email || '',
        avatar: user?.avatar || null,
        bio: user?.bio || '',
        phone: user?.phone || '',
      });
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    if (!profile.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (profile.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (!profile.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle input change
  const handleChange = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  // Handle avatar change
  const handleAvatarChange = (info) => {
    if (info.file.status === 'done' || info.file.status === 'uploading') {
      const file = info.file.originFileObj || info.file;
      const reader = new FileReader();
      reader.onload = (e) => {
        setProfile((prev) => ({ ...prev, avatar: e.target?.result }));
      };
      if (file) {
        reader.readAsDataURL(file);
      }
    }
  };

  // Save profile
  const handleSave = async () => {
    if (!validateForm()) {
      message.error('Please fix the errors before saving');
      return;
    }

    setSaving(true);
    try {
      await apiClient.put('/api/user/profile', profile);
      setOriginalProfile(profile);
      message.success('Profile updated successfully');
    } catch (error) {
      console.error('Failed to save profile:', error);
      message.error('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  // Check if profile has changes
  const hasChanges = JSON.stringify(profile) !== JSON.stringify(originalProfile);

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
            Profile Settings
          </h1>
          <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
            Manage your profile information
          </p>
        </div>
      </div>

      {/* Avatar Section */}
      <div className="mobile-section" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <div className="mobile-card mobile-profile-avatar-card">
          <div className="mobile-profile-avatar-container">
            <Upload
              name="avatar"
              showUploadList={false}
              beforeUpload={() => false}
              onChange={handleAvatarChange}
            >
              <div className="mobile-profile-avatar">
                {profile.avatar ? (
                  <img
                    src={profile.avatar}
                    alt="Profile"
                    style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
                  />
                ) : (
                  <UserOutlined style={{ fontSize: 40, color: 'var(--mobile-text-tertiary)' }} />
                )}
              </div>
            </Upload>
            <div className="mobile-profile-avatar-overlay">
              <CameraOutlined style={{ fontSize: 16, color: 'var(--mobile-text-inverse)' }} />
            </div>
          </div>
          <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)', marginTop: 'var(--mobile-space-sm)' }}>
            Tap to change photo
          </p>
        </div>
      </div>

      {/* Profile Form */}
      <div className="mobile-section">
        <h2 className="mobile-section-title">Personal Information</h2>
        <div className="mobile-card mobile-form-card">
          {/* Name Field */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Full Name</label>
            <div style={{ position: 'relative' }}>
              <UserOutlined
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              />
              <input
                type="text"
                className="mobile-form-input"
                style={{ paddingLeft: 40 }}
                value={profile.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="Enter your name"
              />
            </div>
            {errors.name && (
              <span className="mobile-form-error">{errors.name}</span>
            )}
          </div>

          {/* Email Field */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <MailOutlined
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              />
              <input
                type="email"
                className="mobile-form-input"
                style={{
                  paddingLeft: 40,
                  background: 'var(--mobile-bg-secondary)',
                  cursor: 'not-allowed',
                }}
                value={profile.email}
                onChange={(e) => handleChange('email', e.target.value)}
                placeholder="Enter your email"
                readOnly
              />
            </div>
            <span style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)', marginTop: 4 }}>
              Email cannot be changed
            </span>
            {errors.email && (
              <span className="mobile-form-error">{errors.email}</span>
            )}
          </div>

          {/* Phone Field */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Phone Number (Optional)</label>
            <div style={{ position: 'relative' }}>
              <input
                type="tel"
                className="mobile-form-input"
                value={profile.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="Enter your phone number"
              />
            </div>
          </div>

          {/* Bio Field */}
          <div className="mobile-form-field">
            <label className="mobile-form-label">Bio (Optional)</label>
            <textarea
              className="mobile-form-textarea"
              value={profile.bio}
              onChange={(e) => handleChange('bio', e.target.value)}
              placeholder="Tell us about yourself"
              rows={3}
              maxLength={200}
            />
            <span style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)', marginTop: 4 }}>
              {profile.bio.length}/200 characters
            </span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div style={{ marginTop: 'var(--mobile-space-lg)' }}>
        <Button
          type="primary"
          block
          size="large"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
          disabled={!hasChanges}
          style={{
            height: 48,
            borderRadius: 'var(--mobile-radius-md, 8px)',
            fontWeight: 500,
          }}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  );
};

export default MobileProfile;
