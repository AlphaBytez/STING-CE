import React, { useState, useEffect } from 'react';
import { Card, Alert, Button, Divider, Typography } from 'antd';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';
import { Lock, Smartphone, Shield, Key, AlertTriangle, Fingerprint } from 'lucide-react';
import { useLocation, useSearchParams, useNavigate } from 'react-router-dom';
import { storeCurrentSettingsTab } from '../../utils/settingsNavigation';
// MIGRATION: Using direct passkey manager that fetches from settings flow
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';
import TOTPManager from '../settings/TOTPManager';
import CredentialValidator from '../settings/CredentialValidator';
import ApiKeySettings from '../settings/ApiKeySettings';
import SecuritySetupGuide from '../security/SecuritySetupGuide';
// import AAL2StepUp from '../auth/AAL2StepUp'; // Removed - using simplified auth
import securityGateService from '../../services/securityGateService';
import apiClient from '../../utils/apiClient';
import { resilientGet } from '../../utils/resilientApiClient';
import { biometricService } from '../../services/biometricService';


const SecuritySettings = () => {
  const { identity, session } = useKratos();
  const isAdmin = identity?.traits?.role === 'admin';
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [activeSessions, setActiveSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [securityGateStatus, setSecurityGateStatus] = useState(null);
  const [needsAAL2, setNeedsAAL2] = useState(false);
  const [aalStatus, setAALStatus] = useState(null);

  // Add state for Kratos-based security status
  const [kratosSecurityStatus, setKratosSecurityStatus] = useState({
    hasPasskey: false,
    hasTOTP: false,
    isLoading: true
  });

  // Add state for biometric credential tracking
  const [biometricCredentials, setBiometricCredentials] = useState({
    biometric: [],
    standard: [],
    isLoading: true
  });

  // Add state for passkey mode selection
  const [passkeyMode, setPasskeyMode] = useState(null);
  const [showPasskeyManager, setShowPasskeyManager] = useState(false);

  // ✅ Check if routed from dashboard with setup requirements
  const setupRequired = location.state?.setupRequired || false;
  const securitySetup = location.state?.securitySetup || false;
  const missingMethods = location.state?.missingMethods || [];
  const setupMessage = location.state?.message || null;

  // Check if setup is required (from credential-setup flow)
  const isRequiredSetup = searchParams.get('required') === 'true';

  // Store current tab for post-credential navigation
  useEffect(() => {
    const currentTab = searchParams.get('tab');
    if (currentTab) {
      storeCurrentSettingsTab(currentTab);
    } else {
      storeCurrentSettingsTab('security');
    }
  }, [searchParams]);

  useEffect(() => {
    const loadSecuritySettings = async () => {
      try {
        if (identity) {
          // ✅ SECURITY GATE: Check if user needs AAL2 verification for credential modifications
          // This prevents users with existing credentials from modifying them without re-auth
          try {
            const aal2StatusResponse = await axios.get('/api/aal2/status', {
              withCredentials: true
            });

            const aal2Data = aal2StatusResponse.data;
            const hasExistingCredentials = aal2Data?.status?.passkey_enrolled ||
                                          aal2Data?.status?.totp_enrolled;
            const isAAL2Verified = aal2Data?.status?.aal2_verified;

            console.log('🔐 Security Settings AAL2 Gate Check:', {
              hasExistingCredentials,
              isAAL2Verified,
              fullStatus: aal2Data
            });

            // If user has credentials but not AAL2 verified → redirect to step-up
            if (hasExistingCredentials && !isAAL2Verified) {
              console.log('🔐 User has existing credentials but not AAL2 verified - redirecting to security upgrade');

              // Build return URL with preauth marker (matches tieredAuth.js pattern)
              const currentUrl = window.location.pathname + window.location.search;
              const separator = currentUrl.includes('?') ? '&' : '?';
              const returnUrl = `${currentUrl}${separator}preauth=complete`;

              console.log('🔐 SecuritySettings - Setting return URL:', returnUrl);

              // Redirect to AAL2 step-up page with return_to in URL params
              const redirectUrl = `/security-upgrade?reason=credential_modification&return_to=${encodeURIComponent(returnUrl)}`;

              console.log('🔐 SecuritySettings - Redirecting to:', redirectUrl);
              window.location.href = redirectUrl;
              return; // Stop loading the page
            }

            console.log('✅ AAL2 gate passed - user authorized to view security settings');

          } catch (aal2Error) {
            console.error('❌ AAL2 gate check failed:', aal2Error);
            // On error, allow access (fail open for usability, backend will still enforce)
          }

          // Check if we came from AAL2 setup
          const fromAAL2Setup = sessionStorage.getItem('aal2_passkey_setup');
          const aal2ReturnTo = sessionStorage.getItem('aal2_return_to');

          if (fromAAL2Setup) {
            console.log('🔐 Detected AAL2 passkey setup flow, monitoring for completion...');
            
            // Monitor for passkey registration completion
            const monitorInterval = setInterval(async () => {
              try {
                const session = await axios.get('/api/auth/me', { withCredentials: true });
                // FIXED: Use Flask session format instead of Kratos format
                const hasWebAuthn = session.data?.has_passkey || session.data?.passkey_count > 0;
                
                if (hasWebAuthn) {
                  console.log('✅ Passkey registration detected, redirecting back to AAL2 step-up...');
                  clearInterval(monitorInterval);
                  
                  // Don't clean up session storage yet - keep the flags for the AAL2 page
                  // sessionStorage.removeItem('aal2_passkey_setup'); // Keep this
                  // sessionStorage.removeItem('aal2_return_to'); // Keep this
                  
                  // Set completion flag but redirect to AAL2 step-up page, not dashboard
                  sessionStorage.setItem('aal2_passkey_created', 'true');
                  
                  // Go back to AAL2 step-up to show success and allow user to proceed
                  const aal2StepUpUrl = `/aal2-step-up?return_to=${encodeURIComponent(aal2ReturnTo || '/dashboard')}`;
                  
                  // Stay within settings context - don't break out to AAL2 step-up
                  console.log('🔐 Passkey setup completed, staying on security settings page');
                  // Instead of redirecting, just refresh the security status
                  window.location.reload();
                }
              } catch (err) {
                console.error('Error monitoring passkey registration:', err);
              }
            }, 2000);
            
            // Stop monitoring after 5 minutes
            setTimeout(() => {
              clearInterval(monitorInterval);
              console.log('🔐 Stopped monitoring for passkey registration');
            }, 300000);
          }
          // Check 2FA status using /api/auth/me (same as securityGateService.js)
          try {
            const response = await fetch('/api/auth/me', {
              credentials: 'include',
              headers: { 'Accept': 'application/json' }
            });

            if (response.ok) {
              const userData = await response.json();
              const authMethods = userData?.user?.auth_methods || {};

              setSecurityStatus({
                has_totp: !!authMethods.totp,
                has_passkey: !!authMethods.webauthn,
                is_admin: userData?.user?.role === 'admin',
                configured_methods: authMethods,
                message: 'Security status loaded successfully'
              });
            } else {
              throw new Error(`Auth check failed: ${response.status}`);
            }
          } catch (authError) {
            console.warn('Auth method check failed, using fallback:', authError);
            setSecurityStatus({
              has_totp: false,
              has_passkey: false,
              is_admin: false,
              message: 'Security status check unavailable - please refresh'
            });
          }

          // Security settings should be accessible with email only (AAL1)
          // Use working Kratos data source (same as other components)
          const currentAAL = session?.authenticator_assurance_level || 'aal1';
          setNeedsAAL2(false);
          setAALStatus({ level: currentAAL, role: identity?.traits?.role || 'user' });

          // Check security gate status if we were routed here for setup
          if (securitySetup || setupRequired) {
            try {
              const gateStatus = await securityGateService.checkSecurityStatus({
                email: identity?.traits?.email,
                role: identity?.traits?.role || 'user',
                email_verified: identity?.verifiable_addresses?.[0]?.verified !== false
              });
              console.log('🛡️ SecuritySettings: Security gate status:', gateStatus);
              setSecurityGateStatus(gateStatus);
            } catch (error) {
              console.error('🛡️ SecuritySettings: Failed to check security gate status:', error);
            }
          }
          
          // In a real app, fetch active sessions from your backend
          const sessions = [
            {
              id: '1',
              device: 'Chrome on Windows',
              lastActive: new Date().toISOString(),
              location: 'New York, US',
            },
            // Add more sessions as needed
          ];
          setActiveSessions(sessions);
        }
      } catch (error) {
        console.error('Error loading security settings:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadSecuritySettings();
  }, [identity]);

  // Load biometric credential information
  useEffect(() => {
    const loadBiometricCredentials = async () => {
      try {
        console.log('🔒 Loading biometric credentials...');
        const credentialsData = await biometricService.getUserCredentials();
        
        if (credentialsData.success) {
          setBiometricCredentials({
            biometric: credentialsData.credentials.biometric,
            standard: credentialsData.credentials.standard,
            isLoading: false
          });
          console.log('🔒 Loaded credentials:', credentialsData.credentials);
        } else {
          console.warn('🔒 Failed to load biometric credentials:', credentialsData.error);
          setBiometricCredentials(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('🔒 Error loading biometric credentials:', error);
        setBiometricCredentials(prev => ({ ...prev, isLoading: false }));
      }
    };

    if (identity) {
      loadBiometricCredentials();
    }
  }, [identity]);

  // Check security status from both Kratos and enhanced auth system
  useEffect(() => {
    const checkSecurityStatus = async () => {
      try {
        console.log('🔍 Checking comprehensive security status...');
        
        // Get AAL status from our enhanced system using resilient API pattern
        const fallbackAALData = {
          aal_level: 'aal1',
          auth_source: 'unknown',
          has_webauthn: false,
          configured_methods: { webauthn: false, totp: false }
        };
        const aalData = await resilientGet('/api/auth/aal-status', fallbackAALData, { timeout: 5000 });
        
        console.log('🔍 Enhanced AAL status:', aalData);
        
        // Get current session from Kratos for comparison - with fallback
        let session = null;
        try {
          const kratosResponse = await axios.get('/.ory/sessions/whoami', {
            withCredentials: true,
            timeout: 5000
          });
          session = kratosResponse.data;
        } catch (kratosError) {
          console.warn('🔍 Kratos session unavailable, using AAL data only:', kratosError.message);
          // Create fallback session structure
          session = {
            identity: {
              traits: identity?.traits || {},
              credentials: { totp: null, webauthn: null }
            },
            authenticator_assurance_level: 'aal1'
          };
        }
        console.log('🔍 Kratos session data:', session);
        console.log('🔍 Identity credentials:', session.identity?.credentials);
        
        // Check for TOTP credentials in Kratos
        const hasTOTP = session.identity?.credentials?.totp?.identifiers?.length > 0;
        
        // Check for WebAuthn/Passkey credentials (enhanced system takes precedence)
        const hasWebAuthn = aalData.auth_source === 'enhanced_webauthn' || 
                           session.identity?.credentials?.webauthn?.config?.credentials?.length > 0;
        
        // Check enhanced auth AAL2 status
        const hasAAL2 = aalData.aal_level === 'aal2';
        
        console.log('🔍 Comprehensive security status:', {
          hasTOTP,
          hasWebAuthn,
          hasAAL2,
          aalSource: aalData.auth_source,
          totpIdentifiers: session.identity?.credentials?.totp?.identifiers,
          webauthnCredentials: session.identity?.credentials?.webauthn?.config?.credentials
        });
        
        setKratosSecurityStatus({
          hasPasskey: hasWebAuthn,
          hasTOTP: hasTOTP,
          hasAAL2: hasAAL2,
          aalSource: aalData.auth_source,
          isLoading: false
        });
        
      } catch (error) {
        console.error('❌ Error checking comprehensive security status:', error);
        setKratosSecurityStatus({
          hasPasskey: false,
          hasTOTP: false,
          hasAAL2: false,
          isLoading: false
        });
      }
    };
    
    checkSecurityStatus();
  }, []);

  // Load Kratos WebAuthn script for passkey management
  useEffect(() => {
    const loadKratosWebAuthnScript = () => {
      // Check if script is already loaded
      if (window.oryWebAuthnRegistration) {
        console.log('🔐 Kratos WebAuthn script already loaded');
        return;
      }

      // Check if script is already in DOM
      const existingScript = document.querySelector('script[src*="webauthn.js"]');
      if (existingScript) {
        console.log('🔐 Kratos WebAuthn script already in DOM');
        return;
      }

      console.log('🔐 Loading Kratos WebAuthn script...');
      const script = document.createElement('script');
      script.src = '/.well-known/ory/webauthn.js';
      script.async = true;

      // Add error handler for script errors (including the "Cannot set properties of null" error)
      script.onload = () => {
        console.log('✅ Kratos WebAuthn script loaded successfully');

        // Add global error handler to catch errors from webauthn.js
        window.addEventListener('error', (event) => {
          if (event.message && event.message.includes('Cannot set properties of null')) {
            console.warn('⚠️ Caught webauthn.js DOM error (non-critical):', event.message);
            event.preventDefault(); // Prevent the error from showing to the user
            return true;
          }
        }, { once: false });
      };

      script.onerror = () => {
        console.error('❌ Failed to load Kratos WebAuthn script');
      };

      document.head.appendChild(script);
    };

    loadKratosWebAuthnScript();
  }, []);

  const handleSessionTermination = async (sessionId) => {
    try {
      // In a real implementation, you would use Kratos to revoke a session
      // For example, by calling the Kratos session management API
      
      // Example (not implemented here):
      // 1. Call Kratos API to revoke the specific session
      
      // For now, just update the UI
      setActiveSessions(sessions => 
        sessions.filter(session => session.id !== sessionId)
      );
    } catch (error) {
      console.error('Error terminating session:', error);
    }
  };

  // Biometric authentication handler
  const handleAddBiometric = () => {
    console.log('🔒 Starting biometric authenticator setup (TouchID/FaceID)...');
    setPasskeyMode('platform');
    setShowPasskeyManager(true);
  };

  // Hardware key authentication handler
  const handleAddHardwareKey = () => {
    console.log('🔒 Starting hardware key setup...');
    setPasskeyMode('cross-platform');
    setShowPasskeyManager(true);
  };

  const handlePasskeySetupComplete = () => {
    console.log('🔒 Passkey setup completed, refreshing credentials...');
    setShowPasskeyManager(false);
    setPasskeyMode(null);
    // Reload biometric credentials to reflect changes
    const loadBiometricCredentials = async () => {
      try {
        const credentialsData = await biometricService.getUserCredentials();
        if (credentialsData.success) {
          setBiometricCredentials({
            biometric: credentialsData.credentials.biometric,
            standard: credentialsData.credentials.standard,
            isLoading: false
          });
        }
      } catch (error) {
        console.error('Error refreshing credentials after setup:', error);
      }
    };
    loadBiometricCredentials();
  };

  if (isLoading) {
    return <div className="text-white">Loading...</div>;
  }

  // If AAL2 is required, show inline message instead of redirecting away from settings
  if (needsAAL2) {
    console.log('🔐 AAL2 required - showing inline message instead of redirect');
    return (
      <div className="space-y-6">
        <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-6">
          <div className="flex items-center space-x-4">
            <Shield className="w-8 h-8 text-yellow-400" />
            <div>
              <h3 className="text-yellow-400 font-bold text-lg mb-2">Additional Authentication Required</h3>
              <p className="text-yellow-300 text-sm mb-4">
                To access security settings, please complete two-factor authentication first.
              </p>
              <button
                onClick={() => navigate('/login?aal=aal2&return_to=' + encodeURIComponent(location.pathname))}
                className="px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 font-medium"
              >
                Complete Authentication
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Debug: Log component state
  console.log('🔧 SecuritySettings render state:', {
    identity: !!identity,
    isLoading,
    securityStatus,
    securityGateStatus,
    setupRequired,
    securitySetup,
    needsAAL2,
    aalStatus
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header - Fixed */}
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-2xl font-bold text-white mb-2">Security Settings</h2>
        <p className="text-slate-400">Manage your authentication methods and security preferences</p>
      </div>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto pr-2 space-y-6" style={{maxHeight: 'calc(100vh - 200px)'}}>
        {/* 🛡️ SECURITY SETUP GUIDE - Show when routed from dashboard gate */}
      <SecuritySetupGuide securityStatus={securityGateStatus} />
      
      {/* Enhanced Admin 2FA/3FA Setup Reminder */}
      {isAdmin && !securityGateStatus && (
        <div className="bg-gradient-to-r from-red-900/20 to-amber-900/20 border border-red-500/50 rounded-lg p-6 mb-6">
          <div className="flex items-start space-x-4">
            <Shield className="w-6 h-6 text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-red-400 font-bold text-lg mb-3">Admin Account - Enhanced Security Required</h3>
              <div className="space-y-3">
                <p className="text-red-300 text-sm">
                  <strong>Admin accounts require multi-factor passwordless authentication for maximum security:</strong>
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-green-900/30 border border-green-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Smartphone className="w-4 h-4 text-green-400" />
                      <span className="text-green-300 font-medium text-xs">TOTP</span>
                    </div>
                    <p className="text-green-200 text-xs">Authenticator App</p>
                  </div>
                  <div className="bg-purple-900/30 border border-purple-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Key className="w-4 h-4 text-purple-400" />
                      <span className="text-purple-300 font-medium text-xs">WebAuthn</span>
                    </div>
                    <p className="text-purple-200 text-xs">Passkey / Hardware Key</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3 mt-4">
                  <button
                    onClick={() => document.getElementById('totp-setup-section')?.scrollIntoView({ behavior: 'smooth' })}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium transition-colors flex items-center gap-2"
                  >
                    <Smartphone className="w-4 h-4" />
                    Set Up TOTP
                  </button>
                  <button
                    onClick={() => document.getElementById('passkey-setup-section')?.scrollIntoView({ behavior: 'smooth' })}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 text-sm font-medium transition-colors flex items-center gap-2"
                  >
                    <Key className="w-4 h-4" />
                    Set Up Passkey
                  </button>
                </div>
                <p className="text-amber-400/80 text-xs mt-3">
                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                  Set up both methods in any order. Each provides backup access if the other is unavailable.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legacy setup banner fallback */}
      {setupRequired && setupMessage && !securityGateStatus && !isAdmin && (
        <div className="bg-amber-500/10 border border-amber-500/50 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
            <div>
              <h3 className="text-amber-500 font-semibold mb-2">Security Setup Required</h3>
              <p className="text-amber-400/90 text-sm mb-3">{setupMessage}</p>
              {missingMethods.length > 0 && (
                <div className="mt-3">
                  <p className="text-amber-400/80 text-xs mb-2">Missing authentication methods:</p>
                  <div className="flex flex-wrap gap-2">
                    {missingMethods.includes('totp') && (
                      <span className="px-2 py-1 bg-amber-500/20 rounded text-xs text-amber-400">
                        TOTP Authenticator
                      </span>
                    )}
                    {missingMethods.includes('webauthn') && (
                      <span className="px-2 py-1 bg-amber-500/20 rounded text-xs text-amber-400">
                        Passkey / Hardware Key
                      </span>
                    )}
                  </div>
                </div>
              )}
              <p className="text-amber-400/70 text-xs mt-3">
                Complete the setup below, then logout and login again to access all features.
              </p>
            </div>
          </div>
        </div>
      )}
      

      {/* Authentication Methods Section */}
      <div className="sting-glass-card sting-elevation-medium rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg shadow-lg">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Authentication Methods</h3>
            <p className="text-slate-400 text-sm">TouchID/FaceID and Hardware Keys</p>
          </div>
        </div>

        {!biometricCredentials.isLoading && (
          <div className="space-y-4">
            {/* Show all credentials in a unified list */}
            {biometricCredentials.biometric.length === 0 && biometricCredentials.standard.length === 0 ? (
              <div className="text-center py-8">
                <Key className="w-12 h-12 text-slate-500 mx-auto mb-3" />
                <p className="text-slate-400 mb-4">No passkeys or security keys configured</p>
                <p className="text-slate-500 text-sm mb-4">
                  Add a passkey to enable secure, passwordless authentication. 
                  We'll automatically detect if your device supports biometric authentication or use your security key.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Biometric credentials */}
                {biometricCredentials.biometric.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-green-400 font-medium flex items-center gap-2">
                      <Fingerprint className="w-4 h-4" />
                      {biometricCredentials.biometric.length} biometric authenticator(s) configured
                    </p>
                    {biometricCredentials.biometric.map((cred, index) => (
                      <div key={cred.credential_id || index} className="flex items-center justify-between p-3 sting-glass-subtle rounded-lg">
                        <div className="flex items-center gap-3">
                          <Fingerprint className="w-4 h-4 text-green-400" />
                          <div>
                            <p className="text-white text-sm font-medium">{cred.name}</p>
                            <p className="text-slate-400 text-xs">
                              Biometric authentication • 
                              Last used: {cred.last_used ? new Date(cred.last_used).toLocaleDateString() : 'Never'}
                            </p>
                          </div>
                        </div>
                        <span className="text-green-400 text-xs font-medium px-2 py-1 bg-green-400/10 rounded">Enhanced</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Standard credentials */}
                {biometricCredentials.standard.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-blue-400 font-medium flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      {biometricCredentials.standard.length} security key(s) configured
                    </p>
                    {biometricCredentials.standard.map((cred, index) => (
                      <div key={cred.credential_id || index} className="flex items-center justify-between p-3 sting-glass-subtle rounded-lg">
                        <div className="flex items-center gap-3">
                          <Key className="w-4 h-4 text-blue-400" />
                          <div>
                            <p className="text-white text-sm font-medium">{cred.name}</p>
                            <p className="text-slate-400 text-xs">
                              Hardware security key • 
                              Last used: {cred.last_used ? new Date(cred.last_used).toLocaleDateString() : 'Never'}
                            </p>
                          </div>
                        </div>
                        <span className="text-blue-400 text-xs font-medium px-2 py-1 bg-blue-400/10 rounded">Standard</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Separate Authentication Method Buttons */}
        <div className="space-y-3">
          {/* Biometric Authentication Button */}
          <button
            onClick={handleAddBiometric}
            className="w-full px-4 py-3 bg-gradient-to-r from-yellow-500 to-amber-500 hover:from-yellow-400 hover:to-amber-400 text-black rounded-lg transition-all duration-200 font-medium flex flex-col items-center justify-center gap-2 shadow-lg hover:shadow-xl"
          >
            <div className="flex items-center gap-2">
              <Fingerprint className="w-4 h-4" />
              <span>Add TouchID/FaceID Authentication</span>
            </div>
            <span className="text-xs opacity-80">Enhanced security • Quick access with biometrics</span>
          </button>

          {/* Hardware Key Button */}
          <button
            onClick={handleAddHardwareKey}
            className="w-full px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white border border-slate-600 hover:border-slate-500 rounded-lg transition-all duration-200 font-medium flex flex-col items-center justify-center gap-2"
          >
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4" />
              <span>Add Hardware Security Key</span>
            </div>
            <span className="text-xs opacity-75">Standard security • External key or backup method</span>
          </button>
        </div>
      </div>

      {/* Always Visible Passkey Management Section */}
      <div id="passkey-setup-section" className="sting-glass-card sting-elevation-medium rounded-xl p-6 mb-6">
        {showPasskeyManager && (
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {passkeyMode === 'platform' ? (
                <>
                  <Fingerprint className="w-5 h-5 text-green-400" />
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Setting Up TouchID/FaceID
                    </h3>
                    <p className="text-sm text-slate-400">Follow the prompts to enable biometric authentication</p>
                  </div>
                </>
              ) : (
                <>
                  <Key className="w-5 h-5 text-blue-400" />
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Setting Up Hardware Security Key
                    </h3>
                    <p className="text-sm text-slate-400">Follow the prompts to register your security key</p>
                  </div>
                </>
              )}
            </div>
            <button
              onClick={() => {
                setShowPasskeyManager(false);
                setPasskeyMode(null);
              }}
              className="text-gray-400 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
        )}
        <PasskeyManagerDirect 
          authenticatorType={showPasskeyManager ? passkeyMode : null}
          onSetupComplete={handlePasskeySetupComplete}
          isSetupMode={showPasskeyManager}
        />
      </div>

      {/* TOTP Management Section */}
      <div id="totp-setup-section" className="pb-6">
        <TOTPManager />
      </div>

      {/* API Key Management Section */}
      <div className="pb-6">
        <ApiKeySettings />
      </div>


      <div>
        <h2 className="text-xl font-semibold mb-4 text-white">Active Sessions</h2>
        <div className="space-y-4">
          {activeSessions.map((session) => (
            <div
              key={session.id}
              className="sting-glass-medium sting-glass-hoverable flex items-center justify-between p-4 rounded-lg"
            >
              <div className="flex items-center space-x-4">
                <Shield className="w-6 h-6 text-green-400" />
                <div>
                  <p className="font-medium text-white">{session.device}</p>
                  <p className="text-sm text-gray-300">
                    Last active: {new Date(session.lastActive).toLocaleDateString()}
                  </p>
                  <p className="text-sm text-gray-300">{session.location}</p>
                </div>
              </div>
              <button
                onClick={() => handleSessionTermination(session.id)}
                className="floating-button px-4 py-2 text-red-400 hover:bg-red-900 hover:text-red-300 rounded-lg"
              >
                Terminate
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Debug: Check Kratos Session Button */}
      <Button 
        onClick={async () => {
          try {
            const response = await axios.get('/api/auth/me', { withCredentials: true });
            console.log('Full Kratos Session:', response.data);
            console.log('Identity:', response.data.identity);
            console.log('Credentials:', response.data.identity?.credentials);
            console.log('Auth Methods:', response.data.authentication_methods);
          } catch (err) {
            console.error('Debug error:', err);
          }
        }}
      >
        Debug: Check Kratos Session
      </Button>
      
      {/* Credential Validator - Testing and validation tools */}
      <CredentialValidator />
      
      </div>
    </div>
  );
};

export default SecuritySettings;

// Add the credential validator just before the component export
// This will be added to the SecuritySettings component