import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * KratosRecovery - Component for password recovery flow
 * 
 * This component:
 * 1. Handles the password recovery flow from Kratos
 * 2. Renders a dynamic form based on flow data from Kratos
 * 3. Shows appropriate status messages based on flow state
 */
const KratosRecovery = () => {
  const [searchParams] = useSearchParams();
  const [flowData, setFlowData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [recoveryStatus, setRecoveryStatus] = useState('idle'); // idle, emailSent, completed
  
  // Get Kratos URL from environment
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Get flow ID from URL
  const flowId = searchParams.get('flow');
  
  // Fetch flow data on mount or when flowId changes
  useEffect(() => {
    const fetchFlowData = async () => {
      if (!flowId) {
        setError('No flow ID provided. Cannot render recovery form.');
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        
        // Log the URL we're about to fetch
        console.log(`Fetching recovery flow data from: ${kratosUrl}/self-service/recovery/flows?id=${flowId}`);
        
        const response = await fetch(
          `${kratosUrl}/self-service/recovery/flows?id=${flowId}`,
          {
            credentials: 'include',
          }
        );
        
        // Log the response status
        console.log(`Recovery flow fetch response status: ${response.status}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Recovery flow data retrieved:', data);
          setFlowData(data);
          
          // Check flow state to determine recovery status
          if (data.state === 'sent_email' || 
              data.state === 'passed_challenge' ||
              data.state === 'choose_method' && data.ui.messages?.some(m => m.id === 1060001)) {
            // The ID 1060001 corresponds to "An email containing a recovery link has been sent to the email address"
            setRecoveryStatus('emailSent');
          } else if (data.state === 'passed_challenge') {
            setRecoveryStatus('completed');
          }
        } else {
          const errorData = await response.text();
          console.error('Failed to fetch recovery flow:', errorData);
          setError(`Failed to load recovery form. Status: ${response.status}`);
        }
      } catch (err) {
        console.error('Error fetching recovery flow data:', err);
        setError('Failed to connect to authentication service. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchFlowData();
  }, [flowId, kratosUrl]);
  
  // Render the recovery form based on flow data
  const renderRecoveryForm = () => {
    if (!flowData || !flowData.ui) {
      return null;
    }
    
    // Extract form action and method
    const { action, method } = flowData.ui;
    
    return (
      <form action={action} method={method.toLowerCase()}>
        {/* Hidden CSRF field */}
        {flowData.ui.nodes.map((node, index) => {
          if (node.attributes.name === 'csrf_token') {
            return (
              <input
                key={index}
                type="hidden"
                name={node.attributes.name}
                value={node.attributes.value}
              />
            );
          }
          
          // Skip non-input nodes and submit buttons (we'll add our own)
          if (node.type !== 'input' || node.attributes.type === 'submit') {
            return null;
          }
          
          // Extract label if available
          const label = node.meta?.label?.text || node.attributes.name;
          
          // Render appropriate input based on type and group
          return (
            <div key={index} className="mb-4">
              <label className="block text-gray-300 mb-2">{label}</label>
              <input
                name={node.attributes.name}
                type={node.attributes.type}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                required={node.attributes.required}
                defaultValue={node.attributes.value || ''}
                autoComplete={node.attributes.autocomplete || ''}
              />
              {/* Show any messages for this field */}
              {node.messages?.map((msg, i) => (
                <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {msg.text}
                </p>
              ))}
            </div>
          );
        })}
        
        {/* Submit button */}
        <button 
          type="submit" 
          name="method" 
          value="link"
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 mt-4"
        >
          Send Recovery Link
        </button>
        
        {/* Show form-level messages */}
        {flowData.ui.messages?.map((msg, index) => (
          <div 
            key={index} 
            className={`mt-4 p-3 rounded ${
              msg.type === 'error' ? 'bg-red-900 bg-opacity-30 border border-red-800 text-red-300' : 'bg-green-900 bg-opacity-30 border border-green-800 text-green-300'
            }`}
          >
            {msg.text}
          </div>
        ))}
      </form>
    );
  };
  
  // Render email sent confirmation
  const renderEmailSent = () => {
    return (
      <div className="text-center">
        <div className="mb-6 p-4 bg-green-900 bg-opacity-30 border border-green-700 rounded">
          <p className="text-green-300 mb-2">Recovery email has been sent!</p>
          <p className="text-gray-300">
            Please check your inbox and follow the instructions to reset your password.
          </p>
        </div>
        <div className="mb-6 text-gray-400 text-sm">
          <p>
            If you don't see the email in your inbox, check your spam folder or try again.
          </p>
        </div>
        <button
          onClick={() => window.location.href = `${kratosUrl}/self-service/recovery/browser`}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Send Another Recovery Email
        </button>
      </div>
    );
  };
  
  // Render recovery completed message
  const renderCompleted = () => {
    return (
      <div className="text-center">
        <div className="mb-6 p-4 bg-green-900 bg-opacity-30 border border-green-700 rounded">
          <p className="text-green-300 mb-2">Recovery completed successfully!</p>
          <p className="text-gray-300">
            Your password has been reset. You can now log in with your new password.
          </p>
        </div>
        <button
          onClick={() => window.location.href = '/login'}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Go to Login
        </button>
      </div>
    );
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
        <h2 className="text-2xl font-bold text-center mb-6">Password Recovery</h2>
        
        {isLoading ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
            <p>Loading recovery form...</p>
          </div>
        ) : error ? (
          <div className="p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded mb-6">
            <p className="text-red-300">{error}</p>
            <div className="mt-4">
              <button
                onClick={() => window.location.href = `${kratosUrl}/self-service/recovery/browser`}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : recoveryStatus === 'emailSent' ? (
          renderEmailSent()
        ) : recoveryStatus === 'completed' ? (
          renderCompleted()
        ) : (
          renderRecoveryForm()
        )}
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Remember your password?{' '}
            <a href="/login" className="text-yellow-400 hover:underline">
              Back to Login
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default KratosRecovery;