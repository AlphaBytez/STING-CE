import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useSessionContext } from 'supertokens-auth-react/recipe/session';
import { Alert, AlertDescription } from './ui/alert';

const RoleProtectedRoute = ({ children, requiredRole }) => {
  const location = useLocation();
  const session = useSessionContext();
  
  const hasRequiredRole = session.accessTokenPayload?.roles?.includes(requiredRole);

  if (!hasRequiredRole) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertDescription>
            You don't have permission to access this page.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return children;
};

export default RoleProtectedRoute;

