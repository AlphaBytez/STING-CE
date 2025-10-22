import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useKratos } from './KratosProvider';
import { useAALStatus } from '../hooks/useAALStatus';

/**
 * ProtectedRoute - Route component that requires authentication and AAL compliance
 * Can also check for specific account types or permissions
 */
const ProtectedRoute = ({ 
  children,
  requiredAccountType,
  requiredPermissions = [],
  requiredAAL = null // Optional: specify minimum AAL level
}) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, identity, accountType } = useKratos();
  
  // AAL status management
  const {
    aalStatus,
    isAALCompliant,
    needsSetup,
    getCurrentAAL,
    getRequiredAAL,
    canAccessDashboard,
    isLoading: aalLoading
  } = useAALStatus();
  
  // Show loader while checking authentication or AAL status
  if (isLoading || aalLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
      </div>
    );
  }
  
  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    // Store current path for redirect after login
    sessionStorage.setItem('redirectAfterLogin', location.pathname + location.search);
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // Check AAL compliance if we have AAL status
  if (aalStatus) {
    // Check if user meets required AAL level
    if (requiredAAL && getCurrentAAL() < requiredAAL) {
      console.log(`🔐 Route requires AAL ${requiredAAL}, user has ${getCurrentAAL()}`);
      const stepUpUrl = `/.ory/self-service/login/browser?aal=${requiredAAL}&return_to=${encodeURIComponent(location.pathname + location.search)}`;
      window.location.href = stepUpUrl;
      return null;
    }
    
    // Check general AAL compliance for the user's role
    if (!isAALCompliant() || !canAccessDashboard()) {
      console.log('🔐 User does not meet AAL requirements for their role');
      
      // For security-related pages, allow access to set up authentication
      if (location.pathname.includes('/settings/security')) {
        return children;
      }
      
      // Otherwise redirect to security setup
      return <Navigate to="/dashboard/settings/security" state={{ 
        from: location,
        reason: 'Additional authentication required'
      }} replace />;
    }
  }
  
  // Check account type if required
  if (requiredAccountType && accountType !== requiredAccountType) {
    // You could redirect to an upgrade page or show an access denied message
    return <Navigate to="/account-upgrade" state={{ requiredType: requiredAccountType }} replace />;
  }
  
  // Check permissions if required (implement your permission logic here)
  if (requiredPermissions.length > 0) {
    // This is just a placeholder - implement your permission checking logic
    const hasPermissions = requiredPermissions.every(permission => 
      identity?.metadata_public?.permissions?.includes(permission)
    );
    
    if (!hasPermissions) {
      return <Navigate to="/access-denied" state={{ requiredPermissions }} replace />;
    }
  }
  
  // All checks passed, render the protected content
  return children;
};

export default ProtectedRoute;