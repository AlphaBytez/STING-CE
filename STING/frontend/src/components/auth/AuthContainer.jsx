import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Fingerprint, Mail } from 'lucide-react';
import { Passwordless } from "supertokens-auth-react/recipe/passwordless";
import HybridAuth from './HybridAuth';

const AuthContainer = ({ mode = 'login' }) => {
  const [authMode, setAuthMode] = useState(mode);
  const [authMethod, setAuthMethod] = useState('passkey');
  const [isPasskeyAvailable, setIsPasskeyAvailable] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const checkSecurityContext = () => {
      console.log("Security Context Check:", {
        isSecureContext: window.isSecureContext,
        protocol: window.location.protocol,
        host: window.location.host,
        origin: window.location.origin
      });
    };
  
    const checkPasskeySupport = async () => {
      // Check security context first
      checkSecurityContext();
  
      console.log("🔐 Safari Passkey Check Started");
      
      if (!window.isSecureContext) {
        console.error("WebAuthn requires a secure context!");
        setAuthMethod('traditional');
        return;
      }
  
      if ('PublicKeyCredential' in window) {
        try {
          console.log("PublicKeyCredential found, checking capabilities...");
          const available = await window.PublicKeyCredential
            .isUserVerifyingPlatformAuthenticatorAvailable();
          
          console.log("Passkey availability:", available);
          setIsPasskeyAvailable(available);
          setAuthMethod(available ? 'passkey' : 'traditional');
  
        } catch (error) {
          console.error("Passkey check failed:", error);
          setAuthMethod('traditional');
        }
      } else {
        console.log("PublicKeyCredential not found in window object");
        setAuthMethod('traditional');
      }
    };
  
    checkPasskeySupport();
  }, []);

  console.log("Current auth state:", {
    authMode,
    authMethod,
    isPasskeyAvailable
  });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md">
        <div className="bg-white shadow-xl rounded-xl p-8">
          {/* Logo and Title */}
          <div className="text-center mb-8">
            <img 
              src="/sting-logo.png" 
              alt="STING Logo" 
              className="w-32 h-32 mx-auto mb-4"
            />
            <h2 className="text-2xl font-bold text-gray-900">
              {authMode === 'login' ? 'Welcome Back' : 'Create Account'}
            </h2>
            <p className="text-gray-600 mt-2">
              {authMode === 'login' 
                ? 'Sign in to continue to STING' 
                : 'Join STING today'}
            </p>
          </div>

          {/* Debug Info */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mb-4 p-2 bg-gray-100 rounded text-xs">
              <pre>
                {JSON.stringify({
                  authMode,
                  authMethod,
                  isPasskeyAvailable,
                  hasPasswordless: !!Passwordless,
                  passwordlessMethods: Object.keys(Passwordless || {})
                }, null, 2)}
              </pre>
            </div>
          )}

          {/* Auth Method Selection */}
          {isPasskeyAvailable && (
            <div className="flex gap-4 mb-6">
              <button
                onClick={() => setAuthMethod('passkey')}
                className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border 
                          transition-colors ${
                            authMethod === 'passkey'
                              ? 'bg-yellow-400 border-yellow-500 text-gray-900'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
              >
                <Fingerprint className="w-5 h-5" />
                Passkey
              </button>
              <button
                onClick={() => setAuthMethod('traditional')}
                className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border 
                          transition-colors ${
                            authMethod === 'traditional'
                              ? 'bg-yellow-400 border-yellow-500 text-gray-900'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
              >
                <Mail className="w-5 h-5" />
                Email
              </button>
            </div>
          )}

          {/* Auth Components */}
          {authMethod === 'passkey' && isPasskeyAvailable ? (
            <HybridAuth 
              onSuccess={() => {
                console.log("HybridAuth success");
                navigate('/dashboard');
              }}
              passkeysEnabled={isPasskeyAvailable}
            />
          ) : (
            <HybridAuth 
              onSuccess={() => {
                console.log("Traditional auth success");
                navigate('/dashboard');
              }}
              passkeysEnabled={false}
            />
          )}

          {/* Mode Switch */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              {authMode === 'login' ? (
                <>
                  Don't have an account?{' '}
                  <button
                    onClick={() => setAuthMode('signup')}
                    className="text-yellow-600 hover:text-yellow-700 font-medium"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    onClick={() => setAuthMode('login')}
                    className="text-yellow-600 hover:text-yellow-700 font-medium"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthContainer;