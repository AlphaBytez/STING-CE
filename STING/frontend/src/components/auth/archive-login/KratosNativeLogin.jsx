import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { getKratosUrl } from '../../utils/kratosConfig';

/**
 * KratosNativeLogin - Renders Kratos login flow with minimal interference
 * This component lets Kratos handle WebAuthn natively
 */
const KratosNativeLogin = () => {
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  
  const kratosUrl = getKratosUrl(true);
  const flowId = searchParams.get('flow');

  useEffect(() => {
    // Load Kratos WebAuthn script
    const script = document.createElement('script');
    script.src = `${kratosUrl}/.well-known/ory/webauthn.js`;
    script.async = true;
    script.onload = () => console.log('🔐 Kratos WebAuthn script loaded');
    document.head.appendChild(script);
    
    return () => {
      if (document.head.contains(script)) {
        document.head.removeChild(script);
      }
    };
  }, [kratosUrl]);

  useEffect(() => {
    initializeFlow();
  }, [flowId]);

  const initializeFlow = async () => {
    try {
      setLoading(true);
      let response;
      
      if (flowId) {
        // Fetch existing flow
        response = await axios.get(`${kratosUrl}/self-service/login/flows?id=${flowId}`, {
          withCredentials: true,
          headers: { Accept: 'application/json' }
        });
      } else {
        // Create new flow
        response = await axios.get(`${kratosUrl}/self-service/login/browser`, {
          withCredentials: true,
          headers: { Accept: 'application/json' }
        });
        
        if (response.request.responseURL) {
          const url = new URL(response.request.responseURL);
          const newFlowId = url.searchParams.get('flow');
          if (newFlowId && newFlowId !== flowId) {
            window.history.replaceState({}, '', `?flow=${newFlowId}`);
          }
        }
      }
      
      setFlowData(response.data);
    } catch (err) {
      console.error('Error initializing flow:', err);
      setError('Failed to initialize login');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center">Loading...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  if (!flowData) {
    return <div>No flow data</div>;
  }

  // Render the form with minimal React interference
  // Let Kratos handle everything natively
  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-6">Sign In (Native Kratos)</h1>
      
      {/* Render form as raw HTML to avoid React interference */}
      <div dangerouslySetInnerHTML={{
        __html: `
          <form action="${flowData.ui.action}" method="${flowData.ui.method}" id="kratos-login-form">
            ${flowData.ui.nodes.map(node => {
              // CSRF token
              if (node.attributes.name === 'csrf_token') {
                return `<input type="hidden" name="${node.attributes.name}" value="${node.attributes.value}">`;
              }
              
              // Hidden fields
              if (node.attributes.type === 'hidden') {
                return `<input type="hidden" name="${node.attributes.name}" value="${node.attributes.value || ''}">`;
              }
              
              // Identifier field
              if (node.attributes.name === 'identifier') {
                return `
                  <div class="mb-4">
                    <label class="block text-gray-300 mb-2">Email</label>
                    <input
                      name="${node.attributes.name}"
                      type="${node.attributes.type}"
                      class="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                      required="${node.attributes.required}"
                      autocomplete="username webauthn"
                    >
                  </div>
                `;
              }
              
              // Password field
              if (node.attributes.name === 'password') {
                return `
                  <div class="mb-4">
                    <label class="block text-gray-300 mb-2">Password</label>
                    <input
                      name="${node.attributes.name}"
                      type="${node.attributes.type}"
                      class="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                      required="${node.attributes.required}"
                      autocomplete="current-password"
                    >
                  </div>
                `;
              }
              
              // WebAuthn button
              if (node.attributes.type === 'button' && node.attributes.onclick) {
                const label = node.meta?.label?.text || 'Sign in with Passkey';
                return `
                  <button
                    type="button"
                    name="${node.attributes.name}"
                    value="${node.attributes.value || ''}"
                    onclick="${node.attributes.onclick}"
                    class="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 mb-4 font-semibold"
                  >
                    ${label}
                  </button>
                `;
              }
              
              // Submit buttons
              if (node.attributes.type === 'submit') {
                const label = node.meta?.label?.text || node.attributes.value;
                return `
                  <button
                    type="submit"
                    name="${node.attributes.name}"
                    value="${node.attributes.value}"
                    class="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 mb-2"
                  >
                    ${label}
                  </button>
                `;
              }
              
              // Script nodes
              if (node.type === 'script') {
                return `<script ${Object.entries(node.attributes).map(([k,v]) => `${k}="${v}"`).join(' ')}></script>`;
              }
              
              return '';
            }).join('')}
          </form>
        `
      }} />
      
      {/* Show any flow messages */}
      {flowData.ui.messages?.map((msg, index) => (
        <div key={index} className={`mt-4 p-3 rounded ${
          msg.type === 'error' ? 'bg-red-900/50 text-red-300' : 'bg-yellow-900/50 text-yellow-300'
        }`}>
          {msg.text}
        </div>
      ))}
    </div>
  );
};

export default KratosNativeLogin;