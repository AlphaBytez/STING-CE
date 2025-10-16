import React, { useState, useEffect } from 'react';
import { Mail, Lock, Bell, Shield, Trash2, Settings as SettingsIcon, Cpu, User, Info, Key } from 'lucide-react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import SecuritySettings from './SecuritySettings';
import EmailSettings from './EmailSettings';
import PasswordSettings from './PasswordSettings';
import PreferenceSettings from './PreferenceSettings';
import AccountDeletion from './AccountDeletion';
import ProfileSettings from './ProfileSettings';
import AboutSettings from './AboutSettings';
import BeeSettings from '../settings/BeeSettings';
import BeeSettingsReadOnly from '../settings/BeeSettingsReadOnly';
import ApiKeySettings from '../settings/ApiKeySettings';
import RecoveryCodesSettings from '../settings/RecoveryCodesSettings';
import { useRole } from './RoleContext';
import { useTheme } from '../../context/ThemeContext';

const UserSettings = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState('profile');
  
  // Check URL parameters for initial tab
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['profile', 'security', 'api-keys', 'recovery-codes', 'email', 'password', 'preferences', 'llm', 'about', 'delete'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);
  const { userRole } = useRole();
  const { themeColors } = useTheme();
  
  // Check user permissions
  const isAdmin = userRole === 'admin' || userRole === 'super_admin';
  const isSuperAdmin = userRole === 'super_admin';

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'api-keys', label: 'API Keys', icon: Key, badge: 'Tier 2-3' },
    { id: 'recovery-codes', label: 'Recovery Codes', icon: Shield, badge: 'Tier 3-4' },
    { id: 'email', label: 'Email', icon: Mail },
    { id: 'password', label: 'Password', icon: Lock },
    { id: 'preferences', label: 'Preferences', icon: SettingsIcon },
    // Add LLM settings tab - full access for super admins only, read-only for others
    { id: 'llm', label: 'Bee Settings', icon: Cpu, badge: isSuperAdmin ? 'Super Admin' : 'View' },
    { id: 'about', label: 'About', icon: Info },
    { id: 'delete', label: 'Delete Account', icon: Trash2 },
  ];

  // Handle tab change with URL update
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    // Update URL to reflect the active tab
    const newSearchParams = new URLSearchParams(searchParams);
    newSearchParams.set('tab', tabId);
    setSearchParams(newSearchParams);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileSettings />;
      case 'security':
        return <SecuritySettings />;
      case 'api-keys':
        return <ApiKeySettings />;
      case 'recovery-codes':
        return <RecoveryCodesSettings />;
      case 'email':
        return <EmailSettings />;
      case 'password':
        return <PasswordSettings />;
      case 'preferences':
        return <PreferenceSettings />;
      case 'llm':
        return isSuperAdmin ? <BeeSettings /> : <BeeSettingsReadOnly />;
      case 'about':
        return <AboutSettings />;
      case 'delete':
        return <AccountDeletion />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-white">Account Settings</h1>
      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar */}
        <div className="w-full md:w-64 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`floating-button w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-yellow-500 text-black shadow-lg'
                  : 'bg-gray-700 text-gray-200 hover:bg-gray-600 hover:text-white'
              }`}
            >
              <div className="flex items-center space-x-3">
                <tab.icon className="w-5 h-5" />
                <span className="font-medium">{tab.label}</span>
              </div>
              {tab.badge && (
                <span className="px-2 py-1 text-xs bg-blue-500 text-white rounded-full font-medium">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 dashboard-card p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default UserSettings;