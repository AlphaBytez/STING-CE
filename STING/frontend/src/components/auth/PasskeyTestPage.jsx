import React, { useState, useEffect } from 'react';

/**
 * PasskeyTestPage - A simple component to test WebAuthn/Passkey support
 * This component provides buttons to directly test WebAuthn functionality
 * without going through the Kratos flow.
 */
const PasskeyTestPage = () => {
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [platformAuthSupported, setPlatformAuthSupported] = useState(false);
  const [testStatus, setTestStatus] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [debugLog, setDebugLog] = useState([]);

  // Add to debug log
  const logDebug = (message) => {
    console.log(message);
    setDebugLog(prev => [...prev, `${new Date().toISOString().slice(11, 23)}: ${message}`]);
  };

  // Check WebAuthn support
  useEffect(() => {
    const checkWebAuthnSupport = async () => {
      logDebug('Checking WebAuthn support in browser...');
      
      try {
        // Check if browser supports WebAuthn
        if (window.PublicKeyCredential) {
          logDebug('✅ PublicKeyCredential API exists');
          setWebAuthnSupported(true);
          
          try {
            const platformAuthAvailable = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            logDebug(`Platform authenticator available: ${platformAuthAvailable}`);
            setPlatformAuthSupported(platformAuthAvailable);
          } catch (err) {
            logDebug(`❌ Error checking platform authenticator: ${err.message}`);
            setPlatformAuthSupported(false);
          }
        } else {
          logDebug('❌ WebAuthn API (PublicKeyCredential) not supported in this browser');
          setWebAuthnSupported(false);
        }
      } catch (err) {
        logDebug(`❌ Error during WebAuthn check: ${err.message}`);
        setWebAuthnSupported(false);
      }
    };
    
    checkWebAuthnSupport();
  }, []);
  
  // Test WebAuthn registration
  const testRegistration = async () => {
    setTestStatus('Starting WebAuthn registration test...');
    logDebug('Testing WebAuthn registration...');
    
    try {
      if (!navigator.credentials || !navigator.credentials.create) {
        throw new Error('Credentials API not supported');
      }
      
      // Create a random user ID
      const userId = new Uint8Array(16);
      window.crypto.getRandomValues(userId);
      
      // Create challenge
      const challenge = new Uint8Array(32);
      window.crypto.getRandomValues(challenge);
      
      const publicKeyCredentialCreationOptions = {
        challenge,
        rp: {
          name: 'STING Test',
          id: window.location.hostname,
        },
        user: {
          id: userId,
          name: 'test@example.com',
          displayName: 'Test User',
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 }, // ES256
          { type: 'public-key', alg: -257 }, // RS256
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'preferred',
          requireResidentKey: true,
        },
        timeout: 60000,
        attestation: 'none',
      };
      
      logDebug('Calling navigator.credentials.create()...');
      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      });
      
      logDebug('Registration successful!');
      setTestStatus('Registration successful!');
      setTestResult({
        id: credential.id,
        type: credential.type,
        authenticatorAttachment: credential.authenticatorAttachment,
      });
    } catch (err) {
      logDebug(`❌ Registration failed: ${err.message}`);
      setTestStatus(`Registration failed: ${err.message}`);
      setTestResult(null);
    }
  };
  
  // Test WebAuthn authentication
  const testAuthentication = async () => {
    setTestStatus('Starting WebAuthn authentication test...');
    logDebug('Testing WebAuthn authentication...');
    
    try {
      if (!navigator.credentials || !navigator.credentials.get) {
        throw new Error('Credentials API not supported');
      }
      
      // Create challenge
      const challenge = new Uint8Array(32);
      window.crypto.getRandomValues(challenge);
      
      const publicKeyCredentialRequestOptions = {
        challenge,
        timeout: 60000,
        userVerification: 'preferred',
        rpId: window.location.hostname,
      };
      
      logDebug('Calling navigator.credentials.get()...');
      const assertion = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      });
      
      logDebug('Authentication successful!');
      setTestStatus('Authentication successful!');
      setTestResult({
        id: assertion.id,
        type: assertion.type,
      });
    } catch (err) {
      logDebug(`❌ Authentication failed: ${err.message}`);
      setTestStatus(`Authentication failed: ${err.message}`);
      setTestResult(null);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white p-4">
      <div className="w-full max-w-xl bg-gray-800 p-8 rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold mb-8 text-center">WebAuthn/Passkey Test Page</h1>
        
        {/* Support Status */}
        <div className="mb-8 p-4 bg-gray-700 rounded-lg">
          <h2 className="text-lg font-semibold mb-4">WebAuthn Support Status</h2>
          <div className="grid grid-cols-2 gap-2">
            <div className="font-medium">WebAuthn API:</div>
            <div>
              {webAuthnSupported ? 
                <span className="text-green-400">Supported ✅</span> : 
                <span className="text-red-400">Not Supported ❌</span>
              }
            </div>
            
            <div className="font-medium">Platform Authenticator:</div>
            <div>
              {platformAuthSupported ? 
                <span className="text-green-400">Available ✅</span> : 
                <span className="text-red-400">Not Available ❌</span>
              }
            </div>
          </div>
        </div>
        
        {/* Test Controls */}
        <div className="mb-8 flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4">
          <button 
            onClick={testRegistration}
            disabled={!webAuthnSupported}
            className={`flex-1 py-2 px-4 rounded-lg ${
              webAuthnSupported 
                ? 'bg-blue-600 hover:bg-blue-700' 
                : 'bg-gray-600 cursor-not-allowed'
            }`}
          >
            Test Registration
          </button>
          
          <button 
            onClick={testAuthentication}
            disabled={!webAuthnSupported}
            className={`flex-1 py-2 px-4 rounded-lg ${
              webAuthnSupported 
                ? 'bg-green-600 hover:bg-green-700' 
                : 'bg-gray-600 cursor-not-allowed'
            }`}
          >
            Test Authentication
          </button>
        </div>
        
        {/* Test Results */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-2">Test Results</h2>
          <div className="p-4 bg-gray-700 rounded-lg">
            <p className="mb-2">{testStatus || 'No test run yet'}</p>
            {testResult && (
              <pre className="bg-gray-900 p-3 rounded overflow-x-auto text-sm">
                {JSON.stringify(testResult, null, 2)}
              </pre>
            )}
          </div>
        </div>
        
        {/* Debug Log */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Debug Log</h2>
          <div className="p-4 bg-gray-900 rounded-lg max-h-60 overflow-y-auto text-sm font-mono">
            {debugLog.length > 0 ? (
              <div className="flex flex-col space-y-1">
                {debugLog.map((log, index) => (
                  <div key={index} className="whitespace-pre-wrap">
                    {log}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No log entries</p>
            )}
          </div>
        </div>
        
        <div className="mt-6 text-center">
          <a href="/login" className="text-blue-400 hover:underline">
            Return to Login
          </a>
        </div>
      </div>
    </div>
  );
};

export default PasskeyTestPage;