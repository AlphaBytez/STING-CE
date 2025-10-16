/**
 * BiometricChallenge - Modal for AAL2 Step-up Authentication
 * 
 * This component provides a user-friendly modal for biometric verification:
 * - Explains why AAL2 verification is needed
 * - Integrates with existing WebAuthn flow
 * - Provides clear feedback and error handling
 * - Supports both passkey enrollment and verification flows
 */

import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  Typography,
  Button,
  Box,
  Alert,
  CircularProgress,
  IconButton
} from '@mui/material';
import {
  Fingerprint,
  Security,
  Close,
  CheckCircle,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';
import { useKratos } from '../auth/KratosProviderRefactored';
import { detectWebAuthnCapabilities } from '../utils/webAuthnDetection';

const BiometricChallenge = () => {
  const { user } = useUnifiedAuth();
  const { session } = useKratos();
  
  // PURE KRATOS: Use Kratos AAL directly instead of conflicting AAL2Provider
  const userAAL = session?.authenticator_assurance_level || 'aal1';
  const isAdmin = user?.role === 'admin' || user?.email === 'admin@sting.local';
  const hasAAL2 = userAAL === 'aal2';
  
  // Disable biometric challenge since we have direct Kratos AAL verification
  const showBiometricChallenge = false; // Simplified - use security-upgrade flow instead
  const challengeReason = '';
  
  const handleBiometricSuccess = () => {
    console.log('🔐 Biometric challenge success - redirecting to security-upgrade flow');
    window.location.href = '/security-upgrade';
  };
  
  const handleBiometricCancel = () => {
    console.log('🔐 Biometric challenge cancelled');
  };

  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationError, setVerificationError] = useState(null);
  const [verificationSuccess, setVerificationSuccess] = useState(false);
  const [webAuthnCapabilities, setWebAuthnCapabilities] = useState(null);

  // Detect WebAuthn capabilities when component mounts
  useEffect(() => {
    const detectCapabilities = async () => {
      try {
        const capabilities = await detectWebAuthnCapabilities();
        setWebAuthnCapabilities(capabilities);
      } catch (error) {
        console.error('Failed to detect WebAuthn capabilities:', error);
      }
    };
    
    detectCapabilities();
  }, []);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (showBiometricChallenge) {
      setIsVerifying(false);
      setVerificationError(null);
      setVerificationSuccess(false);
    }
  }, [showBiometricChallenge]);

  /**
   * Handle biometric verification using existing WebAuthn flow
   */
  const handleVerifyBiometric = async () => {
    try {
      setIsVerifying(true);
      setVerificationError(null);

      console.log('🔐 Starting biometric verification for AAL2');

      // Use the existing WebAuthn authentication flow
      // This integrates with the existing webauthn implementation
      const authResponse = await fetch('/api/webauthn/authentication/begin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          operation: 'aal2_verification',
          user_email: user?.email
        })
      });

      if (!authResponse.ok) {
        const errorData = await authResponse.json();
        throw new Error(errorData.message || 'Failed to begin authentication');
      }

      const challengeData = await authResponse.json();
      console.log('🔐 WebAuthn challenge received:', challengeData);

      // Create credential using WebAuthn API
      const credential = await navigator.credentials.get({
        publicKey: challengeData.publicKey
      });

      console.log('🔐 WebAuthn credential obtained');

      // Complete authentication
      const completeResponse = await fetch('/api/webauthn/authentication/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          operation: 'aal2_verification',
          credential: {
            id: credential.id,
            rawId: Array.from(new Uint8Array(credential.rawId)),
            type: credential.type,
            response: {
              clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON)),
              authenticatorData: Array.from(new Uint8Array(credential.response.authenticatorData)),
              signature: Array.from(new Uint8Array(credential.response.signature)),
              userHandle: credential.response.userHandle ? Array.from(new Uint8Array(credential.response.userHandle)) : null
            }
          }
        })
      });

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json();
        throw new Error(errorData.message || 'Authentication verification failed');
      }

      const result = await completeResponse.json();
      console.log('🔐 WebAuthn authentication completed:', result);

      // Mark as successful
      setVerificationSuccess(true);
      
      // Wait a moment to show success, then complete AAL2
      setTimeout(async () => {
        await handleBiometricSuccess();
      }, 1000);

    } catch (err) {
      console.error('🔐 Biometric verification failed:', err);
      
      let errorMessage = 'Biometric verification failed. Please try again.';
      
      if (err.name === 'NotAllowedError') {
        errorMessage = 'Biometric verification was cancelled or timed out.';
      } else if (err.name === 'SecurityError') {
        errorMessage = 'Security error during biometric verification.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setVerificationError(errorMessage);
    } finally {
      setIsVerifying(false);
    }
  };

  /**
   * Handle enrollment navigation
   */
  const handleEnrollPasskey = () => {
    handleBiometricCancel();
    window.location.href = '/dashboard/settings/security';
  };

  if (!showBiometricChallenge) {
    return null;
  }

  return (
    <Dialog
      open={showBiometricChallenge}
      onClose={handleBiometricCancel}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={isVerifying}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <Security color="warning" />
            <Typography variant="h6">
              {webAuthnCapabilities?.hasplatformAuthenticator 
                ? (webAuthnCapabilities.userMessage.includes('Touch ID') ? 'Touch ID or Face ID Required' :
                   webAuthnCapabilities.userMessage.includes('Windows Hello') ? 'Windows Hello Required' :
                   'Biometric Verification Required')
                : 'Passkey Verification Required'
              }
            </Typography>
          </Box>
          <IconButton 
            onClick={handleBiometricCancel} 
            disabled={isVerifying}
            size="small"
          >
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box textAlign="center" py={2}>
          {verificationSuccess ? (
            // Success State
            <Box>
              <CheckCircle color="success" sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h6" color="success.main" gutterBottom>
                Verification Successful!
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Your biometric verification was completed successfully.
              </Typography>
            </Box>
          ) : !hasAAL2 ? (
            // Enrollment Required
            <Box>
              <Fingerprint color="warning" sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Passkey Setup Required
              </Typography>
              <Typography variant="body1" paragraph>
                You need to set up a passkey before accessing sensitive operations.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Passkeys use your device's built-in biometric authentication (fingerprint, face recognition, or PIN) for enhanced security.
              </Typography>
            </Box>
          ) : (
            // Verification Required
            <Box>
              <Fingerprint 
                color={isVerifying ? "action" : "primary"} 
                sx={{ 
                  fontSize: 64, 
                  mb: 2,
                  animation: isVerifying ? 'pulse 2s infinite' : 'none'
                }} 
              />
              <Typography variant="h6" gutterBottom>
                {isVerifying ? 'Verifying...' : 
                 webAuthnCapabilities?.hasplatformAuthenticator 
                   ? (webAuthnCapabilities.userMessage.includes('Touch ID') ? 'Touch ID or Face ID' :
                      webAuthnCapabilities.userMessage.includes('Windows Hello') ? 'Windows Hello' :
                      'Biometric Verification')
                   : 'Passkey Verification'
                }
              </Typography>
              <Typography variant="body1" paragraph>
                {challengeReason || 
                 (webAuthnCapabilities?.hasplatformAuthenticator 
                   ? 'This operation requires biometric verification for security.'
                   : 'This operation requires passkey verification for security.')
                }
              </Typography>
              {isVerifying && (
                <Box display="flex" alignItems="center" justifyContent="center" gap={1} mt={2}>
                  <CircularProgress size={20} />
                  <Typography variant="body2" color="text.secondary">
                    {webAuthnCapabilities?.hasplatformAuthenticator 
                      ? 'Please use your device\'s biometric authentication...'
                      : 'Please use your passkey to authenticate...'
                    }
                  </Typography>
                </Box>
              )}
            </Box>
          )}

          {/* Error Display */}
          {verificationError && (
            <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>
              <Box display="flex" alignItems="center" gap={1}>
                <ErrorIcon fontSize="small" />
                {verificationError}
              </Box>
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        {verificationSuccess ? (
          // Success - no actions needed, will auto-close
          null
        ) : !hasAAL2 ? (
          // Enrollment actions
          <>
            <Button 
              onClick={handleBiometricCancel}
              color="inherit"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleEnrollPasskey}
              variant="contained"
              startIcon={<Security />}
            >
              Set Up Passkey
            </Button>
          </>
        ) : (
          // Verification actions
          <>
            <Button 
              onClick={handleBiometricCancel}
              disabled={isVerifying}
              color="inherit"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleVerifyBiometric}
              disabled={isVerifying}
              variant="contained"
              startIcon={isVerifying ? <CircularProgress size={16} /> : <Fingerprint />}
            >
              {isVerifying ? 'Verifying...' : 
               webAuthnCapabilities?.hasplatformAuthenticator
                 ? (webAuthnCapabilities.userMessage.includes('Touch ID') ? 'Verify with Touch ID' :
                    webAuthnCapabilities.userMessage.includes('Windows Hello') ? 'Verify with Windows Hello' :
                    'Verify with Biometric')
                 : 'Verify with Passkey'
              }
            </Button>
          </>
        )}
      </DialogActions>

      <style jsx>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}</style>
    </Dialog>
  );
};

export default BiometricChallenge;