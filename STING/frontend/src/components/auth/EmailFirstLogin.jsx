/**
 * EmailFirstLogin - New email-first authentication with progressive passkey enhancement
 * 
 * Flow:
 * 1. Email address entry (always works)
 * 2. Email verification code 
 * 3. Success + optional passkey setup prompt
 * 4. Future logins show "Use passkey for faster login" option
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import axios from 'axios';

const EmailFirstLogin = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  
  // State management
  const [step, setStep] = useState('email'); // email, code, totp, success
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [flowData, setFlowData] = useState(null);
  const [hasPasskey, setHasPasskey] = useState(false);
  const [showPasskeyOption, setShowPasskeyOption] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);  // Assume users exist until checked

  // Check if this is AAL2 step-up
  const isAAL2 = searchParams.get('aal') === 'aal2';
  const returnTo = searchParams.get('return_to') || '/dashboard';

  // Dev mode detection and Mailpit URL
  const isDevelopment = process.env.NODE_ENV === 'development';
  const mailpitUrl = `http://${window.location.hostname}:8025`;

  // Define functions before useEffect to avoid hoisting issues
  const initializeKratosFlow = useCallback(async () => {
    try {
      // Use Flask backend API instead of direct Kratos call
      const flowUrl = isAAL2 
        ? '/api/auth/login-flow?aal=aal2'
        : '/api/auth/login-flow?refresh=true';
      
      const response = await axios.get(flowUrl, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      setFlowData(response.data);
      console.log('🔐 Kratos flow initialized:', response.data.id);
      return response.data;
    } catch (error) {
      console.error('Failed to initialize Kratos flow:', error);
      throw error;
    }
  }, [isAAL2]);

  const handleAAL2Flow = useCallback(async () => {
    try {
      console.log('🔐 Initializing AAL2 authentication flow...');
      
      // Initialize AAL2 Kratos flow
      const flow = await initializeKratosFlow();
      
      // Check what methods are available in the AAL2 flow
      const hasTOTP = flow.ui.nodes.some(node => node.group === 'totp');
      const hasWebAuthn = flow.ui.nodes.some(node => node.group === 'webauthn');
      
      console.log('🔐 AAL2 flow methods available:', { hasTOTP, hasWebAuthn });
      
      if (hasTOTP) {
        // Skip directly to TOTP input for AAL2
        setStep('totp');
      } else {
        console.error('🔐 No AAL2 methods available in flow');
        setError('No additional authentication methods available. Please contact support.');
      }
    } catch (error) {
      console.error('🔐 Failed to initialize AAL2 flow:', error);
      setError('Failed to initialize secure authentication. Please try again.');
    }
  }, [initializeKratosFlow]);

  const checkUserPasskey = useCallback(async () => {
    try {
      const response = await axios.get('/api/auth/me', { withCredentials: true });
      if (response.data?.has_passkey) {
        setHasPasskey(true);
        setShowPasskeyOption(true);
        console.log('🔐 User has existing passkey');
      }
    } catch (error) {
      console.log('🔐 No existing session or passkey');

      // For AAL2 flows, check Kratos flow for webauthn availability
      if (isAAL2) {
        console.log('🔐 AAL2 flow - will check Kratos flow for passkey methods');
        setShowPasskeyOption(true); // Assume passkey available for AAL2
      }
    }
  }, [isAAL2]);

  const checkHasUsers = useCallback(async () => {
    try {
      console.log('🔐 Checking if any users exist in the system...');
      const response = await axios.get('/api/auth/has-users', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true,
        timeout: 5000
      });

      if (response.data) {
        const hasUsers = response.data.has_users;
        setHasUsers(hasUsers);

        console.log('🔐 User check complete:', {
          has_users: hasUsers,
          user_count: response.data.user_count,
          source: response.data.source
        });

        if (!hasUsers) {
          console.warn('⚠️ NO USERS FOUND - This appears to be a fresh STING installation!');
          console.warn('⚠️ Please create an admin user with: sudo msting create admin admin@sting.local');
        }
      }
    } catch (error) {
      console.error('🔐 Failed to check user count:', error.message);
      console.log('🔐 Assuming users exist to avoid blocking legitimate access');
      setHasUsers(true);  // Fail-safe: assume users exist to prevent blocking real users
    }
  }, []);

  // Check for existing passkey on mount and handle AAL2 flow
  useEffect(() => {
    console.log('🔐 EmailFirstLogin mounted:', { isAAL2, returnTo, url: window.location.href });

    checkUserPasskey();
    checkHasUsers();

    // If this is AAL2 flow, we need to handle it differently
    if (isAAL2) {
      console.log('🔐 AAL2 flow detected, initializing AAL2 step-up...');
      handleAAL2Flow();
    }
  }, [isAAL2, checkUserPasskey, checkHasUsers, handleAAL2Flow, returnTo]);

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      // Initialize or get flow data
      let flow = flowData;
      if (!flow) {
        flow = await initializeKratosFlow();
      }
      
      // Directly submit with code method like working authentication
      const params = new URLSearchParams();
      params.append('identifier', email);
      params.append('method', 'code');
      
      const csrfToken = flow.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
      if (csrfToken) {
        params.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(flow.ui.action, params.toString(), {
        headers: { 
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        withCredentials: true,
        validateStatus: () => true
      });
      
      console.log('🔐 Email code request response:', response.status);
      
      if (response.status === 200 && response.data?.ui) {
        setFlowData(response.data);
        setStep('code');
        setError('If an account exists with this email address, a verification code has been sent.');
        console.log('🔐 Email code sent successfully');
      } else if (response.status === 400) {
        console.error('🔐 400 error response:', response.data);
        setError('If an account exists with this email address, a verification code will be sent.');
        setStep('code');
      } else {
        console.error('🔐 Unexpected response:', response.status, response.data);
        setError('If an account exists with this email address, a verification code will be sent.');
        setStep('code');
      }
      
    } catch (error) {
      console.error('Email submission failed:', error);
      setError('Failed to process email. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };


  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    if (!code || !flowData) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams();
      params.append('code', code);
      params.append('method', 'code');
      
      // Include identifier like working code does
      if (email) {
        params.append('identifier', email);
      }
      
      const csrfToken = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
      if (csrfToken) {
        params.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(flowData.ui.action, params.toString(), {
        headers: { 
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        withCredentials: true,
        validateStatus: () => true
      });
      
      console.log('🔐 Code verification response:', response.status, response.data);
      
      // Handle AAL2 step-up requirement FIRST (most common for admins)
      if (response.status === 422 && response.data?.redirect_browser_to) {
        const redirectUrl = response.data.redirect_browser_to;
        console.log('🔐 AAL2 step-up required, redirecting to:', redirectUrl);
        
        // Check if it's an AAL2 redirect
        if (redirectUrl.includes('aal=aal2')) {
          // Redirect to our AAL2 step-up page instead of creating new login
          console.log('🔐 AAL2 step-up required, redirecting to step-up component');
          navigate('/security-upgrade', {
            state: {
              fromAAL1: true,
              email: email,
              returnTo: returnTo
            }
          });
          return;
        } else {
          // Other redirects go as-is
          window.location.href = redirectUrl;
          return;
        }
      }
      
      // Check if challenge was passed (flow state = "passed_challenge")
      if (response.data?.state === 'passed_challenge' || response.status === 200) {
        console.log('🔐 Authentication successful! Redirecting...');
        if (response.data?.redirect_browser_to) {
          // SECURITY: Check if this is actually an AAL2 redirect disguised as success
          if (response.data.redirect_browser_to.includes('aal=aal2')) {
            console.log('🔐 Success response contains AAL2 redirect, handling as step-up');
            navigate('/security-upgrade', {
              state: {
                fromAAL1: true,
                email: email,
                returnTo: returnTo
              }
            });
            return;
          }
          window.location.href = response.data.redirect_browser_to;
        } else {
          // Default redirect to dashboard
          window.location.href = returnTo;
        }
        return;
      }
      
      if (response.status === 303) {
        // Success - go to return URL
        window.location.href = returnTo;
      } else if (response.status === 400) {
        // Detailed 400 error logging
        console.error('🔐 400 Error Details:', {
          status: response.status,
          data: response.data,
          flowId: flowData?.id,
          flowState: flowData?.state,
          ui: response.data?.ui
        });
        
        if (response.data?.ui?.messages) {
          const errorMsg = response.data.ui.messages.find(m => m.type === 'error')?.text;
          setError(errorMsg || 'Verification failed. Please try again.');
        } else {
          setError(`Verification failed (${response.status}). Please try again.`);
        }
      } else if (response.data?.ui?.messages) {
        // Show error message
        const errorMsg = response.data.ui.messages.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid verification code. Please try again.');
      } else {
        setError('Invalid verification code. Please try again.');
      }
      
    } catch (error) {
      console.error('Code verification failed:', error);
      setError('Failed to verify code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTOTPSubmit = async (e) => {
    e.preventDefault();
    if (!totpCode || !flowData) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams();
      params.append('totp_code', totpCode);
      params.append('method', 'totp');
      
      const csrfToken = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
      if (csrfToken) {
        params.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(flowData.ui.action, params.toString(), {
        headers: { 
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        withCredentials: true,
        validateStatus: () => true
      });
      
      console.log('🔐 TOTP verification response:', response.status);
      
      if (response.status === 200 || response.data?.state === 'passed_challenge') {
        console.log('🔐 AAL2 authentication successful!');
        // Redirect to the originally requested page
        window.location.href = returnTo;
      } else if (response.data?.redirect_browser_to) {
        window.location.href = response.data.redirect_browser_to;
      } else if (response.data?.ui?.messages) {
        const errorMsg = response.data.ui.messages.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid TOTP code. Please try again.');
      } else {
        setError('Invalid TOTP code. Please try again.');
      }
      
    } catch (error) {
      console.error('TOTP verification failed:', error);
      setError('Failed to verify TOTP code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyLogin = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      console.log('🔐 Attempting passkey authentication for', isAAL2 ? 'AAL2' : 'initial login');
      
      // Initialize Kratos flow for WebAuthn
      let flow = flowData;
      if (!flow) {
        flow = await initializeKratosFlow();
      }
      
      // Look for WebAuthn trigger in the flow
      const webauthnTrigger = flow.ui.nodes.find(node => 
        node.attributes?.name === 'webauthn_login_trigger' ||
        node.attributes?.onclick?.includes('webauthn') ||
        node.group === 'webauthn'
      );
      
      if (webauthnTrigger && webauthnTrigger.attributes?.onclick) {
        console.log('🔐 Found WebAuthn trigger, executing...');
        // Execute the WebAuthn trigger
        eval(webauthnTrigger.attributes.onclick);
      } else {
        console.log('🔐 No WebAuthn trigger found in flow, checking for method...');
        
        // Try submitting webauthn method directly
        const params = new URLSearchParams();
        params.append('method', 'webauthn');
        
        const csrfToken = flow.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
        if (csrfToken) {
          params.append('csrf_token', csrfToken);
        }
        
        const response = await axios.post(flow.ui.action, params.toString(), {
          headers: { 
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        });
        
        console.log('🔐 WebAuthn method response:', response.status, response.data);
        
        if (response.data?.redirect_browser_to) {
          window.location.href = response.data.redirect_browser_to;
        } else {
          setError('WebAuthn authentication not available. Please use email code.');
        }
      }
      
    } catch (error) {
      console.error('Passkey authentication failed:', error);
      setError('Passkey authentication failed. Please use email code.');
    } finally {
      setIsLoading(false);
    }
  };

  // Email entry step
  if (step === 'email') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
          <div className="text-center mb-8">
            <img src="/sting-logo.png" alt="STING Logo" className="w-24 h-24 mx-auto mb-4" />
            <h1 className="text-3xl font-bold text-white mb-2">
              {isAAL2 ? 'Additional Security Required' : 'Welcome to STING'}
            </h1>
            <p className="text-gray-300">
              {isAAL2 ? 'Please verify your identity' : 'Sign in with your email address'}
            </p>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* No users warning - show hint to create admin */}
          {!hasUsers && !isAAL2 && (
            <div className="mb-6 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="text-yellow-300 text-2xl">⚠️</div>
                <div className="flex-1">
                  <h3 className="text-yellow-300 font-medium mb-2">No Users Found</h3>
                  <p className="text-yellow-200 text-sm mb-3">
                    This appears to be a fresh STING installation. You need to create an admin account first.
                  </p>
                  <div className="bg-black/30 rounded p-3 font-mono text-xs text-yellow-100 mb-2">
                    sudo msting create admin admin@sting.local
                  </div>
                  <p className="text-yellow-200 text-xs">
                    Run this command on your server, then return here to log in.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Passkey quick option for returning users and AAL2 */}
          {showPasskeyOption && (
            <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-yellow-300 font-medium">
                    {isAAL2 ? 'Complete Security Verification' : 'Faster Sign In'}
                  </h3>
                  <p className="text-yellow-200 text-sm">
                    {isAAL2 ? 'Use your passkey to complete additional authentication' : 'Use your passkey for instant access'}
                  </p>
                </div>
                <button
                  onClick={handlePasskeyLogin}
                  disabled={isLoading}
                  className="bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black px-4 py-2 rounded-lg font-medium transition-colors"
                >
                  Use Passkey
                </button>
              </div>
              <div className="mt-3 pt-3 border-t border-yellow-500/20">
                <p className="text-yellow-200 text-xs text-center">Or continue with email below</p>
              </div>
            </div>
          )}

          {/* Email form */}
          <form onSubmit={handleEmailSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Enter your email address"
                required
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !email}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Processing...' : 'Continue with Email'}
            </button>
          </form>

          {/* Registration link */}
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Don't have an account?{' '}
              <button
                onClick={() => navigate('/register')}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign up here
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Code verification step
  if (step === 'code') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
          <div className="text-center mb-8">
            <img src="/sting-logo.png" alt="STING Logo" className="w-20 h-20 mx-auto mb-4" />
            <h1 className="text-3xl font-bold text-white mb-2">Check Your Email</h1>
            <p className="text-gray-300">
              Enter the verification code sent to
            </p>
            <p className="text-blue-300 font-medium">{email}</p>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleCodeSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Verification Code
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 text-center text-2xl tracking-widest"
                placeholder="000000"
                maxLength="6"
                required
                disabled={isLoading}
                autoComplete="one-time-code"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !code}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Verifying...' : 'Verify & Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center space-y-2">
            <button
              onClick={() => setStep('email')}
              className="text-gray-400 hover:text-white text-sm"
            >
              ← Use different email
            </button>
            <div className="text-gray-500 text-xs">
              Check your spam folder if you don't see the email
            </div>
          </div>

          {/* Development Mode - Mailpit Link */}
          {isDevelopment && (
            <div className="mt-6 p-4 bg-gradient-to-r from-green-900/30 to-blue-900/30 border-2 border-green-500/50 rounded-lg shadow-lg">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-green-300 font-semibold text-sm">
                    🔧 Development Mode
                  </p>
                  <p className="text-gray-300 text-xs mt-1">
                    Access your verification code directly
                  </p>
                </div>
              </div>
              <a
                href={mailpitUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full mt-3 bg-green-600 hover:bg-green-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 text-center shadow-md hover:shadow-lg transform hover:scale-105"
              >
                📧 Open Mailpit ({window.location.hostname}:8025)
              </a>
            </div>
          )}
        </div>
      </div>
    );
  }

  // TOTP verification step (for AAL2)
  if (step === 'totp') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
          <div className="text-center mb-8">
            <img src="/sting-logo.png" alt="STING Logo" className="w-20 h-20 mx-auto mb-4" />
            <h1 className="text-3xl font-bold text-white mb-2">Two-Factor Authentication</h1>
            <p className="text-gray-300 mb-2">
              You're accessing sensitive data that requires additional verification
            </p>
            <p className="text-blue-300 text-sm">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleTOTPSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Authenticator Code
              </label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 text-center text-2xl tracking-widest"
                placeholder="000000"
                maxLength="6"
                required
                disabled={isLoading}
                autoComplete="one-time-code"
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !totpCode}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Verifying...' : 'Verify'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                // Go back to dashboard without AAL2
                navigate('/dashboard');
              }}
              className="text-gray-400 hover:text-white text-sm"
            >
              Cancel
            </button>
          </div>

          {/* Help text */}
          <div className="mt-6 space-y-3">
            <div className="p-3 bg-blue-900/20 border border-blue-600/30 rounded-lg">
              <p className="text-blue-300 text-sm">
                🔐 <strong>Why this step?</strong> Admin accounts require two-factor authentication for accessing reports and sensitive data.
              </p>
            </div>
            <div className="p-3 bg-yellow-900/20 border border-yellow-600/30 rounded-lg">
              <p className="text-yellow-300 text-sm">
                💡 <strong>Tip:</strong> Open Google Authenticator, Authy, or your TOTP app to get your current 6-digit code.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default EmailFirstLogin;