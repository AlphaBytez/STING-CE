import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTieredAuth } from '../../hooks/useTieredAuthCompatibility';
import { Shield, Fingerprint, Smartphone, AlertTriangle } from 'lucide-react';

/**
 * Enhanced PasskeyReminder Component
 * Shows a prominent reminder for required passkey setup since passkeys are core auth
 * Can display as either a banner (prominent) or notification (subtle) based on importance
 * Guides users to proper setup without causing login loops
 */
const PasskeyReminder = ({ variant = 'auto' }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { identity } = useKratos();
  const { isAuthenticated: isTieredAuthenticated } = useTieredAuth();
  const [show, setShow] = useState(false);
  const [displayVariant, setDisplayVariant] = useState(variant);
  const [isDismissed, setIsDismissed] = useState(false);
  const [missingMethods, setMissingMethods] = useState([]);
  const [setupAttempts, setSetupAttempts] = useState(0);

  useEffect(() => {
    // Load setup attempt count to determine urgency
    const attempts = parseInt(localStorage.getItem('passkey_setup_attempts') || '0');
    setSetupAttempts(attempts);
  }, []);

  useEffect(() => {
    // Check if user has already set up 2FA methods or dismissed the reminder
    const check2FAStatus = async () => {
      const skipped = localStorage.getItem('2fa_setup_skipped');
      const skipTimestamp = localStorage.getItem('2fa_skip_timestamp');
      const reminderDismissed = localStorage.getItem('2fa_reminder_dismissed');
      
      // Don't show if already dismissed for this session (only for notification variant)
      if (reminderDismissed === 'true' && displayVariant === 'notification') {
        return;
      }
      
      // Check if user skipped recently (within 24 hours) - only for notification variant
      if (skipped && skipTimestamp && displayVariant === 'notification') {
        const skipTime = new Date(skipTimestamp).getTime();
        const now = new Date().getTime();
        const hoursSinceSkip = (now - skipTime) / (1000 * 60 * 60);
        
        // Don't show reminder if skipped within 24 hours for notification variant
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
        
        // Use the correct API response structure from /api/auth/me
        const hasPasskey = !!userData?.has_passkey;
        const hasTOTP = !!userData?.has_totp;
        
        console.log('🔍 PasskeyReminder: Method detection (fallback):', {
          hasPasskey,
          hasTOTP,
          setupAttempts,
          displayVariant
        });
        
        const missing = [];
        if (!hasTOTP) missing.push('totp');
        if (!hasPasskey) missing.push('passkey');
        
        // Determine display variant based on missing methods and attempts
        if (variant === 'auto') {
          if (missing.length > 0) {
            // Show banner if passkey is missing or multiple attempts
            if (missing.includes('passkey') || setupAttempts >= 2) {
              setDisplayVariant('banner');
            } else {
              setDisplayVariant('notification');
            }
          }
        }
        
        // Only show if user is missing some 2FA methods
        if (missing.length > 0) {
          setMissingMethods(missing);
          // Add a small delay for notification, immediate for banner
          const delay = displayVariant === 'banner' ? 500 : 3000;
          setTimeout(() => setShow(true), delay);
        }
      } catch (error) {
        console.warn('Could not check 2FA status for reminder:', error);
        console.log('🔍 PasskeyReminder: Skipping reminder due to API error');
      }
    };

    if (identity) {
      check2FAStatus();
    }
  }, [identity, displayVariant, setupAttempts, isTieredAuthenticated, variant]);

  const handleSetupNow = () => {
    // Increment setup attempts
    const newAttempts = setupAttempts + 1;
    localStorage.setItem('passkey_setup_attempts', newAttempts.toString());
    
    // Choose best setup path based on missing methods
    if (missingMethods.includes('passkey')) {
      // Route directly to AAL2 setup for passkey enrollment
      navigate('/aal2-step-up', { 
        state: { 
          preferredMethod: 'passkey',
          from: location.pathname,
          setupContext: 'passkey_reminder'
        }
      });
    } else {
      // Route to settings for TOTP setup
      navigate('/dashboard/settings?tab=security', {
        state: { setupContext: 'passkey_reminder' }
      });
    }
  };

  const handleAlternativeSetup = () => {
    navigate('/dashboard/settings?tab=security&focus=totp', {
      state: { setupContext: 'passkey_reminder' }
    });
  };

  const handleRemindLater = () => {
    // Only allow remind later for notification variant
    if (displayVariant === 'notification') {
      // Store skip info for 24 hours
      localStorage.setItem('2fa_setup_skipped', 'true');
      localStorage.setItem('2fa_skip_timestamp', new Date().toISOString());
    }
    setShow(false);
  };

  const handleDismiss = () => {
    // Only allow dismiss for notification variant
    if (displayVariant === 'notification') {
      setIsDismissed(true);
      localStorage.setItem('2fa_reminder_dismissed', 'true');
    }
    setShow(false);
  };

  if (!show || isDismissed || missingMethods.length === 0) {
    return null;
  }

  const hasMultipleMissing = missingMethods.length > 1;
  const missingTotp = missingMethods.includes('totp');
  const missingPasskey = missingMethods.includes('passkey');
  const isUrgent = missingPasskey || setupAttempts >= 2;

  // Banner variant for critical/required setup
  if (displayVariant === 'banner') {
    return (
      <div className="sticky top-0 z-50 bg-gradient-to-r from-amber-600 via-orange-600 to-red-600 border-b border-orange-500/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-3">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-6 w-6 text-white" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-white">
                  {missingPasskey ? 'Passkey Setup Required' : 'Complete Security Setup'}
                </h3>
                <p className="text-sm text-orange-100">
                  {missingPasskey 
                    ? 'Passkeys are required for core authentication. Some features may not work properly without them.'
                    : 'Complete your security setup for full access to all features.'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {missingPasskey && (
                <button
                  onClick={handleSetupNow}
                  className="bg-white text-orange-600 hover:text-orange-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Set up Passkey Now
                </button>
              )}
              {missingTotp && !missingPasskey && (
                <button
                  onClick={handleAlternativeSetup}
                  className="text-white hover:text-orange-100 px-3 py-2 text-sm font-medium border border-white/30 rounded-md transition-colors"
                >
                  Set up TOTP
                </button>
              )}
              {hasMultipleMissing && (
                <button
                  onClick={handleSetupNow}
                  className="bg-white text-orange-600 hover:text-orange-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Complete Setup
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Notification variant (original floating style)
  return (
    <div className="fixed bottom-4 right-4 max-w-sm z-[9999] animate-fade-in-up">
      <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 shadow-2xl">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <div className={`p-2 rounded-lg ${isUrgent 
              ? 'bg-gradient-to-br from-orange-500/20 to-red-500/20' 
              : 'bg-gradient-to-br from-yellow-500/20 to-amber-500/20'
            }`}>
              {missingPasskey ? (
                <Fingerprint className={`w-5 h-5 ${isUrgent ? 'text-orange-400' : 'text-yellow-400'}`} />
              ) : (
                <Shield className={`w-5 h-5 ${isUrgent ? 'text-orange-400' : 'text-yellow-400'}`} />
              )}
            </div>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-white">
              {hasMultipleMissing ? 'Complete your security setup' : 
               missingTotp ? 'Set up TOTP authentication' : 
               'Set up biometric authentication'}
            </h3>
            <p className="mt-1 text-sm text-slate-300">
              {missingPasskey 
                ? 'Passkeys are required for core authentication and full feature access.'
                : hasMultipleMissing 
                  ? 'Add TOTP and biometric authentication for maximum security'
                  : 'Add TOTP for secure two-factor authentication'
              }
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
              {setupAttempts > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-orange-400">
                  <AlertTriangle className="w-3 h-3" />
                  Attempt #{setupAttempts + 1}
                </span>
              )}
            </div>
            
            <div className="mt-3 flex space-x-3">
              <button
                onClick={handleSetupNow}
                className={`text-sm font-medium transition-colors ${
                  isUrgent 
                    ? 'text-orange-400 hover:text-orange-300' 
                    : 'text-yellow-400 hover:text-yellow-300'
                }`}
              >
                {missingPasskey ? 'Set up Passkey' : 'Set up now'}
              </button>
              {missingTotp && missingPasskey && (
                <button
                  onClick={handleAlternativeSetup}
                  className="text-sm font-medium text-green-400 hover:text-green-300 transition-colors"
                >
                  TOTP only
                </button>
              )}
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
