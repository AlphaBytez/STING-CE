import { useCallback } from 'react';
import { useAuth } from '../contexts/AuthProvider';
import { useKratosFlow } from './useKratosFlow';
import { useSessionCoordination } from './useSessionCoordination';

export function useWebAuthn() {
  const { setError, dispatchAuthSuccess } = useAuth();
  const { submitToFlow, extractCSRFToken } = useKratosFlow();
  const { completeSessionCoordination } = useSessionCoordination();
  
  // Perform WebAuthn authentication as AAL2 second factor
  // NOTE: With passwordless: false in Kratos config, WebAuthn is now a second factor only
  const authenticateAAL2 = useCallback(async (flowData, userEmail, returnTo = '/dashboard') => {
    console.log('🔐 Starting AAL2 WebAuthn authentication for:', userEmail);
    
    if (!flowData) {
      throw new Error('No flow data available for WebAuthn authentication');
    }
    
    try {
      // Prepare form data for Kratos WebAuthn submission
      const formData = new URLSearchParams();
      formData.append('method', 'webauthn');
      
      const csrfToken = extractCSRFToken(flowData);
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      console.log('🔐 Submitting WebAuthn method to Kratos flow...');
      
      // Submit to Kratos flow - this will trigger WebAuthn ceremony
      const response = await submitToFlow(flowData, formData.toString());
      
      console.log('🔐 WebAuthn flow response:', response.status, response.data?.state);
      
      // Check if authentication was successful
      if (response.status === 200 && (response.data?.session || response.data?.state === 'passed_challenge')) {
        console.log('✅ AAL2 WebAuthn authentication successful!');
        
        // Store successful passkey usage
        localStorage.setItem('sting_last_passkey_user', userEmail);
        
        // Dispatch auth success event
        dispatchAuthSuccess('webauthn', 'aal2', true);
        
        // Complete session coordination
        await completeSessionCoordination('webauthn', 'aal2', returnTo);
        
        return true;
      } else if (response.data?.redirect_browser_to) {
        // Handle redirects if needed
        console.log('🔐 WebAuthn flow requires redirect:', response.data.redirect_browser_to);
        window.location.href = response.data.redirect_browser_to;
        return true;
      } else {
        // Extract error from Kratos response
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        throw new Error(errorMsg || 'WebAuthn authentication failed');
      }
    } catch (error) {
      console.error('🔐 AAL2 WebAuthn authentication failed:', error);
      
      if (error.name === 'NotAllowedError') {
        setError('Biometric authentication was cancelled or failed. Please try again.');
      } else {
        setError(`Passkey authentication failed: ${error.message}`);
      }
      
      return false;
    }
  }, [setError, dispatchAuthSuccess, submitToFlow, extractCSRFToken, completeSessionCoordination]);
  
  // Legacy AAL1 method - no longer supported with passwordless: false
  // WebAuthn is now a second factor only
  const authenticateAAL1 = useCallback(async (email, returnTo = '/dashboard') => {
    console.warn('🔐 AAL1 WebAuthn no longer supported - WebAuthn is now second factor only');
    setError('Passkey authentication requires email login first. Please use email code login.');
    return false;
  }, [setError]);
  
  // Check if WebAuthn is available for the user using Kratos session data
  const checkAvailability = useCallback(async () => {
    try {
      if (!window.PublicKeyCredential) {
        return { supported: false, configured: false, count: 0 };
      }
      
      // Use Kratos session data instead of custom API
      const sessionResponse = await fetch('/api/auth/me', { 
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!sessionResponse.ok) {
        return { supported: true, configured: false, count: 0 };
      }
      
      const sessionData = await sessionResponse.json();
      
      // Look for WebAuthn credentials in Kratos identity credentials
      const credentials = sessionData?.identity?.credentials || {};
      const webauthnCreds = credentials.webauthn || {};
      const identifiers = webauthnCreds.identifiers || [];
      
      const count = identifiers.length;
      
      return {
        supported: true,
        configured: count > 0,
        count
      };
    } catch (error) {
      console.error('🔐 Error checking WebAuthn availability:', error);
      return { supported: false, configured: false, count: 0 };
    }
  }, []);
  
  return {
    authenticateAAL1, // Legacy method (now shows warning)
    authenticateAAL2, // Main WebAuthn method for AAL2
    checkAvailability
  };
}