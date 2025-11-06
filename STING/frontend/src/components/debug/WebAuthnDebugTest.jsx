import React, { useState } from 'react';
import { Button, Card, Alert, Typography, Divider } from 'antd';
import { SafetyOutlined, BugOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

/**
 * WebAuthn Debug Test Component
 * 
 * This component provides a standalone test for WebAuthn authentication
 * to help debug the "Cannot read properties of undefined (reading 'id')" error.
 */
const WebAuthnDebugTest = () => {
  const [testResults, setTestResults] = useState([]);
  const [isRunning, setIsRunning] = useState(false);

  const addResult = (type, message, data = null) => {
    const timestamp = new Date().toLocaleTimeString();
    setTestResults(prev => [...prev, { type, message, data, timestamp }]);
  };

  const clearResults = () => {
    setTestResults([]);
  };

  const base64UrlToArrayBuffer = (base64url) => {
    try {
      const padding = '='.repeat((4 - base64url.length % 4) % 4);
      const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
      const binary = window.atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      return bytes.buffer;
    } catch (error) {
      addResult('error', `Base64 decoding failed: ${error.message}`);
      throw error;
    }
  };

  const arrayBufferToBase64Url = (buffer) => {
    try {
      const bytes = new Uint8Array(buffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const base64 = window.btoa(binary);
      return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    } catch (error) {
      addResult('error', `Base64 encoding failed: ${error.message}`);
      throw error;
    }
  };

  const runWebAuthnTest = async () => {
    setIsRunning(true);
    clearResults();
    
    try {
      addResult('info', 'Starting WebAuthn authentication test...');
      
      // Step 1: Check WebAuthn support
      if (!window.PublicKeyCredential) {
        addResult('error', 'WebAuthn not supported in this browser');
        return;
      }
      addResult('success', 'WebAuthn is supported');

      // Step 2: Test authentication begin
      addResult('info', 'Calling /api/webauthn/authentication/begin...');
      
      let beginResponse;
      try {
        beginResponse = await axios.post('/api/webauthn/authentication/begin', {
          username: 'test@example.com' // You can change this
        }, {
          withCredentials: true
        });
        
        addResult('success', 'Authentication begin successful', {
          hasPublicKey: !!beginResponse.data.publicKey,
          hasChallenge: !!beginResponse.data.challenge_id,
          challengeLength: beginResponse.data.challenge_id?.length,
          allowedCredentials: beginResponse.data.publicKey?.allowCredentials?.length || 0
        });
      } catch (error) {
        addResult('error', `Authentication begin failed: ${error.response?.data?.error || error.message}`);
        return;
      }

      // Step 3: Validate response structure
      if (!beginResponse.data.publicKey) {
        addResult('error', 'Missing publicKey in response');
        return;
      }

      if (!beginResponse.data.challenge_id) {
        addResult('error', 'Missing challenge_id in response');
        return;
      }

      addResult('info', 'Response structure is valid');

      // Step 4: Prepare WebAuthn options
      let publicKeyCredentialRequestOptions;
      try {
        publicKeyCredentialRequestOptions = {
          ...beginResponse.data.publicKey,
          challenge: base64UrlToArrayBuffer(beginResponse.data.publicKey.challenge),
          allowCredentials: beginResponse.data.publicKey.allowCredentials?.map(cred => {
            // Validate credential object before accessing properties
            if (!cred || !cred.id) {
              throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
            }
            return {
              ...cred,
              id: base64UrlToArrayBuffer(cred.id)
            };
          })
        };
        
        addResult('success', 'WebAuthn options prepared successfully');
      } catch (error) {
        addResult('error', `Failed to prepare WebAuthn options: ${error.message}`);
        return;
      }

      // Step 5: Test WebAuthn credential request
      addResult('info', 'Requesting credential from browser (you may see a passkey prompt)...');
      
      let credential;
      try {
        credential = await navigator.credentials.get({
          publicKey: publicKeyCredentialRequestOptions
        });
        
        if (!credential) {
          addResult('warning', 'Credential request was cancelled by user');
          return;
        }
        
        addResult('success', 'Credential received from browser', {
          id: credential.id,
          type: credential.type,
          hasRawId: !!credential.rawId,
          hasResponse: !!credential.response,
          hasAuthenticatorData: !!credential.response?.authenticatorData,
          hasClientDataJSON: !!credential.response?.clientDataJSON,
          hasSignature: !!credential.response?.signature
        });
        
      } catch (error) {
        if (error.name === 'NotAllowedError') {
          addResult('warning', 'Authentication was cancelled or not allowed');
        } else {
          addResult('error', `WebAuthn credential request failed: ${error.message}`);
        }
        return;
      }

      // Step 6: Validate credential object
      if (!credential) {
        addResult('error', 'FOUND THE ISSUE: credential object is null/undefined!', credential);
        return;
      }

      if (!credential.id) {
        addResult('error', 'FOUND THE ISSUE: credential.id is undefined!', credential);
        return;
      }

      if (!credential.rawId) {
        addResult('error', 'FOUND THE ISSUE: credential.rawId is undefined!', credential);
        return;
      }

      if (!credential.response) {
        addResult('error', 'FOUND THE ISSUE: credential.response is undefined!', credential);
        return;
      }

      addResult('success', 'Credential object validation passed');

      // Step 7: Prepare response data
      let response;
      try {
        response = {
          id: credential.id,
          rawId: arrayBufferToBase64Url(credential.rawId),
          type: credential.type,
          response: {
            authenticatorData: arrayBufferToBase64Url(credential.response.authenticatorData),
            clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
            signature: arrayBufferToBase64Url(credential.response.signature),
            userHandle: credential.response.userHandle ? arrayBufferToBase64Url(credential.response.userHandle) : null
          }
        };
        
        addResult('success', 'Response data prepared successfully');
      } catch (error) {
        addResult('error', `Failed to prepare response data: ${error.message}`);
        return;
      }

      // Step 8: Send authentication complete
      addResult('info', 'Sending authentication complete request...');
      
      try {
        const completeResponse = await axios.post('/api/webauthn/authentication/complete', {
          credential: response,
          challenge_id: beginResponse.data.challenge_id
        }, {
          withCredentials: true
        });
        
        if (completeResponse.data.success) {
          addResult('success', 'WebAuthn authentication completed successfully!', completeResponse.data);
        } else {
          addResult('warning', 'Authentication completed but not successful', completeResponse.data);
        }
        
      } catch (error) {
        addResult('error', `Authentication complete failed: ${error.response?.data?.error || error.message}`);
      }

    } catch (error) {
      addResult('error', `Unexpected error: ${error.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <Card title={
      <div className="flex items-center gap-2">
        <BugOutlined />
        <span>WebAuthn Debug Test</span>
      </div>
    }>
      <Paragraph>
        This component helps debug the WebAuthn "Cannot read properties of undefined (reading 'id')" error.
        Click the button below to run a comprehensive test of the WebAuthn authentication flow.
      </Paragraph>
      
      <div className="mb-4 flex gap-2">
        <Button 
          type="primary" 
          icon={<SafetyOutlined />}
          onClick={runWebAuthnTest}
          loading={isRunning}
          disabled={isRunning}
        >
          {isRunning ? 'Running Test...' : 'Run WebAuthn Test'}
        </Button>
        
        <Button onClick={clearResults} disabled={isRunning}>
          Clear Results
        </Button>
      </div>

      {testResults.length > 0 && (
        <>
          <Divider />
          <Title level={4}>Test Results</Title>
          
          <div className="space-y-2">
            {testResults.map((result, index) => (
              <Alert
                key={index}
                type={result.type}
                message={
                  <div>
                    <Text strong>[{result.timestamp}]</Text> {result.message}
                    {result.data && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-sm">View data</summary>
                        <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-auto">
                          {JSON.stringify(result.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                }
                showIcon
                className="text-sm"
              />
            ))}
          </div>
        </>
      )}
    </Card>
  );
};

export default WebAuthnDebugTest;