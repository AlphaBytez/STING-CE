import axios from 'axios';

/* global PublicKeyCredential */

// Enhanced Passkey Enforcement Service with Failsafes
export class PasskeyEnforcementService {
    constructor() {
        this.kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
        this.requiredActions = [
            'ai_report_generation',
            'external_ai_access',
            'knowledge_sync',
            'sensitive_data_processing'
        ];
        this.adminBypassActions = [
            'setup_first_admin',
            'emergency_access',
            'system_recovery'
        ];
        this.fallbackMethods = ['password', 'recovery_code', 'admin_override'];
    }

    // Check if WebAuthn is supported
    async checkWebAuthnSupport() {
        try {
            if (!window.PublicKeyCredential) {
                return { supported: false, reason: 'WebAuthn API not available' };
            }

            const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            return { 
                supported: available, 
                reason: available ? 'WebAuthn supported' : 'No platform authenticator available' 
            };
        } catch (error) {
            return { supported: false, reason: `WebAuthn check failed: ${error.message}` };
        }
    }

    // Check if user has registered passkeys with enhanced error handling
    async checkPasskeyRegistration() {
        try {
            // Check for corrupted passkey data
            const passkeyData = this.validatePasskeyData();
            
            // In a real implementation, this would check with your backend
            const hasPasskey = passkeyData.isValid && localStorage.getItem('user_has_passkey') === 'true';
            
            return {
                hasPasskey,
                registeredAt: hasPasskey ? localStorage.getItem('passkey_registered_at') : null,
                lastUsed: hasPasskey ? localStorage.getItem('passkey_last_used') : null,
                isCorrupted: passkeyData.isCorrupted,
                needsRecovery: passkeyData.needsRecovery,
                canFallback: this.canUseFallbackAuth()
            };
        } catch (error) {
            console.error('Failed to check passkey registration:', error);
            return { 
                hasPasskey: false, 
                isCorrupted: true, 
                needsRecovery: true,
                canFallback: true,
                error: error.message 
            };
        }
    }

    // Validate passkey data integrity
    validatePasskeyData() {
        try {
            const hasPasskey = localStorage.getItem('user_has_passkey');
            const registeredAt = localStorage.getItem('passkey_registered_at');
            const lastUsed = localStorage.getItem('passkey_last_used');
            
            // Check for inconsistent data
            const isCorrupted = (hasPasskey === 'true' && !registeredAt) || 
                              (registeredAt && !hasPasskey);
            
            const needsRecovery = isCorrupted || 
                                (hasPasskey === 'true' && this.isPasskeyDataStale(registeredAt));
            
            return {
                isValid: !isCorrupted && hasPasskey === 'true',
                isCorrupted,
                needsRecovery
            };
        } catch (error) {
            return {
                isValid: false,
                isCorrupted: true,
                needsRecovery: true
            };
        }
    }

    // Check if passkey data is stale (older than 90 days without use)
    isPasskeyDataStale(registeredAt) {
        if (!registeredAt) return true;
        
        const registered = new Date(registeredAt);
        const lastUsed = localStorage.getItem('passkey_last_used');
        const lastUsedDate = lastUsed ? new Date(lastUsed) : registered;
        const now = new Date();
        const daysSinceLastUse = (now - lastUsedDate) / (1000 * 60 * 60 * 24);
        
        return daysSinceLastUse > 90;
    }

    // Check if fallback authentication methods are available
    canUseFallbackAuth() {
        // Check if user is admin
        const userRole = localStorage.getItem('user_role');
        const isAdmin = userRole === 'admin' || userRole === 'super_admin';
        
        // Check if system is in setup mode
        const isSetupMode = localStorage.getItem('system_setup_mode') === 'true';
        
        // Check if emergency mode is enabled
        const isEmergencyMode = localStorage.getItem('emergency_mode') === 'true';
        
        return isAdmin || isSetupMode || isEmergencyMode;
    }

    // Enhanced authentication with failsafes and fallback options
    async authenticateForAiAction(action, context = {}) {
        try {
            // Check if action has admin bypass
            if (this.adminBypassActions.includes(action)) {
                return await this.handleAdminBypass(action, context);
            }

            // Check if action requires passkey
            if (!this.requiredActions.includes(action)) {
                return { success: true, reason: 'Action does not require passkey authentication' };
            }

            // Check WebAuthn support with fallback options
            const webAuthnCheck = await this.checkWebAuthnSupport();
            if (!webAuthnCheck.supported) {
                return await this.handleWebAuthnUnsupported(action, context);
            }

            // Check passkey registration with enhanced error handling
            const passkeyCheck = await this.checkPasskeyRegistration();
            
            if (passkeyCheck.isCorrupted || passkeyCheck.needsRecovery) {
                return await this.handleCorruptedPasskey(action, context, passkeyCheck);
            }

            if (!passkeyCheck.hasPasskey) {
                return await this.handleMissingPasskey(action, context);
            }

            // Attempt WebAuthn authentication with retry logic
            const authResult = await this.performWebAuthnAuthenticationWithRetry(action, context);
            
            if (authResult.success) {
                // Update last used timestamp
                localStorage.setItem('passkey_last_used', new Date().toISOString());
                
                return {
                    success: true,
                    authenticatedAt: new Date().toISOString(),
                    action: action,
                    context: context,
                    method: 'passkey'
                };
            } else {
                // Try fallback authentication
                return await this.handleAuthenticationFailure(action, context, authResult);
            }

        } catch (error) {
            console.error('Authentication failed:', error);
            return await this.handleCriticalError(action, context, error);
        }
    }

    // Handle admin bypass for critical actions
    async handleAdminBypass(action, context) {
        const userRole = localStorage.getItem('user_role');
        const isSetupMode = localStorage.getItem('system_setup_mode') === 'true';
        
        if (action === 'setup_first_admin' || isSetupMode) {
            return {
                success: true,
                reason: 'Admin setup mode - passkey not required',
                method: 'admin_bypass',
                authenticatedAt: new Date().toISOString()
            };
        }

        if (userRole === 'super_admin' && context.emergencyOverride) {
            return {
                success: true,
                reason: 'Super admin emergency override',
                method: 'emergency_override',
                authenticatedAt: new Date().toISOString()
            };
        }

        return {
            success: false,
            error: 'Admin bypass not authorized for this action',
            suggestedAction: 'Use standard authentication'
        };
    }

    // Handle WebAuthn not supported
    async handleWebAuthnUnsupported(action, context) {
        if (this.canUseFallbackAuth()) {
            return {
                success: true,
                reason: 'WebAuthn not supported, using fallback authentication',
                method: 'fallback_auth',
                authenticatedAt: new Date().toISOString(),
                warning: 'Consider upgrading to a WebAuthn-compatible browser'
            };
        }

        return {
            success: false,
            error: 'WebAuthn not supported and no fallback available',
            suggestedAction: 'Use a modern browser with biometric authentication support',
            fallbackOptions: this.fallbackMethods
        };
    }

    // Handle corrupted passkey data
    async handleCorruptedPasskey(action, context, passkeyCheck) {
        console.warn('Corrupted passkey data detected, attempting recovery...');
        
        // Clear corrupted data
        this.clearPasskeyData();
        
        if (this.canUseFallbackAuth()) {
            return {
                success: true,
                reason: 'Corrupted passkey data cleared, using fallback authentication',
                method: 'fallback_recovery',
                authenticatedAt: new Date().toISOString(),
                warning: 'Please re-register your passkey for enhanced security'
            };
        }

        return {
            success: false,
            error: 'Passkey data corrupted and no fallback available',
            suggestedAction: 'Contact administrator for account recovery',
            recoveryOptions: ['admin_reset', 'account_recovery']
        };
    }

    // Handle missing passkey
    async handleMissingPasskey(action, context) {
        if (this.canUseFallbackAuth()) {
            return {
                success: true,
                reason: 'No passkey registered, using fallback authentication',
                method: 'fallback_auth',
                authenticatedAt: new Date().toISOString(),
                suggestion: 'Register a passkey for enhanced security'
            };
        }

        return {
            success: false,
            error: 'No passkey registered. Please register a passkey first.',
            suggestedAction: 'setup_passkey',
            canSetupNow: true
        };
    }

    // Handle authentication failure with fallback
    async handleAuthenticationFailure(action, context, authResult) {
        console.warn('Passkey authentication failed, trying fallback...', authResult.error);
        
        if (this.canUseFallbackAuth()) {
            return {
                success: true,
                reason: 'Passkey failed, using fallback authentication',
                method: 'fallback_auth',
                authenticatedAt: new Date().toISOString(),
                warning: `Passkey authentication failed: ${authResult.error}`
            };
        }

        return {
            success: false,
            error: `Authentication failed: ${authResult.error}`,
            suggestedAction: 'Try again or contact administrator',
            retryAvailable: true
        };
    }

    // Handle critical errors
    async handleCriticalError(action, context, error) {
        console.error('Critical authentication error:', error);
        
        // Emergency fallback for critical system functions
        if (this.canUseFallbackAuth() && context.emergencyAccess) {
            return {
                success: true,
                reason: 'Emergency access granted due to critical error',
                method: 'emergency_fallback',
                authenticatedAt: new Date().toISOString(),
                warning: `Critical error bypassed: ${error.message}`
            };
        }

        return {
            success: false,
            error: `Critical authentication error: ${error.message}`,
            suggestedAction: 'Contact system administrator immediately',
            isCritical: true
        };
    }

    // Enhanced WebAuthn authentication with retry logic
    async performWebAuthnAuthenticationWithRetry(action, context, maxRetries = 3) {
        let lastError = null;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`WebAuthn authentication attempt ${attempt}/${maxRetries} for action: ${action}`);
                
                const result = await this.performWebAuthnAuthentication(action, context);
                
                if (result.success) {
                    return result;
                }
                
                lastError = result.error;
                
                // Don't retry on certain errors
                if (this.isNonRetryableError(result.error)) {
                    break;
                }
                
                // Wait before retry (exponential backoff)
                if (attempt < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
                
            } catch (error) {
                lastError = error.message;
                console.warn(`WebAuthn attempt ${attempt} failed:`, error);
            }
        }
        
        return {
            success: false,
            error: `Authentication failed after ${maxRetries} attempts: ${lastError}`,
            attempts: maxRetries
        };
    }

    // Check if error should not be retried
    isNonRetryableError(error) {
        const nonRetryableErrors = [
            'User cancelled',
            'Invalid credential',
            'Credential not found',
            'Security error'
        ];
        
        return nonRetryableErrors.some(nonRetryable => 
            error.toLowerCase().includes(nonRetryable.toLowerCase())
        );
    }

    // Perform WebAuthn authentication
    async performWebAuthnAuthentication(action, context) {
        try {
            // Check if we're in a secure context
            if (!window.isSecureContext) {
                throw new Error('WebAuthn requires a secure context (HTTPS)');
            }

            // In a real implementation, this would:
            // 1. Get challenge from server
            // 2. Call navigator.credentials.get()
            // 3. Send response to server for verification
            
            // For demo purposes, we'll simulate the WebAuthn flow
            console.log(`Simulating WebAuthn authentication for action: ${action}`);
            
            // Simulate user interaction delay
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Simulate random failures for testing (10% failure rate)
            if (Math.random() < 0.1) {
                throw new Error('Simulated authentication failure');
            }
            
            // Create mock credential request options
            const publicKeyCredentialRequestOptions = {
                challenge: new Uint8Array(32),
                allowCredentials: [{
                    id: new Uint8Array(64),
                    type: 'public-key',
                    transports: ['internal', 'hybrid']
                }],
                timeout: 60000,
                userVerification: 'required',
                rpId: window.location.hostname
            };

            // In a real app, this would call navigator.credentials.get()
            // For demo, we'll simulate success
            const mockCredential = {
                id: 'mock-credential-id',
                rawId: new ArrayBuffer(64),
                response: {
                    authenticatorData: new ArrayBuffer(37),
                    clientDataJSON: new ArrayBuffer(121),
                    signature: new ArrayBuffer(70),
                    userHandle: new ArrayBuffer(64)
                },
                type: 'public-key'
            };

            // Simulate server verification
            const verificationResult = await this.verifyWebAuthnResponse(mockCredential, action, context);
            
            return verificationResult;

        } catch (error) {
            console.error('WebAuthn authentication error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Verify WebAuthn response (mock implementation)
    async verifyWebAuthnResponse(credential, action, context) {
        try {
            // In a real implementation, this would send the credential to your backend
            // for verification against the stored public key
            
            console.log('Verifying WebAuthn credential for action:', action);
            
            // Simulate server verification delay
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Validate credential before accessing properties
            if (!credential || !credential.id) {
                console.error('Invalid credential object received:', credential);
                throw new Error('WebAuthn credential validation failed: missing id property');
            }
            
            // For demo, we'll always return success
            // In reality, this would involve cryptographic verification
            return {
                success: true,
                verified: true,
                action: action,
                timestamp: new Date().toISOString(),
                credentialId: credential.id
            };

        } catch (error) {
            console.error('WebAuthn verification error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Enhanced passkey registration with comprehensive error handling
    async registerPasskey(options = {}) {
        try {
            // Pre-registration checks
            const preCheck = await this.performPreRegistrationChecks();
            if (!preCheck.canRegister) {
                return {
                    success: false,
                    error: preCheck.reason,
                    suggestedAction: preCheck.suggestedAction
                };
            }

            // Clear any existing corrupted data
            if (options.clearExisting) {
                this.clearPasskeyData();
            }

            // Attempt registration with retry logic
            const registrationResult = await this.performPasskeyRegistrationWithRetry(options);
            
            if (registrationResult.success) {
                // Store registration data
                localStorage.setItem('user_has_passkey', 'true');
                localStorage.setItem('passkey_registered_at', new Date().toISOString());
                localStorage.setItem('passkey_credential_id', registrationResult.credentialId);
                
                // Clear any emergency flags
                localStorage.removeItem('emergency_mode');
                
                return {
                    success: true,
                    registeredAt: new Date().toISOString(),
                    credentialId: registrationResult.credentialId,
                    method: 'passkey_registration'
                };
            } else {
                return await this.handleRegistrationFailure(registrationResult, options);
            }

        } catch (error) {
            console.error('Passkey registration failed:', error);
            return await this.handleRegistrationError(error, options);
        }
    }

    // Perform pre-registration checks
    async performPreRegistrationChecks() {
        // Check WebAuthn support
        const webAuthnCheck = await this.checkWebAuthnSupport();
        if (!webAuthnCheck.supported) {
            return {
                canRegister: false,
                reason: `WebAuthn not supported: ${webAuthnCheck.reason}`,
                suggestedAction: 'Use a modern browser with biometric authentication'
            };
        }

        // Check secure context
        if (!window.isSecureContext) {
            return {
                canRegister: false,
                reason: 'Passkey registration requires a secure context (HTTPS)',
                suggestedAction: 'Access the application over HTTPS'
            };
        }

        // Check for existing registration conflicts
        const existingData = this.validatePasskeyData();
        if (existingData.isCorrupted) {
            return {
                canRegister: true,
                reason: 'Existing corrupted data will be cleared',
                suggestedAction: 'Proceed with registration to fix corrupted data'
            };
        }

        return {
            canRegister: true,
            reason: 'All pre-registration checks passed'
        };
    }

    // Perform passkey registration with retry logic
    async performPasskeyRegistrationWithRetry(options, maxRetries = 2) {
        let lastError = null;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`Passkey registration attempt ${attempt}/${maxRetries}`);
                
                const result = await this.performPasskeyRegistration(options);
                
                if (result.success) {
                    return result;
                }
                
                lastError = result.error;
                
                // Don't retry on user cancellation
                if (result.error.includes('cancelled') || result.error.includes('abort')) {
                    break;
                }
                
                // Wait before retry
                if (attempt < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
                
            } catch (error) {
                lastError = error.message;
                console.warn(`Registration attempt ${attempt} failed:`, error);
            }
        }
        
        return {
            success: false,
            error: `Registration failed after ${maxRetries} attempts: ${lastError}`,
            attempts: maxRetries
        };
    }

    // Perform actual passkey registration
    async performPasskeyRegistration(options) {
        try {
            // In a real implementation, this would:
            // 1. Get registration options from server
            // 2. Call navigator.credentials.create()
            // 3. Send response to server for storage

            console.log('Simulating passkey registration...');
            
            // Simulate registration delay
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Simulate random failures for testing (5% failure rate)
            if (Math.random() < 0.05) {
                throw new Error('Simulated registration failure');
            }
            
            const credentialId = 'mock-credential-id-' + Date.now();
            
            return {
                success: true,
                credentialId: credentialId,
                registeredAt: new Date().toISOString()
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Handle registration failure
    async handleRegistrationFailure(result, options) {
        console.warn('Passkey registration failed:', result.error);
        
        // Check if we can enable emergency mode
        if (this.canUseFallbackAuth() && !options.noEmergencyMode) {
            localStorage.setItem('emergency_mode', 'true');
            
            return {
                success: true,
                reason: 'Registration failed, emergency mode enabled',
                method: 'emergency_mode',
                warning: 'Please try to register a passkey again later',
                emergencyModeEnabled: true
            };
        }

        return {
            success: false,
            error: result.error,
            suggestedAction: 'Try again or contact administrator',
            retryAvailable: true
        };
    }

    // Handle registration error
    async handleRegistrationError(error, options) {
        console.error('Critical registration error:', error);
        
        // Enable emergency mode for admins
        if (this.canUseFallbackAuth()) {
            localStorage.setItem('emergency_mode', 'true');
            
            return {
                success: true,
                reason: 'Registration error, emergency mode enabled',
                method: 'emergency_fallback',
                warning: `Registration failed: ${error.message}`,
                emergencyModeEnabled: true
            };
        }

        return {
            success: false,
            error: `Registration error: ${error.message}`,
            suggestedAction: 'Contact system administrator',
            isCritical: true
        };
    }

    // Check if specific action requires passkey
    requiresPasskey(action) {
        return this.requiredActions.includes(action);
    }

    // Get passkey status for UI display
    async getPasskeyStatus() {
        const webAuthnSupport = await this.checkWebAuthnSupport();
        const passkeyRegistration = await this.checkPasskeyRegistration();
        
        return {
            webAuthnSupported: webAuthnSupport.supported,
            webAuthnReason: webAuthnSupport.reason,
            hasPasskey: passkeyRegistration.hasPasskey,
            registeredAt: passkeyRegistration.registeredAt,
            lastUsed: passkeyRegistration.lastUsed,
            requiredActions: this.requiredActions
        };
    }

    // Enhanced passkey data management
    clearPasskeyData() {
        localStorage.removeItem('user_has_passkey');
        localStorage.removeItem('passkey_registered_at');
        localStorage.removeItem('passkey_last_used');
        localStorage.removeItem('passkey_credential_id');
        console.log('Passkey data cleared');
    }

    // Emergency recovery methods
    enableEmergencyMode(reason = 'Manual activation') {
        localStorage.setItem('emergency_mode', 'true');
        localStorage.setItem('emergency_mode_reason', reason);
        localStorage.setItem('emergency_mode_enabled_at', new Date().toISOString());
        console.warn('Emergency mode enabled:', reason);
    }

    disableEmergencyMode() {
        localStorage.removeItem('emergency_mode');
        localStorage.removeItem('emergency_mode_reason');
        localStorage.removeItem('emergency_mode_enabled_at');
        console.log('Emergency mode disabled');
    }

    isEmergencyModeActive() {
        return localStorage.getItem('emergency_mode') === 'true';
    }

    // Admin setup helpers
    enableSetupMode() {
        localStorage.setItem('system_setup_mode', 'true');
        localStorage.setItem('setup_mode_enabled_at', new Date().toISOString());
        console.log('System setup mode enabled');
    }

    disableSetupMode() {
        localStorage.removeItem('system_setup_mode');
        localStorage.removeItem('setup_mode_enabled_at');
        console.log('System setup mode disabled');
    }

    isSetupModeActive() {
        return localStorage.getItem('system_setup_mode') === 'true';
    }

    // Complete first admin setup
    async completeFirstAdminSetup(adminData) {
        try {
            // Enable setup mode temporarily
            this.enableSetupMode();
            
            // Store admin role
            localStorage.setItem('user_role', 'super_admin');
            localStorage.setItem('user_id', adminData.userId || 'admin');
            localStorage.setItem('first_admin_setup_completed', 'true');
            
            // Try to register passkey, but don't fail if it doesn't work
            const passkeyResult = await this.registerPasskey({ 
                clearExisting: true,
                noEmergencyMode: false 
            });
            
            // Disable setup mode
            this.disableSetupMode();
            
            return {
                success: true,
                adminSetupCompleted: true,
                passkeyRegistered: passkeyResult.success,
                passkeyError: passkeyResult.success ? null : passkeyResult.error,
                fallbackEnabled: !passkeyResult.success,
                method: passkeyResult.success ? 'passkey' : 'fallback'
            };
            
        } catch (error) {
            console.error('First admin setup failed:', error);
            
            // Enable emergency mode as fallback
            this.enableEmergencyMode('First admin setup failure');
            
            return {
                success: true,
                adminSetupCompleted: true,
                passkeyRegistered: false,
                passkeyError: error.message,
                emergencyModeEnabled: true,
                method: 'emergency_fallback'
            };
        }
    }

    // Recovery and diagnostic methods
    async performSystemDiagnostics() {
        const diagnostics = {
            timestamp: new Date().toISOString(),
            webAuthnSupport: await this.checkWebAuthnSupport(),
            passkeyStatus: await this.checkPasskeyRegistration(),
            secureContext: window.isSecureContext,
            userAgent: navigator.userAgent,
            emergencyMode: this.isEmergencyModeActive(),
            setupMode: this.isSetupModeActive(),
            userRole: localStorage.getItem('user_role'),
            canFallback: this.canUseFallbackAuth()
        };
        
        console.log('System diagnostics:', diagnostics);
        return diagnostics;
    }

    // Reset all authentication data (nuclear option)
    async performFullReset(confirmationCode) {
        if (confirmationCode !== 'RESET_ALL_AUTH_DATA') {
            return {
                success: false,
                error: 'Invalid confirmation code'
            };
        }
        
        // Clear all authentication-related data
        this.clearPasskeyData();
        this.disableEmergencyMode();
        this.disableSetupMode();
        
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_id');
        localStorage.removeItem('first_admin_setup_completed');
        
        console.warn('Full authentication reset performed');
        
        return {
            success: true,
            message: 'All authentication data cleared',
            requiresSetup: true
        };
    }
}

// Create singleton instance
export const passkeyEnforcement = new PasskeyEnforcementService();

// Export utility functions
export const passkeyUtils = {
    // Format authentication status for display
    formatAuthStatus: (authResult) => {
        if (authResult.success) {
            return {
                status: 'success',
                message: 'Authentication successful',
                icon: '✅',
                color: 'green'
            };
        } else {
            return {
                status: 'error',
                message: authResult.error || 'Authentication failed',
                icon: '❌',
                color: 'red'
            };
        }
    },

    // Check if action is sensitive
    isSensitiveAction: (action) => {
        const sensitiveActions = [
            'ai_report_generation',
            'external_ai_access',
            'knowledge_sync',
            'sensitive_data_processing'
        ];
        return sensitiveActions.includes(action);
    },

    // Get action display name
    getActionDisplayName: (action) => {
        const actionNames = {
            'ai_report_generation': 'AI Report Generation',
            'external_ai_access': 'External AI Access',
            'knowledge_sync': 'Knowledge Base Sync',
            'sensitive_data_processing': 'Sensitive Data Processing'
        };
        return actionNames[action] || action;
    },

    // Format time since last authentication
    formatTimeSince: (timestamp) => {
        if (!timestamp) return 'Never';
        
        const now = new Date();
        const then = new Date(timestamp);
        const diffMs = now - then;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minutes ago`;
        if (diffHours < 24) return `${diffHours} hours ago`;
        return `${diffDays} days ago`;
    }
};

export default passkeyEnforcement;