import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlassLoginLayout } from '../styles/GlassLoginStyles';
import { useKratos } from '../auth/KratosProviderRefactored';
import '../theme/sting-glass-theme.css';

/**
 * PostRegistration - Shown after successful registration
 * Handles verification redirect when email verification is required
 */
const PostRegistration = () => {
  const navigate = useNavigate();
  const { identity, checkSession } = useKratos();
  const [step, setStep] = useState('verification'); // verification, security-setup, passkey-setup, totp-setup, complete
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [securityProgress, setSecurityProgress] = useState({
    passkey: false,
    totp: false
  });
  
  useEffect(() => {
    // Check WebAuthn support
    const checkWebAuthn = async () => {
      if (window.PublicKeyCredential) {
        try {
          const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          setWebAuthnSupported(available || true); // Allow external authenticators too
        } catch {
          setWebAuthnSupported(true);
        }
      }
    };
    checkWebAuthn();
  }, []);

  useEffect(() => {
    const handlePostRegistration = async () => {
      // Check if email verification is needed first
      const urlParams = new URLSearchParams(window.location.search);
      const flow = urlParams.get('flow');
      
      if (flow) {
        // Redirect to verification first
        navigate(`/verification?flow=${flow}`);
        return;
      }

      // After verification (or if no verification needed), enforce universal TOTP setup
      await checkSession();
      
      // Check what security methods are already configured
      const hasPasskey = identity?.credentials?.webauthn || false;
      const hasTOTP = identity?.credentials?.totp || false;
      
      setSecurityProgress({
        passkey: hasPasskey,
        totp: hasTOTP
      });
      
      if (hasTOTP) {
        // User has required TOTP backup, proceed to dashboard
        // Note: Passkeys are optional but recommended for better UX
        setStep('complete');
        setTimeout(() => navigate('/dashboard'), 2000);
      } else {
        // TOTP is mandatory for all users as AAL2 backup
        setStep('security-setup');
      }
    };

    handlePostRegistration();
  }, [navigate, identity, checkSession]);

  const handleMandatoryTOTPSetup = async () => {
    try {
      // Navigate to settings to set up TOTP (mandatory)
      navigate('/dashboard/settings?tab=security&setup=totp&required=true');
    } catch (error) {
      console.error('Error setting up TOTP:', error);
    }
  };

  const handleOptionalPasskeySetup = async () => {
    try {
      // Navigate to settings to set up passkey (optional but recommended)
      navigate('/dashboard/settings?tab=security&setup=passkey&recommended=true');
    } catch (error) {
      console.error('Error setting up passkey:', error);
    }
  };

  if (step === 'security-setup') {
    return (
      <GlassLoginLayout 
        title="Complete Security Setup" 
        subtitle="TOTP authentication is required for all users"
      >
        <div className="text-center">
          <div className="mb-6">
            <svg className="w-16 h-16 text-amber-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2-2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            
            <h3 className="text-xl font-semibold text-white mb-4">
              🔒 Enhanced Security Required
            </h3>
            
            <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4 mb-6">
              <p className="text-amber-300 text-sm font-medium mb-2">
                📱 TOTP Setup Required
              </p>
              <p className="text-gray-300 text-sm">
                All users must configure TOTP (Time-based One-Time Password) as a backup authentication method. 
                This ensures you can always access your account, even without biometric devices.
              </p>
            </div>
            
            <div className="space-y-3 mb-6">
              <button
                onClick={handleMandatoryTOTPSetup}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                📱 Set Up TOTP (Required)
              </button>
            </div>
            
            {webAuthnSupported && (
              <div className="space-y-3">
                <div className="border-t border-gray-600 pt-4">
                  <p className="text-gray-400 text-sm mb-3">
                    Optional: Set up a passkey for faster everyday logins
                  </p>
                  <button
                    onClick={handleOptionalPasskeySetup}
                    className="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
                  >
                    🔐 Add Passkey (Recommended)
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </GlassLoginLayout>
    );
  }

  // Original verification/completion flow
  return (
    <GlassLoginLayout 
      title="Welcome to STING!" 
      subtitle="Your account has been created successfully"
    >
      <div className="text-center">
        <div className="mb-6">
          <svg className="w-16 h-16 text-green-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          
          <p className="text-gray-300 mb-4">
            Please check your email to verify your account.
          </p>
          
          <p className="text-sm text-gray-400 mb-4">
            We've sent a verification email to your registered email address.
          </p>
          
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4 mb-6">
            <p className="text-yellow-300 text-sm">
              📧 Check your inbox for the verification email
            </p>
            <p className="text-gray-400 text-xs mt-2">
              For testing: Check Mailpit at <a href="http://localhost:8026" target="_blank" rel="noopener noreferrer" className="text-yellow-400 hover:text-yellow-300">http://localhost:8026</a>
            </p>
          </div>
          
          <div className="flex justify-center">
            <div className="spinner"></div>
          </div>
        </div>
        
        <p className="text-sm text-gray-400">
          Waiting for email verification...
        </p>
      </div>
    </GlassLoginLayout>
  );
};

export default PostRegistration;