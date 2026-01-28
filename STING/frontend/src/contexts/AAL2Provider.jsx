/**
 * AAL2Provider - Custom AAL2 Context for Biometric Step-up Authentication
 * 
 * This provider manages custom AAL2 verification state and biometric challenges:
 * - Tracks AAL2 enrollment and verification status
 * - Handles step-up authentication flows
 * - Manages biometric challenge modals
 * - Integrates with existing WebAuthn implementation
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';
import apiClient from '../utils/apiClient';

const AAL2Context = createContext();

export const useAAL2 = () => {
  const context = useContext(AAL2Context);
  if (!context) {
    throw new Error('useAAL2 must be used within AAL2Provider');
  }
  return context;
};

export const AAL2Provider = ({ children }) => {
  const { isAuthenticated, user } = useUnifiedAuth();
  
  // AAL2 State Management
  const [aal2Status, setAAL2Status] = useState({
    passkey_enrolled: false,
    aal2_verified: false,
    needs_enrollment: true,
    needs_verification: false,
    verification_method: null,
    verified_at: null,
    expires_at: null
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingAAL2, setIsCheckingAAL2] = useState(false);
  const [error, setError] = useState(null);
  
  // Biometric Challenge State
  const [showBiometricChallenge, setShowBiometricChallenge] = useState(false);
  const [challengeReason, setChallengeReason] = useState('');
  const [challengeCallback, setChallengeCallback] = useState(null);

  /**
   * Check AAL2 status from backend
   */
  const checkAAL2Status = useCallback(async () => {
    if (!isAuthenticated || !user) {
      return;
    }

    try {
      setIsCheckingAAL2(true);
      setError(null);

      console.log('🔐 Checking AAL2 status for user:', user.email);

      const response = await apiClient.get('/api/aal2/status', { timeout: 5000 });
      
      if (response.data.success) {
        const status = response.data.status;
        console.log('🔐 AAL2 status received:', status);
        
        // Cross-verify with a quick passkey check if status shows not enrolled
        if (!status.passkey_enrolled) {
          console.log('🔍 AAL2 status shows no passkeys, cross-checking...');
          try {
            // Quick check with webauthn endpoint to see if passkeys exist
            const webauthnCheck = await apiClient.get('/api/webauthn/credentials', { timeout: 3000 });
            if (webauthnCheck.data.success && webauthnCheck.data.credentials && webauthnCheck.data.credentials.length > 0) {
              console.log('🔐 Cross-check found passkeys! Correcting AAL2 status');
              status.passkey_enrolled = true;
              status.configured_methods = status.configured_methods || {};
              status.configured_methods.webauthn = true;
            }
          } catch (crossCheckError) {
            console.log('🔍 Cross-check failed, using original status:', crossCheckError.message);
          }
        }
        
        setAAL2Status(status);
      } else {
        setError('Failed to get AAL2 status');
      }
    } catch (err) {
      console.error('🔐 Error checking AAL2 status:', err);
      console.log('🔐 AAL2 status API failed, applying resilient fallback');
      
      // Resilient fallback: If API fails, assume user might have passkeys enrolled
      // and allow the biometric challenge to proceed rather than blocking access
      const fallbackStatus = {
        aal2_verified: false,
        passkey_enrolled: true, // Assume enrolled to allow authentication attempt
        totp_enrolled: false,
        configured_methods: {
          webauthn: true, // Assume webauthn available
          totp: false
        },
        required_aal: 2,
        current_aal: 1
      };
      
      console.log('🔐 Using fallback AAL2 status:', fallbackStatus);
      setAAL2Status(fallbackStatus);
      
      // Still set error for logging but don't block functionality
      if (err.response?.status === 401) {
        setError('Authentication required');
      } else {
        setError('AAL2 status check failed - using fallback mode');
      }
    } finally {
      setIsCheckingAAL2(false);
    }
  }, [isAuthenticated, user]);

  /**
   * Trigger AAL2 verification check - used by components that need AAL2
   */
  const requireAAL2 = useCallback(async (operation = 'sensitive_operation') => {
    console.log('🔐 AAL2 required for operation:', operation);

    // Only check status if we don't have valid status data
    if (!aal2Status || typeof aal2Status.passkey_enrolled === 'undefined') {
      console.log('🔐 No valid status data, checking AAL2 status...');
      await checkAAL2Status();
    } else {
      console.log('🔐 Using existing AAL2 status:', aal2Status);
    }

    // If already verified, return success
    if (aal2Status.aal2_verified) {
      console.log('✅ AAL2 already verified');
      return { success: true, verified: true };
    }

    // If not enrolled, redirect to enrollment
    if (!aal2Status.passkey_enrolled) {
      console.log('🔐 Passkey not enrolled, need enrollment');
      console.log('🔍 Current AAL2 status:', aal2Status);
      return {
        success: false,
        error: 'PASSKEY_ENROLLMENT_REQUIRED',
        message: 'Please set up a passkey first',
        action: 'enrollment_required',
        enrollment_url: '/dashboard/settings?tab=security'
      };
    }

    // If not AAL2 verified, check what methods are available
    if (!aal2Status.aal2_verified) {
      // If user has both TOTP and passkey, let them choose
      if (aal2Status.totp_enrolled && aal2Status.passkey_enrolled) {
        console.log('🔐 Need AAL2 verification, user has both TOTP and passkey - showing choice');
        return await triggerBiometricChallenge(operation); // This will show choice screen
      }
      
      // If only passkey enrolled, use biometric
      if (aal2Status.passkey_enrolled && !aal2Status.totp_enrolled) {
        console.log('🔐 Need AAL2 verification, passkey only - triggering biometric challenge');
        console.log('🔍 AAL2 Status for biometric trigger:', aal2Status);
        return await triggerBiometricChallenge(operation);
      }
      
      // If only TOTP enrolled, redirect to TOTP entry (future enhancement)
      if (aal2Status.totp_enrolled && !aal2Status.passkey_enrolled) {
        console.log('🔐 Need AAL2 verification, TOTP only - need TOTP entry flow');
        // For now, show biometric challenge which will show TOTP option
        return await triggerBiometricChallenge(operation);
      }
      
      console.log('🔐 Need AAL2 verification but no methods available');
      return {
        success: false,
        error: 'NO_AAL2_METHODS',
        message: 'No AAL2 authentication methods available',
        action: 'enrollment_required',
        enrollment_url: '/dashboard/settings?tab=security'
      };
    }

    return { success: false, error: 'Unknown AAL2 state' };
  }, [aal2Status, checkAAL2Status]);

  /**
   * Trigger biometric challenge modal
   */
  const triggerBiometricChallenge = useCallback(async (operation = 'sensitive_operation') => {
    return new Promise((resolve) => {
      console.log('🔐 Triggering biometric challenge for:', operation);
      
      setChallengeReason(`This ${operation} requires biometric verification for security.`);
      setShowBiometricChallenge(true);
      
      // Store the callback to resolve when challenge completes
      setChallengeCallback(() => resolve);
    });
  }, []);

  /**
   * Handle successful biometric verification
   */
  const handleBiometricSuccess = useCallback(async () => {
    try {
      console.log('🔐 Biometric verification successful, completing AAL2 challenge');
      
      // Call backend to mark AAL2 as verified
      const response = await apiClient.post('/api/aal2/challenge/complete', {
        verification_method: 'webauthn'
      });
      
      if (response.data.success) {
        console.log('✅ AAL2 challenge completed successfully');
        
        // Update status
        setAAL2Status(response.data.status);
        
        // Close modal
        setShowBiometricChallenge(false);
        setChallengeReason('');
        
        // Call the callback if it exists
        if (challengeCallback) {
          challengeCallback({ success: true, verified: true });
          setChallengeCallback(null);
        }
        
        return { success: true, verified: true };
      } else {
        throw new Error(response.data.error || 'AAL2 verification failed');
      }
    } catch (err) {
      console.error('🔐 Error completing AAL2 challenge:', err);
      
      setError(err.response?.data?.message || 'Biometric verification failed');
      
      // Call the callback with error
      if (challengeCallback) {
        challengeCallback({ 
          success: false, 
          error: err.response?.data?.error || 'VERIFICATION_FAILED' 
        });
        setChallengeCallback(null);
      }
      
      return { success: false, error: 'Verification failed' };
    }
  }, [challengeCallback]);

  /**
   * Handle biometric challenge cancellation
   */
  const handleBiometricCancel = useCallback(() => {
    console.log('🔐 Biometric challenge cancelled');
    
    setShowBiometricChallenge(false);
    setChallengeReason('');
    
    // Call the callback with cancellation
    if (challengeCallback) {
      challengeCallback({ 
        success: false, 
        error: 'USER_CANCELLED',
        message: 'Biometric verification was cancelled'
      });
      setChallengeCallback(null);
    }
  }, [challengeCallback]);

  /**
   * Navigate to passkey enrollment
   */
  const navigateToEnrollment = useCallback(() => {
    window.location.href = '/dashboard/settings?tab=security';
  }, []);

  // Check AAL2 status when user changes
  useEffect(() => {
    if (isAuthenticated && user) {
      checkAAL2Status();
    } else {
      // Reset status when not authenticated
      setAAL2Status({
        passkey_enrolled: false,
        aal2_verified: false,
        needs_enrollment: true,
        needs_verification: false,
        verification_method: null,
        verified_at: null,
        expires_at: null
      });
    }
  }, [isAuthenticated, user, checkAAL2Status]);

  const contextValue = {
    // Status
    aal2Status,
    isLoading,
    isCheckingAAL2,
    error,
    
    // Computed status
    isAAL2Verified: aal2Status.aal2_verified,
    isPasskeyEnrolled: aal2Status.passkey_enrolled,
    needsEnrollment: aal2Status.needs_enrollment,
    needsVerification: aal2Status.needs_verification,
    
    // Actions
    checkAAL2Status,
    requireAAL2,
    triggerBiometricChallenge,
    navigateToEnrollment,
    
    // Biometric Challenge Modal State
    showBiometricChallenge,
    challengeReason,
    handleBiometricSuccess,
    handleBiometricCancel,
    
    // Manual modal control
    setShowBiometricChallenge,
    setChallengeReason
  };

  return (
    <AAL2Context.Provider value={contextValue}>
      {children}
    </AAL2Context.Provider>
  );
};

export default AAL2Provider;