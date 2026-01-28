import React, { useState, useEffect } from 'react';
import { Shield, Key, CheckCircle, AlertCircle, RefreshCw, UserPlus, LogIn, Trash2 } from 'lucide-react';
import axios from 'axios';

const PasskeyDebugPanel = () => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({});
  const [testResults, setTestResults] = useState([]);
  const [testUser, setTestUser] = useState(null);
  const [passkeys, setPasskeys] = useState([]);
  
  const apiUrl = window.env?.REACT_APP_API_URL || 'https://localhost:5050';
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';

  // Check WebAuthn support
  useEffect(() => {
    checkWebAuthnSupport();
  }, []);

  const checkWebAuthnSupport = async () => {
    const results = {
      browserSupport: !!window.PublicKeyCredential,
      platformAuthenticator: false,
      conditionalUI: false
    };

    if (window.PublicKeyCredential) {
      try {
        results.platformAuthenticator = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        results.conditionalUI = await window.PublicKeyCredential.isConditionalMediationAvailable?.() || false;
      } catch (err) {
        console.error('Error checking WebAuthn capabilities:', err);
      }
    }

    setStatus(results);
    addResult('WebAuthn Support Check', results.browserSupport ? 'success' : 'error', results);
  };

  const addResult = (test, status, details) => {
    setTestResults(prev => [...prev, {
      test,
      status,
      details,
      timestamp: new Date().toISOString()
    }]);
  };

  // Create test user
  const createTestUser = async () => {
    setLoading(true);
    try {
      // Create registration flow
      const flowResponse = await axios.get(`${kratosUrl}/self-service/registration/api`, {
        withCredentials: true
      });
      
      const flowId = flowResponse.data.id;
      const email = `passkey_test_${Date.now()}@example.com`;
      const password = 'TestPass123!';

      // Register user
      const regResponse = await axios.post(
        `${kratosUrl}/self-service/registration?flow=${flowId}`,
        {
          'traits.email': email,
          'traits.name.first': 'Passkey',
          'traits.name.last': 'Debug',
          password: password,
          method: 'password'
        },
        { withCredentials: true }
      );

      const sessionToken = regResponse.data.session_token;
      const identity = regResponse.data.identity;

      setTestUser({
        email,
        password,
        sessionToken,
        identityId: identity.id
      });

      addResult('Test User Creation', 'success', { email, identityId: identity.id });
      return { email, password, sessionToken };
    } catch (err) {
      addResult('Test User Creation', 'error', err.response?.data || err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Test passkey registration
  const testPasskeyRegistration = async () => {
    setLoading(true);
    try {
      if (!testUser) {
        await createTestUser();
      }

      // Start registration
      const beginResponse = await axios.post(
        `${apiUrl}/api/webauthn/registration/begin`,
        {
          username: testUser.email,
          user_id: testUser.email
        },
        {
          headers: {
            'X-Session-Token': testUser.sessionToken
          },
          withCredentials: true
        }
      );

      const options = beginResponse.data;
      addResult('Registration Begin', 'success', { challenge: options.challenge });

      // Create credential
      const credential = await navigator.credentials.create({
        publicKey: {
          ...options,
          challenge: Uint8Array.from(atob(options.challenge), c => c.charCodeAt(0)),
          user: {
            ...options.user,
            id: Uint8Array.from(atob(options.user.id), c => c.charCodeAt(0))
          }
        }
      });

      // Complete registration
      const completeResponse = await axios.post(
        `${apiUrl}/api/webauthn/registration/complete`,
        {
          credential: {
            id: credential.id,
            rawId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
            response: {
              attestationObject: btoa(String.fromCharCode(...new Uint8Array(credential.response.attestationObject))),
              clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(credential.response.clientDataJSON)))
            },
            type: credential.type
          },
          challenge_id: options.challenge_id,
          user_id: testUser.email,
          username: testUser.email
        },
        {
          headers: {
            'X-Session-Token': testUser.sessionToken
          },
          withCredentials: true
        }
      );

      addResult('Passkey Registration', 'success', completeResponse.data);
      await loadPasskeys();
    } catch (err) {
      addResult('Passkey Registration', 'error', err.response?.data || err.message);
    } finally {
      setLoading(false);
    }
  };

  // Test passkey authentication
  const testPasskeyAuthentication = async () => {
    setLoading(true);
    try {
      // Start authentication
      const beginResponse = await axios.post(
        `${apiUrl}/api/webauthn/authentication/begin`,
        {
          username: testUser?.email || prompt('Enter test user email:')
        },
        { withCredentials: true }
      );

      const options = beginResponse.data;
      addResult('Authentication Begin', 'success', { challenge: options.challenge });

      // Get credential
      const credential = await navigator.credentials.get({
        publicKey: {
          ...options,
          challenge: Uint8Array.from(atob(options.challenge), c => c.charCodeAt(0)),
          allowCredentials: options.allowCredentials?.map(cred => {
            // Validate credential object before accessing properties
            if (!cred || !cred.id) {
              throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
            }
            return {
              ...cred,
              id: Uint8Array.from(atob(cred.id), c => c.charCodeAt(0))
            };
          })
        }
      });

      // Validate credential before using it
      if (!credential) {
        throw new Error('Authentication was cancelled');
      }

      if (!credential.id || !credential.rawId || !credential.response) {
        console.error('🔐 Invalid credential object received:', credential);
        throw new Error('Invalid credential received from authenticator');
      }

      // Complete authentication
      const completeResponse = await axios.post(
        `${apiUrl}/api/webauthn/authentication/complete`,
        {
          credential: {
            id: credential.id,
            rawId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
            response: {
              authenticatorData: btoa(String.fromCharCode(...new Uint8Array(credential.response.authenticatorData))),
              clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(credential.response.clientDataJSON))),
              signature: btoa(String.fromCharCode(...new Uint8Array(credential.response.signature))),
              userHandle: credential.response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(credential.response.userHandle))) : null
            },
            type: credential.type
          },
          challenge_id: options.challenge_id
        },
        { withCredentials: true }
      );

      addResult('Passkey Authentication', 'success', completeResponse.data);
    } catch (err) {
      addResult('Passkey Authentication', 'error', err.response?.data || err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load user's passkeys
  const loadPasskeys = async () => {
    if (!testUser?.sessionToken) return;

    try {
      const response = await axios.get(`${apiUrl}/api/webauthn/passkeys`, {
        headers: {
          'X-Session-Token': testUser.sessionToken
        },
        withCredentials: true
      });
      setPasskeys(response.data.passkeys || []);
    } catch (err) {
      console.error('Failed to load passkeys:', err);
    }
  };

  // Test passwordless flow
  const testPasswordlessFlow = async () => {
    setLoading(true);
    try {
      // Check if passwordless trigger exists
      const loginFlow = await axios.get(`${kratosUrl}/self-service/login/api`, {
        withCredentials: true
      });

      const webauthnTrigger = loginFlow.data.ui.nodes.find(node => 
        node.attributes?.name === 'webauthn_login_trigger'
      );

      if (webauthnTrigger) {
        addResult('Passwordless Trigger Found', 'success', {
          trigger: webauthnTrigger.attributes.name,
          onclick: webauthnTrigger.attributes.onclick ? 'Present' : 'Missing'
        });
      } else {
        addResult('Passwordless Trigger', 'warning', {
          message: 'No passwordless trigger found. User needs registered passkey first.'
        });
      }
    } catch (err) {
      addResult('Passwordless Flow Check', 'error', err.message);
    } finally {
      setLoading(false);
    }
  };

  // Clear test data
  const clearTestData = () => {
    setTestUser(null);
    setPasskeys([]);
    setTestResults([]);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-blue-400" />
        <h2 className="text-xl font-semibold text-white">Passkey Debug Panel</h2>
      </div>

      {/* WebAuthn Status */}
      <div className="mb-6 p-4 bg-gray-700 rounded-lg">
        <h3 className="text-lg font-medium text-white mb-3">WebAuthn Support</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            {status.browserSupport ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
            <span className="text-gray-300">Browser Support</span>
          </div>
          <div className="flex items-center gap-2">
            {status.platformAuthenticator ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-400" />
            )}
            <span className="text-gray-300">Platform Authenticator (Touch ID, Face ID, Windows Hello)</span>
          </div>
          <div className="flex items-center gap-2">
            {status.conditionalUI ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-400" />
            )}
            <span className="text-gray-300">Conditional UI (Autofill)</span>
          </div>
        </div>
      </div>

      {/* Test User Info */}
      {testUser && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg">
          <h3 className="text-lg font-medium text-white mb-2">Test User</h3>
          <div className="space-y-1 text-sm text-gray-300">
            <p>Email: {testUser.email}</p>
            <p>Password: {testUser.password}</p>
            <p>Session Token: {testUser.sessionToken?.substring(0, 20)}...</p>
          </div>
        </div>
      )}

      {/* Passkeys List */}
      {passkeys.length > 0 && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg">
          <h3 className="text-lg font-medium text-white mb-2">Registered Passkeys</h3>
          <div className="space-y-2">
            {passkeys.map((passkey, index) => (
              <div key={passkey.id} className="flex items-center justify-between text-sm text-gray-300">
                <span>{index + 1}. {passkey.name || 'Unnamed Passkey'}</span>
                <span className="text-xs text-gray-500">ID: {passkey.id}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Test Actions */}
      <div className="space-y-3 mb-6">
        <button
          onClick={createTestUser}
          disabled={loading || testUser}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <UserPlus className="w-4 h-4" />
          Create Test User
        </button>

        <button
          onClick={testPasskeyRegistration}
          disabled={loading || !status.browserSupport}
          className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <Key className="w-4 h-4" />
          Test Passkey Registration
        </button>

        <button
          onClick={testPasskeyAuthentication}
          disabled={loading || !status.browserSupport}
          className="w-full py-2 px-4 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <LogIn className="w-4 h-4" />
          Test Passkey Authentication
        </button>

        <button
          onClick={testPasswordlessFlow}
          disabled={loading}
          className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <Shield className="w-4 h-4" />
          Test Passwordless Flow
        </button>

        <button
          onClick={() => {
            checkWebAuthnSupport();
            loadPasskeys();
          }}
          disabled={loading}
          className="w-full py-2 px-4 bg-gray-600 hover:bg-gray-700 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh Status
        </button>

        <button
          onClick={clearTestData}
          className="w-full py-2 px-4 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center justify-center gap-2"
        >
          <Trash2 className="w-4 h-4" />
          Clear Test Data
        </button>
      </div>

      {/* Test Results */}
      {testResults.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-white mb-2">Test Results</h3>
          {testResults.map((result, index) => (
            <div key={index} className={`p-3 rounded-lg ${
              result.status === 'success' ? 'bg-green-900/30 border border-green-700' :
              result.status === 'warning' ? 'bg-yellow-900/30 border border-yellow-700' :
              'bg-red-900/30 border border-red-700'
            }`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-white">{result.test}</span>
                <span className={`text-xs ${
                  result.status === 'success' ? 'text-green-400' :
                  result.status === 'warning' ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {result.status.toUpperCase()}
                </span>
              </div>
              <pre className="text-xs text-gray-300 overflow-x-auto">
                {JSON.stringify(result.details, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* Recovery Flow Note */}
      <div className="mt-6 p-4 bg-blue-900/30 border border-blue-700 rounded-lg">
        <h4 className="text-sm font-medium text-blue-300 mb-2">Recovery Flow Testing</h4>
        <p className="text-xs text-gray-400">
          When users lose their passkey, they'll need:
        </p>
        <ul className="text-xs text-gray-400 ml-4 mt-1 list-disc">
          <li>Email/SMS OTP verification (to be implemented)</li>
          <li>Recovery codes (if enabled)</li>
          <li>Admin assistance for account recovery</li>
        </ul>
      </div>
    </div>
  );
};

export default PasskeyDebugPanel;