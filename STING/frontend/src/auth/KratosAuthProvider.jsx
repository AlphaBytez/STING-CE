/**
 * KratosAuthProvider - Simplified Kratos authentication context
 * 
 * Provides clean authentication state management with Kratos
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Configure axios defaults
axios.defaults.withCredentials = true;

// Create auth context
const AuthContext = createContext(null);

// Custom hook for auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within KratosAuthProvider');
  }
  return context;
};

// Session refresh interval (5 minutes)
const SESSION_REFRESH_INTERVAL = 5 * 60 * 1000;

export const KratosAuthProvider = ({ children }) => {
  // Authentication state
  const [session, setSession] = useState(null);
  const [identity, setIdentity] = useState(null);
  const [aal, setAal] = useState('aal1');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Feature state
  const [hasPasskey, setHasPasskey] = useState(false);
  const [hasTOTP, setHasTOTP] = useState(false);
  const [configuredMethods, setConfiguredMethods] = useState([]);

  /**
   * Fetch current session from Kratos
   */
  const fetchSession = useCallback(async () => {
    try {
      console.log('🔐 Fetching Kratos session...');
      
      // Try to get session from Kratos whoami endpoint
      const response = await axios.get('/.ory/sessions/whoami', {
        headers: { 'Accept': 'application/json' },
        validateStatus: (status) => status < 500
      });
      
      if (response.status === 200 && response.data) {
        const sessionData = response.data;
        
        setSession(sessionData);
        setIdentity(sessionData.identity);
        setAal(sessionData.authenticator_assurance_level || 'aal1');
        setIsAuthenticated(true);
        
        // Check authentication methods
        analyzeAuthMethods(sessionData);
        
        console.log('🔐 Session loaded:', {
          id: sessionData.id,
          identity: sessionData.identity?.id,
          aal: sessionData.authenticator_assurance_level,
          email: sessionData.identity?.traits?.email
        });
        
        return sessionData;
      } else {
        // No active session
        console.log('🔐 No active session found');
        clearSession();
        return null;
      }
    } catch (error) {
      console.error('🔐 Failed to fetch session:', error);
      clearSession();
      setError('Failed to load session');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Analyze available authentication methods from session
   */
  const analyzeAuthMethods = (sessionData) => {
    const methods = [];
    
    if (sessionData.authentication_methods) {
      sessionData.authentication_methods.forEach(method => {
        if (method.method === 'webauthn') {
          setHasPasskey(true);
          methods.push('webauthn');
        }
        if (method.method === 'totp') {
          setHasTOTP(true);
          methods.push('totp');
        }
      });
    }
    
    // Check identity credentials
    if (sessionData.identity?.credentials) {
      Object.keys(sessionData.identity.credentials).forEach(key => {
        if (key === 'webauthn') {
          setHasPasskey(true);
          if (!methods.includes('webauthn')) methods.push('webauthn');
        }
        if (key === 'totp') {
          setHasTOTP(true);
          if (!methods.includes('totp')) methods.push('totp');
        }
      });
    }
    
    setConfiguredMethods(methods);
    console.log('🔐 Configured methods:', methods);
  };

  /**
   * Clear session state
   */
  const clearSession = () => {
    setSession(null);
    setIdentity(null);
    setAal('aal1');
    setIsAuthenticated(false);
    setHasPasskey(false);
    setHasTOTP(false);
    setConfiguredMethods([]);
  };

  /**
   * Refresh session
   */
  const refreshSession = useCallback(async () => {
    console.log('🔐 Refreshing session...');
    return await fetchSession();
  }, [fetchSession]);

  /**
   * Logout user
   */
  const logout = useCallback(async () => {
    try {
      console.log('🔐 Logging out...');
      
      // Create logout flow
      const flowResponse = await axios.get('/.ory/self-service/logout/browser', {
        headers: { 'Accept': 'application/json' }
      });
      
      if (flowResponse.data?.logout_url) {
        // Perform logout
        await axios.get(flowResponse.data.logout_url);
      }
      
      // Clear local session
      clearSession();
      
      // Redirect to login
      window.location.href = '/login';
      
    } catch (error) {
      console.error('🔐 Logout failed:', error);
      // Force clear session even if logout fails
      clearSession();
      window.location.href = '/login';
    }
  }, []);

  /**
   * Check if user needs AAL2 for current context
   */
  const requiresAAL2 = useCallback((requiredLevel = 'aal2') => {
    if (requiredLevel === 'aal2' && aal === 'aal1') {
      return true;
    }
    return false;
  }, [aal]);

  /**
   * Check if user has specific authentication method
   */
  const hasAuthMethod = useCallback((method) => {
    return configuredMethods.includes(method);
  }, [configuredMethods]);

  /**
   * Get user role from identity traits
   */
  const getUserRole = useCallback(() => {
    return identity?.traits?.role || 'user';
  }, [identity]);

  /**
   * Check if user is admin
   */
  const isAdmin = useCallback(() => {
    return getUserRole() === 'admin';
  }, [getUserRole]);

  /**
   * Initialize authentication check on mount
   */
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  /**
   * Set up session refresh interval
   */
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const interval = setInterval(() => {
      refreshSession();
    }, SESSION_REFRESH_INTERVAL);
    
    return () => clearInterval(interval);
  }, [isAuthenticated, refreshSession]);

  /**
   * Listen for storage events (logout from other tabs)
   */
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'kratos_logout' && e.newValue === 'true') {
        console.log('🔐 Logout detected from another tab');
        clearSession();
        window.location.href = '/login';
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Context value
  const value = {
    // Session state
    session,
    identity,
    aal,
    isAuthenticated,
    isLoading,
    error,
    
    // Feature state
    hasPasskey,
    hasTOTP,
    configuredMethods,
    
    // Methods
    refreshSession,
    logout,
    requiresAAL2,
    hasAuthMethod,
    getUserRole,
    isAdmin,
    
    // User info helpers
    user: identity ? {
      id: identity.id,
      email: identity.traits?.email,
      firstName: identity.traits?.name?.first,
      lastName: identity.traits?.name?.last,
      fullName: identity.traits?.name ? 
        `${identity.traits.name.first} ${identity.traits.name.last}` : '',
      role: identity.traits?.role || 'user',
      createdAt: identity.created_at,
      updatedAt: identity.updated_at
    } : null
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default KratosAuthProvider;