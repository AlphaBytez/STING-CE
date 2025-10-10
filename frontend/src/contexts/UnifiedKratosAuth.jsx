import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

/**
 * Unified Kratos Authentication Context
 * Single source of truth for all authentication state
 * Replaces: RoleContext, KratosProvider, AAL2Provider, UnifiedAuthProvider
 */

const UnifiedKratosAuthContext = createContext(null);

export const UnifiedKratosAuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState({
    // Basic authentication
    isAuthenticated: false,
    isLoading: true,
    
    // User information (from Kratos identity)
    user: null,
    identity: null,
    session: null,
    
    // Role and permissions
    role: 'user', // 'user', 'admin', 'super_admin'
    isAdmin: false,
    isSuperAdmin: false,
    
    // Authentication Assurance Level
    aal: 'aal1', // 'aal1', 'aal2', 'aal3'
    needsAAL2: false,
    canUpgradeAAL: false,
    
    // Configured methods (from Kratos identity)
    configuredMethods: {
      totp: false,
      webauthn: false,
      passkeys: []
    },
    
    // Error state
    error: null,
    lastChecked: null
  });

  // Fetch authentication state from Kratos (single source of truth)
  const fetchAuthState = useCallback(async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      
      console.log('🔐 [UnifiedAuth] Checking authentication state...');
      
      // Single call to Kratos for ALL authentication data
      const response = await fetch('/.ory/sessions/whoami', {
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) {
        console.log('🔐 [UnifiedAuth] No active session');
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: false,
          isLoading: false,
          user: null,
          identity: null,
          session: null,
          role: 'user',
          isAdmin: false,
          isSuperAdmin: false,
          aal: 'aal1',
          needsAAL2: false,
          canUpgradeAAL: false,
          configuredMethods: { totp: false, webauthn: false, passkeys: [] }
        }));
        return;
      }
      
      const sessionData = await response.json();
      const identity = sessionData.identity || {};
      const traits = identity.traits || {};
      
      console.log('🔐 [UnifiedAuth] Session data received:', {
        email: traits.email,
        role: traits.role,
        aal: sessionData.authenticator_assurance_level,
        sessionId: sessionData.id
      });
      
      // Extract configured methods from Kratos credentials
      const credentials = identity.credentials || {};
      const configuredMethods = {
        totp: !!(credentials.totp?.identifiers?.length > 0),
        webauthn: !!(credentials.webauthn?.identifiers?.length > 0),
        passkeys: credentials.webauthn?.identifiers || []
      };
      
      // Determine role and permissions
      const userRole = traits.role || 'user';
      const isAdmin = userRole === 'admin';
      const isSuperAdmin = userRole === 'super_admin';
      
      // Determine AAL and upgrade needs
      const currentAAL = sessionData.authenticator_assurance_level || 'aal1';
      const hasAnyMethods = configuredMethods.totp || configuredMethods.webauthn;
      const needsAAL2 = isAdmin && currentAAL === 'aal1' && hasAnyMethods;
      
      // Create unified user object
      const user = {
        id: identity.id,
        email: traits.email,
        name: `${traits.name?.first || ''} ${traits.name?.last || ''}`.trim(),
        role: userRole,
        aal: currentAAL,
        isAdmin,
        isSuperAdmin,
        sessionId: sessionData.id,
        authenticated_at: sessionData.authenticated_at,
        expires_at: sessionData.expires_at
      };
      
      console.log('🔐 [UnifiedAuth] Authentication state updated:', {
        authenticated: true,
        role: userRole,
        aal: currentAAL,
        needsAAL2,
        configuredMethods
      });
      
      setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user,
        identity,
        session: sessionData,
        role: userRole,
        isAdmin,
        isSuperAdmin,
        aal: currentAAL,
        needsAAL2,
        canUpgradeAAL: hasAnyMethods,
        configuredMethods,
        error: null,
        lastChecked: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('🔐 [UnifiedAuth] Error fetching auth state:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error.message,
        lastChecked: new Date().toISOString()
      }));
    }
  }, []);
  
  // Refresh authentication state
  const refresh = useCallback(() => {
    console.log('🔐 [UnifiedAuth] Manual refresh requested');
    fetchAuthState();
  }, [fetchAuthState]);
  
  // Check for AAL2 requirements
  const requireAAL2 = useCallback(() => {
    const { isAdmin, aal, configuredMethods } = authState;
    return isAdmin && aal === 'aal1' && (configuredMethods.totp || configuredMethods.webauthn);
  }, [authState]);
  
  // Get step-up URL
  const getStepUpUrl = useCallback((returnTo = window.location.pathname) => {
    return `/security-upgrade?return_to=${encodeURIComponent(returnTo)}`;
  }, []);
  
  // Initial auth check
  useEffect(() => {
    fetchAuthState();
  }, [fetchAuthState]);
  
  // Listen for auth events (login/logout/session changes)
  useEffect(() => {
    const handleAuthEvent = () => {
      console.log('🔐 [UnifiedAuth] Auth event detected, refreshing state');
      fetchAuthState();
    };
    
    // Listen for custom auth events
    window.addEventListener('auth-state-changed', handleAuthEvent);
    window.addEventListener('aal-status-refresh', handleAuthEvent);
    
    return () => {
      window.removeEventListener('auth-state-changed', handleAuthEvent);
      window.removeEventListener('aal-status-refresh', handleAuthEvent);
    };
  }, [fetchAuthState]);
  
  const contextValue = {
    // Authentication state
    ...authState,
    
    // Actions
    refresh,
    requireAAL2,
    getStepUpUrl,
    
    // Helper methods
    hasRole: (role) => authState.role === role,
    hasMinimumRole: (minRole) => {
      const roleHierarchy = ['user', 'admin', 'super_admin'];
      const userLevel = roleHierarchy.indexOf(authState.role);
      const requiredLevel = roleHierarchy.indexOf(minRole);
      return userLevel >= requiredLevel;
    },
    
    // AAL helpers
    hasAAL: (requiredAAL) => {
      const aalLevels = ['aal1', 'aal2', 'aal3'];
      const currentLevel = aalLevels.indexOf(authState.aal);
      const requiredLevel = aalLevels.indexOf(requiredAAL);
      return currentLevel >= requiredLevel;
    }
  };
  
  return (
    <UnifiedKratosAuthContext.Provider value={contextValue}>
      {children}
    </UnifiedKratosAuthContext.Provider>
  );
};

// Hook to use the unified authentication context
export const useUnifiedKratosAuth = () => {
  const context = useContext(UnifiedKratosAuthContext);
  if (!context) {
    throw new Error('useUnifiedKratosAuth must be used within UnifiedKratosAuthProvider');
  }
  return context;
};

// Backward compatibility hooks (for gradual migration)
export const useAuth = useUnifiedKratosAuth;
export const useUnifiedAuth = useUnifiedKratosAuth;
export const useKratos = () => {
  const { user, identity, session, isAuthenticated, isLoading } = useUnifiedKratosAuth();
  return { user, identity, session, isAuthenticated, isLoading };
};
export const useAAL2 = () => {
  const { aal, needsAAL2, canUpgradeAAL, configuredMethods, getStepUpUrl } = useUnifiedKratosAuth();
  return { 
    aal2Status: { 
      aal2_verified: aal === 'aal2',
      needs_verification: needsAAL2,
      passkey_enrolled: configuredMethods.webauthn,
      verification_method: aal === 'aal2' ? 'kratos_native' : null
    },
    getStepUpUrl
  };
};
export const useRole = () => {
  const { role, isAdmin, isSuperAdmin, hasRole, hasMinimumRole } = useUnifiedKratosAuth();
  return { role, isAdmin, isSuperAdmin, hasRole, hasMinimumRole };
};

// Additional backward compatibility exports
export const UnifiedAuthProvider = UnifiedKratosAuthProvider;
export { UnifiedKratosAuthProvider as KratosProviderRefactored };
export { UnifiedKratosAuthProvider as AAL2Provider };

export default UnifiedKratosAuthProvider;