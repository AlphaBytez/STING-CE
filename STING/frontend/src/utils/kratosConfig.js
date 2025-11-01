/**
 * Kratos configuration utilities
 * Handles the difference between API calls (through proxy) and browser navigation
 * Supports dynamic URLs for Codespaces, VMs, and port forwarding scenarios
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

/**
 * Build a dynamic return URL based on the current browser location
 * This ensures redirects work in Codespaces, VMs, and other forwarded environments
 *
 * @param {string} path - The path to return to (e.g., '/dashboard', '/settings')
 * @returns {string} Full URL including the current origin
 *
 * @example
 * // Running on Codespaces: https://xxx-8443.app.github.dev
 * buildReturnUrl('/dashboard') // => 'https://xxx-8443.app.github.dev/dashboard'
 *
 * // Running locally: http://localhost:8443
 * buildReturnUrl('/dashboard') // => 'http://localhost:8443/dashboard'
 */
export const buildReturnUrl = (path = '/dashboard') => {
  // Get current origin from browser (handles Codespaces, port forwarding, etc.)
  const currentOrigin = window.location.origin;

  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  return `${currentOrigin}${normalizedPath}`;
};

/**
 * Build a flow initialization URL with dynamic return_to parameter
 *
 * @param {string} flowType - Type of flow ('login', 'registration', 'settings', etc.)
 * @param {object} options - Additional options
 * @param {string} options.returnPath - Path to return to after flow completes
 * @param {string} options.aal - AAL level for login flows (e.g., 'aal2')
 * @param {boolean} options.refresh - Whether to refresh the flow
 * @param {object} options.additionalParams - Any additional query parameters
 * @returns {string} Complete flow URL with parameters
 */
export const buildFlowUrl = (flowType, options = {}) => {
  const {
    returnPath = '/dashboard',
    aal,
    refresh,
    additionalParams = {}
  } = options;

  // Build base URL for the flow
  const baseUrl = `/.ory/self-service/${flowType}/browser`;

  // Build query parameters
  const params = new URLSearchParams();

  // Add return_to parameter with dynamic URL
  params.append('return_to', buildReturnUrl(returnPath));

  // Add AAL parameter if specified
  if (aal) {
    params.append('aal', aal);
  }

  // Add refresh parameter if specified
  if (refresh) {
    params.append('refresh', 'true');
  }

  // Add any additional parameters
  Object.entries(additionalParams).forEach(([key, value]) => {
    params.append(key, value);
  });

  return `${baseUrl}?${params.toString()}`;
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