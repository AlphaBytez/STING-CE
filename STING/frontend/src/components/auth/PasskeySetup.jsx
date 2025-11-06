import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProvider';
import { api } from '../../utils/apiClient';

/**
 * PasskeySetup - Dedicated component for setting up passkeys after registration
 */
const PasskeySetup = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [challengeId, setChallengeId] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [sessionWaiting, setSessionWaiting] = useState(false);
  const navigate = useNavigate();
  const { identity } = useKratos();
  
  // Use ref to persist challenge ID across renders
  const challengeIdRef = useRef(null);
  const autoTriggeredRef = useRef(false);

  // Get user email from Kratos identity or localStorage fallback
  const userEmail = identity?.traits?.email || localStorage.getItem('registration_email') || 'user@example.com';

  // Check WebAuthn support and user authentication
  useEffect(() => {
    const checkWebAuthnSupport = async () => {
      try {
        if (window.PublicKeyCredential) {
          const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          setWebAuthnSupported(true); // Support both platform and external authenticators
          console.log('🔐 PasskeySetup: WebAuthn support detected:', available);
        } else {
          console.log('🔐 PasskeySetup: WebAuthn not supported');
          setWebAuthnSupported(false);
        }
      } catch (err) {
        console.error('🔐 PasskeySetup: Error checking WebAuthn support:', err);
        setWebAuthnSupported(false);
      }
      setInitializing(false);
    };

    // Add a delay for new registrations to ensure session is established
    const isNewRegistration = new URLSearchParams(window.location.search).get('new_registration') === 'true';
    if (isNewRegistration) {
      console.log('🔐 PasskeySetup: New registration detected, waiting for session establishment...');
      // Clear the justRegistered flag now that we're on the passkey setup page
      localStorage.removeItem('justRegistered');
      // Wait 2 seconds for session to be fully established
      setTimeout(() => {
        checkWebAuthnSupport();
      }, 2000);
      return;
    }

    // Check if user is authenticated
    if (!identity && !localStorage.getItem('registration_email')) {
      console.log('🔐 PasskeySetup: No authenticated user or registration email');
      
      // If we just registered, wait a bit for the session to be established
      if (localStorage.getItem('justRegistered') === 'true') {
        console.log('🔐 PasskeySetup: Just registered, waiting for session...');
        // Remove the flag
        localStorage.removeItem('justRegistered');
        // Wait and retry
        setTimeout(() => {
          window.location.reload();
        }, 2000);
        return;
      }
      
      console.log('🔐 PasskeySetup: Redirecting to login');
      navigate('/auth/login');
      return;
    }

    checkWebAuthnSupport();
  }, [identity, navigate]);

  // Auto-trigger disabled - manual setup only
  useEffect(() => {
    // Commenting out auto-trigger to avoid 401 errors
    // Users will need to manually click the "Create Passkey" button
    console.log('🔐 PasskeySetup: Ready for manual passkey creation');
  }, [initializing, webAuthnSupported, identity]);

  // Show loading state during initialization
  if (initializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p className="text-white">Preparing passkey setup...</p>
        </div>
      </div>
    );
  }

  // Handle passkey creation
  const handleCreatePasskey = async () => {
    // Check if we have authentication before proceeding
    if (!identity && !localStorage.getItem('registration_email')) {
      console.log('🔐 No authenticated session found, cannot create passkey');
      setError('Please log in to set up your passkey');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      console.log('🔐 Starting passkey creation for:', userEmail);
      
      // If this is a new registration, add a delay to ensure session is established
      // This is necessary because Kratos session propagation can take a moment after registration
      const isNewRegistration = new URLSearchParams(window.location.search).get('new_registration') === 'true';
      if (isNewRegistration) {
        console.log('🔐 New registration detected, waiting for session to establish...');
        setSessionWaiting(true);
        await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds for session propagation
        setSessionWaiting(false);
      }

      // First, ensure we have a valid session by checking with Kratos
      try {
        console.log('🔐 Current cookies:', document.cookie);
        const sessionCheck = await api.kratos.whoami();
        console.log('🔐 Session check result:', sessionCheck.data);
        
        // If we just registered, the session might be from Kratos but not yet in our backend
        // Force a backend session initialization
        if (isNewRegistration) {
          console.log('🔐 New registration detected, checking backend session...');
          try {
            // Try the /me endpoint to check if backend session exists
            const meResponse = await api.auth.me();
            console.log('🔐 Backend session active:', meResponse.data);
          } catch (meErr) {
            console.warn('🔐 Backend session check failed:', meErr);
            // This is expected if the user just registered
            // The session will be created when they log in
          }
        }
        
        // Also check backend session
        try {
          const backendSession = await api.auth.testSession();
          console.log('🔐 Backend test session:', backendSession.data);
        } catch (backendErr) {
          console.error('🔐 Backend session check failed:', backendErr);
        }
      } catch (sessionError) {
        console.error('🔐 Session check failed:', sessionError);
        console.error('🔐 Session error response:', sessionError.response?.data);
        // If session check fails, the user might not be properly authenticated
        setError('Session not found. Please log in again to set up your passkey.');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
        return;
      }

      // Start WebAuthn registration with our API (through frontend proxy)
      // The API client automatically includes credentials
      const response = await api.webauthn.registrationBegin({
        username: userEmail,
        user_id: userEmail
      });

      console.log('🔐 Full response from server:', JSON.stringify(response, null, 2));
      console.log('🔐 Response data type:', typeof response.data);
      console.log('🔐 Response data keys:', Object.keys(response.data || {}));
      
      // Handle potentially nested response structure
      let options = response.data;
      if (options && typeof options === 'object' && !options.challenge) {
        // Check if the data is nested in a property
        if (options.data && options.data.challenge) {
          console.log('🔐 Found nested options in data property');
          options = options.data;
        } else if (options.options && options.options.challenge) {
          console.log('🔐 Found nested options in options property');
          options = options.options;
        } else {
          console.log('🔐 Unknown response structure, attempting to find challenge property');
          console.log('🔐 Available properties:', Object.keys(options));
          // Try to find challenge in any nested object
          for (let key in options) {
            if (options[key] && typeof options[key] === 'object' && options[key].challenge) {
              console.log(`🔐 Found challenge in ${key} property`);
              options = options[key];
              break;
            }
          }
        }
      }
      
      console.log('🔐 Final options object:', JSON.stringify(options, null, 2));
      
      if (!options || !options.challenge) {
        throw new Error('Invalid WebAuthn options received from server - missing challenge');
      }

      // Store challenge_id for completion request
      if (options.challenge_id) {
        setChallengeId(options.challenge_id);
        challengeIdRef.current = options.challenge_id; // Store in ref as backup
        console.log('🔐 Stored challenge ID:', options.challenge_id);
      } else {
        throw new Error('Server did not provide a challenge_id');
      }

      // Convert base64url to ArrayBuffer for WebAuthn API
      console.log('🔐 Raw options from server:', JSON.stringify(options, null, 2));
      
      // Helper function to convert base64url to ArrayBuffer
      const base64urlToArrayBuffer = (base64url) => {
        try {
          console.log('🔐 Converting base64url to ArrayBuffer:', base64url);
          
          // Convert base64url to base64 by replacing URL-safe characters
          let base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
          
          // Add padding if needed
          while (base64.length % 4) {
            base64 += '=';
          }
          
          console.log('🔐 Converted to base64:', base64);
          
          // Decode base64 to binary string
          const binaryString = atob(base64);
          console.log('🔐 Binary string length:', binaryString.length);
          
          // Convert binary string to Uint8Array
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          
          console.log('🔐 ArrayBuffer created, length:', bytes.length);
          return bytes;
        } catch (error) {
          console.error('🔐 Error converting base64url to ArrayBuffer:', error);
          console.error('🔐 Input string:', base64url);
          throw new Error(`Failed to decode base64url string: ${error.message}`);
        }
      };

      const publicKeyCredentialCreationOptions = {
        challenge: base64urlToArrayBuffer(options.challenge),
        rp: options.rp,
        user: {
          id: base64urlToArrayBuffer(options.user.id),
          name: options.user.name,
          displayName: options.user.displayName
        },
        pubKeyCredParams: options.pubKeyCredParams,
        authenticatorSelection: options.authenticatorSelection,
        timeout: options.timeout,
        attestation: options.attestation
      };

      console.log('🔐 Creating credential with options:', publicKeyCredentialCreationOptions);

      // Create the credential
      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions
      });

      // Validate credential before accessing properties
      if (!credential || !credential.id || !credential.rawId || !credential.response) {
        console.error('❌ Invalid credential received from authenticator:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      console.log('🔐 Credential created successfully:', credential.id);
      console.log('🔐 Full credential object:', credential);
      console.log('🔐 Credential properties:', Object.keys(credential));
      console.log('🔐 Credential rawId type:', typeof credential.rawId);
      console.log('🔐 Credential rawId value:', credential.rawId);
      console.log('🔐 Credential response type:', typeof credential.response);
      console.log('🔐 Credential response properties:', Object.keys(credential.response));

      // Prepare credential data for backend
      const credentialData = {
        id: credential.id,
          rawId: credential.rawId ? Array.from(new Uint8Array(credential.rawId)) : null,
          response: {
            attestationObject: credential.response.attestationObject ? 
              Array.from(new Uint8Array(credential.response.attestationObject)) : null,
            clientDataJSON: credential.response.clientDataJSON ? 
              Array.from(new Uint8Array(credential.response.clientDataJSON)) : null
          },
          type: credential.type
        };

        console.log('🔐 Prepared credential data for backend:', JSON.stringify(credentialData, null, 2));

        // Validate required fields
        if (!credentialData.id) {
          throw new Error('Credential missing required id');
        }
        if (!credentialData.rawId) {
          throw new Error('Credential missing required rawId');
        }
        if (!credentialData.response.attestationObject) {
          throw new Error('Credential missing required attestationObject');
        }
        if (!credentialData.response.clientDataJSON) {
          throw new Error('Credential missing required clientDataJSON');
        }

        // Use the challenge ID from ref if state is null (handles re-renders)
        const currentChallengeId = challengeId || challengeIdRef.current;
        
        if (!currentChallengeId) {
          throw new Error('Challenge ID was not preserved. Please try again.');
        }

        // Complete registration with our API (through frontend proxy)
        const completionResponse = await api.webauthn.registrationComplete({
          credential: credentialData,
          challenge_id: currentChallengeId,
          username: userEmail
        });

        if (completionResponse.data.verified) {
          console.log('🔐 Passkey registration completed successfully');
          setSuccess(true);
          
          // Clean up localStorage
          localStorage.removeItem('registration_email');
          
          // Set a flag to indicate successful passkey setup
          localStorage.setItem('passkey_setup_complete', 'true');
          
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            navigate('/dashboard');
          }, 2000);
        } else {
          setError('Failed to register passkey: ' + (completionResponse.data.error || 'Unknown error'));
        }
        
    } catch (error) {
      console.error('🔐 PasskeySetup error:', error);
      
      // Handle specific error cases
      let errorMessage = error.response?.data?.error || error.message;
      
      if (errorMessage.includes('registration session') || errorMessage.includes('No registration session')) {
        errorMessage = 'Registration session expired. Please try registering again or skip passkey setup for now.';
      }
      
      setError('Failed to create passkey: ' + errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Skip passkey setup
  const handleSkip = () => {
    console.log('🔐 User skipped passkey setup');
    localStorage.removeItem('registration_email');
    navigate('/dashboard');
  };

  // If WebAuthn is not supported, show alternative
  if (!webAuthnSupported) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
          <h2 className="text-2xl font-bold mb-6">Passkey Setup</h2>
          
          <div className="mb-6 p-4 bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded">
            <p className="text-yellow-300">
              Your browser doesn't support passkeys, but you can still use STING with your password.
            </p>
          </div>
          
          <button
            onClick={handleSkip}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
        <h2 className="text-2xl font-bold mb-6">Set Up a Passkey</h2>
        
        {success ? (
          <div className="text-center">
            <div className="mb-6">
              <svg className="w-16 h-16 text-green-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <h3 className="text-lg font-semibold text-green-400 mb-2">Passkey Created Successfully!</h3>
              <p className="text-gray-300">
                You can now sign in to STING using your biometrics or security key.
              </p>
            </div>
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-green-400 mx-auto mb-4"></div>
            <p className="text-sm text-gray-400">Redirecting to dashboard...</p>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <p className="text-gray-300 mb-4">
                Enhance your security and login experience by setting up a passkey. 
                This will allow you to sign in without having to remember a password.
              </p>
              
              <div className="p-4 bg-green-900 bg-opacity-20 border border-green-800 rounded mb-4">
                <div className="flex items-center justify-center mb-2">
                  <svg className="w-8 h-8 text-green-500 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                    <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
                  </svg>
                  <span className="text-green-400 font-medium">Passkey Ready</span>
                </div>
                <p className="text-sm text-green-300">
                  Your device supports secure passkey authentication
                </p>
              </div>
            </div>

            {sessionWaiting && (
              <div className="mb-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-800 rounded">
                <p className="text-blue-300 text-sm">
                  🔐 Setting up your secure session after registration...
                </p>
                <p className="text-blue-200 text-xs mt-1">
                  This will just take a moment.
                </p>
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded">
                <p className="text-red-300 text-sm">{error}</p>
                {error.includes('registration session') && (
                  <div className="mt-2 pt-2 border-t border-red-800">
                    <p className="text-red-200 text-xs">
                      You can still use STING with your password. You can set up a passkey later in your account settings.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-4">
              <button
                onClick={handleCreatePasskey}
                disabled={isLoading || sessionWaiting}
                className="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 disabled:opacity-50 flex items-center justify-center font-semibold"
              >
                {sessionWaiting ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-black mr-2"></div>
                    Setting up your session...
                  </>
                ) : isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-black mr-2"></div>
                    Creating Passkey...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                      <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
                    </svg>
                    Create Passkey
                  </>
                )}
              </button>

              <button
                onClick={handleSkip}
                disabled={isLoading || sessionWaiting}
                className="w-full py-2 px-4 text-gray-400 hover:text-white border border-gray-600 hover:border-gray-500 rounded disabled:opacity-50"
              >
                Skip for now
              </button>
            </div>

            <div className="mt-6 text-xs text-gray-500">
              <p>Your device will prompt you to use your biometrics (fingerprint, face) or PIN.</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PasskeySetup;