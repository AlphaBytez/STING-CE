/**
 * AAL2 Protected Route - Claude's cleaner approach
 * Wraps components that need AAL2 step-up authentication
 */

import React, { useState, useEffect } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import AAL2StepUpModal from './AAL2StepUpModal';

const AAL2ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useUnifiedAuth();
  const location = useLocation();
  const [aalLevel, setAALLevel] = useState(null);
  const [checkingAAL, setCheckingAAL] = useState(true);
  const [showStepUp, setShowStepUp] = useState(false);

  useEffect(() => {
    const checkAAL = async () => {
      if (!isAuthenticated) {
        setCheckingAAL(false);
        return;
      }

      try {
        // FIXED: Use kratosClient instead of relying on document.cookie
        const { kratosClient } = await import('../../services/api');
        const response = await kratosClient.get('/.ory/sessions/whoami');
        
        const session = response.data;
        const currentAAL = session?.authenticator_assurance_level || 'aal1';
        
        console.log('🔐 AAL2ProtectedRoute session:', {
          currentAAL,
          sessionActive: session?.active,
          sessionId: session?.id,
          identity: session?.identity?.traits?.email
        });
        
        setAALLevel(currentAAL);
        
        // FIXED: Only show step-up if actually at AAL1
        if (currentAAL === 'aal1' && session?.active) {
          setShowStepUp(true);
        }
      } catch (error) {
        console.error('🔐 AAL2ProtectedRoute: Failed to check AAL:', error);
        setAALLevel('aal1');
        setShowStepUp(true);
      } finally {
        setCheckingAAL(false);
      }
    };

    checkAAL();
  }, [isAuthenticated, location.pathname]);

  if (isLoading || checkingAAL) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Verifying security level...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // FIXED: Check AAL level correctly
  const needsAAL2 = aalLevel === 'aal1';
  
  console.log('🔐 AAL2ProtectedRoute check:', {
    route: location.pathname,
    currentAAL: aalLevel,
    needsAAL2,
    showStepUp
  });

  // FIXED: Remove the cookie check - rely on session data
  if (needsAAL2 && showStepUp) {
    return <AAL2StepUpModal onComplete={() => window.location.reload()} />;
  }

  console.log('🔐 AAL2 requirement satisfied');
  return children;
};

export default AAL2ProtectedRoute;