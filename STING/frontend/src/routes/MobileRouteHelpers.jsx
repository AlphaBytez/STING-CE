import React, { lazy, Suspense } from 'react';
import { Outlet, Navigate } from 'react-router-dom';
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
 * Auth guard for mobile routes - wraps with auth check
 */
export const MobileAuthGuard = ({ children }) => {
  const { isAuthenticated, isLoading } = useUnifiedAuth();

  // Show loading spinner while auth is being checked
  if (isLoading) {
    return <MobileLoadingFallback />;
  }

  // Only redirect when auth check is DONE and user is NOT authenticated
  if (!isAuthenticated) {
    // Store the mobile redirect path so login can redirect back
    sessionStorage.setItem('redirectAfterLogin', '/m/');
    return <Navigate to="/login" replace state={{ from: '/m/' }} />;
  }

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
