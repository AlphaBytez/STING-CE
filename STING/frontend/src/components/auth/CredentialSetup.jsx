import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';
import TOTPManager from '../settings/TOTPManager';
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';

const CredentialSetup = () => {
  const navigate = useNavigate();
  const { identity } = useKratos();
  const [userEmail, setUserEmail] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Credential status
  const [hasPasskey, setHasPasskey] = useState(false);
  const [hasTOTP, setHasTOTP] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  // Active setup step
  const [activeSetup, setActiveSetup] = useState(null); // null, 'totp', 'passkey'

  // Check credential status
  const checkCredentialStatus = async () => {
    try {
      const response = await axios.get('/api/auth/me', {
        withCredentials: true
      });

      const data = response.data;
      const passkey = data?.has_passkey || false;
      const totp = data?.has_totp || false;
      const userRole = data?.user?.role || 'user';
      const isAdminUser = userRole === 'admin' || userRole === 'super_admin';

      console.log('🔐 CredentialSetup check:', { passkey, totp, userRole, isAdminUser });

      setHasPasskey(passkey);
      setHasTOTP(totp);
      setIsAdmin(isAdminUser);
      setUserEmail(data.user?.email || '');

      // Check if setup is complete
      const setupComplete = isAdminUser
        ? (passkey && totp)  // Admins need both
        : totp;               // Users need at least TOTP

      if (setupComplete) {
        console.log('✅ User has required credentials - redirecting to dashboard');
        setTimeout(() => navigate('/dashboard'), 1000);
        return true;
      }

      setIsLoading(false);
      return false;
    } catch (error) {
      console.error('Failed to check credential status:', error);
      setIsLoading(false);
      setError('Unable to verify credential status. Please try again.');
      return false;
    }
  };

  useEffect(() => {
    checkCredentialStatus();
  }, [navigate]);

  // Handle TOTP setup completion
  const handleTOTPComplete = async () => {
    console.log('✅ TOTP setup completed');
    setHasTOTP(true);
    setActiveSetup(null);
    // Re-check status - might be complete now
    await checkCredentialStatus();
  };

  // Handle Passkey setup completion
  const handlePasskeyComplete = async () => {
    console.log('✅ Passkey setup completed');
    setHasPasskey(true);
    setActiveSetup(null);
    // Re-check status - might be complete now
    await checkCredentialStatus();
  };

  // Check if all required credentials are set up
  const isSetupComplete = isAdmin ? (hasPasskey && hasTOTP) : hasTOTP;

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

  if (isSetupComplete) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
          <div className="text-center">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-white mb-2">Security Setup Complete!</h2>
            <p className="text-gray-300">Redirecting to dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header Card */}
        <div className="sting-glass-card sting-glass-default sting-elevation-medium p-6 mb-6">
          <div className="text-center mb-4">
            <img src="/sting-logo.png" alt="STING" className="w-16 h-16 mx-auto mb-3" />
            <h1 className="text-2xl font-bold text-white mb-2">
              🔒 Security Setup Required
            </h1>
            <p className="text-gray-300 text-sm">
              {isAdmin
                ? 'As an admin, you need BOTH Passkey and TOTP for maximum security.'
                : 'Please set up your authentication methods to continue.'}
            </p>
            {userEmail && (
              <p className="text-blue-300 text-sm mt-2">Account: {userEmail}</p>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {/* Progress Indicators */}
          <div className="flex justify-center gap-4 mb-4">
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${hasTOTP ? 'bg-green-500/20 border border-green-500/50' : 'bg-gray-700/50 border border-gray-600'}`}>
              <span className="text-xl">{hasTOTP ? '✅' : '📱'}</span>
              <span className={hasTOTP ? 'text-green-300' : 'text-gray-400'}>TOTP</span>
            </div>
            {isAdmin && (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${hasPasskey ? 'bg-green-500/20 border border-green-500/50' : 'bg-gray-700/50 border border-gray-600'}`}>
                <span className="text-xl">{hasPasskey ? '✅' : '🔑'}</span>
                <span className={hasPasskey ? 'text-green-300' : 'text-gray-400'}>Passkey</span>
              </div>
            )}
          </div>
        </div>

        {/* Active Setup Panel */}
        {activeSetup === 'totp' && (
          <div className="sting-glass-card sting-glass-default sting-elevation-medium p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-white">📱 TOTP Setup</h2>
              <button
                onClick={() => setActiveSetup(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕ Close
              </button>
            </div>
            <TOTPManager
              isEnrollmentMode={true}
              onSetupComplete={handleTOTPComplete}
            />
          </div>
        )}

        {activeSetup === 'passkey' && (
          <div className="sting-glass-card sting-glass-default sting-elevation-medium p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-white">🔑 Passkey Setup</h2>
              <button
                onClick={() => setActiveSetup(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕ Close
              </button>
            </div>
            <PasskeyManagerDirect
              isEnrollmentMode={true}
              onSetupComplete={handlePasskeyComplete}
            />
          </div>
        )}

        {/* Method Selection (when no active setup) */}
        {!activeSetup && (
          <div className="sting-glass-card sting-glass-default sting-elevation-medium p-6">
            {/* Certificate Download Banner */}
            {isAdmin && !hasPasskey && (
              <div className="bg-purple-500/20 border border-purple-500/50 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">🔐</span>
                  <div className="flex-1">
                    <div className="text-purple-200 font-medium text-sm mb-1">Install Certificate for Passkey Support</div>
                    <p className="text-purple-300 text-xs mb-3">
                      WebAuthn/Passkeys require a trusted certificate. Download the installer for your OS:
                    </p>
                    <div className="flex flex-wrap gap-2 mb-3">
                      <a
                        href="/api/config/cert/installer/mac"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs font-medium"
                        download="install-ca-mac.sh"
                      >
                        🍎 macOS
                      </a>
                      <a
                        href="/api/config/cert/installer/windows"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs font-medium"
                        download="install-ca-windows.ps1"
                      >
                        🪟 Windows
                      </a>
                      <a
                        href="/api/config/cert/installer/linux"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs font-medium"
                        download="install-ca-linux.sh"
                      >
                        🐧 Linux
                      </a>
                    </div>
                    <details className="text-xs">
                      <summary className="text-purple-300 cursor-pointer hover:text-purple-200">How to install</summary>
                      <div className="mt-2 pl-2 border-l-2 border-purple-500/30 text-purple-400 space-y-1">
                        <p><strong>macOS/Linux:</strong> Open Terminal, cd to downloads, run: <code className="bg-black/30 px-1 rounded">chmod +x install-ca-*.sh && sudo ./install-ca-*.sh</code></p>
                        <p><strong>Windows:</strong> Right-click the .ps1 file → "Run with PowerShell" (as Admin)</p>
                        <p className="text-purple-500">After installing, restart your browser.</p>
                      </div>
                    </details>
                  </div>
                </div>
              </div>
            )}

            <h3 className="text-lg font-semibold text-white mb-4">Select a method to set up:</h3>

            <div className="space-y-3">
              {/* TOTP Setup Button */}
              {!hasTOTP && (
                <button
                  onClick={() => setActiveSetup('totp')}
                  className="w-full p-4 bg-green-500/10 border border-green-500/50 rounded-lg hover:bg-green-500/20 transition-colors group"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">📱</div>
                    <div className="text-left flex-1">
                      <div className="font-semibold text-white group-hover:text-green-200">
                        Set Up TOTP (Authenticator App)
                      </div>
                      <div className="text-sm text-gray-400">
                        Google Authenticator, Authy, 1Password, etc.
                      </div>
                    </div>
                    <div className="text-green-400 font-medium">Setup →</div>
                  </div>
                </button>
              )}

              {/* Passkey Setup Button (for admins or if TOTP is done) */}
              {isAdmin && !hasPasskey && (
                <button
                  onClick={() => setActiveSetup('passkey')}
                  className="w-full p-4 bg-blue-500/10 border border-blue-500/50 rounded-lg hover:bg-blue-500/20 transition-colors group"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">🔑</div>
                    <div className="text-left flex-1">
                      <div className="font-semibold text-white group-hover:text-blue-200">
                        Set Up Passkey (Biometric)
                      </div>
                      <div className="text-sm text-gray-400">
                        Face ID, Touch ID, Windows Hello, or security key
                      </div>
                    </div>
                    <div className="text-blue-400 font-medium">Setup →</div>
                  </div>
                </button>
              )}

              {/* Completed items shown as disabled */}
              {hasTOTP && (
                <div className="w-full p-4 bg-green-500/10 border border-green-500/50 rounded-lg opacity-75">
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">✅</div>
                    <div className="text-left flex-1">
                      <div className="font-semibold text-green-300">TOTP Configured</div>
                      <div className="text-sm text-green-400">Authenticator app is set up</div>
                    </div>
                  </div>
                </div>
              )}

              {isAdmin && hasPasskey && (
                <div className="w-full p-4 bg-green-500/10 border border-green-500/50 rounded-lg opacity-75">
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">✅</div>
                    <div className="text-left flex-1">
                      <div className="font-semibold text-green-300">Passkey Configured</div>
                      <div className="text-sm text-green-400">Biometric authentication is set up</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Info Footer */}
            <div className="mt-6 pt-4 border-t border-gray-700">
              <div className="text-xs text-gray-500 text-center space-y-1">
                {isAdmin ? (
                  <>
                    <p>🛡️ Admins require BOTH methods for maximum security</p>
                    <p>After setup, you only need ONE method for daily login</p>
                  </>
                ) : (
                  <p>🛡️ Set up TOTP to secure your account</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CredentialSetup;
