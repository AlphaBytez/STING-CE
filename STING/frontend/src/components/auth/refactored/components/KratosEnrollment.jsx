/**
 * Kratos-Native Enrollment Component
 * 
 * Uses Kratos settings flows for WebAuthn and TOTP registration
 * Replaces custom API enrollment after migration to passwordless: false
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, CheckCircle, Key, Fingerprint, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthProvider';
import { useKratosSettings } from '../hooks/useKratosSettings';

const KratosEnrollment = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const {
    userEmail,
    isLoading,
    error,
    successMessage,
    clearMessages
  } = useAuth();
  
  const {
    isLoading: settingsLoading,
    registerWebAuthn,
    registerTOTP,
    verifyTOTPCode,
    getCurrentSettings
  } = useKratosSettings();
  
  // Component state
  const [step, setStep] = useState('loading'); // loading, totp, totp_verify, passkey, complete
  const [userRole, setUserRole] = useState('user');
  const [currentSettings, setCurrentSettings] = useState({});
  const [totpData, setTotpData] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [localError, setLocalError] = useState('');
  const [localSuccess, setLocalSuccess] = useState('');
  
  const isAdmin = userRole === 'admin';

  // Initialize component and check current state
  useEffect(() => {
    const initialize = async () => {
      try {
        console.log('🔧 Initializing Kratos enrollment...');
        
        // Check authentication and get current settings
        const sessionResponse = await fetch('/api/auth/me', {
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });
        
        if (!sessionResponse.ok) {
          console.log('❌ No valid session, redirecting to login');
          navigate('/login');
          return;
        }
        
        const session = await sessionResponse.json();
        const email = session?.identity?.traits?.email || 'Unknown';
        const role = session?.identity?.traits?.role || 'user';
        
        console.log('✅ Session valid:', email, 'Role:', role);
        setUserRole(role);
        
        // Get current configured methods
        const settings = await getCurrentSettings();
        if (settings.success) {
          setCurrentSettings(settings.credentials);
          console.log('🔧 Current settings:', settings.credentials);
          
          // Determine starting step
          if (settings.credentials.totp && settings.credentials.webauthn) {
            console.log('🔧 User has complete setup, redirecting to dashboard');
            navigate('/dashboard');
            return;
          } else if (settings.credentials.totp) {
            console.log('🔧 TOTP configured, starting with passkey setup');
            setStep('passkey');
          } else {
            console.log('🔧 Starting with TOTP setup');
            setStep('totp');
          }
        } else {
          console.warn('🔧 Could not get settings, starting with TOTP');
          setStep('totp');
        }
      } catch (error) {
        console.error('🔧 Initialization error:', error);
        setLocalError('Failed to initialize enrollment');
        setStep('totp'); // Default fallback
      }
    };
    
    initialize();
  }, [navigate, getCurrentSettings]);

  // Handle TOTP setup
  const handleTOTPSetup = async () => {
    clearMessages();
    setLocalError('');
    
    try {
      console.log('🔧 Starting TOTP setup...');
      const result = await registerTOTP();
      
      if (result.success) {
        if (result.alreadyConfigured) {
          setLocalSuccess('TOTP already configured! Proceeding to passkey setup...');
          setTimeout(() => setStep('passkey'), 2000);
        } else if (result.totpData) {
          console.log('🔧 TOTP data received, showing QR code');
          setTotpData(result.totpData);
          setStep('totp_verify');
        }
      } else {
        setLocalError(`TOTP setup failed: ${result.error}`);
      }
    } catch (error) {
      console.error('🔧 TOTP setup error:', error);
      setLocalError(`TOTP setup failed: ${error.message}`);
    }
  };

  // Handle TOTP verification
  const handleTOTPVerification = async (e) => {
    e.preventDefault();
    
    if (!totpCode || totpCode.length !== 6) {
      setLocalError('Please enter a 6-digit code');
      return;
    }
    
    clearMessages();
    setLocalError('');
    
    try {
      console.log('🔧 Verifying TOTP code...');
      const result = await verifyTOTPCode(totpData.flow, totpCode);
      
      if (result.success) {
        setLocalSuccess('TOTP configured successfully! Proceeding to passkey setup...');
        setCurrentSettings(prev => ({ ...prev, totp: true }));
        setTimeout(() => setStep('passkey'), 2000);
      } else {
        setLocalError(`TOTP verification failed: ${result.error}`);
      }
    } catch (error) {
      console.error('🔧 TOTP verification error:', error);
      setLocalError(`TOTP verification failed: ${error.message}`);
    }
  };

  // Handle WebAuthn setup
  const handleWebAuthnSetup = async () => {
    clearMessages();
    setLocalError('');
    
    try {
      console.log('🔧 Starting WebAuthn setup...');
      const result = await registerWebAuthn();
      
      if (result.success) {
        setLocalSuccess('Passkey registered successfully!');
        setCurrentSettings(prev => ({ ...prev, webauthn: true }));
        setTimeout(() => setStep('complete'), 2000);
      } else {
        setLocalError(`Passkey setup failed: ${result.error}`);
      }
    } catch (error) {
      console.error('🔧 WebAuthn setup error:', error);
      setLocalError(`Passkey setup failed: ${error.message}`);
    }
  };

  // Complete enrollment and redirect
  const completeEnrollment = () => {
    console.log('🔧 Enrollment complete, redirecting to dashboard');
    navigate('/dashboard');
  };

  // Show loading state
  if (isLoading || settingsLoading || step === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-400"></div>
          <p className="text-gray-400 mt-4">Loading enrollment...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Shield className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isAdmin ? 'Admin Security Setup' : 'Security Setup Required'}
          </h1>
          <p className="text-gray-300 mb-2">
            Welcome, <span className="text-blue-400">{userEmail}</span>
          </p>
          <p className="text-gray-400">
            {isAdmin 
              ? 'Admin accounts require enhanced security with Kratos native authentication.'
              : 'Set up two-factor authentication using Kratos native flows.'
            }
          </p>
        </div>

        {/* Progress indicator */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${
              step === 'totp' || step === 'totp_verify' ? 'text-blue-400' : 
              step === 'passkey' || step === 'complete' ? 'text-green-400' : 'text-gray-400'
            }`}>
              <Key className="w-5 h-5" />
              <span className="font-medium">TOTP Setup</span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500" />
            <div className={`flex items-center space-x-2 ${
              step === 'passkey' ? 'text-blue-400' : 
              step === 'complete' ? 'text-green-400' : 'text-gray-400'
            }`}>
              <Fingerprint className="w-5 h-5" />
              <span className="font-medium">Passkey Setup</span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500" />
            <div className={`flex items-center space-x-2 ${
              step === 'complete' ? 'text-green-400' : 'text-gray-400'
            }`}>
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Complete</span>
            </div>
          </div>
        </div>

        {/* Error/Success Messages */}
        {(error || localError) && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error || localError}
          </div>
        )}

        {(successMessage || localSuccess) && (
          <div className="bg-green-500/20 border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6 flex items-center">
            <CheckCircle className="w-5 h-5 mr-2" />
            {successMessage || localSuccess}
          </div>
        )}

        {/* TOTP Setup Step */}
        {step === 'totp' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Step 1: Authenticator App Setup</h2>
            
            {isAdmin && (
              <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-red-300 font-medium">Admin Account Requirement</p>
                    <p className="text-gray-400 text-sm mt-1">
                      Admin accounts must complete both TOTP and Passkey setup for dashboard access.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <p className="text-gray-300">
                Set up an authenticator app (Google Authenticator, Authy, 1Password) using Kratos native TOTP.
              </p>
              
              <button
                onClick={handleTOTPSetup}
                disabled={settingsLoading}
                className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
              >
                {settingsLoading ? 'Setting up...' : 'Set Up Authenticator App'}
              </button>
            </div>
          </div>
        )}

        {/* TOTP Verification Step */}
        {step === 'totp_verify' && totpData && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Verify Authenticator App</h2>
            
            <div className="space-y-6">
              {/* QR Code */}
              {totpData.qr_code && (
                <div className="text-center">
                  <img 
                    src={totpData.qr_code} 
                    alt="TOTP QR Code"
                    className="mx-auto bg-white p-4 rounded-lg"
                  />
                  <p className="text-gray-400 text-sm mt-2">
                    Scan this QR code with your authenticator app
                  </p>
                </div>
              )}

              {/* Secret key backup */}
              {totpData.secret && (
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-gray-300 text-sm mb-2">Manual entry key:</p>
                  <code className="text-blue-300 break-all">{totpData.secret}</code>
                </div>
              )}

              {/* Verification form */}
              <form onSubmit={handleTOTPVerification} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Enter verification code
                  </label>
                  <input
                    type="text"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white text-center text-2xl tracking-widest"
                    placeholder="000000"
                    maxLength="6"
                    required
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={settingsLoading || totpCode.length !== 6}
                  className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
                >
                  {settingsLoading ? 'Verifying...' : 'Verify & Continue'}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Passkey Setup Step */}
        {step === 'passkey' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Step 2: Passkey Setup</h2>
            
            {currentSettings.totp && (
              <div className="bg-green-500/20 border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-4 flex items-center">
                <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                <div>
                  <p className="font-medium">TOTP Authentication Configured ✓</p>
                  <p className="text-sm mt-1">Now set up a passkey using Kratos WebAuthn.</p>
                </div>
              </div>
            )}

            <div className="space-y-6">
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                <p className="text-blue-200 text-sm">
                  <strong>Kratos Passkeys</strong> use your device's built-in security (fingerprint, face recognition, PIN) 
                  for secure authentication as a second factor.
                </p>
              </div>

              <div className="text-center space-y-4">
                <Fingerprint className="w-16 h-16 text-blue-400 mx-auto" />
                <p className="text-gray-300">
                  Your device will prompt you to use biometric authentication or PIN.
                </p>
                
                <button
                  onClick={handleWebAuthnSetup}
                  disabled={settingsLoading}
                  className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                >
                  {settingsLoading ? 'Setting up...' : 'Set Up Passkey'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="bg-gray-800 rounded-lg p-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-4">Kratos Security Setup Complete!</h2>
            
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6">
              <p className="text-green-200">
                Your account is now secured with Kratos native two-factor authentication. 
                You can access all features with proper AAL2 step-up authentication.
              </p>
            </div>

            <button
              onClick={completeEnrollment}
              className="bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-8 rounded-lg transition duration-200"
            >
              Access Dashboard
            </button>
          </div>
        )}

        {/* Help Section */}
        <div className="mt-8 text-center">
          <p className="text-gray-400 text-sm">
            Using Kratos native authentication flows. Having trouble?{' '}
            <a 
              href="/settings/security" 
              className="text-blue-400 hover:text-blue-300 underline"
            >
              Advanced security settings
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default KratosEnrollment;