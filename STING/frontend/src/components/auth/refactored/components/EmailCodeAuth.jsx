import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthProvider';
import { useKratosFlow } from '../hooks/useKratosFlow';
import { useSessionCoordination } from '../hooks/useSessionCoordination';

const EmailCodeAuth = ({ onSwitchToPasskey, onSuccess }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('email'); // 'email' or 'code'
  const [code, setCode] = useState('');
  
  const {
    userEmail,
    setUserEmail,
    isLoading,
    setLoading,
    error,
    setError,
    successMessage,
    setSuccessMessage,
    clearMessages,
    flowData,
    setFlowData,
    hasRegisteredPasskey,
    checkEmailPasskeys,
    dispatchAuthSuccess,
    cacheCurrentCredentials
  } = useAuth();
  
  const { initializeFlow, submitToFlow, processContinueWith, extractCSRFToken } = useKratosFlow();
  const { completeSessionCoordination } = useSessionCoordination();
  
  const isAAL2 = searchParams.get('aal') === 'aal2';
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // 🔍 DEBUG: Track component mounting and updates
  useEffect(() => {
    console.log('🔍 EmailCodeAuth mounted/updated:', {
      step,
      hasUserEmail: !!userEmail,
      userEmailLength: userEmail?.length,
      hasCode: !!code,
      codeLength: code?.length,
      hasFlowData: !!flowData,
      flowId: flowData?.id,
      isLoading,
      isAAL2,
      returnTo,
      timestamp: new Date().toISOString()
    });
  }, [step, userEmail, code, flowData, isLoading, isAAL2, returnTo]);
  
  // Handle email input with debounced passkey checking
  const handleEmailChange = useCallback((newEmail) => {
    setUserEmail(newEmail);
    
    // Clear any existing timeout
    if (window.passkeyCheckTimeout) {
      clearTimeout(window.passkeyCheckTimeout);
    }
    
    // Check for passkeys after user stops typing
    if (newEmail && newEmail.includes('@') && newEmail.length > 5) {
      // Quick check for known test emails
      if (newEmail === 'user@sting.local' || newEmail === 'admin@sting.local') {
        console.log('🔐 Known test email - checking passkeys immediately');
        checkEmailPasskeys(newEmail);
        return;
      }
      
      // Debounced check for other emails
      window.passkeyCheckTimeout = setTimeout(() => {
        console.log('🔐 Checking passkeys for:', newEmail);
        checkEmailPasskeys(newEmail);
      }, 2000);
    }
  }, [setUserEmail, checkEmailPasskeys]);
  
  // Handle email submission
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!userEmail) return;
    
    setLoading(true);
    clearMessages();
    
    try {
      console.log('🔐 Starting email code flow for:', userEmail);
      
      // Initialize fresh Kratos flow
      const flow = await initializeFlow(isAAL2);
      
      // Use identifier-first approach
      const identifierFormData = new URLSearchParams();
      identifierFormData.append('identifier', userEmail);
      
      const csrfToken = extractCSRFToken(flow);
      if (csrfToken) {
        identifierFormData.append('csrf_token', csrfToken);
      }
      
      // Submit identifier
      const identifierResponse = await submitToFlow(flow, identifierFormData.toString());
      
      console.log('🔐 Identifier response:', identifierResponse.status, identifierResponse.data?.state);
      
      // Check if we can proceed with code method
      const updatedFlow = identifierResponse.data;
      const hasCodeMethod = updatedFlow?.ui?.nodes?.some(
        n => n.attributes?.name === 'method' && n.attributes?.value === 'code'
      );
      
      if (hasCodeMethod) {
        console.log('🔐 Code method available, requesting code...');
        
        const codeFormData = new URLSearchParams();
        codeFormData.append('identifier', userEmail);
        codeFormData.append('method', 'code');
        
        const updatedCsrfToken = extractCSRFToken(updatedFlow);
        if (updatedCsrfToken) {
          codeFormData.append('csrf_token', updatedCsrfToken);
        }
        
        const codeResponse = await submitToFlow(updatedFlow, codeFormData.toString());
        
        console.log('🔐 Code request response:', codeResponse.status, codeResponse.data?.state);
        
        if (codeResponse.data?.state === 'sent_email' || codeResponse.data?.ui) {
          console.log('✅ Email sent successfully');
          setFlowData(codeResponse.data);
          setStep('code');
          setSuccessMessage('A verification code has been sent to your email address.');
        } else {
          throw new Error('Failed to send verification code');
        }
      } else {
        // Check if user has passkeys but no code method
        const hasWebAuthnMethod = updatedFlow?.ui?.nodes?.some(
          n => n.attributes?.name === 'method' && n.attributes?.value === 'webauthn'
        );
        
        if (hasWebAuthnMethod && !hasCodeMethod) {
          // Check actual passkey count
          const hasPasskeys = await checkEmailPasskeys(userEmail);
          if (hasPasskeys) {
            setError('This account has passkeys configured. Please use passkey authentication for better security.');
            // Suggest switching to passkey
            if (onSwitchToPasskey) {
              setTimeout(() => onSwitchToPasskey(), 2000);
            }
            return;
          } else {
            // New user needs registration
            console.log('🔐 New user needs registration');
            sessionStorage.setItem('register_email', userEmail);
            navigate('/register');
            return;
          }
        } else {
          setError('Email authentication is not available for this account. Please try using passkey authentication.');
        }
      }
    } catch (error) {
      console.error('🔐 Email submission failed:', error);
      // Use generic message to prevent user enumeration
      setError('If an account exists with this email address, a verification code will be sent.');
      setSuccessMessage('If an account exists with this email address, a verification code will be sent.');
      setStep('code');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle code verification
  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    
    // 🔍 DEBUG: Log every submission attempt
    console.log('🔍 EmailCodeAuth handleCodeSubmit triggered:', {
      email: userEmail,
      code: code,
      codeLength: code?.length,
      hasFlowData: !!flowData,
      flowId: flowData?.id,
      isLoading,
      timestamp: new Date().toISOString(),
      eventType: e?.type,
      eventTarget: e?.target?.tagName
    });
    
    // Validate required data before proceeding
    if (!userEmail || userEmail.trim() === '') {
      console.warn('⚠️ Attempted to submit without email');
      setError('Please enter your email address first');
      return;
    }
    
    if (!code || code.trim() === '') {
      console.warn('⚠️ Attempted to submit without code');
      setError('Please enter the verification code');
      return;
    }
    
    if (code.length < 6) {
      console.warn('⚠️ Code too short:', code.length);
      setError('Please enter the complete 6-digit code');
      return;
    }
    
    if (!flowData) {
      console.error('❌ No flow data available for submission');
      setError('Authentication flow not initialized. Please refresh and try again.');
      return;
    }
    
    setLoading(true);
    clearMessages();
    
    try {
      console.log('🔐 Verifying code for:', userEmail);
      
      // Let Kratos handle the session transition natively without custom caching
      console.log('🔐 Submitting email code - letting Kratos handle session transition');
      
      const formData = new URLSearchParams();
      formData.append('code', code);
      formData.append('method', 'code');
      formData.append('identifier', userEmail);
      
      const csrfToken = extractCSRFToken(flowData);
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await submitToFlow(flowData, formData.toString());
      
      // Handle AAL2 requirement first (422 status or isAAL2Required flag)
      if (response.status === 422 || response.isAAL2Required) {
        console.log('🔐 AAL2 step-up required after email code authentication');
        
        // Check error type: browser_location_change_required means follow redirect
        const errorId = response.data?.error?.id;
        if (errorId === 'browser_location_change_required') {
          console.log('🔐 Kratos requires browser redirect for AAL2 flow');
          const redirectUrl = response.data.redirect_browser_to;
          
          if (redirectUrl) {
            console.log('🔐 Following Kratos browser redirect for proper AAL2 flow:', redirectUrl);
            // Follow Kratos's browser flow as intended
            window.location.href = redirectUrl;
            return;
          }
        }
        
        // Fallback: Check if there are continue_with actions that establish AAL1 session first
        const continueWith = response.data?.continue_with;
        if (continueWith && continueWith.length > 0) {
          console.log('🔐 Found continue_with actions, processing AAL1 session establishment first:', continueWith);
          
          // Process continue_with actions to establish AAL1 session
          const sessionEstablished = await processContinueWith(continueWith);
          if (sessionEstablished) {
            console.log('✅ AAL1 session established via continue_with, now proceeding to AAL2');
          } else {
            console.log('⚠️ Continue_with processing failed, proceeding anyway');
          }
        }
        
        // Final fallback: navigate to our AAL2 component
        console.log('🔐 Using fallback AAL2 step-up component navigation');
        sessionStorage.setItem('aal1_completed', 'true');
        sessionStorage.setItem('aal1_email', userEmail);
        
        navigate('/security-upgrade', {
          state: {
            fromEmailLogin: true,
            email: userEmail,
            returnTo: returnTo,
            preserveAAL1: true
          }
        });
        return;
      }
      
      if (response.status === 200 || response.data?.state === 'passed_challenge') {
        console.log('🔐 Email code authentication successful! Deferring to Kratos for flow control.');
        
        // Process continue_with actions (Kratos native flow handling)
        const continueWith = response.data?.continue_with || response.data?.continueWith;
        if (continueWith) {
          console.log('🔐 Processing Kratos continue_with actions:', continueWith);
          await processContinueWith(continueWith);
          return; // Let Kratos handle the flow
        }
        
        // Check if Kratos wants a redirect - conditionally override for security bridge
        if (response.data?.redirect_browser_to) {
          const redirectUrl = response.data.redirect_browser_to;
          console.log('🔐 Kratos requesting redirect:', redirectUrl);
          
          // SECURITY BRIDGE: Check if we should override Kratos redirect for admin users
          try {
            const sessionCheck = await fetch('/.ory/sessions/whoami', { 
              credentials: 'include',
              headers: { 'Accept': 'application/json' }
            });
            
            if (sessionCheck.ok) {
              const sessionData = await sessionCheck.json();
              console.log('🔐 Session check after auth - Role:', sessionData?.identity?.traits?.role, 'AAL:', sessionData?.authenticator_assurance_level);
              
              // Override redirect for admin users with AAL1 to guide them to security upgrade
              if (sessionData?.identity?.traits?.role === 'admin' && 
                  sessionData?.authenticator_assurance_level === 'aal1') {
                console.log('🔐 OVERRIDING Kratos redirect - admin user needs security upgrade bridge');
                const securityUpgradeUrl = `/security-upgrade?newuser=true&return_to=${encodeURIComponent(returnTo)}`;
                console.log('🔐 Redirecting to security bridge:', securityUpgradeUrl);
                window.location.href = securityUpgradeUrl;
                return;
              }
            }
          } catch (bridgeError) {
            console.log('🔐 Security bridge check failed, following Kratos guidance:', bridgeError.message);
          }
          
          console.log('🔐 Following Kratos redirect guidance:', redirectUrl);
          window.location.href = redirectUrl;
          return;
        }
        
        // If Kratos doesn't provide guidance, check session state via Kratos
        console.log('🔐 No Kratos flow guidance - checking session state for next step');
        try {
          const sessionCheck = await fetch('/.ory/sessions/whoami', { 
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
          });
          
          if (sessionCheck.ok) {
            const sessionData = await sessionCheck.json();
            console.log('🔐 Session established, AAL:', sessionData.authenticator_assurance_level);
            
            // Let the system's normal navigation handle the redirect
            // Don't force a specific route - let the app's authentication logic decide
            dispatchAuthSuccess('email_code', sessionData.authenticator_assurance_level || 'aal1');
            setSuccessMessage('Authentication successful!');
            
            // SECURITY UPGRADE BRIDGE: Guide admin users to enhanced security after AAL1 login
            if (sessionData?.identity?.traits?.role === 'admin' && 
                sessionData?.authenticator_assurance_level === 'aal1') {
              console.log('🔐 Admin user with AAL1 - offering security upgrade bridge');
              setTimeout(() => {
                window.location.href = `/security-upgrade?newuser=true&return_to=${encodeURIComponent(returnTo)}`;
              }, 500);
            } else {
              // Brief pause to let session sync, then let normal app navigation handle routing
              setTimeout(() => {
                window.location.href = returnTo;
              }, 500);
            }
          } else {
            console.log('🔐 Session check failed after successful authentication');
            setError('Authentication completed but session verification failed. Please try again.');
          }
        } catch (error) {
          console.error('🔐 Error checking session after authentication:', error);
          setError('Authentication completed but verification failed. Please try again.');
        }
      } else {
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid verification code. Please try again.');
      }
    } catch (error) {
      console.error('🔐 Code verification failed:', error);
      setError('Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      {step === 'email' && (
        <>
          {/* INFO: Passkey authentication option removed - WebAuthn is now second factor only */}
          {/* Users must complete email authentication first, then use passkey for AAL2 */}
          
          {/* Email form */}
          <form onSubmit={handleEmailSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={userEmail}
                onChange={(e) => handleEmailChange(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                placeholder="you@example.com"
                required
                disabled={isLoading}
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !userEmail}
              className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Sending...' : 'Send Verification Code'}
            </button>
          </form>
        </>
      )}
      
      {step === 'code' && (
        <>
          <div className="text-center mb-4">
            <p className="text-gray-300 text-sm">
              Code sent to: <span className="text-blue-400">{userEmail}</span>
            </p>
          </div>
          
          <form 
            onSubmit={handleCodeSubmit} 
            className="space-y-6"
            onKeyPress={(e) => {
              // 🔍 DEBUG: Log key press events
              console.log('🔍 Form keypress:', {
                key: e.key,
                hasCode: !!code,
                codeLength: code?.length,
                isEnter: e.key === 'Enter'
              });
              
              // Prevent Enter key from submitting if code is incomplete
              if (e.key === 'Enter' && (!code || code.length < 6)) {
                e.preventDefault();
                console.log('⚠️ Prevented incomplete form submission on Enter');
                setError('Please enter the complete 6-digit code');
              }
            }}
            noValidate  // Prevent browser validation interference
          >
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
                Enter the 6-digit code from your email
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
        </>
      )}
    </div>
  );
};

export default EmailCodeAuth;