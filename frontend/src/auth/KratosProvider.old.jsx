import React, { createContext, useContext, useState, useEffect } from 'react';
import kratosApi from '../utils/kratosConfig';
import { api } from '../utils/apiClient';

// Create a context for Kratos authentication
const KratosContext = createContext(null);

/**
 * KratosProvider - Central authentication state provider that integrates with Ory Kratos
 * 
 * This provider:
 * 1. Manages authentication state
 * 2. Provides user identity information when authenticated
 * 3. Exposes authentication-related methods (login, logout, etc.)
 * 4. Tracks custom user attributes like account type
 */
export const KratosProvider = ({ children }) => {
  // Base state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [identity, setIdentity] = useState(null);
  
  // Extended user attributes (from your application)
  const [accountType, setAccountType] = useState(null);
  const [userSettings, setUserSettings] = useState(null);
  
  // Get Kratos URL from environment
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Check authentication status on mount and when kratosUrl changes
  useEffect(() => {
    const checkAuth = async () => {
      try {
        setIsLoading(true);
        console.log('[KratosProvider] Checking authentication at:', kratosApi.whoami());
        console.log('[KratosProvider] Current cookies:', document.cookie);
        console.log('[KratosProvider] Looking for ory_session cookie...');
        
        // Use the backend session proxy instead of direct Kratos call
        const response = await fetch('/api/session/whoami', {
          credentials: 'include',
        });
        
        console.log('[KratosProvider] Auth check response:', response.status, response.statusText);
        
        if (response.ok) {
          const data = await response.json();
          console.log('[KratosProvider] User authenticated:', data);
          console.log('[KratosProvider] Session details:', {
            id: data.id,
            active: data.active,
            traits: data.identity?.traits,
            expires_at: data.expires_at,
            authenticated_at: data.authenticated_at,
            identity_id: data.identity?.id,
            identity_email: data.identity?.traits?.email
          });
          setIsAuthenticated(true);
          setIdentity(data.identity);
          
          // If you store extended user data in Kratos metadata, extract it
          if (data.identity?.metadata_public) {
            try {
              const metadata = data.identity.metadata_public;
              setAccountType(metadata.account_type || 'standard');
              // Extract any other custom fields
            } catch (err) {
              console.error('Error parsing user metadata:', err);
            }
          } else {
            // If not in Kratos, fetch from your own API
            await fetchUserExtendedData(data.identity.id);
          }
        } else {
          // Not authenticated
          console.log('[KratosProvider] User not authenticated, status:', response.status);
          const errorText = await response.text();
          console.log('[KratosProvider] Error response:', errorText);
          console.log('[KratosProvider] Check if cookies are being blocked or not sent');
          setIsAuthenticated(false);
          setIdentity(null);
          setAccountType(null);
          setUserSettings(null);
        }
      } catch (err) {
        console.error('Authentication check failed:', err);
        setIsAuthenticated(false);
        setIdentity(null);
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, [kratosUrl]);
  
  // Fetch additional user data from your own API
  const fetchUserExtendedData = async (userId) => {
    try {
      // Replace with your API endpoint
      const apiUrl = window.env?.REACT_APP_API_URL || 'https://localhost:5050';
      // Check if we're in development mode
      const isDev = window.env?.NODE_ENV === 'development' || !window.env?.NODE_ENV;
      
      if (isDev) {
        // In development mode, use mock data to avoid certificate issues
        console.log('Development mode: Using mock user data');
        setAccountType('standard');
        setUserSettings({
          theme: 'blue',
          notifications: { email: true, push: true }
        });
        return;
      }
      
      // In production mode, make the actual API call
      const response = await fetch(`${apiUrl}/api/users/${userId}/profile`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const userData = await response.json();
        setAccountType(userData.accountType || 'standard');
        setUserSettings(userData.settings || {});
      }
    } catch (err) {
      console.error('Failed to fetch extended user data:', err);
      // Set defaults even if API call fails
      setAccountType('standard');
      setUserSettings(null);
    }
  };
  
  // Handle login - redirect to Kratos
  const login = () => {
    // Use the public URL from env if available
    const originUrl = window.env?.PUBLIC_URL || window.location.origin;
    const returnTo = encodeURIComponent(originUrl + '/dashboard');
    
    console.log(`Redirecting to Kratos login...`);
    console.log(`Return URL: ${returnTo}`);
    console.log(`Kratos URL: ${kratosUrl}`);
    console.log(`Full URL: ${kratosUrl}/self-service/login/browser?return_to=${returnTo}`);
    
    // Use fetch to check if we can connect to Kratos
    fetch(kratosApi.healthAlive(), { 
      method: 'GET',
      credentials: 'include'
    })
    .then(() => {
      console.log('Kratos health check OK, redirecting to login');
      window.location.href = `${kratosUrl}/self-service/login/browser?return_to=${returnTo}`;
    })
    .catch(err => {
      console.error('Kratos health check failed, trying direct URL anyway:', err);
      window.location.href = `${kratosUrl}/self-service/login/browser?return_to=${returnTo}`;
    });
  };
  
  // Handle registration - redirect to Kratos
  const register = () => {
    const returnTo = encodeURIComponent(window.location.origin + '/dashboard');
    window.location.href = `${kratosUrl}/self-service/registration/browser?return_to=${returnTo}`;
  };
  
  // Handle password recovery - redirect to Kratos
  const recover = () => {
    const returnTo = encodeURIComponent(window.location.origin + '/recovery');
    window.location.href = `${kratosUrl}/self-service/recovery/browser?return_to=${returnTo}`;
  };
  
  // Handle logout - Use our dedicated logout page for better UX
  const logout = () => {
    console.log('KratosProvider: Starting logout process...');
    
    // Clear all local storage
    localStorage.clear();
    sessionStorage.clear();
    
    // Clear all cookies (best effort - some are httpOnly)
    const clearCookie = (name) => {
      // Clear with various domain and path combinations
      const domains = ['', 'localhost', '.localhost', window.location.hostname];
      const paths = ['/', '/dashboard', '/api'];
      
      domains.forEach(domain => {
        paths.forEach(path => {
          const domainPart = domain ? `; domain=${domain}` : '';
          document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path}${domainPart}`;
        });
      });
    };
    
    // Clear all existing cookies
    document.cookie.split(";").forEach((c) => {
      const cookieName = c.split('=')[0].trim();
      if (cookieName) {
        clearCookie(cookieName);
      }
    });
    
    // Explicitly clear known session cookies
    ['ory_kratos_session', 'ory_kratos_session', 'ory_session', 
     'sting_session', 'session', 'flask_session',
     'ory_kratos_continuity', 'csrf_token'].forEach(clearCookie);
    
    // Prevent credential access for WebAuthn
    if (navigator.credentials && navigator.credentials.preventSilentAccess) {
      navigator.credentials.preventSilentAccess().catch(() => {
        // Ignore errors from browsers that don't support this
      });
    }
    
    // Clear auth state immediately
    setIsAuthenticated(false);
    setIdentity(null);
    setAccountType(null);
    setUserSettings(null);
    
    // Force hard navigation to logout page with cache bypass
    window.location.replace('/logout?t=' + Date.now());
  };
  
  // Update account type (through your API)
  const updateAccountType = async (newType) => {
    if (!identity?.id) return;
    
    try {
      const apiUrl = window.env?.REACT_APP_API_URL || 'https://localhost:5050';
      const response = await fetch(`${apiUrl}/api/users/${identity.id}/account-type`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ accountType: newType }),
      });
      
      if (response.ok) {
        setAccountType(newType);
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to update account type:', err);
      return false;
    }
  };
  
  // Check session method - returns session data if authenticated
  const checkSession = async () => {
    try {
      console.log('[KratosProvider] Checking session...');
      const response = await fetch(kratosApi.whoami(), {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('[KratosProvider] Session check successful:', data);
        setIsAuthenticated(true);
        setIdentity(data.identity);
        return data;
      } else {
        console.log('[KratosProvider] Session check failed:', response.status);
        setIsAuthenticated(false);
        setIdentity(null);
        return null;
      }
    } catch (err) {
      console.error('[KratosProvider] Session check error:', err);
      return null;
    }
  };

  // Create context value with all authentication state and methods
  const contextValue = {
    // Auth state
    isAuthenticated,
    isLoading,
    identity,
    accountType,
    userSettings,
    
    // Auth methods
    login,
    register,
    recover,
    logout,
    checkSession,
    
    // App-specific methods
    updateAccountType,
    
    // Utility
    kratosUrl,
  };
  
  return (
    <KratosContext.Provider value={contextValue}>
      {children}
    </KratosContext.Provider>
  );
};

// Custom hook for using the auth context
export const useKratos = () => {
  const context = useContext(KratosContext);
  
  if (!context) {
    throw new Error('useKratos must be used within a KratosProvider');
  }
  
  return context;
};