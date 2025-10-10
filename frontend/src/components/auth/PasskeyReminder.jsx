import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTieredAuth } from '../../hooks/useTieredAuthCompatibility';
import { Shield, Fingerprint, Smartphone } from 'lucide-react';

/**
 * PasskeyReminder Component
 * Shows a non-intrusive reminder on the dashboard if user hasn't set up 2FA methods
 * Updated to remind about both TOTP and passkeys
 */
const PasskeyReminder = () => {
  const navigate = useNavigate();
  const { identity } = useKratos();
  const { isAuthenticated: isTieredAuthenticated } = useTieredAuth();
  const [show, setShow] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [missingMethods, setMissingMethods] = useState([]);

  useEffect(() => {
    // Check if user has already set up 2FA methods or dismissed the reminder
    const check2FAStatus = async () => {
      const skipped = localStorage.getItem('2fa_setup_skipped');
      const skipTimestamp = localStorage.getItem('2fa_skip_timestamp');
      const reminderDismissed = localStorage.getItem('2fa_reminder_dismissed');
      
      // Don't show if already dismissed for this session
      if (reminderDismissed === 'true') {
        return;
      }
      
      // Check if user skipped recently (within 24 hours)
      if (skipped && skipTimestamp) {
        const skipTime = new Date(skipTimestamp).getTime();
        const now = new Date().getTime();
        const hoursSinceSkip = (now - skipTime) / (1000 * 60 * 60);
        
        // Don't show reminder if skipped within 24 hours
        if (hoursSinceSkip < 24) {
          return;
        }
      }

      // Check 2FA status using the same working endpoint as SecurityGateService
      try {
        // UNIFIED: Use tiered authentication status
        if (isTieredAuthenticated) {
          console.log('🔍 PasskeyReminder: Already authenticated - checking methods');
          // Continue to check missing methods
        }
        
        // If no AAL2, check what's missing (fallback to API check)
        const response = await fetch('/api/auth/me', {
          credentials: 'include'
        });
        const userData = await response.json();
        
        // Use the correct Kratos data structure
        const authMethods = userData?.user?.auth_methods || {};
        const hasPasskey = !!authMethods.webauthn;
        const hasTOTP = !!authMethods.totp;
        
        console.log('🔍 PasskeyReminder: Method detection (fallback):', {
          hasPasskey,
          hasTOTP,
          authMethods,
          isTieredAuthenticated
        });
        
        const missing = [];
        if (!hasTOTP) missing.push('totp');
        if (!hasPasskey) missing.push('passkey');
        
        // Only show if user is missing some 2FA methods
        if (missing.length > 0) {
          setMissingMethods(missing);
          // Add a small delay so it doesn't appear immediately
          setTimeout(() => setShow(true), 3000);
        }
      } catch (error) {
        console.warn('Could not check 2FA status for reminder:', error);
        // Don't show fallback popup since we can't reliably determine status
        console.log('🔍 PasskeyReminder: Skipping reminder due to API error');
      }
    };

    if (identity) {
      check2FAStatus();
    }
  }, [identity]);

  const handleSetupNow = () => {
    navigate('/dashboard/settings?tab=security');
  };

  const handleRemindLater = () => {
    // Store skip info for 24 hours
    localStorage.setItem('2fa_setup_skipped', 'true');
    localStorage.setItem('2fa_skip_timestamp', new Date().toISOString());
    setShow(false);
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('2fa_reminder_dismissed', 'true');
    setShow(false);
  };

  if (!show || isDismissed || missingMethods.length === 0) {
    return null;
  }

  const hasMultipleMissing = missingMethods.length > 1;
  const missingTotp = missingMethods.includes('totp');
  const missingPasskey = missingMethods.includes('passkey');

  return (
    <div className="fixed bottom-4 right-4 max-w-sm z-[9999] animate-fade-in-up">
      <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 shadow-2xl">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <div className="p-2 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-lg">
              <Shield className="w-5 h-5 text-yellow-400" />
            </div>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-white">
              {hasMultipleMissing ? 'Complete your security setup' : 
               missingTotp ? 'Set up TOTP authentication' : 
               'Set up biometric authentication'}
            </h3>
            <p className="mt-1 text-sm text-slate-300">
              {hasMultipleMissing ? 'Add TOTP and biometric authentication for maximum security' :
               missingTotp ? 'Add TOTP for secure two-factor authentication' :
               'Add biometric authentication for quick and secure access'}
            </p>
            
            {/* Show what's missing */}
            <div className="mt-2 flex items-center gap-2">
              {missingTotp && (
                <span className="inline-flex items-center gap-1 text-xs text-green-400">
                  <Smartphone className="w-3 h-3" />
                  TOTP
                </span>
              )}
              {missingPasskey && (
                <span className="inline-flex items-center gap-1 text-xs text-purple-400">
                  <Fingerprint className="w-3 h-3" />
                  Passkey
                </span>
              )}
            </div>
            
            <div className="mt-3 flex space-x-3">
              <button
                onClick={handleSetupNow}
                className="text-sm font-medium text-yellow-400 hover:text-yellow-300 transition-colors"
              >
                Set up now
              </button>
              <button
                onClick={handleRemindLater}
                className="text-sm font-medium text-slate-400 hover:text-slate-300 transition-colors"
              >
                Remind me later
              </button>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="ml-4 flex-shrink-0 text-slate-400 hover:text-slate-300"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default PasskeyReminder;