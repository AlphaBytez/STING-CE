/**
 * Dedicated AAL2 Step-Up Authentication Page
 * 
 * This page handles AAL2 step-up authentication without the chicken-and-egg problem
 * of security settings requiring AAL2 to access AAL2 setup.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../auth/KratosProviderRefactored';
import SimpleAAL2StepUp from '../components/auth/SimpleAAL2StepUp';

const AAL2Page = () => {
  const { identity } = useKratos();
  const navigate = useNavigate();

  // Debug logging to check if component renders
  console.log('🔐 AAL2Page rendering with identity:', identity);

  const handleAAL2Success = () => {
    console.log('🔐 AAL2 authentication successful, redirecting to dashboard');
    // Redirect to dashboard after successful AAL2
    navigate('/dashboard', { replace: true });
  };

  const handleAAL2Error = (error) => {
    console.error('🔐 AAL2 authentication failed:', error);
    // Could add error handling here, like redirecting to login
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 w-full max-w-md">
        <SimpleAAL2StepUp 
          user={{
            email: identity?.traits?.email,
            role: identity?.traits?.role || 'user'
          }}
          onSuccess={handleAAL2Success}
          onError={handleAAL2Error}
        />
        
        {/* Additional Info */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-400">
            Having trouble? Contact support for assistance.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AAL2Page;