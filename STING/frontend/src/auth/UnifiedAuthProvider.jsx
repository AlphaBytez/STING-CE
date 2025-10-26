import React, { createContext, useContext, useState, useEffect } from 'react';
import { useKratos } from './KratosProviderRefactored';

const UnifiedAuthContext = createContext();

export const useUnifiedAuth = () => {
  const context = useContext(UnifiedAuthContext);
  if (!context) {
    throw new Error('useUnifiedAuth must be used within UnifiedAuthProvider');
  }
  return context;
};

export const UnifiedAuthProvider = ({ children }) => {
  const kratosAuth = useKratos();

  // Listen for authentication events from login flows
  useEffect(() => {
    const handleAuthSuccess = () => {
      // Force Kratos to re-check session after successful auth
      if (kratosAuth.checkSession) {
        kratosAuth.checkSession();
      }
    };

    window.addEventListener('sting-auth-success', handleAuthSuccess);
    return () => window.removeEventListener('sting-auth-success', handleAuthSuccess);
  }, [kratosAuth]);

  // Simplified: Use Kratos as single source of truth
  const isAuthenticated = kratosAuth.isAuthenticated;
  const isLoading = kratosAuth.isLoading;
  const identity = kratosAuth.identity;
  
  // Create user object from Kratos identity
  const user = identity ? {
    id: identity.id,
    email: identity.traits?.email,
    role: identity.traits?.role || 'user',
    ...identity.traits
  } : null;

  // Development logging disabled for cleaner console

  return (
    <UnifiedAuthContext.Provider value={{
      isAuthenticated,
      isLoading,
      identity,
      user,
      kratosAuth,
      // Simplified auth state
      isKratosAuthenticated: kratosAuth.isAuthenticated,
      isCustomAuthenticated: false,
      // Keep Kratos methods
      logout: kratosAuth.logout,
      checkSession: kratosAuth.checkSession,
      requiresAction: kratosAuth.requiresAction
    }}>
      {children}
    </UnifiedAuthContext.Provider>
  );
};