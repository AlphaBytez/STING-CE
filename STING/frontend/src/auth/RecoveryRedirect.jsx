import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useKratos } from './KratosProvider';
import KratosRecovery from './KratosRecovery';

/**
 * RecoveryRedirect - Handles redirects to/from Kratos recovery flow
 * 
 * This component:
 * 1. If there's a flow ID, renders KratosRecovery component
 * 2. If not, redirects to Kratos to start a new recovery flow
 */
const RecoveryRedirect = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, isLoading, kratosUrl } = useKratos();
  
  // Get flow ID from URL if present
  const flowId = searchParams.get('flow');
  
  // Redirect already authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, isLoading, navigate]);
  
  // If no flow ID, redirect to Kratos to start a new recovery flow
  useEffect(() => {
    if (!flowId && !isLoading && !isAuthenticated) {
      console.log('No flow ID, redirecting to Kratos recovery');
      
      // Small delay to prevent immediate redirect
      const timer = setTimeout(() => {
        const returnTo = encodeURIComponent(window.location.origin + '/recovery');
        window.location.href = `${kratosUrl}/self-service/recovery/browser?return_to=${returnTo}`;
      }, 300);
      
      return () => clearTimeout(timer);
    }
  }, [flowId, isLoading, isAuthenticated, kratosUrl]);
  
  // Loading indicator
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p className="text-lg">Checking authentication status...</p>
        </div>
      </div>
    );
  }
  
  // If we have a flow ID, render the KratosRecovery component
  if (flowId) {
    console.log(`Recovery flow ID found: ${flowId}, rendering KratosRecovery component`);
    return <KratosRecovery />;
  }
  
  // If we're not loading and don't have a flow ID, show a redirect message
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
        <h2 className="text-2xl font-bold text-center mb-6">Password Recovery</h2>
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
        <p className="text-lg">Redirecting to recovery service...</p>
        <button
          onClick={() => {
            const returnTo = encodeURIComponent(window.location.origin + '/recovery');
            window.location.href = `${kratosUrl}/self-service/recovery/browser?return_to=${returnTo}`;
          }}
          className="mt-4 py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Click here if not redirected
        </button>
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Remember your password?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-yellow-400 hover:underline"
            >
              Back to Login
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RecoveryRedirect;