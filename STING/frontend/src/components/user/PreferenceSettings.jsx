import React, { useState, useEffect } from 'react';
import { Bell, Globe, Clock, Palette, Monitor, Zap } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';
import { useTheme as useNewTheme, THEMES, THEME_CONFIG } from '../theme/ThemeManager';
import PerformanceIndicator from '../theme/PerformanceIndicator';

const PreferenceSettings = () => {
  const { identity } = useKratos();
  const { currentTheme, switchTheme, themeConfig, isTransitioning } = useNewTheme();
  const [preferences, setPreferences] = useState({
    language: 'en',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    notifications: {
      email: true,
      pushNotifications: true,
      updates: true,
      newsletter: false,
      teamInvites: true,
      security: true
    }
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadPreferences = async () => {
      try {
        // In a real app, fetch user preferences from your backend
        setIsLoading(false);
      } catch (error) {
        console.error('Error loading preferences:', error);
        setIsLoading(false);
      }
    };

    loadPreferences();
  }, []);

  const handleNotificationToggle = (key) => {
    setPreferences(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [key]: !prev.notifications[key]
      }
    }));
  };

  const handlePreferenceChange = (key, value) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Save preferences to your backend
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      // Show success message or handle accordingly
    } catch (error) {
      console.error('Error saving preferences:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="pb-6 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Display</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
              <div>
                <p className="font-medium" style={{ color: 'var(--color-text)' }}>Language</p>
                <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Select your preferred language</p>
              </div>
            </div>
            <select
              value={preferences.language}
              onChange={(e) => handlePreferenceChange('language', e.target.value)}
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
                borderRadius: 'var(--radius-lg)',
                padding: '0.5rem 0.75rem'
              }}
              className="focus:ring-2 focus:ring-primary focus:border-primary"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
              <div>
                <p className="font-medium" style={{ color: 'var(--color-text)' }}>Timezone</p>
                <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Set your timezone</p>
              </div>
            </div>
            <select
              value={preferences.timezone}
              onChange={(e) => handlePreferenceChange('timezone', e.target.value)}
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
                borderRadius: 'var(--radius-lg)',
                padding: '0.5rem 0.75rem'
              }}
              className="focus:ring-2 focus:ring-primary focus:border-primary"
            >
              {Intl.supportedValuesOf('timeZone').map(timezone => (
                <option key={timezone} value={timezone}>
                  {timezone}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Palette className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
              <div>
                <p className="font-medium" style={{ color: 'var(--color-text)' }}>Theme</p>
                <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  Choose your visual theme ({themeConfig[currentTheme]?.performance})
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isTransitioning && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-400"></div>
              )}
              <select
                value={currentTheme}
                onChange={(e) => switchTheme(e.target.value)}
                disabled={isTransitioning}
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '0.5rem 0.75rem'
                }}
                className="focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50"
              >
                {Object.entries(THEMES).map(([key, themeId]) => (
                  <option key={themeId} value={themeId}>
                    {THEME_CONFIG[themeId]?.name} - {THEME_CONFIG[themeId]?.category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Theme info panel */}
          <div 
            className="p-3 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              borderColor: 'var(--color-border)'
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Monitor className="w-4 h-4" style={{ color: 'var(--color-primary)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                Current Theme: {themeConfig[currentTheme]?.name}
              </span>
            </div>
            <p className="text-xs mb-2" style={{ color: 'var(--color-text-secondary)' }}>
              {themeConfig[currentTheme]?.description}
            </p>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-green-400" />
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  {themeConfig[currentTheme]?.performance}
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {themeConfig[currentTheme]?.features.slice(0, 2).map((feature, idx) => (
                  <span
                    key={idx}
                    className="px-1.5 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: 'var(--color-bg)',
                      color: 'var(--color-text-secondary)'
                    }}
                  >
                    {feature}
                  </span>
                ))}
                {themeConfig[currentTheme]?.features.length > 2 && (
                  <span
                    className="px-1.5 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: 'var(--color-bg)',
                      color: 'var(--color-text-secondary)'
                    }}
                  >
                    +{themeConfig[currentTheme].features.length - 2} more
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Performance Monitor */}
          <div className="mt-4">
            <PerformanceIndicator />
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Notifications</h2>
        <div className="space-y-4">
          {Object.entries(preferences.notifications).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
                <div>
                  <p className="font-medium capitalize" style={{ color: 'var(--color-text)' }}>{key.replace(/([A-Z])/g, ' $1')}</p>
                  <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    Receive notifications for {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                  </p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={() => handleNotificationToggle(key)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 
                              peer-focus:ring-primary-light rounded-full peer 
                              peer-checked:after:translate-x-full peer-checked:after:border-white 
                              after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                              after:bg-white after:border-gray-300 after:border after:rounded-full 
                              after:h-5 after:w-5 after:transition-all peer-checked:bg-primary">
                </div>
              </label>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-6 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="floating-button w-full py-3 px-4 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          style={{
            backgroundColor: 'var(--color-primary)',
            color: 'var(--color-text-inverse)'
          }}
          onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--color-primary-hover)'}
          onMouseLeave={(e) => e.target.style.backgroundColor = 'var(--color-primary)'}
        >
          {isSaving ? 'Saving Preferences...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
};

export default PreferenceSettings;