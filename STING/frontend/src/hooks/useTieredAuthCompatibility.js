/**
 * Tiered Authentication Compatibility Hook
 *
 * Provides backward compatibility for components using useAAL2()
 * Maps legacy AAL2 calls to the tiered authentication system
 */

import { useState, useEffect } from 'react';
import { useKratos } from '../auth/KratosProviderRefactored';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';

// Export with both names for compatibility during transition
export const useTieredAuth = () => {
  const { session } = useKratos();
  const { user } = useUnifiedAuth();

  // For tiered auth, we only need Kratos AAL1
  const userAAL = session?.authenticator_assurance_level || 'aal1';

  // Legacy compatibility - map AAL2 concept to "authenticated"
  const isAAL2Verified = userAAL === 'aal1' && !!session;
  const needsVerification = false; // Tiered auth handles this per-operation
  
  // Tiered auth compatibility layer active
  
  // Provide same interface as old AAL2Provider for compatibility
  return {
    // Status object (matches old AAL2Provider format)
    aal2Status: {
      aal2_verified: isAAL2Verified,
      needs_verification: needsVerification,
      passkey_enrolled: false, // Tiered auth handles this
      verification_method: isAAL2Verified ? 'tiered_auth' : null,
      user_id: user?.id,
      enrollment_url: '/dashboard/settings/security'
    },

    // Direct flags
    isAAL2Verified,
    needsVerification,

    // Functions (mapped to tiered auth)
    requireAAL2: async (operation) => {
      // Tiered auth handles this at the operation level
      if (isAAL2Verified) {
        return { success: true, verified: true, method: 'tiered_auth' };
      } else {
        // User not authenticated at all
        return {
          success: false,
          action: 'login_required',
          error: 'NOT_AUTHENTICATED',
          message: 'Please log in to continue',
          redirectUrl: '/login?return_to=' + encodeURIComponent(window.location.pathname)
        };
      }
    },
    canUpgradeAAL: () => false, // Tiered auth doesn't use AAL upgrades
    
    // Challenge/modal state (simplified)
    showBiometricChallenge: false, // Use security-upgrade flow instead
    challengeReason: '',
    
    // Actions
    handleBiometricSuccess: () => {
      console.log('🔐 Redirecting to security-upgrade flow');
      window.location.href = '/security-upgrade';
    },
    handleBiometricCancel: () => {
      console.log('🔐 AAL2 verification cancelled');
    },
    
    // Step-up function - not used in tiered auth
    triggerAAL2StepUp: (returnTo = window.location.pathname) => {
      // Tiered auth handles authentication per-operation
      // This is here for legacy compatibility only
    }
  };
};

// Legacy export alias for backward compatibility
export const useAAL2 = useTieredAuth;

// Export for direct usage
export default useTieredAuth;