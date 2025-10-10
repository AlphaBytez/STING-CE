import React, { useState, useEffect } from 'react';
import { Card, Switch, Button, message, List, Space, Typography } from 'antd';
import { 
  DashboardOutlined, 
  MessageOutlined, 
  FileTextOutlined, 
  AppstoreOutlined, 
  SettingOutlined, 
  GlobalOutlined, 
  ShoppingOutlined, 
  TeamOutlined, 
  BarChartOutlined,
  HolderOutlined,
  SaveOutlined,
  ReloadOutlined,
  UpOutlined,
  DownOutlined,
  SwapOutlined,
  InboxOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { useTheme } from '../../context/ThemeContext';
import { loadNavigationConfig, saveNavigationConfig, antdIconMap, NAV_CONFIG_VERSION } from '../../config/navigationConfig';
import preferencesService from '../../services/preferencesService';

const { Text } = Typography;

const NavigationSettings = () => {
  const { themeColors } = useTheme();
  
  const [navConfig, setNavConfig] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);

  // Load saved configuration using database-backed preferences
  useEffect(() => {
    const loadConfig = async () => {
      setIsLoading(true);
      try {
        const config = await loadNavigationConfig(true, true); // Always pass true for admin in settings, use database
        setNavConfig(config);
      } catch (error) {
        console.error('Failed to load navigation config:', error);
        message.error('Failed to load navigation configuration');
        // Fallback to localStorage
        const fallbackConfig = await loadNavigationConfig(true, false);
        setNavConfig(fallbackConfig);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  // Move item up within section
  const moveItemUp = (section, index) => {
    if (index === 0) return;
    const items = [...navConfig[section]];
    [items[index - 1], items[index]] = [items[index], items[index - 1]];
    setNavConfig({ ...navConfig, [section]: items });
    setHasChanges(true);
  };

  // Move item down within section
  const moveItemDown = (section, index) => {
    if (index === navConfig[section].length - 1) return;
    const items = [...navConfig[section]];
    [items[index], items[index + 1]] = [items[index + 1], items[index]];
    setNavConfig({ ...navConfig, [section]: items });
    setHasChanges(true);
  };

  // Move item between sections
  const moveItemBetweenSections = (fromSection, toSection, index) => {
    const fromItems = [...navConfig[fromSection]];
    const toItems = [...navConfig[toSection]];
    const [movedItem] = fromItems.splice(index, 1);
    toItems.push(movedItem);
    
    setNavConfig({
      ...navConfig,
      [fromSection]: fromItems,
      [toSection]: toItems
    });
    setHasChanges(true);
  };

  // Toggle item enabled/disabled
  const toggleItem = (section, index, enabled) => {
    const newConfig = { ...navConfig };
    newConfig[section][index].enabled = enabled;
    setNavConfig(newConfig);
    setHasChanges(true);
  };

  // Save configuration to database
  const saveConfiguration = async () => {
    setSaveLoading(true);
    try {
      const success = await saveNavigationConfig(navConfig, true); // Save to database with localStorage fallback
      
      if (success) {
        setHasChanges(false);
        message.success('Navigation configuration saved successfully!');
        
        // Trigger a custom event to notify MainInterface of the change
        window.dispatchEvent(new CustomEvent('navigation-config-updated', { 
          detail: navConfig 
        }));
      } else {
        message.error('Failed to save navigation configuration');
      }
    } catch (error) {
      console.error('Error saving navigation config:', error);
      message.error('Failed to save navigation configuration');
    } finally {
      setSaveLoading(false);
    }
  };

  // Reset to defaults
  const resetToDefaults = async () => {
    try {
      const config = await loadNavigationConfig(true, false); // Load defaults without database
      setNavConfig(config);
      setHasChanges(true);
      message.info('Configuration reset to defaults. Click Save to apply.');
    } catch (error) {
      console.error('Error resetting to defaults:', error);
      message.error('Failed to reset configuration');
    }
  };

  const renderNavItem = (item, index, section) => (
    <div key={item.id} className="nav-config-item">
      <div className="flex items-center justify-between p-3 dynamic-card-subtle rounded-lg mb-2 hover:bg-gray-600/20 transition-colors">
        <div className="flex items-center gap-3">
          <div className="text-lg">{antdIconMap[item.icon]}</div>
          <div>
            <div className="text-white font-medium">{item.name}</div>
            <div className="text-xs text-gray-400">{item.path}</div>
            {item.badge && (
              <span className="inline-block px-2 py-1 text-xs bg-purple-500/80 text-white rounded mt-1">
                {item.badge}
              </span>
            )}
            {item.adminOnly && (
              <span className="inline-block px-2 py-1 text-xs bg-red-500/80 text-white rounded mt-1 ml-1">
                Admin Only
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Space>
            <Button
              size="small"
              icon={<UpOutlined />}
              disabled={index === 0}
              onClick={() => moveItemUp(section, index)}
              title="Move up"
            />
            <Button
              size="small"
              icon={<DownOutlined />}
              disabled={index === navConfig[section].length - 1}
              onClick={() => moveItemDown(section, index)}
              title="Move down"
            />
            <Button
              size="small"
              icon={<SwapOutlined />}
              onClick={() => moveItemBetweenSections(section, section === 'persistent' ? 'scrollable' : 'persistent', index)}
              title={`Move to ${section === 'persistent' ? 'scrollable' : 'persistent'} section`}
            />
          </Space>
          <Switch
            checked={item.enabled}
            onChange={(checked) => toggleItem(section, index, checked)}
            size="small"
          />
        </div>
      </div>
    </div>
  );

  if (isLoading || !navConfig) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
            <p className="text-gray-400">Loading navigation settings...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">Navigation Settings</h2>
        <p className="text-gray-400">
          Customize the floating navigation panel. Changes are saved to the database and persist across devices.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Persistent Items */}
        <Card 
          title={<span className="text-white">Persistent Items</span>}
          className="dynamic-card-subtle"
          extra={<span className="text-xs text-gray-400">Always visible at top</span>}
        >
          <div className="min-h-32">
            {navConfig.persistent.map((item, index) => 
              renderNavItem(item, index, 'persistent')
            )}
            {navConfig.persistent.length === 0 && (
              <div className="text-center text-gray-400 py-8">
                <span className="text-gray-400">No persistent items</span>
              </div>
            )}
          </div>
        </Card>

        {/* Scrollable Items */}
        <Card 
          title={<span className="text-white">Scrollable Items</span>}
          className="dynamic-card-subtle"
          extra={<span className="text-xs text-gray-400">Scrollable section below divider</span>}
        >
          <div className="min-h-32">
            {navConfig.scrollable.map((item, index) => 
              renderNavItem(item, index, 'scrollable')
            )}
            {navConfig.scrollable.length === 0 && (
              <div className="text-center text-gray-400 py-8">
                <span className="text-gray-400">No scrollable items</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mt-6">
        <button
          onClick={saveConfiguration}
          disabled={!hasChanges || saveLoading}
          className="floating-button text-white px-4 py-2 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {saveLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1"></div>
              Saving...
            </>
          ) : (
            <>
              <SaveOutlined />
              Save Configuration
            </>
          )}
        </button>
        <button
          onClick={resetToDefaults}
          className="dynamic-card-subtle px-4 py-2 rounded-xl transition-colors hover:bg-gray-600/20 text-gray-300 hover:text-white flex items-center gap-2 border border-gray-600"
        >
          <ReloadOutlined />
          Reset to Defaults
        </button>
      </div>

      {hasChanges && (
        <div className="mt-4 p-3 bg-orange-500/10 border border-orange-400/30 rounded text-orange-300 text-sm">
          <strong>Unsaved Changes:</strong> Remember to save your configuration to apply changes to the navigation.
        </div>
      )}

      <style jsx>{`
        .glass-card {
          background: rgba(42, 49, 66, 0.9) !important;
          border: 1px solid rgba(58, 67, 86, 0.5) !important;
        }
        
        .glass-card .ant-card-head {
          background: rgba(42, 49, 66, 0.7) !important;
          border-bottom: 1px solid rgba(58, 67, 86, 0.5) !important;
        }
        
        .glass-card .ant-card-head-title {
          color: white !important;
        }
      `}</style>
    </div>
  );
};

export default NavigationSettings;