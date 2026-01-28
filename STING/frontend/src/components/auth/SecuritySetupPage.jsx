import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Key, Smartphone, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';
import TOTPManager from '../settings/TOTPManager';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import apiClient from '../../utils/apiClient';

/**
 * SecuritySetupPage - Enforces 2FA/3FA requirements based on user role
 * - Regular users: Must set up at least one method (TOTP recommended, Passkey optional)
 * - Admin users: Must set up TOTP first (works everywhere), then Passkey (3FA)
 *
 * IMPORTANT: TOTP is enforced first because it works on any device.
 * Passkeys are device-specific and can lock users out if it's their only method.
 */
const SecuritySetupPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { identity, isAuthenticated } = useUnifiedAuth();
  
  const [loading, setLoading] = useState(true);
  const [requirements, setRequirements] = useState(null);
  const [setupStatus, setSetupStatus] = useState({
    has_totp: false,
    has_webauthn: false,
    needs_setup: true,
    role: 'user'
  });

  // Check current 2FA status
  useEffect(() => {
    const checkSetupStatus = async () => {
      if (!isAuthenticated) {
        navigate('/login');
        return;
      }

      try {
        setLoading(true);
        
        // Get current 2FA status using working Kratos endpoint
        const response = await apiClient.get('/api/auth/me');
        const userData = response.data;
        
        // Convert to expected format
        const authMethods = userData?.user?.auth_methods || {};
        const role = userData?.user?.role || 'user';
        const isAdminUser = role === 'admin' || role === 'super_admin';

        // Determine if setup is complete based on role:
        // - Admins: MUST have TOTP (required), Passkey recommended but optional for completion
        // - Users: Need at least one method (TOTP preferred)
        const has_totp = !!authMethods.totp;
        const has_webauthn = !!authMethods.webauthn;
        const setupComplete = isAdminUser
          ? (has_totp && has_webauthn)  // Admins need BOTH
          : (has_totp || has_webauthn);  // Users need at least one

        const status = {
          has_totp,
          has_webauthn,
          needs_setup: !setupComplete,
          role
        };

        setSetupStatus(status);
        setRequirements(status.requirements);

        // If setup is complete, redirect to intended destination
        if (setupComplete) {
          const from = location.state?.from?.pathname || '/dashboard';
          console.log('Security setup complete, redirecting to:', from);
          navigate(from, { replace: true });
        }
        
      } catch (error) {
        console.error('Failed to check 2FA status:', error);
        // If we can't check status, assume setup is needed
      } finally {
        setLoading(false);
      }
    };

    checkSetupStatus();
  }, [isAuthenticated, navigate, location.state]);

  const handleSetupComplete = async () => {
    // Refresh status to check if all requirements are met
    try {
      const response = await apiClient.get('/api/auth/me');
      const userData = response.data;

      // Convert to expected format
      const authMethods = userData?.user?.auth_methods || {};
      const role = userData?.user?.role || 'user';
      const isAdminUser = role === 'admin' || role === 'super_admin';

      const has_totp = !!authMethods.totp;
      const has_webauthn = !!authMethods.webauthn;
      const setupComplete = isAdminUser
        ? (has_totp && has_webauthn)  // Admins need BOTH
        : (has_totp || has_webauthn);  // Users need at least one

      const status = {
        has_totp,
        has_webauthn,
        needs_setup: !setupComplete,
        role
      };

      setSetupStatus(status);
      setRequirements(status.requirements);

      // If setup is complete, redirect to intended destination
      if (setupComplete) {
        const from = location.state?.from?.pathname || '/dashboard';
        console.log('Security setup complete after enrollment, redirecting to:', from);
        navigate(from, { replace: true });
      }
    } catch (error) {
      console.error('Failed to refresh 2FA status:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
          <div className="text-yellow-400">Checking security requirements...</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect in useEffect
  }

  const userRole = setupStatus.role || 'user';
  const isAdmin = userRole === 'admin';
  const userEmail = identity?.traits?.email || 'your account';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Shield className="w-16 h-16 text-yellow-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Security Setup Required
          </h1>
          <p className="text-gray-300 text-lg">
            {isAdmin 
              ? "Admin accounts require enhanced security with both Passkey and TOTP authentication"
              : "Complete your security setup to access your dashboard"
            }
          </p>
        </div>

        {/* Requirements Overview */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border-2 border-yellow-400/30">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
              <AlertTriangle className="w-5 h-5 text-yellow-400 mr-2" />
              Required Security Setup for {userRole === 'admin' ? 'Admin' : 'User'} Account
            </h2>
            
            <div className="space-y-4">
              {/* TOTP Requirement - Step 1 for Admins (works on any device) */}
              <div className="flex items-center space-x-4 p-4 bg-gray-700 rounded-lg">
                <div className="flex-shrink-0">
                  {setupStatus.has_totp ? (
                    <CheckCircle className="w-6 h-6 text-green-400" />
                  ) : (
                    <Smartphone className="w-6 h-6 text-yellow-400" />
                  )}
                </div>
                <div className="flex-grow">
                  <h3 className="font-medium text-white">
                    {isAdmin ? 'Step 1: ' : ''}TOTP Authenticator
                    {setupStatus.has_totp && <span className="text-green-400 ml-2">✓ Configured</span>}
                    {isAdmin && !setupStatus.has_totp && <span className="text-yellow-400 ml-2">(Required)</span>}
                  </h3>
                  <p className="text-gray-300 text-sm">
                    Time-based codes from Google Authenticator, Authy, or similar apps.
                    {isAdmin && ' Works on any device - your recovery fallback.'}
                  </p>
                </div>
              </div>

              {/* Passkey Requirement - Step 2 for Admins */}
              {isAdmin && (
                <div className="flex items-center space-x-4 p-4 bg-gray-700 rounded-lg">
                  <div className="flex-shrink-0">
                    {setupStatus.has_webauthn ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <Key className="w-6 h-6 text-yellow-400" />
                    )}
                  </div>
                  <div className="flex-grow">
                    <h3 className="font-medium text-white">
                      Step 2: Passkey Authentication
                      {setupStatus.has_webauthn && <span className="text-green-400 ml-2">✓ Configured</span>}
                      {!setupStatus.has_webauthn && <span className="text-yellow-400 ml-2">(Required)</span>}
                    </h3>
                    <p className="text-gray-300 text-sm">
                      Use your device's built-in security (Face ID, Touch ID, Windows Hello, etc.)
                      Note: Passkeys are device-specific.
                    </p>
                  </div>
                </div>
              )}

              {/* For non-admins, show passkey as optional enhancement */}
              {!isAdmin && (
                <div className="flex items-center space-x-4 p-4 bg-gray-700 rounded-lg opacity-75">
                  <div className="flex-shrink-0">
                    {setupStatus.has_webauthn ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <Key className="w-6 h-6 text-gray-400" />
                    )}
                  </div>
                  <div className="flex-grow">
                    <h3 className="font-medium text-white">
                      Passkey Authentication
                      {setupStatus.has_webauthn && <span className="text-green-400 ml-2">✓ Configured</span>}
                      {!setupStatus.has_webauthn && <span className="text-gray-400 ml-2">(Optional)</span>}
                    </h3>
                    <p className="text-gray-300 text-sm">
                      Optional: Use your device's built-in security for faster logins.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Progress indicator */}
            <div className="mt-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-300">Setup Progress</span>
                <span className="text-sm text-gray-300">
                  {setupStatus.has_webauthn ? 1 : 0}{isAdmin ? ` + ${setupStatus.has_totp ? 1 : 0}` : ''} of {isAdmin ? '2' : '1'} complete
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                  style={{ 
                    width: `${isAdmin 
                      ? ((setupStatus.has_webauthn ? 50 : 0) + (setupStatus.has_totp ? 50 : 0))
                      : (setupStatus.has_webauthn ? 100 : 0)
                    }%` 
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Setup Components */}
        <div className="max-w-4xl mx-auto space-y-8">
          {/* TOTP Setup - Always Step 1 (works everywhere, prevents lockout) */}
          {!setupStatus.has_totp && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4 flex items-center">
                <Smartphone className="w-6 h-6 text-yellow-400 mr-2" />
                {isAdmin ? 'Step 1: ' : ''}Set up TOTP Authentication
              </h2>
              <div className="mb-4">
                <p className="text-gray-300 mb-2">
                  TOTP provides secure authentication that works on any device.
                  {isAdmin && ' Required for admin accounts.'}
                </p>
                <p className="text-gray-400 text-sm">
                  You can use Google Authenticator, Authy, 1Password, or any compatible authenticator app.
                </p>
                {isAdmin && (
                  <p className="text-yellow-400 text-sm mt-2">
                    ⚠️ Set up TOTP first - it's your recovery method if you lose access to a passkey device.
                  </p>
                )}
              </div>
              <TOTPManager onSetupComplete={handleSetupComplete} />
            </div>
          )}

          {/* Passkey Setup - Step 2 for Admins (only show after TOTP is set up) */}
          {isAdmin && setupStatus.has_totp && !setupStatus.has_webauthn && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4 flex items-center">
                <Key className="w-6 h-6 text-yellow-400 mr-2" />
                Step 2: Set up Passkey Authentication
              </h2>
              <div className="mb-4">
                <p className="text-gray-300 mb-2">
                  Passkeys provide secure, phishing-resistant authentication using your device's built-in security.
                </p>
                <p className="text-gray-400 text-sm">
                  This works with Face ID, Touch ID, Windows Hello, or security keys.
                </p>
                <p className="text-blue-400 text-sm mt-2">
                  ✓ TOTP is configured - you can always use it to recover access on any device.
                </p>
              </div>
              <PasskeyManagerDirect onSetupComplete={handleSetupComplete} />
            </div>
          )}

          {/* For non-admins who have TOTP, optionally show passkey setup */}
          {!isAdmin && setupStatus.has_totp && !setupStatus.has_webauthn && (
            <div className="bg-gray-800 rounded-lg p-6 opacity-75">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Key className="w-5 h-5 text-gray-400 mr-2" />
                Optional: Add Passkey for Faster Logins
              </h2>
              <div className="mb-4">
                <p className="text-gray-300 mb-2">
                  You can add a passkey for quicker logins using Face ID, Touch ID, or Windows Hello.
                </p>
              </div>
              <PasskeyManagerDirect onSetupComplete={handleSetupComplete} />
            </div>
          )}

          {/* Completion Message */}
          {setupStatus.has_webauthn && (!isAdmin || setupStatus.has_totp) && (
            <div className="bg-green-900/30 border-2 border-green-400/30 rounded-lg p-6 text-center">
              <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
              <h2 className="text-2xl font-semibold text-white mb-2">
                Security Setup Complete!
              </h2>
              <p className="text-gray-300 mb-6">
                Your account is now secured with {isAdmin ? '3FA (Passkey + TOTP)' : '2FA (Passkey)'} authentication.
              </p>
              <button
                onClick={() => {
                  const from = location.state?.from?.pathname || '/dashboard';
                  navigate(from, { replace: true });
                }}
                className="bg-yellow-400 hover:bg-yellow-500 text-black font-medium py-3 px-6 rounded-lg transition-colors flex items-center mx-auto"
              >
                Continue to Dashboard
                <ArrowRight className="w-4 h-4 ml-2" />
              </button>
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="max-w-4xl mx-auto mt-8 text-center">
          <p className="text-gray-400 text-sm">
            Questions about security setup? Contact your administrator or check the documentation.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SecuritySetupPage;