/**
 * Custom hook for managing Authentication Assurance Level (AAL) status
 * Integrates with STING's AAL-based progressive authentication system
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export const useAALStatus = () => {
  const [aalStatus, setAALStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Fetch current AAL status from backend
   */
  const fetchAALStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.get('/api/auth/aal-status', {
        withCredentials: true,
        validateStatus: (status) => status < 500 // Don't throw on 4xx
      });

      if (response.status === 401) {
        // Not authenticated
        setAALStatus(null);
        return null;
      }

      if (response.status !== 200) {
        throw new Error(`AAL status check failed: ${response.status}`);
      }

      const status = response.data;
      setAALStatus(status);
      return status;
      
    } catch (err) {
      console.error('Error fetching AAL status:', err);
      setError(err.message);
      setAALStatus(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Check if user meets AAL requirements for their role
   */
  const isAALCompliant = useCallback(() => {
    if (!aalStatus) return false;
    return aalStatus.validation?.valid === true;
  }, [aalStatus]);

  /**
   * Get missing authentication methods
   */
  const getMissingMethods = useCallback(() => {
    if (!aalStatus?.validation) return [];
    return aalStatus.validation.missing_methods || [];
  }, [aalStatus]);

  /**
   * Check if user needs to set up additional authentication
   */
  const needsSetup = useCallback(() => {
    return !isAALCompliant();
  }, [isAALCompliant]);

  /**
   * Get the required AAL level for user's role
   */
  const getRequiredAAL = useCallback(() => {
    return aalStatus?.requirements?.minimum_aal || 'aal2';
  }, [aalStatus]);

  /**
   * Get user's current AAL level
   */
  const getCurrentAAL = useCallback(() => {
    return aalStatus?.current_aal || 'aal1';
  }, [aalStatus]);

  /**
   * Check if user is admin (needs 3FA)
   */
  const isAdmin = useCallback(() => {
    return aalStatus?.role === 'admin';
  }, [aalStatus]);

  /**
   * Get step-up authentication URL for higher AAL
   * Updated to use custom login UI instead of Kratos login page
   */
  const getStepUpUrl = useCallback((targetAAL = 'aal2', returnUrl = null) => {
    const currentUrl = returnUrl || window.location.href;
    return `/login?aal=${targetAAL}&return_to=${encodeURIComponent(currentUrl)}`;
  }, []);

  /**
   * Initiate step-up authentication flow
   * Updated to use custom login UI instead of Kratos login page
   */
  const initiateStepUp = useCallback(async (targetAAL = 'aal2') => {
    try {
      // Store current location for return after step-up
      const currentUrl = window.location.href;
      sessionStorage.setItem('redirectAfterLogin', currentUrl);
      
      // Redirect to custom login UI with AAL parameter
      const stepUpUrl = getStepUpUrl(targetAAL, currentUrl);
      window.location.href = stepUpUrl;
      
      return { step_up_url: stepUpUrl };
    } catch (err) {
      console.error('Error initiating step-up:', err);
      throw err;
    }
  }, [getStepUpUrl]);

  /**
   * Get authentication requirements for current user role
   */
  const getRequirements = useCallback(() => {
    return aalStatus?.requirements || {
      minimum_aal: 'aal2',
      required_methods: ['webauthn'],
      allow_alternatives: true,
      description: 'Regular users require 2FA (passkey or TOTP)'
    };
  }, [aalStatus]);

  /**
   * Check if user can access dashboard without additional auth
   */
  const canAccessDashboard = useCallback(() => {
    return aalStatus?.can_access_dashboard === true;
  }, [aalStatus]);

  // Fetch AAL status on mount and when session changes
  useEffect(() => {
    fetchAALStatus();
  }, [fetchAALStatus]);

  // Listen for session changes to refresh AAL status
  useEffect(() => {
    const handleSessionChange = () => {
      console.log('🔐 Session change detected, refreshing AAL status...');
      fetchAALStatus();
    };

    // Listen for custom session change events
    window.addEventListener('kratos-session-changed', handleSessionChange);
    window.addEventListener('aal-status-refresh', handleSessionChange);

    return () => {
      window.removeEventListener('kratos-session-changed', handleSessionChange);
      window.removeEventListener('aal-status-refresh', handleSessionChange);
    };
  }, [fetchAALStatus]);

  return {
    // State
    aalStatus,
    isLoading,
    error,
    
    // Actions
    fetchAALStatus,
    initiateStepUp,
    
    // Computed values
    isAALCompliant,
    needsSetup,
    getMissingMethods,
    getRequiredAAL,
    getCurrentAAL,
    isAdmin,
    getStepUpUrl,
    getRequirements,
    canAccessDashboard
  };
};

export default useAALStatus;