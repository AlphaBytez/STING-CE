import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthProvider';

const AAL2StepUp = ({ onMethodSelected, onCancel }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [availableMethods, setAvailableMethods] = useState({});
  const [loading, setLoading] = useState(true);
  
  const {
    userEmail,
    biometricAvailable,
    hasRegisteredPasskey,
    setError,
    clearMessages,
    cachedCredentials
  } = useAuth();
  
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // WebAuthn availability check function (from archived version)
  const checkWebAuthnAvailability = async () => {
    try {
      if (!window.PublicKeyCredential) {
        return { supported: false, configured: false, count: 0 };
      }
      
      // Check Kratos session for WebAuthn credentials
      const sessionResponse = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        // Look for WebAuthn credentials in Kratos identity
        const credentials = sessionData?.identity?.credentials || {};
        const webauthnCreds = credentials.webauthn || {};
        const identifiers = webauthnCreds.identifiers || [];
        
        const count = identifiers.length;
        
        return {
          supported: true,
          configured: count > 0,
          count
        };
      }
      
      return { supported: true, configured: false, count: 0 };
    } catch (error) {
      console.error('🔐 Error checking WebAuthn availability:', error);
      return { supported: false, configured: false, count: 0 };
    }
  };
  
  // Check available AAL2 methods for current user
  useEffect(() => {
    checkAAL2Methods();
  }, [userEmail]);
  
  const checkAAL2Methods = async () => {
    try {
      setLoading(true);
      clearMessages();
      
      console.log('🔐 Checking AAL2 methods for user:', userEmail);
      
      let currentUserEmail = userEmail;
      let sessionData = null;
      
      // Get current session data (we'll need this for direct Kratos credential checking)
      const sessionResponse = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (sessionResponse.ok) {
        sessionData = await sessionResponse.json();
        if (!currentUserEmail) {
          currentUserEmail = sessionData.identity?.traits?.email;
        }
      }
      
      if (!currentUserEmail) {
        setError('Unable to determine user email for AAL2 verification');
        return;
      }
      
      // Direct Kratos credential checking (most reliable)
      let hasTotp = false;
      let hasWebAuthn = false;
      let webauthnCount = 0;
      
      try {
        console.log('🔒 Checking Kratos credentials directly...');
        
        // IMPORTANT: During AAL2, prioritize cached credentials since session may be invalidated
        if (cachedCredentials?.credentials?.totp) {
          // Primary: Use cached credentials from AAL1 session
          const cachedTotpCreds = cachedCredentials.credentials.totp;
          hasTotp = cachedTotpCreds.identifiers && cachedTotpCreds.identifiers.length > 0;
          console.log('🔒 Using cached TOTP credentials:', { hasTotp, identifiers: cachedTotpCreds.identifiers, timestamp: cachedCredentials.timestamp });
        } else if (sessionData?.identity?.credentials?.totp) {
          // Fallback: Try direct Kratos session credentials if available
          const totpCreds = sessionData.identity.credentials.totp;
          hasTotp = totpCreds.identifiers && totpCreds.identifiers.length > 0;
          console.log('🔒 Direct Kratos TOTP check:', { hasTotp, identifiers: totpCreds.identifiers });
        }
        
        // Check WebAuthn - prioritize cached credentials during AAL2
        if (cachedCredentials?.credentials?.webauthn) {
          // Primary: Use cached WebAuthn credentials from AAL1 session
          const cachedWebAuthnCreds = cachedCredentials.credentials.webauthn;
          webauthnCount = cachedWebAuthnCreds.identifiers ? cachedWebAuthnCreds.identifiers.length : 0;
          hasWebAuthn = webauthnCount > 0;
          console.log('🔒 Using cached WebAuthn credentials:', { hasWebAuthn, webauthnCount, identifiers: cachedWebAuthnCreds.identifiers });
        } else {
          // Fallback: Try direct Kratos session credentials if available
          const webauthnStatus = await checkWebAuthnAvailability();
          hasWebAuthn = webauthnStatus.configured === true;
          webauthnCount = webauthnStatus.count || 0;
          console.log('🔒 Direct WebAuthn check:', { hasWebAuthn, webauthnCount });
        }
        
        console.log('🔒 Direct Kratos credential check:', { hasTotp, hasWebAuthn, webauthnCount });
        
        // Fallback to API endpoints only if direct check shows no methods
        if (!hasTotp && !hasWebAuthn) {
          console.log('🔒 Direct Kratos check shows no methods, trying API fallbacks...');
          
          const [totpResponse, securityGateResponse] = await Promise.all([
            axios.get('/api/totp/totp-status', { withCredentials: true }).catch((err) => {
              console.log('🔒 TOTP API failed:', err.response?.status, err.response?.statusText);
              return { data: { enabled: false } };
            }),
            axios.get('/api/auth/security-gate/status', { withCredentials: true }).catch((err) => {
              console.log('🔒 Security gate API failed:', err.response?.status, err.response?.statusText);
              return { data: { has_totp: false, has_passkey: false } };
            })
          ]);
          
          // Use API results if direct check missed something
          if (totpResponse.data?.enabled === true) {
            console.log('🔒 API detected TOTP that direct check missed');
            hasTotp = true;
          }
          
          if (securityGateResponse.data?.has_totp === true) {
            console.log('🔒 Security gate detected TOTP that other checks missed');
            hasTotp = true;
          }
          
          if (securityGateResponse.data?.has_passkey === true && !hasWebAuthn) {
            console.log('🔒 Security gate detected WebAuthn that other checks missed');
            hasWebAuthn = true;
          }
        }
      } catch (overallError) {
        console.error('🔒 All method detection failed:', overallError);
      }
      
      const methods = {
        hasTotp,
        hasWebAuthn,
        customPasskeys: hasWebAuthn ? webauthnCount : 0,
        totalPasskeys: webauthnCount
      };
      
      // NOTE: With Kratos native WebAuthn migration, custom passkeys are legacy
      // Only use Kratos WebAuthn for AAL2 - user may need to re-enroll passkeys
      
      setAvailableMethods(methods);
      
      console.log('🔐 AAL2 methods available:', methods);
      
      // Auto-route if user has only one method
      if (methods.hasTotp && !methods.hasWebAuthn) {
        console.log('🔐 Only TOTP available, auto-selecting TOTP');
        handleMethodSelection('totp');
      } else if (!methods.hasTotp && methods.hasWebAuthn) {
        console.log('🔐 Only WebAuthn available, auto-selecting passkey');
        handleMethodSelection('passkey');
      } else if (methods.hasTotp && methods.hasWebAuthn) {
        console.log('🔐 Both TOTP and WebAuthn available - user can choose');
        // Don't auto-select, let user choose their preferred method
      }
      
    } catch (error) {
      console.error('🔐 Error checking AAL2 methods:', error);
      setError('Failed to check available authentication methods');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle method selection
  const handleMethodSelection = (method) => {
    console.log('🔐 User selected AAL2 method:', method);
    
    // Save user preference for future
    localStorage.setItem('sting-aal2-preference', method);
    
    if (onMethodSelected) {
      onMethodSelected(method);
    }
  };
  
  // Reset user preference
  const resetPreference = () => {
    localStorage.removeItem('sting-aal2-preference');
    setError('');
    console.log('🔐 AAL2 preference reset');
  };
  
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p className="text-gray-300">Checking available authentication methods...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-xl font-semibold text-white mb-2">
          Additional Security Required
        </h2>
        <p className="text-gray-300 text-sm">
          {userEmail ? `Logged in as: ${userEmail}` : 'Choose your authentication method'}
        </p>
        <p className="text-gray-400 text-xs mt-2">
          You're accessing sensitive data that requires additional verification
        </p>
      </div>
      
      {/* Security notice */}
      <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-4">
        <p className="text-blue-300 text-sm text-center">
          🔐 Second factor authentication required for high-security access
        </p>
      </div>
      
      {/* Authentication method options */}
      <div className="space-y-4">
        {/* Passkey/Biometric Option */}
        {availableMethods.hasWebAuthn && (
          <button
            onClick={() => handleMethodSelection('passkey')}
            className={`w-full font-semibold py-4 px-4 rounded-lg transition duration-200 flex items-center justify-center ${
              biometricAvailable && hasRegisteredPasskey
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-gray-600 hover:bg-gray-700 text-white'
            }`}
          >
            <span className="mr-3 text-2xl">
              {biometricAvailable ? (navigator.platform.includes('Mac') ? '👆' : '🔐') : '🔑'}
            </span>
            <div className="text-left">
              <div className="font-semibold">
                {biometricAvailable 
                  ? (navigator.platform.includes('Mac') ? 'Touch ID' : 'Biometric Authentication')
                  : 'Hardware Security Key'
                }
              </div>
              <div className="text-sm opacity-90">
                {biometricAvailable 
                  ? 'Use your fingerprint or face recognition'
                  : 'YubiKey or other external authenticator'
                }
              </div>
            </div>
          </button>
        )}
        
        {/* TOTP Option */}
        {availableMethods.hasTotp && (
          <button
            onClick={() => handleMethodSelection('totp')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-4 rounded-lg transition duration-200 flex items-center justify-center"
          >
            <span className="mr-3 text-2xl">📱</span>
            <div className="text-left">
              <div className="font-semibold">Authenticator App</div>
              <div className="text-sm opacity-90">Enter 6-digit TOTP code</div>
            </div>
          </button>
        )}
        
        {/* No methods available */}
        {!availableMethods.hasTotp && !availableMethods.hasWebAuthn && (
          <div className="sting-glass-subtle border border-red-500/50 rounded-lg p-4">
            <p className="text-red-300 text-sm text-center mb-3">
              ⚠️ No second factor authentication methods configured
            </p>
            <button
              onClick={() => navigate('/enrollment')}
              className="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Set Up Security Methods
            </button>
          </div>
        )}
      </div>
      
      {/* Method details */}
      {(availableMethods.hasTotp || availableMethods.hasWebAuthn) && (
        <div className="sting-glass-subtle border border-gray-600/50 rounded-lg p-3">
          <p className="text-gray-400 text-xs text-center mb-2">Available methods:</p>
          <div className="text-xs text-gray-500 space-y-1">
            {availableMethods.hasTotp && (
              <div className="flex items-center justify-center">
                <span className="mr-2">📱</span>
                <span>TOTP Authenticator App configured</span>
              </div>
            )}
            {availableMethods.hasWebAuthn && (
              <div className="flex items-center justify-center">
                <span className="mr-2">🔑</span>
                <span>{availableMethods.customPasskeys} passkey(s) configured</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex space-x-4">
        {onCancel && (
          <button
            onClick={onCancel}
            className="flex-1 text-gray-400 hover:text-white text-sm"
          >
            Cancel (return to dashboard)
          </button>
        )}
        
        <button
          onClick={resetPreference}
          className="text-gray-500 hover:text-gray-300 text-xs"
          title="Reset saved preference and re-detect capabilities"
        >
          Reset Choice
        </button>
      </div>
    </div>
  );
};

export default AAL2StepUp;