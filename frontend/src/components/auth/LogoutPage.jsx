import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../utils/apiClient';

/**
 * LogoutPage - Handles proper Kratos logout flow
 * This component processes the logout flow and redirects users
 */
const LogoutPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('Logging you out...');
  
  useEffect(() => {
    // Process the logout
    const processLogout = async () => {
      try {
        console.log("Starting logout process...");
        
        // Simply call our backend logout endpoint which handles everything
        const backendResponse = await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });
        
        if (backendResponse.ok) {
          console.log("Backend logout successful");
          setMessage('You have been logged out!');
        } else {
          console.warn("Backend logout returned non-OK status:", backendResponse.status);
          setMessage('Logging out...');
        }
        
        // Clear local storage as a final cleanup
        localStorage.clear();
        sessionStorage.clear();
        
        // Clear any cached authentication state
        localStorage.setItem('kratos_auth_cleared', Date.now().toString());
        
        // Aggressively clear all cookies
        document.cookie.split(";").forEach(function(c) { 
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=" + window.location.hostname);
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=." + window.location.hostname);
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=localhost");
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=.localhost");
        });
        
        // Try to clear browser stored credentials
        if (navigator.credentials && navigator.credentials.preventSilentAccess) {
          try {
            await navigator.credentials.preventSilentAccess();
            console.log("Prevented silent credential access");
          } catch (err) {
            console.error("Error preventing silent access:", err);
          }
        }
        
        // Force clear cookies via JavaScript as backup
        document.cookie.split(";").forEach(function(c) { 
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=" + window.location.hostname);
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        
      } catch (err) {
        console.error('Logout error:', err);
        setError('An error occurred during logout.');
        
        // Even if backend logout fails, clear local storage
        localStorage.clear();
        sessionStorage.clear();
        
        // Try to clear browser stored credentials even on error
        if (navigator.credentials && navigator.credentials.preventSilentAccess) {
          try {
            await navigator.credentials.preventSilentAccess();
          } catch (err) {
            console.error("Error preventing silent access:", err);
          }
        }
      } finally {
        setLoading(false);
        
        // After a short delay, redirect to login
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    };
    
    processLogout();
  }, [navigate]);
  
  return (
    <div className="min-h-screen bg-[#161922] flex items-center justify-center p-4">
      <div className="bg-[#1a1f2e] p-8 rounded-lg shadow-lg max-w-md w-full text-white text-center">
        <div className="mb-6">
          {loading ? (
            <div className="w-12 h-12 border-t-2 border-b-2 border-yellow-400 rounded-full animate-spin mx-auto"></div>
          ) : error ? (
            <svg className="w-12 h-12 text-red-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          ) : (
            <svg className="w-12 h-12 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
            </svg>
          )}
        </div>
        
        <h1 className="text-2xl font-bold mb-2">
          {error ? 'Logout Failed' : 'Logging Out'}
        </h1>
        
        <p className="text-gray-300 mb-6">
          {error || message}
        </p>
        
        <div className="flex flex-col space-y-4">
          {error && (
            <button 
              onClick={() => window.location.reload()}
              className="w-full py-2 bg-yellow-600 hover:bg-yellow-700 rounded"
            >
              Try Again
            </button>
          )}
          
          <button 
            onClick={() => navigate('/login')}
            className={`w-full py-2 ${
              error 
                ? 'bg-gray-700 hover:bg-gray-600' 
                : 'bg-blue-600 hover:bg-blue-700'
            } rounded`}
          >
            Return to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default LogoutPage;