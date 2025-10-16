import React, { useState, useEffect, useRef } from 'react';
import { Key, Shield, Loader, AlertCircle, Check, Trash2, Plus } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasskeyManagerImproved = () => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [passkeyName, setPasskeyName] = useState('');
  const [registrationStatus, setRegistrationStatus] = useState('');
  const checkIntervalRef = useRef(null);
  const timeoutRef = useRef(null);

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
            last_used: cred.updated_at || cred.created_at,
            identifier: cred.identifier
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

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Monitor for WebAuthn completion
  const monitorWebAuthnCompletion = async (initialPasskeyCount) => {
    console.log('🔍 Monitoring WebAuthn completion...');
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds total
    
    checkIntervalRef.current = setInterval(async () => {
      attempts++;
      
      try {
        // Check if a new passkey was added
        const sessionResponse = await axios.get('/.ory/sessions/whoami', {
          withCredentials: true,
          headers: { 'Accept': 'application/json' }
        });
        
        const currentIdentity = sessionResponse.data.identity;
        const currentPasskeys = currentIdentity?.credentials?.webauthn || [];
        
        if (currentPasskeys.length > initialPasskeyCount) {
          console.log('✅ New passkey detected!');
          clearInterval(checkIntervalRef.current);
          setSuccess('Passkey registered successfully!');
          setPasskeyName('');
          setIsRegistering(false);
          setRegistrationStatus('');
          // Reload to show new passkey
          window.location.reload();
          return;
        }
      } catch (err) {
        console.error('Error checking session:', err);
      }
      
      if (attempts >= maxAttempts) {
        clearInterval(checkIntervalRef.current);
        setError('Passkey registration timed out. Please try again.');
        setIsRegistering(false);
        setRegistrationStatus('');
      }
    }, 1000); // Check every second
  };

  // Start passkey registration using the Kratos flow
  const startRegistration = async () => {
    if (!passkeyName.trim()) {
      setError('Please enter a name for your passkey');
      return;
    }

    setError('');
    setSuccess('');
    setIsRegistering(true);
    setRegistrationStatus('Initializing...');

    try {
      // Get current passkey count
      const currentPasskeyCount = passkeys.length;

      // Step 1: Create settings flow
      console.log('🔐 Creating settings flow...');
      setRegistrationStatus('Creating security session...');
      
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      console.log('🔐 Settings flow created:', flow.id);

      // Step 2: Find the WebAuthn nodes
      const webauthnNodes = flow.ui.nodes.filter(n => n.group === 'webauthn');
      console.log('🔐 Found', webauthnNodes.length, 'WebAuthn nodes');

      // Find the trigger button
      const triggerNode = webauthnNodes.find(
        n => n.attributes?.name === 'webauthn_register_trigger' && 
             n.attributes?.type === 'button'
      );

      if (!triggerNode) {
        throw new Error('WebAuthn registration button not found. Please ensure your email is verified.');
      }

      // The trigger node contains the WebAuthn options in its value
      const webauthnOptions = JSON.parse(triggerNode.attributes.value);
      console.log('🔐 WebAuthn options:', webauthnOptions);

      // Step 3: Execute WebAuthn registration
      setRegistrationStatus('Waiting for browser security prompt...');
      
      // Make sure the WebAuthn script is loaded
      if (!window.oryWebAuthnRegistration) {
        console.log('⏳ Loading WebAuthn script...');
        setRegistrationStatus('Loading security components...');
        
        // Load the script if not already loaded
        const scriptSrc = webauthnNodes.find(n => n.type === 'script')?.attributes?.src;
        if (scriptSrc) {
          await loadScript(scriptSrc);
        }
      }

      // Create a form that Kratos expects
      const form = document.createElement('form');
      form.id = 'webauthn-registration-form';
      form.style.display = 'none';
      form.action = flow.ui.action;
      form.method = flow.ui.method || 'POST';
      
      // Add all the form nodes
      flow.ui.nodes.forEach(node => {
        if (node.type === 'input') {
          const input = document.createElement('input');

          // Null check for input element creation
          if (!input) {
            console.error('❌ Failed to create input element for passkey registration');
            return;
          }

          // Safely set attributes with null checks
          try {
            input.type = node.attributes?.type || 'hidden';
            input.name = node.attributes?.name || '';
            input.id = node.attributes?.name || '';

            if (node.attributes?.name === 'webauthn_register_displayname') {
              input.value = passkeyName || '';
            } else {
              input.value = node.attributes?.value || '';
            }

            form.appendChild(input);
          } catch (error) {
            console.error('❌ Error setting input properties for passkey registration:', error);
          }
        }
      });

      document.body.appendChild(form);

      // Override form submission to intercept the response
      const originalSubmit = form.submit;
      form.submit = function() {
        console.log('🔐 Form is being submitted...');
        originalSubmit.call(this);
      };

      // Call the WebAuthn registration function
      if (window.oryWebAuthnRegistration) {
        console.log('🔐 Triggering WebAuthn registration...');
        setRegistrationStatus('Please complete the security prompt in your browser...');
        
        // Start monitoring for completion
        monitorWebAuthnCompletion(currentPasskeyCount);
        
        // Trigger the WebAuthn ceremony
        window.oryWebAuthnRegistration(webauthnOptions);
        
        // Set a timeout for the entire process (2 minutes to match WebAuthn timeout)
        timeoutRef.current = setTimeout(() => {
          if (checkIntervalRef.current) {
            clearInterval(checkIntervalRef.current);
          }
          document.body.removeChild(form);
          setError('Passkey registration timed out. Please try again.');
          setIsRegistering(false);
          setRegistrationStatus('');
        }, 120000); // 2 minutes
        
      } else {
        throw new Error('WebAuthn script not loaded');
      }

    } catch (err) {
      console.error('Registration error:', err);
      setError(err.message || 'Failed to register passkey');
      setIsRegistering(false);
      setRegistrationStatus('');
    }
  };

  // Helper to load a script
  const loadScript = (src) => {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  };

  // Remove passkey
  const removePasskey = async (passkeyId) => {
    if (!window.confirm('Are you sure you want to remove this passkey?')) {
      return;
    }

    setError('');
    setSuccess('');

    try {
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      const csrfToken = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;

      // Find the remove button for this specific passkey
      const removeNode = flow.ui.nodes.find(
        n => n.group === 'webauthn' && 
        n.attributes?.name === 'webauthn_remove' &&
        n.attributes?.value === passkeyId
      );

      if (!removeNode) {
        throw new Error('Cannot find remove button for this passkey');
      }

      const formData = new URLSearchParams();
      formData.append('csrf_token', csrfToken);
      formData.append(removeNode.attributes.name, removeNode.attributes.value);

      await axios.post(flow.ui.action, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true
      });

      await checkSession();
      setSuccess('Passkey removed successfully');
      window.location.reload();
    } catch (err) {
      console.error('Remove error:', err);
      setError('Failed to remove passkey');
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

          {success && (
            <div className="mb-6 p-4 glass-subtle border border-green-500/30 rounded-lg flex items-center gap-3">
              <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
              <span className="text-green-300">{success}</span>
            </div>
          )}

          {/* Registration Status */}
          {registrationStatus && (
            <div className="mb-6 p-4 glass-subtle border border-blue-500/30 rounded-lg flex items-center gap-3">
              <Loader className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
              <span className="text-blue-300">{registrationStatus}</span>
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
                      <button
                        onClick={() => removePasskey(passkey.id)}
                        className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Remove passkey"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
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
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-2 text-sm font-medium">
                    Passkey Name
                  </label>
                  <input
                    type="text"
                    value={passkeyName}
                    onChange={(e) => setPasskeyName(e.target.value)}
                    placeholder="e.g., MacBook Pro, iPhone, YubiKey"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                    disabled={isRegistering}
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Give your passkey a name to identify it later
                  </p>
                </div>

                <button
                  onClick={startRegistration}
                  disabled={isRegistering || !window.PublicKeyCredential}
                  className="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRegistering ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      <span>Registering...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-5 h-5" />
                      <span>Register New Passkey</span>
                    </>
                  )}
                </button>

                {isRegistering && (
                  <p className="text-xs text-gray-400 text-center">
                    Complete the security prompt in your browser. This may take up to 2 minutes.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Alternative Option */}
          <div className="mt-6 p-4 bg-slate-700/30 rounded-lg">
            <p className="text-sm text-gray-400 mb-2">Having trouble? You can also:</p>
            <button
              onClick={() => window.open('/.ory/self-service/settings/browser', '_blank')}
              className="text-yellow-400 hover:text-yellow-300 text-sm underline"
            >
              Use Kratos Settings UI directly
            </button>
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

export default PasskeyManagerImproved;