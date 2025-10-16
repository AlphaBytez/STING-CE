import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from './KratosProvider';
import { api } from '../utils/apiClient';

const SessionCheck = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, identity } = useKratos();
  const hasRedirected = useRef(false);

  useEffect(() => {
    const initializeBackendSession = async () => {
      if (!isLoading && isAuthenticated) {
        console.log('[SessionCheck] User is authenticated, initializing backend session');
        
        try {
          // Initialize backend session from Kratos session
          await api.auth.initSession();
          console.log('[SessionCheck] Backend session initialized successfully');
        } catch (error) {
          console.error('[SessionCheck] Failed to initialize backend session:', error);
          // Continue anyway - the middleware should handle it
        }
        
        // Check if this is a new registration that needs passkey setup
        const justRegistered = localStorage.getItem('justRegistered');
        if (justRegistered && !hasRedirected.current) {
          console.log('[SessionCheck] New registration detected, checking WebAuthn support...');
          // Don't clear the flag here - let PasskeySetup handle it
          
          // Check if WebAuthn is available
          if (window.PublicKeyCredential) {
            try {
              const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
              if (available) {
                console.log('[SessionCheck] WebAuthn available, redirecting to passkey setup');
                hasRedirected.current = true;
                navigate('/settings/security?setup=passkey', { replace: true });
                return;
              }
            } catch (err) {
              console.error('[SessionCheck] Error checking WebAuthn support:', err);
            }
          }
          
          // If WebAuthn is not available, clear the flag and continue to dashboard
          localStorage.removeItem('justRegistered');
        }
        
        // Email verification disabled for development
        // const emailVerified = identity?.verifiable_addresses?.some(
        //   addr => addr.via === 'email' && addr.verified === true
        // );
        
        // if (!emailVerified) {
        //   console.log('[SessionCheck] Email not verified, redirecting to verification page');
        //   navigate('/verify-email', { replace: true });
        // } else {
        //   console.log('[SessionCheck] User authenticated and verified, redirecting to dashboard');
        //   navigate('/dashboard', { replace: true });
        // }
        
        // Skip email verification check - go directly to dashboard
        if (!hasRedirected.current) {
          console.log('[SessionCheck] User authenticated (email verification disabled), redirecting to dashboard');
          hasRedirected.current = true;
          navigate('/dashboard', { replace: true });
        }
      } else if (!isLoading && !isAuthenticated && !hasRedirected.current) {
        console.log('[SessionCheck] User is not authenticated, redirecting to login');
        hasRedirected.current = true;
        navigate('/login?registered=true', { replace: true });
      }
    };

    initializeBackendSession();
  }, [isAuthenticated, isLoading, navigate, identity]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto"></div>
        <p className="mt-4 text-white">Checking your session...</p>
      </div>
    </div>
  );
};

export default SessionCheck;