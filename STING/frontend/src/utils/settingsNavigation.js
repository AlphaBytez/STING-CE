/**
 * Settings Navigation Utilities
 * 
 * Handles proper navigation within the settings page and ensures users
 * return to the correct tab after credential operations like passkey setup.
 */

/**
 * Get the current settings URL with tab parameter
 * @param {string} tab - The tab to navigate to
 * @returns {string} The settings URL with tab parameter
 */
export const getSettingsUrl = (tab = 'profile') => {
  const baseUrl = '/dashboard/settings';
  const params = new URLSearchParams();
  params.set('tab', tab);
  return `${baseUrl}?${params.toString()}`;
};

/**
 * Navigate to a specific settings tab
 * @param {function} navigate - React Router navigate function
 * @param {string} tab - The tab to navigate to
 * @param {object} options - Additional navigation options
 */
export const navigateToSettingsTab = (navigate, tab = 'profile', options = {}) => {
  const url = getSettingsUrl(tab);
  navigate(url, options);
};

/**
 * Store the current settings tab in session storage for return navigation
 * @param {string} tab - The current tab
 */
export const storeCurrentSettingsTab = (tab) => {
  sessionStorage.setItem('settings_current_tab', tab);
};

/**
 * Get the stored settings tab from session storage
 * @returns {string|null} The stored tab or null if none exists
 */
export const getStoredSettingsTab = () => {
  return sessionStorage.getItem('settings_current_tab');
};

/**
 * Clear the stored settings tab from session storage
 */
export const clearStoredSettingsTab = () => {
  sessionStorage.removeItem('settings_current_tab');
};

/**
 * Handle post-credential operation navigation
 * This ensures users return to the settings page after completing
 * credential setup operations (like passkey or TOTP setup)
 * 
 * @param {function} navigate - React Router navigate function
 * @param {string} defaultTab - Default tab if no stored tab exists
 */
export const handlePostCredentialNavigation = (navigate, defaultTab = 'security') => {
  const storedTab = getStoredSettingsTab();
  const targetTab = storedTab || defaultTab;
  
  // Clear the stored tab since we're navigating back
  clearStoredSettingsTab();
  
  // Navigate to the settings page with the appropriate tab
  navigateToSettingsTab(navigate, targetTab, { replace: true });
};

/**
 * Check if the current URL is a Kratos settings flow URL
 * @param {string} url - The URL to check
 * @returns {boolean} True if it's a Kratos settings flow URL
 */
export const isKratosSettingsUrl = (url) => {
  return url.includes('/.ory/') || 
         url.includes('kratos') || 
         url.includes('self-service/settings/browser') ||
         url.includes('flow=');
};

/**
 * Prevent navigation to Kratos settings URLs and redirect to proper settings
 * @param {function} navigate - React Router navigate function
 * @param {string} url - The URL being navigated to
 * @param {string} fallbackTab - The tab to fall back to
 * @returns {boolean} True if navigation was prevented
 */
export const preventKratosNavigation = (navigate, url, fallbackTab = 'security') => {
  if (isKratosSettingsUrl(url)) {
    console.log('🔐 Preventing navigation to Kratos URL, redirecting to settings:', url);
    handlePostCredentialNavigation(navigate, fallbackTab);
    return true;
  }
  return false;
};

/**
 * Setup global navigation prevention for Kratos URLs
 * Call this in a useEffect to prevent unwanted redirects
 * 
 * @param {function} navigate - React Router navigate function
 * @param {string} fallbackTab - The tab to redirect to if Kratos URL is detected
 * @returns {function} Cleanup function to remove event listeners
 */
export const setupGlobalNavigationPrevention = (navigate, fallbackTab = 'security') => {
  const originalPushState = window.history.pushState;
  const originalReplaceState = window.history.replaceState;
  
  // Override history methods to prevent Kratos redirects
  window.history.pushState = function(state, title, url) {
    if (url && preventKratosNavigation(navigate, url, fallbackTab)) {
      return;
    }
    return originalPushState.call(this, state, title, url);
  };
  
  window.history.replaceState = function(state, title, url) {
    if (url && preventKratosNavigation(navigate, url, fallbackTab)) {
      return;
    }
    return originalReplaceState.call(this, state, title, url);
  };
  
  // Return cleanup function
  return () => {
    window.history.pushState = originalPushState;
    window.history.replaceState = originalReplaceState;
  };
};