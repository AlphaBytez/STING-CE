import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ColonyLoadingScreen from '../common/ColonyLoadingScreen';
import { useColonyLoading } from '../../hooks/useColonyLoading';

const AAL2PasskeyVerify = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Colony loading screen
  const { showAAL2Loading, hideLoading } = useColonyLoading();
  const [userEmail, setUserEmail] = useState('');
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [flowId, setFlowId] = useState(null);
  const [verificationStarted, setVerificationStarted] = useState(false);
  const ceremonyCompleteRef = useRef(false);

  // Check user email and biometric availability
  useEffect(() => {
    const fetchUserEmail = async () => {
      try {
        const response = await fetch('/api/auth/me', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          console.log('🔍 AAL2 Passkey - Session data received:', data);
          // Try multiple possible locations for email based on Flask session format
          const email = data.identity?.traits?.email || 
                       data.user?.email || 
                       data.email || 
                       'user@example.com';
          setUserEmail(email);
          console.log('🔐 Retrieved user email for AAL2 passkey:', email);
        } else {
          console.log('🔍 AAL2 Passkey - Session check failed:', response.status, response.statusText);
        }
      } catch (error) {
        console.log('Could not fetch user email:', error);
        setUserEmail('user@example.com');
      }
    };

    const checkBiometricAvailability = async () => {
      // Check WebAuthn availability
      if (window.PublicKeyCredential) {
        try {
          const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          setBiometricAvailable(available);
        } catch (e) {
          console.log('Could not check biometric availability:', e);
          setBiometricAvailable(false);
        }
      }
    };

    fetchUserEmail();
    checkBiometricAvailability();
  }, []);

  // Load Kratos WebAuthn script for passkey functionality
  useEffect(() => {
    const loadKratosWebAuthnScript = () => {
      // Check if script is already loaded
      if (window.oryWebAuthnLogin) {
        console.log('🔐 Kratos WebAuthn script already loaded');
        return;
      }

      console.log('🔐 Loading Kratos WebAuthn script for AAL2 passkey verification...');
      const script = document.createElement('script');
      if (!script) {
        console.error('❌ Failed to create script element for Kratos WebAuthn');
        setError('Failed to create authentication components');
        return;
      }

      try {
        script.src = '/.well-known/ory/webauthn.js';
        script.async = true;
        script.onload = () => {
          console.log('✅ Kratos WebAuthn script loaded successfully');
        };
        script.onerror = () => {
          console.error('❌ Failed to load Kratos WebAuthn script');
          setError('Failed to load authentication components');
        };

        if (document.head) {
          document.head.appendChild(script);
        } else {
          console.error('❌ document.head is null, cannot append WebAuthn script');
          setError('Failed to load authentication components');
        }
      } catch (error) {
        console.error('❌ Error setting up WebAuthn script:', error);
        setError('Failed to load authentication components');
      }
    };

    loadKratosWebAuthnScript();
  }, []);

  // Timeout for AAL2 verification
  useEffect(() => {
    if (!verificationStarted) return;

    // Set a backup timeout in case the ceremony fails silently
    const timeoutId = setTimeout(() => {
      if (!ceremonyCompleteRef.current) {
        console.log('⏰ Passkey ceremony timed out - redirecting back to method selection');

        // Get return URL to preserve it
        const returnTo = searchParams.get('return_to') || '/dashboard/settings?tab=security';
        const reason = searchParams.get('reason') || 'operation';

        // Redirect back to method selection with timeout message
        const methodSelectionUrl = `/security-upgrade?passkey_timeout=true&reason=${reason}&return_to=${encodeURIComponent(returnTo)}`;

        setError('Passkey verification timed out');
        setLoading(false);
        setVerificationStarted(false);
        hideLoading();

        // Give user a moment to see the error, then redirect
        setTimeout(() => {
          window.location.href = methodSelectionUrl;
        }, 2000);
      }
    }, 30000);

    return () => clearTimeout(timeoutId);
  }, [verificationStarted]);


  const completeAAL2Verification = async () => {
    try {
      ceremonyCompleteRef.current = true; // Mark ceremony as complete

      const returnTo = searchParams.get('return_to') || '/dashboard';

      // Verify AAL2 elevation with Flask backend
      const completeResponse = await fetch('/api/aal2/challenge/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          verification_method: 'webauthn',
          flow_id: flowId,
          // Include a timestamp to prevent replay attacks
          timestamp: new Date().toISOString()
        })
      });

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json();
        console.error('❌ Flask AAL2 elevation failed:', errorData);

        // SECURITY FIX: Don't proceed if Flask AAL2 elevation fails
        // This is critical - we must NOT grant access without proper AAL2
        throw new Error('AAL2 elevation failed - access denied');
      }

      const completeData = await completeResponse.json();
      console.log('✅ Flask AAL2 elevation successful!', completeData);

      // Only store success markers if actually successful
      localStorage.setItem('sting_last_passkey_user', userEmail);
      localStorage.setItem('sting_aal2_verified', 'true');
      localStorage.setItem('sting_aal2_timestamp', new Date().toISOString());

      // Navigate to the protected resource only after successful AAL2
      console.log('🔐 AAL2 verification complete, redirecting to:', returnTo);
      window.location.href = returnTo;

    } catch (error) {
      console.error('❌ AAL2 completion failed:', error);

      // SECURITY FIX: Do NOT redirect to dashboard on failure
      // Instead, redirect back to security-upgrade page
      const returnTo = searchParams.get('return_to') || '/dashboard';
      const reason = searchParams.get('reason') || 'operation';

      setError('AAL2 verification failed. Please try again.');
      setLoading(false);
      setVerificationStarted(false);
      hideLoading();

      // Redirect back to method selection
      setTimeout(() => {
        window.location.href = `/security-upgrade?aal2_failed=true&reason=${reason}&return_to=${encodeURIComponent(returnTo)}`;
      }, 2000);
    }
  };

  const handlePasskeyAuth = async () => {
    setLoading(true);
    setError('');
    setVerificationStarted(true);
    ceremonyCompleteRef.current = false;

    // Show colony loading for AAL2 verification
    showAAL2Loading();

    console.log('🔐 Starting AAL2 passkey authentication...');

    try {
      // MATCHING TOTP APPROACH: Use ?aal=aal2 directly like TOTP does
      // TOTP successfully elevates Kratos to AAL2, let's try the same for passkey
      console.log('🔐 Initializing AAL2 flow (matching TOTP approach)...');
      const flowResponse = await fetch(`/.ory/self-service/login/browser?aal=aal2`, {
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      });

      if (!flowResponse.ok) {
        // If direct AAL2 fails, try with refresh parameter
        console.log('🔐 Direct AAL2 failed, trying with refresh parameter...');
        const refreshResponse = await fetch(`/.ory/self-service/login/browser?refresh=true&aal=aal2`, {
          headers: { 'Accept': 'application/json' },
          credentials: 'include'
        });

        if (!refreshResponse.ok) {
          throw new Error('Failed to initialize AAL2 flow');
        }

        const flowData = await refreshResponse.json();
        console.log('🔐 AAL2 refresh flow initialized:', flowData.id);
        setFlowId(flowData.id);
        return handleFlowData(flowData);
      }

      const flowData = await flowResponse.json();
      console.log('🔐 AAL2 flow initialized (like TOTP):', flowData.id);
      console.log('🔐 Flow state:', flowData.state);
      setFlowId(flowData.id);

      // Continue with flow data processing
      await handleFlowData(flowData);

    } catch (error) {
      console.error('❌ AAL2 passkey authentication failed:', error);
      setError(`Passkey authentication failed: ${error.message}`);
      setLoading(false);
      setVerificationStarted(false);
      hideLoading();
    }
  };

  const handleFlowData = async (flowData) => {
    try {
      console.log('🔐 Processing AAL2 flow data...');
      console.log('🔐 Flow nodes:', flowData.ui?.nodes?.length);

      // Check for WebAuthn triggers in the AAL2 flow
      const webauthnTrigger = flowData.ui?.nodes?.find(n =>
        n.attributes?.onclick?.includes('window.oryWebAuthnLogin')
      );

      const webauthnLoginTrigger = flowData.ui?.nodes?.find(n =>
        n.attributes?.name === 'webauthn_login_trigger'
      );

      if (webauthnTrigger || webauthnLoginTrigger) {
        console.log('✅ Found WebAuthn trigger in AAL2 flow!');

        const trigger = webauthnTrigger || webauthnLoginTrigger;
        const scriptContent = trigger?.attributes?.onclick;

        if (scriptContent && typeof scriptContent === 'string' && scriptContent.trim()) {
          console.log('🔐 Executing WebAuthn ceremony script...');

          // Create a promise to track the ceremony completion
          const ceremonyPromise = new Promise((resolve, reject) => {
            let ceremonyStarted = false;

            // Listen for WebAuthn credential request to know ceremony started
            const originalGet = navigator.credentials.get;
            navigator.credentials.get = async function(options) {
              console.log('🔐 WebAuthn ceremony started - Touch ID/biometric requested');
              ceremonyStarted = true;

              try {
                // Call the original get and wait for user to complete biometric
                const credential = await originalGet.call(this, options);
                console.log('✅ Biometric authentication completed!');
                ceremonyCompleteRef.current = true;

                // Restore original function
                navigator.credentials.get = originalGet;

                // Give Kratos time to process the credential
                setTimeout(() => resolve(credential), 1500);

                return credential;
              } catch (error) {
                console.error('❌ Biometric authentication failed:', error);
                navigator.credentials.get = originalGet;
                reject(error);
              }
            };

            // Execute the WebAuthn script
            try {
              // Validate script content before evaluation
              if (!scriptContent || typeof scriptContent !== 'string') {
                throw new Error('Invalid script content for WebAuthn');
              }
              eval(scriptContent);

              // Only set a timeout if ceremony actually starts
              setTimeout(() => {
                if (!ceremonyStarted) {
                  console.log('⚠️ WebAuthn ceremony never started');
                  navigator.credentials.get = originalGet;
                  reject(new Error('WebAuthn ceremony failed to start'));
                }
              }, 5000);

              // Extended timeout for actual biometric completion
              setTimeout(() => {
                if (ceremonyStarted && !ceremonyCompleteRef.current) {
                  console.log('⏰ Biometric authentication timed out');
                  navigator.credentials.get = originalGet;
                  reject(new Error('Biometric authentication timed out'));
                }
              }, 60000); // 60 seconds for user to complete Touch ID

            } catch (e) {
              console.error('❌ Script execution failed:', e);
              navigator.credentials.get = originalGet;
              reject(e);
            }
          });

          // Wait for ceremony completion
          try {
            await ceremonyPromise;
            console.log('✅ WebAuthn biometric ceremony completed successfully!');

            // Biometric authentication completed successfully
            console.log('✅ Biometric authentication completed - notifying backend');
            await completeAAL2Verification();
          } catch (error) {
            console.error('❌ Biometric ceremony failed:', error);
            throw error;
          }
        } else {
          throw new Error('No WebAuthn script found');
        }
      } else {
        // Check if this is a fresh auth request (Kratos demands new login)
        if (flowData.ui?.messages?.some(m => m.id === 4000003)) {
          console.log('⚠️ Kratos demands fresh authentication - this is the AAL2 loop issue');
          throw new Error('Kratos requires fresh authentication. This is a known issue with WebAuthn AAL2. Please use TOTP instead.');
        }

        // No WebAuthn trigger available
        console.log('⚠️ No WebAuthn trigger found in AAL2 flow');
        console.log('Available nodes:', flowData.ui?.nodes?.map(n => ({
          name: n.attributes?.name,
          type: n.attributes?.type,
          group: n.group
        })));

        // Check if TOTP is available as alternative
        const hasTOTPNode = flowData.ui?.nodes?.some(n =>
          n.attributes?.name === 'totp_code' || n.group === 'totp'
        );

        if (hasTOTPNode) {
          console.log('🔐 TOTP is available as alternative');
          throw new Error('Passkey AAL2 not available. Redirecting to TOTP verification...');
        }

        throw new Error('No AAL2 methods available. This might be the Kratos WebAuthn AAL2 bug.');
      }
    } catch (error) {
      console.error('❌ Passkey authentication failed:', error);
      setError(error.message);
      setLoading(false);
      setVerificationStarted(false);
      hideLoading();

      // If passkey fails due to Kratos bug, offer TOTP as alternative
      if (error.message.includes('TOTP')) {
        setTimeout(() => {
          const returnTo = searchParams.get('return_to') || '/dashboard';
          navigate(`/verify-totp?return_to=${encodeURIComponent(returnTo)}`);
        }, 2000);
      }
    }
  };

  // Placeholder for the rest of the removed code
  const handleFlowDataOriginal = async (flowData) => {
    // Original complex flow code (kept for reference but disabled)
    console.log('🔐 Original flow disabled');
  };

  // Removed complex WebAuthn flow code - keeping component simple for now

  const handleBack = () => {
    navigate(-1);
  };

  const handleSkip = () => {
    // SECURITY: Do not allow skip for AAL2
    setError('AAL2 verification is required for this resource. Please complete passkey verification.');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-16 h-16 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">
            Passkey Verification Required
          </h1>
          <p className="text-gray-300 text-sm">
            AAL2 verification is required to access this resource
          </p>
        </div>

        {/* User Info */}
        {userEmail && (
          <div className="text-center mb-6 text-sm text-gray-400">
            Authenticating: <span className="text-blue-300">{userEmail}</span>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Passkey Authentication */}
        <div className="space-y-4 mb-6">
          <button
            onClick={handlePasskeyAuth}
            disabled={loading}
            className="w-full p-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors focus:ring-2 focus:ring-blue-500/25 focus:outline-none"
          >
            {loading ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div className="text-left">
                  <div className="font-semibold">Waiting for verification...</div>
                  <div className="text-sm opacity-75">Complete biometric authentication</div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center">
                <div className="text-2xl mr-3">
                  {biometricAvailable ? '👆' : '🔑'}
                </div>
                <div className="text-left">
                  <div className="font-semibold">
                    {biometricAvailable ? 'Use Touch ID / Face ID' : 'Use Security Key'}
                  </div>
                  <div className="text-sm opacity-75">
                    {biometricAvailable ? 'Biometric verification required' : 'Insert your security key'}
                  </div>
                </div>
              </div>
            )}
          </button>
        </div>

        {/* Navigation - Only back button, no skip */}
        <div className="flex justify-center">
          <button
            onClick={handleBack}
            className="px-6 py-3 border border-gray-600 hover:border-gray-500 text-gray-300 hover:text-white rounded-lg transition-colors"
          >
            ← Back
          </button>
        </div>

        {/* Security Notice */}
        <div className="mt-6 text-center text-xs text-gray-500">
          🔒 This verification cannot be skipped for security reasons
        </div>

        {/* Development Mode Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs text-center">
              🔧 Dev: AAL2 Passkey Verification (Secure)
              <br />
              ✅ No skip allowed, proper ceremony validation
              <br />
              ✅ Backend verification required
              <br />
              Flow ID: {flowId || 'Not initialized'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AAL2PasskeyVerify;