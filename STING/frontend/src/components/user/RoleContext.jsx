import React, { createContext, useContext, useState, useEffect } from 'react';

const RoleContext = createContext();

export const ROLES = {
  ADMIN: 'admin',
  MODERATOR: 'moderator',
  USER: 'user',
};

export const PERMISSIONS = {
  CREATE_TEAM: ['admin', 'super_admin'],
  DELETE_TEAM: ['admin', 'super_admin'],
  MANAGE_USERS: ['admin', 'super_admin'],
  MANAGE_LLM: ['admin', 'super_admin'],
  SEND_MESSAGES: ['admin', 'super_admin', 'user'],
  VIEW_ANALYTICS: ['admin', 'super_admin'],
};

export const RoleProvider = ({ children }) => {
  const [userRole, setUserRole] = useState(ROLES.USER);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadUserRole = async () => {
      // Skip auth checks on public routes
      const publicRoutes = ['/login', '/register', '/verify-email', '/error', '/reset-password'];
      const currentPath = window.location.pathname;
      
      if (publicRoutes.some(route => currentPath.startsWith(route))) {
        // On public route, skipping auth check
        setUserRole(null);
        setIsLoading(false);
        return;
      }
      
      try {
        // Loading user role...
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
        
        try {
          // Try to get user info from Kratos session with timeout
          const userResponse = await fetch('/.ory/sessions/whoami', {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            },
            signal: controller.signal,
          });
          
          clearTimeout(timeoutId); // Clear timeout if request completes
          
          if (userResponse.ok) {
            const userData = await userResponse.json();
            // Kratos session data received
            
            let role = ROLES.USER;
            const userEmail = userData.identity?.traits?.email;
            const userRole = userData.identity?.traits?.role;
            
            // Check for admin role based on Kratos traits
            if (userRole === 'super_admin') {
              role = 'super_admin';
              // User is super admin
            } else if (userRole === 'admin' || userEmail === 'admin@sting.local' || localStorage.getItem('temp-admin-override') === 'true') {
              role = 'admin';
              // User is admin
            } else {
              // User is regular user
            }
            
            // Auto-set admin override for admin@sting.local users
            if (userEmail === 'admin@sting.local') {
              localStorage.setItem('temp-admin-override', 'true');
            }
            
            setUserRole(role);
          } else if (userResponse.status === 401) {
            // User not authenticated - this is OK for debug pages
            setUserRole(null); // No role for unauthenticated users
          } else {
            // Failed to get Kratos session data
            setUserRole(ROLES.USER); // Default to user role instead of making another call
          }
        } catch (fetchError) {
          clearTimeout(timeoutId);
          if (fetchError.name === 'AbortError') {
            // Auth request timed out after 5 seconds
          } else {
            // Auth request failed
          }
          setUserRole(ROLES.USER); // Default to user role
        }
      } catch (error) {
        // Error loading user role
        setUserRole(ROLES.USER); // Default to user role
      } finally {
        setIsLoading(false);
        // Role loading complete
      }
    };

    loadUserRole();
  }, []);

  const hasPermission = (permission) => {
    if (!PERMISSIONS[permission]) return false;
    return PERMISSIONS[permission].includes(userRole);
  };

  const value = {
    userRole,
    setUserRole,
    hasPermission,
    isLoading,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <div className="text-gray-600">Loading user permissions...</div>
        </div>
      </div>
    );
  }

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
};

export const useRole = () => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
};

// Protected Route Component
export const ProtectedRoute = ({ children, requiredPermission }) => {
  const { hasPermission } = useRole();

  if (!hasPermission(requiredPermission)) {
    return (
      <div className="p-6 text-center">
        <h2 className="text-xl font-bold text-red-600">Access Denied</h2>
        <p className="mt-2 text-gray-600">
          You don't have permission to access this resource.
        </p>
      </div>
    );
  }

  return children;
};

export default RoleContext;