import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AAL2RedirectHandler = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Check if we have a stored return path
    const returnTo = sessionStorage.getItem('aal2_return_to');
    
    if (returnTo) {
      console.log('🔐 AAL2 redirect handler: Found stored return path:', returnTo);
      sessionStorage.removeItem('aal2_return_to');
      
      // Extract the path from the full URL
      try {
        const url = new URL(returnTo);
        const path = url.pathname + url.search + url.hash;
        console.log('🔐 Redirecting to:', path);
        navigate(path, { replace: true });
      } catch (e) {
        console.error('🔐 Invalid return URL:', e);
        navigate('/dashboard', { replace: true });
      }
    } else {
      // No stored path, go to dashboard
      console.log('🔐 No stored return path, going to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
};

export default AAL2RedirectHandler;