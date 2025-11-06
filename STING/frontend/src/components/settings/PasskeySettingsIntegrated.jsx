import React, { useState, useEffect } from 'react';
import {
  Key,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle,
  Shield,
  Loader
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';
import CertificateWarning from '../common/CertificateWarning';

/**
 * PasskeySettingsIntegrated - Uses custom WebAuthn endpoints for passkey management
 * Provides in-app passkey registration without redirecting to Kratos UI
 */
const PasskeySettingsIntegrated = () => {
  const { themeColors } = useTheme();
  const { identity } = useKratos();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Component identifier for debugging
  console.log('🚀 PASSKEY COMPONENT: PasskeySettingsIntegrated is rendering (v7 - ' + new Date().getTime() + ')');
  console.log('🚀 Identity from Kratos:', identity);
  console.log('🚀 Loading state:', loading);
  
  const [passkeys, setPasskeys] = useState([]);
  const [hasPasskeys, setHasPasskeys] = useState(false);
  
  // Fetch passkeys from custom endpoint
  useEffect(() => {
    const fetchPasskeys = async () => {
      try {
        const response = await axios.get('/api/webauthn/passkeys', {
          withCredentials: true
        });
        
        if (response.data.passkeys) {
          setPasskeys(response.data.passkeys);
          setHasPasskeys(response.data.passkeys.length > 0);
        }
      } catch (err) {
        console.error('Failed to fetch passkeys:', err);
        // Fallback to Kratos identity if custom endpoint fails
        const kratosPasskeys = identity?.credentials?.webauthn?.config?.credentials || [];
        setPasskeys(kratosPasskeys);
        setHasPasskeys(kratosPasskeys.length > 0);
      }
    };
    
    if (identity) {
      fetchPasskeys();
    }
  }, [identity]);

  const handleAddPasskey = async () => {
    console.log('🔐 handleAddPasskey called - VERSION 4');
    console.log('🔐 Identity:', identity);
    console.log('🔐 Identity traits:', identity?.traits);
    console.log('🔐 Identity email:', identity?.traits?.email || identity?.email);
    console.log('🔐 Button was clicked at:', new Date().toISOString());
    
    // Check if function is even executing
    alert('Add Passkey button clicked! Check console for logs.');
    
    // Use custom WebAuthn registration instead of Kratos flow
    try {
      setLoading(true);
      setError('');
      
      const username = identity?.traits?.email || identity?.email;
      if (!username) {
        console.error('🔐 No username found!');
        setError('No email address found. Please ensure you are logged in.');
        setLoading(false);
        return;
      }
      
      // Start custom WebAuthn registration
      console.log('🔐 Starting custom WebAuthn registration...');
      console.log('🔐 Sending username:', username);
      
      const requestBody = { username: username };
      console.log('🔐 Request body:', JSON.stringify(requestBody));
      console.log('🔐 Request body length:', JSON.stringify(requestBody).length);
      console.log('🔐 CACHE BUSTER v2: This is the updated code with username field');
      
      const beginResponse = await axios.post('/api/webauthn/registration/begin', requestBody, {
        withCredentials: true,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      
      console.log('🔐 Registration begin response:', beginResponse.data);
      
      if (beginResponse.data.publicKey) {
        console.log('🔐 Received publicKey options:', beginResponse.data.publicKey);
        
        // Convert base64url strings to ArrayBuffers for WebAuthn API
        const publicKeyCredentialCreationOptions = {
          ...beginResponse.data.publicKey,
          challenge: base64UrlToArrayBuffer(beginResponse.data.publicKey.challenge),
          user: {
            ...beginResponse.data.publicKey.user,
            id: base64UrlToArrayBuffer(beginResponse.data.publicKey.user.id)
          }
        };
        
        console.log('🔐 Converted options for WebAuthn:', publicKeyCredentialCreationOptions);
        
        // Create credentials using the browser's WebAuthn API
        const credential = await navigator.credentials.create({
          publicKey: publicKeyCredentialCreationOptions
        });
        
        console.log('🔐 Created credential:', credential);
        
        // Validate credential before accessing properties
        if (!credential || !credential.id || !credential.rawId || !credential.response) {
          console.error('❌ Invalid credential received from authenticator:', credential);
          throw new Error('Invalid credential received from authenticator');
        }
        
        // Complete the registration
        const completeResponse = await axios.post('/api/webauthn/registration/complete', {
          id: credential.id,
          rawId: arrayBufferToBase64Url(credential.rawId),
          type: credential.type,
          response: {
            clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
            attestationObject: arrayBufferToBase64Url(credential.response.attestationObject)
          },
          challenge_id: beginResponse.data.challenge_id
        }, {
          withCredentials: true
        });
        
        console.log('🔐 Registration complete response:', completeResponse.data);
        
        if (completeResponse.data.status === 'success') {
          setSuccess('Passkey registered successfully!');
          // Refresh the page to update the passkey list
          setTimeout(() => {
            window.location.reload();
          }, 1500);
        }
      }
    } catch (err) {
      console.error('🔐 Passkey registration error:', err);
      
      if (err.name === 'NotAllowedError') {
        setError('Passkey registration was cancelled or not allowed.');
      } else if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else {
        setError('Failed to register passkey. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRemovePasskey = async (credentialId) => {
    if (!window.confirm('Are you sure you want to remove this passkey?')) {
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      const response = await axios.delete(`/api/webauthn/passkeys/${credentialId}`, {
        withCredentials: true
      });
      
      if (response.data.status === 'success') {
        setSuccess('Passkey removed successfully');
        // Refresh the page to update the passkey list
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to remove passkey:', err);
      setError(err.response?.data?.error || 'Failed to remove passkey');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString();
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

  // Add a test to see if component is interactive
  useEffect(() => {
    console.log('🔴 PasskeySettingsIntegrated mounted/updated');
    console.log('🔴 Component can access window:', typeof window !== 'undefined');
    console.log('🔴 Component in React:', typeof React !== 'undefined');
    
    // Test if we can add event listeners directly
    const testButton = document.getElementById('passkey-test-button');
    if (testButton) {
      console.log('🔴 Found test button, adding direct listener');
      testButton.addEventListener('click', () => {
        console.log('🔴 Direct DOM event listener fired!');
        alert('Direct DOM listener worked!');
      });
    }
  }, []);
  
  return (
    <div className="space-y-6">
      <div className="pb-6 border-b border-gray-600">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Passkeys</h2>
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <Shield className="w-4 h-4" />
            <span>Passwordless authentication</span>
          </div>
        </div>
        
        <p className="text-gray-400 mb-6">
          Passkeys provide a secure, passwordless way to sign in using biometrics, security keys, or device credentials.
        </p>

        {/* Certificate Trust Warning */}
        <CertificateWarning className="mb-6" />

        {/* Email Verification Notice */}
        {identity && identity.verifiable_addresses && identity.verifiable_addresses.length > 0 && !identity.verifiable_addresses[0].verified && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 mb-6">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-yellow-300 mb-1">
                  Email Verification Required
                </p>
                <p className="text-sm text-gray-300">
                  Please verify your email address to enable passkey setup. Check your inbox for a verification email from STING Platform.
                </p>
                <ul className="text-sm text-gray-400 mt-2 space-y-1">
                  <li>• Check your email inbox and spam folder</li>
                  <li>• Click the verification link in the email</li>
                  <li>• After verification, return here to set up your passkey</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Status Card */}
        <div className={`dynamic-card-subtle p-4 mb-6 rounded-lg ${
          hasPasskeys ? 'bg-green-900/30 border-green-700' : 'bg-gray-700 border-gray-600'
        } border`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {hasPasskeys ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-yellow-500" />
              )}
              <div>
                <p className="font-medium text-white">
                  {hasPasskeys ? `${passkeys.length} Passkey${passkeys.length > 1 ? 's' : ''} Configured` : 'No Passkeys Configured'}
                </p>
                <p className="text-sm text-gray-400">
                  {hasPasskeys 
                    ? 'Your account is protected with passkey authentication' 
                    : 'Add a passkey to enable passwordless sign-in'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Passkey List */}
        {hasPasskeys && (
          <div className="space-y-3 mb-6">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Your Passkeys</h3>
            {passkeys.map((passkey, index) => (
              <div key={passkey.id || index} className="dynamic-card-subtle p-4 bg-gray-700 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-gray-600 rounded-lg">
                      <Key className="w-5 h-5 text-yellow-500" />
                    </div>
                    <div>
                      <p className="font-medium text-white">
                        {passkey.display_name || `Passkey ${index + 1}`}
                      </p>
                      <p className="text-sm text-gray-400">
                        Added on {formatDate(passkey.created_at)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemovePasskey(passkey.id)}
                    className="text-red-400 hover:text-red-300 p-2"
                    title="Remove passkey"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Test Button with ID for direct DOM access */}
        <button
          id="passkey-test-button"
          className="mb-4 px-4 py-2 bg-red-500 text-white rounded"
        >
          Test DOM Button (ID: passkey-test-button)
        </button>
        
        {/* Add Passkey Button */}
        <button
          onClick={(e) => {
            console.log('🔴 BUTTON CLICKED - Direct onClick handler');
            e.preventDefault();
            e.stopPropagation();
            handleAddPasskey();
          }}
          onMouseDown={() => console.log('🔴 MouseDown event')}
          onPointerDown={() => console.log('🔴 PointerDown event')}
          disabled={loading}
          className="floating-button flex items-center justify-center px-4 py-2 bg-yellow-500 text-black font-medium rounded-lg hover:bg-yellow-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ zIndex: 10, pointerEvents: 'auto' }}
        >
          {loading ? (
            <Loader className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Plus className="w-4 h-4 mr-2" />
          )}
          {hasPasskeys ? 'Add Another Passkey' : 'Add Your First Passkey'}
        </button>


        {/* Information Box */}
        <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-400 mb-2">About Passkeys</h3>
          <ul className="space-y-2 text-sm text-gray-300">
            <li className="flex items-start">
              <span className="text-blue-400 mr-2">•</span>
              <span>Works with Face ID, Touch ID, Windows Hello, or security keys</span>
            </li>
            <li className="flex items-start">
              <span className="text-blue-400 mr-2">•</span>
              <span>More secure than passwords - can't be phished or stolen</span>
            </li>
            <li className="flex items-start">
              <span className="text-blue-400 mr-2">•</span>
              <span>Synced across your devices through your platform account</span>
            </li>
          </ul>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg flex items-center">
            <AlertCircle className="w-4 h-4 text-red-400 mr-2" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
        )}
        
        {success && (
          <div className="mt-4 p-3 bg-green-900/50 border border-green-700 rounded-lg flex items-center">
            <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
            <span className="text-green-300 text-sm">{success}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PasskeySettingsIntegrated;