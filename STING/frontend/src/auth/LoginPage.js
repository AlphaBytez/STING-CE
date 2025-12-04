import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

// Dynamically import WebAuthn to prevent server-side rendering issues
let startAuthentication;
let webAuthnLoading = false;
let webAuthnLoaded = false;

const loadWebAuthn = async () => {
  if (webAuthnLoaded || webAuthnLoading) return startAuthentication;
  
  webAuthnLoading = true;
  try {
    const module = await import('@simplewebauthn/browser');
    startAuthentication = module.startAuthentication;
    webAuthnLoaded = true;
    return startAuthentication;
  } catch (error) {
    console.error('Failed to load WebAuthn module:', error);
    throw error;
  } finally {
    webAuthnLoading = false;
  }
};

// Start loading immediately if in browser
if (typeof window !== 'undefined') {
  loadWebAuthn().catch(console.error);
}
// Simple login page using Ory Kratos
const LoginPage = () => {
  // In development, we use the proxy in setupProxy.js
  // In production, we use the Kratos URL from environment  
  const isDev = process.env.NODE_ENV === 'development';
  const KRATOS_URL = process.env.REACT_APP_KRATOS_PUBLIC_URL || window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // In development mode, use the full Kratos URL since there's no nginx proxy
  // In production, nginx handles the proxying
  const baseUrl = process.env.NODE_ENV === 'development' ? KRATOS_URL : '';
  const [flow, setFlow] = useState(null);
  const [loadingFlow, setLoadingFlow] = useState(true);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [passkeyLoading, setPasskeyLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Check for registration success message
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('registered') === 'true') {
      setSuccessMessage('Registration successful! Please log in with your credentials.');
    }
  }, []);

  // Initialize login flow with browser flow instead of API flow to avoid CORS/CSRF issues
  useEffect(() => {
    // Check if we need to refresh an existing session
    const urlParams = new URLSearchParams(window.location.search);
    const needsRefresh = urlParams.get('refresh') === 'true';
    
    // Use the browser flow instead of the API flow to ensure proper cookie handling
    // Always add refresh=true to force a new login flow even if a session exists
    fetch(`${baseUrl}/self-service/login/browser?refresh=true`, {
      credentials: 'include',
      redirect: 'follow'
    })
      .then(res => {
        // If it's a redirect, get the URL and extract the flow ID
        if (res.redirected) {
          const url = new URL(res.url);
          const flowId = url.searchParams.get('flow');
          if (flowId) {
            // Now fetch the flow details
            return fetch(`${baseUrl}/self-service/login/flows?id=${flowId}`, {
              credentials: 'include'
            });
          }
        }
        return res;
      })
      .then(res => res.json())
      .then(data => {
        console.log('Login flow data:', data);
        setFlow(data);
      })
      .catch(err => {
        console.error('Failed to initialize login flow:', err);
        setError('Failed to load login form');
      })
      .finally(() => setLoadingFlow(false));
  }, [KRATOS_URL]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      // Extract CSRF token if present
      const csrfNode = flow?.ui?.nodes?.find(n => n.attributes.name === 'csrf_token');
      const csrfToken = csrfNode?.attributes?.value;
      console.log('CSRF Token:', csrfToken);
      
      // Prepare login payload
      const payload = {
        method: 'password',
        identifier: identifier, // Changed from password_identifier to identifier
        password: password,
        csrf_token: csrfToken
      };
      
      console.log('Login payload:', payload);
      console.log('Action URL:', flow.ui.action);
      
      // Kratos expects form-encoded data, not JSON
      const formData = new URLSearchParams();
      Object.keys(payload).forEach(key => {
        if (payload[key] !== undefined && payload[key] !== null) {
          formData.append(key, payload[key]);
        }
      });
      
      const res = await fetch(`${baseUrl}${flow?.ui?.action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: formData.toString()
      });
      if (res.ok) {
        window.location.href = '/dashboard';
      } else {
        const data = await res.json().catch(() => null);
        const messages = data?.ui?.messages?.map(m => m.text) || [];
        const errorText = messages.join(' ') || 'Login failed';
        
        // Check if the error indicates the account doesn't exist
        // Kratos typically returns a generic error for security, but we can check for specific patterns
        if (errorText.toLowerCase().includes('credentials') || errorText.toLowerCase().includes('invalid')) {
          setError(errorText + '. If you don\'t have an account, please register first.');
        } else {
          setError(errorText);
        }
        
        if (data) setFlow(data);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Login error. Please try again.');
    }
  };

  // Show loading or error state before form
  if (loadingFlow) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
        Loading login form...
      </div>
    );
  }
  if (!flow) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white p-4">
        <p className="text-red-500">{error || 'Unable to load login form'}</p>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-800 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-yellow-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-cyan-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-amber-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>
      
      {/* Glass morphism card */}
      <div className="relative w-full max-w-md">
        <div className="absolute inset-0 bg-gradient-to-r from-yellow-400 to-cyan-400 shadow-lg transform -skew-y-6 sm:skew-y-0 sm:-rotate-6 sm:rounded-3xl"></div>
        <div className="relative bg-slate-700/90 backdrop-blur-xl p-8 rounded-2xl shadow-2xl border border-slate-600/50">
          <img src="/sting-logo.png" alt="Hive Logo" className="w-32 h-32 mx-auto mb-6 drop-shadow-2xl" />
          <h2 className="text-3xl font-bold text-center mb-2 text-slate-100">Welcome Back</h2>
          <p className="text-center text-slate-300 mb-6">Sign in to your Hive account</p>
          
          {successMessage && (
            <div className="mb-4 p-3 bg-green-500/20 backdrop-blur-sm border border-green-500/50 text-green-200 rounded-lg">
              {successMessage}
            </div>
          )}
          
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 backdrop-blur-sm border border-red-500/50 text-red-200 rounded-lg">
              <div>{error}</div>
              <button
                onClick={() => {
                  setError('');
                  // Reinitialize the login flow
                  window.location.reload();
                }}
                className="mt-2 px-4 py-2 bg-red-500/30 hover:bg-red-500/40 text-red-100 rounded transition-colors duration-200 text-sm"
              >
                Try Again
              </button>
            </div>
          )}
          {flow && flow.ui?.nodes?.some(n => n.attributes.type === 'webauthn') && (
            <button
              onClick={async () => {
                setError('');
                setPasskeyLoading(true);
                
                if (!flow) {
                  setPasskeyLoading(false);
                  return;
                }
                
                try {
                  // Ensure WebAuthn module is loaded
                  await loadWebAuthn();
                  
                  if (!startAuthentication) {
                    setError('WebAuthn module failed to load. Please refresh the page and try again.');
                    setPasskeyLoading(false);
                    return;
                  }
                  
                  const webauthnNode = flow?.ui?.nodes?.find(n => n.attributes.type === 'webauthn');
                  if (!webauthnNode) {
                    setError('Passkey login not available');
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
                    
                    // Start WebAuthn authentication
                    console.log('Starting WebAuthn authentication with options:', publicKey);
                    const assertion = await startAuthentication(publicKey);
                    console.log('WebAuthn assertion completed:', assertion);
                    
                    // Prepare and send payload
                    const payload = { method: 'webauthn' };
                    payload[webauthnNode.attributes.name] = assertion;
                    
                    const res = await fetch(`${baseUrl}${flow?.ui?.action}`, {
                      method: 'POST',
                      credentials: 'include',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(payload),
                    });
                    
                    if (res.ok) {
                      window.location.href = '/dashboard';
                    } else {
                      let errorMessage = 'Passkey login failed';
                      try {
                        const data = await res.json();
                        if (data && data.ui && data.ui.messages) {
                          errorMessage = data.ui.messages.map(m => m.text).join(' ');
                        }
                        if (data) setFlow(data);
                      } catch (e) {
                        console.error('Failed to parse error response:', e);
                      }
                      setError(errorMessage);
                    }
                  } catch (err) {
                    console.error('Passkey error:', err);
                    setError(`Passkey authentication error: ${err.message || 'Unknown error'}`);
                  }
                } catch (err) {
                  console.error('WebAuthn loading error:', err);
                  setError('Failed to load passkey authentication');
                } finally {
                  setPasskeyLoading(false);
                }
              }}
              className="w-full mb-4 p-3 bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-900 rounded-lg font-semibold hover:from-yellow-500 hover:to-amber-600 transform hover:scale-[1.02] transition-all duration-200 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              disabled={passkeyLoading}
            >
              {passkeyLoading ? 'Loading Passkey...' : '🔑 Continue with Passkey'}
            </button>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-slate-200 text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={identifier}
                onChange={e => setIdentifier(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full px-4 py-3 bg-slate-800/50 backdrop-blur-sm text-slate-100 placeholder-slate-400 border border-slate-600/50 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all duration-200"
              />
            </div>
            <div>
              <label className="block text-slate-200 text-sm font-medium mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-slate-800/50 backdrop-blur-sm text-slate-100 placeholder-slate-400 border border-slate-600/50 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all duration-200"
              />
            </div>
            
            {/* Remember me and Forgot password */}
            <div className="flex items-center justify-between">
              <label className="flex items-center">
                <input type="checkbox" className="w-4 h-4 text-yellow-400 bg-slate-800 border-slate-600 rounded focus:ring-yellow-400 focus:ring-2" />
                <span className="ml-2 text-sm text-slate-300">Remember me</span>
              </label>
              <Link to="/forgot-password" className="text-sm text-yellow-400 hover:text-yellow-300 transition-colors">
                Forgot password?
              </Link>
            </div>
            
            <button
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-yellow-400 to-amber-500 text-slate-900 rounded-lg font-semibold hover:from-yellow-500 hover:to-amber-600 transform hover:scale-[1.02] transition-all duration-200 shadow-lg"
            >
              Sign In
            </button>
          </form>
          
          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-600/50"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-slate-700/90 text-slate-400">Or continue with</span>
            </div>
          </div>
          
          {/* Social login buttons */}
          <div className="grid grid-cols-3 gap-3">
            <button className="flex items-center justify-center py-2 px-4 bg-slate-800/50 backdrop-blur-sm border border-slate-600/50 rounded-lg hover:bg-slate-800/70 transition-all duration-200">
              <span className="w-5 h-5 text-red-400">G</span>
            </button>
            <button className="flex items-center justify-center py-2 px-4 bg-slate-800/50 backdrop-blur-sm border border-slate-600/50 rounded-lg hover:bg-slate-800/70 transition-all duration-200">
              <span className="w-5 h-5 text-slate-100">GH</span>
            </button>
            <button className="flex items-center justify-center py-2 px-4 bg-slate-800/50 backdrop-blur-sm border border-slate-600/50 rounded-lg hover:bg-slate-800/70 transition-all duration-200">
              <span className="w-5 h-5 text-blue-400">MS</span>
            </button>
          </div>
          
          <p className="mt-6 text-center text-sm text-slate-300">
            Don't have an account?{' '}
            <Link to="/register" className="text-yellow-400 hover:text-yellow-300 font-medium transition-colors">
              Create account
            </Link>
          </p>
        </div>
      </div>
      
      {/* Add CSS for animations */}
      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </div>
  );
};

export default LoginPage;