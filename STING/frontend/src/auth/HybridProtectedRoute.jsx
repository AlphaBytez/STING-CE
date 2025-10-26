import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useUnifiedAuth } from './UnifiedAuthProvider';
import enterprisePolicyService from '../services/enterprisePolicyService';

/**
 * HybridProtectedRoute - Simple AAL2 enforcement with enterprise-ready hooks
 * 
 * Core Flow:
 * 1. Settings page bypass (prevent infinite loops)
 * 2. Basic authentication check
 * 3. Admin AAL2 enforcement  
 * 4. Enterprise policy hooks (future SAML/SSO)
 */
const HybridProtectedRoute = ({ children }) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, identity } = useUnifiedAuth();
  const [aalLevel, setAALLevel] = useState(null);
  const [checkingAAL, setCheckingAAL] = useState(false);
  const [policyStatus, setPolicyStatus] = useState(null);

  // 🚨 CRITICAL: Settings page bypass to prevent infinite redirect loops
  const isOnSettingsPage = () => {
    return location.pathname.includes('/settings') || 
           location.pathname.includes('/security') ||
           location.pathname === '/dashboard/settings/security' ||
           location.pathname === '/enrollment';
  };

  // 🏢 Enterprise policy enforcement using policy service
  const checkEnterprisePolicies = async (user) => {
    try {
      // Use enterprise policy service for extensible policy management
      const policy = await enterprisePolicyService.getPolicyForUser(user);
      
      return {
        requiresAAL2: policy.requiresAAL2,
        allowedMethods: policy.allowedMethods,
        requiredMethods: policy.requiredMethods,
        policySource: policy.source,
        organization: policy.user?.organization,
        sessionTimeout: policy.sessionTimeout
      };
    } catch (error) {
      console.warn('Enterprise policy check failed, using fallback:', error);
      
      // Fallback to basic admin/user logic
      const isAdmin = user?.traits?.role === 'admin';
      return {
        requiresAAL2: isAdmin,
        allowedMethods: isAdmin ? ['passkey', 'totp'] : ['email', 'passkey'],
        policySource: 'fallback'
      };
    }
  };

  // Check AAL level and enterprise policies for authenticated users
  useEffect(() => {
    if (!isAuthenticated || !identity) return;

    const checkSecurityRequirements = async () => {
      setCheckingAAL(true);
      
      try {
        // 1. Check enterprise policies first
        const policy = await checkEnterprisePolicies(identity);
        setPolicyStatus(policy);
        
        // 2. If no AAL2 required by policy, skip AAL check
        if (!policy.requiresAAL2) {
          setAALLevel('not_required');
          return;
        }

        // 3. Check current AAL level from Kratos
        const response = await fetch('/.ory/sessions/whoami', { credentials: 'include' });
        if (response.ok) {
          const session = await response.json();
          const level = session.authenticator_assurance_level || 'aal1';
          console.log('🔐 AAL level:', level, 'Required:', policy.requiresAAL2 ? 'AAL2' : 'AAL1');
          setAALLevel(level);
        } else {
          setAALLevel('unknown');
        }
      } catch (err) {
        console.error('Failed to check security requirements:', err);
        setAALLevel('error');
        setPolicyStatus({ requiresAAL2: false, allowedMethods: ['email'] });
      } finally {
        setCheckingAAL(false);
      }
    };

    checkSecurityRequirements();
  }, [isAuthenticated, identity]);

  // Show loading while checking auth or security requirements
  if (isLoading || checkingAAL) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
        <div className="ml-4 text-yellow-400">
          {checkingAAL ? 'Checking security requirements...' : 'Loading...'}
        </div>
      </div>
    );
  }

  // 🚨 CRITICAL: Always allow access to settings pages to prevent loops
  if (isOnSettingsPage()) {
    console.log('🛡️ Settings page bypass - allowing access to:', location.pathname);
    return children;
  }

  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 🏢 Enterprise policy enforcement
  if (policyStatus?.requiresAAL2 && aalLevel === 'aal1') {
    // Only redirect from dashboard paths (not from AAL2 page itself)
    if (location.pathname.startsWith('/dashboard')) {
      console.log('🚨 Security policy requires AAL2, redirecting...', {
        currentAAL: aalLevel,
        policySource: policyStatus.policySource,
        allowedMethods: policyStatus.allowedMethods
      });
      return <Navigate to="/aal2" state={{ 
        from: location,
        policy: policyStatus,
        reason: 'Enterprise security policy requires additional authentication'
      }} replace />;
    }
  }

  // All checks passed - render protected content
  console.log('✅ Security requirements met:', {
    aalLevel,
    requiresAAL2: policyStatus?.requiresAAL2,
    path: location.pathname
  });
  
  return children;
};

export default HybridProtectedRoute;