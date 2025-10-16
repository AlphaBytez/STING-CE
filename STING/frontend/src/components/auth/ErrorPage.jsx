import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const ErrorPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [errorId, setErrorId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('An error occurred');

  useEffect(() => {
    // Extract error ID from URL query parameters
    const params = new URLSearchParams(location.search);
    const id = params.get('id');
    if (id) {
      setErrorId(id);
      
      // You could fetch error details from Kratos here
      // For now, just show generic error message with ID
      setErrorMessage(`Authentication error (ID: ${id.substring(0, 8)}...)`);
    }
  }, [location]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#161922]">
      <div className="w-full max-w-md bg-[#1a1f2e] p-8 rounded-lg shadow-lg text-white">
        <div className="flex justify-center mb-6">
          <div className="bg-red-600 rounded-full p-3">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        </div>
        
        <h2 className="text-2xl font-bold text-center mb-4">Authentication Error</h2>
        
        <div className="text-center mb-6">
          <p className="text-gray-300 mb-4">{errorMessage}</p>
          <p className="text-gray-400 text-sm">
            There was a problem processing your authentication request. 
            This could be due to an expired session, invalid credentials, or a system error.
          </p>
        </div>
        
        <div className="flex flex-col space-y-3">
          <button 
            onClick={() => navigate('/login')}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Return to Login
          </button>
          
          <button 
            onClick={() => navigate('/')}
            className="w-full py-2 px-4 bg-transparent border border-white text-white rounded hover:bg-gray-700"
          >
            Go to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorPage;