/**
 * Security Gate Service
 * Handles dashboard-gate security enforcement for progressive authentication
 * 
 * Flow: Email Verification → Dashboard Access → Security Setup → Full Access
 */

import axios from 'axios';

class SecurityGateService {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    this.lastCheck = new Map(); // Track last check times per user
    this.debounceTime = 3000; // 3 seconds debounce
  }

  /**
   * Check if user meets security requirements for dashboard access
   * @param {Object} user - User object with role, email, etc.
   * @returns {Promise<Object>} Security status with requirements and recommendations
   */
  async checkSecurityStatus(user) {
    if (!user?.email) {
      return {
        meetsRequirements: false,
        reason: 'No user data available',
        redirectTo: '/login',
        currentMethods: {
          passkey: false,
          totp: false,
          email: false
        }
      };
    }

    // Check cache first
    const cacheKey = `security_${user.email}`;
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }

    // 🚨 DEBOUNCE: Prevent excessive API calls (except for critical AAL2 flows)
    const lastCheckTime = this.lastCheck.get(user.email) || 0;
    const now = Date.now();
    const isAAL2Check = window.location.pathname === '/aal2';
    
    if (now - lastCheckTime < this.debounceTime && !isAAL2Check) {
      // Return cached result or a basic fallback during debounce
      if (cached) {
        return cached.data;
      }
      // Return loading state during debounce - don't make security decisions
      return {
        isLoading: true,  // ← This prevents AAL2 logic from running
        reason: 'Debouncing security check',
        message: 'Security verification in progress...',
        currentMethods: {
          passkey: false,
          totp: false,
          email: true
        }
      };
    }
    this.lastCheck.set(user.email, now);

    try {
      // Get user's current authentication methods
      const [passkeyStatus, totpStatus, aalStatus] = await Promise.all([
        this.getPasskeyStatus(),
        this.getTOTPStatus(),
        this.getAALStatus()
      ]);

      // Minimal logging to prevent console flooding
      console.log('🔍 SecurityGate Check:', {
        email: user.email,
        role: user.role,
        hasPasskey: passkeyStatus.hasPasskey,
        hasTOTP: totpStatus.hasTOTP
      });

      const status = this.analyzeSecurityStatus({
        user,
        passkeyStatus,
        totpStatus,
        aalStatus
      });

      // Cache the result
      this.cache.set(cacheKey, {
        data: status,
        timestamp: Date.now()
      });

      return status;

    } catch (error) {
      console.error('🔒 SecurityGate: Error checking security status:', error);
      
      // Graceful degradation - allow access but recommend setup
      return {
        meetsRequirements: false,
        hasWarnings: true,
        reason: 'Could not verify security methods - API errors detected',
        message: 'Unable to verify your security configuration. Please set up authentication methods below.',
        actionText: 'Set Up Security Methods',
        urgency: 'medium',
        requiredMethods: user.role === 'admin' ? ['passkey OR totp'] : ['optional'],
        currentMethods: {
          passkey: false, // Unknown due to API error
          totp: false,    // Unknown due to API error  
          email: true
        },
        redirectTo: '/dashboard/settings/security', // API error fallback
        allowDismiss: user.role !== 'admin',
        gracePeriod: 7
      };
    }
  }

  /**
   * Analyze user's security status based on role and configured methods
   * @private
   */
  analyzeSecurityStatus({ user, passkeyStatus, totpStatus, aalStatus }) {
    const isAdmin = user.role === 'admin';
    const hasPasskey = passkeyStatus.hasPasskey;
    const hasTOTP = totpStatus.hasTOTP;
    const emailVerified = user.email_verified !== false; // Default to true if not specified

    // Base requirements
    let requiredMethods = [];
    let recommendedMethods = [];
    let gracePeriod = isAdmin ? 3 : 7; // days
    
    // UNIVERSAL 3-FACTOR SECURITY MODEL: All users need redundant authentication
    // Email (always required) + Passkey (primary) + Hardware Key OR TOTP (backup)
    // This prevents lockouts while maintaining strong security for everyone
    
    // ALL USERS: Require passkey AND (hardware key OR TOTP) for complete security
    requiredMethods = ['passkey AND (hardware key OR totp)'];
    
    // Build recommendation list based on what's missing
    if (!hasPasskey) recommendedMethods.push('passkey');
    if (!hasTOTP) recommendedMethods.push('hardware key OR totp');
    
    // Note: hasPasskey includes both regular passkeys and hardware keys via WebAuthn

    // Check if requirements are met - PROGRESSIVE SECURITY MODEL
    // Users need at least ONE strong auth method to access dashboard
    // Full security (both methods) is encouraged but not required for basic access
    const meetsRequirements = hasPasskey || hasTOTP;  // Either method sufficient for access
    
    // Determine the type of security issue
    const hasAnyMethods = hasPasskey || hasTOTP;
    const needsSetup = !hasAnyMethods; // No methods configured
    const needsAAL2 = hasAnyMethods && !meetsRequirements; // Has methods but needs step-up
    
    // Only log when requirements are not met to reduce console noise
    if (!meetsRequirements) {
      console.log('🔍 SecurityGate Analysis:', {
        isAdmin,
        hasPasskey,
        hasTOTP,
        meetsRequirements,
        requiredMethods
      });
    }

    // Determine messaging and actions
    let message, actionText, urgency;
    
    if (!emailVerified) {
      return {
        meetsRequirements: false,
        reason: 'Email verification required',
        message: 'Please verify your email address to access dashboard features',
        actionText: 'Verify Email',
        redirectTo: '/verification',
        urgency: 'high'
      };
    }

    if (!meetsRequirements) {
      // UNIVERSAL 3-FACTOR SECURITY MODEL: All users need complete security setup
      if (!hasPasskey && !hasTOTP) {
        message = '🔒 Complete security setup required: Set up a passkey (Face ID/Touch ID) AND choose a backup method (hardware key 🔑 or TOTP app 📱) for secure access.';
      } else if (hasPasskey && !hasTOTP) {
        message = '🔒 Almost there! You have a passkey ✅ Now add a backup method: Use a hardware key 🔑 (YubiKey, etc.) or TOTP app 📱 (Google Authenticator, etc.) to complete setup.';
      } else if (!hasPasskey && hasTOTP) {
        message = '🔒 You have a backup method ✅ Now add a passkey 🔐 (Face ID/Touch ID/Windows Hello) for convenient daily authentication.';
      } else {
        message = '🔒 Security setup appears incomplete. Please ensure both passkey and backup method (hardware key or TOTP) are properly configured.';
      }
      // Universal return object for all users
      return {
        meetsRequirements: false,
        reason: 'Universal 3-factor security setup required',
        message,
        actionText,
        urgency,
        requiredMethods,
        recommendedMethods,
        gracePeriod: isAdmin ? 0 : 3, // Admins: immediate, Users: 3 days
        currentMethods: {
          passkey: hasPasskey,
          totp: hasTOTP,
          email: true
        },
        redirectTo: '/dashboard/settings?tab=security',
        allowDismiss: false, // No dismissal for universal security requirement
        enforcementMode: 'universal', // Universal enforcement for all users
        hardwareKeySupported: true, // Indicate hardware key option availability
        suggestions: {
          primary: 'Set up Face ID/Touch ID passkey for daily convenience',
          backup: 'Add hardware key (YubiKey) or TOTP app as secure backup',
          benefits: [
            '🔒 Never get locked out (redundant authentication)',
            '⚡ Fast daily login with passkey',
            '🌍 Hardware keys work on any device, anywhere',
            '📱 TOTP apps work offline'
          ]
        }
      }
    }

    // Requirements met - check for recommendations
    if (recommendedMethods.length > 0) {
      return {
        meetsRequirements: true,
        hasRecommendations: true,
        message: isAdmin 
          ? `Admin account meets security requirements with ${this.formatMethods(hasPasskey, hasTOTP)}. Consider adding the other method as backup.`
          : 'Consider adding an authenticator app as backup for enhanced security.',
        recommendedMethods,
        gracePeriod,
        currentMethods: {
          passkey: hasPasskey,
          totp: hasTOTP,
          email: true
        }
      };
    }

    // Fully compliant
    return {
      meetsRequirements: true,
      reason: 'All security requirements met',
      message: isAdmin 
        ? `Admin account fully secured with ${this.formatMethods(hasPasskey, hasTOTP)} (industry standard).`
        : 'Account secured with strong authentication methods.',
      currentMethods: {
        passkey: hasPasskey,
        totp: hasTOTP,
        email: true
      }
    };
  }

  /**
   * Get passkey status for current user
   * @private
   */
  async getPasskeyStatus() {
    try {
      // Use Flask coordination endpoint that provides structured auth_methods
      const response = await axios.get('/api/auth/me');
      const userData = response.data;
      
      // Check auth_methods from Flask/Kratos coordination (correct structure)
      const authMethods = userData?.user?.auth_methods || {};
      const hasPasskey = !!authMethods.webauthn;
      const passkeyCount = authMethods.passkeys?.length || 0;
      
      console.log('🔍 SecurityGate: Passkey detection via Kratos:', {
        hasPasskey,
        passkeyCount,
        authMethods: authMethods
      });
      
      return { 
        hasPasskey, 
        passkeyCount, 
        passkeys: authMethods.passkeys || []
      };
    } catch (error) {
      console.error('🔍 SecurityGate: Failed to check passkey status:', error);
      return { hasPasskey: false, passkeyCount: 0, passkeys: [] };
    }
  }

  /**
   * Get TOTP status for current user
   * @private
   */
  async getTOTPStatus() {
    try {
      // Use Flask coordination endpoint that provides structured auth_methods
      const response = await axios.get('/api/auth/me');
      const userData = response.data;
      
      // Check auth_methods from Flask/Kratos coordination (correct structure)
      const authMethods = userData?.user?.auth_methods || {};
      const hasTOTP = !!authMethods.totp;
      
      console.log('🔍 SecurityGate: TOTP detection via Kratos:', {
        hasTOTP,
        authMethods: authMethods
      });
      
      return {
        hasTOTP,
        totpEnabled: hasTOTP
      };
    } catch (error) {
      // Suppress 401 errors to prevent console spam
      if (error.response?.status !== 401) {
        console.warn('🔍 SecurityGate: TOTP API error:', error.response?.status);
      }
      
      // Fallback: Check Kratos session directly for TOTP
      try {
        const kratosResponse = await axios.get('/api/auth/me');
        const session = kratosResponse.data;
        
        // Check if TOTP is in authentication methods (AAL2 achieved)
        const hasTOTP = session?.authentication_methods?.some(method => 
          method.method === 'totp' || method.aal === 'aal2'
        ) || session?.authenticator_assurance_level === 'aal2';
        
        // Also check localStorage flags for recent setup
        const recentSetup = localStorage.getItem('totp_setup_complete') === 'true';
        
        // Minimal logging for TOTP session check
        
        return { 
          hasTOTP: hasTOTP || recentSetup, 
          totpEnabled: hasTOTP || recentSetup 
        };
      } catch (kratosError) {
        console.warn('🔍 SecurityGate: Kratos session check failed:', kratosError);
        // Final fallback
        return { hasTOTP: false, totpEnabled: false };
      }
    }
  }

  /**
   * Get AAL status for context
   * @private
   */
  async getAALStatus() {
    try {
      const response = await axios.get('/api/auth/aal-status');
      return response.data;
    } catch (error) {
      // AAL status is optional - don't fail if unavailable
      return { aal: 'aal1', methods: [] };
    }
  }

  /**
   * Format method status for user messaging
   * @private
   */
  formatMethods(hasPasskey, hasTOTP) {
    const methods = [];
    if (hasPasskey) methods.push('passkey');
    if (hasTOTP) methods.push('authenticator app');
    
    if (methods.length === 0) return 'no security methods';
    if (methods.length === 1) return `only ${methods[0]}`;
    return methods.join(' and ');
  }

  /**
   * Clear cache for user (call after security method changes)
   * @param {string} email - User email
   */
  clearCache(email) {
    if (email) {
      this.cache.delete(`security_${email}`);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Check if user should be allowed to dismiss security setup
   * @param {Object} securityStatus - Status from checkSecurityStatus
   */
  canDismissSetup(securityStatus) {
    return securityStatus.allowDismiss === true;
  }

  /**
   * Get grace period remaining for user
   * @param {Object} user - User object
   * @param {number} gracePeriod - Grace period in days
   */
  getGracePeriodRemaining(user, gracePeriod) {
    if (!user.created_at) return gracePeriod;
    
    const createdDate = new Date(user.created_at);
    const now = new Date();
    const daysSinceCreation = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24));
    
    return Math.max(0, gracePeriod - daysSinceCreation);
  }
}

// Export singleton instance
export default new SecurityGateService();