/**
 * Authentication Method Preference Service
 * Implements industry-standard authentication method hierarchy following GitHub/AWS patterns
 * 
 * Preference Order:
 * 1. Passkey (WebAuthn) - Most secure, frictionless when available
 * 2. TOTP - Reliable fallback, works across devices
 * 3. Recovery Codes - Emergency access method
 * 
 * Handles smart method selection, fallback logic, and user experience optimization
 */

import axios from 'axios';
import securityGateService from './securityGateService';

class AuthMethodPreferenceService {
  constructor() {
    this.preferenceCache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    
    // Default preference hierarchy (industry standard)
    this.defaultHierarchy = ['passkey', 'totp', 'recovery_codes'];
    
    // User preference storage key
    this.preferenceKey = 'auth_method_preference';
  }

  /**
   * Get the preferred authentication method for a user during login
   * @param {Object} user - User object
   * @param {Object} availableMethods - Methods available in current flow
   * @param {Object} userMethods - Methods user has configured
   * @returns {Object} Preferred method configuration
   */
  async getPreferredMethod(user, availableMethods = {}, userMethods = {}) {
    try {
      // Get user's configured methods
      const configuredMethods = await this.getUserConfiguredMethods(user);
      
      // Get user's preference if they've set one
      const userPreference = this.getUserPreference();
      
      // Determine the best method based on:
      // 1. User preference (if valid and available)
      // 2. Method reliability context
      // 3. Default hierarchy
      const recommendation = this.calculateMethodPreference({
        configured: configuredMethods,
        available: availableMethods,
        userPreference,
        context: this.getAuthContext()
      });

      console.log('🎯 Auth Method Preference:', {
        configured: configuredMethods,
        available: availableMethods,
        userPreference,
        recommendation
      });

      return recommendation;
      
    } catch (error) {
      console.error('Error getting preferred method:', error);
      
      // Fallback to basic preference
      return {
        primary: availableMethods.passkey ? 'passkey' : 'totp',
        fallback: availableMethods.totp ? 'totp' : 'recovery_codes',
        reason: 'API error - using basic fallback'
      };
    }
  }

  /**
   * Calculate method preference based on multiple factors
   * @private
   */
  calculateMethodPreference({ configured, available, userPreference, context }) {
    const methods = [];
    
    // Start with user's explicit preference if valid
    if (userPreference && configured[userPreference] && available[userPreference]) {
      methods.push({
        method: userPreference,
        reason: 'user_preference',
        priority: 1
      });
    }
    
    // Add methods by hierarchy, considering context
    for (const method of this.defaultHierarchy) {
      if (!configured[method] || !available[method]) continue;
      if (methods.some(m => m.method === method)) continue; // Already added
      
      let priority = this.getMethodPriority(method, context);
      let reason = this.getMethodReason(method, context);
      
      methods.push({ method, reason, priority });
    }
    
    // Sort by priority (lower number = higher priority)
    methods.sort((a, b) => a.priority - b.priority);
    
    const primary = methods[0];
    const fallback = methods[1];
    
    return {
      primary: primary?.method || 'totp',
      fallback: fallback?.method || 'recovery_codes',
      reasoning: {
        primary: primary?.reason || 'default',
        fallback: fallback?.reason || 'default'
      },
      allOptions: methods,
      shouldPromptUserChoice: this.shouldPromptUserChoice(methods),
      contextualMessage: this.getContextualMessage(primary, context)
    };
  }

  /**
   * Get method priority based on context
   * @private
   */
  getMethodPriority(method, context) {
    const basePriorities = {
      passkey: 1,
      totp: 2,
      recovery_codes: 3
    };
    
    let priority = basePriorities[method] || 999;
    
    // Adjust priority based on context
    if (context.isServiceUpdate && method === 'totp') {
      // TOTP is more reliable during service updates
      priority -= 0.5;
    }
    
    if (context.isHighSecurity && method === 'passkey') {
      // Passkeys preferred for high-security operations
      priority -= 0.3;
    }
    
    if (context.isMobileDevice && method === 'passkey') {
      // Passkeys work great on mobile
      priority -= 0.2;
    }
    
    return priority;
  }

  /**
   * Get reason for method selection
   * @private
   */
  getMethodReason(method, context) {
    if (context.isServiceUpdate && method === 'totp') {
      return 'reliable_during_updates';
    }
    
    if (context.isHighSecurity && method === 'passkey') {
      return 'enhanced_security';
    }
    
    return {
      passkey: 'most_secure_frictionless',
      totp: 'reliable_cross_device',
      recovery_codes: 'emergency_access'
    }[method] || 'default';
  }

  /**
   * Determine if we should prompt user to choose method
   * @private
   */
  shouldPromptUserChoice(methods) {
    // Prompt if user has multiple strong methods and no preference set
    const strongMethods = methods.filter(m => 
      ['passkey', 'totp'].includes(m.method)
    );
    
    return strongMethods.length > 1 && !this.getUserPreference();
  }

  /**
   * Get contextual message for the user
   * @private
   */
  getContextualMessage(primaryMethod, context) {
    if (!primaryMethod) return null;
    
    const messages = {
      passkey: {
        default: "Sign in securely with your passkey",
        enhanced_security: "Use your passkey for the highest security",
        mobile_optimized: "Quick sign-in with your passkey"
      },
      totp: {
        default: "Enter code from your authenticator app",
        reliable_during_updates: "TOTP is recommended during service updates",
        cross_device: "Works on any device with your authenticator app"
      },
      recovery_codes: {
        default: "Use a recovery code for emergency access",
        emergency_access: "Emergency access with recovery code"
      }
    };
    
    const methodMessages = messages[primaryMethod.method] || {};
    return methodMessages[primaryMethod.reason] || methodMessages.default;
  }

  /**
   * Get current authentication context
   * @private
   */
  getAuthContext() {
    return {
      isServiceUpdate: this.detectServiceUpdate(),
      isHighSecurity: this.detectHighSecurityContext(),
      isMobileDevice: this.detectMobileDevice(),
      timestamp: Date.now()
    };
  }

  /**
   * Detect if we're in a service update period
   * @private
   */
  detectServiceUpdate() {
    // Check if there's a service update indicator
    // This could be from server headers, localStorage flag, etc.
    return localStorage.getItem('service_update_mode') === 'true' ||
           sessionStorage.getItem('webauthn_unreliable') === 'true';
  }

  /**
   * Detect high-security context
   * @private
   */
  detectHighSecurityContext() {
    // Check URL paths that indicate high-security operations
    const sensitivePages = [
      '/admin',
      '/settings/security',
      '/reports',
      '/honey-reserve'
    ];
    
    return sensitivePages.some(page => window.location.pathname.includes(page));
  }

  /**
   * Detect mobile device
   * @private
   */
  detectMobileDevice() {
    return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Get user's configured authentication methods
   * @private
   */
  async getUserConfiguredMethods(user) {
    try {
      // Use SecurityGateService to get current methods
      const [passkeyStatus, totpStatus] = await Promise.all([
        securityGateService.getPasskeyStatus(),
        securityGateService.getTOTPStatus()
      ]);
      
      return {
        passkey: passkeyStatus.hasPasskey,
        totp: totpStatus.hasTOTP,
        recovery_codes: true // Assume recovery codes are always available
      };
      
    } catch (error) {
      console.warn('Failed to get user methods:', error);
      return {
        passkey: false,
        totp: false,
        recovery_codes: true
      };
    }
  }

  /**
   * Get user's saved preference
   */
  getUserPreference() {
    try {
      const saved = localStorage.getItem(this.preferenceKey);
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.warn('Failed to get user preference:', error);
      return null;
    }
  }

  /**
   * Save user's method preference
   * @param {string} method - Preferred method
   * @param {Object} context - Context for the preference
   */
  setUserPreference(method, context = {}) {
    try {
      const preference = {
        method,
        context,
        timestamp: Date.now()
      };
      
      localStorage.setItem(this.preferenceKey, JSON.stringify(preference));
      
      console.log('🎯 Saved auth method preference:', preference);
      
    } catch (error) {
      console.error('Failed to save user preference:', error);
    }
  }

  /**
   * Clear user's saved preference
   */
  clearUserPreference() {
    localStorage.removeItem(this.preferenceKey);
  }

  /**
   * Get method selection UI configuration
   * @param {Object} methods - Available methods
   * @param {Object} recommendation - Method recommendation
   */
  getMethodSelectionUI(methods, recommendation) {
    const options = [];
    
    if (methods.passkey) {
      options.push({
        method: 'passkey',
        label: 'Passkey',
        description: 'Most secure and convenient',
        icon: '🔐',
        isPrimary: recommendation.primary === 'passkey',
        onClick: () => this.selectMethod('passkey')
      });
    }
    
    if (methods.totp) {
      options.push({
        method: 'totp',
        label: 'Authenticator App',
        description: 'Reliable across all devices',
        icon: '📱',
        isPrimary: recommendation.primary === 'totp',
        onClick: () => this.selectMethod('totp')
      });
    }
    
    if (methods.recovery_codes) {
      options.push({
        method: 'recovery_codes',
        label: 'Recovery Code',
        description: 'Emergency access only',
        icon: '🔑',
        isPrimary: recommendation.primary === 'recovery_codes',
        onClick: () => this.selectMethod('recovery_codes')
      });
    }
    
    return {
      options,
      recommendation,
      showChoice: recommendation.shouldPromptUserChoice
    };
  }

  /**
   * Handle method selection
   * @param {string} method - Selected method
   */
  selectMethod(method) {
    // Save as user preference for future logins
    this.setUserPreference(method, {
      selectedAt: Date.now(),
      context: this.getAuthContext()
    });
    
    // Trigger method selection event
    window.dispatchEvent(new CustomEvent('authMethodSelected', {
      detail: { method }
    }));
    
    console.log('🎯 User selected auth method:', method);
  }

  /**
   * Clear method selection cache
   */
  clearCache() {
    this.preferenceCache.clear();
  }
}

// Export singleton instance
export default new AuthMethodPreferenceService();