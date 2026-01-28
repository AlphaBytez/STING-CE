import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Key, Fingerprint, Shield, Check, ArrowRight, AlertCircle } from 'lucide-react';

/**
 * New Admin Setup Flow: Email → Email Code → TOTP → Passkey
 * This replaces the old password-based admin setup with a truly passwordless flow
 */
const AdminSetupFlow = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Email, 2: Email Code, 3: TOTP, 4: Passkey
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form data
  const [email, setEmail] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [totpQrCode, setTotpQrCode] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [adminData, setAdminData] = useState(null);

  // Auto-detect initial setup status
  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    try {
      const response = await fetch('/api/auth/admin-setup-status', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.setup_complete) {
          // Admin is already set up, redirect to login
          navigate('/login');
        }
        // Otherwise stay on setup flow
      }
    } catch (error) {
      console.error('Failed to check setup status:', error);
    }
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email || loading) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/admin-setup-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ email })
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(`Verification code sent to ${email}`);
        setStep(2);
      } else {
        setError(data.error || 'Failed to send verification code');
      }
    } catch (error) {
      console.error('Email setup error:', error);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailCodeSubmit = async (e) => {
    e.preventDefault();
    if (!emailCode || loading) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/admin-setup-verify-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ email, code: emailCode })
      });

      const data = await response.json();

      if (response.ok) {
        setTotpQrCode(data.totp_qr_code);
        setAdminData(data.admin_data);
        setSuccess('Email verified! Please set up two-factor authentication');
        setStep(3);
      } else {
        setError(data.error || 'Invalid verification code');
      }
    } catch (error) {
      console.error('Email verification error:', error);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = async (e) => {
    e.preventDefault();
    if (!totpCode || loading) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/admin-setup-totp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ email, totp_code: totpCode })
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess('Two-factor authentication configured! Now set up biometric login');
        setStep(4);
      } else {
        setError(data.error || 'Invalid TOTP code');
      }
    } catch (error) {
      console.error('TOTP setup error:', error);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeySetup = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/admin-setup-passkey', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ email })
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess('Admin setup complete! You can now log in with biometrics');
        
        // Redirect to dashboard after a brief delay
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      } else {
        setError(data.error || 'Failed to set up biometric authentication');
      }
    } catch (error) {
      console.error('Passkey setup error:', error);
      
      if (error.name === 'NotSupportedError') {
        setError('Biometric authentication is not supported on this device');
      } else if (error.name === 'SecurityError') {
        setError('Biometric setup was blocked by security policy');
      } else {
        setError('Failed to set up biometric authentication');
      }
    } finally {
      setLoading(false);
    }
  };

  const skipPasskey = async () => {
    setSuccess('Admin setup complete! You can set up biometrics later in settings');
    setTimeout(() => {
      navigate('/dashboard');
    }, 2000);
  };

  const renderStepIndicator = () => (
    <div className="flex justify-center mb-8">
      <div className="flex items-center space-x-8">
        {[
          { num: 1, label: 'Email', icon: Mail, completed: step > 1 },
          { num: 2, label: 'Verify', icon: Key, completed: step > 2 },
          { num: 3, label: '2FA', icon: Shield, completed: step > 3 },
          { num: 4, label: 'Biometrics', icon: Fingerprint, completed: step > 4 }
        ].map((stepInfo, index) => (
          <React.Fragment key={stepInfo.num}>
            <div className="flex flex-col items-center">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                stepInfo.completed 
                  ? 'bg-green-600 text-white' 
                  : step === stepInfo.num
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400'
              }`}>
                {stepInfo.completed ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <stepInfo.icon className="w-5 h-5" />
                )}
              </div>
              <span className={`text-sm mt-2 ${
                step === stepInfo.num ? 'text-blue-400' : 'text-gray-500'
              }`}>
                {stepInfo.label}
              </span>
            </div>
            {index < 3 && (
              <ArrowRight className={`w-4 h-4 ${
                stepInfo.completed ? 'text-green-600' : 'text-gray-600'
              }`} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]" />
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-green-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}} />
      </div>

      {/* Main Content */}
      <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong animate-fade-in-up">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="Hive Logo" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white">Admin Setup</h1>
          <p className="text-gray-400 mt-2">
            Set up your administrator account with passwordless authentication
          </p>
        </div>

        {renderStepIndicator()}

        {/* Error/Success Messages */}
        {error && (
          <div className="mb-6 p-3 bg-red-900/30 border border-red-800 rounded">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}
        
        {success && (
          <div className="mb-6 p-3 bg-green-900/30 border border-green-800 rounded">
            <div className="flex items-center space-x-2">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              <p className="text-green-300 text-sm">{success}</p>
            </div>
          </div>
        )}

        {/* Step 1: Email */}
        {step === 1 && (
          <form onSubmit={handleEmailSubmit} className="space-y-6">
            <div>
              <label className="block text-gray-300 mb-2 font-medium">
                Administrator Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="admin@yourdomain.com"
                required
                autoFocus
              />
              <p className="text-sm text-gray-400 mt-2">
                A verification code will be sent to this email address
              </p>
            </div>
            
            <button
              type="submit"
              disabled={loading || !email}
              className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending Code...' : 'Send Verification Code'}
            </button>
          </form>
        )}

        {/* Step 2: Email Code */}
        {step === 2 && (
          <form onSubmit={handleEmailCodeSubmit} className="space-y-6">
            <div>
              <label className="block text-gray-300 mb-2 font-medium">
                Verification Code
              </label>
              <input
                type="text"
                value={emailCode}
                onChange={(e) => setEmailCode(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white text-center text-xl tracking-widest font-mono transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="000000"
                maxLength="6"
                required
                autoFocus
              />
              <p className="text-sm text-gray-400 mt-2">
                Check your email at <strong className="text-blue-400">{email}</strong>
              </p>
              <p className="text-xs text-gray-500 mt-1">
                💡 For testing, check Mailpit at the configured URL
              </p>
            </div>
            
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 py-3 px-4 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || !emailCode}
                className="flex-1 py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Verifying...' : 'Verify Code'}
              </button>
            </div>
          </form>
        )}

        {/* Step 3: TOTP Setup */}
        {step === 3 && (
          <form onSubmit={handleTotpSubmit} className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-lg font-semibold text-white mb-3">
                Set Up Two-Factor Authentication
              </h3>
              <p className="text-sm text-gray-400 mb-4">
                Scan this QR code with your authenticator app
              </p>
              
              {totpQrCode && (
                <div className="bg-white p-4 rounded-lg inline-block">
                  <div dangerouslySetInnerHTML={{ __html: totpQrCode }} />
                </div>
              )}
              
              <p className="text-xs text-gray-500 mt-3">
                Use Google Authenticator, Authy, or similar apps
              </p>
            </div>

            <div>
              <label className="block text-gray-300 mb-2 font-medium">
                Authentication Code
              </label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white text-center text-xl tracking-widest font-mono transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="000000"
                maxLength="6"
                required
                autoFocus
              />
              <p className="text-sm text-gray-400 mt-2">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>
            
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="flex-1 py-3 px-4 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || !totpCode}
                className="flex-1 py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Verifying...' : 'Verify TOTP'}
              </button>
            </div>
          </form>
        )}

        {/* Step 4: Passkey Setup */}
        {step === 4 && (
          <div className="space-y-6 text-center">
            <div>
              <h3 className="text-lg font-semibold text-white mb-3">
                Set Up Biometric Authentication
              </h3>
              <p className="text-sm text-gray-400 mb-6">
                Complete your setup with fingerprint, face, or hardware key authentication for the most secure and convenient login experience.
              </p>
              
              <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-center space-x-2 text-blue-300 mb-2">
                  <Fingerprint className="w-5 h-5" />
                  <span className="font-medium">Recommended</span>
                </div>
                <p className="text-sm text-blue-200">
                  Biometric authentication provides the highest level of security while offering the fastest login experience.
                </p>
              </div>
            </div>
            
            <div className="flex flex-col space-y-3">
              <button
                onClick={handlePasskeySetup}
                disabled={loading}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                <Fingerprint className="w-5 h-5" />
                <span>{loading ? 'Setting up...' : 'Set Up Biometrics'}</span>
              </button>
              
              <button
                onClick={skipPasskey}
                className="w-full py-2 px-4 text-gray-400 hover:text-gray-300 transition-colors text-sm"
              >
                Skip for now (can be added later in settings)
              </button>
            </div>

            <div className="text-center">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="text-sm text-gray-500 hover:text-gray-400 transition-colors"
              >
                ← Back to TOTP setup
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminSetupFlow;