/**
 * Simple Protected Route - Clean Route Protection
 * 
 * Simplified route protection that handles:
 * 1. Authentication check
 * 2. Admin AAL2 requirement  
 * 3. Clean redirects to simplified login
 */

import React, { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from './UnifiedAuthProvider';
import { useKratos } from './KratosProviderRefactored';
import ColonyLoadingScreen from '../components/common/ColonyLoadingScreen';
import { useColonyLoading } from '../hooks/useColonyLoading';

const SimpleProtectedRoute = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, identity } = useUnifiedAuth();
  const { session } = useKratos(); // Use same data source as working providers

  // Colony loading screen
  const {
    isVisible: loadingVisible,
    showAuthLoading,
    showAAL2Loading,
    hideLoading,
    updateMessage
  } = useColonyLoading();

  // Session sync state management
  const [syncAttempts, setSyncAttempts] = useState(0);
  const [syncStartTime, setSyncStartTime] = useState(null);

  // Authentication state check completion
  const [authCheckComplete, setAuthCheckComplete] = useState(false);

  // IMPROVED: More accurate authentication state detection
  // Check for valid authentication cookies (not just presence)
  // Cookie values will be empty strings if deleted, so check for actual values
  const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    acc[key] = value;
    return acc;
  }, {});

  const hasKratosCookie = cookies['ory_kratos_session'] && cookies['ory_kratos_session'].length > 0;
  const hasStingCookie = cookies['sting_session'] && cookies['sting_session'].length > 0;
  const hasAnyCookies = hasKratosCookie || hasStingCookie;

  const recentAuth = sessionStorage.getItem('sting_recent_auth');
  const isRecentlyAuthenticated = recentAuth && (Date.now() - parseInt(recentAuth)) < 30000; // 30 seconds for auth sync

  // Clean up stale auth markers to prevent them from getting stuck
  // Also clear the marker when authentication succeeds
  useEffect(() => {
    if (recentAuth) {
      const authTime = parseInt(recentAuth);
      // Clear if authentication succeeded or if marker is old
      if (isAuthenticated) {
        // Authentication succeeded, clearing marker
        sessionStorage.removeItem('sting_recent_auth');
      } else if (Date.now() - authTime > 30000) { // Clear if older than 30 seconds
        // Clearing stale auth marker
        sessionStorage.removeItem('sting_recent_auth');
      }
    }
  }, [recentAuth, isAuthenticated]);
  
  // Define isAdmin before using it in useEffect
  const isAdmin = identity?.traits?.role === 'admin';
  
  // Mark auth check as complete once identity is loaded
  useEffect(() => {
    if (!isLoading) {
      setAuthCheckComplete(true);
    }
  }, [isLoading]);

  // Session sync timeout management - MUST be called before any returns
  useEffect(() => {
    if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated) && !isLoading) {
      // Start sync timer if not started
      if (!syncStartTime) {
        setSyncStartTime(Date.now());
        // Starting session sync
      }

      // Set timeout for sync attempt
      const syncTimeout = setTimeout(() => {
        const currentTime = Date.now();
        const syncDuration = currentTime - (syncStartTime || currentTime);

        if (syncDuration > 15000) { // 15 seconds total timeout for session sync (increased from 10)
          if (syncAttempts < 2) { // Allow 2 retries
            // Try one more time
            // Session sync timeout, retrying
            setSyncAttempts(prev => prev + 1);
            setSyncStartTime(Date.now());
            // Instead of reload, try clearing stale session data first
            sessionStorage.removeItem('sting_recent_auth');
            localStorage.removeItem('sting_last_passkey_user');
            window.location.reload();
          } else {
            // Give up and redirect to login with cleanup
            // Session sync failed, redirecting to login
            sessionStorage.removeItem('sting_recent_auth');
            localStorage.removeItem('sting_last_passkey_user');
            navigate('/login?session_sync_failed=true', { replace: true });
          }
        }
      }, 3000); // 3 second check interval

      return () => clearTimeout(syncTimeout);
    }
  }, [isAuthenticated, hasAnyCookies, isRecentlyAuthenticated, isLoading, syncAttempts, syncStartTime, navigate]);
  
  // Show loading spinner while authentication state is being determined
  if (isLoading) {
    return (
      <ColonyLoadingScreen
        isVisible={true}
        message="Connecting to your Colony"
        subMessage="Verifying authentication..."
      />
    );
  }

  // Only redirect if truly no authentication signs at all AND auth check is complete
  // BUT NOT if we're in the middle of session sync
  const isSessionSyncing = !isAuthenticated && isRecentlyAuthenticated && syncStartTime;

  if (!isAuthenticated && !hasAnyCookies && !isRecentlyAuthenticated && !isLoading && !isSessionSyncing) {
    // User not authenticated, redirecting to login
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?return_to=${returnTo}`} state={{ from: location }} replace />;
  }
  
  // If we have authentication signs but provider says not authenticated, show loading
  if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated)) {
    // Authentication provider not ready, waiting...
    const syncDuration = syncStartTime ? Math.floor((Date.now() - syncStartTime) / 1000) : 0;
    
    return (
      <ColonyLoadingScreen
        isVisible={true}
        message="Synchronizing with your Colony"
        subMessage={`Session coordination in progress... (${syncDuration}s)${syncAttempts > 0 ? ` - Attempt ${syncAttempts + 1} of 3` : ''}${syncDuration > 8 ? ' - Taking longer than expected...' : ''}`}
      />
    );
  }

  // Wait for auth check to complete
  if (!authCheckComplete) {
    return (
      <ColonyLoadingScreen
        isVisible={true}
        message="Checking authentication"
        subMessage="Please wait..."
      />
    );
  }

  // Authentication verified - render protected content
  // Note: Tiered authentication will be handled by individual operations
  
  return children;
};

export default SimpleProtectedRoute;