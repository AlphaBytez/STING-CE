import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';

const GracefulAAL2StepUp = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedMethod, setSelectedMethod] = useState('');

  // Check if user came back from passkey issues
  const passkeyTimeout = searchParams.get('passkey_timeout') === 'true';
  const passkeyFailed = searchParams.get('passkey_failed') === 'true';
  
  // Check if this is post-login security upgrade (newuser flow)
  const isNewUserFlow = searchParams.get('newuser') === 'true';
  const { session } = useKratos();
  
  // Check if user already has AAL2 and show success instead of redirecting
  const [hasAAL2, setHasAAL2] = useState(false);
  
  useEffect(() => {
    const userAAL = session?.authenticator_assurance_level;
    if (userAAL === 'aal2') {
      console.log('🎉 User already has AAL2 - showing success state');
      setHasAAL2(true);
      setSuccessMessage('✅ Enhanced security verified! You now have full access.');
    } else {
      setHasAAL2(false);
    }
  }, [session]);
  const [userEmail, setUserEmail] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Get user email from session/API
  useEffect(() => {
    const fetchUserEmail = async () => {
      try {
        const response = await fetch('/api/auth/me', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          console.log('🔍 AAL2 Step-up - Session data received:', data);
          setUserEmail(data.user?.email || 'user@example.com');
        } else {
          console.log('🔍 AAL2 Step-up - Session check failed:', response.status, response.statusText);
        }
      } catch (error) {
        console.log('Could not fetch user email:', error);
        setUserEmail('user@example.com'); // Fallback
      }
    };
    
    fetchUserEmail();
  }, []);

  // Timer removed - during AAL2 requirement, user must complete authentication

  const handleMethodSelection = (method) => {
    setSelectedMethod(method);
    setError('');
    setSuccessMessage('');

    // Get return URL - check sessionStorage first (set by SecuritySettings), then URL params, then default
    const storedReturnTo = sessionStorage.getItem('aal2_return_to');
    const urlReturnTo = new URLSearchParams(window.location.search).get('return_to');
    const currentReturnTo = storedReturnTo || urlReturnTo || '/dashboard';

    if (method === 'totp') {
      // Navigate to dedicated AAL2 TOTP verification page
      navigate(`/verify-totp?return_to=${encodeURIComponent(currentReturnTo)}`);
    } else if (method === 'passkey') {
      // Navigate to dedicated AAL2 passkey verification page
      navigate(`/verify-passkey?return_to=${encodeURIComponent(currentReturnTo)}`);
    }
  };

  const handleSkipForNow = () => {
    // Get return URL - check sessionStorage first, then URL params, then default
    const storedReturnTo = sessionStorage.getItem('aal2_return_to');
    const urlReturnTo = new URLSearchParams(window.location.search).get('return_to');
    const currentReturnTo = storedReturnTo || urlReturnTo || '/dashboard';

    setSuccessMessage('Dashboard access granted. Enhanced security can be configured later.');

    // Clean up sessionStorage
    sessionStorage.removeItem('aal2_return_to');
    sessionStorage.removeItem('aal2_return_reason');

    setTimeout(() => {
      navigate(currentReturnTo);
    }, 1500);
  };

  const handleSetupNow = () => {
    navigate('/dashboard/settings?tab=security&setup=true');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isNewUserFlow ? 'Enhance Your Security' : 'Enhanced Security Available'}
          </h1>
          <p className="text-gray-300">
            {isNewUserFlow 
              ? 'Welcome! Let\'s set up enhanced security for your admin account. This protects sensitive data and admin functions.'
              : 'Please re-authenicate to keep your account secure. Choose a method below to proceed.'}
          </p>
        </div>

        {/* Passkey Issues Warning */}
        {(passkeyTimeout || passkeyFailed) && (
          <div className="sting-glass-subtle border border-yellow-500/50 text-yellow-200 px-4 py-3 rounded-lg mb-6">
            <div className="flex items-center space-x-2">
              <span>{passkeyTimeout ? '⏰' : '🚫'}</span>
              <div>
                <div className="font-semibold">
                  {passkeyTimeout ? 'Passkey authentication timed out' : 'Passkey authentication was cancelled or failed'}
                </div>
                <div className="text-sm text-yellow-300">
                  Try TOTP authentication instead - it gives you more control over the timing
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="sting-glass-subtle border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6">
            {successMessage}
          </div>
        )}

        {/* Method Selection */}
        <div className="space-y-4 mb-6">
          <button
            onClick={() => handleMethodSelection('passkey')}
            className="w-full p-4 sting-glass-subtle border border-blue-500/50 rounded-lg hover:border-blue-400/75 transition-colors group"
          >
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🔑</div>
              <div className="text-left">
                <div className="font-semibold text-white group-hover:text-blue-200">
                  Authenticate with Passkey
                </div>
                <div className="text-sm text-gray-400">
                  Quick and secure biometric authentication
                </div>
              </div>
            </div>
          </button>

          <button
            onClick={() => handleMethodSelection('totp')}
            className="w-full p-4 sting-glass-subtle border border-green-500/50 rounded-lg hover:border-green-400/75 transition-colors group"
          >
            <div className="flex items-center space-x-3">
              <div className="text-2xl">📱</div>
              <div className="text-left">
                <div className="font-semibold text-white group-hover:text-green-200">
                  Authenticate with TOTP
                </div>
                <div className="text-sm text-gray-400">
                  Use your authenticator app (Google Authenticator, etc.)
                </div>
              </div>
            </div>
          </button>
        </div>

        {/* User Info */}
        {userEmail && (
          <div className="text-center mb-6 text-sm text-gray-400">
            Enhancing security for: <span className="text-blue-300">{userEmail}</span>
          </div>
        )}

        {/* Navigation Options - No auto-skip during AAL2 requirement */}
        <div className="border-t border-gray-700 pt-6 space-y-3">
          <button
            onClick={() => navigate('/dashboard/settings?tab=security&setup=true')}
            className="w-full py-2 px-4 border border-gray-600 hover:border-gray-500 text-gray-300 hover:text-white rounded-lg transition-colors text-sm"
          >
            Go to Settings → Security
          </button>
          
          <button
            onClick={() => navigate(-1)}
            className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg transition-colors text-sm"
          >
            ← Go Back
          </button>
          
          <div className="text-xs text-gray-500 text-center">
            For security, AAL2 authentication is required for admin dashboard access
          </div>
        </div>

        {/* Development Mode Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs text-center">
              🔧 Dev: Graceful AAL2 step-up page
              <br />
              This provides a user-friendly way to handle enhanced security
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default GracefulAAL2StepUp;