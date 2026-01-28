import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MobileLayout from '../components/mobile/MobileLayout';
import MobileLoadingSpinner from '../components/mobile/MobileLoadingSpinner';
import MobileTest from '../components/mobile/MobileTest';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';

/**
 * Loading fallback for lazy-loaded mobile pages
 */
const LoadingFallback = () => (
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
 * Auth guard for mobile routes
 */
const RequireAuth = ({ children }) => {
  const { isAuthenticated, isLoading } = useUnifiedAuth();

  // Don't block rendering while checking auth
  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: '/m/' }} />;
  }

  return children;
};

/**
 * Admin guard for mobile routes
 */
const RequireAdmin = ({ children }) => {
  const { user, isLoading } = useUnifiedAuth();

  if (isLoading) {
    return <MobileLoadingSpinner />;
  }

  const isAdmin = user && (user.role === 'admin' || user.role === 'super_admin');

  if (!isAdmin) {
    return <Navigate to="/m/" replace />;
  }

  return children;
};

// Lazy load all mobile page components
const MobileDashboard = lazy(() => import('../components/mobile/pages/MobileDashboard'));
const MobileChat = lazy(() => import('../components/mobile/pages/MobileChat'));
const MobileBasket = lazy(() => import('../components/mobile/pages/MobileBasket'));
const MobileSearch = lazy(() => import('../components/mobile/pages/MobileSearch'));
const MobileReports = lazy(() => import('../components/mobile/pages/MobileReports'));
const MobileReportDetail = lazy(() => import('../components/mobile/pages/MobileReportDetail'));
const MobileTemplates = lazy(() => import('../components/mobile/pages/MobileTemplates'));
const MobileTemplateDetail = lazy(() => import('../components/mobile/pages/MobileTemplateDetail'));
const MobileHoneyJars = lazy(() => import('../components/mobile/pages/MobileHoneyJars'));
const MobileHoneyJarDetail = lazy(() => import('../components/mobile/pages/MobileHoneyJarDetail'));
const MobileSettings = lazy(() => import('../components/mobile/pages/MobileSettings'));
const MobileProfile = lazy(() => import('../components/mobile/pages/MobileProfile'));
const MobileSecurity = lazy(() => import('../components/mobile/pages/MobileSecurity'));
const MobileAdmin = lazy(() => import('../components/mobile/pages/admin/MobileAdmin'));
const MobileAdminPending = lazy(() => import('../components/mobile/pages/admin/MobileAdminPending'));
const MobileAdminUsers = lazy(() => import('../components/mobile/pages/admin/MobileAdminUsers'));

/**
 * MobileRoutesComponent - Renders all mobile routes using standard Routes/Route
 * This is used inside the main BrowserRouter
 */
const MobileRoutesComponent = () => {
  return (
    <Routes>
      {/* Test route - no auth, no lazy loading */}
      <Route path="test" element={<MobileTest />} />

      {/* Main mobile app with layout and auth */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <MobileLayout />
          </RequireAuth>
        }
      >
        {/* Dashboard (default) */}
        <Route
          index
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileDashboard />
            </Suspense>
          }
        />

        {/* Chat routes */}
        <Route
          path="chat"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileChat />
            </Suspense>
          }
        />
        <Route
          path="chat/:conversationId"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileChat />
            </Suspense>
          }
        />

        {/* Core features */}
        <Route
          path="basket"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileBasket />
            </Suspense>
          }
        />
        <Route
          path="search"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileSearch />
            </Suspense>
          }
        />

        {/* Reports */}
        <Route
          path="reports"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileReports />
            </Suspense>
          }
        />
        <Route
          path="reports/:id"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileReportDetail />
            </Suspense>
          }
        />

        {/* Templates */}
        <Route
          path="templates"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileTemplates />
            </Suspense>
          }
        />
        <Route
          path="templates/:id"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileTemplateDetail />
            </Suspense>
          }
        />

        {/* Honey Jars */}
        <Route
          path="honey-jars"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileHoneyJars />
            </Suspense>
          }
        />
        <Route
          path="honey-jars/:id"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileHoneyJarDetail />
            </Suspense>
          }
        />

        {/* Settings */}
        <Route
          path="settings"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileSettings />
            </Suspense>
          }
        />
        <Route
          path="settings/profile"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileProfile />
            </Suspense>
          }
        />
        <Route
          path="settings/security"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <MobileSecurity />
            </Suspense>
          }
        />

        {/* Admin routes */}
        <Route
          path="admin"
          element={
            <RequireAdmin>
              <Suspense fallback={<LoadingFallback />}>
                <MobileAdmin />
              </Suspense>
            </RequireAdmin>
          }
        />
        <Route
          path="admin/pending"
          element={
            <RequireAdmin>
              <Suspense fallback={<LoadingFallback />}>
                <MobileAdminPending />
              </Suspense>
            </RequireAdmin>
          }
        />
        <Route
          path="admin/users"
          element={
            <RequireAdmin>
              <Suspense fallback={<LoadingFallback />}>
                <MobileAdminUsers />
              </Suspense>
            </RequireAdmin>
          }
        />

        {/* Catch-all within mobile layout - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/m/" replace />} />
      </Route>
    </Routes>
  );
};

export default MobileRoutesComponent;
