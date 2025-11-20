import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';

const CredentialSetup = () => {
  const navigate = useNavigate();
  const { identity } = useKratos();
  const [userEmail, setUserEmail] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [hasCredentials, setHasCredentials] = useState(false);

  // Check if user already has credentials - if so, redirect to dashboard
  useEffect(() => {
    const checkCredentialStatus = async () => {
      try {
        const response = await axios.get('/api/aal2/status', {
          withCredentials: true
        });

        const status = response.data?.status;
        const hasPasskey = status?.passkey_enrolled || false;
        const hasTotp = status?.totp_enrolled || false;

        // STING requires BOTH Passkey AND TOTP for 3FA
        if (hasPasskey && hasTotp) {
          console.log('✅ User has both credentials (3FA complete) - redirecting to dashboard');
          setHasCredentials(true);
          // User has both credentials, redirect to dashboard
          setTimeout(() => {
            navigate('/dashboard');
          }, 1000);
        } else {
          console.log('⚠️ User missing credentials:', {
            hasPasskey,
            hasTotp,
            needsPasskey: !hasPasskey,
            needsTotp: !hasTotp
          });
          setIsLoading(false);
        }
      } catch (error) {
        console.error('Failed to check credential status:', error);
        setIsLoading(false);
        setError('Unable to verify credential status. Please try again.');
      }
    };

    checkCredentialStatus();
  }, [navigate]);

  // Get user email
  useEffect(() => {
    const fetchUserEmail = async () => {
      try {
        const response = await fetch('/api/auth/me', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setUserEmail(data.user?.email || 'user@example.com');
        }
      } catch (error) {
        console.log('Could not fetch user email:', error);
        setUserEmail('user@example.com');
      }
    };

    fetchUserEmail();
  }, []);

  const handleSetupMethod = (method) => {
    // Navigate to security settings with setup flag
    if (method === 'totp') {
      navigate('/dashboard/settings?tab=security&setup=totp&required=true');
    } else if (method === 'passkey') {
      navigate('/dashboard/settings?tab=security&setup=passkey&required=true');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Checking security status...</p>
        </div>
      </div>
    );
  }

  if (hasCredentials) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
          <div className="text-center">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-white mb-2">Security Already Configured</h2>
            <p className="text-gray-300">Redirecting to dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            🔒 3-Factor Security Setup
          </h1>
          <p className="text-gray-300">
            Welcome! STING uses 3-factor authentication (Email + Passkey + TOTP) to ensure you never get locked out while maintaining maximum security.
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Info Banner */}
        <div className="sting-glass-subtle border border-blue-500/50 text-blue-200 px-4 py-3 rounded-lg mb-6">
          <div className="flex items-start space-x-2">
            <span className="text-xl">ℹ️</span>
            <div className="text-sm">
              <div className="font-semibold mb-1">How 3-Factor Authentication Works</div>
              <div className="text-blue-300 space-y-2">
                <p><strong>Setup:</strong> You'll configure BOTH Passkey and TOTP (takes 2-3 minutes)</p>
                <p><strong>Daily Use:</strong> Only verify with ONE method (Passkey OR TOTP)</p>
                <p><strong>Benefit:</strong> Never get locked out - if one method fails, use the other!</p>
              </div>
            </div>
          </div>
        </div>

        {/* Method Selection */}
        <div className="space-y-4 mb-6">
          <button
            onClick={() => handleSetupMethod('passkey')}
            className="w-full p-4 sting-glass-subtle border border-blue-500/50 rounded-lg hover:border-blue-400/75 transition-colors group"
          >
            <div className="flex items-center space-x-3">
              <div className="text-3xl">🔑</div>
              <div className="text-left flex-1">
                <div className="font-semibold text-white group-hover:text-blue-200">
                  Step 1: Set Up Passkey
                </div>
                <div className="text-sm text-gray-400">
                  Face ID, Touch ID, or security key (start here)
                </div>
              </div>
              <div className="text-blue-400 text-sm font-semibold">
                Start →
              </div>
            </div>
          </button>

          <button
            onClick={() => handleSetupMethod('totp')}
            className="w-full p-4 sting-glass-subtle border border-green-500/50 rounded-lg hover:border-green-400/75 transition-colors group"
          >
            <div className="flex items-center space-x-3">
              <div className="text-3xl">📱</div>
              <div className="text-left flex-1">
                <div className="font-semibold text-white group-hover:text-green-200">
                  Or Step 1: Set Up TOTP First
                </div>
                <div className="text-sm text-gray-400">
                  Google Authenticator, Authy (you'll add the other next)
                </div>
              </div>
              <div className="text-green-400 text-sm">
                Start →
              </div>
            </div>
          </button>
        </div>

        {/* User Info */}
        {userEmail && (
          <div className="text-center mb-6 text-sm text-gray-400">
            Setting up 2FA for: <span className="text-blue-300">{userEmail}</span>
          </div>
        )}

        {/* Footer Info */}
        <div className="border-t border-gray-700 pt-6">
          <div className="text-xs text-gray-500 text-center space-y-2">
            <p>🛡️ <strong>Important:</strong> You must set up BOTH methods to access STING</p>
            <p>After setup, you only need ONE method for daily login</p>
            <p>Choose either method to start - you'll add the other one next</p>
          </div>
        </div>

        {/* Development Mode Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs text-center">
              🔧 Dev: Forced credential setup page
              <br />
              New users must set up 2FA before dashboard access
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CredentialSetup;
