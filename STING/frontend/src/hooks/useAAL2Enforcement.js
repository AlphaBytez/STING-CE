/**
 * FIXED: Proper AAL2 enforcement hook
 * Handles step-up authentication instead of forcing re-login
 */

import { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';

export const useAAL2Enforcement = () => {
  const location = useLocation();
  
  const [isCheckingAAL, setIsCheckingAAL] = useState(false);
  const [needsAAL2, setNeedsAAL2] = useState(false);
  const [showStepUp, setShowStepUp] = useState(false);
  const [stepUpError, setStepUpError] = useState(null);
  const [stepUpUrl, setStepUpUrl] = useState(null);

  /**
   * FIXED: Proper AAL2 enforcement with step-up authentication
   */
  const checkAAL2Status = useCallback(async () => {
    try {
      setIsCheckingAAL(true);
      setStepUpError(null);

      // Get current session from Flask backend
      const sessionResponse = await axios.get('/api/auth/me', {
        withCredentials: true
      });

      const session = sessionResponse.data;
      const currentAAL = session.auth_method === 'enhanced_webauthn' ? 'aal2' : 'aal1';
      const userRole = session.user?.role || 'user';
      
      // Check if user has 2FA methods configured (Flask response format)
      const hasWebAuthn = session.has_passkey || session.passkey_count > 0;
      const hasTOTP = false; // TOTP not implemented in Flask backend yet
      const has2FAMethods = hasWebAuthn || hasTOTP;

      console.log('🔐 FIXED AAL2 Check:', {
        currentAAL,
        has2FAMethods,
        userRole,
        pathname: location.pathname,
        hasWebAuthn,
        hasTOTP
      });

      // Determine if AAL2 is required for this route
      const requiresAAL2 = userRole === 'admin' || location.pathname.includes('/reports');
      
      if (requiresAAL2) {
        if (!has2FAMethods) {
          // No 2FA setup - need to set it up first
          console.log('🔐 No 2FA methods configured, redirecting to setup');
          setStepUpError('Please complete 2FA setup before accessing sensitive data.');
          setNeedsAAL2(true);
          setStepUpUrl('/enrollment');
          return;
        }
        
        if (currentAAL !== 'aal2') {
          // Has 2FA but needs step-up
          console.log('🔐 Has 2FA methods but at AAL1, initiating step-up flow');
          const returnUrl = encodeURIComponent(window.location.href);
          
          // FIXED: Use the correct step-up URL format
          const stepUpUrl = `/.ory/self-service/login/browser?refresh=true&aal=aal2&return_to=${returnUrl}`;
          
          setStepUpUrl(stepUpUrl);
          // FIXED: Better error message for step-up
          setStepUpError('Please authenticate with your passkey or TOTP to access sensitive data.');
          setNeedsAAL2(true);
          setShowStepUp(true);
          return;
        }
      }

      // All requirements met
      console.log('🔐 AAL2 requirements satisfied');
      setNeedsAAL2(false);
      setStepUpError(null);
      setShowStepUp(false);

    } catch (error) {
      console.error('🔐 AAL2 status check failed:', error);
      
      // Check if this is an API error indicating step-up is needed
      if (error.response?.status === 403 && error.response?.data?.error === 'AAL2_REQUIRED') {
        setStepUpUrl(error.response.data.step_up_url);
        setStepUpError(error.response.data.message);
        setNeedsAAL2(true);
        setShowStepUp(true);
      } else {
        setStepUpError('Unable to verify security level. Please try again.');
        setNeedsAAL2(true);
      }
    } finally {
      setIsCheckingAAL(false);
    }
  }, [location.pathname]);

  /**
   * FIXED: Initiate proper step-up authentication
   */
  const initiateStepUp = useCallback(() => {
    if (stepUpUrl) {
      console.log('🔐 Initiating step-up with URL:', stepUpUrl);
      console.log('🔐 Current location:', window.location.href);
      console.log('🔐 Decoded return URL:', decodeURIComponent(stepUpUrl.split('return_to=')[1] || ''));
      
      // Store the intended destination in sessionStorage as backup
      sessionStorage.setItem('aal2_return_to', window.location.href);
      
      window.location.href = stepUpUrl;
    }
  }, [stepUpUrl]);

  /**
   * Handle successful step-up authentication
   */
  const handleAAL2Success = useCallback(() => {
    console.log('🔐 AAL2 step-up completed, refreshing status');
    setNeedsAAL2(false);
    setShowStepUp(false);
    setStepUpError(null);
    
    // Re-check AAL status
    checkAAL2Status();
  }, [checkAAL2Status]);

  // Check AAL2 status when route changes
  useEffect(() => {
    checkAAL2Status();
  }, [checkAAL2Status]);

  return {
    isCheckingAAL,
    needsAAL2,
    showStepUp,
    stepUpError,
    stepUpUrl,
    checkAAL2Status,
    handleAAL2Success,
    initiateStepUp,
    setShowStepUp
  };
};

export default useAAL2Enforcement;