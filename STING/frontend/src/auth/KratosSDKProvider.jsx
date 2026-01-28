import React, { createContext, useContext, useEffect, useState } from 'react';
import { Configuration, FrontendApi } from '@ory/kratos-client';
import { useNavigate } from 'react-router-dom';

// Create Kratos client
const kratosConfig = new Configuration({
  basePath: process.env.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433',
  baseOptions: {
    withCredentials: true, // Important for cookies
  },
});

const kratos = new FrontendApi(kratosConfig);

// Context
const KratosContext = createContext({});

export const useKratosSDK = () => useContext(KratosContext);

export const KratosSDKProvider = ({ children }) => {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check session on mount and when needed
  const checkSession = async () => {
    try {
      setLoading(true);
      const { data } = await kratos.toSession();
      setSession(data);
      setError(null);
      return data;
    } catch (err) {
      console.error('Session check failed:', err);
      setSession(null);
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Initialize login flow
  const initializeLogin = async () => {
    try {
      const { data } = await kratos.createBrowserLoginFlow();
      return data;
    } catch (err) {
      console.error('Failed to initialize login:', err);
      throw err;
    }
  };

  // Initialize registration flow
  const initializeRegistration = async () => {
    try {
      const { data } = await kratos.createBrowserRegistrationFlow();
      return data;
    } catch (err) {
      console.error('Failed to initialize registration:', err);
      throw err;
    }
  };

  // Initialize settings flow
  const initializeSettings = async () => {
    try {
      const { data } = await kratos.createBrowserSettingsFlow();
      return data;
    } catch (err) {
      // If 403, user needs to authenticate first
      if (err.response?.status === 403) {
        navigate('/login');
        return null;
      }
      console.error('Failed to initialize settings:', err);
      throw err;
    }
  };

  // Submit flow (works for login, registration, settings, etc.)
  const submitFlow = async (flowId, method, body) => {
    try {
      const { data } = await kratos.updateLoginFlow({
        flow: flowId,
        updateLoginFlowBody: {
          method,
          ...body,
        },
      });
      
      // After successful login/registration, check session
      if (data.session) {
        setSession(data.session);
      }
      
      return data;
    } catch (err) {
      console.error('Flow submission failed:', err);
      throw err;
    }
  };

  // Logout
  const logout = async () => {
    try {
      const { data } = await kratos.createBrowserLogoutFlow();
      // Redirect to logout URL
      window.location.href = data.logout_url;
    } catch (err) {
      console.error('Logout failed:', err);
      // Fallback - clear session and redirect
      setSession(null);
      navigate('/login');
    }
  };

  // Check if user needs any action
  const checkRequiredAction = () => {
    if (!session) return null;
    
    // Check if email needs verification
    if (session.identity?.verifiable_addresses?.some(addr => !addr.verified)) {
      return 'VERIFY_EMAIL';
    }
    
    // Add other checks as needed
    return null;
  };

  // Check session on mount
  useEffect(() => {
    checkSession();
  }, []);

  // Handle authentication errors globally
  useEffect(() => {
    if (error?.response?.status === 401 || error?.response?.status === 403) {
      // Session expired or invalid
      navigate('/login');
    }
  }, [error, navigate]);

  const value = {
    // State
    session,
    loading,
    error,
    identity: session?.identity,
    authenticated: !!session?.active,
    
    // Methods
    checkSession,
    initializeLogin,
    initializeRegistration,
    initializeSettings,
    submitFlow,
    logout,
    checkRequiredAction,
    
    // Direct access to Kratos client for advanced use
    kratos,
  };

  return (
    <KratosContext.Provider value={value}>
      {children}
    </KratosContext.Provider>
  );
};