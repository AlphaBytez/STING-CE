import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useKratos } from './KratosProvider';

/**
 * VerificationRedirect - Handles verification flow from Kratos
 */
const VerificationRedirect = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { kratosUrl } = useKratos();
  
  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState('');
  
  // Get flow ID from URL if present
  const flowId = searchParams.get('flow');
  
  // Effect for handling flow ID
  useEffect(() => {
    if (flowId) {
      // Fetch verification flow details
      const fetchFlow = async () => {
        try {
          const response = await fetch(
            `${kratosUrl}/self-service/verification/flows?id=${flowId}`,
            { credentials: 'include' }
          );
          
          if (response.ok) {
            const flowData = await response.json();
            
            // Check for success message
            if (flowData.state === 'passed_challenge') {
              setStatus('success');
              setMessage('Your email has been successfully verified! You can now log in.');
            } else if (flowData.ui?.messages) {
              // Check if there are messages
              const successMessage = flowData.ui.messages
                .filter(m => m.type === 'info')
                .map(m => m.text)
                .join(' ');
                
              const errorMessage = flowData.ui.messages
                .filter(m => m.type === 'error')
                .map(m => m.text)
                .join(' ');
              
              if (successMessage) {
                setStatus('success');
                setMessage(successMessage);
              } else if (errorMessage) {
                setStatus('error');
                setMessage(errorMessage);
              } else {
                setStatus('pending');
                setMessage('Please verify your email by clicking the link we sent you.');
              }
            } else {
              // No clear status, assume pending
              setStatus('pending');
              setMessage('Please verify your email by clicking the link we sent you.');
            }
          } else {
            // Flow not found or expired
            setStatus('error');
            setMessage('Verification session expired. Please try again.');
          }
        } catch (err) {
          console.error('Error fetching verification flow:', err);
          setStatus('error');
          setMessage('Failed to connect to verification service.');
        }
      };
      
      fetchFlow();
    } else {
      // No flow ID, show general verification message
      setStatus('pending');
      setMessage('Please verify your email by clicking the link we sent you.');
    }
  }, [flowId, kratosUrl]);
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white text-center">
        <h2 className="text-2xl font-bold mb-6">Email Verification</h2>
        
        {status === 'checking' && (
          <div className="mb-6">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
            <p>Checking verification status...</p>
          </div>
        )}
        
        {status === 'success' && (
          <div className="mb-6 p-4 bg-green-900 bg-opacity-30 border border-green-700 rounded">
            <p className="text-green-300">{message}</p>
          </div>
        )}
        
        {status === 'error' && (
          <div className="mb-6 p-4 bg-red-900 bg-opacity-30 border border-red-800 rounded">
            <p className="text-red-300">{message}</p>
          </div>
        )}
        
        {status === 'pending' && (
          <div className="mb-6 p-4 bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded">
            <p className="text-yellow-300">{message}</p>
          </div>
        )}
        
        <div className="flex flex-col space-y-3">
          {status === 'success' && (
            <button
              onClick={() => navigate('/login')}
              className="py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go to Login
            </button>
          )}
          
          {status === 'error' && (
            <button
              onClick={() => navigate('/register')}
              className="py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Try Again
            </button>
          )}
          
          <button
            onClick={() => navigate('/')}
            className="py-2 px-4 bg-transparent border border-gray-500 text-gray-300 rounded hover:bg-gray-700"
          >
            Go to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerificationRedirect;