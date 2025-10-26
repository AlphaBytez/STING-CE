import React from 'react';
import { useNavigate } from 'react-router-dom';

const QuickLogout = () => {
  const navigate = useNavigate();
  
  const handleQuickLogout = () => {
    // Clear all cookies
    document.cookie.split(";").forEach(function(c) { 
      document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/;domain=localhost"); 
      document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
    });
    
    // Clear localStorage
    localStorage.clear();
    sessionStorage.clear();
    
    // Navigate to login
    navigate('/login');
    
    // Force reload to clear any cached state
    window.location.reload();
  };
  
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg max-w-md w-full text-white text-center">
        <h1 className="text-2xl font-bold mb-4">Quick Logout</h1>
        <p className="text-gray-300 mb-6">
          Click the button below to clear your session and return to login.
        </p>
        <button 
          onClick={handleQuickLogout}
          className="w-full py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition-colors"
        >
          Clear Session & Logout
        </button>
      </div>
    </div>
  );
};

export default QuickLogout;