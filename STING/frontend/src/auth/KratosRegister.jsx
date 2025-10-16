import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * KratosRegister - Component for handling Kratos registration flows
 * 
 * This component:
 * 1. Receives a flow ID from the URL
 * 2. Fetches registration flow data from Kratos
 * 3. Renders a dynamic registration form based on Kratos schema
 */
const KratosRegister = () => {
  const [searchParams] = useSearchParams();
  const [flowData, setFlowData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Get Kratos URL from environment
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  
  // Get flow ID from URL
  const flowId = searchParams.get('flow');
  
  // Fetch flow data on mount or when flowId changes
  useEffect(() => {
    const fetchFlowData = async () => {
      if (!flowId) {
        setError('No flow ID provided. Cannot render registration form.');
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        
        // Log the URL we're about to fetch
        console.log(`Fetching registration flow data from: ${kratosUrl}/self-service/registration/flows?id=${flowId}`);
        
        const response = await fetch(
          `${kratosUrl}/self-service/registration/flows?id=${flowId}`,
          {
            credentials: 'include',
          }
        );
        
        // Log the response status
        console.log(`Registration flow fetch response status: ${response.status}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Registration flow data retrieved:', data);
          setFlowData(data);
        } else {
          const errorData = await response.text();
          console.error('Failed to fetch registration flow:', errorData);
          setError(`Failed to load registration form. Status: ${response.status}`);
        }
      } catch (err) {
        console.error('Error fetching registration flow data:', err);
        setError('Failed to connect to authentication service. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchFlowData();
  }, [flowId, kratosUrl]);
  
  // Render the registration form based on flow data
  const renderRegistrationForm = () => {
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
          if (node.group === 'password') {
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
          }
          
          // Traits (user profile data)
          if (node.group === 'default' && node.attributes.name.startsWith('traits.')) {
            // Extract the field name (e.g., "traits.email" -> "Email")
            const fieldName = node.attributes.name.split('.').pop();
            const capitalizedFieldName = fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
            
            return (
              <div key={index} className="mb-4">
                <label className="block text-gray-300 mb-2">{label || capitalizedFieldName}</label>
                <input
                  name={node.attributes.name}
                  type={node.attributes.type}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                  required={node.attributes.required}
                  defaultValue={node.attributes.value || ''}
                />
                {/* Show any messages for this field */}
                {node.messages?.map((msg, i) => (
                  <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {msg.text}
                  </p>
                ))}
              </div>
            );
          }
          
          // Default rendering for other fields
          return (
            <div key={index} className="mb-4">
              <label className="block text-gray-300 mb-2">{label}</label>
              <input
                name={node.attributes.name}
                type={node.attributes.type}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                required={node.attributes.required}
                defaultValue={node.attributes.value || ''}
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
        
        {/* Submit button for password method */}
        <button 
          type="submit" 
          name="method" 
          value="password"
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 mt-4"
        >
          Create Account
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
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg text-white">
        <h2 className="text-2xl font-bold text-center mb-6">Create your account</h2>
        
        {isLoading ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
            <p>Loading registration form...</p>
          </div>
        ) : error ? (
          <div className="p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded mb-6">
            <p className="text-red-300">{error}</p>
            <div className="mt-4">
              <button
                onClick={() => window.location.href = `${kratosUrl}/self-service/registration/browser`}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          renderRegistrationForm()
        )}
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <p>
            Already have an account?{' '}
            <a href="/login" className="text-yellow-400 hover:underline">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default KratosRegister;