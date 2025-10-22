import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const VerificationPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTimeoutRef = useRef(null);

  // In development, we'll use the proxy defined in setupProxy.js
  let countdownInterval = null;
  // In development, we'll use the proxy defined in setupProxy.js
  // This avoids CORS and certificate issues with self-signed certs
  const isDevelopment = process.env.NODE_ENV === 'development';
  const KRATOS_URL = isDevelopment
    ? '' // Empty URL means use the current domain through proxy
    : (process.env.REACT_APP_KRATOS_PUBLIC_URL ||
       window.env?.REACT_APP_KRATOS_PUBLIC_URL ||
       'https://localhost:4433');

  console.log('Using Kratos URL:', KRATOS_URL || 'Local proxy');
  
  const [flow, setFlow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [verificationStatus, setVerificationStatus] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [redirectUrl, setRedirectUrl] = useState(null);

  // Initialize verification flow
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const flowId = urlParams.get('flow');
    const token = urlParams.get('token');
    const code = urlParams.get('code');
    
    console.log('🔍 Verification page params:', { flowId, token, code });
    
    if (flowId) {
      fetchFlowWithId(flowId);
    } else if (token || code) {
      // If we have a token or code directly, try to use it
      handleDirectVerification(token || code);
    } else {
      // Otherwise initiate a new verification flow
      initializeVerificationFlow();
    }
  }, [location.search]);

  // Fetch verification flow with ID
  const fetchFlowWithId = async (flowId) => {
    try {
      setLoading(true);
      const response = await fetch(
        `/.ory/self-service/verification/flows?id=${flowId}`,
        { credentials: 'include' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch verification flow');
      }
      
      const flowData = await response.json();
      console.log('Verification flow retrieved:', flowData);
      setFlow(flowData);
      
      // If there's a token in the URL, use it
      const urlParams = new URLSearchParams(location.search);
      const token = urlParams.get('token');
      if (token && flowData) {
        await verifyWithFlow(flowData, token);
      }
      
      // Check for error messages
      if (flowData.ui?.messages) {
        const errorMessages = flowData.ui.messages
          .filter(m => m.type === 'error')
          .map(m => m.text)
          .join(' ');
        
        if (errorMessages) setError(errorMessages);
      }
    } catch (err) {
      console.error('Error fetching verification flow:', err);
      setError('Failed to load verification flow. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Initialize a new verification flow
  const initializeVerificationFlow = async () => {
    try {
      setLoading(true);
      console.log('Initializing new verification flow');
      
      const response = await fetch(
        `/.ory/self-service/verification/browser`,
        {
          credentials: 'include',
          redirect: 'manual' // Handle redirects manually
        }
      );
      
      // Handle redirects if needed
      if (response.type === 'opaqueredirect' || response.redirected) {
        if (response.redirected) {
          const url = new URL(response.url);
          const flowId = url.searchParams.get('flow');
          
          if (flowId) {
            await fetchFlowWithId(flowId);
            return;
          }
        }
        
        // If we can't get flow ID from redirect, fetch the latest flow
        const latestFlowResponse = await fetch(
          `/.ory/self-service/verification/flows`,
          { credentials: 'include' }
        );
        
        if (!latestFlowResponse.ok) {
          throw new Error('Failed to get verification flow data');
        }
        
        const flowData = await latestFlowResponse.json();
        setFlow(flowData);
      } else {
        // No redirect, parse the response directly
        const flowData = await response.json();
        setFlow(flowData);
      }
    } catch (err) {
      console.error('Failed to initialize verification flow:', err);
      setError('Failed to load verification flow. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  // Handle direct verification with token or code
  const handleDirectVerification = async (value) => {
    try {
      setLoading(true);
      
      // First, we need to get a verification flow
      const response = await fetch(
        `/.ory/self-service/verification/browser`,
        {
          credentials: 'include',
          headers: { 'Accept': 'application/json' },
          redirect: 'manual'
        }
      );
      
      let flowData;
      
      if (response.ok) {
        flowData = await response.json();
      } else if (response.type === 'opaqueredirect' || response.redirected) {
        // Handle redirect
        const flowId = new URL(response.url || window.location.href).searchParams.get('flow');
        if (flowId) {
          const flowResponse = await fetch(
            `/.ory/self-service/verification/flows?id=${flowId}`,
            { 
              credentials: 'include',
              headers: { 'Accept': 'application/json' }
            }
          );
          if (flowResponse.ok) {
            flowData = await flowResponse.json();
          }
        }
      }
      
      if (!flowData) {
        throw new Error('Failed to get verification flow');
      }
      
      setFlow(flowData);
      
      // Now submit the verification with the token/code
      const formData = new URLSearchParams();
      
      // Add CSRF token
      const csrfNode = flowData.ui.nodes.find(n => n.attributes?.name === 'csrf_token');
      if (csrfNode) {
        formData.append('csrf_token', csrfNode.attributes.value);
      }
      
      // Set method to code
      formData.append('method', 'code');
      
      // Add the verification value (could be token or code)
      // Try both 'code' and 'token' fields as Kratos might accept either
      formData.append('code', value);
      
      console.log('🔐 Submitting verification with code/token:', value);
      
      // Submit verification
      const verifyResponse = await fetch(flowData.ui.action, {
        method: flowData.ui.method || 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
      });
      
      const responseData = await verifyResponse.json();
      
      if (verifyResponse.ok) {
        console.log('✅ Verification successful');
        setVerificationStatus('success');
        
        // Redirect after success
        setTimeout(() => {
          navigate('/dashboard');
        }, 3000);
      } else {
        console.error('❌ Verification failed:', responseData);
        
        // Extract error message
        let errorMessage = 'Verification failed';
        if (responseData.ui?.messages) {
          errorMessage = responseData.ui.messages
            .filter(m => m.type === 'error')
            .map(m => m.text)
            .join(' ');
        }
        
        setError(errorMessage);
        setVerificationStatus('error');
        setFlow(responseData); // Update flow with error state
      }
    } catch (err) {
      console.error('Verification error:', err);
      setError('Failed to verify. The link may have expired.');
      setVerificationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  // Try to verify with token directly
  const verifyToken = async (token) => {
    try {
      setLoading(true);
      
      // First, we need to get a verification flow
      const response = await fetch(
        `/.ory/self-service/verification/browser`,
        {
          credentials: 'include',
          redirect: 'manual'
        }
      );
      
      if (!response.ok && !response.redirected) {
        throw new Error('Failed to initialize verification flow');
      }
      
      let flowId;
      if (response.redirected) {
        const url = new URL(response.url);
        flowId = url.searchParams.get('flow');
      }
      
      if (!flowId) {
        throw new Error('Failed to get flow ID');
      }
      
      // Now fetch the flow data
      const flowResponse = await fetch(
        `/.ory/self-service/verification/flows?id=${flowId}`,
        { credentials: 'include' }
      );
      
      if (!flowResponse.ok) {
        throw new Error('Failed to fetch verification flow');
      }
      
      const flowData = await flowResponse.json();
      
      // Use the flow with the token
      await verifyWithFlow(flowData, token);
      
    } catch (err) {
      console.error('Verification error:', err);
      setError('Failed to verify your email. The link may have expired.');
      setVerificationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  // Verify with a specific flow and token
  const verifyWithFlow = async (flowData, token) => {
    try {
      if (!flowData || !flowData.ui) {
        throw new Error('Verification flow is not properly loaded');
      }
      
      // Create form data
      const formData = new FormData();
      
      // Add CSRF token if available
      const csrfNode = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token');
      if (csrfNode) {
        formData.append('csrf_token', csrfNode.attributes.value);
      }
      
      // Set method to code (Kratos is configured with code-based verification)
      formData.append('method', 'code');
      
      // Add verification token
      formData.append('token', token);
      
      // Convert to JSON payload
      const payload = {};
      formData.forEach((value, key) => {
        payload[key] = value;
      });
      
      console.log('Submitting verification with payload:', payload);
      
      // Submit verification - use relative URL for proxy
      const actionUrl = flowData.ui.action.startsWith('http') 
        ? flowData.ui.action.replace(/https?:\/\/[^\/]+/, '') 
        : flowData.ui.action;
      
      const verifyResponse = await fetch(actionUrl, {
        method: flowData.ui.method || 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
      });
      
      // Handle successful verification or redirects
      if (verifyResponse.ok || verifyResponse.redirected) {
        console.log('Verification successful or redirected');
        setVerificationStatus('success');
        
        // If we have a redirect URL, follow it after a short delay
        if (verifyResponse.redirected || verifyResponse.url) {
          redirectTimeoutRef.current = setTimeout(() => {
            navigate(verifyResponse.url);
          }, 3000);
        } else {
          // If no redirect, navigate to dashboard after a delay
          redirectTimeoutRef.current = setTimeout(() => {
            navigate('/dashboard');
          }, 3000);
        }
        return;
      }
      
      // Handle errors
      const errorData = await verifyResponse.json();
      console.error('Verification error response:', errorData);
      
      // Extract error messages
      let errorMessage = 'Verification failed';
      
      if (errorData.ui?.messages) {
        const messages = errorData.ui.messages
          .filter(m => m.type === 'error')
          .map(m => m.text)
          .join(' ');
        
        if (messages) errorMessage = messages;
      }
      
      setError(errorMessage);
      setVerificationStatus('error');
      
    } catch (err) {
      console.error('Verification error:', err);
      setError(`Verification error: ${err.message || 'Unknown error'}`);
      setVerificationStatus('error');
    }
  };

  // Handle email verification form submission
  const handleSubmitEmail = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setError('');
      
      if (!flow || !flow.ui) {
        setError('Verification form is not properly loaded. Please refresh the page.');
        return;
      }
      
      const email = e.target.email.value;
      if (!email) {
        setError('Please enter your email address.');
        return;
      }
      
      // Create form data
      const formData = new FormData();
      
      // Add CSRF token if available
      const csrfNode = flow.ui.nodes.find(n => n.attributes.name === 'csrf_token');
      if (csrfNode) {
        formData.append('csrf_token', csrfNode.attributes.value);
      }
      
      // Set method to code (Kratos is configured with code-based verification)
      formData.append('method', 'code');
      
      // Add email
      formData.append('email', email);
      
      // Convert to JSON payload
      const payload = {};
      formData.forEach((value, key) => {
        payload[key] = value;
      });
      
      console.log('Submitting verification request with payload:', payload);
      
      // Submit verification - use the action URL directly (should be proxied)
      const actionUrl = flow.ui.action.startsWith('http') 
        ? flow.ui.action.replace(/https?:\/\/[^\/]+/, '') // Convert absolute URL to relative
        : flow.ui.action;
      
      console.log('Submitting to:', actionUrl);
      
      const response = await fetch(actionUrl, {
        method: flow.ui.method || 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
      });
      
      // Handle successful submission
      if (response.ok) {
        const responseData = await response.json();
        console.log('Verification response:', responseData);
        
        // Update flow with new state (should now show code input)
        if (responseData.ui) {
          setFlow(responseData);
          setVerificationStatus('code-sent');
        } else {
          setVerificationStatus('email-sent');
        }
        return;
      }
      
      // Handle errors
      const errorData = await response.json();
      console.error('Email submission error:', errorData);
      
      // Update flow with error information
      if (errorData) setFlow(errorData);
      
      // Extract error messages
      let errorMessage = 'Failed to send verification email';
      
      if (errorData.ui?.messages) {
        const messages = errorData.ui.messages
          .filter(m => m.type === 'error')
          .map(m => m.text)
          .join(' ');
        
        if (messages) errorMessage = messages;
      }
      
      setError(errorMessage);
      
    } catch (err) {
      console.error('Email submission error:', err);
      setError(`Failed to send verification email: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  // Clear redirect timeout on unmount
  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
      }
    };
  }, []);

  // Countdown timer for redirect
  useEffect(() => {
    if (verificationStatus === 'success' && countdown === null) {
      setCountdown(3);
      
      const interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [verificationStatus, countdown]);

  // Show loading state
  if (loading && !verificationStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922] text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p>Verifying your email...</p>
        </div>
      </div>
    );
  }

  // Show successful verification
  if (verificationStatus === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
          <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-center mb-6">Email Verified</h2>
          
          <div className="mb-6 p-4 bg-green-800 bg-opacity-30 border border-green-700 rounded text-center">
            <p className="mb-2">Your email has been successfully verified!</p>
            <p>
              {countdown !== null
                ? `Redirecting in ${countdown} second${countdown === 1 ? '' : 's'}...`
                : 'You will be redirected to the dashboard shortly.'}
            </p>
          </div>
          
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => {
                if (redirectUrl) {
                  window.location.href = redirectUrl;
                } else {
                  navigate('/dashboard');
                }
              }}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go Now
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show email sent confirmation
  if (verificationStatus === 'email-sent') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
          <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-center mb-6">Verification Email Sent</h2>
          
          <div className="mb-6 p-4 bg-blue-800 bg-opacity-30 border border-blue-700 rounded text-center">
            <p className="mb-2">We've sent a verification email to your inbox.</p>
            <p>Please check your email and click the verification link.</p>
          </div>
          
          <div className="text-center text-gray-400 text-sm">
            <p className="mb-4">
              If you don't see the email, please check your spam folder or try again.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show verification error
  if (verificationStatus === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
          <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-center mb-6">Verification Failed</h2>
          
          <div className="mb-6 p-4 bg-red-900 bg-opacity-30 border border-red-800 rounded text-center">
            <p className="mb-2">{error || 'Failed to verify your email.'}</p>
            <p>The verification link may have expired or is invalid.</p>
          </div>
          
          <div className="flex flex-col space-y-4">
            <button
              onClick={() => initializeVerificationFlow()}
              className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              Request New Verification
            </button>
            
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show code input form when code is sent or user wants to enter manually
  if (verificationStatus === 'code-sent') {
    // Create a minimal flow structure if we don't have one
    const displayFlow = flow || {
      ui: {
        action: '/.ory/self-service/verification',
        method: 'POST',
        nodes: []
      }
    };
    
    const codeNode = displayFlow.ui.nodes.find(n => n.attributes?.name === 'code') || {
      attributes: { name: 'code' }
    };
    const emailNode = displayFlow.ui.nodes.find(n => n.attributes?.name === 'email' && n.attributes?.type === 'submit');
    
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#161922]">
        <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
          <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-center mb-6">Enter Verification Code</h2>
          
          {flow.ui.messages?.map((message, idx) => (
            <div key={idx} className={`mb-4 p-3 ${message.type === 'error' ? 'bg-red-900' : 'bg-blue-800'} bg-opacity-30 border ${message.type === 'error' ? 'border-red-800' : 'border-blue-700'} rounded`}>
              {message.text}
            </div>
          ))}
          
          {error && <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 text-white rounded">{error}</div>}
          
          <form 
            action={displayFlow.ui.action} 
            method={displayFlow.ui.method || 'POST'}
            onSubmit={async (e) => {
              e.preventDefault();
              setLoading(true);
              setError('');
              
              // If we don't have a proper flow, we need to create one first
              if (!flow) {
                try {
                  // Initialize a new verification flow
                  const flowResponse = await fetch('/.ory/self-service/verification/browser', {
                    credentials: 'include',
                    headers: { 'Accept': 'application/json' },
                  });
                  
                  const newFlow = await flowResponse.json();
                  setFlow(newFlow);
                  
                  // Now submit with the code
                  const formData = new URLSearchParams();
                  formData.append('csrf_token', newFlow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value || '');
                  formData.append('method', 'code');
                  formData.append('code', e.target.code.value);
                  formData.append('email', e.target.email?.value || '');
                  
                  const actionUrl = newFlow.ui.action.startsWith('http') 
                    ? newFlow.ui.action.replace(/https?:\/\/[^\/]+/, '') 
                    : newFlow.ui.action;
                  
                  const response = await fetch(actionUrl, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                      'Content-Type': 'application/x-www-form-urlencoded',
                      'Accept': 'application/json',
                    },
                    body: formData
                  });
                  
                  if (response.ok) {
                    window.location.href = '/dashboard';
                  } else {
                    const errorData = await response.json();
                    if (errorData.ui) {
                      setFlow(errorData);
                    }
                    setError(errorData.ui?.messages?.[0]?.text || 'Invalid code. Please try again.');
                  }
                } catch (err) {
                  console.error('Flow initialization error:', err);
                  setError('Failed to initialize verification. Please try again.');
                }
              } else {
                // We have a flow, proceed normally
                const formData = new URLSearchParams();
                
                // Get all form inputs
                const form = e.target;
                for (let i = 0; i < form.elements.length; i++) {
                  const element = form.elements[i];
                  if (element.name && element.value) {
                    formData.append(element.name, element.value);
                  }
                }
                
                const actionUrl = flow.ui.action.startsWith('http') 
                  ? flow.ui.action.replace(/https?:\/\/[^\/]+/, '') 
                  : flow.ui.action;
                
                try {
                  const response = await fetch(actionUrl, {
                    method: flow.ui.method || 'POST',
                    credentials: 'include',
                    headers: {
                      'Content-Type': 'application/x-www-form-urlencoded',
                      'Accept': 'application/json',
                    },
                    body: formData
                  });
                  
                  if (response.ok) {
                    // Verification successful - redirect to dashboard
                    window.location.href = '/dashboard';
                  } else {
                    const errorData = await response.json();
                    if (errorData.ui) {
                      setFlow(errorData);
                    }
                    setError(errorData.ui?.messages?.[0]?.text || 'Invalid code. Please try again.');
                  }
                } catch (err) {
                  console.error('Code submission error:', err);
                  setError('Failed to verify code. Please try again.');
                }
              }
              
              setLoading(false);
            }}
          >
            {/* Hidden inputs */}
            {displayFlow.ui.nodes
              .filter(n => n.type === 'input' && n.attributes?.type === 'hidden')
              .map((node, idx) => (
                <input
                  key={idx}
                  type="hidden"
                  name={node.attributes.name}
                  value={node.attributes.value || ''}
                />
              ))}
            
            {/* Email input for manual code entry */}
            {!flow && (
              <div className="mb-4">
                <label className="block text-gray-200 mb-1">Email Address</label>
                <input
                  type="email"
                  name="email"
                  required
                  className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
                  placeholder="Your email address"
                />
              </div>
            )}
            
            {/* Code input */}
            <div className="mb-6">
              <label className="block text-gray-200 mb-1">Verification Code</label>
              <input
                type="text"
                name={codeNode.attributes?.name || 'code'}
                required
                autoFocus={!!flow}
                className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
                placeholder="Enter 6-digit code"
              />
              <p className="text-sm text-gray-400">
                Enter the verification code from your email
              </p>
            </div>
            
            <div className="space-y-3">
              <button
                type="submit"
                name="method"
                value="code"
                disabled={loading}
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50"
              >
                {loading ? 'Verifying...' : 'Verify Code'}
              </button>
              
              {/* Resend button */}
              {emailNode && (
                <button
                  type="submit"
                  name={emailNode.attributes.name}
                  value={emailNode.attributes.value}
                  disabled={loading}
                  className="w-full py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded disabled:opacity-50"
                >
                  Resend Code
                </button>
              )}
            </div>
          </form>
          
          <p className="mt-6 text-center text-sm text-gray-300">
            <a href="/login" className="text-yellow-400 hover:underline">Back to Login</a>
          </p>
        </div>
      </div>
    );
  }

  // Default: Show email verification form with manual code option
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#161922]">
      <div className="w-full max-w-md bg-gray-800 p-8 rounded-lg shadow-lg text-white">
        <img src="/sting-logo.png" alt="STING Logo" className="w-32 h-32 mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-center mb-6">Verify Your Email</h2>
        
        {error && <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 text-white rounded">{error}</div>}
        
        <form onSubmit={handleSubmitEmail}>
          <div className="mb-6">
            <label className="block text-gray-200 mb-1">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              required
              className="w-full p-2 mb-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded focus:ring-2 focus:ring-yellow-400"
              placeholder="Enter your email address"
            />
            <p className="text-sm text-gray-400">
              Enter the email you registered with to receive a verification code.
            </p>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Verification Code'}
          </button>
        </form>
        
        {/* Manual code entry section */}
        <div className="mt-6 pt-6 border-t border-gray-700">
          <p className="text-center text-sm text-gray-400 mb-4">
            Already have a verification code?
          </p>
          <button
            onClick={() => {
              // Just switch to code entry mode without initializing a new flow
              setVerificationStatus('code-sent');
              setError(''); // Clear any existing errors
            }}
            className="w-full py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
          >
            Enter Code Manually
          </button>
        </div>
        
        <p className="mt-6 text-center text-sm text-gray-300">
          <a href="/login" className="text-yellow-400 hover:underline">Back to Login</a>
        </p>
      </div>
    </div>
  );
};

export default VerificationPage;