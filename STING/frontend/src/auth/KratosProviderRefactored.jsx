import React, { createContext, useContext, useCallback, useEffect, useState, useRef } from 'react';
import axios from 'axios';
import kratosApi, { getKratosUrl } from '../utils/kratosConfig';

// Keep the existing context structure for compatibility
const KratosContext = createContext({
  identity: null,
  session: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  login: async () => {},
  logout: async () => {},
  checkSession: async () => {},
  clearError: () => {},
});

export const useKratos = () => useContext(KratosContext);

/**
 * Refactored Kratos Provider that simplifies authentication
 * while maintaining compatibility with existing components
 */
export const KratosProviderRefactored = ({ children }) => {
  const [identity, setIdentity] = useState(null);
  const [session, setSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use refs to track current state for async callbacks
  const identityRef = useRef(null);
  const sessionRef = useRef(null);

  // Update refs when state changes
  useEffect(() => {
    identityRef.current = identity;
    sessionRef.current = session;
  }, [identity, session]);

  const kratosUrl = getKratosUrl(true);

  // Check session - single source of truth with AAL2 fallback
  const checkSession = useCallback(async () => {
    // Skip session check on public routes to avoid 401 errors in console
    const publicRoutes = ['/login', '/register', '/verify-email', '/error', '/reset-password'];
    const currentPath = window.location.pathname;

    if (publicRoutes.some(route => currentPath.startsWith(route))) {
      setIdentity(null);
      setSession(null);
      setIsLoading(false);
      return null;
    }

    // If we have a recent auth marker, add a small delay to ensure Kratos has committed the session
    const recentAuth = sessionStorage.getItem('sting_recent_auth');
    if (recentAuth) {
      const authTime = parseInt(recentAuth);
      if (Date.now() - authTime < 2000) { // Within 2 seconds of auth
        console.log('🔄 Very recent authentication detected, adding delay for Kratos session commit');
        await new Promise(resolve => setTimeout(resolve, 500)); // 500ms delay
      }
    }

    try {
      setIsLoading(true);
      const response = await axios.get(kratosApi.whoami(), {
        withCredentials: true,
      });

      // Session check successful

      // Handle Flask /api/auth/me response structure
      // Check for both true boolean and truthy values, or if user exists (fallback for undefined authenticated)
      if (response.status === 200 && (response.data.authenticated === true || response.data.authenticated === 'true' || (response.data.user && response.data.authenticated !== false))) {
        // Convert Flask response to Kratos-compatible structure
        const user = response.data.user;
        const compatibleIdentity = {
          id: user.kratos_id || user.id,
          traits: {
            email: user.email,
            role: user.role,
            name: `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username
          }
        };

        // Create session object
        const sessionData = {
          identity: compatibleIdentity,
          authenticator_assurance_level: response.data.session?.aal || 'aal1',
          active: true,
          authenticated_at: response.data.session?.authenticated_at,
          expires_at: response.data.session?.expires_at
        };

        setIdentity(compatibleIdentity);
        setSession(sessionData);
        setError(null);

        // Emit session change event
        window.dispatchEvent(new CustomEvent('kratos-session-changed', {
          detail: sessionData
        }));

        return sessionData;
      }
    } catch (err) {
      // CRITICAL FIX: Check for AAL2 errors and fallback to Flask session
      const isAAL2Error = err.response?.status === 403 && 
                          (err.response?.data?.error?.id === 'session_aal2_required' || 
                           String(err.response?.data?.error?.message || '').toLowerCase().includes('aal2') ||
                           String(err.response?.data?.error?.reason || '').toLowerCase().includes('authenticator assurance level'));

      if (isAAL2Error) {
        // AAL2 error detected, trying Flask session fallback
        
        try {
          // Fallback to our Flask-based auth endpoint
          const fallbackResponse = await axios.get('/api/auth/me', {
            withCredentials: true,
          });
          
          if (fallbackResponse.status === 200 && fallbackResponse.data.authenticated && fallbackResponse.data.user) {
            // Flask session fallback successful
            
            // Create a compatible identity object from Flask session data
            const flaskUser = fallbackResponse.data.user;
            const compatibleIdentity = {
              id: flaskUser.id || flaskUser.user_id,
              traits: {
                email: flaskUser.email,
                role: flaskUser.role || 'user',
                name: flaskUser.name || flaskUser.email
              }
            };
            
            // Create a compatible session object
            const compatibleSession = {
              identity: compatibleIdentity,
              authenticator_assurance_level: 'aal2',  // Flask session indicates AAL2
              active: true
            };
            
            setIdentity(compatibleIdentity);
            setSession(compatibleSession);
            setError(null);
            
            // Emit session change event
            window.dispatchEvent(new CustomEvent('kratos-session-changed', {
              detail: compatibleSession
            }));
            
            return compatibleSession;
          }
        } catch (fallbackErr) {
          // Flask session fallback also failed
        }
      }

      // Only log non-401 errors (401 is expected when not logged in)
      if (err.response?.status !== 401) {
        // Session check failed (non-401)
        setError(err.message);
      }
      setIdentity(null);
      setSession(null);
    } finally {
      setIsLoading(false);
    }
    return null;
  }, []); // Empty dependency array - checkSession doesn't need to recreate

  // Initialize session check on mount - avoid infinite loops
  useEffect(() => {
    checkSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Force session refresh when we detect recent authentication
  useEffect(() => {
    const recentAuth = sessionStorage.getItem('sting_recent_auth');
    if (recentAuth && !session && !isLoading) {
      const authTime = parseInt(recentAuth);
      if (Date.now() - authTime < 15000) { // Within 15 seconds
        // CRITICAL: Mark that we're processing to prevent duplicate refreshes
        const processingKey = 'sting_auth_processing';

        // Check retry count to prevent infinite loops
        const retryKey = 'sting_auth_retry_count';
        const retryCount = parseInt(sessionStorage.getItem(retryKey) || '0');
        if (retryCount >= 3) {
          // Max auth retry attempts reached, clearing markers
          sessionStorage.removeItem('sting_recent_auth');
          sessionStorage.removeItem(processingKey);
          sessionStorage.removeItem(retryKey);
          return;
        }
        sessionStorage.setItem(retryKey, (retryCount + 1).toString());

        // Use a more robust check with timestamp to prevent race conditions
        const existingProcess = sessionStorage.getItem(processingKey);
        if (existingProcess) {
          const processTime = parseInt(existingProcess);
          if (Date.now() - processTime < 5000) { // Process started within 5 seconds
            // Session refresh already in progress, skipping duplicate
            return;
          }
        }

        sessionStorage.setItem(processingKey, Date.now().toString());
        console.log('🔄 Recent authentication detected, forcing session refresh');

        // Simply check the session after a small delay
        const timer = setTimeout(async () => {
          try {
            console.log('🔄 Checking session after recent authentication...');

            // Just check the session directly - no complex establishment
            await checkSession();

            // Check if we got authenticated
            setTimeout(() => {
              // Use refs to check current state, not closure values
              if (identityRef.current || sessionRef.current) {
                console.log('✅ Session verified after authentication, clearing markers', {
                  hasIdentity: !!identityRef.current,
                  hasSession: !!sessionRef.current
                });
                sessionStorage.removeItem('sting_recent_auth');
                sessionStorage.removeItem(processingKey);
                sessionStorage.removeItem('sting_auth_retry_count');
              } else {
                console.log('⚠️ No session found after check, clearing markers to prevent loop');
                sessionStorage.removeItem('sting_recent_auth');
                sessionStorage.removeItem(processingKey);
                sessionStorage.removeItem('sting_auth_retry_count');
              }
            }, 1000); // Give state time to propagate
          } catch (err) {
            console.error('🔄 Session check failed:', err);
            sessionStorage.removeItem('sting_recent_auth');
            sessionStorage.removeItem(processingKey);
            sessionStorage.removeItem('sting_auth_retry_count');
          }
        }, 1000); // 1 second delay to let Kratos session fully establish
        return () => {
          clearTimeout(timer);
          sessionStorage.removeItem(processingKey);
        };
      }
    }
  }, [session, isLoading]); // Remove checkSession to prevent infinite loop

  // Simplified login - let Kratos handle the flow
  const login = useCallback(async (flowId, credentials) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await axios.post(
        `/.ory/self-service/login?flow=${flowId}`,
        credentials,
        { withCredentials: true }
      );

      if (response.data.session) {
        setIdentity(response.data.session.identity);
        setSession(response.data.session);
        return { success: true, session: response.data.session };
      }

      return { success: false, error: 'No session returned' };
    } catch (err) {
      const errorMessage = err.response?.data?.ui?.messages?.[0]?.text || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  }, [kratosUrl]);

  // Simplified logout
  const logout = useCallback(async () => {
    try {
      // Create logout flow
      const { data } = await axios.get(
        `/.ory/self-service/logout/browser`,
        { withCredentials: true }
      );

      if (data.logout_url) {
        // Redirect to Kratos logout URL
        window.location.href = data.logout_url;
      }
    } catch (err) {
      console.error('Logout error:', err);
      // Fallback - clear local state and redirect
      setIdentity(null);
      setSession(null);
      window.location.href = '/login';
    }
  }, [kratosUrl]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Check if settings are required (for password changes, etc.)
  const requiresAction = useCallback(() => {
    // Check if user needs to change password
    if (identity?.traits?.force_password_change === true) {
      return 'CHANGE_PASSWORD';
    }
    return false;
  }, [identity]);

  // Add refresh session method for TOTP setup completion
  const refreshSession = useCallback(async () => {
    try {
      console.log('🔐 KratosProvider: Refreshing session after authentication change');
      await checkSession();
      console.log('🔐 KratosProvider: Session refresh complete');
      return true;
    } catch (error) {
      console.error('🔐 KratosProvider: Failed to refresh session:', error);
      return false;
    }
  }, [checkSession]);

  const value = {
    identity,
    session,
    isAuthenticated: !!identity,
    isLoading,
    error,
    login,
    logout,
    checkSession,
    clearError,
    requiresAction,
    refreshSession,
    // Add compatibility properties
    user: identity, // Some components use 'user' instead of 'identity'
  };

  return (
    <KratosContext.Provider value={value}>
      {children}
    </KratosContext.Provider>
  );
};

// Export as KratosProvider for backward compatibility
export const KratosProvider = KratosProviderRefactored;

export default KratosProviderRefactored;