import React, { useState, useEffect, useRef } from 'react';
import { Key, Shield, Loader, AlertCircle, Check, Trash2, Plus, Info } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasskeyManagerFinal = () => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [passkeyName, setPasskeyName] = useState('');
  const [registrationStatus, setRegistrationStatus] = useState('');
  const formRef = useRef(null);
  const checkIntervalRef = useRef(null);

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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      // Clean up any forms we created
      if (formRef.current && document.body.contains(formRef.current)) {
        document.body.removeChild(formRef.current);
      }
    };
  }, []);

  // Intercept form submission to prevent redirect
  useEffect(() => {
    const interceptFormSubmission = (e) => {
      const form = e.target;
      if (form.id === 'webauthn-settings-form') {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('🔐 Intercepted form submission');
        
        // Submit via AJAX instead
        const formData = new FormData(form);
        const data = new URLSearchParams();
        for (const [key, value] of formData.entries()) {
          data.append(key, value.toString());
        }
        
        // Submit the form via fetch
        fetch(form.action, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          body: data
        }).then(response => {
          console.log('🔐 Form submission response:', response.status);
          if (response.ok || response.status === 422) {
            // 422 might mean the flow needs to be refreshed
            setTimeout(() => {
              checkForNewPasskey();
            }, 1000);
          }
        }).catch(err => {
          console.error('Form submission error:', err);
        });
        
        return false;
      }
    };

    // Add global form submit listener
    document.addEventListener('submit', interceptFormSubmission, true);
    
    return () => {
      document.removeEventListener('submit', interceptFormSubmission, true);
    };
  }, []);

  // Check if a new passkey was added
  const checkForNewPasskey = async () => {
    try {
      const sessionResponse = await axios.get('/.ory/sessions/whoami', {
        withCredentials: true,
        headers: { 'Accept': 'application/json' }
      });
      
      const currentIdentity = sessionResponse.data.identity;
      const currentPasskeys = currentIdentity?.credentials?.webauthn || [];
      
      if (currentPasskeys.length > passkeys.length) {
        console.log('✅ New passkey detected!');
        setSuccess('Passkey registered successfully!');
        setPasskeyName('');
        setIsRegistering(false);
        setRegistrationStatus('');
        // Update local state
        const formattedPasskeys = currentPasskeys.map((cred, index) => ({
          id: cred.id || `passkey-${index}`,
          display_name: cred.display_name || `Passkey ${index + 1}`,
          created_at: cred.created_at,
          last_used: cred.updated_at || cred.created_at,
          identifier: cred.identifier
        }));
        setPasskeys(formattedPasskeys);
        
        // Clean up form
        if (formRef.current && document.body.contains(formRef.current)) {
          document.body.removeChild(formRef.current);
          formRef.current = null;
        }
        
        return true;
      }
      return false;
    } catch (err) {
      console.error('Error checking for new passkey:', err);
      return false;
    }
  };

  // Start passkey registration using a more direct approach
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
      // Step 1: Create settings flow
      console.log('🔐 Creating settings flow...');
      setRegistrationStatus('Creating security session...');
      
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      console.log('🔐 Settings flow created:', flow.id);

      // Step 2: Build the form exactly as Kratos expects
      const form = document.createElement('form');
      form.id = 'webauthn-settings-form';
      form.action = flow.ui.action;
      form.method = 'POST';
      form.style.cssText = 'position: absolute; left: -9999px; visibility: hidden;';
      
      // Add all nodes from the flow
      flow.ui.nodes.forEach(node => {
        if (node.type === 'input') {
          const input = document.createElement('input');

          // Null check for input element creation
          if (!input) {
            console.error('❌ Failed to create input element for passkey registration');
            return;
          }

          try {
            input.type = node.attributes?.type || 'text';
            input.name = node.attributes?.name || '';
            input.value = node.attributes?.value || '';

            // Set display name
            if (node.attributes?.name === 'webauthn_register_displayname') {
              input.value = passkeyName || '';
            }

            form.appendChild(input);
          } catch (error) {
            console.error('❌ Error setting input properties for passkey registration:', error);
          }
        }
      });

      // Find the WebAuthn trigger button
      const triggerNode = flow.ui.nodes.find(
        n => n.group === 'webauthn' &&
             n.attributes?.name === 'webauthn_register_trigger' &&
             n.attributes?.type === 'button'
      );

      if (!triggerNode) {
        throw new Error('WebAuthn registration not available. Please ensure your email is verified.');
      }

      // Add the trigger button
      const button = document.createElement('button');

      // Null check for button element creation
      if (!button) {
        console.error('❌ Failed to create button element for passkey registration');
        throw new Error('Failed to create registration button');
      }

      try {
        button.type = 'submit';
        button.name = triggerNode.attributes?.name || '';
        button.value = triggerNode.attributes?.value || '';
      } catch (error) {
        console.error('❌ Error setting button properties for passkey registration:', error);
        throw new Error('Failed to configure registration button');
      }
      button.onclick = (e) => {
        e.preventDefault();
        const webauthnOptions = JSON.parse(triggerNode.attributes.value);
        console.log('🔐 Triggering WebAuthn with options:', webauthnOptions);
        
        if (window.oryWebAuthnRegistration) {
          window.oryWebAuthnRegistration(webauthnOptions);
        } else if (triggerNode.attributes.onclick) {
          // Fallback: execute the onclick directly
          eval(triggerNode.attributes.onclick);
        }
      };
      form.appendChild(button);

      // Append form to body
      document.body.appendChild(form);
      formRef.current = form;

      // Step 3: Load WebAuthn script if needed
      if (!window.oryWebAuthnRegistration) {
        console.log('⏳ Loading WebAuthn script...');
        setRegistrationStatus('Loading security components...');
        
        const scriptNode = flow.ui.nodes.find(n => n.type === 'script' && n.group === 'webauthn');
        if (scriptNode?.attributes?.src) {
          await loadScript(scriptNode.attributes.src);
        }
      }

      // Step 4: Trigger the registration
      setRegistrationStatus('Please complete the security prompt in your browser...');
      console.log('🔐 Clicking WebAuthn trigger button...');
      
      // Start monitoring for completion
      let attempts = 0;
      checkIntervalRef.current = setInterval(async () => {
        attempts++;
        
        const found = await checkForNewPasskey();
        if (found) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        } else if (attempts >= 120) { // 2 minutes
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
          setError('Passkey registration timed out. Please try again.');
          setIsRegistering(false);
          setRegistrationStatus('');
          if (formRef.current && document.body.contains(formRef.current)) {
            document.body.removeChild(formRef.current);
            formRef.current = null;
          }
        }
      }, 1000);

      // Click the button to start WebAuthn
      button.click();

    } catch (err) {
      console.error('Registration error:', err);
      setError(err.message || 'Failed to register passkey');
      setIsRegistering(false);
      setRegistrationStatus('');
      
      // Clean up
      if (formRef.current && document.body.contains(formRef.current)) {
        document.body.removeChild(formRef.current);
        formRef.current = null;
      }
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
    }
  };

  // Helper to load a script
  const loadScript = (src) => {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }
      
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

      // Update local state
      setPasskeys(prev => prev.filter(p => p.id !== passkeyId));
      setSuccess('Passkey removed successfully');
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

          {/* Troubleshooting */}
          {isRegistering && (
            <div className="mt-4 p-4 bg-amber-900/20 border border-amber-700/50 rounded-lg">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-300">
                  <p className="font-semibold mb-1">Don't see the prompt?</p>
                  <ul className="space-y-1 list-disc list-inside text-xs">
                    <li>Check if your browser blocked the popup</li>
                    <li>Make sure you're not in incognito/private mode</li>
                    <li>Try refreshing the page and starting again</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

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

export default PasskeyManagerFinal;