import React, { useState, useEffect } from 'react';
import { Key, Shield, Loader, AlertCircle, Check, Trash2, Plus } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasskeyManagerFixed = () => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [passkeyName, setPasskeyName] = useState('');
  const [currentFlow, setCurrentFlow] = useState(null);
  const [webauthnScript, setWebauthnScript] = useState(null);

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

  // Execute WebAuthn script when it's available
  useEffect(() => {
    if (webauthnScript && currentFlow) {
      console.log('🔐 Executing WebAuthn script');
      
      // Create a container for the flow UI
      const container = document.createElement('div');
      container.style.display = 'none';
      document.body.appendChild(container);
      
      // Build the form with all nodes
      const form = document.createElement('form');
      form.action = currentFlow.ui.action;
      form.method = currentFlow.ui.method || 'POST';
      
      // Add all nodes to the form
      currentFlow.ui.nodes.forEach(node => {
        if (node.type === 'input') {
          const input = document.createElement('input');

          // Null check for input element creation
          if (!input) {
            console.error('❌ Failed to create input element for passkey registration');
            return;
          }

          try {
            input.type = node.attributes?.type || 'hidden';
            input.name = node.attributes?.name || '';
            input.value = node.attributes?.value || '';
            if (node.attributes?.required) input.required = true;
            form.appendChild(input);
          } catch (error) {
            console.error('❌ Error setting input properties for passkey registration:', error);
          }
        } else if (node.type === 'script') {
          // Skip script nodes - we'll execute them separately
        }
      });
      
      container.appendChild(form);
      
      // Execute the WebAuthn script
      try {
        // The script should be the actual JavaScript code
        const script = document.createElement('script');
        script.textContent = webauthnScript;
        document.body.appendChild(script);
        
        // Clean up
        setTimeout(() => {
          if (document.body.contains(script)) {
            document.body.removeChild(script);
          }
          if (document.body.contains(container)) {
            document.body.removeChild(container);
          }
        }, 100);
        
        // Monitor for completion
        const checkInterval = setInterval(async () => {
          try {
            await checkSession();
            clearInterval(checkInterval);
            setSuccess('Passkey registered successfully!');
            setPasskeyName('');
            setIsRegistering(false);
            setWebauthnScript(null);
            setCurrentFlow(null);
          } catch (err) {
            // Still registering
          }
        }, 1000);
        
        // Clear interval after 30 seconds
        setTimeout(() => {
          clearInterval(checkInterval);
          if (isRegistering) {
            setError('Registration timeout. Please try again.');
            setIsRegistering(false);
            setWebauthnScript(null);
            setCurrentFlow(null);
          }
        }, 30000);
        
      } catch (err) {
        console.error('Error executing WebAuthn script:', err);
        setError('Failed to execute WebAuthn registration');
        setIsRegistering(false);
        setWebauthnScript(null);
        setCurrentFlow(null);
      }
    }
  }, [webauthnScript, currentFlow, checkSession, isRegistering]);

  // Start passkey registration
  const startRegistration = async () => {
    if (!passkeyName.trim()) {
      setError('Please enter a name for your passkey');
      return;
    }

    setError('');
    setSuccess('');
    setIsRegistering(true);

    try {
      // Step 1: Create settings flow
      console.log('🔐 Creating settings flow...');
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      console.log('🔐 Settings flow created:', flow.id);

      // Step 2: Check if WebAuthn is available in the flow
      const webauthnGroup = flow.ui.nodes.filter(n => n.group === 'webauthn');
      if (webauthnGroup.length === 0) {
        throw new Error('WebAuthn is not available. Please ensure email is verified.');
      }

      // Step 3: Prepare the form data
      const formData = new URLSearchParams();
      
      // Add CSRF token
      const csrfNode = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token');
      if (csrfNode) {
        formData.append('csrf_token', csrfNode.attributes.value);
      }

      // Add display name
      const displayNameNode = flow.ui.nodes.find(
        n => n.group === 'webauthn' && n.attributes?.name === 'webauthn_register_displayname'
      );
      if (displayNameNode) {
        formData.append('webauthn_register_displayname', passkeyName);
      }

      // Find and add the trigger
      const triggerNode = flow.ui.nodes.find(
        n => n.group === 'webauthn' && 
        n.attributes?.name === 'webauthn_register_trigger' &&
        n.type === 'input' &&
        n.attributes?.type === 'button'  // It's a button, not submit!
      );

      if (!triggerNode) {
        console.error('❌ No WebAuthn trigger found. Available WebAuthn nodes:', webauthnGroup);
        throw new Error('WebAuthn registration trigger not found');
      }

      console.log('🔐 Found trigger node:', triggerNode.attributes);
      formData.append(triggerNode.attributes.name, triggerNode.attributes.value || '');

      // Step 4: Submit the form to trigger WebAuthn
      console.log('🔐 Submitting WebAuthn registration...');
      const registerResponse = await axios.post(flow.ui.action, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true,
        validateStatus: (status) => status < 500 // Don't reject 4xx responses
      });

      console.log('🔐 Registration response status:', registerResponse.status);
      console.log('🔐 Registration response data:', registerResponse.data);

      // Step 5: Handle the response
      if (registerResponse.data.ui) {
        const responseFlow = registerResponse.data;
        
        // Look for WebAuthn script node
        const scriptNode = responseFlow.ui.nodes.find(
          n => n.type === 'script' && n.group === 'webauthn'
        );

        if (scriptNode) {
          console.log('🔐 WebAuthn script node found');
          setCurrentFlow(responseFlow);
          
          // Check if it's an inline script or external script
          if (scriptNode.attributes?.src) {
            // External script - load it
            console.log('🔐 Loading external WebAuthn script:', scriptNode.attributes.src);
            const script = document.createElement('script');
            script.src = scriptNode.attributes.src;
            script.async = true;
            script.onload = () => {
              console.log('🔐 External WebAuthn script loaded');
            };
            script.onerror = () => {
              console.error('🔐 Failed to load external WebAuthn script');
              setError('Failed to load WebAuthn script');
              setIsRegistering(false);
            };
            document.body.appendChild(script);
          } else if (scriptNode.attributes?.integrity) {
            // Script with content - execute it
            console.log('🔐 Found inline WebAuthn script');
            setWebauthnScript(scriptNode.attributes.integrity);
          } else {
            // Try to find script content in node
            console.log('🔐 Script node structure:', scriptNode);
            // Some versions of Kratos might put the script differently
            if (scriptNode.attributes?.async === false && scriptNode.attributes?.crossorigin === 'anonymous') {
              // This might be a reference to load the Ory WebAuthn script
              console.log('🔐 Loading Ory WebAuthn helper');
              
              // The script should already be loaded from /.ory/.well-known/ory/webauthn.js
              // Just wait for the ceremony to complete
              setTimeout(async () => {
                await checkSession();
                setSuccess('Passkey registered successfully!');
                setPasskeyName('');
                setIsRegistering(false);
              }, 5000);
            }
          }
        } else {
          // Check for error messages
          const errorMessages = responseFlow.ui.messages?.filter(m => m.type === 'error') || [];
          if (errorMessages.length > 0) {
            throw new Error(errorMessages.map(m => m.text).join('. '));
          }
          
          console.error('❌ No WebAuthn script in response');
          throw new Error('WebAuthn registration not properly initialized');
        }
      }
    } catch (err) {
      console.error('Registration error:', err);
      
      // Extract error message
      let errorMessage = 'Failed to register passkey';
      if (err.response?.data?.ui?.messages) {
        errorMessage = err.response.data.ui.messages
          .filter(m => m.type === 'error')
          .map(m => m.text)
          .join('. ');
      } else if (err.response?.data?.error?.message) {
        errorMessage = err.response.data.error.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      setIsRegistering(false);
    }
  };

  // Remove passkey
  const removePasskey = async (passkeyId) => {
    if (!window.confirm('Are you sure you want to remove this passkey?')) {
      return;
    }

    setError('');
    setSuccess('');

    try {
      // Create settings flow and remove passkey
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
              </div>
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

export default PasskeyManagerFixed;