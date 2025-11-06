import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { buildReturnUrl } from '../../utils/kratosConfig';

/**
 * EnhancedKratosRegistration - A component that handles user registration
 * and encourages the creation of passkeys during the registration process.
 */
const EnhancedKratosRegistration = () => {
  console.log('🔐 EnhancedKratosRegistration component mounted');
  
  // State
  const [flowData, setFlowData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [flowStep, setFlowStep] = useState('initial'); // initial, form, passkey
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  // Get Kratos URL from environment
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Get flow ID from URL if present
  const flowId = searchParams.get('flow');
  
  // Check if WebAuthn/passkeys are supported
  useEffect(() => {
    const checkWebAuthnSupport = async () => {
      console.log('🔐 Checking WebAuthn support for registration...');
      try {
        // Check if browser supports WebAuthn
        if (window.PublicKeyCredential) {
          console.log('🔐 PublicKeyCredential exists in window object');
          
          try {
            const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            console.log('🔐 WebAuthn platform authenticator available:', available);
            setWebAuthnSupported(available);
            
            // Additional checks for better compatibility
            console.log('🔐 Registration: Platform authenticator available:', available);
            // Enable for both platform and external authenticators
            setWebAuthnSupported(true); // Always enable to support external authenticators too
          } catch (checkErr) {
            console.error('🔐 Error checking platform authenticator:', checkErr);
            // Fallback: if we can't check, assume it's supported and let WebAuthn API handle it
            setWebAuthnSupported(true);
          }
        } else {
          console.log('🔐 ❌ PublicKeyCredential NOT available in this browser');
          setWebAuthnSupported(false);
        }
        
        // Debug WebAuthn method in credentials API
        if (navigator.credentials) {
          console.log('🔐 navigator.credentials API is available');
          console.log('🔐 navigator.credentials create method exists:', !!navigator.credentials.create);
          console.log('🔐 navigator.credentials get method exists:', !!navigator.credentials.get);
        } else {
          console.log('🔐 navigator.credentials API is NOT available');
        }
      } catch (err) {
        console.error('🔐 Critical error checking WebAuthn support:', err);
        setWebAuthnSupported(false);
      }
    };
    
    // Execute the check
    checkWebAuthnSupport();
  }, []);
  
  // Debug log WebAuthn state changes
  useEffect(() => {
    console.log('🔐 WebAuthn support state updated:', webAuthnSupported);
  }, [webAuthnSupported]);
  
  // Fetch flow data on mount or when flowId changes
  useEffect(() => {
    const fetchFlowData = async () => {
      if (!flowId) {
        // If no flow ID, we're not in a registration flow yet
        return;
      }
      
      try {
        setIsLoading(true);
        console.log(`Fetching registration flow data from: ${kratosUrl}/self-service/registration/flows?id=${flowId}`);
        
        const response = await axios.get(
          `${kratosUrl}/self-service/registration/flows?id=${flowId}`,
          {
            withCredentials: true,
          }
        );
        
        console.log(`Flow fetch response status: ${response.status}`);
        setFlowData(response.data);
        setFlowStep('form');
      } catch (err) {
        console.error('Error fetching registration flow data:', err);
        setError('Failed to connect to authentication service. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchFlowData();
  }, [flowId, kratosUrl]);
  
  // Start registration flow
  const startRegistration = () => {
    // Build dynamic return URL to handle Codespaces/VMs/port forwarding
    const returnUrl = buildReturnUrl('/dashboard');
    window.location.href = `${kratosUrl}/self-service/registration/browser?return_to=${encodeURIComponent(returnUrl)}`;
  };
  
  // Extract WebAuthn-related nodes from flow
  const getWebAuthnButton = () => {
    if (!flowData || !flowData.ui || !flowData.ui.nodes) return null;
    
    // Find the WebAuthn button node
    const webAuthnNode = flowData.ui.nodes.find(node => 
      node.attributes &&
      node.attributes.name === 'webauthn_register_trigger' &&
      node.attributes.type === 'button'
    );
    
    return webAuthnNode ? webAuthnNode.attributes.onclick : null;
  };
  
  // Trigger WebAuthn registration
  const handleWebAuthnRegistration = async (e) => {
    e.preventDefault();
    
    try {
      setIsLoading(true);
      
      // Get user email from session/localStorage or prompt
      const userEmail = localStorage.getItem('registration_email') || 'user@example.com';
      
      // Start WebAuthn registration with our API
      const response = await axios.post('https://localhost:5050/api/webauthn/registration/begin', {
        username: userEmail,
        user_id: userEmail
      }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const options = response.data;
      
      // Convert base64url to ArrayBuffer for WebAuthn API
      const publicKeyCredentialCreationOptions = {
        challenge: Uint8Array.from(atob(options.challenge + '==='.slice((options.challenge.length + 3) % 4)), c => c.charCodeAt(0)),
        rp: options.rp,
        user: {
          id: Uint8Array.from(atob(options.user.id + '==='.slice((options.user.id.length + 3) % 4)), c => c.charCodeAt(0)),
          name: options.user.name,
          displayName: options.user.displayName
        },
        pubKeyCredParams: options.pubKeyCredParams,
        authenticatorSelection: options.authenticatorSelection,
        timeout: options.timeout,
        attestation: options.attestation
      };
      
      // Create the credential
      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions
      });
      
      // Validate credential before accessing properties
      if (!credential || !credential.id || !credential.rawId || !credential.response) {
        console.error('❌ Invalid credential received from authenticator:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      // Complete registration with our API
      const completionResponse = await axios.post('https://localhost:5050/api/webauthn/registration/complete', {
        credential: {
          id: credential.id,
          rawId: Array.from(new Uint8Array(credential.rawId)),
          response: {
            attestationObject: Array.from(new Uint8Array(credential.response.attestationObject)),
            clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON))
          },
          type: credential.type
        }
      }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (completionResponse.data.verified) {
        // Success! Redirect to dashboard
        navigate('/dashboard');
      } else {
        setError('Failed to register passkey: ' + (completionResponse.data.error || 'Unknown error'));
      }
      
    } catch (error) {
      console.error('WebAuthn registration error:', error);
      setError('Failed to create passkey: ' + (error.response?.data?.error || error.message));
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle form submission
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    
    console.log('🔐 REGISTRATION FORM SUBMITTED - EnhancedKratosRegistration component');
    
    try {
      // Submit the form data to Kratos
      const formData = new FormData(e.target);
      
      // Store email for passkey setup
      const email = formData.get('traits.email');
      console.log('🔐 Registration: form data email:', email);
      console.log('🔐 Registration: all form data keys:', Array.from(formData.keys()));
      
      if (email) {
        localStorage.setItem('registration_email', email);
        console.log('🔐 Registration: stored email in localStorage:', email);
        console.log('🔐 Registration: localStorage verification:', localStorage.getItem('registration_email'));
      } else {
        console.log('🔐 Registration: no email found in form data');
        console.log('🔐 Registration: searching for email in other field names...');
        for (let [key, value] of formData.entries()) {
          console.log(`🔐 Registration form field: ${key} = ${value}`);
        }
      }
      
      console.log('🔐 Submitting registration form to Kratos...');
      console.log('🔐 Form action:', flowData.ui.action);
      console.log('🔐 WebAuthn supported:', webAuthnSupported);
      
      // Convert FormData to URLSearchParams for proper encoding
      const params = new URLSearchParams();
      for (let [key, value] of formData.entries()) {
        params.append(key, value);
      }
      console.log('🔐 Registration params being sent:', params.toString());
      
      const response = await axios.post(flowData.ui.action, params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        withCredentials: true,
        // Prevent automatic redirects so we can handle them
        maxRedirects: 0,
        validateStatus: function (status) {
          // Accept both success and redirect status codes
          return status >= 200 && status < 400;
        }
      });
      
      console.log('🔐 Registration response status:', response.status);
      console.log('🔐 Registration response data:', response.data);
      
      // Check if registration was successful (200) or redirected (3xx)
      if (response.status === 200 || (response.status >= 300 && response.status < 400)) {
        console.log('🔐 Registration successful, checking redirect...');
        
        // Mark that registration was just completed
        localStorage.setItem('justRegistered', 'true');
        
        // For Kratos registration, we need to follow the redirect to complete the flow
        // The session hook will create the session after successful registration
        if (response.headers?.location || response.data?.redirect_browser_to) {
          const redirectUrl = response.headers?.location || response.data?.redirect_browser_to;
          console.log('🔐 Following Kratos redirect to:', redirectUrl);
          
          // Parse the URL to get the path
          try {
            const url = new URL(redirectUrl);
            const path = url.pathname + url.search;
            console.log('🔐 Navigating to path:', path);
            navigate(path);
          } catch (e) {
            console.log('🔐 Could not parse URL, using full redirect');
            window.location.href = redirectUrl;
          }
        } else {
          // If no redirect from Kratos, wait a moment for session to be established
          console.log('🔐 Waiting for session to be established...');
          setTimeout(() => {
            // Redirect to post-registration which will handle email verification
            console.log('🔐 Redirecting to post-registration...');
            navigate('/post-registration');
          }, 1000); // Wait 1 second for session
        }
      }
    } catch (error) {
      console.error('🔐 Registration error:', error);
      
      // Check if this is a redirect that axios treated as an error
      if (error.response && error.response.status >= 300 && error.response.status < 400) {
        console.log('🔐 Registration successful (redirect response)');
        
        // Mark that registration was just completed
        localStorage.setItem('justRegistered', 'true');
        
        // For Kratos registration, we need to follow the redirect
        const redirectUrl = error.response.headers?.location || error.response.data?.redirect_browser_to;
        if (redirectUrl) {
          console.log('🔐 Following Kratos redirect to:', redirectUrl);
          
          // Parse the URL to get the path
          try {
            const url = new URL(redirectUrl);
            const path = url.pathname + url.search;
            console.log('🔐 Navigating to path:', path);
            navigate(path);
          } catch (e) {
            console.log('🔐 Could not parse URL, using full redirect');
            window.location.href = redirectUrl;
          }
        } else {
          // Wait for session to be established
          setTimeout(() => {
            // Redirect to post-registration which will handle email verification
            console.log('🔐 Redirecting to post-registration...');
            navigate('/post-registration');
          }, 1000);
        }
      } else {
        // Actual error
        console.error('🔐 Actual registration error:', error.response?.data);
        setError(`Registration failed: ${error.response?.data?.ui?.messages?.[0]?.text || error.message}`);
      }
    }
  };
  
  // Render the registration form based on flow data
  const renderRegistrationForm = () => {
    if (!flowData || !flowData.ui) {
      return (
        <div className="text-center py-6">
          <p>No registration data available. Please try again.</p>
          <button
            onClick={startRegistration}
            className="mt-4 py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Restart Registration
          </button>
        </div>
      );
    }
    
    // Extract form action and method
    const { action, method } = flowData.ui;
    
    return (
      <form 
        onSubmit={handleFormSubmit}
      >
        {/* Hidden CSRF field */}
        {flowData.ui.nodes.map((node, index) => {
          if (node.attributes.name === 'csrf_token') {
            return (
              <input
                key={index}
                type="hidden"
                name={node.attributes.name}
                value={node.attributes.value}
              />
            );
          }
          
          // Skip non-input nodes, WebAuthn triggers, and submit buttons (we'll add our own)
          if (node.type !== 'input' || 
              node.attributes.type === 'submit' || 
              node.attributes.name?.includes('webauthn')) {
            return null;
          }
          
          // Extract label and attributes
          const label = node.meta?.label?.text || node.attributes.name;
          const name = node.attributes.name;
          
          // Properly parse traits fields for better form structure
          if (name.startsWith('traits.')) {
            // Extract trait field name
            const traitField = name.split('.').slice(1).join('.');
            
            // Special handling for nested objects like traits.name.first
            if (traitField.includes('.')) {
              const [parentField, childField] = traitField.split('.');
              
              // Format the label for better display
              const formattedLabel = childField.charAt(0).toUpperCase() + childField.slice(1);
              
              return (
                <div key={index} className="mb-4">
                  <label className="block text-gray-300 mb-2">{formattedLabel}</label>
                  <input
                    name={name}
                    type={node.attributes.type}
                    className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                    required={node.attributes.required}
                    defaultValue={node.attributes.value || ''}
                    autoComplete={parentField === 'name' && childField === 'first' ? 'given-name' : 
                                 parentField === 'name' && childField === 'last' ? 'family-name' : ''}
                  />
                  {/* Show any messages for this field */}
                  {node.messages?.map((msg, i) => (
                    <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {msg.text}
                    </p>
                  ))}
                </div>
              );
            }
            
            // Handle simple traits like traits.email
            return (
              <div key={index} className="mb-4">
                <label className="block text-gray-300 mb-2">{label}</label>
                <input
                  name={name}
                  type={node.attributes.type}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                  required={node.attributes.required}
                  defaultValue={node.attributes.value || ''}
                  autoComplete={traitField === 'email' ? 'email' : ''}
                />
                {/* Show any messages for this field */}
                {node.messages?.map((msg, i) => (
                  <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {msg.text}
                  </p>
                ))}
              </div>
            );
          }
          
          // Handle password field - ensure it's always shown even if not in nodes
          if (name === 'password') {
            return (
              <div key={index} className="mb-4">
                <label className="block text-gray-300 mb-2">Password</label>
                <input
                  name={name}
                  type="password"
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                  required={node.attributes.required !== false}
                  autoComplete="new-password"
                  placeholder="Choose a strong password"
                />
                {/* Show any messages for this field */}
                {node.messages?.map((msg, i) => (
                  <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {msg.text}
                  </p>
                ))}
              </div>
            );
          }
          
          // Default rendering for other fields
          return (
            <div key={index} className="mb-4">
              <label className="block text-gray-300 mb-2">{label}</label>
              <input
                name={name}
                type={node.attributes.type}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                required={node.attributes.required}
                defaultValue={node.attributes.value || ''}
              />
              {/* Show any messages for this field */}
              {node.messages?.map((msg, i) => (
                <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {msg.text}
                </p>
              ))}
            </div>
          );
        })}
        
        {/* Ensure password field exists */}
        {!flowData.ui.nodes.some(node => node.attributes.name === 'password') && (
          <div className="mb-4">
            <label className="block text-gray-300 mb-2">Password</label>
            <input
              name="password"
              type="password"
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
              required
              autoComplete="new-password"
              placeholder="Choose a strong password"
            />
          </div>
        )}
        
        {/* Hidden method field for Kratos */}
        <input type="hidden" name="method" value="password" />
        
        {/* Submit button */}
        <button 
          type="submit" 
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 mt-4"
        >
          Create Account
        </button>
        
        {/* Show form-level messages */}
        {flowData.ui.messages?.map((msg, index) => (
          <div 
            key={index} 
            className={`mt-4 p-3 rounded ${
              msg.type === 'error' ? 'bg-red-900 bg-opacity-30 border border-red-800 text-red-300' : 'bg-green-900 bg-opacity-30 border border-green-800 text-green-300'
            }`}
          >
            {msg.text}
          </div>
        ))}
      </form>
    );
  };
  
  // Render passkey setup screen
  const renderPasskeySetup = () => {
    return (
      <div className="text-center py-6">
        <h3 className="text-lg font-semibold mb-4">Set up a Passkey</h3>
        <p className="mb-6">
          Improve your security and login experience by setting up a passkey.
          This will allow you to sign in without having to remember a password.
        </p>
        
        <div className="flex flex-col items-center justify-center mb-6">
          <svg className="w-16 h-16 text-green-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"></path>
          </svg>
          
          <button
            onClick={handleWebAuthnRegistration}
            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Create Passkey
          </button>
        </div>
        
        <div className="text-sm text-gray-400">
          <p>Your device will prompt you to use your biometrics (fingerprint, face) or PIN.</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 text-blue-400 hover:underline"
          >
            Skip for now
          </button>
        </div>
      </div>
    );
  };
  
  // If no flow ID, render the initial registration screen
  if (!flowId && flowStep === 'initial') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
          <h2 className="text-2xl font-bold text-center mb-6">Create your account</h2>
          
          {webAuthnSupported && (
            <>
              <p className="text-center mb-6 text-gray-300">
                STING supports passkeys, a more secure and easier way to sign in
                without remembering passwords.
              </p>
              
              <div className="flex flex-col items-center justify-center mb-8">
                <svg className="w-20 h-20 text-green-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                </svg>
              </div>
            </>
          )}
          
          <button
            onClick={startRegistration}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Get Started
          </button>
          
          <div className="mt-6 text-center">
            <p className="text-gray-400">
              Already have an account?{" "}
              <a href="/login" className="text-blue-400 hover:underline">
                Sign in
              </a>
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // Handle the "passkey" flow step
  if (flowStep === 'passkey' && webAuthnSupported) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
          <h2 className="text-2xl font-bold text-center mb-6">Set Up Passkey</h2>
          {renderPasskeySetup()}
        </div>
      </div>
    );
  }
  
  // Render full registration form with flow data
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#161922]">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
        <h2 className="text-2xl font-bold text-center mb-6">Create your account</h2>
        
        {/* WebAuthn Support Indicator */}
        {webAuthnSupported && (
          <div className="mb-4 p-3 bg-yellow-900 bg-opacity-20 border border-yellow-600 rounded">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-yellow-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span className="text-yellow-400 text-sm">
                🔐 Passkey support detected! You'll be able to set up a passkey after registration.
              </span>
            </div>
          </div>
        )}
        
        {isLoading ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
            <p>Loading registration form...</p>
          </div>
        ) : error ? (
          <div className="p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded mb-6">
            <p className="text-red-300">{error}</p>
            <div className="mt-4">
              <button
                onClick={startRegistration}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          renderRegistrationForm()
        )}
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Already have an account?{' '}
            <a href="/login" className="text-blue-400 hover:underline">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default EnhancedKratosRegistration;