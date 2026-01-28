import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Modal, Button, Alert } from 'antd';
import { SafetyOutlined, LoadingOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useKratos } from '../../auth/KratosProviderRefactored';

const PasskeyAuthModal = ({ visible, onSuccess, onCancel, title = "Passkey Authentication Required" }) => {
  const { identity, checkSession } = useKratos();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [authState, setAuthState] = useState('idle'); // idle, authenticating, success

  useEffect(() => {
    if (!visible) {
      setError('');
      setAuthState('idle');
    }
  }, [visible]);

  const handlePasskeyAuth = async () => {
    setLoading(true);
    setError('');
    setAuthState('authenticating');

    try {
      // Start passkey authentication
      console.log('🔐 Starting passkey authentication...');
      const beginResponse = await axios.post('/api/webauthn/authentication/begin', {
        username: identity?.traits?.email || identity?.email
      }, {
        withCredentials: true
      });

      console.log('🔐 Authentication begin response:', beginResponse.data);

      if (!beginResponse.data.publicKey) {
        throw new Error('Invalid authentication challenge received');
      }

      // Prepare the credential request options
      const publicKeyCredentialRequestOptions = {
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

      // Request passkey authentication from the browser
      console.log('🔐 Requesting credential from browser with options:', publicKeyCredentialRequestOptions);
      const credential = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions
      });

      console.log('🔐 Received credential from browser:', credential);

      if (!credential) {
        throw new Error('Authentication was cancelled');
      }

      // Add additional validation to ensure credential has required properties
      if (!credential.id || !credential.rawId || !credential.response) {
        console.error('🔐 Invalid credential object:', credential);
        throw new Error('Invalid credential received from authenticator');
      }

      // Prepare the response
      const response = {
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

      console.log('🔐 Prepared credential response:', {
        id: response.id,
        type: response.type,
        hasAuthenticatorData: !!response.response.authenticatorData,
        hasClientDataJSON: !!response.response.clientDataJSON,
        hasSignature: !!response.response.signature
      });

      // Complete authentication
      console.log('🔐 Sending authentication complete request with:', {
        credential: response,
        challenge_id: beginResponse.data.challenge_id
      });
      
      const completeResponse = await axios.post('/api/webauthn/authentication/complete', {
        credential: response,
        challenge_id: beginResponse.data.challenge_id
      }, {
        withCredentials: true
      });

      console.log('🔐 Authentication complete response:', completeResponse.data);

      if (completeResponse.data.success) {
        setAuthState('success');
        
        // Refresh Kratos session
        await checkSession();
        
        // Brief success animation
        setTimeout(() => {
          onSuccess();
        }, 500);
      } else {
        throw new Error(completeResponse.data.message || 'Authentication failed');
      }
    } catch (err) {
      console.error('Passkey authentication error:', err);
      setAuthState('idle');
      
      if (err.name === 'NotAllowedError') {
        setError('Authentication was cancelled or timed out. Please try again.');
      } else if (err.message?.includes('No passkeys found')) {
        setError('No passkeys found. Please set up a passkey in your security settings first.');
      } else {
        setError(err.message || 'Passkey authentication failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Helper functions for base64url encoding/decoding
  const base64UrlToArrayBuffer = (base64url) => {
    const padding = '='.repeat((4 - base64url.length % 4) % 4);
    const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
    const binary = window.atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  };

  const arrayBufferToBase64Url = (buffer) => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64 = window.btoa(binary);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <SafetyOutlined className="text-2xl text-yellow-400" />
          <span className="text-xl font-semibold">{title}</span>
        </div>
      }
      open={visible}
      onCancel={onCancel}
      footer={null}
      centered
      className="passkey-auth-modal"
      width={480}
    >
      <div className="py-6">
        {authState === 'success' ? (
          <div className="text-center">
            <CheckCircleOutlined className="text-6xl text-green-500 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Authentication Successful!</h3>
            <p className="text-gray-400">Proceeding with your request...</p>
          </div>
        ) : (
          <>
            <div className="text-center mb-6">
              <div className="mb-4">
                <SafetyOutlined className="text-6xl text-yellow-400" />
              </div>
              <p className="text-gray-300 mb-2">
                This action requires passkey authentication for security.
              </p>
              <p className="text-sm text-gray-400">
                Your biometric or security key will be used to verify your identity.
              </p>
            </div>

            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                className="mb-4"
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)'
                }}
              />
            )}

            <div className="flex flex-col gap-3">
              <Button
                type="primary"
                size="large"
                icon={loading ? <LoadingOutlined /> : <SafetyOutlined />}
                onClick={handlePasskeyAuth}
                loading={loading}
                className="w-full h-12 text-lg font-semibold"
                style={{
                  background: loading ? 'rgba(234, 179, 8, 0.6)' : 'rgba(234, 179, 8, 1)',
                  borderColor: 'rgba(234, 179, 8, 1)',
                  color: '#000'
                }}
              >
                {loading ? 'Authenticating...' : 'Authenticate with Passkey'}
              </Button>

              <Button
                type="text"
                size="large"
                onClick={onCancel}
                className="text-gray-400 hover:text-gray-300"
                disabled={loading}
              >
                Cancel
              </Button>
            </div>

            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                Don't have a passkey? 
                <a 
                  href="/dashboard/settings" 
                  className="text-yellow-400 hover:text-yellow-300 ml-1"
                  onClick={(e) => {
                    e.preventDefault();
                    window.location.href = '/dashboard/settings?tab=security';
                  }}
                >
                  Set one up in Security Settings
                </a>
              </p>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};

export default PasskeyAuthModal;