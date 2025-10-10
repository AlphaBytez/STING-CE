import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useKratos } from './KratosProvider';
import EnhancedKratosRegistration from '../components/auth/EnhancedKratosRegistration';

/**
 * RegistrationRedirect - Handles redirects from Kratos registration flow
 * 
 * This component:
 * 1. Receives redirects from Kratos with flow ID
 * 2. If there's a flow ID, renders KratosRegister 
 * 3. If not, redirects to Kratos to start a new registration flow
 * 4. Shows verification sent message when appropriate
 */
const RegistrationRedirect = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, isLoading, register, kratosUrl } = useKratos();
  
  const [verificationSent, setVerificationSent] = useState(false);
  
  // Get flow ID from URL if present
  const flowId = searchParams.get('flow');
  
  // Redirect already authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, isLoading, navigate]);
  
  // If no flow ID, redirect to Kratos to start a new registration flow
  useEffect(() => {
    if (!flowId && !isLoading && !isAuthenticated) {
      console.log('No flow ID, redirecting to Kratos registration');
      // Small delay to prevent immediate redirect
      const timer = setTimeout(() => register(), 300);
      return () => clearTimeout(timer);
    }
  }, [flowId, isLoading, isAuthenticated, register]);
  
  // If we have a flow ID, check if verification was sent
  useEffect(() => {
    if (flowId && !isLoading && !isAuthenticated) {
      const checkVerificationStatus = async () => {
        try {
          const response = await fetch(
            `${kratosUrl}/self-service/registration/flows?id=${flowId}`,
            { credentials: 'include' }
          );
          
          if (response.ok) {
            const flowData = await response.json();
            
            // Check if registration completed and verification was sent
            if (flowData.state === 'passed_challenge' || 
                flowData.state === 'success' ||
                flowData.continue_with?.some(item => item.action === 'show_verification_ui')) {
              console.log('Verification sent, showing confirmation');
              setVerificationSent(true);
            }
          }
        } catch (err) {
          console.error('Error checking verification status:', err);
        }
      };
      
      checkVerificationStatus();
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
  
  // Show verification sent message
  if (verificationSent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
          <h2 className="text-2xl font-bold mb-6">Verification Email Sent</h2>
          <div className="mb-6 p-4 bg-green-900 bg-opacity-30 border border-green-700 rounded">
            <p>
              Registration successful! We've sent a verification email to your address.
              Please check your inbox and follow the link to verify your account.
            </p>
          </div>
          <div className="mb-6 text-gray-300">
            <p>
              If you don't see the email, please check your spam folder or try again.
            </p>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }
  
  // If we have a flow ID, render the EnhancedKratosRegistration component
  if (flowId) {
    console.log(`Flow ID found: ${flowId}, rendering EnhancedKratosRegistration component`);
    return <EnhancedKratosRegistration />;
  }
  
  // If we're not loading and don't have a flow ID, show a redirect message
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
        <h2 className="text-2xl font-bold text-center mb-6">Create an Account</h2>
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
        <p className="text-lg">Redirecting to registration service...</p>
        <button
          onClick={register}
          className="mt-4 py-2 px-4 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Click here if not redirected
        </button>
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Already have an account?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-yellow-400 hover:underline"
            >
              Log in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegistrationRedirect;