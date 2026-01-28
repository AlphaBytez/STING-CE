/**
 * Enhanced WebAuthn Detection Utility
 * 
 * Provides accurate detection and user-friendly messaging for different WebAuthn scenarios:
 * - Platform authenticators (Touch ID, Face ID, Windows Hello)
 * - External passkeys (stored on Mac Studio, security keys)
 * - Proper fallback messaging for unsupported setups
 */

/**
 * Detect and categorize available WebAuthn authenticators
 * @returns {Promise<object>} Detailed authenticator information
 */
export const detectWebAuthnCapabilities = async () => {
  const result = {
    supported: false,
    hasplatformAuthenticator: false,
    hasExternalAuthenticator: false,
    conditionalUIAvailable: false,
    recommendedMethod: 'password',
    userMessage: 'Use password to sign in',
    technicalDetails: {}
  };

  // Check basic WebAuthn support
  if (!window.PublicKeyCredential) {
    result.userMessage = 'Your browser doesn\'t support modern authentication methods. Please use your password.';
    result.technicalDetails.reason = 'PublicKeyCredential API not available';
    return result;
  }

  result.supported = true;

  try {
    // Check platform authenticator availability
    const platformAvailable = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    result.hasplatformAuthenticator = platformAvailable;

    // Check conditional UI support (for passkey autofill)
    if (window.PublicKeyCredential.isConditionalMediationAvailable) {
      result.conditionalUIAvailable = await window.PublicKeyCredential.isConditionalMediationAvailable();
    }

    // Platform detection for better messaging
    const platform = detectPlatform();
    
    if (platformAvailable) {
      // User has platform authenticator (Touch ID, Face ID, etc.)
      result.recommendedMethod = 'platform_authenticator';
      result.userMessage = getPlatformAuthenticatorMessage(platform);
    } else if (result.supported) {
      // WebAuthn supported but no platform authenticator
      // This means external passkeys/security keys are possible
      result.hasExternalAuthenticator = true;
      result.recommendedMethod = 'external_passkey';
      result.userMessage = getExternalPasskeyMessage(platform);
    }

    result.technicalDetails = {
      platform,
      platformAuthenticator: platformAvailable,
      conditionalUI: result.conditionalUIAvailable,
      userAgent: navigator.userAgent
    };

  } catch (error) {
    console.warn('WebAuthn capability detection failed:', error);
    result.userMessage = 'Unable to detect authentication methods. You can try using a passkey or use your password.';
    result.technicalDetails.error = error.message;
  }

  return result;
};

/**
 * Detect the user's platform for targeted messaging
 * @returns {object} Platform information
 */
function detectPlatform() {
  const userAgent = navigator.userAgent.toLowerCase();
  
  const platform = {
    isMac: userAgent.includes('mac') && !userAgent.includes('iphone') && !userAgent.includes('ipad'),
    isWindows: userAgent.includes('windows'),
    isiOS: userAgent.includes('iphone') || userAgent.includes('ipad'),
    isAndroid: userAgent.includes('android'),
    isLinux: userAgent.includes('linux') && !userAgent.includes('android'),
    isMobile: userAgent.includes('mobile') || userAgent.includes('iphone') || userAgent.includes('ipad') || userAgent.includes('android')
  };

  // Determine primary platform
  if (platform.isMac) platform.name = 'macOS';
  else if (platform.isWindows) platform.name = 'Windows';
  else if (platform.isiOS) platform.name = 'iOS';
  else if (platform.isAndroid) platform.name = 'Android';
  else if (platform.isLinux) platform.name = 'Linux';
  else platform.name = 'Unknown';

  return platform;
}

/**
 * Get user-friendly message for platform authenticators
 * @param {object} platform - Platform detection result
 * @returns {string} User-friendly message
 */
function getPlatformAuthenticatorMessage(platform) {
  if (platform.isMac || platform.isiOS) {
    return 'You can sign in with Touch ID, Face ID, or your password';
  } else if (platform.isWindows) {
    return 'You can sign in with Windows Hello or your password';
  } else if (platform.isAndroid) {
    return 'You can sign in with your fingerprint, face unlock, or password';
  } else {
    return 'You can sign in with biometric authentication or your password';
  }
}

/**
 * Get user-friendly message for external passkeys
 * This is the key function for Mac Studio users with external passkeys
 * @param {object} platform - Platform detection result
 * @returns {string} User-friendly message
 */
function getExternalPasskeyMessage(platform) {
  if (platform.isMac) {
    return 'You can sign in with a passkey, security key, or your password';
  } else if (platform.isWindows) {
    return 'You can sign in with a passkey, security key, or your password';
  } else {
    return 'You can sign in with a passkey or your password';
  }
}

/**
 * Check if user likely has passkeys registered
 * This doesn't check actual registration but helps with UI decisions
 * @returns {Promise<boolean>} True if passkeys are likely available
 */
export const isPasskeyLikelyAvailable = async () => {
  const capabilities = await detectWebAuthnCapabilities();
  
  // Return true if any WebAuthn method is supported
  return capabilities.supported && (
    capabilities.hasplatformAuthenticator || 
    capabilities.hasExternalAuthenticator
  );
};

/**
 * Get appropriate authentication button text based on capabilities
 * @returns {Promise<object>} Button text and styling recommendations
 */
export const getAuthenticationButtonConfig = async () => {
  const capabilities = await detectWebAuthnCapabilities();
  
  if (!capabilities.supported) {
    return {
      primary: 'Sign in with Password',
      secondary: null,
      icon: 'password',
      showPasskeyOption: false
    };
  }
  
  if (capabilities.hasplatformAuthenticator) {
    const platform = capabilities.technicalDetails.platform;
    if (platform.isMac || platform.isiOS) {
      return {
        primary: 'Sign in with Touch ID',
        secondary: 'Or use password',
        icon: 'fingerprint',
        showPasskeyOption: true,
        passkeyText: 'Touch ID or Face ID'
      };
    } else if (platform.isWindows) {
      return {
        primary: 'Sign in with Windows Hello',
        secondary: 'Or use password',
        icon: 'fingerprint',
        showPasskeyOption: true,
        passkeyText: 'Windows Hello'
      };
    } else {
      return {
        primary: 'Sign in with Biometrics',
        secondary: 'Or use password',
        icon: 'fingerprint',
        showPasskeyOption: true,
        passkeyText: 'Biometric Authentication'
      };
    }
  } else if (capabilities.hasExternalAuthenticator) {
    // This is the key case for Mac Studio users
    return {
      primary: 'Sign in with Passkey',
      secondary: 'Or use password',
      icon: 'key',
      showPasskeyOption: true,
      passkeyText: 'Passkey or Security Key'
    };
  }
  
  return {
    primary: 'Sign in with Password',
    secondary: null,
    icon: 'password',
    showPasskeyOption: false
  };
};

/**
 * Validate WebAuthn support for a specific operation
 * @param {string} operation - The operation type ('login', 'registration', 'aal2')
 * @returns {Promise<object>} Validation result with recommendations
 */
export const validateWebAuthnForOperation = async (operation) => {
  const capabilities = await detectWebAuthnCapabilities();
  
  const result = {
    canProceed: false,
    recommendedFlow: 'password',
    userMessage: '',
    fallbackOptions: []
  };
  
  if (!capabilities.supported) {
    result.userMessage = 'WebAuthn not supported in this browser. Please use password authentication.';
    result.fallbackOptions = ['password'];
    return result;
  }
  
  result.canProceed = true;
  
  if (capabilities.hasplatformAuthenticator) {
    result.recommendedFlow = 'platform_webauthn';
    result.userMessage = capabilities.userMessage;
    result.fallbackOptions = ['platform_webauthn', 'password'];
  } else if (capabilities.hasExternalAuthenticator) {
    result.recommendedFlow = 'external_webauthn';
    result.userMessage = capabilities.userMessage;
    result.fallbackOptions = ['external_webauthn', 'password', 'totp'];
  } else {
    result.recommendedFlow = 'password';
    result.userMessage = 'Please use password authentication.';
    result.fallbackOptions = ['password'];
  }
  
  return result;
};