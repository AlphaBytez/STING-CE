import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

// Dynamically import WebAuthn to prevent server-side rendering issues
let startRegistration;
if (typeof window !== 'undefined') {
  import('@simplewebauthn/browser').then(module => {
    startRegistration = module.startRegistration;
  });
}
// Simple registration page using Ory Kratos
const RegisterPage = () => {
  // In development, we use the proxy in setupProxy.js
  // In production, we use the Kratos URL from environment
  const isDev = process.env.NODE_ENV === 'development';
  const KRATOS_URL = process.env.REACT_APP_KRATOS_PUBLIC_URL || window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Always use empty baseUrl in development to leverage the proxy
  // The proxy in setupProxy.js will handle routing to the correct Kratos instance
  const baseUrl = '';
  const [flow, setFlow] = useState(null);
  const [loadingFlow, setLoadingFlow] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [error, setError] = useState('');
  const [debugInfo, setDebugInfo] = useState(null);

  // Initialize registration flow
  useEffect(() => {
    console.log('Initializing registration flow');
    
    // Get the flow ID from URL if it exists
    const urlParams = new URLSearchParams(window.location.search);
    const flowId = urlParams.get('flow');
    
    if (flowId) {
      console.log('Flow ID found in URL:', flowId);
      // Fetch flow data using the ID from the URL
      fetch(`${baseUrl}/self-service/registration/flows?id=${flowId}`, {
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      })
        .then(res => {
          console.log('Flow fetch response:', res.status, res.headers.get('content-type'));
          if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
          }
          // Check if response is JSON
          const contentType = res.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            return res.json();
          } else {
            // If not JSON, log the text for debugging
            return res.text().then(text => {
              console.error('Non-JSON response:', text);
              throw new Error('Expected JSON response but got: ' + contentType);
            });
          }
        })
        .then(data => {
          console.log('Flow data retrieved:', data);
          setFlow(data);
          // Extract any error messages
          if (data.ui?.messages) {
            const errorMessages = data.ui.messages.map(m => m.text).join(' ');
            if (errorMessages) setError(errorMessages);
          }
        })
        .catch(err => {
          console.error('Failed to get flow data:', err);
          setError('Failed to load registration form: ' + err.message);
          // Don't call initiateNewFlow here to avoid infinite loop
        })
        .finally(() => setLoadingFlow(false));
    } else {
      // No flow ID in URL, initiate a new flow
      initiateNewFlow();
    }
  }, []);
  
  const initiateNewFlow = () => {
    console.log('Initiating new registration flow');
    
    // Use browser flow which will redirect us to a flow URL
    window.location.href = `${baseUrl}/self-service/registration/browser`;
  };

  const validatePassword = (password) => {
    // Password requirements:
    // - At least 8 characters
    // - At least one uppercase letter
    // - At least one lowercase letter
    // - At least one number
    // - At least one special character
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    if (password.length < minLength) {
      return 'Password must be at least 8 characters long';
    }
    if (!hasUpperCase) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!hasLowerCase) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!hasNumber) {
      return 'Password must contain at least one number';
    }
    if (!hasSpecialChar) {
      return 'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validate password
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    
    try {
      if (!flow || !flow.ui) {
        setError('Registration form is not properly loaded. Please refresh the page.');
        return;
      }

      // Extract all form data from the flow
      const formData = new FormData();
      
      // Extract CSRF token
      const csrfNode = flow.ui.nodes.find(n => n.attributes.name === 'csrf_token');
      if (csrfNode) {
        formData.append('csrf_token', csrfNode.attributes.value);
      }
      
      // Set method to password
      const methodNode = flow.ui.nodes.find(n => n.attributes.name === 'method' && n.attributes.value === 'password');
      if (methodNode) {
        formData.append('method', 'password');
      } else {
        console.warn('Password method not found in flow, using default');
        formData.append('method', 'password');
      }
      
      // Add email as trait
      formData.append('traits.email', email);
      
      // Add name traits
      formData.append('traits.name.first', firstName);
      formData.append('traits.name.last', lastName);
      
      // Add password
      formData.append('password', password);
      
      // Strip the Kratos URL from action to use proxy
      let actionUrl = flow.ui.action;
      if (actionUrl.includes('://')) {
        // Extract just the path portion
        const url = new URL(actionUrl);
        actionUrl = url.pathname + url.search;
      }
      
      console.log('Submitting registration to:', actionUrl);
      
      // Convert FormData to a plain object for JSON submission
      const payload = {};
      formData.forEach((value, key) => {
        // Handle nested properties like traits.email and traits.name.first
        if (key.includes('.')) {
          const parts = key.split('.');
          if (parts.length === 2) {
            // For traits.email, create traits object if it doesn't exist
            if (!payload[parts[0]]) {
              payload[parts[0]] = {};
            }
            payload[parts[0]][parts[1]] = value;
          } else if (parts.length === 3) {
            // For traits.name.first, create nested structure
            if (!payload[parts[0]]) {
              payload[parts[0]] = {};
            }
            if (!payload[parts[0]][parts[1]]) {
              payload[parts[0]][parts[1]] = {};
            }
            payload[parts[0]][parts[1]][parts[2]] = value;
          }
        } else {
          payload[key] = value;
        }
      });

      console.log('Submitting with payload:', JSON.stringify(payload));
      
      // Submit the registration
      const res = await fetch(`${baseUrl}${actionUrl}`, {
        method: flow.ui.method || 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      console.log('Registration response status:', res.status);
      console.log('Registration response redirected:', res.redirected);
      console.log('Registration response URL:', res.url);
      
      // Handle successful registration
      if (res.ok) {
        console.log('Registration successful!');
        
        // Try to parse the response to check for any redirect instructions
        try {
          const data = await res.json();
          console.log('Registration response data:', data);
          
          // Check if there's a session token or redirect instruction
          if (data.session_token || data.session) {
            console.log('Session created:', data.session_token || data.session);
          }
          
          // Check if there's a redirect_browser_to field
          if (data.redirect_browser_to) {
            window.location.href = data.redirect_browser_to;
            return;
          }
        } catch (e) {
          console.log('No JSON response body or error parsing:', e);
        }
        
        // Since Kratos creates sessions after registration (confirmed in DB),
        // redirect to session check which will handle the authentication state
        console.log('Registration successful, redirecting to session check');
        
        // Store email temporarily for passkey setup
        localStorage.setItem('registration_email', email);
        localStorage.setItem('justRegistered', 'true');
        
        // Add a small delay to ensure cookies are set
        setTimeout(() => {
          console.log('Redirecting to session check for new registration...');
          window.location.href = '/session-check?new_registration=true';
        }, 500);
        return;
      }
      
      // Handle redirects (3xx status codes)
      if (res.redirected || (res.status >= 300 && res.status < 400)) {
        console.log('Registration redirected!');
        // For redirects, we should follow the Location header
        const redirectUrl = res.headers.get('Location') || res.url;
        console.log('Redirecting to:', redirectUrl);
        window.location.href = redirectUrl;
        return;
      }
      
      // Handle 422 status - this often means the flow completed successfully
      if (res.status === 422) {
        console.log('Registration flow completed (422 status)');
        try {
          const data = await res.json();
          console.log('422 response data:', data);
          
          // Check if this is actually a success with a new flow
          if (data.redirect_browser_to) {
            window.location.href = data.redirect_browser_to;
            return;
          }
          
          // Sometimes Kratos returns 422 when registration succeeds but needs verification
          // Check if there's a success message
          if (data.ui?.messages?.some(m => m.type === 'success')) {
            console.log('Registration successful, redirecting to session check');
            window.location.href = '/session-check?new_registration=true';
            return;
          }
        } catch (e) {
          console.error('Error parsing 422 response:', e);
        }
      }
      
      // Handle 400 status - might be a flow refresh
      if (res.status === 400) {
        console.log('Registration returned 400 - checking if session was created');
        // Even if we get a 400, the registration might have succeeded
        // Let's check the session state
        setTimeout(() => {
          window.location.href = '/session-check?new_registration=true';
        }, 500);
        return;
      }
      
      // Handle other errors
      console.error('Registration failed with status:', res.status);
      
      try {
        const data = await res.json();
        console.error('Error response:', data);
        
        // Update the flow with the error information
        if (data) setFlow(data);
        
        // Extract and display error messages from the response
        let errorMessage = 'Registration failed';
        
        if (data.ui?.messages) {
          const messages = data.ui.messages
            .filter(m => m.type === 'error')
            .map(m => m.text)
            .join(' ');
          if (messages) errorMessage = messages;
        }
        
        // Check for field-specific errors
        const fieldErrors = [];
        data.ui?.nodes?.forEach(node => {
          if (node.messages && node.messages.length > 0) {
            const fieldName = node.attributes?.name || 'Unknown field';
            const errorTexts = node.messages
              .filter(m => m.type === 'error')
              .map(m => m.text)
              .join(' ');
            if (errorTexts) {
              fieldErrors.push(`${fieldName}: ${errorTexts}`);
            }
          }
        });
        
        if (fieldErrors.length > 0) {
          errorMessage += ` (${fieldErrors.join(', ')})`;
        }
        
        setError(errorMessage);
      } catch (err) {
        console.error('Failed to parse error response:', err);
        setError('Registration failed. Please check your information and try again.');
      }
    } catch (err) {
      console.error('Registration error:', err);
      setError(`Registration error: ${err.message || 'Unknown error'}`);
    }
  };

  // Show loading or error state before form
  if (loadingFlow) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
        Loading registration form...
      </div>
    );
  }
  if (!flow) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white p-4">
        <p className="text-red-500">{error || 'Unable to load registration form'}</p>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
        <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-center mb-6">Create your STING account</h2>
        {error && <div className="mb-4 p-2 bg-red-600 text-white rounded">{error}</div>}
        {flow && flow.ui?.nodes?.some(n => n.attributes?.type === 'webauthn') && (
          <button
            onClick={async () => {
              setError('');
              if (!flow || !flow.ui) {
                setError('Registration form is not properly loaded. Please refresh the page.');
                return;
              }
              
              // Check if WebAuthn module is loaded
              if (!startRegistration) {
                setError('WebAuthn not available yet. Please try again in a moment.');
                // Try to load it again
                if (typeof window !== 'undefined') {
                  try {
                    const module = await import('@simplewebauthn/browser');
                    startRegistration = module.startRegistration;
                  } catch (err) {
                    console.error('Failed to load WebAuthn module:', err);
                    setError('Failed to load WebAuthn module. Please ensure your browser supports WebAuthn.');
                    return;
                  }
                }
                if (!startRegistration) {
                  setError('WebAuthn could not be initialized. Please try again or use password registration.');
                  return;
                }
              }
              
              // Email is required for registration
              if (!email) {
                setError('Please enter your email first');
                return;
              }
              
              const webauthnNode = flow.ui.nodes.find(n => n.attributes?.type === 'webauthn');
              if (!webauthnNode) {
                setError('Passkey registration not available in this flow');
                return;
              }
              
              try {
                // Parse webauthn data safely
                let publicKey;
                try {
                  publicKey = JSON.parse(webauthnNode.attributes.value);
                } catch (e) {
                  console.error('Failed to parse webauthn data:', e);
                  setError('Invalid passkey data received from server');
                  return;
                }
                
                // Process the WebAuthn options before submitting
                // Convert Base64URL strings to ArrayBuffers for challenge and user ID
                if (publicKey.challenge) {
                  // The challenge needs to be a proper format for WebAuthn
                  // Kratos should already provide this in the correct format
                  console.log('Challenge format:', typeof publicKey.challenge);
                }
                
                // Start WebAuthn registration
                console.log('Starting WebAuthn registration with options:', publicKey);
                const credential = await startRegistration(publicKey);
                console.log('WebAuthn registration completed:', credential);
                
                // Prepare form data for WebAuthn registration
                const formData = new FormData();
                
                // Extract CSRF token and credential name
                const csrfNode = flow.ui.nodes.find(n => n.attributes.name === 'csrf_token');
                const credentialName = webauthnNode.attributes.name;
                
                if (csrfNode) {
                  formData.append('csrf_token', csrfNode.attributes.value);
                }
                
                // Set method to webauthn
                formData.append('method', 'webauthn');
                
                // Add email as trait
                formData.append('traits.email', email);
                
                // Add name traits
                formData.append('traits.name.first', firstName);
                formData.append('traits.name.last', lastName);
                
                // Convert FormData to a plain object for JSON submission
                const payload = {};
                formData.forEach((value, key) => {
                  if (key.includes('.')) {
                    const parts = key.split('.');
                    if (parts.length === 2) {
                      if (!payload[parts[0]]) {
                        payload[parts[0]] = {};
                      }
                      payload[parts[0]][parts[1]] = value;
                    } else if (parts.length === 3) {
                      // For traits.name.first, create nested structure
                      if (!payload[parts[0]]) {
                        payload[parts[0]] = {};
                      }
                      if (!payload[parts[0]][parts[1]]) {
                        payload[parts[0]][parts[1]] = {};
                      }
                      payload[parts[0]][parts[1]][parts[2]] = value;
                    }
                  } else {
                    payload[key] = value;
                  }
                });
                
                // Add the WebAuthn credential to the payload
                payload[credentialName] = credential;
                
                console.log('Submitting WebAuthn registration with payload:', payload);
                
                // Strip the Kratos URL from action to use proxy
                let actionUrl = flow.ui.action;
                if (actionUrl.includes('://')) {
                  // Extract just the path portion
                  const url = new URL(actionUrl);
                  actionUrl = url.pathname + url.search;
                }
                
                // Submit the registration
                const res = await fetch(`${baseUrl}${actionUrl}`, {
                  method: flow.ui.method || 'POST',
                  credentials: 'include',
                  headers: {
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify(payload)
                });
                
                console.log('WebAuthn registration response status:', res.status);
                console.log('WebAuthn registration response redirected:', res.redirected);
                console.log('WebAuthn registration response URL:', res.url);
                
                // Handle successful registration
                if (res.ok) {
                  console.log('WebAuthn registration successful!');
                  
                  // Try to parse the response to check for any redirect instructions
                  try {
                    const data = await res.json();
                    console.log('WebAuthn registration response data:', data);
                    
                    // Check if there's a redirect_browser_to field
                    if (data.redirect_browser_to) {
                      window.location.href = data.redirect_browser_to;
                      return;
                    }
                  } catch (e) {
                    console.log('No JSON response body or error parsing:', e);
                  }
                  
                  // Default redirect to session check
                  window.location.href = '/session-check?new_registration=true';
                  return;
                }
                
                // Handle redirects (3xx status codes)
                if (res.redirected || (res.status >= 300 && res.status < 400)) {
                  console.log('WebAuthn registration redirected!');
                  // For redirects, we should follow the Location header
                  const redirectUrl = res.headers.get('Location') || res.url;
                  console.log('Redirecting to:', redirectUrl);
                  window.location.href = redirectUrl;
                  return;
                }
                
                // Handle errors
                console.error('WebAuthn registration failed with status:', res.status);
                
                try {
                  const data = await res.json();
                  console.error('WebAuthn error response:', data);
                  
                  // Update the flow with the error information
                  if (data) setFlow(data);
                  
                  // Extract and display error messages from the response
                  let errorMessage = 'Passkey registration failed';
                  
                  if (data.ui?.messages) {
                    const messages = data.ui.messages
                      .filter(m => m.type === 'error')
                      .map(m => m.text)
                      .join(' ');
                    if (messages) errorMessage = messages;
                  }
                  
                  setError(errorMessage);
                } catch (e) {
                  console.error('Failed to parse WebAuthn error response:', e);
                  setError('Passkey registration failed. Please try again or use password registration.');
                }
              } catch (err) {
                console.error('Passkey registration error:', err);
                // Provide specific error messages for common WebAuthn errors
                if (err.name === 'AbortError') {
                  setError('Passkey registration was cancelled. Please try again.');
                } else if (err.name === 'NotAllowedError') {
                  setError('Passkey registration was blocked. Please check your browser settings.');
                } else if (err.name === 'NotSupportedError') {
                  setError('Your browser does not support passkeys. Please use password registration instead.');
                } else {
                  setError(`Passkey registration error: ${err.message || 'Unknown error'}`);
                }
              }
            }}
            className="w-full mb-4 p-2 bg-yellow-400 text-gray-900 rounded hover:bg-yellow-500"
          >
            Register with Passkey
          </button>
        )}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-200 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-200 mb-1">First Name</label>
            <input
              type="text"
              value={firstName}
              onChange={e => setFirstName(e.target.value)}
              required
              className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-200 mb-1">Last Name</label>
            <input
              type="text"
              value={lastName}
              onChange={e => setLastName(e.target.value)}
              required
              className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-200 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
            />
            {password && (
              <div className="mt-2 text-xs space-y-1">
                <div className={password.length >= 8 ? 'text-green-400' : 'text-gray-400'}>
                  ✓ At least 8 characters
                </div>
                <div className={/[A-Z]/.test(password) ? 'text-green-400' : 'text-gray-400'}>
                  ✓ One uppercase letter
                </div>
                <div className={/[a-z]/.test(password) ? 'text-green-400' : 'text-gray-400'}>
                  ✓ One lowercase letter
                </div>
                <div className={/\d/.test(password) ? 'text-green-400' : 'text-gray-400'}>
                  ✓ One number
                </div>
                <div className={/[!@#$%^&*(),.?":{}|<>]/.test(password) ? 'text-green-400' : 'text-gray-400'}>
                  ✓ One special character
                </div>
              </div>
            )}
          </div>
          <button
            type="submit"
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            Create Account
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-300">
          Already have an account? <Link to="/login" className="text-yellow-400 hover:underline">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;