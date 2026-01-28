import { useState, useEffect } from 'react';

// Breakpoint for mobile detection (phones only, not tablets)
const MOBILE_BREAKPOINT = 768;

// User agent regex for mobile detection
// Note: "Android" without "Mobile" = tablet, iPad is not matched (tablet)
const MOBILE_UA_REGEX = /Android.*Mobile|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i;

/**
 * Check if the current device is a mobile phone
 * Must be BOTH mobile user agent AND small screen (< 768px)
 */
export function isMobileDevice() {
  if (typeof window === 'undefined') return false;

  // Desktop override via localStorage
  if (localStorage.getItem('sting-prefer-desktop') === '1') return false;

  const ua = navigator.userAgent;
  const isMobileUA = MOBILE_UA_REGEX.test(ua);
  const isSmallScreen = window.innerWidth < MOBILE_BREAKPOINT;

  // Must be BOTH mobile UA AND small screen
  return isMobileUA && isSmallScreen;
}

/**
 * Hook to detect viewport information
 * Provides device type, dimensions, and orientation
 */
export function useViewport() {
  const [viewport, setViewport] = useState(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
    isLandscape: typeof window !== 'undefined' ? window.innerWidth > window.innerHeight : true,
  }));

  useEffect(() => {
    const checkViewport = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      const isMobileUA = MOBILE_UA_REGEX.test(navigator.userAgent);
      const isMobileWidth = width < MOBILE_BREAKPOINT;

      setViewport({
        // Mobile: phone with mobile UA AND small screen
        isMobile: isMobileUA && isMobileWidth,
        // Tablet: screen >= 768px but < 1024px OR tablet UA
        isTablet: width >= 768 && width < 1024,
        // Desktop: screen >= 1024px OR not mobile UA
        isDesktop: width >= 1024 || !isMobileUA,
        width,
        height,
        isLandscape: width > height,
      });
    };

    // Initial check
    checkViewport();

    // Listen for resize
    window.addEventListener('resize', checkViewport);

    // Also listen for orientation change on mobile
    window.addEventListener('orientationchange', () => {
      // Small delay to let layout settle after orientation change
      setTimeout(checkViewport, 100);
    });

    return () => {
      window.removeEventListener('resize', checkViewport);
      window.removeEventListener('orientationchange', checkViewport);
    };
  }, []);

  return viewport;
}

export default useViewport;
