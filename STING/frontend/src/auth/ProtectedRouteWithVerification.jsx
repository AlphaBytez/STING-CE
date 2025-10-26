import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useKratos } from './KratosProvider';

/**
 * ProtectedRouteWithVerification - Route component that requires authentication AND email verification
 */
const ProtectedRouteWithVerification = ({ 
  children,
  requiredAccountType,
  requiredPermissions = []
}) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, identity, accountType } = useKratos();
  
  // Show loader while checking authentication
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
      </div>
    );
  }
  
  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // Check email verification
  const emailVerified = identity?.verifiable_addresses?.some(
    addr => addr.via === 'email' && addr.verified === true
  );
  
  if (!emailVerified) {
    return <Navigate to="/verify-email" replace />;
  }
  
  // Check account type if required
  if (requiredAccountType && accountType !== requiredAccountType) {
    return <Navigate to="/account-upgrade" state={{ requiredType: requiredAccountType }} replace />;
  }
  
  // Check permissions if required
  if (requiredPermissions.length > 0) {
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

export default ProtectedRouteWithVerification;