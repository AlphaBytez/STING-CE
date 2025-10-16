import { useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthProvider';

export function useSessionCoordination() {
  const { setError, setSyncStatus } = useAuth();
  
  // Wait for Kratos session to be established
  const waitForKratosSession = useCallback(async (maxAttempts = 10) => {
    console.log('🔐 Waiting for Kratos session to be established...');
    
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const sessionCheck = await fetch('/api/auth/me', { 
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });
        
        if (sessionCheck.ok) {
          const sessionData = await sessionCheck.json();
          // Handle both direct Kratos response and Flask coordination response
          const sessionEmail = sessionData?.identity?.traits?.email || sessionData?.user?.email;
          if (sessionEmail) {
            console.log('✅ Kratos session confirmed for:', sessionEmail);
            return sessionData;
          }
        }
      } catch (e) {
        console.log(`🔐 Session check attempt ${attempts + 1} failed:`, e.message);
      }
      
      attempts++;
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    console.warn('🔐 Session confirmation timed out after', maxAttempts, 'attempts');
    return null;
  }, []);
  
  // Verify Flask session coordination via /api/auth/me
  const createFlaskSession = useCallback(async (authMethod, aalLevel = 'aal1') => {
    try {
      console.log('🔐 Verifying Flask session coordination...', { authMethod, aalLevel });
      
      // Use /api/auth/me which handles session coordination automatically
      const response = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.ok) {
        const sessionData = await response.json();
        console.log('✅ Flask session coordination verified');
        return sessionData;
      } else {
        console.warn('⚠️ Flask session coordination failed:', response.status);
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to verify Flask session:', error);
      return false;
    }
  }, []);
  
  // Complete full session coordination (Kratos + Flask)
  const completeSessionCoordination = useCallback(async (authMethod, aalLevel = 'aal1', returnTo = '/dashboard') => {
    try {
      console.log('🔄 Starting session coordination...', { authMethod, aalLevel, returnTo });
      
      // Step 1: Wait for Kratos session
      const kratosSession = await waitForKratosSession();
      if (!kratosSession) {
        throw new Error('Kratos session could not be established');
      }
      
      // Step 2: Create Flask session
      const flaskSessionCreated = await createFlaskSession(authMethod, aalLevel);
      if (!flaskSessionCreated) {
        console.warn('⚠️ Flask session creation failed, but continuing...');
      }
      
      // Step 3: Check for enrollment requirements (only for non-dashboard destinations)
      if (returnTo !== '/dashboard') {
        console.log('🔒 Checking enrollment requirements for:', returnTo);
        await checkEnrollmentRequirements(returnTo);
      }
      
      console.log('✅ Session coordination complete, redirecting to:', returnTo);
      
      // Force refresh to ensure UI state updates properly
      // This prevents the manual refresh requirement after email code login
      setTimeout(() => {
        console.log('🔄 Force refreshing to ensure proper UI state...');
        window.location.href = returnTo;
      }, 100);
      
      return true;
    } catch (error) {
      console.error('❌ Session coordination failed:', error);
      setError('Session setup failed. Please try again.');
      return false;
    }
  }, [waitForKratosSession, createFlaskSession, setError]);
  
  // Check if user needs enrollment
  const checkEnrollmentRequirements = useCallback(async (returnTo) => {
    try {
      console.log('🔒 Checking enrollment requirements for destination:', returnTo);
      
      // Get current session data
      const sessionResponse = await axios.get('/api/auth/me', { withCredentials: true });
      const sessionData = sessionResponse.data;
      
      const userEmail = sessionData?.identity?.traits?.email;
      const userRole = sessionData?.identity?.traits?.role || 'user';
      
      if (!userEmail) {
        throw new Error('No user email found in session');
      }
      
      // Check authentication methods
      const [totpResponse, webauthnStatus] = await Promise.all([
        axios.get('/api/totp/totp-status', { withCredentials: true }).catch(() => ({ data: { enabled: false } })),
        checkWebAuthnAvailability()
      ]);
      
      const hasTOTP = totpResponse.data?.enabled === true;
      const hasWebAuthn = webauthnStatus.configured === true;
      
      console.log('🔒 User authentication status:', {
        email: userEmail,
        role: userRole,
        hasTOTP,
        hasWebAuthn
      });
      
      // If user has no auth methods, redirect to enrollment
      if (!hasTOTP && !hasWebAuthn) {
        console.log('🔒 No authentication methods found, redirecting to enrollment');
        window.location.href = '/enrollment';
        return;
      }
      
      // For admin users, check if they meet aggressive security requirements
      if (userRole === 'admin') {
        // Import SecurityGateService dynamically to avoid circular dependencies
        const { default: securityGateService } = await import('../../../services/securityGateService');
        
        const securityStatus = await securityGateService.checkSecurityStatus({
          email: userEmail,
          role: userRole,
          email_verified: sessionData?.identity?.verifiable_addresses?.[0]?.verified !== false
        });
        
        if (!securityStatus?.meetsRequirements) {
          console.log('🚨 Admin does not meet security requirements - redirecting to enrollment');
          window.location.href = '/enrollment';
          return;
        }
      }
      
      console.log('✅ User meets enrollment requirements');
    } catch (error) {
      console.error('🔒 Error checking enrollment requirements:', error);
      // Don't block authentication for enrollment check errors
    }
  }, []);
  
  // Check WebAuthn availability using Kratos session data
  const checkWebAuthnAvailability = useCallback(async () => {
    try {
      if (!window.PublicKeyCredential) {
        return { supported: false, configured: false, count: 0 };
      }
      
      // Check Kratos session for WebAuthn credentials instead of custom API
      const sessionResponse = await axios.get('/api/auth/me', { withCredentials: true });
      const sessionData = sessionResponse.data;
      
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
  
  // Simplified sync status - no longer needed with pure Kratos authentication
  const pollSyncStatus = useCallback(async () => {
    console.log('🔄 Profile sync not required with pure Kratos authentication');
    setSyncStatus({ 
      isActive: false, 
      message: 'Sync not required - using Kratos native auth',
      progress: 100
    });
    return true;
  }, [setSyncStatus]);
  
  return {
    waitForKratosSession,
    createFlaskSession,
    completeSessionCoordination,
    checkEnrollmentRequirements,
    pollSyncStatus
  };
}