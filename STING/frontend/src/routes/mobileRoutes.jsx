import React, { lazy, Suspense, Component } from 'react';
import { Navigate } from 'react-router-dom';
import MobileLayout from '../components/mobile/MobileLayout';
import MobileLoadingSpinner from '../components/mobile/MobileLoadingSpinner';
import MobileTest from '../components/mobile/MobileTest';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';

/**
 * Error boundary for lazy-loaded components
 * Catches errors during rendering of lazy components
 * Attempts recovery by re-rendering children on retry
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, retryKey: 0 };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Mobile route error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, retryKey: this.state.retryKey + 1 });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: 'var(--mobile-space-xl)',
          textAlign: 'center',
          background: 'var(--mobile-surface)',
          border: '1px solid var(--mobile-border)',
          borderRadius: 'var(--mobile-radius-lg)',
          margin: 'var(--mobile-space-md)',
        }}>
          <h3 style={{ color: 'var(--mobile-error)', marginBottom: 'var(--mobile-space-md)' }}>
            Something went wrong
          </h3>
          <p style={{ color: 'var(--mobile-text-secondary)', marginBottom: 'var(--mobile-space-md)' }}>
            {this.state.error?.message || 'Unknown error'}
          </p>
          <button
            onClick={this.handleRetry}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: 'var(--mobile-primary)',
              border: 'none',
              borderRadius: 'var(--mobile-radius-md)',
              color: 'var(--mobile-text-inverse)',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    // Add key to force re-render on retry
    return React.cloneElement(this.props.children, { key: this.state.retryKey });
  }
}

/**
 * Loading fallback for lazy-loaded mobile pages
 */
const withSuspense = (Component) => (props) => (
  <ErrorBoundary>
    <Suspense fallback={
      <div style={{
        minHeight: '200px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <MobileLoadingSpinner />
      </div>
    }>
      <Component {...props} />
    </Suspense>
  </ErrorBoundary>
);

/**
 * Auth guard for mobile routes
 * Does NOT block rendering - renders content while auth checks in background
 * Redirects to login only if auth fails (not while loading)
 */
const RequireAuth = ({ children }) => {
  const { isAuthenticated, isLoading } = useUnifiedAuth();

  // Don't block rendering while checking auth
  // If not authenticated after loading completes, redirect
  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: '/m/' }} />;
  }

  return children;
};

/**
 * Admin guard for mobile routes
 * Redirects to dashboard if not admin
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
 * Mobile routes configuration
 * All routes are under /m/* namespace
 */
export const mobileRoutes = {
  path: '/m',
  children: [
    // TEST ROUTE - bypasses ALL guards for debugging
    { path: 'test', element: <MobileTest /> },
    
    // Main mobile app with auth
    {
      path: '',
      element: (
        <RequireAuth>
          <MobileLayout />
        </RequireAuth>
      ),
      children: [
        // Dashboard (default)
        { index: true, element: withSuspense(MobileDashboard) },

        // Core features
        { path: 'chat', element: withSuspense(MobileChat) },
        { path: 'chat/:conversationId', element: withSuspense(MobileChat) },
        { path: 'basket', element: withSuspense(MobileBasket) },
        { path: 'search', element: withSuspense(MobileSearch) },

        // Content management
        { path: 'reports', element: withSuspense(MobileReports) },
        { path: 'reports/:id', element: withSuspense(MobileReportDetail) },
        { path: 'templates', element: withSuspense(MobileTemplates) },
        { path: 'templates/:id', element: withSuspense(MobileTemplateDetail) },
        { path: 'honey-jars', element: withSuspense(MobileHoneyJars) },
        { path: 'honey-jars/:id', element: withSuspense(MobileHoneyJarDetail) },

        // Settings
        { path: 'settings', element: withSuspense(MobileSettings) },
        { path: 'settings/profile', element: withSuspense(MobileProfile) },
        { path: 'settings/security', element: withSuspense(MobileSecurity) },

        // Admin routes (protected by RequireAdmin)
        {
          path: 'admin',
          element: <RequireAdmin />,
          children: [
            { index: true, element: withSuspense(MobileAdmin) },
            { path: 'pending', element: withSuspense(MobileAdminPending) },
            { path: 'users', element: withSuspense(MobileAdminUsers) },
          ],
        },
      ],
    },

    // Catch-all - redirect to dashboard
    { path: '*', element: <Navigate to="/m/" replace /> },
  ],
};

export default mobileRoutes;
