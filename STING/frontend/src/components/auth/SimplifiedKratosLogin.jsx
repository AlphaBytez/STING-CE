/**
 * Simplified Kratos Login Component
 * 
 * Clean, focused login component that handles:
 * 1. Regular login (AAL1)
 * 2. Admin step-up (AAL2) 
 * 3. Passkey authentication (with email fallback)
 * 
 * Eliminates complexity while maintaining all critical functionality.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { buildFlowUrl } from '../../utils/kratosConfig';

const SimplifiedKratosLogin = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Simple state management
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [flowData, setFlowData] = useState(null);
  
  // Check if this is AAL2 step-up
  const isAAL2 = searchParams.get('aal') === 'aal2';
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // Initialize Kratos flow
  useEffect(() => {
    initializeFlow();
  }, [isAAL2]);

  const initializeFlow = async () => {
    setIsLoading(true);
    setError('');

    try {
      // Use centralized utility to build flow URL with dynamic return_to
      // This ensures redirects work in Codespaces, VMs, and other forwarded environments
      const flowUrl = buildFlowUrl('login', {
        returnPath: returnTo,
        aal: isAAL2 ? 'aal2' : undefined,
        refresh: !isAAL2
      });

      const response = await axios.get(flowUrl, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      setFlowData(response.data);
      console.log(`🔐 ${isAAL2 ? 'AAL2' : 'Regular'} login flow initialized:`, response.data.id);

    } catch (error) {
      console.error('Failed to initialize login flow:', error);
      setError('Failed to initialize login. Please refresh the page.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email || !flowData) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams();
      params.append('identifier', email);
      params.append('method', 'identifier_first');
      
      const csrfToken = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
      if (csrfToken) {
        params.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(flowData.ui.action, params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true,
        validateStatus: () => true
      });
      
      if (response.status === 200 || response.status === 303) {
        // Success - redirect to dashboard
        window.location.href = returnTo;
      } else if (response.status === 400 && response.data?.ui) {
        // Flow updated with next step
        setFlowData(response.data);
        handleAuthenticationMethods(response.data);
      } else {
        setError('Authentication failed. Please try again.');
      }
      
    } catch (error) {
      console.error('Email submission failed:', error);
      setError('Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAuthenticationMethods = (flowData) => {
    const hasWebAuthn = flowData.ui.nodes.some(node => 
      node.group === 'webauthn' || node.attributes?.name?.includes('webauthn')
    );
    
    const hasCode = flowData.ui.nodes.some(node => 
      node.group === 'code' || node.attributes?.name === 'code'
    );
    
    const hasTOTP = flowData.ui.nodes.some(node => 
      node.group === 'totp' || node.attributes?.name === 'totp_code'
    );
    
    console.log('🔐 Available auth methods:', { hasWebAuthn, hasCode, hasTOTP });
    
    // For AAL2, prefer WebAuthn if available
    if (isAAL2 && hasWebAuthn) {
      console.log('🔐 AAL2 flow - WebAuthn available');
    }
    
    // DISABLED: Auto-submit code method to prevent premature submission
    if (false && hasCode && !hasWebAuthn && !hasTOTP) {
      console.log('🔐 Auto-submitting code method to get email verification');
      setTimeout(() => autoSubmitCodeMethod(flowData), 500);
    }
  };

  const autoSubmitCodeMethod = async (flowData) => {
    try {
      const params = new URLSearchParams();
      params.append('identifier', email);
      params.append('method', 'code');
      
      const csrfToken = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value;
      if (csrfToken) {
        params.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(flowData.ui.action, params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true,
        validateStatus: () => true
      });
      
      if (response.data?.ui) {
        setFlowData(response.data);
        setError('Check your email for the verification code');
      }
      
    } catch (error) {
      console.error('Auto-submit code method failed:', error);
      setError('Failed to request verification code');
    }
  };

  const handleWebAuthnLogin = () => {
    if (!flowData) return;
    
    const webauthnNode = flowData.ui.nodes.find(node => 
      node.attributes?.onclick && node.attributes.onclick.includes('webauthn')
    );
    
    if (webauthnNode?.attributes?.onclick) {
      console.log('🔐 Triggering WebAuthn login');

      // Add temporary error handler for eval execution to catch DOM errors
      const originalError = window.onerror;
      window.onerror = function(msg, url, line, col, error) {
        if (msg && msg.includes('Cannot set properties of null')) {
          console.warn('⚠️ Caught webauthn.js DOM error during eval (non-critical):', msg);
          return true; // Prevent default error handling
        }
        if (originalError) {
          return originalError(msg, url, line, col, error);
        }
        return false;
      };

      eval(webauthnNode.attributes.onclick);

      // Restore original error handler after a brief delay
      setTimeout(() => {
        window.onerror = originalError;
      }, 100);
    } else {
      setError('WebAuthn not available');
    }
  };

  const getAvailableMethods = () => {
    if (!flowData) return [];
    
    const methods = [];
    
    if (flowData.ui.nodes.some(n => n.group === 'webauthn' || n.attributes?.onclick?.includes('webauthn'))) {
      methods.push({ type: 'webauthn', label: 'Use Passkey', action: handleWebAuthnLogin });
    }
    
    if (flowData.ui.nodes.some(n => n.group === 'code' || n.attributes?.name === 'code')) {
      methods.push({ type: 'code', label: 'Send Email Code', action: () => autoSubmitCodeMethod(flowData) });
    }
    
    return methods;
  };

  // Simple, clean UI
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            {isAAL2 ? 'Additional Security Required' : 'Welcome to STING'}
          </h1>
          <p className="text-gray-300">
            {isAAL2 ? 'Please authenticate with your second factor' : 'Sign in to continue'}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {!flowData ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-yellow-400 mx-auto"></div>
            <p className="text-gray-300 mt-4">Initializing secure login...</p>
          </div>
        ) : (
          <div>
            {/* Email Input */}
            <form onSubmit={handleEmailSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400"
                  placeholder="Enter your email"
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !email}
                className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
              >
                {isLoading ? 'Processing...' : (isAAL2 ? 'Continue Authentication' : 'Sign In')}
              </button>
            </form>

            {/* Available Authentication Methods */}
            {getAvailableMethods().length > 0 && (
              <div className="mt-6 pt-6 border-t border-white/20">
                <p className="text-sm text-gray-300 mb-4">Alternative methods:</p>
                <div className="space-y-2">
                  {getAvailableMethods().map((method) => (
                    <button
                      key={method.type}
                      onClick={method.action}
                      className="w-full bg-white/10 hover:bg-white/20 text-white py-2 px-4 rounded-lg transition duration-200"
                    >
                      {method.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {isAAL2 && (
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-400">
              Admin access requires additional authentication for security
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimplifiedKratosLogin;