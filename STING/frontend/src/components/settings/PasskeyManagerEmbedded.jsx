import React, { useState, useEffect, useRef } from 'react';
import { Key, Shield, Loader, AlertCircle } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasskeyManagerEmbedded = () => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showIframe, setShowIframe] = useState(false);
  const [flowUrl, setFlowUrl] = useState('');
  const iframeRef = useRef(null);

  // Load existing passkeys
  useEffect(() => {
    const loadPasskeys = async () => {
      try {
        setLoading(true);
        
        // Get passkeys from identity
        if (identity?.credentials?.webauthn) {
          const formattedPasskeys = identity.credentials.webauthn.map((cred, index) => ({
            id: cred.id || `passkey-${index}`,
            display_name: cred.display_name || `Passkey ${index + 1}`,
            created_at: cred.created_at,
            last_used: cred.updated_at || cred.created_at
          }));
          setPasskeys(formattedPasskeys);
        } else {
          setPasskeys([]);
        }
      } catch (err) {
        console.error('Error loading passkeys:', err);
        setError('Failed to load passkeys');
      } finally {
        setLoading(false);
      }
    };

    if (identity) {
      loadPasskeys();
    }
  }, [identity]);

  // Listen for messages from iframe
  useEffect(() => {
    const handleMessage = async (event) => {
      // Only handle messages from our domain
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'webauthn-complete') {
        console.log('🔐 WebAuthn registration complete');
        setShowIframe(false);
        await checkSession();
        window.location.reload(); // Refresh to show new passkey
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [checkSession]);

  // Monitor iframe for navigation
  useEffect(() => {
    if (showIframe && iframeRef.current) {
      const checkIframeUrl = setInterval(() => {
        try {
          // Try to access iframe location (will fail for cross-origin)
          const iframeUrl = iframeRef.current?.contentWindow?.location?.href;
          console.log('Iframe URL:', iframeUrl);
          
          // If we successfully accessed it and it's the success page, close iframe
          if (iframeUrl && iframeUrl.includes('/settings')) {
            clearInterval(checkIframeUrl);
            setShowIframe(false);
            checkSession();
            window.location.reload();
          }
        } catch (e) {
          // Cross-origin, can't access - this is expected
        }
      }, 1000);

      return () => clearInterval(checkIframeUrl);
    }
  }, [showIframe, checkSession]);

  // Start passkey registration
  const startRegistration = async () => {
    try {
      // Create settings flow
      const flowResponse = await axios.get('/.ory/self-service/settings/browser?', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flowId = flowResponse.data.id;
      
      // Set URL to show only WebAuthn section
      const url = `/.ory/self-service/settings/browser?flow=${flowId}`;
      setFlowUrl(url);
      setShowIframe(true);
    } catch (err) {
      console.error('Error creating settings flow:', err);
      setError('Failed to start passkey registration');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="w-8 h-8 animate-spin text-yellow-400" />
      </div>
    );
  }

  return (
    <div className={`max-w-4xl mx-auto p-6 ${themeColors.mainBg || 'bg-slate-800'}`}>
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Key className="w-8 h-8 text-yellow-400" />
              <div>
                <h1 className="text-2xl font-bold text-white">Passkey Management</h1>
                <p className="text-gray-400 text-sm mt-1">
                  Manage your passwordless authentication methods
                </p>
              </div>
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="mb-6 p-4 glass-subtle border border-red-500/30 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="text-red-300">{error}</span>
            </div>
          )}

          {/* WebAuthn Support Check */}
          {!window.PublicKeyCredential && (
            <div className="mb-6 p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
              <p className="text-yellow-300">
                Your browser doesn't support passkeys. Please use a modern browser like Chrome, Edge, or Safari.
              </p>
            </div>
          )}

          {/* Iframe for WebAuthn registration */}
          {showIframe && (
            <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
              <div className="bg-slate-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
                <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                  <h3 className="text-white font-semibold">Register Passkey</h3>
                  <button
                    onClick={() => setShowIframe(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
                <div className="relative h-[60vh]">
                  <iframe
                    ref={iframeRef}
                    src={flowUrl}
                    className="w-full h-full bg-white"
                    title="Passkey Registration"
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                  />
                </div>
                <div className="p-4 border-t border-slate-700 text-center text-sm text-gray-400">
                  Complete the passkey registration in the form above
                </div>
              </div>
            </div>
          )}

          {/* Existing Passkeys */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Your Passkeys</h2>
            
            {passkeys.length === 0 ? (
              <div className="p-6 bg-slate-700/30 border border-slate-600/50 rounded-lg text-center">
                <Shield className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                <p className="text-gray-400">No passkeys registered yet</p>
                <p className="text-gray-500 text-sm mt-1">
                  Add a passkey to enable passwordless sign-in
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {passkeys.map((passkey) => (
                  <div
                    key={passkey.id}
                    className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg hover:bg-slate-700/70 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Key className="w-5 h-5 text-yellow-400" />
                        <div>
                          <p className="text-white font-medium">{passkey.display_name}</p>
                          <p className="text-xs text-gray-400">
                            Added: {formatDate(passkey.created_at)}
                            {passkey.last_used && passkey.last_used !== passkey.created_at && (
                              <span> • Last used: {formatDate(passkey.last_used)}</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add New Passkey */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Add New Passkey</h2>
            
            <div className="p-6 bg-blue-900/20 border border-blue-700/50 rounded-lg">
              <button
                onClick={startRegistration}
                disabled={!window.PublicKeyCredential}
                className="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Key className="w-5 h-5" />
                <span>Register New Passkey</span>
              </button>
              <p className="text-gray-500 text-xs mt-3 text-center">
                A secure window will open to complete passkey registration
              </p>
            </div>
          </div>

          {/* Info Section */}
          <div className="mt-8 p-4 bg-slate-700/30 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">About Passkeys</h3>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>• Passkeys are a secure, passwordless way to sign in</li>
              <li>• They use your device's biometrics or security key</li>
              <li>• Each passkey is unique to this website</li>
              <li>• You can have multiple passkeys on different devices</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PasskeyManagerEmbedded;