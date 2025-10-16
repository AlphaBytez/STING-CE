/**
 * Simple AAL2 Step-Up Component
 * 
 * Simplified approach that redirects to EnhancedKratosLogin to avoid 4010002 errors.
 * This ensures we use our proven authentication flow with all fixes applied.
 */

import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const SimpleAAL2StepUp = ({ user, onSuccess, onError }) => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    console.log('🔐 SimpleAAL2StepUp: Redirecting to enhanced login for AAL2...');
    
    // Store current page so we can return after authentication
    sessionStorage.setItem('aal2_return_url', location.pathname);
    
    // Extract any method preference from location state
    const preferredMethod = location.state?.preferredMethod || 'passkey';
    
    // Redirect to our enhanced login with AAL2 parameter
    // This ensures consistent authentication flow and avoids 4010002 errors
    const returnTo = encodeURIComponent('/dashboard');
    window.location.href = `/login?aal=aal2&method=${preferredMethod}&return_to=${returnTo}`;
  }, [location, navigate]);

  // Show loading while redirecting
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto"></div>
        <div className="mt-4 text-yellow-400">
          Redirecting to secure authentication...
        </div>
        <div className="mt-2 text-gray-400 text-sm">
          Additional security verification required
        </div>
      </div>
    </div>
  );
};

export default SimpleAAL2StepUp;