/**
 * Utility functions for Kratos session management
 * Provides consistent interface for checking authentication status using browser flows
 */

/**
 * Check the current Kratos session status
 * @param {AbortSignal} signal - Optional abort signal for timeout handling
 * @returns {Promise<{isAuthenticated: boolean, session: object|null, error: string|null}>}
 */
export const checkKratosSession = async (signal = null) => {
  try {
    const response = await fetch('/.ory/sessions/whoami', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      signal
    });

    if (response.ok) {
      const session = await response.json();
      return {
        isAuthenticated: true,
        session,
        error: null
      };
    } else if (response.status === 401) {
      // Not authenticated - this is a normal state
      return {
        isAuthenticated: false,
        session: null,
        error: null
      };
    } else {
      // Other error
      return {
        isAuthenticated: false,
        session: null,
        error: `Session check failed with status: ${response.status}`
      };
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      return {
        isAuthenticated: false,
        session: null,
        error: 'Session check timeout'
      };
    }
    
    return {
      isAuthenticated: false,
      session: null,
      error: error.message
    };
  }
};

/**
 * Get user email from Kratos session
 * @returns {Promise<string|null>}
 */
export const getUserEmail = async () => {
  const { session } = await checkKratosSession();
  return session?.identity?.traits?.email || null;
};

/**
 * Get user role from Kratos session
 * @returns {Promise<string>}
 */
export const getUserRole = async () => {
  const { session } = await checkKratosSession();
  const role = session?.identity?.traits?.role;
  
  if (role === 'super_admin') return 'super_admin';
  if (role === 'admin') return 'admin';
  return 'user';
};

/**
 * Check if user has admin privileges
 * @returns {Promise<boolean>}
 */
export const isAdmin = async () => {
  const role = await getUserRole();
  return role === 'admin' || role === 'super_admin';
};

/**
 * Get AAL (Authentication Assurance Level) information from session
 * @returns {Promise<{aal: string, configuredMethods: object}>}
 */
export const getAALStatus = async () => {
  const { session } = await checkKratosSession();
  
  if (!session) {
    return {
      aal: null,
      configuredMethods: {
        totp: false,
        webauthn: false
      }
    };
  }

  const aal = session.authenticator_assurance_level || 'aal1';
  
  // Check for configured authentication methods
  const configuredMethods = {
    totp: session.identity?.credentials?.totp?.identifiers?.length > 0,
    webauthn: session.identity?.credentials?.webauthn?.identifiers?.length > 0
  };

  return {
    aal,
    configuredMethods
  };
};

/**
 * Check if user needs AAL2 step-up
 * @returns {Promise<boolean>}
 */
export const needsAAL2StepUp = async () => {
  const { aal, configuredMethods } = await getAALStatus();
  
  // If user has configured methods but is only at AAL1, they need step-up
  if (aal === 'aal1' && (configuredMethods.totp || configuredMethods.webauthn)) {
    return true;
  }
  
  return false;
};

/**
 * Get available authentication methods for AAL2
 * @returns {Promise<{totp: boolean, webauthn: boolean}>}
 */
export const getAvailableAAL2Methods = async () => {
  const { configuredMethods } = await getAALStatus();
  return configuredMethods;
};

/**
 * Create a session check with timeout
 * @param {number} timeoutMs - Timeout in milliseconds (default: 5000)
 * @returns {Promise<object>}
 */
export const checkKratosSessionWithTimeout = async (timeoutMs = 5000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const result = await checkKratosSession(controller.signal);
    clearTimeout(timeoutId);
    return result;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};

export default {
  checkKratosSession,
  checkKratosSessionWithTimeout,
  getUserEmail,
  getUserRole,
  isAdmin,
  getAALStatus,
  needsAAL2StepUp,
  getAvailableAAL2Methods
};