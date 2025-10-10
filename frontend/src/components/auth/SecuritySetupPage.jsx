import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Key, Smartphone, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';
import TOTPManager from '../settings/TOTPManager';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import apiClient from '../../utils/apiClient';

/**
 * SecuritySetupPage - Enforces 2FA/3FA requirements based on user role
 * - Regular users: Must set up Passkey (WebAuthn)
 * - Admin users: Must set up both Passkey and TOTP (3FA)
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
        const status = {
          has_totp: !!authMethods.totp,
          has_webauthn: !!authMethods.webauthn,
          needs_setup: !(authMethods.totp || authMethods.webauthn),
          role: userData?.user?.role || 'user'
        };
        
        setSetupStatus(status);
        setRequirements(status.requirements);
        
        // If setup is complete, redirect to intended destination
        if (!status.needs_setup) {
          const from = location.state?.from?.pathname || '/dashboard';
          console.log('2FA setup complete, redirecting to:', from);
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
      const status = {
        has_totp: !!authMethods.totp,
        has_webauthn: !!authMethods.webauthn,
        needs_setup: !(authMethods.totp || authMethods.webauthn),
        role: userData?.user?.role || 'user'
      };
      
      setSetupStatus(status);
      setRequirements(status.requirements);
      
      // If setup is complete, redirect to intended destination
      if (!status.needs_setup) {
        const from = location.state?.from?.pathname || '/dashboard';
        console.log('2FA setup complete after component setup, redirecting to:', from);
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
              {/* Passkey Requirement */}
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
                    Passkey Authentication
                    {setupStatus.has_webauthn && <span className="text-green-400 ml-2">✓ Configured</span>}
                  </h3>
                  <p className="text-gray-300 text-sm">
                    Use your device's built-in security (Face ID, Touch ID, Windows Hello, etc.)
                  </p>
                </div>
              </div>

              {/* TOTP Requirement (Admins only) */}
              {isAdmin && (
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
                      TOTP Authenticator
                      {setupStatus.has_totp && <span className="text-green-400 ml-2">✓ Configured</span>}
                    </h3>
                    <p className="text-gray-300 text-sm">
                      Time-based codes from Google Authenticator, Authy, or similar apps
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
          {/* Passkey Setup */}
          {!setupStatus.has_webauthn && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4 flex items-center">
                <Key className="w-6 h-6 text-yellow-400 mr-2" />
                Step 1: Set up Passkey Authentication
              </h2>
              <div className="mb-4">
                <p className="text-gray-300 mb-2">
                  Passkeys provide secure, phishing-resistant authentication using your device's built-in security.
                </p>
                <p className="text-gray-400 text-sm">
                  This works with Face ID, Touch ID, Windows Hello, or security keys.
                </p>
              </div>
              <PasskeyManagerDirect onSetupComplete={handleSetupComplete} />
            </div>
          )}

          {/* TOTP Setup (Admins only) */}
          {isAdmin && !setupStatus.has_totp && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4 flex items-center">
                <Smartphone className="w-6 h-6 text-yellow-400 mr-2" />
                Step {setupStatus.has_webauthn ? '2' : '2'}: Set up TOTP Authentication
              </h2>
              <div className="mb-4">
                <p className="text-gray-300 mb-2">
                  TOTP provides a backup authentication method and is required for admin accounts.
                </p>
                <p className="text-gray-400 text-sm">
                  You can use Google Authenticator, Authy, 1Password, or any compatible authenticator app.
                </p>
              </div>
              <TOTPManager onSetupComplete={handleSetupComplete} />
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