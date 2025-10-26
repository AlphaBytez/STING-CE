import React, { createContext, useContext, useState, useEffect } from 'react';

const UnifiedAuthContext = createContext();

export const useUnifiedAuth = () => {
  const context = useContext(UnifiedAuthContext);
  if (!context) {
    throw new Error('useUnifiedAuth must be used within CleanUnifiedAuthProvider');
  }
  return context;
};

export const CleanUnifiedAuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [identity, setIdentity] = useState(null);
  const [user, setUser] = useState(null);

  // Direct session checking (like RoleContext) instead of broken useKratos() hook
  const checkSession = async () => {
    try {
      setIsLoading(true);
      
      // Use the same approach that works in RoleContext and your console test
      const response = await fetch('/.ory/sessions/whoami', {
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      });

      if (response.ok) {
        const sessionData = await response.json();
        console.log('🔄 CleanUnifiedAuth: Valid Kratos session detected:', sessionData);
        
        setIsAuthenticated(true);
        setIdentity(sessionData.identity);
        
        // Create user object with combined Kratos + STING database data
        let userData = null;
        if (sessionData.identity) {
          // Start with Kratos identity data
          userData = {
            id: sessionData.identity.id,
            email: sessionData.identity.traits?.email,
            role: sessionData.identity.traits?.role || 'user',
            aal: sessionData.authenticator_assurance_level || 'aal1',
            sessionId: sessionData.id,
            // Auth method detection from Kratos session
            hasTotp: sessionData.authentication_methods?.some(m => m.method === 'totp') || false,
            hasKratosWebauthn: sessionData.authentication_methods?.some(m => m.method === 'webauthn') || false,
            ...sessionData.identity.traits
          };

          // Fetch STING database profile data to complement Kratos data
          try {
            const profileResponse = await fetch('/api/auth/me', {
              credentials: 'include',
              headers: { 'Accept': 'application/json' }
            });
            
            if (profileResponse.ok) {
              const profileData = await profileResponse.json();
              console.log('🔄 CleanUnifiedAuth: STING profile data:', profileData);
              
              // Merge STING database fields with Kratos data
              userData = {
                ...userData,
                // STING database profile fields (these were missing!)
                isAdmin: profileData.is_admin || (userData.role === 'admin'),
                stingUserId: profileData.id,
                displayName: profileData.display_name,
                firstName: profileData.first_name,
                lastName: profileData.last_name,
                organization: profileData.organization,
                // Custom passkey data from STING database
                hasStingPasskeys: profileData.has_passkeys || false,
                passkeyCount: profileData.passkey_count || 0
              };
            } else {
              console.log('⚠️ CleanUnifiedAuth: Could not fetch STING profile, using Kratos-only data');
              // Fallback to Kratos-derived data
              userData.isAdmin = (userData.role === 'admin');
            }
          } catch (profileError) {
            console.warn('🔒 CleanUnifiedAuth: Profile fetch error:', profileError);
            userData.isAdmin = (userData.role === 'admin');
          }
        }
        
        setUser(userData);
        
        console.log('✅ CleanUnifiedAuth: Session state updated:', {
          isAuthenticated: true,
          aal: sessionData.authenticator_assurance_level,
          email: userData?.email
        });
      } else {
        console.log('🔒 CleanUnifiedAuth: No valid session found');
        setIsAuthenticated(false);
        setIdentity(null);
        setUser(null);
      }
    } catch (error) {
      console.error('🔒 CleanUnifiedAuth: Session check error:', error);
      setIsAuthenticated(false);
      setIdentity(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Check session on mount
  useEffect(() => {
    checkSession();
  }, []);

  // Listen for authentication events
  useEffect(() => {
    const handleAuthSuccess = () => {
      console.log('📱 CleanUnifiedAuth: Auth success event, checking session');
      setTimeout(() => checkSession(), 100); // Small delay for session establishment
    };

    const handleEnrollmentComplete = () => {
      console.log('📱 CleanUnifiedAuth: Enrollment complete event, checking session');
      setTimeout(() => checkSession(), 100);
    };

    window.addEventListener('sting-auth-success', handleAuthSuccess);
    window.addEventListener('sting-enrollment-complete', handleEnrollmentComplete);
    
    return () => {
      window.removeEventListener('sting-auth-success', handleAuthSuccess);
      window.removeEventListener('sting-enrollment-complete', handleEnrollmentComplete);
    };
  }, []);

  const logout = async () => {
    try {
      // Clear local state immediately
      setIsAuthenticated(false);
      setIdentity(null);
      setUser(null);
      
      // Call Kratos logout
      await fetch('/.ory/self-service/logout/browser', {
        credentials: 'include'
      });
      
      console.log('✅ CleanUnifiedAuth: Logout completed');
    } catch (error) {
      console.error('🔒 CleanUnifiedAuth: Logout error:', error);
    }
  };

  return (
    <UnifiedAuthContext.Provider value={{
      isAuthenticated,
      isLoading,
      identity,
      user,
      checkSession,
      logout,
      // Keep compatibility with existing components
      isKratosAuthenticated: isAuthenticated,
      isCustomAuthenticated: false,
      requiresAction: () => false // Simplified
    }}>
      {children}
    </UnifiedAuthContext.Provider>
  );
};