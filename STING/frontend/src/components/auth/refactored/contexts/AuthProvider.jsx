import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import axios from 'axios';

// Auth state actions
const AUTH_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_SUCCESS_MESSAGE: 'SET_SUCCESS_MESSAGE',
  SET_USER_EMAIL: 'SET_USER_EMAIL',
  SET_BIOMETRIC_AVAILABLE: 'SET_BIOMETRIC_AVAILABLE',
  SET_HAS_PASSKEY: 'SET_HAS_PASSKEY',
  SET_FLOW_DATA: 'SET_FLOW_DATA',
  SET_AUTH_CAPABILITIES: 'SET_AUTH_CAPABILITIES',
  CLEAR_MESSAGES: 'CLEAR_MESSAGES',
  SET_SYNC_STATUS: 'SET_SYNC_STATUS',
  SET_CACHED_CREDENTIALS: 'SET_CACHED_CREDENTIALS'
};

// Initial auth state
const initialState = {
  // UI State
  isLoading: false,
  error: '',
  successMessage: '',
  
  // User Data
  userEmail: '',
  
  // Capabilities
  biometricAvailable: false,
  hasRegisteredPasskey: false,
  
  // Flow Data
  flowData: null,
  
  // Auth Capabilities
  authCapabilities: {
    webauthnSupported: false,
    platformAuthenticatorAvailable: false,
    hasConfiguredMethods: false,
    availableMethods: {}
  },
  
  // Sync Status
  syncStatus: {
    isActive: false,
    message: '',
    progress: null
  },
  
  // Cached Credentials (for AAL1→AAL2 transition)
  cachedCredentials: null
};

// Auth reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.SET_LOADING:
      return { ...state, isLoading: action.payload };
      
    case AUTH_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload, isLoading: false };
      
    case AUTH_ACTIONS.SET_SUCCESS_MESSAGE:
      return { ...state, successMessage: action.payload, error: '' };
      
    case AUTH_ACTIONS.SET_USER_EMAIL:
      return { ...state, userEmail: action.payload };
      
    case AUTH_ACTIONS.SET_BIOMETRIC_AVAILABLE:
      return { ...state, biometricAvailable: action.payload };
      
    case AUTH_ACTIONS.SET_HAS_PASSKEY:
      return { ...state, hasRegisteredPasskey: action.payload };
      
    case AUTH_ACTIONS.SET_FLOW_DATA:
      return { ...state, flowData: action.payload };
      
    case AUTH_ACTIONS.SET_AUTH_CAPABILITIES:
      return { ...state, authCapabilities: { ...state.authCapabilities, ...action.payload } };
      
    case AUTH_ACTIONS.CLEAR_MESSAGES:
      return { ...state, error: '', successMessage: '' };
      
    case AUTH_ACTIONS.SET_SYNC_STATUS:
      return { ...state, syncStatus: { ...state.syncStatus, ...action.payload } };
      
    case AUTH_ACTIONS.SET_CACHED_CREDENTIALS:
      return { ...state, cachedCredentials: action.payload };
      
    default:
      return state;
  }
}

// Auth context
const AuthContext = createContext();

// Auth provider component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);
  
  // Action creators
  const actions = {
    setLoading: (loading) => dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: loading }),
    setError: (error) => dispatch({ type: AUTH_ACTIONS.SET_ERROR, payload: error }),
    setSuccessMessage: (message) => dispatch({ type: AUTH_ACTIONS.SET_SUCCESS_MESSAGE, payload: message }),
    setUserEmail: (email) => dispatch({ type: AUTH_ACTIONS.SET_USER_EMAIL, payload: email }),
    setBiometricAvailable: (available) => dispatch({ type: AUTH_ACTIONS.SET_BIOMETRIC_AVAILABLE, payload: available }),
    setHasPasskey: (hasPasskey) => dispatch({ type: AUTH_ACTIONS.SET_HAS_PASSKEY, payload: hasPasskey }),
    setFlowData: (data) => dispatch({ type: AUTH_ACTIONS.SET_FLOW_DATA, payload: data }),
    setAuthCapabilities: (capabilities) => dispatch({ type: AUTH_ACTIONS.SET_AUTH_CAPABILITIES, payload: capabilities }),
    clearMessages: () => dispatch({ type: AUTH_ACTIONS.CLEAR_MESSAGES }),
    setSyncStatus: (status) => dispatch({ type: AUTH_ACTIONS.SET_SYNC_STATUS, payload: status }),
    setCachedCredentials: (credentials) => dispatch({ type: AUTH_ACTIONS.SET_CACHED_CREDENTIALS, payload: credentials })
  };
  
  // Initialize authentication capabilities (with singleton pattern to prevent multiple calls)
  const initializeAuthCapabilities = useCallback(async () => {
    // Prevent multiple initializations during component re-mounts
    if (window.__stingAuthInitialized) {
      console.log('🔐 Auth capabilities already initialized, skipping...');
      return;
    }
    
    try {
      // Check WebAuthn support
      const webauthnSupported = !!window.PublicKeyCredential;
      const platformAuthenticatorAvailable = webauthnSupported 
        ? await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable() 
        : false;
      
      dispatch({
        type: AUTH_ACTIONS.SET_AUTH_CAPABILITIES,
        payload: {
          webauthnSupported,
          platformAuthenticatorAvailable
        }
      });
      
      console.log('🔐 Auth capabilities initialized:', {
        webauthnSupported,
        platformAuthenticatorAvailable
      });
      
      // Mark as initialized to prevent multiple calls
      window.__stingAuthInitialized = true;
    } catch (error) {
      console.error('🔐 Error initializing auth capabilities:', error);
    }
  }, []);
  
  // Initialize capabilities on mount
  useEffect(() => {
    initializeAuthCapabilities();
  }, [initializeAuthCapabilities]);
  
  // Check user's configured authentication methods
  const checkUserAuthMethods = async (email) => {
    if (!email) return null;
    
    try {
      const response = await axios.post('/api/auth/check-configured-methods', {
        email: email
      }, {
        withCredentials: true,
        headers: { 'Content-Type': 'application/json' }
      });
      
      const methods = {
        hasTotp: response.data?.has_totp || false,
        hasWebAuthn: response.data?.has_webauthn || false,
        passkeyCount: response.data?.passkey_count || 0,
        customPasskeys: response.data?.passkey_details?.custom_passkeys || 0
      };
      
      actions.setAuthCapabilities({
        hasConfiguredMethods: methods.hasTotp || methods.hasWebAuthn,
        availableMethods: methods
      });
      
      console.log('🔐 User auth methods checked:', methods);
      return methods;
    } catch (error) {
      console.error('🔐 Error checking user auth methods:', error);
      return null;
    }
  };
  
  // Check if email has passkeys - simplified for Kratos-native auth
  const checkEmailPasskeys = async (email) => {
    if (!email || !email.includes('@')) return false;
    
    console.log('🔐 Passkey check deprecated with Kratos-native auth for:', email);
    
    // With Kratos-native auth, we don't pre-check for passkeys by email
    // Users will discover passkey availability during the authentication flow
    actions.setHasPasskey(false);
    actions.setBiometricAvailable(false);
    
    return false;
  };
  
  // Cache current session credentials for AAL2 transition
  const cacheCurrentCredentials = async () => {
    try {
      console.log('🔒 Caching current session credentials for AAL2 transition...');
      
      const sessionResponse = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        const credentials = sessionData?.identity?.credentials;
        
        if (credentials) {
          const cachedData = {
            timestamp: Date.now(),
            email: sessionData.identity?.traits?.email,
            credentials: {
              totp: credentials.totp ? {
                identifiers: credentials.totp.identifiers || []
              } : null,
              webauthn: credentials.webauthn ? {
                identifiers: credentials.webauthn.identifiers || []
              } : null
            }
          };
          
          actions.setCachedCredentials(cachedData);
          console.log('🔒 Cached credentials for AAL2:', cachedData);
          return cachedData;
        }
      }
    } catch (error) {
      console.warn('🔒 Failed to cache credentials:', error);
    }
    return null;
  };

  // Dispatch authentication success event
  const dispatchAuthSuccess = (method, aalLevel = 'aal1', kratosSessionCreated = false) => {
    console.log('🔐 Dispatching auth success event:', { method, aalLevel, kratosSessionCreated });
    
    window.dispatchEvent(new CustomEvent('sting-auth-success', {
      detail: { method, aalLevel, kratosSessionCreated }
    }));
    
    // Mark recent authentication
    const authTimestamp = Date.now().toString();
    sessionStorage.setItem('sting_recent_auth', authTimestamp);
  };
  
  // Context value
  const value = {
    // State
    ...state,
    
    // Actions
    ...actions,
    
    // Helper functions
    checkUserAuthMethods,
    checkEmailPasskeys,
    dispatchAuthSuccess,
    initializeAuthCapabilities,
    cacheCurrentCredentials
  };
  
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { AUTH_ACTIONS };