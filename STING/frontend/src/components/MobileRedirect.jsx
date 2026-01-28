import React, { useEffect, useState, useCallback } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

// Breakpoint for mobile detection
const MOBILE_BREAKPOINT = 768;

// User agent regex for mobile detection
const MOBILE_UA_REGEX = /Android.*Mobile|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i;

/**
 * Check if the current device is a mobile phone
 * Must be BOTH mobile user agent AND small screen (< 768px)
 * Can be overridden via localStorage or URL query parameter
 */
export function isMobileDevice() {
  if (typeof window === 'undefined') return false;

  // Check URL query parameter first (for testing)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mobile') === '1' || urlParams.get('mobile') === 'true') {
    return true;
  }
  if (urlParams.get('desktop') === '1' || urlParams.get('desktop') === 'true') {
    return false;
  }

  // Desktop override via localStorage (user preference)
  const preferDesktop = localStorage.getItem('sting-prefer-desktop');
  if (preferDesktop === '1') return false;

  // Mobile preference via localStorage
  const preferMobile = localStorage.getItem('sting-prefer-mobile');
  if (preferMobile === '1') return true;

  const ua = navigator.userAgent || '';
  const isMobileUA = MOBILE_UA_REGEX.test(ua);
  const isSmallScreen = window.innerWidth < MOBILE_BREAKPOINT;

  // Must be BOTH mobile UA AND small screen
  return isMobileUA && isSmallScreen;
}

/**
 * MobileRedirect - Auto-redirect wrapper for mobile devices
 * Checks on mount and redirects phone users to /m/* routes
 *
 * Usage: Wrap desktop routes with this component to enable mobile redirect
 * <Route path="/dashboard" element={
 *   <MobileRedirect>
 *     <Dashboard />
 *   </MobileRedirect>
 * } />
 *
 * Manual override options:
 * - Add ?mobile=1 to URL to force mobile
 * - Add ?desktop=1 to URL to force desktop
 * - Set localStorage 'sting-prefer-mobile' = '1' for mobile
 * - Set localStorage 'sting-prefer-desktop' = '1' for desktop
 */
const MobileRedirect = ({ children, to = '/m/', enabled = true }) => {
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(false);
  const [hasChecked, setHasChecked] = useState(false);

  const checkDevice = useCallback(() => {
    try {
      const mobile = isMobileDevice();
      setIsMobile(mobile);
    } catch (e) {
      console.warn('Mobile detection error:', e);
      setIsMobile(false);
    }
    setHasChecked(true);
  }, []);

  useEffect(() => {
    // Check immediately on mount
    checkDevice();

    // Also check after a short delay to catch any edge cases
    const timeoutId = setTimeout(checkDevice, 100);

    // Re-check on resize
    let resizeTimeout;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(checkDevice, 100);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimeout);
      clearTimeout(timeoutId);
    };
  }, [checkDevice]);

  // Show loading while checking (prevent flash)
  if (!hasChecked) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'var(--color-bg-layout, #161922)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{ color: 'var(--color-text, #f1f5f9)' }}>Loading...</span>
      </div>
    );
  }

  // Check if already on a mobile route - don't redirect if so!
  const isAlreadyOnMobileRoute = location.pathname.startsWith('/m');

  // CRITICAL: Don't redirect on auth routes - this causes infinite loops!
  // Mobile users need to access these routes before being redirected to /m/
  const authRoutes = [
    '/login',
    '/register',
    '/logout',
    '/verification',
    '/error',
    '/change-password',
    '/credential-setup',
    '/post-registration',
    '/security-upgrade',
    '/session-check',
    '/quick-logout',
    '/enrollment',
    '/first-run',
    '/debug',
  ];
  const isOnAuthRoute = authRoutes.some(route => location.pathname.startsWith(route));

  // Redirect mobile users to mobile routes (only if not already on mobile routes or auth routes)
  if (enabled && isMobile && !isAlreadyOnMobileRoute && !isOnAuthRoute) {
    return <Navigate to={to} replace />;
  }

  // Render children for desktop users, mobile users on /m/*, or users on auth routes
  return children;
};

/**
 * Helper function to toggle mobile preference
 * Call this to switch between mobile and desktop views
 */
export const toggleMobilePreference = () => {
  const isMobile = isMobileDevice();
  if (isMobile) {
    localStorage.setItem('sting-prefer-desktop', '1');
    localStorage.removeItem('sting-prefer-mobile');
  } else {
    localStorage.setItem('sting-prefer-mobile', '1');
    localStorage.removeItem('sting-prefer-desktop');
  }
  window.location.reload();
};

export default MobileRedirect;
