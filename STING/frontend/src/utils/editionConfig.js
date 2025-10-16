/**
 * Edition Configuration Utility
 * Manages Community Edition vs Enterprise Edition features
 * 
 * Copyright 2025 STING-CE Contributors
 * Licensed under the Apache License, Version 2.0
 */

// Default configuration for Community Edition
const defaultConfig = {
  type: 'ce',
  hideEnterpriseUI: true,
  enterpriseEndpointsEnabled: false,
  enterpriseFeatures: {
    marketplace: false,
    teams: false,
    swarmOrchestration: false,
    advancedPiiCompliance: false,
    nectarBotManager: false
  },
  placeholderText: "This feature is available in STING Enterprise Edition",
  placeholderLink: "https://github.com/sting-ce/enterprise"
};

// Cache for edition configuration
let editionConfig = null;

/**
 * Load edition configuration from backend
 */
export const loadEditionConfig = async () => {
  try {
    const response = await fetch('/api/config/edition', {
      credentials: 'include'
    });
    
    if (response.ok) {
      editionConfig = await response.json();
    } else {
      console.warn('Failed to load edition config, using defaults');
      editionConfig = defaultConfig;
    }
  } catch (error) {
    console.error('Error loading edition config:', error);
    editionConfig = defaultConfig;
  }
  
  return editionConfig;
};

/**
 * Get current edition type
 * @returns {string} 'ce' or 'enterprise'
 */
export const getEditionType = () => {
  if (!editionConfig) {
    // Check environment variable as fallback
    const envEdition = process.env.REACT_APP_STING_EDITION;
    return envEdition || 'ce';
  }
  return editionConfig.type;
};

/**
 * Check if running Community Edition
 * @returns {boolean}
 */
export const isCommunityEdition = () => {
  return getEditionType() === 'ce';
};

/**
 * Check if running Enterprise Edition
 * @returns {boolean}
 */
export const isEnterpriseEdition = () => {
  return getEditionType() === 'enterprise';
};

/**
 * Check if a specific enterprise feature is enabled
 * @param {string} feature - Feature name (e.g., 'marketplace', 'teams')
 * @returns {boolean}
 */
export const isEnterpriseFeatureEnabled = (feature) => {
  // In CE, all enterprise features are disabled
  if (isCommunityEdition()) {
    return false;
  }
  
  // In Enterprise, check specific feature flag
  if (!editionConfig || !editionConfig.enterpriseFeatures) {
    return false;
  }
  
  return editionConfig.enterpriseFeatures[feature] === true;
};

/**
 * Check if enterprise UI should be hidden
 * @returns {boolean}
 */
export const shouldHideEnterpriseUI = () => {
  if (!editionConfig) {
    return true; // Default to hiding in CE
  }
  return editionConfig.hideEnterpriseUI;
};

/**
 * Get placeholder text for enterprise features
 * @returns {string}
 */
export const getEnterprisePlaceholderText = () => {
  if (!editionConfig) {
    return defaultConfig.placeholderText;
  }
  return editionConfig.placeholderText || defaultConfig.placeholderText;
};

/**
 * Get link to enterprise information
 * @returns {string}
 */
export const getEnterprisePlaceholderLink = () => {
  if (!editionConfig) {
    return defaultConfig.placeholderLink;
  }
  return editionConfig.placeholderLink || defaultConfig.placeholderLink;
};

/**
 * Filter navigation items based on edition
 * @param {Array} navItems - Navigation items array
 * @returns {Array} Filtered navigation items
 */
export const filterNavigationByEdition = (navItems) => {
  if (!shouldHideEnterpriseUI()) {
    return navItems; // Show all items in enterprise
  }
  
  // Define enterprise-only routes
  const enterpriseRoutes = [
    '/marketplace',
    '/teams',
    '/swarm',
    '/nectar-bot',
    '/advanced-pii'
  ];
  
  // Filter out enterprise-only items
  return navItems.filter(item => {
    // Check if item path is enterprise-only
    if (item.path && enterpriseRoutes.includes(item.path)) {
      return false;
    }
    
    // Check if item has explicit enterprise flag
    if (item.enterprise === true) {
      return false;
    }
    
    // Recursively filter children if present
    if (item.children) {
      item.children = filterNavigationByEdition(item.children);
    }
    
    return true;
  });
};

/**
 * Check if a route is accessible in current edition
 * @param {string} path - Route path
 * @returns {boolean}
 */
export const isRouteAccessible = (path) => {
  if (isEnterpriseEdition()) {
    return true; // All routes accessible in enterprise
  }
  
  // Define CE-accessible routes
  const ceRoutes = [
    '/',
    '/login',
    '/logout',
    '/register',
    '/dashboard',
    '/chat',
    '/honey-jars',
    '/reports',
    '/settings',
    '/admin',
    '/enrollment',
    '/aal2-step-up'
  ];
  
  // Check if route is in CE whitelist
  return ceRoutes.some(route => path.startsWith(route));
};

// Initialize configuration on module load
if (typeof window !== 'undefined') {
  loadEditionConfig().catch(console.error);
}

export default {
  loadEditionConfig,
  getEditionType,
  isCommunityEdition,
  isEnterpriseEdition,
  isEnterpriseFeatureEnabled,
  shouldHideEnterpriseUI,
  getEnterprisePlaceholderText,
  getEnterprisePlaceholderLink,
  filterNavigationByEdition,
  isRouteAccessible
};