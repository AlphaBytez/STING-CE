import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import MailViewer from './MailViewer';
import KratosDebug from './KratosDebug';
import VerificationDebug from './VerificationDebug';

/**
 * DebugPage - A component for testing and debugging authentication flows
 */
const DebugPage = () => {
  const [kratosStatus, setKratosStatus] = useState(null);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Get Kratos URL
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Check Kratos status
  useEffect(() => {
    const checkKratosStatus = async () => {
      try {
        const response = await axios.get(`${kratosUrl}/health/ready`, {
          withCredentials: true,
          timeout: 5000,
          // Skip SSL verification for development
          httpsAgent: new (require('https').Agent)({
            rejectUnauthorized: false
          })
        });
        
        setKratosStatus({
          status: response.status,
          statusText: response.statusText,
          data: response.data
        });
      } catch (err) {
        setKratosStatus({
          error: true,
          message: err.message,
          status: err.response?.status,
          statusText: err.response?.statusText
        });
      }
    };
    
    checkKratosStatus();
  }, [kratosUrl]);
  
  // Check session status
  useEffect(() => {
    const checkSessionStatus = async () => {
      try {
        const response = await axios.get(`${kratosUrl}/sessions/whoami`, {
          withCredentials: true,
          timeout: 5000,
          // Skip SSL verification for development
          httpsAgent: new (require('https').Agent)({
            rejectUnauthorized: false
          })
        });
        
        setSessionStatus({
          authenticated: true,
          status: response.status,
          data: response.data
        });
      } catch (err) {
        setSessionStatus({
          authenticated: false,
          error: true,
          message: err.message,
          status: err.response?.status,
          statusText: err.response?.statusText
        });
      } finally {
        setLoading(false);
      }
    };
    
    checkSessionStatus();
  }, [kratosUrl]);
  
  // Create a test registration flow
  const createRegistrationFlow = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get(`${kratosUrl}/self-service/registration/api`, {
        withCredentials: true,
        // Skip SSL verification for development
        httpsAgent: new (require('https').Agent)({
          rejectUnauthorized: false
        })
      });
      
      window.open(`/register?flow=${response.data.id}`, '_blank');
    } catch (err) {
      setError(`Failed to create registration flow: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Create a test login flow
  const createLoginFlow = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get(`${kratosUrl}/self-service/login/api`, {
        withCredentials: true,
        // Skip SSL verification for development
        httpsAgent: new (require('https').Agent)({
          rejectUnauthorized: false
        })
      });
      
      window.open(`/login?flow=${response.data.id}`, '_blank');
    } catch (err) {
      setError(`Failed to create login flow: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Logout using our dedicated logout page
  const logout = () => {
    window.location.href = '/logout';
  };
  
  return (
    <div className="min-h-screen bg-gray-900 p-8 text-white">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Authentication Debug Page</h1>
        
        {/* Status Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Kratos Status */}
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold mb-4">Kratos Server Status</h2>
            
            {kratosStatus ? (
              <div>
                {kratosStatus.error ? (
                  <div className="text-red-400 mb-2">
                    Error connecting: {kratosStatus.message}
                  </div>
                ) : (
                  <div className="text-green-400 mb-2">
                    Server is online: {kratosStatus.statusText || 'OK'}
                  </div>
                )}
                
                <div className="bg-gray-900 p-3 rounded text-sm font-mono overflow-x-auto">
                  <pre>{JSON.stringify(kratosStatus, null, 2)}</pre>
                </div>
              </div>
            ) : (
              <div className="text-gray-400">Checking Kratos status...</div>
            )}
          </div>
          
          {/* Session Status */}
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold mb-4">Authentication Status</h2>
            
            {sessionStatus ? (
              <div>
                {sessionStatus.authenticated ? (
                  <div className="text-green-400 mb-2">
                    You are authenticated
                  </div>
                ) : (
                  <div className="text-yellow-400 mb-2">
                    You are not authenticated
                  </div>
                )}
                
                <div className="bg-gray-900 p-3 rounded text-sm font-mono overflow-x-auto">
                  <pre>{JSON.stringify(sessionStatus, null, 2)}</pre>
                </div>
              </div>
            ) : (
              <div className="text-gray-400">Checking authentication status...</div>
            )}
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-xl font-semibold mb-4">Authentication Actions</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={createLoginFlow}
              disabled={loading}
              className={`py-2 px-4 rounded ${loading ? 'bg-gray-600' : 'bg-blue-600 hover:bg-blue-700'}`}
            >
              Test Login Flow
            </button>
            
            <button
              onClick={createRegistrationFlow}
              disabled={loading}
              className={`py-2 px-4 rounded ${loading ? 'bg-gray-600' : 'bg-green-600 hover:bg-green-700'}`}
            >
              Test Registration Flow
            </button>
            
            <button
              onClick={logout}
              disabled={loading || !sessionStatus?.authenticated}
              className={`py-2 px-4 rounded ${
                loading || !sessionStatus?.authenticated 
                  ? 'bg-gray-600' 
                  : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              Logout
            </button>
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded">
              <p className="text-red-300">{error}</p>
            </div>
          )}
        </div>
        
        {/* Quick Links */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-xl font-semibold mb-4">Testing Links</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium mb-2">Authentication Pages</h3>
              <ul className="space-y-2 ml-4">
                <li>
                  <Link to="/login" className="text-blue-400 hover:underline">Simple Passkey Login</Link>
                </li>
                <li>
                  <Link to="/register" className="text-blue-400 hover:underline">Simple Passkey Registration</Link>
                </li>
                <li>
                  <Link to="/login-basic" className="text-blue-400 hover:underline">Basic Kratos Login (Troubleshooting)</Link>
                </li>
                <li>
                  <Link to="/login-enhanced" className="text-blue-400 hover:underline">Enhanced Kratos Login</Link>
                </li>
                <li>
                  <Link to="/register-enhanced" className="text-blue-400 hover:underline">Enhanced Kratos Registration</Link>
                </li>
                <li>
                  <Link to="/login-legacy" className="text-blue-400 hover:underline">Legacy Login</Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">Diagnostic Tools</h3>
              <ul className="space-y-2 ml-4">
                <li>
                  <a 
                    href="/passkey-test.html" 
                    target="_blank"
                    className="text-blue-400 hover:underline"
                    rel="noopener noreferrer"
                  >
                    WebAuthn Browser Test
                  </a>
                </li>
                <li>
                  <Link to="/test-passkey" className="text-blue-400 hover:underline">PasskeyTestPage Component</Link>
                </li>
                <li>
                  <a 
                    href={`${kratosUrl}/.well-known/jsonwebkeys.json`}
                    target="_blank"
                    className="text-blue-400 hover:underline"
                    rel="noopener noreferrer"
                  >
                    Kratos JWKS Endpoint
                  </a>
                </li>
                <li>
                  <a 
                    href={`${kratosUrl}/health/ready`}
                    target="_blank"
                    className="text-blue-400 hover:underline"
                    rel="noopener noreferrer"
                  >
                    Kratos Health Endpoint
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        {/* Kratos API Diagnostics Section */}
        <div className="mb-8">
          <KratosDebug />
        </div>
        
        {/* Email Verification Section */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-xl font-semibold mb-4">Email Verification</h2>
          <MailViewer />
        </div>

        {/* Verification Debug Section */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-xl font-semibold mb-4">Verification Debug Tools</h2>
          <VerificationDebug />
        </div>
        
        {/* Browser Information */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Browser Information</h2>
          
          <div className="space-y-2">
            <p><strong>User Agent:</strong> {navigator.userAgent}</p>
            <p><strong>WebAuthn API:</strong> {window.PublicKeyCredential ? 'Supported ✅' : 'Not Supported ❌'}</p>
            <p><strong>Credentials API:</strong> {navigator.credentials ? 'Supported ✅' : 'Not Supported ❌'}</p>
            <p><strong>Secure Context:</strong> {window.isSecureContext ? 'Yes ✅' : 'No ❌'}</p>
          </div>
        </div>
        
        <div className="mt-8 text-center">
          <Link to="/dashboard" className="text-blue-400 hover:underline">
            Go to Dashboard
          </Link>
          {' | '}
          <Link to="/" className="text-blue-400 hover:underline">
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
};

export default DebugPage;