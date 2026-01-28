import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { getKratosUrl } from '../../utils/kratosConfig';
import { useKratos } from '../../auth/KratosProvider';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import '../../theme/sting-glass-theme.css';

const UserEnrollment = () => {
  const navigate = useNavigate();
  const { identity, checkSession } = useKratos();
  const { user, isLoading: authLoading } = useUnifiedAuth();
  const [step, setStep] = useState('password'); // 'password', 'passkey', or 'totp'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [settingsFlow, setSettingsFlow] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  
  const kratosUrl = getKratosUrl(true);
  
  // Check if user is admin
  const userRole = identity?.traits?.role;
  const isAdmin = userRole && (
    userRole.toLowerCase() === 'admin' || 
    userRole.toUpperCase() === 'ADMIN'
  );
  const hasTOTP = identity?.credentials?.totp?.config;

  // Debug - ensure component is mounting
  useEffect(() => {
    console.log('[UserEnrollment] Component mounted');
    window.alert('[DEBUG] UserEnrollment component mounted');
  }, []);

  // Initialize settings flow and determine initial step
  useEffect(() => {
    console.log('[UserEnrollment] Auth state:', {
      authLoading,
      user,
      forcePasswordChange: user?.force_password_change,
      identity,
      identityForcePasswordChange: identity?.traits?.force_password_change,
      isAdmin,
      hasTOTP
    });

    // Don't do anything while auth is loading
    if (authLoading) {
      return;
    }

    const initFlow = async () => {
      try {
        setIsInitializing(true);
        
        // Check what step we should start with
        const needsPasswordChange = user?.force_password_change || identity?.traits?.force_password_change;
        
        if (!needsPasswordChange) {
          // For passwordless accounts, prioritize passkey setup first
          setStep('passkey');
        } else {
          // Start with password change (legacy accounts)
          setStep('password');
        }
        
        // Only init settings flow if we need password change
        if (needsPasswordChange) {
          const response = await axios.get(`${kratosUrl}/self-service/settings/browser`, {
            withCredentials: true
          });
          
          // Extract flow ID from redirect URL
          const flowId = new URL(response.request.responseURL).searchParams.get('flow');
          if (flowId) {
            const flowResponse = await axios.get(`${kratosUrl}/self-service/settings/flows?id=${flowId}`, {
              withCredentials: true
            });
            setSettingsFlow(flowResponse.data);
          }
        }
      } catch (err) {
        console.error('Failed to initialize settings flow:', err);
        setError('Failed to initialize enrollment. Please try logging in again.');
      } finally {
        setIsInitializing(false);
      }
    };

    initFlow();
  }, [identity, user, kratosUrl, navigate, authLoading, isAdmin, hasTOTP]);

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (!settingsFlow) return;

    setLoading(true);
    setError('');

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);

    try {
      const response = await axios.post(settingsFlow.ui.action, {
        ...data,
        method: 'password'
      }, {
        withCredentials: true
      });

      if (response.status === 200) {
        // Password changed successfully
        await checkSession(); // Refresh session
        
        // Check if admin needs TOTP setup
        if (isAdmin && !hasTOTP) {
          setStep('totp');
        } else {
          setStep('passkey');
        }
      }
    } catch (err) {
      console.error('Password change error:', err);
      setError(err.response?.data?.ui?.messages?.[0]?.text || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const handleTOTPSetup = () => {
    // Race condition protection
    if (loading) return;
    
    setLoading(true);
    // Navigate to TOTP setup
    navigate('/setup-totp');
  };

  const handleSkipTOTP = () => {
    // Race condition protection
    if (loading) return;
    
    // SECURITY: For admin users, TOTP should NEVER be skippable
    if (isAdmin) {
      setError('TOTP setup is required for administrative accounts. This cannot be skipped.');
      return;
    }
    
    // For non-admin users, allow skip to passkey setup
    setStep('passkey');
  };
  
  // Check if TOTP was completed and move to next step
  const checkTOTPCompletion = async () => {
    try {
      const response = await fetch('/api/auth/totp-status', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.has_totp) {
          console.log('🔐 TOTP setup completed, moving to passkey step');
          setStep('passkey');
          setError('');
        }
      }
    } catch (error) {
      console.error('Error checking TOTP status:', error);
    }
  };
  
  // Poll for TOTP completion when user returns from setup
  useEffect(() => {
    if (step === 'totp') {
      const interval = setInterval(() => {
        checkTOTPCompletion();
      }, 2000); // Check every 2 seconds
      
      return () => clearInterval(interval);
    }
  }, [step]);

  const handlePasskeySetup = () => {
    // Race condition protection
    if (loading) return;
    
    setLoading(true);
    // Navigate to passkey setup in settings
    navigate('/settings', { state: { openPasskey: true } });
  };

  const handleSkipPasskey = () => {
    // Race condition protection
    if (loading) return;
    
    // For admin users, offer TOTP backup setup
    if (isAdmin && !hasTOTP) {
      setStep('totp');
      return;
    }
    
    setLoading(true);
    // Go to dashboard
    navigate('/dashboard');
  };
  
  // Check if passkey was added and offer next step
  const checkPasskeyCompletion = async () => {
    try {
      // Check if user now has passkey
      await checkSession(); // Refresh identity
      
      // If admin without TOTP, offer backup setup
      if (isAdmin && !hasTOTP) {
        console.log('🔐 Admin completed passkey, offering TOTP backup');
        setStep('totp');
      } else {
        // Non-admin or admin with TOTP can go to dashboard
        navigate('/dashboard');
      }
    } catch (error) {
      console.error('Error checking passkey completion:', error);
    }
  };
  
  // Poll for passkey completion when user returns from setup
  useEffect(() => {
    if (step === 'passkey') {
      const interval = setInterval(() => {
        checkPasskeyCompletion();
      }, 3000); // Check every 3 seconds
      
      return () => clearInterval(interval);
    }
  }, [step, isAdmin, hasTOTP]);

  if (step === 'password') {
    // Only show password step if we have a settings flow
    if (!settingsFlow) {
      // If no settings flow but we're on password step, skip to next step
      if (isAdmin && !hasTOTP) {
        setStep('totp');
      } else {
        setStep('passkey');
      }
      return null;
    }
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold">Change Your Password</h2>
            <p className="text-gray-400 mt-2">Please set a new password to continue</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handlePasswordSubmit}>
            {/* CSRF Token */}
            {settingsFlow.ui.nodes
              .filter(node => node.attributes.name === 'csrf_token')
              .map(node => (
                <input
                  key={node.attributes.name}
                  type="hidden"
                  name={node.attributes.name}
                  value={node.attributes.value}
                />
              ))
            }

            {/* Password fields */}
            {settingsFlow.ui.nodes
              .filter(node => node.group === 'password' && node.attributes.type !== 'submit')
              .map(node => (
                <div key={node.attributes.name} className="mb-4">
                  <label className="block text-gray-300 mb-2">
                    {node.meta?.label?.text || node.attributes.name}
                  </label>
                  <input
                    name={node.attributes.name}
                    type={node.attributes.type}
                    required={node.attributes.required}
                    className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                    autoComplete={node.attributes.autocomplete}
                  />
                </div>
              ))
            }

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Changing Password...' : 'Change Password'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (step === 'totp') {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-red-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-red-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold">Setup Backup Authentication</h2>
            <p className="text-gray-400 mt-2">TOTP backup for admin account recovery</p>
          </div>

          <div className="mb-6 p-4 bg-blue-900/20 border border-blue-600 rounded-lg">
            <p className="text-blue-300 text-sm">
              <strong>🔄 Backup & Recovery:</strong> TOTP provides a reliable backup method if your primary passkey is unavailable. Essential for admin account recovery scenarios.
            </p>
          </div>
          
          {/* Error display */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg">
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <button
              onClick={handleTOTPSetup}
              disabled={loading}
              className={`w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-500 font-semibold transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? 'Redirecting...' : 'Setup TOTP Backup'}
            </button>

            {/* Only show skip button for non-admin users */}
            {!isAdmin && (
              <button
                onClick={handleSkipTOTP}
                disabled={loading}
                className="w-full py-2 px-4 text-gray-400 hover:text-gray-300 disabled:opacity-50"
              >
                Skip to Passkey Setup
              </button>
            )}
            
            {/* For admins, show info instead of skip button */}
            {isAdmin && (
              <div className="text-center">
                <p className="text-sm text-gray-400">
                  🔄 TOTP backup is strongly recommended for admin account recovery
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Provides alternative access if passkey device is unavailable
                </p>
                <button
                  onClick={() => navigate('/dashboard')}
                  disabled={loading}
                  className="mt-3 text-sm text-blue-400 hover:text-blue-300 underline disabled:opacity-50"
                >
                  {loading ? 'Redirecting...' : 'Skip and Continue to Dashboard'}
                </button>
              </div>
            )}
          </div>

          <div className="mt-6 text-sm text-gray-400 text-center">
            <p>📱 Use authenticator apps: Google Authenticator, Authy, or 1Password</p>
            <p className="mt-1">🔄 Serves as backup when passkey is unavailable</p>
            <p className="mt-1">⚡ Quick recovery for device loss scenarios</p>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'passkey') {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold">Setup Primary Authentication</h2>
            <p className="text-gray-400 mt-2">Secure your account with phishing-resistant passkeys</p>
          </div>
          
          <div className="mb-6 p-4 bg-yellow-900/20 border border-yellow-600 rounded-lg">
            <p className="text-yellow-300 text-sm">
              <strong>🛡️ Recommended Primary Method:</strong> Passkeys provide the strongest protection against phishing and credential theft. Works with Touch ID, Face ID, Windows Hello, or hardware keys like YubiKey.
            </p>
          </div>

          <div className="space-y-4">
            <button
              onClick={handlePasskeySetup}
              disabled={loading}
              className={`w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 font-semibold transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? 'Redirecting...' : 'Setup Passkey (Recommended)'}
            </button>

            <button
              onClick={handleSkipPasskey}
              disabled={loading}
              className="w-full py-2 px-4 text-gray-400 hover:text-gray-300 disabled:opacity-50"
            >
              {loading ? 'Redirecting...' : (isAdmin ? 'Skip to Backup Setup' : 'Skip for now')}
            </button>
          </div>

          <div className="mt-6 text-sm text-gray-400 text-center">
            <p>🔑 Works with Touch ID, Face ID, Windows Hello, or YubiKey</p>
            <p className="mt-1">📱 Same passkey works across all your devices</p>
            {isAdmin && (
              <p className="mt-2 text-yellow-400 text-xs">
                ⚠️ Admin accounts: TOTP backup will be offered after passkey setup
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Loading state - show while auth is loading or initializing
  if (authLoading || isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
      </div>
    );
  }

  // Error state
  if (error && !settingsFlow) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="max-w-md p-8 bg-red-900/20 border border-red-800 rounded-lg">
          <h2 className="text-xl font-semibold text-red-400 mb-4">Enrollment Error</h2>
          <p className="text-gray-300 mb-6">{error}</p>
          <button
            onClick={() => navigate('/login')}
            className="w-full py-2 px-4 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  // If no settings flow and no error, show loading
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
    </div>
  );
};

export default UserEnrollment;