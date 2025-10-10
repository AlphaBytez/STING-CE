import React, { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from './UnifiedAuthProvider';
import { useAALStatus } from '../hooks/useAALStatus';
import securityGateService from '../services/securityGateService';
import apiClient from '../utils/apiClient';

/**
 * UnifiedProtectedRoute - Route component with dashboard-gate security enforcement
 * 
 * Flow: Authentication → Dashboard Gate → Security Setup → Full Access
 */
const UnifiedProtectedRoute = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, requiresAction, identity } = useUnifiedAuth();
  
  const [securityStatus, setSecurityStatus] = useState(null);
  const [securityLoading, setSecurityLoading] = useState(false);
  const [bypassActive, setBypassActive] = useState(false);
  const [needsAAL2Redirect, setNeedsAAL2Redirect] = useState(() => {
    // Check sessionStorage for persistent AAL2 redirect requirement
    return sessionStorage.getItem('needsAAL2Redirect') === 'true';
  });
  const [aalCheckInProgress, setAALCheckInProgress] = useState(false);
  const [aalCheckCompleted, setAALCheckCompleted] = useState(() => {
    // Check sessionStorage for persistent AAL check completion
    return sessionStorage.getItem('aalCheckCompleted') === 'true';
  });
  const [aalCheckPending, setAALCheckPending] = useState(false);
  
  // 🚨 EMERGENCY DEBUG MODE (moved here to fix linting)
  const debugMode = localStorage.getItem('aal_debug') === 'true';
  
  // Enhanced debug logging only when enabled
  if (debugMode) {
    const renderCount = ++window.renderCount || (window.renderCount = 1);
    console.log(`🔄 UnifiedProtectedRoute RENDER #${renderCount}:`, {
      pathname: location.pathname,
      isAuthenticated,
      isLoading,
      needsAAL2Redirect,
      aalCheckCompleted,
      aalCheckInProgress,
      sessionStorageAAL2: sessionStorage.getItem('needsAAL2Redirect'),
      sessionStorageCompleted: sessionStorage.getItem('aalCheckCompleted'),
      timestamp: new Date().toISOString()
    });
  }
  
  // Keep AAL status for backward compatibility and debugging
  const {
    aalStatus,
    isAALCompliant,
    needsSetup,
    canAccessDashboard,
    isLoading: aalLoading,
    getMissingMethods
  } = useAALStatus();

  // Check security status when user is authenticated and on dashboard routes
  useEffect(() => {
    const checkSecurityGate = async () => {
      // Only check security for dashboard and AAL2 routes
      if (!isAuthenticated || (!location.pathname.startsWith('/dashboard') && location.pathname !== '/aal2')) {
        setSecurityStatus(null);
        return;
      }

      // Skip check if already on settings pages or specific security routes - DO THIS FIRST
      if (location.pathname.includes('/settings') || 
          location.pathname.includes('/security') ||
          location.pathname === '/dashboard/settings/security') {
        console.log('🛡️ Security Gate: ABSOLUTE BYPASS - on settings page, stopping all security checks');
        setSecurityStatus({ meetsRequirements: true, reason: 'On security settings page - bypass active' });
        setSecurityLoading(false);
        setBypassActive(true);
        return;
      }
      
      // If bypass was previously active but we're no longer on settings, reset it
      if (bypassActive) {
        console.log('🛡️ Security Gate: Resetting bypass - left settings page');
        setBypassActive(false);
      }

      // Don't run security checks if bypass is active
      if (bypassActive) {
        console.log('🛡️ Security Gate: Bypass active - skipping security check');
        return;
      }

      setSecurityLoading(true);
      
      try {
        // Get user role from identity first, then aalStatus
        const userRole = identity?.traits?.role || aalStatus?.role || 'user';
        const userEmail = identity?.traits?.email || aalStatus?.email;
        
        console.log('🔍 UnifiedProtectedRoute: User detection:', {
          identityRole: identity?.traits?.role,
          aalStatusRole: aalStatus?.role,
          finalRole: userRole,
          email: userEmail
        });

        const status = await securityGateService.checkSecurityStatus({
          email: userEmail,
          role: userRole,
          email_verified: identity?.verifiable_addresses?.[0]?.verified !== false
        });

        console.log('🛡️ Security Gate Status:', status);
        setSecurityStatus(status);
      } catch (error) {
        console.error('🛡️ Security Gate Error:', error);
        // Graceful degradation - allow access
        setSecurityStatus({ 
          meetsRequirements: true, 
          hasWarnings: true,
          reason: 'Security check failed - allowing access with warnings'
        });
      } finally {
        setSecurityLoading(false);
      }
    };

    checkSecurityGate();
  }, [isAuthenticated, location.pathname, identity?.traits?.email, bypassActive]);

  // Tiered auth doesn't require AAL2 checking - backend handles per-operation auth
  // Keeping minimal session state for compatibility
  
  // Clear legacy AAL state on logout
  useEffect(() => {
    if (!isAuthenticated) {
      sessionStorage.removeItem('needsAAL2Redirect');
      sessionStorage.removeItem('aalCheckCompleted');
      setNeedsAAL2Redirect(false);
      setAALCheckCompleted(false);
    }
  }, [isAuthenticated]);

  // Log legacy AAL status for debugging/transition
  useEffect(() => {
    if (isAuthenticated && aalStatus) {
      console.log('🔒 Legacy AAL Status (for reference):', {
        role: aalStatus.role,
        email: aalStatus.email,
        isCompliant: isAALCompliant(),
        needsSetup: needsSetup(),
        canAccess: canAccessDashboard(),
        missingMethods: getMissingMethods(),
        currentPath: location.pathname
      });
    }
  }, [isAuthenticated, aalStatus, location.pathname, isAALCompliant, needsSetup, canAccessDashboard, getMissingMethods]);

  // Navigate to security upgrade if needed (legacy AAL2 compatibility)
  useEffect(() => {
    if (isAuthenticated && needsAAL2Redirect && location.pathname !== '/security-upgrade') {
      if (debugMode) {
        console.log('🔒 Navigating to security upgrade page');
      }

      // Navigate to security upgrade for method setup
      navigate('/security-upgrade', {
        state: {
          reason: 'Security setup required',
          hasConfiguredMethods: true,
          from: location
        },
        replace: true 
      });
    }
  }, [isAuthenticated, needsAAL2Redirect, location.pathname, navigate, debugMode, location]);
  
  // Show loader while checking authentication or security status
  // CRITICAL: Also show loader if we're an admin who hasn't completed AAL check yet
  const isAdminPendingAALCheck = identity?.traits?.role === 'admin' && 
                                  !aalCheckCompleted && 
                                  !needsAAL2Redirect &&
                                  location.pathname.startsWith('/dashboard');
  
  if (isLoading || aalLoading || securityLoading || aalCheckInProgress || aalCheckPending || isAdminPendingAALCheck) {
    if (debugMode) {
      console.log('🔄 UnifiedProtectedRoute: Showing loading state', {
        isLoading,
        aalLoading,
        securityLoading,
        aalCheckInProgress,
        currentPath: location.pathname
      });
    }
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
        <div className="ml-4 text-yellow-400">
          {(aalCheckInProgress || aalCheckPending) && 'Verifying authentication level...'}
          {securityLoading && 'Checking security requirements...'}
          {aalLoading && 'Checking authentication requirements...'}
          {isLoading && 'Loading...'}
        </div>
      </div>
    );
  }
  
  // 🚨 CRITICAL: Allow enrollment page access FIRST before auth checks to prevent loops
  if (location.pathname === '/enrollment') {
    console.log('✅ UnifiedProtectedRoute: Enrollment page accessed - allowing access regardless of auth state');
    console.log('✅ UnifiedProtectedRoute: AUTH STATE:', { isAuthenticated, isLoading, location: location.pathname });
    return children;
  }
  
  // 🛡️ CRITICAL: Allow security settings access even if auth state is loading/uncertain
  if (location.pathname.includes('/settings') || 
      location.pathname.includes('/security') ||
      location.pathname === '/dashboard/settings/security') {
    console.log('✅ UnifiedProtectedRoute: Security settings page - allowing access during auth state sync');
    return children;
  }
  
  // Not authenticated - redirect to login  
  if (!isAuthenticated) {
    console.log('🚨 UnifiedProtectedRoute: User not authenticated, redirecting to login');
    console.log('🚨 UnifiedProtectedRoute: Auth state:', { isAuthenticated, isLoading, requiresAction });
    console.log('🚨 UnifiedProtectedRoute: Current location:', location.pathname);
    console.log('🚨 UnifiedProtectedRoute: This redirect is likely causing the enrollment loop!');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // 🛡️ NEW SECURITY GATE: Dashboard and AAL2 route protection with progressive security
  if (isAuthenticated && securityStatus && (location.pathname.startsWith('/dashboard') || location.pathname === '/aal2-step-up')) {
    
    // 🚨 CRITICAL: Skip AAL2 checks if security gate is still loading
    if (securityStatus.isLoading) {
      console.log('🔄 Security Gate still loading - skipping AAL2 checks');
      return (
        <div className="flex h-screen w-full items-center justify-center bg-gray-900">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
          <div className="ml-4 text-yellow-400">Security verification in progress...</div>
        </div>
      );
    }
    
    // 🚨 CRITICAL AAL2 ENFORCEMENT: Check if admin users need AAL2 step-up
    const userRole = identity?.traits?.role || aalStatus?.role || 'user';
    const isAdmin = userRole === 'admin';
    
    console.log('🔍 AAL2 ENFORCEMENT DEBUG:', {
      userRole,
      isAdmin,
      identityRole: identity?.traits?.role,
      aalStatusRole: aalStatus?.role,
      aalStatusExists: !!aalStatus,
      aalStatusData: aalStatus,
      securityStatusExists: !!securityStatus,
      currentPath: location.pathname
    });
    
    // For admin users, check current AAL level directly from Kratos session
    // 🔧 FIX: Check for admin regardless of loading state to prevent login loops
    if (isAdmin && (securityStatus || !securityLoading)) {
      const hasPasskey = securityStatus?.currentMethods?.passkey || false;
      const hasTOTP = securityStatus?.currentMethods?.totp || false;
      const hasConfiguredMethods = hasPasskey || hasTOTP;
      
      // 🔧 AGGRESSIVE ENROLLMENT: Check SecurityGateService requirements
      // For admins: require BOTH passkey AND TOTP (not just any configured methods)
      const meetsAggressiveRequirements = securityStatus?.meetsRequirements || false;
      
      console.log('🛡️ AGGRESSIVE SECURITY CHECK:', {
        hasPasskey,
        hasTOTP,
        hasConfiguredMethods,
        meetsAggressiveRequirements,
        securityStatusRequirements: securityStatus?.meetsRequirements,
        recommendedMethods: securityStatus?.recommendedMethods
      });
      
      // CRITICAL FIX: Route based on configured methods, not aggressive requirements
      // Users with ANY configured methods should get AAL2 step-up, not enrollment
      if (!aalCheckCompleted) {
        if (hasConfiguredMethods) {
          console.log('🚨 Admin with configured methods - redirecting to AAL2 step-up');
          console.log('🔐 Configured methods detected:', { hasPasskey, hasTOTP });
          
          // User has methods configured, send to AAL2 step-up
          setNeedsAAL2Redirect(true);
          sessionStorage.setItem('needsAAL2Redirect', 'true');
          setAALCheckCompleted(true);
          sessionStorage.setItem('aalCheckCompleted', 'true');
          
          return;  // Let the AAL2 redirect logic handle it
        } else {
          console.log('🚨 Admin with no configured methods - redirecting to enrollment');
          console.log('🗑️ Clearing any stale AAL state for fresh start');
          
          // Clear ALL stale sessionStorage state that might cause loops
          sessionStorage.removeItem('needsAAL2Redirect');
          sessionStorage.removeItem('aalCheckCompleted');
          
          // Set completed state to prevent re-checking on enrollment page
          setAALCheckCompleted(true);
          setNeedsAAL2Redirect(false);
          
          return <Navigate to="/enrollment" state={{ 
            reason: 'Security setup required for admin access',
            hasConfiguredMethods: false,
            from: location 
          }} replace />;
        }
      }
      
      // AGGRESSIVE: If admin meets aggressive requirements but needsAAL2Redirect is false, check once  
      if (meetsAggressiveRequirements && !needsAAL2Redirect && !aalCheckCompleted && !aalCheckPending) {
        console.log('🚨 Admin meeting aggressive requirements - checking AAL level once...');
        setAALCheckPending(true);
        setAALCheckInProgress(true);
        
        // Single AAL check without debouncing complexity
        // Tiered auth: Check if user needs security setup (not AAL2)
        // Backend handles per-operation authentication
        fetch('/api/auth/me', { credentials: 'include' })
          .then(response => response.ok ? response.json() : null)
          .then(userData => {
            console.log('🔍 Checking security setup status');

            // Check if admin needs to set up security methods
            const authMethods = userData?.user?.auth_methods || {};
            const hasPasskey = !!authMethods.webauthn;
            const hasTOTP = !!authMethods.totp;

            // Admins need both TOTP and Passkey
            if (userRole === 'admin' && (!hasPasskey || !hasTOTP)) {
              console.log('🔒 Admin needs security setup');
              setNeedsAAL2Redirect(true);
              sessionStorage.setItem('needsAAL2Redirect', 'true');
              window.location.href = '/security-upgrade';
              return;
            }

            // Regular users just need passkey
            if (userRole !== 'admin' && !hasPasskey) {
              console.log('🔒 User needs passkey setup');
              setNeedsAAL2Redirect(true);
              sessionStorage.setItem('needsAAL2Redirect', 'true');
              window.location.href = '/security-upgrade';
              return;
            }

            console.log('✅ Security requirements met');
            setAALCheckCompleted(true);
            sessionStorage.setItem('aalCheckCompleted', 'true');
          })
          .catch(error => {
            console.log('⚠️ Security check failed, allowing access:', error);
            setAALCheckCompleted(true);
            sessionStorage.setItem('aalCheckCompleted', 'true');
          })
          .finally(() => {
            setAALCheckInProgress(false);
            setAALCheckPending(false);
          });
      }
    }
    
    // If security requirements not met, redirect to security setup
    if (!securityStatus.meetsRequirements) {
      console.log('🛡️ Security Gate: Requirements not met, redirecting to security setup:', {
        reason: securityStatus.reason,
        message: securityStatus.message,
        requiredMethods: securityStatus.requiredMethods,
        currentMethods: securityStatus.currentMethods,
        redirectTo: securityStatus.redirectTo
      });

      // Prepare state for security settings page
      const securitySetupState = {
        from: location,
        securitySetup: true,
        securityStatus: securityStatus,
        isRequired: !securityStatus.allowDismiss
      };

      return <Navigate 
        to={securityStatus.redirectTo || '/enrollment'} 
        state={securitySetupState} 
        replace 
      />;
    }

    // Show recommendations if user meets requirements but has suggestions
    if (securityStatus.hasRecommendations) {
      console.log('🛡️ Security Gate: User has recommendations:', {
        message: securityStatus.message,
        recommendedMethods: securityStatus.recommendedMethods
      });
      // Continue to dashboard but we could show a dismissible banner later
    }

    // Show warnings if security check had issues
    if (securityStatus.hasWarnings) {
      console.log('🛡️ Security Gate: Warnings detected:', {
        reason: securityStatus.reason,
        message: securityStatus.message
      });
      // Continue to dashboard but we could show a warning later
    }
  }
  
  // 🎯 AUTHENTICATED - User passed all security gates, render protected content
  console.log('🛡️ UnifiedProtectedRoute: User authenticated and passed security gates, rendering protected content');
  
  // Log final status for debugging
  if (securityStatus) {
    console.log('🛡️ Final Security Status:', {
      meetsRequirements: securityStatus.meetsRequirements,
      hasRecommendations: securityStatus.hasRecommendations,
      hasWarnings: securityStatus.hasWarnings,
      currentPath: location.pathname
    });
  }
  
  return children;
};

export default UnifiedProtectedRoute;