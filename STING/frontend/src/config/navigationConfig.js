import React from 'react';
import {
  DashboardOutlined,
  MessageOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  SettingOutlined,
  GlobalOutlined,
  TeamOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import {
  MessageSquare,
  Settings,
  Users,
  FileText,
  Package,
  Globe,
} from 'lucide-react';
import BasketIcon from '../components/icons/BasketIcon';
import BeeSearchIcon from '../components/icons/BeeSearchIcon';

/**
 * Centralized Navigation Configuration
 * Used by both MainInterface.js floating navigation and Sidebar.jsx
 */

// Current configuration version - increment when adding new items
export const NAV_CONFIG_VERSION = 5;

// Default navigation structure
export const defaultNavConfig = {
  version: NAV_CONFIG_VERSION,
  persistent: [
    { id: 'dashboard', name: 'Dashboard', icon: 'DashboardOutlined', path: '/dashboard', enabled: true },
    { id: 'chat', name: 'Bee Chat', icon: 'MessageOutlined', path: '/dashboard/chat', enabled: true },
    { id: 'basket', name: 'Basket', icon: 'BasketOutlined', path: '/dashboard/basket', enabled: true },
  ],
  scrollable: [
    { id: 'search', name: 'Search', icon: 'GlobalOutlined', path: '/dashboard/search', enabled: true },
    { id: 'reports', name: 'Bee Reports', icon: 'FileTextOutlined', path: '/dashboard/reports', enabled: true },
    { id: 'report-templates', name: 'Templates', icon: 'FileTextOutlined', path: '/dashboard/report-templates', enabled: true },
    { id: 'honey-jars', name: 'Honey Jars', icon: 'AppstoreOutlined', path: '/dashboard/honey-jars', enabled: true },
    { id: 'admin', name: 'Admin', icon: 'TeamOutlined', path: '/dashboard/admin', enabled: true, adminOnly: true },
    { id: 'settings', name: 'Settings', icon: 'SettingOutlined', path: '/dashboard/settings', enabled: true },
  ]
};

// Icon mappings for different UI libraries
export const antdIconMap = {
  DashboardOutlined: <DashboardOutlined />,
  MessageOutlined: <MessageOutlined />,
  FileTextOutlined: <FileTextOutlined />,
  AppstoreOutlined: <AppstoreOutlined />,
  SettingOutlined: <SettingOutlined />,
  GlobalOutlined: <GlobalOutlined />,
  TeamOutlined: <TeamOutlined />,
  BasketOutlined: <InboxOutlined />,
  SearchOutlined: <BeeSearchIcon className="w-4 h-4" />,
};

export const lucideIconMap = {
  DashboardOutlined: Globe,
  MessageOutlined: MessageSquare,
  FileTextOutlined: FileText,
  AppstoreOutlined: Package,
  SettingOutlined: Settings,
  GlobalOutlined: Globe,
  TeamOutlined: Users,
  BasketOutlined: BasketIcon,
  SearchOutlined: BeeSearchIcon,
};

// React component icon map (for MainInterface floating nav)
export const componentIconMap = {
  DashboardOutlined: <DashboardOutlined />,
  MessageOutlined: <MessageOutlined />,
  FileTextOutlined: <FileTextOutlined />,
  AppstoreOutlined: <AppstoreOutlined />,
  SettingOutlined: <SettingOutlined />,
  GlobalOutlined: <GlobalOutlined />,
  TeamOutlined: <TeamOutlined />,
  BasketOutlined: <BasketIcon className="w-5 h-5" />,
  SearchOutlined: <BeeSearchIcon className="w-5 h-5" />,
};

/**
 * Load navigation configuration with database-backed preferences
 * Falls back to localStorage for backward compatibility
 * @param {boolean} isAdmin - Whether current user is admin
 * @param {boolean} useDatabase - Whether to use database-backed preferences
 * @returns {object} Navigation configuration
 */
export const loadNavigationConfig = async (isAdmin = false, useDatabase = true) => {
  let config = defaultNavConfig;
  
  if (useDatabase) {
    try {
      // Try to load from database first
      const preferencesService = (await import('../services/preferencesService.js')).default;
      
      // Auto-migrate if needed
      await preferencesService.autoMigrate();
      
      // Get navigation preferences from database
      const response = await preferencesService.getNavigationPreferences();
      
      if (response && response.config) {
        config = response.config;
        // Navigation: Loaded from database
      } else {
        // Navigation: No database config found, using defaults
      }
    } catch (error) {
      // Navigation: Database load failed, falling back to localStorage
      // Fall back to localStorage method
      config = loadNavigationConfigFromLocalStorage();
    }
  } else {
    // Use localStorage method (backward compatibility)
    config = loadNavigationConfigFromLocalStorage();
  }
  
  // Filter admin-only items based on user role
  if (!isAdmin) {
    config = {
      ...config,
      persistent: config.persistent.filter(item => !item.adminOnly),
      scrollable: config.scrollable.filter(item => !item.adminOnly)
    };
  }
  
  return config;
};

/**
 * Legacy localStorage-based navigation config loading
 * @returns {object} Navigation configuration from localStorage
 */
export const loadNavigationConfigFromLocalStorage = () => {
  const saved = localStorage.getItem('sting-nav-config');
  let config = defaultNavConfig;
  
  if (saved) {
    try {
      const savedConfig = JSON.parse(saved);
      
      // Check if saved config is outdated - force update if version is older
      if (!savedConfig.version || savedConfig.version < NAV_CONFIG_VERSION) {
        console.log(`Navigation: Updating localStorage config from version ${savedConfig.version || 'legacy'} to ${NAV_CONFIG_VERSION}`);
        config = defaultNavConfig;
        localStorage.setItem('sting-nav-config', JSON.stringify(defaultNavConfig));
      } else {
        // Smart merge: add any new items from defaults that don't exist in saved config
        const mergedConfig = {
          version: NAV_CONFIG_VERSION,
          persistent: [...savedConfig.persistent || []],
          scrollable: [...savedConfig.scrollable || []]
        };
        
        // Add missing items from defaults
        defaultNavConfig.persistent.forEach(defaultItem => {
          if (!mergedConfig.persistent.find(item => item.id === defaultItem.id)) {
            mergedConfig.persistent.push(defaultItem);
          }
        });
        
        defaultNavConfig.scrollable.forEach(defaultItem => {
          if (!mergedConfig.scrollable.find(item => item.id === defaultItem.id)) {
            mergedConfig.scrollable.push(defaultItem);
          }
        });
        
        config = mergedConfig;
        localStorage.setItem('sting-nav-config', JSON.stringify(mergedConfig));
      }
    } catch (e) {
      console.error('Failed to parse saved navigation config:', e);
      config = defaultNavConfig;
    }
  }
  
  return config;
};

/**
 * Save navigation configuration to database
 * @param {object} config - Navigation configuration
 * @param {boolean} fallbackToLocalStorage - Whether to save to localStorage if database fails
 */
export const saveNavigationConfig = async (config, fallbackToLocalStorage = true) => {
  try {
    const preferencesService = (await import('../services/preferencesService.js')).default;
    await preferencesService.updateNavigationPreferences(config, config.version || NAV_CONFIG_VERSION);
    console.log('Navigation: Saved to database successfully');
    return true;
  } catch (error) {
    console.warn('Navigation: Database save failed:', error);
    
    if (fallbackToLocalStorage) {
      try {
        localStorage.setItem('sting-nav-config', JSON.stringify(config));
        console.log('Navigation: Saved to localStorage as fallback');
        return true;
      } catch (localError) {
        console.error('Navigation: LocalStorage save also failed:', localError);
      }
    }
    
    return false;
  }
};

/**
 * Convert string icons to components for floating navigation
 * @param {object} config - Navigation configuration
 * @returns {object} Configuration with React components as icons
 */
export const convertIconsToComponents = (config) => {
  const converted = { ...config };
  ['persistent', 'scrollable'].forEach(section => {
    if (converted[section]) {
      converted[section] = converted[section].map(item => ({
        ...item,
        icon: typeof item.icon === 'string' ? (componentIconMap[item.icon] || <SettingOutlined />) : item.icon
      }));
    }
  });
  return converted;
};