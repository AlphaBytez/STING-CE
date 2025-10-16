// HybridAuth.jsx
import React, { useState } from 'react';
import { startAuthentication } from '@simplewebauthn/browser';
import { SignInUp } from 'supertokens-auth-react/recipe/passwordless/prebuiltui';
import { useSessionContext } from 'supertokens-auth-react/recipe/session';
import { useNavigate } from 'react-router-dom';

const HybridAuth = ({ onSuccess, passkeysEnabled }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const session = useSessionContext();

  const handleAuthSuccess = async (response) => {
    console.log('Auth success response:', response);

    if (response?.user?.email) {
      await onSuccess(response.user.email);

      return false;
    }
    return true;
  };

  const tryPasskeyLogin = async (email) => {
    try {
      const response = await fetch('https://localhost:5050/api/auth/passkey/authenticate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      });
      
      const options = await response.json();
      
      const credential = await startAuthentication(options);
      
      const verifyResponse = await fetch('https://localhost:5050/api/auth/passkey/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credential)
      });
      
      return verifyResponse.ok;
    } catch (error) {
      console.error('Passkey login failed:', error);
      return false;
    }
  };

  return (
    <div className="w-full">
      {error && (
        <div className="mb-4 p-2 bg-yellow-900 border border-yellow-700 text-yellow-300 rounded">
          {error}
        </div>
      )}

      <SignInUp
        onSuccess={handleAuthSuccess}
        override={{
          functions: (originalImplementation) => ({
            ...originalImplementation,
            submitNewPasswordlessFlow: async function(input) {
              console.log('Submitting passwordless flow:', input);
              if (passkeysEnabled) {
                const passkeySuccess = await tryPasskeyLogin(input.email);
                if (passkeySuccess) {
                  return { status: 'OK' };
                }
              }
              return originalImplementation.submitNewPasswordlessFlow(input);
            }
          }),
          components: {
            PasswordlessLinkSent: ({ email }) => (
              <div className="text-center p-4">
                <p>Code sent to {email}</p>
                <p className="text-sm text-gray-600 mt-2">
                  After verification, you'll be prompted to set up passkey authentication.
                </p>
              </div>
            )
          }
        }}
      />
    </div>
  );
};

export default HybridAuth;