/**
 * Tiered Authentication Utilities
 * Handles operation-specific authentication checks for STING's tiered security model
 */

/**
 * Security Tiers:
 * Tier 1: View operations (no auth required)
 * Tier 2: Modify operations (1 strong factor: webauthn OR totp)
 * Tier 3: Remove operations (2 factors: primary + secondary verification)
 * Tier 4: Critical operations (all factors: email + webauthn + totp)
 */

export const SECURITY_TIERS = {
  VIEW: 1,        // No additional auth needed
  MODIFY: 2,      // 1 strong factor (webauthn OR totp)
  REMOVE: 3,      // 2 factors (primary + secondary)
  CRITICAL: 4     // All factors (email + webauthn + totp)
};

export const TIER_CACHE_DURATION = {
  [SECURITY_TIERS.MODIFY]: 5 * 60 * 1000,    // 5 minutes
  [SECURITY_TIERS.REMOVE]: 1 * 60 * 1000,    // 1 minute
  [SECURITY_TIERS.CRITICAL]: 0               // No cache
};

export const TIER_ERROR_CODES = {
  SPECIFIC_METHOD_REQUIRED: SECURITY_TIERS.MODIFY,
  METHOD_REQUIRED: SECURITY_TIERS.MODIFY,
  PRIMARY_FACTOR_REQUIRED: SECURITY_TIERS.REMOVE,
  SECONDARY_FACTOR_REQUIRED: SECURITY_TIERS.REMOVE,
  CRITICAL_AUTH_REQUIRED: SECURITY_TIERS.CRITICAL
};

/**
 * Check if user has recent authorization for a specific security tier
 */
export const hasRecentAuth = (tier, operation = 'general') => {
  const cacheDuration = TIER_CACHE_DURATION[tier] || 0;
  if (cacheDuration === 0) return false; // No cache for critical operations

  const storageKey = `${operation}_auth_verified`;
  const recentAuth = sessionStorage.getItem(storageKey);

  if (!recentAuth) return false;

  const authTime = parseInt(recentAuth);
  const cacheExpiry = Date.now() - cacheDuration;

  return authTime > cacheExpiry;
};

/**
 * Set authorization marker for completed authentication
 */
export const setAuthMarker = (operation) => {
  sessionStorage.setItem(`${operation}_auth_verified`, Date.now().toString());
  console.log(`✅ Authorization marker set for ${operation}`);
};

/**
 * Clear authorization marker after operation completion
 */
export const clearAuthMarker = (operation) => {
  sessionStorage.removeItem(`${operation}_auth_verified`);
  sessionStorage.removeItem(`${operation}_pre_operation`);
  console.log(`🧹 Authorization marker cleared for ${operation}`);
};

/**
 * Handle authentication error and redirect to appropriate confirmation flow
 */
export const handleAuthError = (error, operation, returnUrl = null) => {
  if (!error.response || error.response.status !== 403) {
    return false; // Not an auth error
  }

  const errorCode = error.response.data?.code;
  const tier = TIER_ERROR_CODES[errorCode];

  if (!tier) {
    return false; // Not a recognized tiered auth error
  }

  console.log(`🔒 ${operation} requires Tier ${tier} authentication (${errorCode})`);

  // Set operation context for return flow
  sessionStorage.setItem(`${operation}_pre_operation`, operation);

  // Preserve current URL with query params (e.g., tab parameter)
  const currentUrl = returnUrl || (window.location.pathname + window.location.search);
  const separator = currentUrl.includes('?') ? '&' : '?';
  const redirectUrl = `/security-upgrade?reason=${encodeURIComponent(operation)}&tier=${tier}&return_to=${encodeURIComponent(currentUrl + separator + 'preauth=complete')}`;

  window.location.href = redirectUrl;
  return true; // Handled
};

/**
 * Check if user just returned from authentication
 */
export const handleReturnFromAuth = (operation) => {
  const urlParams = new URLSearchParams(window.location.search);
  const preAuthComplete = urlParams.get('preauth');

  if (preAuthComplete === 'complete') {
    console.log(`🎉 User returned from successful authentication for ${operation}`);

    // Set authorization marker
    setAuthMarker(operation);

    // Clean up URL
    window.history.replaceState({}, '', window.location.pathname);

    return true; // User just completed auth
  }

  return false; // Normal page load
};

/**
 * Enhanced operation context storage and retrieval
 */
export const storeOperationContext = (operation, context = {}) => {
  const operationData = {
    operation,
    context,
    timestamp: Date.now(),
    url: window.location.pathname + window.location.search  // Include query params
  };
  sessionStorage.setItem(`${operation}_context`, JSON.stringify(operationData));
  console.log(`💾 Stored context for ${operation}:`, context);
};

export const getStoredOperationContext = (operation) => {
  const stored = sessionStorage.getItem(`${operation}_context`);
  if (!stored) return null;

  try {
    const data = JSON.parse(stored);
    // Clear the stored context after retrieval
    sessionStorage.removeItem(`${operation}_context`);
    console.log(`📤 Retrieved context for ${operation}:`, data.context);
    return data.context;
  } catch (e) {
    console.error('Failed to parse stored operation context:', e);
    return null;
  }
};

/**
 * Check if an operation should be automatically retried after authentication
 */
export const shouldRetryOperation = (operation) => {
  const urlParams = new URLSearchParams(window.location.search);
  const preAuthComplete = urlParams.get('preauth');
  const hasContext = sessionStorage.getItem(`${operation}_context`);

  return preAuthComplete === 'complete' && hasContext;
};

/**
 * Preemptive operation check - validates before user invests time in forms
 */
export const checkOperationAuth = async (operation, tier = SECURITY_TIERS.MODIFY, context = {}) => {
  // Check cache first
  if (hasRecentAuth(tier, operation)) {
    console.log(`✅ Recent authentication valid for ${operation} (Tier ${tier})`);
    return true;
  }

  console.log(`🔒 ${operation} requires Tier ${tier} authentication confirmation`);

  // Store operation context for retry after authentication
  storeOperationContext(operation, context);

  // Redirect for confirmation - preserve current URL with query params
  const currentUrl = window.location.pathname + window.location.search;
  const separator = currentUrl.includes('?') ? '&' : '?';
  const redirectUrl = `/security-upgrade?reason=${encodeURIComponent(operation)}&tier=${tier}&return_to=${encodeURIComponent(currentUrl + separator + 'preauth=complete')}`;

  window.location.href = redirectUrl;
  return false; // Block the operation
};

/**
 * Operation definitions for consistent messaging
 */
export const OPERATIONS = {
  // Tier 2 (Modify)
  CREATE_API_KEY: { name: 'create API key', tier: SECURITY_TIERS.MODIFY },
  EDIT_API_KEY: { name: 'edit API key', tier: SECURITY_TIERS.MODIFY },
  CHANGE_SETTINGS: { name: 'change security settings', tier: SECURITY_TIERS.MODIFY },

  // Tier 3 (Remove)
  DELETE_API_KEY: { name: 'delete API key', tier: SECURITY_TIERS.REMOVE },
  REMOVE_PASSKEY: { name: 'remove passkey', tier: SECURITY_TIERS.REMOVE },
  REMOVE_TOTP: { name: 'remove TOTP', tier: SECURITY_TIERS.REMOVE },

  // Tier 4 (Critical)
  DISABLE_ALL_2FA: { name: 'disable all 2FA', tier: SECURITY_TIERS.CRITICAL },
  DELETE_ACCOUNT: { name: 'delete account', tier: SECURITY_TIERS.CRITICAL }
};

/**
 * Convenience functions for common operations
 */
export const createApiKeyAuth = () => checkOperationAuth(OPERATIONS.CREATE_API_KEY.name, OPERATIONS.CREATE_API_KEY.tier);
export const deleteApiKeyAuth = () => checkOperationAuth(OPERATIONS.DELETE_API_KEY.name, OPERATIONS.DELETE_API_KEY.tier);
export const removePasskeyAuth = () => checkOperationAuth(OPERATIONS.REMOVE_PASSKEY.name, OPERATIONS.REMOVE_PASSKEY.tier);

export default {
  SECURITY_TIERS,
  OPERATIONS,
  hasRecentAuth,
  setAuthMarker,
  clearAuthMarker,
  handleAuthError,
  handleReturnFromAuth,
  checkOperationAuth,
  createApiKeyAuth,
  deleteApiKeyAuth,
  removePasskeyAuth
};