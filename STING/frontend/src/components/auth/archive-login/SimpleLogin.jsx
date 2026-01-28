import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../../theme/sting-glass-theme.css';
import '../../theme/glass-login-override.css';

/**
 * SimpleLogin - A simplified login component that supports both passkeys and passwords
 */
const SimpleLogin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [showPasswordField, setShowPasswordField] = useState(false);
  const navigate = useNavigate();

  // Check WebAuthn support
  useEffect(() => {
    const checkWebAuthnSupport = async () => {
      try {
        if (window.PublicKeyCredential) {
          setWebAuthnSupported(true);
          console.log('🔐 WebAuthn is supported');
        }
      } catch (err) {
        console.error('🔐 Error checking WebAuthn support:', err);
        setWebAuthnSupported(false);
      }
    };
    
    checkWebAuthnSupport();
  }, []);

  // Handle passkey authentication
  const handlePasskeyLogin = async (useEmail = false) => {
    try {
      setIsLoading(true);
      setError('');
      
      // Start authentication
      const beginData = useEmail && email ? { username: email } : {};
      const beginResponse = await axios.post('/api/webauthn/authentication/begin', beginData, {
        withCredentials: true
      });
      
      console.log('🔐 Auth options received:', beginResponse.data);
      
      // Convert for browser API
      const publicKeyOptions = beginResponse.data;
      
      // Handle base64url encoded challenge
      const challengeStr = publicKeyOptions.publicKey ? publicKeyOptions.publicKey.challenge : publicKeyOptions.challenge;
      if (challengeStr) {
        const base64 = challengeStr.replace(/-/g, '+').replace(/_/g, '/');
        const padded = base64 + '=='.substring(0, (4 - base64.length % 4) % 4);
        publicKeyOptions.challenge = Uint8Array.from(atob(padded), c => c.charCodeAt(0));
        if (publicKeyOptions.publicKey) {
          publicKeyOptions.publicKey.challenge = publicKeyOptions.challenge;
        }
      }
      
      if (publicKeyOptions.publicKey.allowCredentials && publicKeyOptions.publicKey.allowCredentials.length > 0) {
        publicKeyOptions.publicKey.allowCredentials = publicKeyOptions.publicKey.allowCredentials.map(cred => {
          // Validate credential object before accessing properties
          if (!cred || !cred.id) {
            throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
          }
          const credIdStr = cred.id.replace(/-/g, '+').replace(/_/g, '/');
          const paddedCredId = credIdStr + '=='.substring(0, (4 - credIdStr.length % 4) % 4);
          return {
            ...cred,
            id: Uint8Array.from(atob(paddedCredId), c => c.charCodeAt(0))
          };
        });
      } else if (!useEmail) {
        // For discoverable credentials
        delete publicKeyOptions.publicKey.allowCredentials;
      }
      
      // Get credential
      const credential = await navigator.credentials.get({
        publicKey: publicKeyOptions.publicKey
      });
      
      // Validate credential before accessing properties
      if (!credential || !credential.id || !credential.rawId || !credential.response) {
        console.error('❌ Invalid credential received from authenticator:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      // Complete authentication
      const completeResponse = await axios.post('/api/webauthn/authentication/complete', {
        credential: {
          id: credential.id,
          rawId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
          response: {
            clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(credential.response.clientDataJSON))),
            authenticatorData: btoa(String.fromCharCode(...new Uint8Array(credential.response.authenticatorData))),
            signature: btoa(String.fromCharCode(...new Uint8Array(credential.response.signature))),
            userHandle: credential.response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(credential.response.userHandle))) : null
          },
          type: credential.type
        }
      }, {
        withCredentials: true
      });
      
      if (completeResponse.data.verified) {
        console.log('🔐 Authentication successful!');
        window.location.href = '/dashboard';
      } else {
        setError('Authentication failed');
      }
      
    } catch (err) {
      console.error('🔐 Passkey error:', err);
      if (err.response?.data?.error_code === 'NO_PASSKEYS') {
        setError('No passkeys found for this account');
        setShowPasswordField(true);
      } else if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.name === 'NotAllowedError') {
        setError('Authentication was cancelled');
      } else {
        setError('Failed to authenticate with passkey');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Handle password login via Kratos
  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }
    
    // For password login, redirect to Kratos login page with pre-filled email
    // This is simpler than trying to manage the Kratos flow directly
    const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || process.env.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
    const returnTo = encodeURIComponent(window.location.origin + '/dashboard');
    window.location.href = `${kratosUrl}/self-service/login/browser?return_to=${returnTo}`;
  };

  // Handle email submission
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    
    // Check if user has passkeys
    try {
      const checkResponse = await axios.post('/api/webauthn/debug/check-passkeys', {
        email: email
      }, {
        withCredentials: true,
        validateStatus: () => true
      });
      
      if (checkResponse.status === 200 && checkResponse.data?.passkeys?.active > 0) {
        // User has passkeys, try to authenticate
        await handlePasskeyLogin(true);
      } else {
        // No passkeys, show password field
        setShowPasswordField(true);
      }
    } catch (err) {
      console.log('Could not check passkeys, showing password field');
      setShowPasswordField(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-slate-800 to-gray-900"></div>
      
      {/* Animated background shapes */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      {/* Glass card container */}
      <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
        <div className="text-center mb-6">
          <img src="/sting-logo.png" alt="STING Logo" className="w-24 h-24 mx-auto mb-2" />
          <h2 className="text-2xl font-bold">Sign in to STING</h2>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded text-red-300">
            {error}
          </div>
        )}
        
        {/* Quick passkey button */}
        {webAuthnSupported && !showPasswordField && (
          <>
            <button
              onClick={() => handlePasskeyLogin(false)}
              className="mb-4 w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 flex items-center justify-center font-semibold"
              disabled={isLoading}
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
              </svg>
              {isLoading ? 'Authenticating...' : 'Sign in with Passkey'}
            </button>
            
            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-600"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-800 text-gray-400">Or sign in with email</span>
              </div>
            </div>
          </>
        )}
        
        {/* Email/Password form */}
        <form onSubmit={showPasswordField ? handlePasswordLogin : handleEmailSubmit}>
          <div className="mb-4">
            <label className="block text-gray-300 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
              placeholder="you@example.com"
              required
              autoFocus
              disabled={showPasswordField}
            />
          </div>
          
          {showPasswordField && (
            <div className="mb-4">
              <label className="block text-gray-300 mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                required
                autoFocus
              />
            </div>
          )}
          
          <button 
            type="submit" 
            className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
            disabled={isLoading}
          >
            {isLoading ? 'Signing in...' : (showPasswordField ? 'Sign In' : 'Continue')}
          </button>
        </form>
        
        {showPasswordField && (
          <button
            onClick={() => {
              setShowPasswordField(false);
              setPassword('');
              setError('');
            }}
            className="mt-2 text-sm text-gray-400 hover:text-gray-300"
          >
            ← Back
          </button>
        )}
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Don't have an account?{' '}
            <a href="/register" className="text-yellow-400 hover:underline">
              Register
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SimpleLogin;