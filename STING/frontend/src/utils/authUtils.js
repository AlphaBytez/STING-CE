/**
 * Authentication utility functions for handling passkeys and authentication methods
 */

/**
 * Comprehensive check for WebAuthn authenticator capabilities
 * Properly distinguishes between platform and external authenticators
 * @returns {Promise<object>} Detailed authenticator support information
 */
export const getAuthenticatorCapabilities = async () => {
  const capabilities = {
    webAuthnSupported: false,
    platformAuthenticator: false,
    externalAuthenticator: false,
    conditionalUI: false,
    userFriendlyName: 'Password',
    description: 'Standard password authentication'
  };

  try {
    if (!window.PublicKeyCredential) {
      console.log('WebAuthn API not supported in this browser');
      return capabilities;
    }

    capabilities.webAuthnSupported = true;

    // Check for platform authenticator (Touch ID, Face ID, Windows Hello)
    try {
      capabilities.platformAuthenticator = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch (err) {
      console.warn('Platform authenticator check failed:', err);
      capabilities.platformAuthenticator = false;
    }

    // Check for conditional UI (passkey autofill)
    try {
      capabilities.conditionalUI = await window.PublicKeyCredential.isConditionalMediationAvailable?.() || false;
    } catch (err) {
      console.warn('Conditional UI check failed:', err);
      capabilities.conditionalUI = false;
    }

    // Determine user-friendly naming based on platform
    const userAgent = navigator.userAgent.toLowerCase();
    const isMac = userAgent.includes('mac');
    const isWindows = userAgent.includes('windows');
    const isiOS = userAgent.includes('iphone') || userAgent.includes('ipad');
    const isAndroid = userAgent.includes('android');

    if (capabilities.platformAuthenticator) {
      if (isMac || isiOS) {
        capabilities.userFriendlyName = 'Touch ID or Face ID';
        capabilities.description = 'Use your device\'s biometric authentication';
      } else if (isWindows) {
        capabilities.userFriendlyName = 'Windows Hello';
        capabilities.description = 'Use Windows Hello biometric authentication';
      } else if (isAndroid) {
        capabilities.userFriendlyName = 'Biometric Authentication';
        capabilities.description = 'Use your device\'s fingerprint or face unlock';
      } else {
        capabilities.userFriendlyName = 'Platform Authenticator';
        capabilities.description = 'Use your device\'s built-in authentication';
      }
    } else if (capabilities.webAuthnSupported) {
      // WebAuthn supported but no platform authenticator = external passkeys/security keys
      capabilities.externalAuthenticator = true;
      capabilities.userFriendlyName = 'Passkey or Security Key';
      capabilities.description = 'Use a passkey or external security key';
    }

    console.log('Authenticator capabilities:', capabilities);
    return capabilities;
  } catch (err) {
    console.error(`Error checking authenticator capabilities: ${err.message}`);
    return capabilities;
  }
};

/**
 * Legacy function for backward compatibility
 * @returns {Promise<boolean>} True if any WebAuthn authenticator is available
 */
export const isPasskeySupported = async () => {
  const capabilities = await getAuthenticatorCapabilities();
  return capabilities.webAuthnSupported && (capabilities.platformAuthenticator || capabilities.externalAuthenticator);
};

/**
 * Check if SSO should be used based on email domain
 * Add your organization's SSO domains here
 * @param {string} email - User email address
 * @returns {object} Authentication method details
 */
export const checkAuthMethodByEmail = (email) => {
  if (!email || !email.includes('@')) {
    return {
      preferredMethod: 'password',
      ssoAvailable: false,
      passkey: false,
      message: 'Enter your email to continue'
    };
  }
  
  const domain = email.split('@')[1].toLowerCase();
  
  // Configure your organization's SSO domains here
  const ssoConfigurations = {
    'company.com': { method: 'sso', provider: 'generic' },
    'google-domain.com': { method: 'sso', provider: 'google' },
    'microsoft-domain.com': { method: 'sso', provider: 'microsoft' },
    'okta-domain.com': { method: 'sso', provider: 'okta' },
  };
  
  // Check if domain is in SSO list
  if (domain in ssoConfigurations) {
    const config = ssoConfigurations[domain];
    return {
      preferredMethod: config.method,
      provider: config.provider,
      ssoAvailable: true,
      message: `Single Sign-On available for ${domain}`
    };
  }
  
  // Check for LDAP domains
  const ldapDomains = ['internal-ldap.com', 'ldap-company.org'];
  if (ldapDomains.includes(domain)) {
    return {
      preferredMethod: 'ldap',
      ssoAvailable: false,
      message: 'LDAP authentication required'
    };
  }
  
  // Default to passkey if supported, otherwise password
  return {
    preferredMethod: 'passkey',
    ssoAvailable: false,
    message: 'You can use a passkey or password'
  };
};

/**
 * Stores the authentication method in session storage
 * @param {string} method - Authentication method (passkey, password, sso, ldap)
 */
export const setPreferredAuthMethod = (method) => {
  sessionStorage.setItem('preferredAuthMethod', method);
};

/**
 * Gets the stored authentication method from session storage
 * @returns {string} Authentication method or null if not set
 */
export const getPreferredAuthMethod = () => {
  return sessionStorage.getItem('preferredAuthMethod');
};

/**
 * Determines if email is already registered (mock implementation)
 * In a real application, this would make an API call to check
 * @param {string} email - Email to check
 * @returns {Promise<boolean>} Whether the email is registered
 */
export const isEmailRegistered = async (email) => {
  // This is a mock implementation
  // In a real app, you would make an API call to check if the email is registered
  
  try {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Mock list of registered emails
    const registeredEmails = [
      'test@example.com',
      'admin@company.com',
      'user@domain.com'
    ];
    
    return registeredEmails.includes(email.toLowerCase());
  } catch (error) {
    console.error('Error checking email registration:', error);
    return false;
  }
};