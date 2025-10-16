/**
 * Kratos configuration utilities
 * Handles the difference between API calls (through proxy) and browser navigation
 */

const isDevelopment = process.env.NODE_ENV === 'development';

// For API calls in development, use relative URLs to go through proxy
// For production or browser navigation, use the full Kratos URL
export const getKratosUrl = (forBrowserNavigation = false) => {
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || process.env.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Always use relative URLs for API calls to go through the proxy (nginx in production, webpack in dev)
  // Only use full URL for browser navigation (redirects)
  if (!forBrowserNavigation) {
    return ''; // Empty string means relative URLs
  }
  
  return kratosUrl;
};

// Helper to build endpoints
export const kratosApi = {
  // Session endpoints - Use Flask endpoint that coordinates Kratos + STING sessions
  whoami: () => `/api/auth/me`,
  
  // Self-service flow endpoints - BROWSER FLOWS ONLY (API flows removed to prevent misuse)
  loginBrowser: () => `${getKratosUrl(true)}/self-service/login/browser`,
  loginFlow: (flowId) => `/.ory/self-service/login/flows?id=${flowId}`,
  
  registrationBrowser: () => `${getKratosUrl(true)}/self-service/registration/browser`,
  registrationFlow: (flowId) => `/.ory/self-service/registration/flows?id=${flowId}`,
  
  logoutBrowser: () => `/.ory/self-service/logout/browser`,
  
  // Settings flow endpoints
  settingsBrowser: () => `/.ory/self-service/settings/browser`,
  settingsFlow: (flowId) => `/.ory/self-service/settings/flows?id=${flowId}`,
  
  // Health endpoints
  healthAlive: () => `/.ory/health/alive`,
  healthReady: () => `/.ory/health/ready`,
};

export default kratosApi;