import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthProvider';
import { useKratosFlow } from '../hooks/useKratosFlow';
import { useSessionCoordination } from '../hooks/useSessionCoordination';

const TOTPAuth = ({ onSuccess, onCancel }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [totpCode, setTotpCode] = useState('');
  
  const {
    userEmail,
    isLoading,
    setLoading,
    error,
    setError,
    successMessage,
    setSuccessMessage,
    clearMessages,
    dispatchAuthSuccess
  } = useAuth();
  
  const { processContinueWith } = useKratosFlow();
  const { completeSessionCoordination } = useSessionCoordination();
  
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // Handle TOTP submission
  const handleTOTPSubmit = async (e) => {
    e.preventDefault();
    if (!totpCode || totpCode.length < 6) return;
    
    setLoading(true);
    clearMessages();
    
    try {
      console.log('🔐 Starting TOTP AAL2 authentication...');
      
      // Initialize AAL2 flow
      const flowResponse = await axios.get(`/.ory/self-service/login/browser?aal=aal2`, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      // Prepare TOTP form data
      const formData = new URLSearchParams();
      formData.append('totp_code', totpCode);
      formData.append('method', 'totp');
      
      const csrfToken = flowResponse.data.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      // Submit TOTP
      const totpActionUrl = flowResponse.data.ui.action.replace(/https?:\/\/[^\/]+/, '');
      console.log('🔐 Submitting TOTP to:', totpActionUrl);
      
      const response = await axios.post(
        totpActionUrl,
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
      
      console.log('🔐 TOTP response:', response.status, response.data?.state);
      
      if (response.status === 200 || response.data?.state === 'passed_challenge') {
        console.log('🔐 TOTP AAL2 authentication successful!');
        
        // Process continue_with actions to complete session
        const continueWith = response.data?.continue_with || response.data?.continueWith;
        if (continueWith) {
          await processContinueWith(continueWith);
        }
        
        // Dispatch auth success event
        dispatchAuthSuccess('totp', 'aal2');
        
        setSuccessMessage('TOTP authentication successful!');
        
        // Check if user needs enrollment after TOTP
        await checkEnrollmentNeeds();
        
        // Complete session coordination
        const sessionSuccess = await completeSessionCoordination('totp', 'aal2', returnTo);
        if (sessionSuccess) {
          if (onSuccess) {
            onSuccess();
          } else {
            setTimeout(() => {
              navigate(returnTo, { replace: true });
            }, 1000);
          }
        }
      } else {
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid TOTP code. Please try again.');
      }
    } catch (error) {
      console.error('🔐 TOTP verification failed:', error);
      setError('TOTP verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  // Check if user needs enrollment after TOTP verification
  const checkEnrollmentNeeds = async () => {
    try {
      // Get current session
      const sessionResponse = await fetch('/.ory/sessions/whoami', { 
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!sessionResponse.ok) return;
      
      const sessionData = await sessionResponse.json();
      const currentUserEmail = sessionData?.identity?.traits?.email;
      
      if (!currentUserEmail) return;
      
      // Check configured methods
      const methodsResponse = await axios.post('/api/auth/check-configured-methods', {
        email: currentUserEmail
      }, {
        withCredentials: true,
        headers: { 'Content-Type': 'application/json' }
      });
      
      const hasTOTP = methodsResponse.data?.has_totp || false;
      const hasWebAuthn = methodsResponse.data?.has_webauthn || false;
      
      console.log('🔐 User 2FA status after TOTP:', { hasTOTP, hasWebAuthn, email: currentUserEmail });
      
      // If user has TOTP but missing passkey, redirect to enrollment
      if (hasTOTP && !hasWebAuthn) {
        console.log('🔐 User needs to complete passkey setup, redirecting to enrollment');
        sessionStorage.setItem('aggressive_enrollment', 'true');
        sessionStorage.setItem('has_existing_totp', 'true');
        
        // Delay redirect to show success message first
        setTimeout(() => {
          navigate('/enrollment', { 
            state: { 
              from: 'aggressive',
              hasExistingTOTP: true,
              userEmail: currentUserEmail,
              authenticated: true
            },
            replace: true
          });
        }, 2000);
      }
    } catch (error) {
      console.error('🔐 Error checking enrollment needs:', error);
      // Don't block authentication for enrollment check errors
    }
  };
  
  return (
    <div className="space-y-6">
      {/* User context */}
      {userEmail && (
        <div className="text-center mb-4">
          <p className="text-gray-300 text-sm">
            TOTP verification for: <span className="text-blue-400">{userEmail}</span>
          </p>
          <p className="text-gray-500 text-xs mt-1">
            Enter the code from your authenticator app
          </p>
        </div>
      )}
      
      {/* TOTP form */}
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
            autoComplete="one-time-code"
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-gray-400 text-sm">
              6-digit code from your authenticator app
            </p>
            <p className="text-gray-500 text-xs">
              Code refreshes every 30s
            </p>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading || totpCode.length < 6}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
        >
          {isLoading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Verifying...
            </div>
          ) : (
            'Verify Code'
          )}
        </button>
      </form>
      
      {/* Help and alternatives */}
      <div className="space-y-3">
        <div className="text-center">
          <details className="text-gray-400">
            <summary className="text-sm cursor-pointer hover:text-gray-300">
              Need help with TOTP? ▼
            </summary>
            <div className="mt-3 text-xs space-y-2 text-left bg-slate-800/30 rounded-lg p-3">
              <p>• Open your authenticator app (Google Authenticator, Authy, etc.)</p>
              <p>• Find the entry for "STING" or "{window.location.hostname}"</p>
              <p>• Enter the current 6-digit code</p>
              <p>• Code changes every 30 seconds</p>
            </div>
          </details>
        </div>
        
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="w-full text-gray-400 hover:text-white text-sm"
          >
            ← Back to security options
          </button>
        )}
      </div>
      
      {/* Common TOTP apps */}
      <div className="sting-glass-subtle border border-gray-600/50 rounded-lg p-3">
        <p className="text-gray-400 text-xs text-center mb-2">Compatible authenticator apps:</p>
        <div className="flex justify-center space-x-4 text-xs text-gray-500">
          <span>Google Authenticator</span>
          <span>•</span>
          <span>Authy</span>
          <span>•</span>
          <span>1Password</span>
          <span>•</span>
          <span>Microsoft Authenticator</span>
        </div>
      </div>
    </div>
  );
};

export default TOTPAuth;