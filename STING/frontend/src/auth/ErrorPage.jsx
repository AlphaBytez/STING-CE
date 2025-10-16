import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useKratos } from './KratosProvider';

/**
 * ErrorPage - Handles error redirects from Kratos
 */
const ErrorPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { kratosUrl } = useKratos();
  
  const [error, setError] = useState('Authentication error occurred');
  const [errorDetails, setErrorDetails] = useState('');
  
  // Get error ID from URL if present
  const errorId = searchParams.get('id');
  
  // Effect for handling error ID
  useEffect(() => {
    if (errorId) {
      // Fetch error details from Kratos
      const fetchErrorDetails = async () => {
        try {
          const response = await fetch(
            `${kratosUrl}/self-service/errors?id=${errorId}`,
            { credentials: 'include' }
          );
          
          if (response.ok) {
            const errorData = await response.json();
            setError(errorData.error?.message || 'Authentication error occurred');
            
            if (errorData.error?.details) {
              setErrorDetails(JSON.stringify(errorData.error.details, null, 2));
            }
          }
        } catch (err) {
          console.error('Error fetching error details:', err);
        }
      };
      
      fetchErrorDetails();
    }
  }, [errorId, kratosUrl]);
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
        <h2 className="text-2xl font-bold text-center mb-6">Authentication Error</h2>
        
        <div className="mb-6 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded">
          <p className="text-red-300">{error}</p>
          {errorDetails && (
            <pre className="mt-4 p-2 bg-gray-900 rounded text-xs overflow-x-auto">
              {errorDetails}
            </pre>
          )}
        </div>
        
        <div className="flex flex-col space-y-3">
          <button
            onClick={() => navigate('/login')}
            className="py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Return to Login
          </button>
          
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

export default ErrorPage;