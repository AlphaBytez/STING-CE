/**
 * SimpleEnrollment - Streamlined 2FA enrollment for authenticated users
 * 
 * Features:
 * - Uses proven custom WebAuthn APIs
 * - Clear TOTP → Passkey flow
 * - No pre-auth complexity
 * - Direct API calls to working endpoints
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { Shield, CheckCircle, Key, Fingerprint, AlertCircle, ArrowRight, ExternalLink } from 'lucide-react';
import axios from 'axios';
import IntegratedTOTPSetup from './IntegratedTOTPSetup';
import { processWebAuthnOptions, processCredentialForBackend } from '../../utils/webauthnUtils';

const SimpleEnrollment = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoading } = useKratos();
  
  // State management
  const [step, setStep] = useState('totp'); // totp, passkey, complete
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true); // Loading state for auth check
  const [userEmail, setUserEmail] = useState(''); // Store email from Kratos session
  const [userRole, setUserRole] = useState('user'); // Store role from Kratos session
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasTOTPConfigured, setHasTOTPConfigured] = useState(false); // Track if TOTP is already setup
  
  // Removed TOTP state - now handled by IntegratedTOTPSetup component
  
  // User info
  // Use stored values from Kratos session check
  const isAdmin = userRole === 'admin';

  // Check authentication and existing 2FA status
  useEffect(() => {
    const verifyKratosSession = async () => {
      setIsCheckingAuth(true);
      try {
        // CRITICAL FIX: Check Kratos session directly instead of relying on Flask backend
        console.log('🔒 Checking Kratos session directly...');
        const response = await fetch('/.ory/sessions/whoami', { 
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });
        
        if (response.ok) {
          const session = await response.json();
          console.log('✅ Kratos session valid:', session?.identity?.traits?.email);
          
          // Store user info from Kratos session
          setUserEmail(session?.identity?.traits?.email || 'Unknown');
          setUserRole(session?.identity?.traits?.role || 'user');
          
          // Check if user already has 2FA configured
          await checkExisting2FA();
        } else {
          console.log('❌ No valid Kratos session found, status:', response.status);
          
          // Wait a bit for session to propagate before redirecting
          setTimeout(() => {
            console.log('🔒 Redirecting to login after grace period');
            navigate('/login');
          }, 2000);
        }
      } catch (error) {
        console.error('🔒 Error checking Kratos session:', error);
        navigate('/login');
      } finally {
        setIsCheckingAuth(false);
      }
    };

    // Only check if not loading
    if (!isLoading) {
      verifyKratosSession();
    }
  }, [isLoading, navigate]);

  const checkExisting2FA = async () => {
    try {
      console.log('🔍 Checking existing 2FA configuration...');
      
      // AGGRESSIVE ENROLLMENT FIX: Check React Router location state first
      if (location.state?.from === 'aggressive' || location.state?.hasExistingTOTP) {
        console.log('🔒 User redirected from aggressive enrollment - has TOTP, needs passkey');
        console.log('🔒 Location state:', location.state);
        
        // Store user email from location state
        if (location.state?.userEmail) {
          setUserEmail(location.state.userEmail);
        }
        
        setHasTOTPConfigured(true); // Mark TOTP as already configured
        setStep('passkey');
        sessionStorage.setItem('aggressive_enrollment', 'false'); // Clear flag
        return;
      }
      
      // Fallback: Check URL params and sessionStorage
      const urlParams = new URLSearchParams(window.location.search);
      const fromAggressiveEnrollment = urlParams.get('from') === 'aggressive' || 
                                       sessionStorage.getItem('aggressive_enrollment') === 'true';
      
      if (fromAggressiveEnrollment) {
        console.log('🔒 User redirected from aggressive enrollment (URL/session) - has TOTP, needs passkey');
        setStep('passkey');
        sessionStorage.setItem('aggressive_enrollment', 'false'); // Clear flag
        return;
      }
      
      const [totpResponse, passkeyResponse] = await Promise.all([
        axios.get('/api/totp/totp-status', { withCredentials: true }),
        axios.get('/api/webauthn/passkeys', { withCredentials: true })
      ]);

      const hasTOTP = totpResponse.data?.enabled === true;
      const hasPasskey = passkeyResponse.data?.passkeys?.length > 0;

      console.log('🔒 Existing 2FA status:', { hasTOTP, hasPasskey });

      if (hasTOTP && hasPasskey) {
        // User has everything configured
        console.log('🔒 User already has complete 2FA setup, redirecting to dashboard');
        navigate('/dashboard');
        return;
      } else if (hasTOTP) {
        // Skip to passkey setup
        console.log('🔒 User has TOTP, skipping to passkey setup');
        setStep('passkey');
      }
      // Otherwise start with TOTP setup

    } catch (error) {
      console.error('🔒 Error checking existing 2FA:', error);
      // FALLBACK: If we get 401 errors, check location state for hints
      if (error.response?.status === 401) {
        console.log('🔒 Got 401 - checking location state for enrollment hints');
        
        // Check React Router location state
        if (location.state?.from === 'aggressive' || location.state?.hasExistingTOTP) {
          console.log('🔒 Location state indicates user has TOTP, needs passkey setup');
          if (location.state?.userEmail) {
            setUserEmail(location.state.userEmail);
          }
          setStep('passkey');
          return;
        }
        
        // Also check sessionStorage flags
        if (sessionStorage.getItem('has_existing_totp') === 'true') {
          console.log('🔒 SessionStorage indicates user has TOTP, needs passkey setup');
          setStep('passkey');
          return;
        }
      }
      // Continue with enrollment anyway
    }
  };

  const handlePostTOTPFlow = async (_method, _info) => {
    console.log('🔒 Post-TOTP flow triggered. Proceeding directly to passkey setup.');
    setSuccess('TOTP configured! Proceeding to passkey setup...');
    setStep('passkey');
  };

  const checkCurrentAuthFactors = async () => {
    console.log('🔒 Checking current authentication factors...');
    
    try {
      // Check both Kratos session and STING backend for comprehensive status
      const [kratosResponse, stingResponse] = await Promise.allSettled([
        fetch('/.ory/sessions/whoami', {
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        }),
        axios.get('/api/auth/me', { 
          headers: { 'Accept': 'application/json' },
          withCredentials: true 
        })
      ]);

      let factors = {
        totp: false,
        webauthn: false,
        currentAAL: 'aal1',
        userRole: userRole,
        isAdmin: isAdmin,
        canProceed: false,
        needsAAL2StepUp: false,
        session: null,
        error: null
      };

      // Parse Kratos session if available
      if (kratosResponse.status === 'fulfilled' && kratosResponse.value.ok) {
        const kratosSession = await kratosResponse.value.json();
        factors.session = kratosSession;
        factors.currentAAL = kratosSession.authenticator_assurance_level || kratosSession.aal || 'aal1';
        
        // Check authentication methods from Kratos
        const methods = kratosSession.identity?.credentials || {};
        factors.totp = !!(methods.totp?.identifiers?.length > 0);
        factors.webauthn = !!(methods.webauthn?.identifiers?.length > 0);
        
        console.log('🔒 Kratos factors:', { 
          totp: factors.totp, 
          webauthn: factors.webauthn, 
          aal: factors.currentAAL 
        });
      }

      // Parse STING backend response if available (may have additional context)
      if (stingResponse.status === 'fulfilled') {
        const stingData = stingResponse.value.data;
        if (stingData.user) {
          factors.userRole = stingData.user.role || userRole;
          factors.isAdmin = factors.userRole === 'admin';
          
          // STING backend might have more detailed auth method info
          if (stingData.auth_methods) {
            factors.totp = factors.totp || stingData.auth_methods.totp || false;
            factors.webauthn = factors.webauthn || stingData.auth_methods.webauthn || false;
          }
        }
      }

      return factors;
      
    } catch (error) {
      console.error('🔒 Error checking auth factors:', error);
      return {
        totp: false,
        webauthn: false,
        currentAAL: 'aal1',
        userRole: userRole,
        isAdmin: isAdmin,
        canProceed: false,
        needsAAL2StepUp: true,
        session: null,
        error: error.message
      };
    }
  };

  const verifyAAL2Eligibility = async (factors) => {
    console.log('🔒 Verifying AAL2 eligibility...', factors);
    
    const status = {
      hasRequiredFactors: false,
      isAtAAL2: false,
      needsStepUp: false,
      canProceedToPasskey: false,
      recommendation: 'unknown',
      reason: ''
    };

    // Check if user has sufficient factors for AAL2
    status.hasRequiredFactors = factors.totp || factors.webauthn;
    status.isAtAAL2 = factors.currentAAL === 'aal2';

    if (!status.hasRequiredFactors) {
      // Edge case: User somehow lost their factors
      status.recommendation = 'restart_enrollment';
      status.reason = 'No valid authentication factors found. Need to restart enrollment.';
      return status;
    }

    if (status.isAtAAL2) {
      // Perfect case: Already at AAL2
      status.canProceedToPasskey = true;
      status.recommendation = 'proceed_to_passkey';
      status.reason = 'Session already at AAL2, can proceed directly to passkey setup.';
      return status;
    }

    // Most common case: Has factors but not at AAL2
    if (factors.isAdmin) {
      // Admins MUST have AAL2 for passkey setup
      status.needsStepUp = true;
      status.recommendation = 'force_aal2_stepup';
      status.reason = 'Admin users require AAL2 authentication before passkey setup.';
    } else {
      // Regular users - we can try passkey setup and gracefully handle failures
      status.canProceedToPasskey = true;
      status.needsStepUp = true; // Flag for graceful handling
      status.recommendation = 'proceed_with_fallback';
      status.reason = 'Regular user - will attempt passkey setup with AAL2 fallback handling.';
    }

    return status;
  };

  const handleAAL2Flow = async (aal2Status, factors) => {
    console.log('🔒 Handling AAL2 flow:', aal2Status);

    // Wait for any session propagation
    await new Promise(resolve => setTimeout(resolve, 1500));

    switch (aal2Status.recommendation) {
      case 'restart_enrollment':
        setError(`Authentication setup incomplete: ${aal2Status.reason} Please restart the enrollment process.`);
        setTimeout(() => {
          // Clear any stale session data and restart
          sessionStorage.removeItem('has_existing_totp');
          navigate('/enrollment', { replace: true, state: { restart: true } });
        }, 3000);
        break;

      case 'proceed_to_passkey':
        setSuccess('✅ Session verified at AAL2! Setting up passkey...');
        setStep('passkey');
        break;

      case 'force_aal2_stepup':
        setError(`Admin session needs AAL2 elevation: ${aal2Status.reason}`);
        setTimeout(() => {
          navigate('/security-upgrade', {
            state: {
              reason: 'AAL2 required for admin passkey setup',
              fromEnrollment: true,
              requiresAAL2: true,
              availableFactors: {
                totp: factors.totp,
                webauthn: factors.webauthn
              }
            }
          });
        }, 2500);
        break;

      case 'proceed_with_fallback':
        setSuccess(`TOTP configured! ${aal2Status.reason}`);
        // Set a flag so passkey setup can handle AAL2 failures gracefully
        sessionStorage.setItem('aal2_fallback_mode', 'true');
        setStep('passkey');
        break;

      default:
        // Unknown state - be defensive
        console.warn('🔒 Unknown AAL2 status, falling back to basic flow');
        setSuccess('TOTP configured! Attempting passkey setup...');
        setStep('passkey');
        break;
    }
  };

  // Removed setupTOTP function - now handled by IntegratedTOTPSetup component

  // Removed verifyTOTP function - now handled by IntegratedTOTPSetup component

  // Use custom STING WebAuthn APIs (working implementation)
  const setupPasskeyViaCustomAPI = async () => {
    console.log('🔒 Setting up passkey using custom STING WebAuthn APIs...');
    
    try {
      // Step 1: Begin registration
      console.log('🔒 Step 1: Beginning passkey registration...');
      const beginResponse = await axios.post('/api/webauthn/register/begin', {
        displayName: `${userEmail} - Enrollment Passkey`
      }, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      if (!beginResponse.data.success) {
        throw new Error(beginResponse.data.error || 'Failed to begin passkey registration');
      }

      const options = beginResponse.data.options;
      console.log('🔒 Registration options received:', options);

      // Process options to convert base64url strings to ArrayBuffers
      console.log('🔒 Converting WebAuthn options for browser API...');
      const processedOptions = processWebAuthnOptions(options);
      console.log('🔒 Processed options ready for WebAuthn API:', processedOptions);

      // Step 2: Create WebAuthn credential
      console.log('🔒 Step 2: Creating WebAuthn credential...');
      const credential = await navigator.credentials.create({
        publicKey: processedOptions
      });

      // Validate credential before accessing properties
      if (!credential || !credential.id || !credential.rawId || !credential.response) {
        console.error('❌ Invalid credential received from authenticator:', credential);
        throw new Error('Invalid credential received from authenticator');
      }

      console.log('🔒 WebAuthn credential created successfully');

      // Process credential for backend submission
      console.log('🔒 Converting credential for backend submission...');
      const processedCredential = processCredentialForBackend(credential);

      // Step 3: Complete registration
      console.log('🔒 Step 3: Completing passkey registration...');
      const completeResponse = await axios.post('/api/webauthn/register/complete', {
        credential: processedCredential
      }, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      if (!completeResponse.data.success) {
        throw new Error(completeResponse.data.error || 'Failed to complete passkey registration');
      }

      console.log('✅ Passkey registration completed successfully!');
      setSuccess('Passkey registered successfully!');
      setStep('complete');
      setError('');

    } catch (error) {
      console.error('🔒 Custom WebAuthn registration failed:', error);
      throw error;
    }
  };

  // Legacy Kratos function (kept for reference but not used)
  const setupPasskeyViaKratosLegacy = async () => {
    console.log('🔒 [LEGACY] Enhanced passkey setup with direct Kratos browser flow...');
    
    try {
      // Load WebAuthn script if needed (mirror SecuritySettings)
      if (!window.oryWebAuthnRegistration) {
        console.log('⏳ Loading WebAuthn script...');
        setIsProcessing(true);
        
        // Legacy code - flow variable not defined in this context
        // const scriptNode = flow.ui.nodes.find(n => n.type === 'script' && n.group === 'webauthn');
        const scriptNode = null;
        if (scriptNode?.attributes?.src) {
          await new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${scriptNode.attributes.src}"]`);
            if (existing) {
              resolve();
              return;
            }
            
            const script = document.createElement('script');
            script.src = scriptNode.attributes.src;
            script.async = true;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
          });
        }
      }
      
      // Enhanced navigation prevention (mirror SecuritySettings)
      const originalPushState = window.history.pushState;
      const originalReplaceState = window.history.replaceState;
      const originalAssign = window.location.assign;
      const originalReplace = window.location.replace;
      
      // Override navigation methods to prevent Kratos redirects
      const preventKratosNavigation = () => {
        const shouldBlockRedirect = (url) => {
          if (!url) return false;
          return url.includes('ory') || url.includes('kratos') || url.includes('self-service');
        };
        
        window.history.pushState = (state, title, url) => {
          if (shouldBlockRedirect(url)) {
            console.log('🔒 Blocked pushState redirect to:', url);
            return;
          }
          return originalPushState.call(window.history, state, title, url);
        };
        
        window.history.replaceState = (state, title, url) => {
          if (shouldBlockRedirect(url)) {
            console.log('🔒 Blocked replaceState redirect to:', url);
            return;
          }
          return originalReplaceState.call(window.history, state, title, url);
        };
      };
      
      // Start redirect prevention
      preventKratosNavigation();
      
      // Restore methods after 15 seconds
      setTimeout(() => {
        window.history.pushState = originalPushState;
        window.history.replaceState = originalReplaceState;
        console.log('🔒 Redirect prevention restored');
      }, 15000);
      
      // 🔒 BIOMETRIC SERVICE INTEGRATION (mirror SecuritySettings)
      const originalCredentialsCreate = navigator.credentials.create;
      navigator.credentials.create = async (options) => {
        console.log('🔒 WebAuthn create intercepted, calling original...');
        try {
          const credential = await originalCredentialsCreate.call(navigator.credentials, options);
          console.log('🔒 WebAuthn credential created, processing with biometric service...');

          // Validate credential before accessing properties
          if (!credential || !credential.id || !credential.rawId || !credential.response) {
            console.error('❌ Invalid credential received from authenticator:', credential);
            throw new Error('Invalid credential received from authenticator');
          }

          // Process credential for biometric detection (if biometric service available)
          if (window.biometricService?.processCredential) {
            const biometricResult = await window.biometricService.processCredential(credential);
            console.log('🔒 Biometric processing result:', biometricResult);

            if (biometricResult.success && biometricResult.biometric) {
              console.log('🔒 Biometric authentication detected! AAL2 should be available.');
            } else {
              console.log('🔒 Standard passkey detected (no biometric verification).');
            }
          }

          return credential;
        } catch (error) {
          console.error('🔒 Error in WebAuthn interception:', error);
          throw error;
        } finally {
          // Always restore original function
          navigator.credentials.create = originalCredentialsCreate;
          console.log('🔒 WebAuthn interception cleaned up');
        }
      };
      
      // Trigger WebAuthn registration (mirror SecuritySettings approach)
      console.log('🔒 Triggering WebAuthn registration...');
      
      if (window.oryWebAuthnRegistration) {
        // Legacy code - triggerNode not defined in this context  
        console.log('🔒 Legacy function - cannot call oryWebAuthnRegistration without proper setup');
        // const webauthnOptions = JSON.parse(triggerNode.attributes.value);
        // window.oryWebAuthnRegistration(webauthnOptions);
      } else {
        // Legacy code - button not defined in this context
        console.log('🔒 Legacy function - cannot trigger button click without proper setup');
        // button.click();
      }

      // Monitor for completion (mirror SecuritySettings approach)
      let attempts = 0;
      const initialCount = 0; // Start with 0 for enrollment
      
      const checkInterval = setInterval(async () => {
        attempts++;
        
        try {
          // Check for new passkeys by fetching fresh settings flow
          const checkResponse = await axios.get('/api/auth/settings', {
            headers: { 'Accept': 'application/json' },
            withCredentials: true
          });
          
          const checkFlow = checkResponse.data;
          const checkNodes = checkFlow.ui.nodes.filter(n => n.group === 'webauthn');
          const removeNodes = checkNodes.filter(n => 
            n.attributes?.name === 'webauthn_remove' && 
            n.attributes?.type === 'submit'
          );
          
          // Check if passkey was created
          if (removeNodes.length > initialCount) {
            console.log('✅ Passkey registration completed!');
            clearInterval(checkInterval);
            
            setSuccess('Passkey registered successfully!');
            setIsProcessing(false);
            
            // Clean up (no form to remove in this legacy implementation)
            
            setTimeout(() => {
              setStep('complete');
              setError('');
            }, 1500);
            return;
          }
        } catch (err) {
          console.error('Error checking for new passkey:', err);
        }
        
        if (attempts >= 120) { // 2 minutes timeout
          clearInterval(checkInterval);
          setError('Passkey registration timed out. Please try again.');
          setIsProcessing(false);
          
          // No form to remove in this legacy implementation
        }
      }, 1000);
    } catch (error) {
      console.error('🔒 Kratos WebAuthn fallback failed:', error);
      throw error;
    }
  };


  const completeEnrollment = () => {
    // Clear any enrollment flags
    sessionStorage.removeItem('aalCheckCompleted');
    sessionStorage.removeItem('needsAAL2Redirect');
    
    // CRITICAL: Clear stale auth state that can cause account corruption
    sessionStorage.removeItem('sting_recent_auth');
    
    console.log('🔒 Session storage cleaned, enrollment complete');
    
    // ALWAYS redirect to dashboard after successful enrollment
    console.log('🔒 Enrollment complete, redirecting to dashboard for all users');
    navigate('/dashboard');
  };

  // Removed TOTP setup useEffect - now handled by IntegratedTOTPSetup component

  // Show loading spinner while checking auth or loading
  if (isLoading || isCheckingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-400"></div>
          <p className="text-gray-400 mt-4">
            {isCheckingAuth ? 'Verifying authentication...' : 'Loading...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Shield className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isAdmin ? 'Admin Security Setup' : 'Security Setup Required'}
          </h1>
          <p className="text-gray-300 mb-2">
            Welcome, <span className="text-blue-400">{userEmail}</span>
          </p>
          <p className="text-gray-400">
            {isAdmin 
              ? 'Admin accounts require enhanced security. Set up TOTP first, then add passkey protection.'
              : 'Secure your account with two-factor authentication for AI operations.'
            }
          </p>
        </div>

        {/* Progress indicator */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${step === 'totp' ? 'text-blue-400' : step === 'passkey' || step === 'complete' ? 'text-green-400' : 'text-gray-400'}`}>
              <Key className="w-5 h-5" />
              <span className="font-medium">TOTP Setup</span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500" />
            <div className={`flex items-center space-x-2 ${step === 'passkey' ? 'text-blue-400' : step === 'complete' ? 'text-green-400' : 'text-gray-400'}`}>
              <Fingerprint className="w-5 h-5" />
              <span className="font-medium">Passkey Setup</span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500" />
            <div className={`flex items-center space-x-2 ${step === 'complete' ? 'text-green-400' : 'text-gray-400'}`}>
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Complete</span>
            </div>
          </div>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500/20 border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6 flex items-center">
            <CheckCircle className="w-5 h-5 mr-2" />
            {success}
          </div>
        )}

        {/* TOTP Setup Step */}
        {step === 'totp' && (
          <div>
            <h2 className="text-xl font-semibold text-white mb-4">Step 1: Authenticator App Setup</h2>
            
            {/* Show skip button ONLY for non-admins or if TOTP is already configured */}
            {(!isAdmin || hasTOTPConfigured) && (
              <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-blue-300 font-medium">Already have TOTP configured?</p>
                    <p className="text-gray-400 text-sm mt-1">If you've already set up an authenticator app, you can proceed to passkey setup.</p>
                  </div>
                  <button
                    onClick={() => {
                      console.log('🔒 User indicates TOTP is already configured, skipping to passkey');
                      setStep('passkey');
                    }}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                  >
                    Skip to Passkey →
                  </button>
                </div>
              </div>
            )}
            
            {/* Warning for admins */}
            {isAdmin && !hasTOTPConfigured && (
              <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-red-300 font-medium">Admin Account Requirement</p>
                    <p className="text-gray-400 text-sm mt-1">As an administrator, you must complete both TOTP and Passkey setup to access the dashboard.</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Use the integrated TOTP component */}
            <IntegratedTOTPSetup 
              onSetupComplete={async (method, info) => {
                console.log(`✅ TOTP setup completed via ${method}`, info);
                setIsProcessing(true);
                
                try {
                  // ✅ ENHANCED: More robust AAL verification and handling
                  await handlePostTOTPFlow(method, info);
                } catch (error) {
                  console.error('🔒 Error in post-TOTP flow:', error);
                  // Fall back to basic passkey setup
                  setSuccess('TOTP configured! Proceeding to passkey setup...');
                  setStep('passkey');
                } finally {
                  setIsProcessing(false);
                }
              }}
            />
          </div>
        )}

        {/* Passkey Setup Step */}
        {step === 'passkey' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">
              {hasTOTPConfigured ? 'Final Step: Passkey Setup' : 'Step 2: Passkey Setup (Recommended)'}
            </h2>
            
            {/* Show TOTP success message if redirected from aggressive enrollment */}
            {hasTOTPConfigured && (
              <div className="bg-green-500/20 border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-4 flex items-center">
                <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                <div>
                  <p className="font-medium">TOTP Authentication Already Configured ✓</p>
                  <p className="text-sm mt-1">Your authenticator app is set up. Now add a passkey for complete security.</p>
                </div>
              </div>
            )}
            
            <div className="space-y-6">
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                <p className="text-blue-200 text-sm">
                  <strong>Passkeys</strong> use your device's built-in security (fingerprint, face recognition, PIN) 
                  for convenient and secure authentication without passwords.
                </p>
              </div>

              <div className="text-center space-y-4">
                <Fingerprint className="w-16 h-16 text-blue-400 mx-auto" />
                <p className="text-gray-300">
                  Your device will prompt you to use biometric authentication or PIN.
                </p>
                
                <div className="flex space-x-4 justify-center">
                  <button
                    onClick={async () => {
                      setIsProcessing(true);
                      setError('');
                      
                      try {
                        await setupPasskeyViaCustomAPI();
                      } catch (error) {
                        console.error('🔒 Passkey setup error:', error);
                        
                        // Check if we're in fallback mode and handle gracefully
                        const fallbackMode = sessionStorage.getItem('aal2_fallback_mode') === 'true';
                        
                        if (fallbackMode && (error.message?.includes('AAL2') || error.message?.includes('session') || error.response?.status === 403)) {
                          // AAL2 related error in fallback mode - offer alternatives
                          setError('Passkey setup requires additional authentication. Please complete AAL2 step-up first.');
                          setTimeout(() => {
                            navigate('/security-upgrade', {
                              state: {
                                reason: 'AAL2 required for passkey setup',
                                fromPasskeySetup: true,
                                fallbackMode: true
                              }
                            });
                          }, 3000);
                        } else if (error.response?.status === 401) {
                          // Authentication issue - redirect to login
                          setError('Session expired. Please log in again.');
                          setTimeout(() => navigate('/login'), 2000);
                        } else if (error.name === 'NotSupportedError') {
                          // WebAuthn not supported
                          setError('Passkeys are not supported on this device or browser.');
                        } else if (error.name === 'SecurityError') {
                          // Security/origin error
                          setError('Security error: Please ensure you\'re using HTTPS and the correct domain.');
                        } else if (error.name === 'NotAllowedError') {
                          // User cancelled or timeout
                          setError('Passkey setup was cancelled or timed out. Please try again.');
                        } else {
                          // Generic error
                          setError(`Passkey setup failed: ${error.message || 'Unknown error'}`);
                        }
                      } finally {
                        setIsProcessing(false);
                        // Clear fallback mode flag after attempt
                        sessionStorage.removeItem('aal2_fallback_mode');
                      }
                    }}
                    disabled={isProcessing}
                    className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                  >
                    {isProcessing ? 'Setting up...' : 'Set Up Passkey'}
                  </button>
                </div>

              </div>
            </div>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="bg-gray-800 rounded-lg p-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-4">Security Setup Complete!</h2>
            
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6">
              <p className="text-green-200">
                Your account is now secured with two-factor authentication. 
                You can access all AI operations and admin features.
              </p>
            </div>

            <button
              onClick={completeEnrollment}
              className="bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-8 rounded-lg transition duration-200"
            >
              Access Dashboard
            </button>
          </div>
        )}

        {/* Help Section */}
        <div className="mt-8 text-center">
          <p className="text-gray-400 text-sm">
            Having trouble? Contact support or{' '}
            <a 
              href="/settings/security" 
              className="text-blue-400 hover:text-blue-300 underline"
            >
              use advanced settings
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SimpleEnrollment;