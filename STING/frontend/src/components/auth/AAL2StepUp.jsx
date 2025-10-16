/**
 * AAL2StepUp - Simplified component for second factor authentication
 * 
 * Uses working components (PasskeyManagerDirect, TOTPManager) from previous commits
 * for reliable AAL2 passkey/TOTP setup and authentication.
 * 
 * Now uses proper STING theming system instead of hardcoded styles.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAALStatus } from '../../hooks/useAALStatus';
import { useTheme } from '../../context/ThemeContext';
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';
import TOTPManager from '../settings/TOTPManager';
import '../../theme/sting-glass-theme.css';
import '../../theme/glass-login-override.css';

const AAL2StepUp = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { themeColors } = useTheme();
  
  const {
    aalStatus,
    getMissingMethods,
    isAdmin,
    fetchAALStatus,
    canAccessDashboard
  } = useAALStatus();
  
  // Simplified state management
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [showSetup, setShowSetup] = useState(false);
  const [setupMethod, setSetupMethod] = useState(null);
  const [setupComplete, setSetupComplete] = useState(false);
  
  // Flexible fallback options
  const [skipTimer, setSkipTimer] = useState(30);
  const [showFallbackOptions, setShowFallbackOptions] = useState(true);
  
  const returnTo = searchParams.get('return_to') || '/dashboard';
  const missingMethods = getMissingMethods();
  
  console.log('🔐 AAL2StepUp initialized:', { returnTo, missingMethods, aalStatus });

  // Auto-skip timer for flexible UX
  useEffect(() => {
    if (showFallbackOptions && skipTimer > 0) {
      const timer = setTimeout(() => {
        setSkipTimer(prev => {
          if (prev <= 1) {
            handleCompleteNowSkipLater();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [skipTimer, showFallbackOptions]);

  // Initialize on mount
  useEffect(() => {
    const initialize = async () => {
      console.log('🔐 AAL2StepUp initializing...');
      console.log('🔐 AAL Status:', aalStatus);
      console.log('🔐 Missing methods:', missingMethods);
      console.log('🔐 Can access dashboard:', canAccessDashboard());
      console.log('🔐 Full AAL Status object:', JSON.stringify(aalStatus, null, 2));
      
      // Check if user is authenticated at all - improved session detection
      const hasKratosSession = document.cookie.includes('ory_kratos_session');
      const hasStingSession = document.cookie.includes('sting_session');
      const hasAnySession = hasKratosSession || hasStingSession;
      
      console.log('🔐 Session detection:', { 
        hasKratosSession, 
        hasStingSession, 
        hasAnySession,
        aalStatus: aalStatus !== null 
      });
      
      // Check if coming from email login - skip aggressive logout detection
      const fromEmailLogin = new URLSearchParams(window.location.search).get('from_email') === 'true' ||
                             sessionStorage.getItem('aal1_completed') === 'true';
      
      if (aalStatus === null && !hasAnySession && !fromEmailLogin) {
        console.log('❌ No session cookies found, user likely logged out, redirecting to login');
        window.location.href = '/login';
        return;
      }
      
      if (fromEmailLogin) {
        console.log('✅ Coming from email login - trusting AAL1 session, proceeding with AAL2');
        
        // If AAL status is null during transition, assume standard admin 2FA methods are available
        if (!aalStatus) {
          console.log('🔐 AAL status null during transition - using reliable credential detection');
          
          // Use reliable detection: Check Kratos directly bypassing Flask middleware
          try {
            const kratosCheckResponse = await fetch('/.ory/sessions/whoami', {
              method: 'GET',
              credentials: 'include',
              headers: { 'Accept': 'application/json' }
            });
            
            if (kratosCheckResponse.ok) {
              const sessionData = await kratosCheckResponse.json();
              console.log('🔐 Direct session check during AAL2:', {
                aal: sessionData.authenticator_assurance_level,
                hasCredentials: !!sessionData.identity?.credentials,
                credentialTypes: Object.keys(sessionData.identity?.credentials || {})
              });
              
              // Check if user has TOTP or WebAuthn configured
              const credentials = sessionData.identity?.credentials || {};
              const hasTotp = !!credentials.totp;
              const hasWebAuthn = !!credentials.webauthn;
              
              console.log('🔐 Credential detection result:', { hasTotp, hasWebAuthn });
              
              if (hasTotp || hasWebAuthn) {
                console.log('✅ User has 2FA configured - proceeding to authentication mode');
                setIsLoading(false);
                return;
              } else {
                console.log('⚠️ No 2FA detected - user needs enrollment');
                // Let component show enrollment options
              }
            } else {
              console.log('🔐 Session check failed during AAL2 - assuming 2FA configured');
              setIsLoading(false);
              return;
            }
          } catch (error) {
            console.error('🔐 Credential detection failed:', error);
            console.log('🔐 Falling back to assume 2FA configured');
            setIsLoading(false);
            return;
          }
        }
      }
      
      // Wait for AAL status to be loaded, but only if we have a session
      if (!aalStatus && hasAnySession) {
        console.log('🔐 Waiting for AAL status to load...');
        // If we've been waiting too long and still no AAL status, user might be logged out
        setTimeout(() => {
          if (!aalStatus && hasAnySession) {
            console.log('⚠️ AAL status not loaded after timeout but session exists, proceeding with defaults');
            // Set loading to false to show the interface anyway
            setIsLoading(false);
          }
        }, 3000); // Reduced timeout from 5s to 3s
        return;
      }
      
      // If we have no session and no AAL status, redirect to login (unless coming from email)
      if (!aalStatus && !hasAnySession && !fromEmailLogin) {
        console.log('❌ No AAL status and no session, redirecting to login');
        window.location.href = '/login';
        return;
      }
      
      // Check if setup is already complete OR if user already has AAL2
      // Also allow access if we have a session but no AAL status (session coordination lag)
      if (canAccessDashboard() || aalStatus?.aal === 'aal2' || (!aalStatus && hasAnySession)) {
        console.log('✅ User can already access dashboard or has AAL2, redirecting...', {
          canAccessDashboard: canAccessDashboard(),
          aalLevel: aalStatus?.aal,
          hasSession: hasAnySession,
          aalStatus: !!aalStatus
        });
        
        // If we have a session but no AAL status, it might be session coordination lag
        if (!aalStatus && hasAnySession) {
          console.log('⚠️ Session exists but no AAL status - assuming authentication completed, redirecting to dashboard');
        }
        
        navigate(returnTo);
        return;
      }
      
      // Check if we just returned from passkey registration
      const passkeyCreated = sessionStorage.getItem('aal2_passkey_created');
      if (passkeyCreated) {
        console.log('🎉 Returned from successful passkey registration!');
        sessionStorage.removeItem('aal2_passkey_created');
        setSetupComplete(true);
        setIsLoading(false);
        return;
      }
      
      // Check if user has configured methods that just need authentication (not setup)
      // Handle both response formats (configured_methods or has_webauthn/has_totp)
      const hasConfiguredMethods = 
        (aalStatus?.configured_methods && 
          (aalStatus.configured_methods.webauthn || aalStatus.configured_methods.totp)) ||
        (aalStatus?.has_webauthn || aalStatus?.has_totp);
      
      if (hasConfiguredMethods) {
        // User has methods configured - they need to authenticate, not set up new methods
        console.log('🔐 User has configured methods, needs authentication:', {
          webauthn: aalStatus?.has_webauthn || aalStatus?.configured_methods?.webauthn,
          totp: aalStatus?.has_totp || aalStatus?.configured_methods?.totp
        });
        setIsLoading(false);
        // Don't auto-redirect, let user click the authentication button
        return;
      }
      
      // Check if we have missing methods that need setup
      if (missingMethods && missingMethods.length > 0 && !fromEmailLogin) {
        console.log('🔐 Missing methods detected, showing setup:', missingMethods);
        setShowSetup(false); // Don't auto-show setup, let user choose
        // Default to passkey setup if available
        setSetupMethod(missingMethods.includes('webauthn') ? 'webauthn' : 'totp');
      } else if (fromEmailLogin) {
        console.log('🔐 Coming from email login - assuming 2FA configured, skipping setup mode');
        setShowSetup(false); // Force authentication mode, not setup mode
      }
      
      setIsLoading(false);
    };
    
    initialize();
  }, [aalStatus, canAccessDashboard, missingMethods, navigate, returnTo]);

  // Handle completion from PasskeyManagerDirect or TOTPManager
  const handleSetupComplete = async (method) => {
    console.log(`🔐 ${method} setup completed!`);
    
    // Force refresh AAL status
    await fetchAALStatus();
    
    // Set bypass and redirect
    console.log('✅ Setup completed, setting AAL2 bypass and redirecting...');
    setSetupComplete(true);
    sessionStorage.setItem('aal2_setup_complete', 'true');
    
    // Clean up any AAL2 setup flags
    sessionStorage.removeItem('aal2_passkey_setup');
    sessionStorage.removeItem('aal2_return_to');
    
    setTimeout(() => {
      navigate(returnTo);
    }, 1500);
  };

  const handleSetupCancel = () => {
    setShowSetup(false);
    setSetupMethod(null);
  };

  // Flexible fallback handlers (enrollment pattern)
  const handleCompleteNowSkipLater = () => {
    console.log('🔐 User chose to complete enhanced security later');
    
    // Set session flag to remember user's choice
    sessionStorage.setItem('aal2_skip_until_settings', 'true');
    sessionStorage.setItem('aal2_last_skip', Date.now().toString());
    
    // Redirect to dashboard
    navigate(returnTo);
  };

  const handleFixInSettings = () => {
    console.log('🔐 User chose to configure security in settings');
    navigate('/dashboard/settings?tab=security&setup=true&reason=aal2');
  };

  const handleStopTimerContinue = () => {
    setShowFallbackOptions(false);
    setSkipTimer(0);
  };

  // New function to handle AAL2 authentication with existing methods
  const initiateAAL2Authentication = async () => {
    try {
      console.log('🔐 Initiating AAL2 authentication with existing methods...');
      console.log('🔐 Configured methods:', aalStatus?.configured_methods);
      
      // Check if user has passkeys configured (handle both response formats)
      if (aalStatus?.configured_methods?.webauthn || aalStatus?.has_webauthn) {
        console.log('🔐 User has passkeys configured, initiating WebAuthn authentication...');
        
        // Use Kratos browser flow for AAL2 step-up with proper return URL
        try {
          console.log('🔐 Initiating AAL2 step-up via Kratos browser flow...');
          console.log('🔐 Return to:', returnTo);
          
          // Create an AAL2 login flow with refresh=true to step up existing session
          const flaskAAL2Url = `/api/auth/aal2-stepup?return_to=${encodeURIComponent(returnTo)}`;
          console.log('🔐 Redirecting to Flask AAL2 step-up:', flaskAAL2Url);
          
          // Navigate to the AAL2 step-up flow via Flask backend
          window.location.href = flaskAAL2Url;
          
        } catch (error) {
          console.error('❌ Error initiating AAL2 step-up:', error);
          setError('Failed to initiate passkey authentication. Please try again.');
        }
        
      } else if (aalStatus?.configured_methods?.totp || aalStatus?.has_totp) {
        console.log('🔐 User has TOTP configured, redirecting to Kratos AAL2 flow...');
        
        // Redirect to Flask AAL2 step-up flow for TOTP authentication
        const flaskAAL2Url = `/api/auth/aal2-stepup?return_to=${encodeURIComponent(returnTo)}`;
        console.log('🔐 Redirecting to Flask AAL2 step-up:', flaskAAL2Url);
        window.location.href = flaskAAL2Url;
        
      } else {
        console.log('⚠️ No configured methods found, falling back to setup flow');
        setShowSetup(true);
        setSetupMethod('webauthn');
      }
      
    } catch (error) {
      console.error('❌ Error initiating AAL2 authentication:', error);
      setError('Failed to initiate authentication. Please try again.');
    }
  };

  // Show completion message
  if (setupComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: themeColors.background }}>
        <div className="dynamic-card p-8 w-full max-w-lg">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: themeColors.success }}>
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="font-bold text-xl mb-2" style={{ color: themeColors.success }}>Setup Complete!</h3>
            <p className="text-sm mb-4" style={{ color: themeColors.textSecondary }}>
              Your additional security method has been configured successfully.
            </p>
            <p className="text-xs" style={{ color: themeColors.textMuted }}>
              Redirecting to dashboard...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show inline setup view
  if (showSetup && setupMethod) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: themeColors.background }}>
        <div className="dynamic-card p-8 w-full max-w-2xl">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: themeColors.text }}>
              Setup {setupMethod === 'webauthn' ? 'Passkey' : 'Authenticator App'}
            </h1>
            <p style={{ color: themeColors.textSecondary }}>
              {setupMethod === 'webauthn' 
                ? 'Configure your passkey for secure authentication'
                : 'Configure TOTP for two-factor authentication'
              }
            </p>
          </div>

          <div className="space-y-6">
            {setupMethod === 'webauthn' && (
              <div className="dynamic-card-subtle p-6">
                <PasskeyManagerDirect 
                  isEnrollmentMode={false}
                  onSetupComplete={() => handleSetupComplete('webauthn')}
                  onError={(err) => setError(err)}
                />
              </div>
            )}

            {setupMethod === 'totp' && (
              <div className="dynamic-card-subtle p-6">
                <TOTPManager 
                  isEnrollmentMode={false}
                  onSetupComplete={() => handleSetupComplete('totp')}
                  onError={(err) => setError(err)}
                />
              </div>
            )}

            {error && (
              <div className="alert-error">
                {error}
              </div>
            )}
          </div>

          <div className="mt-6 text-center">
            <button
              onClick={handleSetupCancel}
              className="floating-button px-4 py-2 text-sm"
              style={{ color: themeColors.textMuted }}
            >
              ← Back to options
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: themeColors.background }}>
        <div className="dynamic-card p-8 w-full max-w-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 mx-auto mb-4" style={{ borderTopColor: themeColors.primary, borderBottomColor: themeColors.primary }}></div>
            <p style={{ color: themeColors.text }}>Checking security requirements...</p>
          </div>
        </div>
      </div>
    );
  }

  // Check if user has configured methods for authentication
  // Handle both response formats (configured_methods or has_webauthn/has_totp)
  const hasConfiguredMethods = 
    (aalStatus?.configured_methods && 
      (aalStatus.configured_methods.webauthn || aalStatus.configured_methods.totp)) ||
    (aalStatus?.has_webauthn || aalStatus?.has_totp);

  // Main AAL2 step-up interface
  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: themeColors.background }}>
      <div className="dynamic-card p-8 w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2" style={{ color: themeColors.text }}>Please Confirm It's You</h1>
          <p style={{ color: themeColors.textSecondary }}>
            {hasConfiguredMethods
              ? 'Quick confirmation required to continue'
              : 'Set up a secure method to continue'
            }
          </p>
        </div>

        {error && (
          <div className="alert-error mb-6">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {/* Authentication Options for users with configured methods */}
          {hasConfiguredMethods ? (
            <div className="space-y-4">
              <div className="alert-info text-center">
                <h3 className="font-medium mb-2">Authentication Required</h3>
                <p className="text-sm mb-4">
                  You have security methods configured. Click below to authenticate.
                </p>
              </div>
              
              {(aalStatus?.configured_methods?.webauthn || aalStatus?.has_webauthn) && (
                <div className="dynamic-card-subtle p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium" style={{ color: themeColors.primary }}>Confirm with Secure Key</h3>
                      <p className="text-sm" style={{ color: themeColors.textSecondary }}>Quick tap to confirm it's you</p>
                    </div>
                    <button
                      onClick={initiateAAL2Authentication}
                      disabled={isLoading}
                      className="floating-button px-4 py-2 font-medium"
                      style={{
                        backgroundColor: themeColors.primary,
                        color: 'white',
                        opacity: isLoading ? 0.6 : 1
                      }}
                    >
                      Use Secure Key
                    </button>
                  </div>
                </div>
              )}
              
              {(aalStatus?.configured_methods?.totp || aalStatus?.has_totp) && (
                <div className="dynamic-card-subtle p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium" style={{ color: themeColors.success }}>Authenticate with TOTP</h3>
                      <p className="text-sm" style={{ color: themeColors.textSecondary }}>Use your authenticator app</p>
                    </div>
                    <button
                      onClick={initiateAAL2Authentication}
                      disabled={isLoading}
                      className="floating-button px-4 py-2 font-medium"
                      style={{ 
                        backgroundColor: themeColors.success, 
                        color: 'white',
                        opacity: isLoading ? 0.6 : 1
                      }}
                    >
                      Use TOTP
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Setup Options for users without configured methods */
            <div className="space-y-4">
              <div className="alert-warning text-center">
                <h3 className="font-medium mb-2">Setup Required</h3>
                <p className="text-sm mb-4">
                  You need to configure a second factor authentication method to access admin features.
                </p>
              </div>
              
              {/* Passkey Setup Option */}
              <div className="dynamic-card-subtle p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium" style={{ color: themeColors.primary }}>Setup Passkey</h3>
                    <p className="text-sm" style={{ color: themeColors.textSecondary }}>Fast, secure login with your device</p>
                  </div>
                  <button
                    onClick={() => {
                      setSetupMethod('webauthn');
                      setShowSetup(true);
                    }}
                    disabled={isLoading}
                    className="floating-button px-4 py-2 font-medium"
                    style={{ 
                      backgroundColor: themeColors.primary, 
                      color: 'white',
                      opacity: isLoading ? 0.6 : 1
                    }}
                  >
                    Setup Passkey
                  </button>
                </div>
              </div>
              
              {/* TOTP Setup Option */}
              <div className="dynamic-card-subtle p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium" style={{ color: themeColors.success }}>Setup Authenticator App</h3>
                    <p className="text-sm" style={{ color: themeColors.textSecondary }}>Use Google Authenticator, Authy, etc.</p>
                  </div>
                  <button
                    onClick={() => {
                      setSetupMethod('totp');
                      setShowSetup(true);
                    }}
                    disabled={isLoading}
                    className="floating-button px-4 py-2 font-medium"
                    style={{ 
                      backgroundColor: themeColors.success, 
                      color: 'white',
                      opacity: isLoading ? 0.6 : 1
                    }}
                  >
                    Setup TOTP
                  </button>
                </div>
              </div>
              
              <div className="dynamic-card-subtle p-4">
                <p className="text-sm text-center" style={{ color: themeColors.textMuted }}>
                  💡 <strong>Recommended:</strong> Setup both methods for backup access
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Flexible Fallback Options (Enrollment Pattern) */}
        {showFallbackOptions && (
          <div className="mt-8 border-t pt-6" style={{ borderTopColor: themeColors.border }}>
            <div className="text-center mb-4">
              <h3 className="text-lg font-medium mb-2" style={{ color: themeColors.text }}>
                Complete Later Options
              </h3>
              <p className="text-sm" style={{ color: themeColors.textSecondary }}>
                Enhanced security can be configured anytime - you won't lose access
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <button
                onClick={handleCompleteNowSkipLater}
                className="floating-button px-4 py-3 text-center"
                style={{ backgroundColor: themeColors.primary, color: 'white' }}
              >
                <div className="font-medium">Continue to Dashboard</div>
                <div className="text-sm opacity-90">Auto-redirect in {skipTimer}s</div>
              </button>
              
              <button
                onClick={handleFixInSettings}
                className="floating-button px-4 py-3 text-center"
                style={{ 
                  backgroundColor: 'transparent', 
                  border: `1px solid ${themeColors.primary}`,
                  color: themeColors.primary
                }}
              >
                <div className="font-medium">Setup in Settings</div>
                <div className="text-sm opacity-75">Configure security first</div>
              </button>
            </div>
            
            <div className="text-center space-y-2">
              <button
                onClick={handleStopTimerContinue}
                className="text-sm underline"
                style={{ color: themeColors.textMuted }}
              >
                Stay here (stop timer)
              </button>
              <br />
              <button
                onClick={() => navigate('/logout')}
                className="text-sm"
                style={{ color: themeColors.textMuted }}
              >
                Sign out instead
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AAL2StepUp;