/**
 * HybridPasswordlessAuth - The ideal passwordless authentication system
 * 
 * Flow:
 * 1. Email + Code (Kratos) → AAL1 access
 * 2. For sensitive data → Custom WebAuthn with userVerification = AAL2
 * 3. TOTP fallback for devices without biometrics
 * 
 * This gives perfect UX: Touch ID for reports, email for quick login
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import axios from 'axios';

// Utility function to convert base64url to ArrayBuffer
const base64urlToArrayBuffer = (base64url) => {
  // Add padding if needed
  const padding = '='.repeat((4 - base64url.length % 4) % 4);
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
  
  // Decode base64 to binary string
  const binaryString = atob(base64);
  
  // Convert binary string to ArrayBuffer
  const buffer = new ArrayBuffer(binaryString.length);
  const view = new Uint8Array(buffer);
  
  for (let i = 0; i < binaryString.length; i++) {
    view[i] = binaryString.charCodeAt(i);
  }
  
  return buffer;
};

const HybridPasswordlessAuth = ({ mode = 'login' }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  
  // Flow state
  const [flowData, setFlowData] = useState(null);
  const [step, setStep] = useState('email');
  
  // Form data
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [totpCode, setTotpCode] = useState('');
  
  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [syncingProfile, setSyncingProfile] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  
  // WebAuthn capabilities
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [hasRegisteredPasskey, setHasRegisteredPasskey] = useState(false);
  
  // AAL detection
  const isAAL2 = searchParams.get('aal') === 'aal2';
  const returnTo = searchParams.get('return_to') || '/dashboard';

  /**
   * Check biometric capabilities and existing passkeys
   */
  const checkWebAuthnCapabilities = useCallback(async () => {
    try {
      // Check if WebAuthn is supported
      if (!window.PublicKeyCredential) {
        console.log('🔐 WebAuthn not supported');
        return;
      }
      
      // Check for platform authenticator (Touch ID/Face ID)
      const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      setBiometricAvailable(available);
      console.log('🔐 Biometric authenticator available:', available);
      
      // Check for existing passkeys for both AAL1 and AAL2 flows
      // The key is controlling WHEN AAL2 gets triggered, not whether we detect passkeys
      try {
        const response = await axios.get('/api/auth/me', { withCredentials: true });
        if (response.data?.authenticated && response.data?.has_passkey) {
          setHasRegisteredPasskey(response.data.has_passkey);
          console.log('🔐 User has passkey:', response.data.passkey_count);
        }
      } catch (e) {
        console.log('🔐 No active session to check passkeys');
        // Check localStorage for previous passkey usage
        const lastPasskeyUser = localStorage.getItem('sting_last_passkey_user');
        if (lastPasskeyUser) {
          console.log('🔐 Found previous passkey user in localStorage');
          setHasRegisteredPasskey(true);
        }
      }
    } catch (error) {
      console.error('🔐 Error checking WebAuthn capabilities:', error);
    }
  }, []);

  /**
   * Initialize Kratos flow for email/code
   */
  const initializeKratosFlow = useCallback(async () => {
    try {
      const kratosUrl = 'https://localhost:4433';
      const flowUrl = isAAL2 
        ? `${kratosUrl}/self-service/login/browser?aal=aal2`
        : `${kratosUrl}/self-service/login/browser?refresh=true`;
        
      const response = await axios.get(flowUrl, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      setFlowData(response.data);
      console.log('🔐 Kratos flow initialized:', response.data.id);
      return response.data;
    } catch (error) {
      console.error('🔐 Failed to initialize Kratos flow:', error);
      setError('Failed to initialize authentication. Please refresh and try again.');
      throw error;
    }
  }, [isAAL2]);

  /**
   * Check if email has passkeys registered (non-blocking)
   */
  const checkEmailPasskeys = useCallback(async (emailToCheck) => {
    try {
      console.log(`🔐 Checking passkeys for email: ${emailToCheck}`);
      // Use relative URL for proper proxy handling
      const response = await axios.post('/api/enhanced-webauthn/check-passkeys', {
        email: emailToCheck
      }, { withCredentials: true });
      
      console.log(`🔐 Passkey check response for ${emailToCheck}:`, response.data);
      
      if (response.data?.has_passkeys && response.data?.passkey_count > 0) {
        console.log(`🔐 Email ${emailToCheck} has ${response.data.passkey_count} registered passkeys`);
        setHasRegisteredPasskey(true);
        
        // Conservative approach: Only show biometric option if we can definitively
        // detect platform authenticator capability AND the user likely has it
        const hasPlatformCapability = await window.PublicKeyCredential?.isUserVerifyingPlatformAuthenticatorAvailable?.() || false;
        
        // For now, be conservative - only show biometric if platform capability exists
        // and user hasn't explicitly preferred TOTP
        const userPreference = localStorage.getItem('sting-aal2-preference');
        const shouldShowBiometric = hasPlatformCapability && userPreference !== 'totp';
        
        console.log(`🔐 Platform capability: ${hasPlatformCapability}, User preference: ${userPreference}, Show biometric: ${shouldShowBiometric}`);
        setBiometricAvailable(shouldShowBiometric);
        
        return true;
      } else {
        console.log(`🔐 Email ${emailToCheck} has no registered passkeys`);
        setBiometricAvailable(false);
        setHasRegisteredPasskey(false);
        return false;
      }
    } catch (error) {
      console.log('🔐 Error checking email passkeys or endpoint not available:', error.message);
      setHasRegisteredPasskey(false);
      return false;
    }
  }, []);

  /**
   * Email change handler with smart passkey checking
   */
  const handleEmailChange = useCallback((newEmail) => {
    setEmail(newEmail);
    
    // Reset passkey state when email changes
    setHasRegisteredPasskey(false);
    
    // Clear any existing timeout
    if (window.passkeyCheckTimeout) {
      clearTimeout(window.passkeyCheckTimeout);
    }
    
    // Check for passkeys after user stops typing (for both AAL1 and AAL2)
    // This enables AAL1 passkey login while preventing AAL2 auto-trigger after email codes
    if (newEmail && newEmail.includes('@') && newEmail.length > 5) {
      // Immediate check for known test email
      if (newEmail === 'user@sting.local') {
        console.log('🔐 Known test email - checking passkeys immediately');
        checkEmailPasskeys(newEmail);
        return;
      }
      
      // Set timeout for other emails
      window.passkeyCheckTimeout = setTimeout(() => {
        console.log('🔐 Checking passkeys for:', newEmail);
        checkEmailPasskeys(newEmail);
      }, 1000); // Wait 1 second after user stops typing
    }
  }, [checkEmailPasskeys]);

  /**
   * Handle email submission for code-based auth (AAL1)
   * Uses two-step approach for identifier_first style
   */
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      // Step 1: Initialize fresh Kratos flow
      console.log('🔐 Initializing fresh Kratos flow for email submission...');
      const flow = await initializeKratosFlow();
      setFlowData(flow);
      
      // Step 2: Use the PROVEN working pattern from EnhancedKratosLogin
      console.log('🔐 Using proven working email code pattern...');
      
      // Check for code submission capability (working pattern)
      const codeSubmitButton = flow.ui.nodes.find(n => 
        n.attributes?.name === 'method' && n.attributes?.value === 'code'
      );
      const hasCodeInputField = flow.ui.nodes.some(n => 
        n.attributes?.name === 'code' && n.attributes?.type === 'text'
      );
      
      console.log('🔐 Code submit button found:', !!codeSubmitButton);
      console.log('🔐 Has code input field:', hasCodeInputField);
      
      // Apply the working pattern: auto-submit code method if we have button but no input field
      if (codeSubmitButton && !hasCodeInputField) {
        console.log('🔐 Auto-submitting code method to trigger email sending (proven pattern)...');
        
        const csrfToken = flow.ui.nodes.find(
          n => n.attributes?.name === 'csrf_token'
        )?.attributes?.value;
        
        const params = new URLSearchParams();
        params.append('identifier', email);
        params.append('method', 'code');
        if (csrfToken) {
          params.append('csrf_token', csrfToken);
        }
        
        const submitResponse = await axios.post(
          flow.ui.action,
          params.toString(),
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'Accept': 'application/json'
            },
            withCredentials: true,
            validateStatus: () => true
          }
        );
        
        console.log('🔐 Auto-submit response:', submitResponse.status, submitResponse.data?.state);
        
        if (submitResponse.data?.ui) {
          console.log('🔐 Email code auto-submit successful - updating flow!');
          setFlowData(submitResponse.data);
          setStep('code');
          setSuccessMessage('Check your email for the verification code');
          // Clear passkey state when transitioning to code entry to prevent UI conflicts
          setHasRegisteredPasskey(false);
          return;
        } else {
          console.log('🔐 Auto-submit response data:', submitResponse.data);
        }
      }
      
      // Fallback: Try identifier-first approach if auto-submit didn't work
      console.log('🔐 Trying identifier-first fallback approach...');
      
      const identifierFormData = new URLSearchParams();
      identifierFormData.append('identifier', email);
      
      const csrfToken = flow.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        identifierFormData.append('csrf_token', csrfToken);
      }
      
      const identifierResponse = await axios.post(
        flow.ui.action,
        identifierFormData.toString(),
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      console.log('🔐 Fallback identifier response:', identifierResponse.status, identifierResponse.data?.state);
      
      // Check if this gives us code method
      const updatedFlow = identifierResponse.data;
      const codeMethod = updatedFlow?.ui?.nodes?.find(
        n => n.attributes?.name === 'method' && n.attributes?.value === 'code'
      );
      
      if (codeMethod) {
        console.log('🔐 Code method found in fallback, submitting...');
        
        const codeFormData = new URLSearchParams();
        codeFormData.append('identifier', email);
        codeFormData.append('method', 'code');
        
        const updatedCsrfToken = updatedFlow.ui.nodes.find(
          n => n.attributes?.name === 'csrf_token'
        )?.attributes?.value;
        if (updatedCsrfToken) {
          codeFormData.append('csrf_token', updatedCsrfToken);
        }
        
        const codeResponse = await axios.post(
          updatedFlow.ui.action,
          codeFormData.toString(),
          {
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            withCredentials: true,
            validateStatus: () => true
          }
        );
        
        console.log('🔐 Fallback code response:', codeResponse.status, codeResponse.data?.state);
        
        if (codeResponse.data?.ui) {
          setFlowData(codeResponse.data);
          setStep('code');
          setSuccessMessage('Check your email for the verification code');
          // Clear passkey state when transitioning to code entry to prevent UI conflicts
          setHasRegisteredPasskey(false);
          return;
        }
      }
      
      // Handle cases where neither approach worked
      if (identifierResponse?.status === 400 && identifierResponse.data?.state === 'choose_method') {
        console.log('🔐 In choose_method state, checking available options...');
        
        // Check if WebAuthn is the only available option
        const webauthnMethod = updatedFlow?.ui?.nodes?.find(
          n => n.attributes?.name === 'method' && n.attributes?.value === 'webauthn'
        );
        
        if (webauthnMethod && !codeMethod) {
          // IMPORTANT: Check actual passkey count, not just WebAuthn method presence
          console.log('🔐 WebAuthn method available but no code method. Checking actual passkey count...');
          
          // Use our passkey detection API to verify if user actually has passkeys
          try {
            const passkeyCheck = await checkEmailPasskeys(email);
            if (passkeyCheck) {
              console.warn('🔐 User actually has passkeys configured');
              setError('This account has passkeys configured. Please use "Sign in with Touch ID" above for better security.');
              // Force UI to update to show passkey options
              setHasRegisteredPasskey(true);
              // Reset step to show the updated UI with passkey button
              setStep('email');
              return; // Exit the email submission flow
            } else {
              console.warn('🔐 User has NO passkeys but email codes not available - new account needs registration flow');
              console.log('🔐 Redirecting to registration for new user:', email);
              // Store email in sessionStorage so registration page can pre-fill it
              sessionStorage.setItem('register_email', email);
              window.location.href = '/register';
              return;
            }
          } catch (passkeyCheckError) {
            console.error('🔐 Error checking passkeys:', passkeyCheckError);
            setError('Unable to determine authentication options. Please try again or contact support.');
          }
        } else {
          console.error('🔐 No suitable authentication methods available');
          setError('Email authentication is not available for this account. Please try using passkey authentication.');
        }
      } else {
        console.error('🔐 Email code flow failed completely');
        setError('Failed to set up email authentication. Please try again or use passkey authentication.');
      }
      
    } catch (error) {
      console.error('🔐 Email submission failed:', error);
      setError('Failed to send verification code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle code verification (AAL1 completion)
   */
  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    if (!code || !flowData) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const formData = new URLSearchParams();
      formData.append('code', code);
      formData.append('method', 'code');
      formData.append('identifier', email);
      
      const csrfToken = flowData.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(
        flowData.ui.action,
        formData.toString(),
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      if (response.status === 200 || response.data?.state === 'passed_challenge') {
        // AAL1 authentication successful
        console.log('🔐 Email code authentication successful!');
        
        // Clear any passkey state to prevent auto-triggering AAL2
        setHasRegisteredPasskey(false);
        
        // Notify UnifiedAuthProvider about successful authentication
        console.log('🔐 Dispatching auth success event for UnifiedAuthProvider');
        window.dispatchEvent(new CustomEvent('sting-auth-success', {
          detail: { method: 'email_code', aalLevel: 'aal1' }
        }));
        
        // Mark recent authentication for dashboard access
        const authTimestamp = Date.now().toString();
        sessionStorage.setItem('sting_recent_auth', authTimestamp);
        console.log('🔐 Setting sessionStorage sting_recent_auth:', authTimestamp);
        
        if (isAAL2) {
          // Check user preference or available methods for smart AAL2 routing
          const userAAL2Preference = localStorage.getItem('sting-aal2-preference');
          
          if (userAAL2Preference === 'totp') {
            console.log('🔐 User prefers TOTP for AAL2, going directly to TOTP');
            setStep('totp');
          } else if (userAAL2Preference === 'biometric' || userAAL2Preference === 'hardware') {
            console.log(`🔐 User prefers ${userAAL2Preference} for AAL2, triggering passkey flow`);
            handleBiometricAAL2();
          } else {
            // Need AAL2 for sensitive data - show choice
            setStep('aal2-choice');
          }
        } else {
          // Regular dashboard access - redirect immediately to prevent UI state issues
          console.log('🔐 AAL1 login complete, redirecting to dashboard');
          // Use setTimeout to ensure state updates are processed before redirect
          setTimeout(() => {
            window.location.href = returnTo;
          }, 100); // Very short delay to ensure state clears
        }
      } else if (response.status === 422 && response.data?.redirect_browser_to) {
        // AAL2 required by Kratos
        setStep('aal2-choice');
      } else {
        console.log('🔐 Unexpected response:', response.status, response.data);
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid verification code. Please try again.');
      }
    } catch (error) {
      console.error('🔐 Code verification failed:', error);
      setError('Verification failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle custom WebAuthn AAL1 authentication (regular passwordless login)
   */
  const handleBiometricAAL1 = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      console.log('🔐 Starting AAL1 WebAuthn authentication...');
      
      // Step 1: Begin authentication with our enhanced endpoint
      // Use relative URL for proper proxy handling
      const beginResponse = await axios.post('/api/enhanced-webauthn/authentication/begin', {
        username: email,
        aal_level: 'aal1'  // Custom flag for AAL1 (regular passwordless login)
      }, { withCredentials: true });
      
      if (!beginResponse.data) {
        throw new Error('Failed to get authentication challenge');
      }
      
      // Step 2: Perform WebAuthn ceremony with user verification preferred (not required for AAL1)
      console.log('🔐 WebAuthn options received:', beginResponse.data);
      
      // Extract the publicKey options from the response
      const webauthnOptions = beginResponse.data.publicKey;
      if (!webauthnOptions || !webauthnOptions.challenge) {
        throw new Error('Invalid WebAuthn options received from server');
      }
      
      // Convert base64url strings to ArrayBuffers for WebAuthn API
      const processedOptions = {
        ...webauthnOptions,
        challenge: base64urlToArrayBuffer(webauthnOptions.challenge),
        allowCredentials: webauthnOptions.allowCredentials?.map(cred => {
          // Validate credential object before accessing properties
          if (!cred || !cred.id) {
            throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
          }
          return {
            ...cred,
            id: base64urlToArrayBuffer(cred.id)
          };
        }) || [],
        userVerification: 'preferred',  // AAL1: biometric preferred but not required
        timeout: 60000
      };
      
      console.log('🔐 Processed WebAuthn options:', processedOptions);
      
      const credential = await navigator.credentials.get({
        publicKey: processedOptions
      });
      
      if (!credential) {
        throw new Error('Authentication was cancelled');
      }

      // Additional validation for credential properties
      if (!credential.id || !credential.rawId || !credential.response) {
        console.error('🔐 Invalid credential object received:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      console.log('🔐 WebAuthn credential obtained, verifying...');
      
      // Step 3: Complete authentication and mark as AAL1
      const completeResponse = await axios.post('/api/enhanced-webauthn/authentication/complete', {
        credential: {
          id: credential.id,
          rawId: Array.from(new Uint8Array(credential.rawId)),
          type: credential.type,
          response: {
            authenticatorData: Array.from(new Uint8Array(credential.response.authenticatorData)),
            clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON)),
            signature: Array.from(new Uint8Array(credential.response.signature)),
            userHandle: credential.response.userHandle ? 
              Array.from(new Uint8Array(credential.response.userHandle)) : null
          }
        },
        challenge_id: beginResponse.data.challenge_id,  // Use challenge_id from begin response
        aal_level: 'aal1'  // Mark this session as AAL1
      }, { withCredentials: true });
      
      console.log('🔐 Complete response status:', completeResponse.status);
      console.log('🔐 Complete response data:', completeResponse.data);
      
      if (completeResponse.data?.verified) {
        console.log('🔐 AAL1 passkey authentication successful!');
        // Store successful passkey usage for future login hint
        localStorage.setItem('sting_last_passkey_user', email);
        
        // Use backend-specified delay or fallback to 500ms
        const redirectDelay = completeResponse.data?.redirect_delay_ms || 500;
        const kratosSessionCreated = completeResponse.data?.kratos_session_created || false;
        
        console.log(`🔐 Kratos session created: ${kratosSessionCreated}`);
        console.log(`🔐 Redirecting to dashboard in ${redirectDelay}ms...`);
        
        // Notify UnifiedAuthProvider about successful authentication
        console.log('🔐 Dispatching auth success event for UnifiedAuthProvider');
        window.dispatchEvent(new CustomEvent('sting-auth-success', {
          detail: { method: 'webauthn', kratosSessionCreated, aalLevel: 'aal1' }
        }));
        
        // Mark recent authentication for dashboard access
        const authTimestamp = Date.now().toString();
        sessionStorage.setItem('sting_recent_auth', authTimestamp);
        console.log('🔐 Setting sessionStorage sting_recent_auth:', authTimestamp);
        
        setTimeout(() => {
          window.location.href = returnTo;
        }, redirectDelay);
      } else {
        console.error('🔐 Authentication verification failed:', completeResponse.data);
        throw new Error(completeResponse.data?.error || 'Authentication verification failed');
      }
    } catch (error) {
      console.error('🔐 AAL1 passkey authentication failed:', error);
      if (error.name === 'NotAllowedError') {
        setError('Authentication was cancelled or failed. Please try again.');
      } else {
        setError(`Passkey authentication failed: ${error.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Poll sync status until completion
   * Used to show loading window until profile sync is confirmed
   */
  const checkSyncCompletion = async () => {
    const maxAttempts = 10; // Poll for up to 10 seconds
    const pollInterval = 1000; // Check every second
    let attempts = 0;

    const pollSyncStatus = async () => {
      try {
        attempts++;
        console.log(`🔄 Checking sync status (attempt ${attempts}/${maxAttempts})`);

        const response = await axios.get('/api/enhanced-webauthn/sync-status', {
          withCredentials: true
        });

        if (response.data?.success) {
          const status = response.data.status;
          const isHealthy = status?.sync_health?.healthy;
          const lastSyncSuccess = status?.sync_health?.last_sync_success;

          console.log(`🔄 Sync status check: healthy=${isHealthy}, last_success=${lastSyncSuccess}`);

          // Update UI with sync progress
          if (isHealthy && lastSyncSuccess) {
            setSyncStatus('Sync completed successfully!');
            setSyncingProfile(false);
            setSuccessMessage('🔐 Authentication successful! ✅ Profile synchronized');
            return true; // Sync completed
          } else if (attempts < maxAttempts) {
            setSyncStatus(`Synchronizing... (${attempts}/${maxAttempts})`);
            // Continue polling
            setTimeout(pollSyncStatus, pollInterval);
            return false;
          } else {
            // Max attempts reached
            setSyncStatus('Sync taking longer than expected');
            setSyncingProfile(false);
            setSuccessMessage('🔐 Authentication successful! (Sync may still be in progress)');
            return true; // Stop polling but don't fail auth
          }
        } else {
          // API error
          if (attempts < maxAttempts) {
            console.warn(`🔄 Sync status check failed, retrying... (${attempts}/${maxAttempts})`);
            setTimeout(pollSyncStatus, pollInterval);
            return false;
          } else {
            setSyncStatus('Unable to confirm sync status');
            setSyncingProfile(false);
            setSuccessMessage('🔐 Authentication successful! (Sync status unknown)');
            return true;
          }
        }
      } catch (error) {
        console.error(`🔄 Sync status polling error (attempt ${attempts}):`, error);
        
        if (attempts < maxAttempts) {
          setTimeout(pollSyncStatus, pollInterval);
          return false;
        } else {
          setSyncStatus('Sync status check failed');
          setSyncingProfile(false);
          setSuccessMessage('🔐 Authentication successful! (Sync status unavailable)');
          return true;
        }
      }
    };

    // Start polling
    await pollSyncStatus();
  };

  /**
   * Handle custom WebAuthn AAL2 authentication (for sensitive operations)
   */
  const handleBiometricAAL2 = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      console.log('🔐 Starting custom WebAuthn AAL2 authentication...');
      
      // Step 1: Begin authentication with our enhanced endpoint
      // Use relative URL for proper proxy handling
      const beginResponse = await axios.post('/api/enhanced-webauthn/authentication/begin', {
        username: email,
        aal_level: 'aal2'  // Custom flag for AAL2
      }, { withCredentials: true });
      
      if (!beginResponse.data) {
        throw new Error('Failed to get authentication challenge');
      }
      
      // Step 2: Perform WebAuthn ceremony with user verification required
      console.log('🔐 WebAuthn options received:', beginResponse.data);
      
      // Extract the publicKey options from the response
      const webauthnOptions = beginResponse.data.publicKey;
      if (!webauthnOptions || !webauthnOptions.challenge) {
        throw new Error('Invalid WebAuthn options received from server');
      }
      
      // Convert base64url strings to ArrayBuffers for WebAuthn API
      const processedOptions = {
        ...webauthnOptions,
        challenge: base64urlToArrayBuffer(webauthnOptions.challenge),
        allowCredentials: webauthnOptions.allowCredentials?.map(cred => {
          // Validate credential object before accessing properties
          if (!cred || !cred.id) {
            throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
          }
          return {
            ...cred,
            id: base64urlToArrayBuffer(cred.id)
          };
        }) || [],
        userVerification: 'required',  // CRITICAL: Forces biometric/PIN
        timeout: 60000
      };
      
      console.log('🔐 Processed WebAuthn options:', processedOptions);
      
      const credential = await navigator.credentials.get({
        publicKey: processedOptions
      });
      
      if (!credential) {
        throw new Error('Authentication was cancelled');
      }

      // Additional validation for credential properties
      if (!credential.id || !credential.rawId || !credential.response) {
        console.error('🔐 Invalid credential object received:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      console.log('🔐 WebAuthn credential obtained, verifying...');
      
      // Step 3: Complete authentication and mark as AAL2
      const completeResponse = await axios.post('/api/enhanced-webauthn/authentication/complete', {
        credential: {
          id: credential.id,
          rawId: Array.from(new Uint8Array(credential.rawId)),
          type: credential.type,
          response: {
            authenticatorData: Array.from(new Uint8Array(credential.response.authenticatorData)),
            clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON)),
            signature: Array.from(new Uint8Array(credential.response.signature)),
            userHandle: credential.response.userHandle ? 
              Array.from(new Uint8Array(credential.response.userHandle)) : null
          }
        },
        challenge_id: beginResponse.data.challenge_id,  // Use challenge_id from begin response
        aal_level: 'aal2'  // Mark this session as AAL2
      }, { withCredentials: true });
      
      console.log('🔐 Complete response status:', completeResponse.status);
      console.log('🔐 Complete response data:', completeResponse.data);
      
      if (completeResponse.data?.verified) {
        console.log('🔐 AAL2 biometric authentication successful!');
        // Store successful passkey usage for future login hint
        localStorage.setItem('sting_last_passkey_user', email);
        
        // Handle profile sync status
        const redirectDelay = completeResponse.data?.redirect_delay_ms || 500;
        const kratosSessionCreated = completeResponse.data?.kratos_session_created || false;
        const profileSyncStatus = completeResponse.data?.profile_sync_status;
        const profileSyncDetails = completeResponse.data?.profile_sync_details;
        
        console.log(`🔐 Kratos session created: ${kratosSessionCreated}`);
        console.log(`🔄 Profile sync status: ${profileSyncStatus}`, profileSyncDetails);
        console.log(`🔐 Redirecting to dashboard in ${redirectDelay}ms...`);
        
        // Show sync status to user
        if (profileSyncStatus === 'triggered') {
          setSyncingProfile(true);
          setSyncStatus('Synchronizing profile...');
          setSuccessMessage('🔐 Authentication successful! 🔄 Finalizing sync...');
          
          // Start checking sync status
          checkSyncCompletion();
        } else if (profileSyncStatus === 'error') {
          setSuccessMessage('🔐 Authentication successful! (Profile sync pending)');
        } else {
          setSuccessMessage('🔐 Authentication successful!');
        }
        
        // Notify UnifiedAuthProvider about successful authentication
        console.log('🔐 Dispatching auth success event for UnifiedAuthProvider');
        window.dispatchEvent(new CustomEvent('sting-auth-success', {
          detail: { method: 'webauthn', kratosSessionCreated }
        }));
        
        // Mark recent authentication for dashboard access
        const authTimestamp = Date.now().toString();
        sessionStorage.setItem('sting_recent_auth', authTimestamp);
        console.log('🔐 Setting sessionStorage sting_recent_auth:', authTimestamp);
        
        setTimeout(() => {
          window.location.href = returnTo;
        }, redirectDelay);
      } else {
        console.error('🔐 Authentication verification failed:', completeResponse.data);
        throw new Error(completeResponse.data?.error || 'Authentication verification failed');
      }
    } catch (error) {
      console.error('🔐 Biometric AAL2 failed:', error);
      if (error.name === 'NotAllowedError') {
        setError('Authentication was cancelled or failed. Please try again.');
      } else {
        setError(`Biometric authentication failed: ${error.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle TOTP AAL2 (fallback)
   */
  const handleTOTPSubmit = async (e) => {
    e.preventDefault();
    if (!totpCode) return;
    
    // Use existing Kratos TOTP flow
    setIsLoading(true);
    setError('');
    
    try {
      // Initialize TOTP flow
      const kratosUrl = 'https://localhost:4433';
      const flowResponse = await axios.get(`${kratosUrl}/self-service/login/browser?aal=aal2`, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      const formData = new URLSearchParams();
      formData.append('totp_code', totpCode);
      formData.append('method', 'totp');
      
      const csrfToken = flowResponse.data.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(
        flowResponse.data.ui.action,
        formData.toString(),
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      if (response.status === 200 || response.data?.state === 'passed_challenge') {
        console.log('🔐 TOTP AAL2 authentication successful!');
        
        // Notify UnifiedAuthProvider about successful authentication
        console.log('🔐 Dispatching auth success event for UnifiedAuthProvider');
        window.dispatchEvent(new CustomEvent('sting-auth-success', {
          detail: { method: 'totp', aalLevel: 'aal2' }
        }));
        
        // Mark recent authentication for dashboard access
        const authTimestamp = Date.now().toString();
        sessionStorage.setItem('sting_recent_auth', authTimestamp);
        console.log('🔐 Setting sessionStorage sting_recent_auth:', authTimestamp);
        
        window.location.href = returnTo;
      } else {
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid TOTP code. Please try again.');
      }
    } catch (error) {
      console.error('🔐 TOTP verification failed:', error);
      setError('TOTP verification failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Initialize on mount
  useEffect(() => {
    const initialize = async () => {
      try {
        // Check for registration success message
        const locationState = location.state;
        if (locationState?.registrationSuccess) {
          setSuccessMessage(locationState.message || 'Registration successful! Sign in with your passkey.');
          if (locationState.email) {
            setEmail(locationState.email);
          }
          // Clear the state to prevent showing message on refresh
          navigate(location.pathname, { replace: true });
        }
        
        await checkWebAuthnCapabilities();
        
        if (isAAL2) {
          // For AAL2 requests, check if user has biometric auth available
          setStep('aal2-choice');
        } else {
          // Regular login, start with email - don't initialize Kratos flow immediately
          setStep('email');
        }
      } catch (error) {
        console.error('🔐 Initialization error:', error);
        setError('Failed to initialize. Please refresh and try again.');
      }
    };
    
    initialize();
  }, [isAAL2, checkWebAuthnCapabilities]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isAAL2 ? 'Secure Access Required' : 'Welcome to STING'}
          </h1>
          <p className="text-gray-300">
            {isAAL2 
              ? 'Additional verification needed for sensitive data'
              : 'Sign in to continue'
            }
          </p>
        </div>

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

        {/* Profile Sync Status */}
        {syncingProfile && syncStatus && (
          <div className="sting-glass-subtle border border-blue-500/50 text-blue-200 px-4 py-3 rounded-lg mb-6">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400 mr-3"></div>
              {syncStatus}
            </div>
          </div>
        )}

        {/* Email Step (AAL1) */}
        {step === 'email' && (
          <>
            {/* Quick Passkey/External Authenticator Login - show if user has passkeys */}
            {hasRegisteredPasskey && email && (
              <div className="mb-6">
                <div className="sting-glass-subtle border border-green-500/50 rounded-lg p-3 mb-3">
                  <p className="text-green-300 text-sm text-center">
                    ✅ Secure passkey authentication available for {email}
                  </p>
                </div>
                <button
                  onClick={isAAL2 ? handleBiometricAAL2 : handleBiometricAAL1}
                  disabled={isLoading || !email}
                  className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold py-4 px-4 rounded-lg transition duration-200 flex items-center justify-center text-lg"
                >
                  <span className="mr-3 text-2xl">
                    {biometricAvailable ? (navigator.platform.includes('Mac') ? '👆' : '🔐') : '🔑'}
                  </span>
                  <div className="text-left">
                    <div className="font-semibold">
                      {biometricAvailable 
                        ? `Sign in with ${navigator.platform.includes('Mac') ? 'Touch ID' : 'Biometric'}`
                        : 'Sign in with Security Key'
                      }
                    </div>
                    <div className="text-sm opacity-90">
                      {biometricAvailable ? 'Recommended for your account' : 'External authenticator or YubiKey'}
                    </div>
                  </div>
                </button>
                
                {/* Add TOTP option for AAL2 fallback */}
                <div className="mt-3">
                  <button
                    onClick={() => setStep('totp')}
                    className="w-full bg-amber-600 hover:bg-amber-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
                  >
                    📱 Use TOTP App Instead
                  </button>
                </div>
                
                <div className="text-center text-gray-400 text-sm mt-3">
                  <button 
                    type="button"
                    onClick={() => setStep('email-fallback')}
                    className="text-gray-400 hover:text-gray-300 underline"
                  >
                    Or use email code (AAL1 only)
                  </button>
                </div>
              </div>
            )}

            {/* Show hint when no email but has passkey capability */}
            {hasRegisteredPasskey && biometricAvailable && !email && (
              <div className="mb-6">
                <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-3">
                  <p className="text-blue-300 text-sm text-center">
                    💡 Enter your email first to enable passkey authentication
                  </p>
                </div>
              </div>
            )}

            {/* Show email form - always show unless user has passkey AND email filled */}
            {!(hasRegisteredPasskey && biometricAvailable && email) && (
              <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => handleEmailChange(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                  placeholder="you@example.com"
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !email}
                className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
              >
                {isLoading ? 'Sending...' : 'Continue with Email'}
              </button>
            </form>
            )}
          </>
        )}

        {/* Email Fallback Step - for users with passkeys who want to use email */}
        {step === 'email-fallback' && (
          <>
            <div className="sting-glass-subtle border border-amber-500/50 rounded-lg p-4 mb-6">
              <p className="text-amber-300 text-sm">
                ⚠️ <strong>Security Notice:</strong> You have secure passkey authentication available. 
                Email codes are less secure than passkeys.
              </p>
              <button
                onClick={() => setStep('email')}
                className="text-amber-300 hover:text-amber-200 underline text-sm mt-2"
              >
                ← Back to secure passkey login
              </button>
            </div>

            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => handleEmailChange(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                  placeholder="you@example.com"
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !email}
                className="w-full bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
              >
                {isLoading ? 'Sending...' : 'Send Email Code (Less Secure)'}
              </button>
            </form>
          </>
        )}

        {/* Code Verification Step (AAL1) */}
        {step === 'code' && (
          <form onSubmit={handleCodeSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Verification Code
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 text-center text-2xl tracking-widest"
                placeholder="000000"
                maxLength="6"
                required
                disabled={isLoading}
                autoFocus
              />
              <p className="text-gray-400 text-sm mt-2 text-center">
                Check your email for the 6-digit code
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || code.length < 6}
              className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Verifying...' : 'Verify & Continue'}
            </button>

            <button
              type="button"
              onClick={() => setStep('email')}
              className="w-full text-gray-400 hover:text-white text-sm"
            >
              ← Back to email
            </button>
          </form>
        )}

        {/* AAL2 Choice Step */}
        {step === 'aal2-choice' && (
          <div className="space-y-6">
            <div className="sting-glass-subtle border border-amber-500/50 rounded-lg p-4">
              <p className="text-amber-300 text-sm">
                🔐 You're accessing sensitive data that requires additional security verification.
              </p>
              <p className="text-gray-400 text-xs mt-2">
                Choose your preferred second factor: biometric (Touch ID/Face ID) or authenticator app (TOTP)
              </p>
            </div>

            {/* Biometric Option */}
            {biometricAvailable && (
              <button
                onClick={() => {
                  // Save user preference for future AAL2 flows
                  localStorage.setItem('sting-aal2-preference', 'biometric');
                  handleBiometricAAL2();
                }}
                disabled={isLoading}
                className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-4 px-4 rounded-lg transition duration-200 flex items-center justify-center"
              >
                <span className="mr-3 text-2xl">
                  {navigator.platform.includes('Mac') ? '👆' : '🔐'}
                </span>
                <div className="text-left">
                  <div className="font-semibold">
                    {navigator.platform.includes('Mac') ? 'Touch ID' : 'Biometric Authentication'}
                  </div>
                  <div className="text-sm opacity-80">
                    Use your fingerprint or face recognition
                  </div>
                </div>
              </button>
            )}

            {/* Authentication Options */}
            <div className="space-y-3">
              <button
                onClick={() => {
                  // Save user preference for future AAL2 flows
                  localStorage.setItem('sting-aal2-preference', 'totp');
                  setStep('totp');
                }}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
              >
                Use Authenticator App
              </button>
              
              {/* Hardware Key Option (if biometric not available but has passkeys) */}
              {!biometricAvailable && hasRegisteredPasskey && (
                <button
                  onClick={() => {
                    // Save user preference and try hardware passkey
                    localStorage.setItem('sting-aal2-preference', 'hardware');
                    handleBiometricAAL2();
                  }}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center"
                >
                  <span className="mr-3 text-xl">🔑</span>
                  <div className="text-left">
                    <div className="font-semibold">Use Hardware Key</div>
                    <div className="text-sm opacity-80">YubiKey or other external authenticator</div>
                  </div>
                </button>
              )}
              
              <div className="flex space-x-4">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="flex-1 text-gray-400 hover:text-white text-sm"
                >
                  Cancel (return to dashboard)
                </button>
                <button
                  onClick={() => {
                    localStorage.removeItem('sting-aal2-preference');
                    // Also reset biometric availability to re-detect
                    setBiometricAvailable(false);
                    console.log('🔐 AAL2 preference reset');
                  }}
                  className="text-gray-500 hover:text-gray-300 text-xs"
                  title="Reset saved preference and re-detect capabilities"
                >
                  Reset Choice
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TOTP Step */}
        {step === 'totp' && (
          <form onSubmit={handleTOTPSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Authenticator Code
              </label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 text-center text-2xl tracking-widest"
                placeholder="000000"
                maxLength="6"
                required
                disabled={isLoading}
                autoFocus
              />
              <p className="text-gray-400 text-sm mt-2 text-center">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || totpCode.length < 6}
              className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Verifying...' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={() => setStep('aal2-choice')}
              className="w-full text-gray-400 hover:text-white text-sm"
            >
              ← Back to security options
            </button>
          </form>
        )}

        {/* Registration Link */}
        {!isAAL2 && (
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Don't have an account?{' '}
              <button
                onClick={() => navigate('/register')}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign up here
              </button>
            </p>
          </div>
        )}

        {/* Dev Mode Helper */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs">
              📧 Dev: Check{' '}
              <a href="http://localhost:8026" target="_blank" rel="noopener noreferrer" className="underline">
                Mailpit
              </a>{' '}
              for emails
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HybridPasswordlessAuth;