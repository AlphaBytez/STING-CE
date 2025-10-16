import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams, Navigate } from 'react-router-dom';
import { Shield, Key, Smartphone, CheckCircle, ArrowRight, AlertCircle } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import securityGateService from '../../services/securityGateService';
import SecuritySettings from '../user/SecuritySettings';

/**
 * Modern Enrollment Page
 * 
 * Clean, simple enrollment that leverages working SecuritySettings component
 * Implements universal 3-factor security: Email + Passkey + (Hardware Key OR TOTP)
 */
const ModernEnrollment = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  
  const { identity, session, isLoading } = useKratos();
  const { isAuthenticated } = useUnifiedAuth();
  
  // Get return URL from search params
  const returnTo = searchParams.get('return_to') || '/dashboard';
  const isNewUser = searchParams.get('newuser') === 'true';
  const isReauth = searchParams.get('reauth') === 'true' ||
                   location.pathname.includes('aal2') ||
                   location.pathname.includes('security-upgrade') ||
                   searchParams.get('reason') || // Coming from operation requiring confirmation
                   searchParams.get('tier') || // Coming from tiered security system
                   document.referrer.includes('dashboard') || // Coming from existing session
                   sessionStorage.getItem('api_key_pre_operation'); // Operation-specific auth
  
  // Component state
  const [securityStatus, setSecurityStatus] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [enrollmentStep, setEnrollmentStep] = useState('intro'); // intro, setup, complete
  
  // Extract user info
  const userEmail = identity?.traits?.email;
  const isAdmin = identity?.traits?.role === 'admin';
  
  // Skip complex security checking - enrollment should work with AAL1
  useEffect(() => {
    const checkMethodStatus = async () => {
      if (!identity?.traits?.email) return;
      
      console.log('🔒 ModernEnrollment: User authenticated with AAL1, proceeding to setup');
      
      try {
        // Use the AAL2 status endpoint for method detection
        const response = await fetch('/api/auth/aal2/status', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' }
        });

        let hasPasskey = false;
        let hasTOTP = false;

        if (response.ok) {
          const statusData = await response.json();
          // The endpoint returns configured_methods, not available_methods
          const configuredMethods = statusData?.configured_methods || {};

          hasPasskey = configuredMethods.webauthn || statusData?.has_webauthn || false;
          hasTOTP = configuredMethods.totp || statusData?.has_totp || false;

          console.log('🔒 ModernEnrollment: Method detection via /api/auth/aal2/status:', {
            hasPasskey,
            hasTOTP,
            configuredMethods,
            statusData
          });
        } else {
          console.warn('🔒 ModernEnrollment: /api/auth/aal2/status failed, using fallback');
        }
        
        // Create enrollment status with actual detection
        const enrollmentStatus = {
          meetsRequirements: hasPasskey && hasTOTP, // Both required for completion
          reason: 'Universal 3-factor setup required',
          message: hasPasskey && hasTOTP ? 'Security setup complete!' : 'Complete your security setup to access all features',
          currentMethods: {
            passkey: hasPasskey,
            totp: hasTOTP,
            email: true // Already verified via AAL1
          },
          suggestions: {
          primary: 'Set up Face ID/Touch ID passkey for daily convenience',
          backup: 'Add hardware key (YubiKey) or TOTP app as secure backup',
          benefits: [
            '🔒 Never get locked out (redundant authentication)',
            '⚡ Fast daily login with passkey',
            '🌍 Hardware keys work on any device, anywhere',
            '📱 TOTP apps work offline'
          ]
        }
      };
      
        setSecurityStatus(enrollmentStatus);

        // Only show completion screen during actual enrollment, not reauthentication
        if (isReauth) {
          // During reauthentication, skip enrollment flow entirely - go to method selection
          console.log('🔄 Reauthentication context detected, proceeding to method selection');
          setEnrollmentStep('setup');
        } else if (hasPasskey && hasTOTP) {
          // True enrollment context AND user has completed setup
          console.log('✅ Enrollment complete, showing completion screen');
          setEnrollmentStep('complete');
        } else {
          // True enrollment context, user needs to complete setup
          console.log('📝 Starting enrollment flow');
          setEnrollmentStep('intro');
        }
        
      } catch (error) {
        console.error('🔒 ModernEnrollment: Error checking method status:', error);
        // Fallback to basic setup
        const fallbackStatus = {
          meetsRequirements: false,
          reason: 'Universal 3-factor setup required', 
          message: 'Complete your security setup to access all features',
          currentMethods: { passkey: false, totp: false, email: true },
          suggestions: {
            primary: 'Set up Face ID/Touch ID passkey for daily convenience',
            backup: 'Add hardware key (YubiKey) or TOTP app as secure backup',
            benefits: [
              '🔒 Never get locked out (redundant authentication)',
              '⚡ Fast daily login with passkey', 
              '🌍 Hardware keys work on any device, anywhere',
              '📱 TOTP apps work offline'
            ]
          }
        };
        setSecurityStatus(fallbackStatus);
        setEnrollmentStep('intro');
      } finally {
        setCheckingStatus(false);
      }
    };
    
    checkMethodStatus();
  }, [identity]);
  
  // Handle completion and navigation
  const handleEnrollmentComplete = async () => {
    console.log('🎉 ModernEnrollment: 3-factor enrollment complete!');
    setEnrollmentStep('complete');
    
    try {
      // CRITICAL: Set Flask AAL2 flag to prevent infinite redirects
      console.log('🔐 Setting Flask AAL2 access after enrollment completion...');
      const aal2Response = await fetch('/api/auth/grant-aal2-access', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (aal2Response.ok) {
        console.log('✅ Flask AAL2 access granted successfully');
      } else {
        console.warn('⚠️ Failed to set Flask AAL2 access - user may need to re-authenticate');
      }
    } catch (error) {
      console.error('❌ Error setting Flask AAL2 access:', error);
    }
    
    // Navigate to return URL after Flask AAL2 is set
    setTimeout(() => {
      navigate(returnTo, { replace: true });
    }, 1000); // Reduced delay since we're not just showing success
  };
  
  // Loading state
  if (isLoading || checkingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p className="text-lg">Checking security requirements...</p>
        </div>
      </div>
    );
  }
  
  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // Introduction step
  if (enrollmentStep === 'intro') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
        <div className="w-full max-w-2xl bg-gray-800 rounded-lg shadow-xl p-8 text-white">
          <div className="text-center mb-8">
            <Shield className="w-16 h-16 text-yellow-400 mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-2">Welcome to STING Security</h1>
            <p className="text-gray-300 text-lg">
              {isAdmin ? 'Admin' : 'User'} account security setup required
            </p>
          </div>
          
          <div className="bg-blue-950 border border-blue-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-blue-200 mb-4">🔒 Universal 3-Factor Security</h2>
            <p className="text-blue-300 mb-4">
              STING uses 3-factor authentication to ensure you never get locked out while maintaining maximum security:
            </p>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span><strong>Email</strong> - Already verified ✅</span>
              </div>
              <div className="flex items-center space-x-3">
                <Key className="w-5 h-5 text-yellow-400" />
                <span><strong>Passkey</strong> - Face ID/Touch ID for daily convenience</span>
              </div>
              <div className="flex items-center space-x-3">
                <Smartphone className="w-5 h-5 text-purple-400" />
                <span><strong>Backup Method</strong> - Hardware key (YubiKey) or TOTP app</span>
              </div>
            </div>
          </div>
          
          <div className="bg-green-950 border border-green-700 rounded-lg p-4 mb-6">
            <h3 className="text-green-200 font-medium mb-2">🚀 Benefits:</h3>
            <ul className="text-green-300 text-sm space-y-1">
              <li>• 🔒 Never get locked out (redundant authentication)</li>
              <li>• ⚡ Fast daily login with passkey</li>
              <li>• 🌍 Hardware keys work on any device, anywhere</li>
              <li>• 📱 TOTP apps work offline</li>
            </ul>
          </div>
          
          <div className="flex justify-center">
            <button
              onClick={() => setEnrollmentStep('setup')}
              className="px-8 py-3 bg-yellow-600 text-black font-medium rounded-lg hover:bg-yellow-500 transition-colors flex items-center space-x-2"
            >
              <span>Set Up Security Methods</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  // Setup step - embed SecuritySettings component
  if (enrollmentStep === 'setup') {
    return (
      <div className="min-h-screen bg-gray-900 p-4">
        <div className="w-full max-w-4xl mx-auto">
          {/* Enrollment Header */}
          <div className="bg-gray-800 rounded-lg shadow-xl p-6 mb-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold flex items-center space-x-2">
                  <Shield className="w-6 h-6 text-yellow-400" />
                  <span>Security Setup - {isAdmin ? 'Admin' : 'User'} Account</span>
                </h1>
                <p className="text-gray-400 mt-1">
                  {userEmail} | Configure your authentication methods below
                </p>
              </div>
              
              {securityStatus && (
                <div className="text-right">
                  <div className="text-sm text-gray-400">Progress</div>
                  <div className="flex space-x-2">
                    <div className={`w-3 h-3 rounded-full ${securityStatus.currentMethods?.passkey ? 'bg-green-500' : 'bg-gray-600'}`}></div>
                    <div className={`w-3 h-3 rounded-full ${securityStatus.currentMethods?.totp ? 'bg-green-500' : 'bg-gray-600'}`}></div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Requirements Display */}
            {securityStatus && !securityStatus.meetsRequirements && (
              <div className="mt-4 p-4 bg-orange-950 border border-orange-700 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <AlertCircle className="w-5 h-5 text-orange-400" />
                  <span className="text-orange-200 font-medium">Setup Required</span>
                </div>
                <p className="text-orange-300 text-sm">{securityStatus.message}</p>
              </div>
            )}
          </div>
          
          {/* Embed SecuritySettings Component */}
          <div className="bg-gray-800 rounded-lg shadow-xl">
            <SecuritySettings 
              enrollmentMode={true}
              onEnrollmentComplete={handleEnrollmentComplete}
              showEnrollmentProgress={true}
            />
          </div>
          
          {/* Manual completion override for testing */}
          <div className="mt-6 text-center">
            <button
              onClick={async () => {
                console.log('🎉 Manual enrollment completion triggered');
                await handleEnrollmentComplete();
              }}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium"
            >
              🚀 I've completed both passkey and TOTP setup - Continue to Dashboard
            </button>
            <p className="text-gray-400 text-xs mt-2">
              Click this if you've set up both authentication methods
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // Complete step
  if (enrollmentStep === 'complete') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
        <div className="w-full max-w-md bg-gray-800 rounded-lg shadow-xl p-8 text-white text-center">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Security Setup Complete!</h1>
          <p className="text-gray-300 mb-6">
            Your account is now secured with 3-factor authentication. You'll have 8 hours of uninterrupted access.
          </p>
          
          <div className="bg-green-950 border border-green-700 rounded-lg p-4 mb-6">
            <h3 className="text-green-200 font-medium mb-2">✅ Configured Methods:</h3>
            <div className="space-y-2 text-sm text-green-300">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4" />
                <span>Email verification</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4" />
                <span>Passkey (Face ID/Touch ID)</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4" />
                <span>Backup method (Hardware key or TOTP)</span>
              </div>
            </div>
          </div>
          
          <button
            onClick={async () => {
              // Ensure AAL2 is set before navigating
              try {
                console.log('🔐 Ensuring Flask AAL2 before navigation...');
                const response = await fetch('/api/auth/grant-aal2-access', {
                  method: 'POST',
                  credentials: 'include',
                  headers: { 'Content-Type': 'application/json' }
                });

                if (response.ok) {
                  console.log('✅ Flask AAL2 confirmed, navigating to dashboard');
                } else {
                  console.warn('⚠️ AAL2 grant failed, but continuing anyway');
                }
              } catch (error) {
                console.error('Error setting AAL2:', error);
              }

              navigate(returnTo, { replace: true });
            }}
            className="w-full px-6 py-3 bg-yellow-600 text-black font-medium rounded-lg hover:bg-yellow-500 transition-colors"
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    );
  }
  
  return null;
};

export default ModernEnrollment;