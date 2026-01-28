import React, { lazy, Suspense, useState, useEffect } from 'react';
import { Outlet, Navigate, useLocation, useNavigate } from 'react-router-dom';
import MobileLayout from '../components/mobile/MobileLayout';
import MobileLoadingSpinner from '../components/mobile/MobileLoadingSpinner';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';

/**
 * Loading fallback for lazy-loaded mobile pages
 */
export const MobileLoadingFallback = () => (
  <div style={{
    minHeight: '200px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#161922',
  }}>
    <MobileLoadingSpinner />
  </div>
);

/**
 * Mobile Loading Screen - matches desktop ColonyLoadingScreen style
 */
const MobileLoadingScreen = ({ message, subMessage }) => (
  <div style={{
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#161922',
    color: '#fff',
    padding: '20px',
    textAlign: 'center',
  }}>
    <MobileLoadingSpinner />
    <p style={{ marginTop: '20px', fontSize: '16px', fontWeight: '500' }}>{message}</p>
    {subMessage && (
      <p style={{ marginTop: '8px', fontSize: '14px', opacity: 0.7 }}>{subMessage}</p>
    )}
  </div>
);

/**
 * Auth guard for mobile routes - matches desktop SimpleProtectedRoute pattern
 * 
 * Handles:
 * 1. Authentication check with cookie detection
 * 2. Session sync during login flow
 * 3. Clean redirects to login
 */
export const MobileAuthGuard = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, identity } = useUnifiedAuth();

  // Session sync state management (matches desktop)
  const [syncAttempts, setSyncAttempts] = useState(0);
  const [syncStartTime, setSyncStartTime] = useState(null);
  const [authCheckComplete, setAuthCheckComplete] = useState(false);

  // Check for valid authentication cookies (matches desktop logic)
  const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    acc[key] = value;
    return acc;
  }, {});

  const hasKratosCookie = cookies['ory_kratos_session'] && cookies['ory_kratos_session'].length > 0;
  const hasStingCookie = cookies['sting_session'] && cookies['sting_session'].length > 0;
  const hasAnyCookies = hasKratosCookie || hasStingCookie;

  const recentAuth = sessionStorage.getItem('sting_recent_auth');
  const isRecentlyAuthenticated = recentAuth && (Date.now() - parseInt(recentAuth)) < 30000; // 30 seconds

  // Clean up stale auth markers (matches desktop)
  useEffect(() => {
    if (recentAuth) {
      const authTime = parseInt(recentAuth);
      if (isAuthenticated) {
        sessionStorage.removeItem('sting_recent_auth');
      } else if (Date.now() - authTime > 30000) {
        sessionStorage.removeItem('sting_recent_auth');
      }
    }
  }, [recentAuth, isAuthenticated]);

  // Mark auth check as complete once identity is loaded
  useEffect(() => {
    if (!isLoading) {
      setAuthCheckComplete(true);
    }
  }, [isLoading]);

  // Session sync timeout management (matches desktop)
  useEffect(() => {
    if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated) && !isLoading) {
      if (!syncStartTime) {
        setSyncStartTime(Date.now());
      }

      const syncTimeout = setTimeout(() => {
        const currentTime = Date.now();
        const syncDuration = currentTime - (syncStartTime || currentTime);

        if (syncDuration > 15000) { // 15 seconds total timeout
          if (syncAttempts < 2) { // Allow 2 retries
            setSyncAttempts(prev => prev + 1);
            setSyncStartTime(Date.now());
            sessionStorage.removeItem('sting_recent_auth');
            localStorage.removeItem('sting_last_passkey_user');
            window.location.reload();
          } else {
            // Give up and redirect to login
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
      <MobileLoadingScreen
        message="Connecting to your Colony"
        subMessage="Verifying authentication..."
      />
    );
  }

  // Determine if we're syncing session
  const isSessionSyncing = !isAuthenticated && isRecentlyAuthenticated && syncStartTime;

  // Only redirect if truly no authentication signs at all
  if (!isAuthenticated && !hasAnyCookies && !isRecentlyAuthenticated && !isLoading && !isSessionSyncing) {
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?return_to=${returnTo}`} state={{ from: location }} replace />;
  }

  // If we have authentication signs but provider says not authenticated, show loading
  if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated)) {
    const syncDuration = syncStartTime ? Math.floor((Date.now() - syncStartTime) / 1000) : 0;
    
    return (
      <MobileLoadingScreen
        message="Synchronizing with your Colony"
        subMessage={`Session coordination in progress... (${syncDuration}s)${syncAttempts > 0 ? ` - Attempt ${syncAttempts + 1} of 3` : ''}${syncDuration > 8 ? ' - Taking longer than expected...' : ''}`}
      />
    );
  }

  // Wait for auth check to complete
  if (!authCheckComplete) {
    return (
      <MobileLoadingScreen
        message="Checking authentication"
        subMessage="Please wait..."
      />
    );
  }

  // Authentication verified - render protected content
  return children || <Outlet />;
};

/**
 * Admin guard for mobile routes
 */
export const MobileAdminGuard = ({ children }) => {
  const { user, isLoading } = useUnifiedAuth();

  if (isLoading) {
    return <MobileLoadingSpinner />;
  }

  const isAdmin = user && (user.role === 'admin' || user.role === 'super_admin');

  if (!isAdmin) {
    return <Navigate to="/m/" replace />;
  }

  return children || <Outlet />;
};

/**
 * MobileLayoutWrapper - Wraps mobile pages with MobileLayout
 * Uses Outlet for child route rendering
 */
export const MobileLayoutWrapper = () => {
  return (
    <MobileAuthGuard>
      <MobileLayout />
    </MobileAuthGuard>
  );
};

// Lazy load all mobile page components
export const MobileDashboard = lazy(() => import('../components/mobile/pages/MobileDashboard'));
export const MobileChat = lazy(() => import('../components/mobile/pages/MobileChat'));
export const MobileBasket = lazy(() => import('../components/mobile/pages/MobileBasket'));
export const MobileSearch = lazy(() => import('../components/mobile/pages/MobileSearch'));
export const MobileReports = lazy(() => import('../components/mobile/pages/MobileReports'));
export const MobileReportDetail = lazy(() => import('../components/mobile/pages/MobileReportDetail'));
export const MobileTemplates = lazy(() => import('../components/mobile/pages/MobileTemplates'));
export const MobileTemplateDetail = lazy(() => import('../components/mobile/pages/MobileTemplateDetail'));
export const MobileHoneyJars = lazy(() => import('../components/mobile/pages/MobileHoneyJars'));
export const MobileHoneyJarDetail = lazy(() => import('../components/mobile/pages/MobileHoneyJarDetail'));
export const MobileSettings = lazy(() => import('../components/mobile/pages/MobileSettings'));
export const MobileProfile = lazy(() => import('../components/mobile/pages/MobileProfile'));
export const MobileSecurity = lazy(() => import('../components/mobile/pages/MobileSecurity'));
export const MobileAdmin = lazy(() => import('../components/mobile/pages/admin/MobileAdmin'));
export const MobileAdminPending = lazy(() => import('../components/mobile/pages/admin/MobileAdminPending'));
export const MobileAdminUsers = lazy(() => import('../components/mobile/pages/admin/MobileAdminUsers'));

/**
 * Wrapper to add Suspense to lazy components
 */
export const withMobileSuspense = (Component) => (
  <Suspense fallback={<MobileLoadingFallback />}>
    <Component />
  </Suspense>
);
