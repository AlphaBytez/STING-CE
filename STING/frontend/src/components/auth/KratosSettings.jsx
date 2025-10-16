import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { Loader, AlertCircle, Shield, Key, Mail, User, ArrowLeft } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const KratosSettings = () => {
  const { themeColors } = useTheme();
  const { identity } = useKratos();
  
  // Use proper background color from theme
  const backgroundColor = themeColors.mainBg ? `${themeColors.mainBg.replace('bg-', '')}` : 'slate-800';
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [flow, setFlow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);

  const flowId = searchParams.get('flow');

  // Load WebAuthn script
  useEffect(() => {
    if (!scriptLoaded) {
      const script = document.createElement('script');
      script.src = `/.ory/.well-known/ory/webauthn.js`;
      script.async = true;
      script.onload = () => {
        console.log('🔐 Kratos WebAuthn script loaded');
        setScriptLoaded(true);

        // Add global error handler to suppress non-critical webauthn.js DOM errors
        window.addEventListener('error', (event) => {
          if (event.message && event.message.includes('Cannot set properties of null')) {
            console.warn('⚠️ Caught webauthn.js DOM error (non-critical):', event.message);
            event.preventDefault(); // Prevent the error from showing to the user
            return true;
          }
        }, { once: false });
      };
      script.onerror = () => {
        console.error('🔐 Failed to load Kratos WebAuthn script');
      };
      document.head.appendChild(script);
      
      return () => {
        if (document.head.contains(script)) {
          document.head.removeChild(script);
        }
      };
    }
  }, [scriptLoaded]);

  useEffect(() => {
    console.log('🔐 KratosSettings mounted, flowId:', flowId);
    initializeFlow();
  }, [flowId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Load WebAuthn script if flow contains WebAuthn nodes
    if (flow && flow.ui.nodes.some(n => n.type === 'script' || n.group === 'webauthn')) {
      // First load the WebAuthn library
      const script = document.createElement('script');
      script.src = `/.ory/.well-known/ory/webauthn.js`;
      script.crossOrigin = 'anonymous';
      script.async = true;
      
      script.onload = () => {
        console.log('WebAuthn script loaded');

        // Add global error handler to suppress non-critical webauthn.js DOM errors
        window.addEventListener('error', (event) => {
          if (event.message && event.message.includes('Cannot set properties of null')) {
            console.warn('⚠️ Caught webauthn.js DOM error (non-critical):', event.message);
            event.preventDefault(); // Prevent the error from showing to the user
            return true;
          }
        }, { once: false });

        // Then execute any script nodes from the flow
        flow.ui.nodes
          .filter(n => n.type === 'script')
          .forEach(scriptNode => {
            if (scriptNode.attributes?.src) {
              const flowScript = document.createElement('script');
              flowScript.src = scriptNode.attributes.src;
              flowScript.async = scriptNode.attributes.async;
              flowScript.crossOrigin = scriptNode.attributes.crossorigin;
              flowScript.referrerPolicy = scriptNode.attributes.referrerpolicy;
              flowScript.type = scriptNode.attributes.type || 'text/javascript';
              document.body.appendChild(flowScript);
            }
          });
      };
      
      document.head.appendChild(script);

      return () => {
        document.head.removeChild(script);
      };
    }
  }, [flow]);

  const initializeFlow = async () => {
    try {
      setLoading(true);
      setError('');

      let flowData;
      
      if (flowId) {
        console.log('🔐 Fetching existing flow:', flowId);
        // Fetch existing flow using the proxy endpoint
        const response = await fetch(`/.ory/self-service/settings/flows?id=${flowId}`, {
          credentials: 'include',
          headers: {
            'Accept': 'application/json'
          }
        });

        console.log('🔐 Flow fetch response:', response.status);

        if (!response.ok) {
          if (response.status === 410) {
            console.log('🔐 Flow expired, creating new one');
            // Flow expired, create new one using proxy endpoint
            window.location.href = `/.ory/self-service/settings/browser`;
            return;
          }
          throw new Error('Failed to fetch settings flow');
        }

        flowData = await response.json();
        console.log('🔐 Flow data received:', flowData);
        console.log('🔐 Flow data type:', typeof flowData);
        console.log('🔐 Flow has ui property:', !!flowData.ui);
        console.log('🔐 Flow has nodes:', flowData.ui?.nodes?.length);
      } else {
        console.log('🔐 No flow ID, redirecting to create one');
        // No flow ID, redirect to create one using proxy endpoint
        window.location.href = `/.ory/self-service/settings/browser`;
        return;
      }

      if (flowData && flowData.ui) {
        setFlow(flowData);
        console.log('🔐 Flow state set successfully');
        console.log('🔐 WebAuthn nodes:', flowData.ui.nodes.filter(n => n.group === 'webauthn').length);
      } else {
        console.error('🔐 Invalid flow data structure:', flowData);
        setError('Invalid settings data received');
      }
    } catch (err) {
      console.error('🔐 Error initializing settings flow:', err);
      console.error('🔐 Error details:', err.message, err.stack);
      setError('Failed to load settings. Please try again.');
      setFlow(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (node) => {
    try {
      setSubmitting(true);
      setError('');
      setSuccess('');

      // Prepare form data
      const formData = new URLSearchParams();
      
      // Add all form fields
      flow.ui.nodes.forEach(n => {
        if (n.attributes.name && n.attributes.value !== undefined) {
          formData.append(n.attributes.name, n.attributes.value);
        }
      });

      // Add the clicked button value
      if (node.attributes.name && node.attributes.value) {
        formData.append(node.attributes.name, node.attributes.value);
      }

      const response = await fetch(flow.ui.action, {
        method: flow.ui.method,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.ui?.messages) {
          setError(data.ui.messages.map(m => m.text).join(' '));
        } else {
          setError('Failed to update settings');
        }
        return;
      }

      // Check for success messages
      if (data.ui?.messages?.some(m => m.type === 'success')) {
        setSuccess(data.ui.messages.find(m => m.type === 'success').text);
      }

      // Update flow with new data
      setFlow(data);
    } catch (err) {
      console.error('Error submitting settings:', err);
      setError('Failed to update settings. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderWebAuthnSection = () => {
    const webauthnNodes = flow.ui.nodes.filter(node => 
      node.group === 'webauthn' || 
      node.attributes.name?.includes('webauthn')
    );

    // Always show WebAuthn section with registration button
    if (webauthnNodes.length === 0) {
      return (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Key className="w-6 h-6 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Passkey Management</h3>
          </div>
          
          <div className="p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg mb-4">
            <p className="text-blue-300 mb-2">WebAuthn/Passkeys are enabled in Kratos.</p>
            <p className="text-gray-300 text-sm">To register a passkey, you need to trigger the WebAuthn registration flow.</p>
          </div>

          <button
            onClick={() => {
              // Trigger WebAuthn registration by updating a trait
              const form = document.createElement('form');
              if (!form) {
                console.error('❌ Failed to create form element for WebAuthn registration');
                return;
              }

              try {
                form.method = 'POST';
                form.action = flow.ui.action;
              } catch (error) {
                console.error('❌ Error setting form properties:', error);
                return;
              }
              
              // Add CSRF token
              const csrfNode = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token');
              if (csrfNode) {
                const csrfInput = document.createElement('input');
                if (csrfInput) {
                  try {
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrf_token';
                    csrfInput.value = csrfNode.attributes?.value || '';
                    form.appendChild(csrfInput);
                  } catch (error) {
                    console.error('❌ Error setting CSRF input properties:', error);
                  }
                }
              }

              // Add method to trigger WebAuthn
              const methodInput = document.createElement('input');
              if (methodInput) {
                try {
                  methodInput.type = 'hidden';
                  methodInput.name = 'method';
                  methodInput.value = 'webauthn';
                  form.appendChild(methodInput);
                } catch (error) {
                  console.error('❌ Error setting method input properties:', error);
                }
              }

              try {
                if (document.body && form) {
                  document.body.appendChild(form);
                  form.submit();
                } else {
                  console.error('❌ Cannot append form: document.body or form is null');
                }
              } catch (error) {
                console.error('❌ Error submitting WebAuthn form:', error);
              }
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200"
          >
            Register New Passkey
          </button>

          {/* Debug info */}
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300">Debug: View Flow Nodes</summary>
            <pre className="mt-2 p-2 bg-gray-800 rounded text-xs text-gray-300 overflow-auto">
              {JSON.stringify(flow.ui.nodes.map(n => ({
                type: n.type,
                group: n.group,
                name: n.attributes?.name,
                node_type: n.attributes?.node_type
              })), null, 2)}
            </pre>
          </details>
        </div>
      );
    }

    return (
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Key className="w-6 h-6 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Passkey Management</h3>
        </div>
        
        <div className="space-y-4">
          {webauthnNodes.map((node, index) => {
            if (node.type === 'script') {
              return (
                <div key={index} dangerouslySetInnerHTML={{ __html: node.attributes.src }} />
              );
            }

            if (node.type === 'input' && node.attributes.type === 'submit') {
              return (
                <button
                  key={index}
                  type="button"
                  onClick={() => handleSubmit(node)}
                  disabled={submitting}
                  className="floating-button px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-200"
                >
                  {submitting ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Key className="w-4 h-4" />
                  )}
                  {node.meta?.label?.text || 'Add Passkey'}
                </button>
              );
            }

            if (node.type === 'input' && node.attributes.type === 'hidden') {
              return null; // Hidden inputs are handled in form submission
            }

            return null;
          })}
        </div>

        {/* Show existing passkeys */}
        {identity?.credentials?.webauthn?.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-gray-400">Registered Passkeys:</p>
            {identity.credentials.webauthn.map((cred, index) => (
              <div key={index} className="p-3 bg-slate-700/50 border border-slate-600 rounded-lg hover:bg-slate-700/70 transition-all duration-200">
                <p className="text-white">{cred.display_name || `Passkey ${index + 1}`}</p>
                <p className="text-xs text-gray-400">
                  Added: {new Date(cred.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderProfileSection = () => {
    const profileNodes = flow.ui.nodes.filter(node => 
      node.group === 'profile' || 
      node.group === 'default'
    );

    if (profileNodes.length === 0) return null;

    return (
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <User className="w-6 h-6 text-green-400" />
          <h3 className="text-lg font-semibold text-white">Profile Settings</h3>
        </div>
        
        <div className="space-y-4">
          {profileNodes.map((node, index) => {
            if (node.type === 'input' && node.attributes.type !== 'submit' && node.attributes.type !== 'hidden') {
              return (
                <div key={index}>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    {node.meta?.label?.text || node.attributes.name}
                  </label>
                  <input
                    type={node.attributes.type}
                    name={node.attributes.name}
                    defaultValue={node.attributes.value}
                    disabled={node.attributes.disabled}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 transition-all duration-200"
                    onChange={(e) => {
                      // Update node value for form submission with null check
                      if (node.attributes) {
                        try {
                          node.attributes.value = e.target.value;
                        } catch (error) {
                          console.error('❌ Error updating node attributes value:', error);
                        }
                      }
                    }}
                  />
                </div>
              );
            }
            return null;
          })}
        </div>
      </div>
    );
  };

  const renderPasswordSection = () => {
    const passwordNodes = flow.ui.nodes.filter(node => 
      node.group === 'password'
    );

    if (passwordNodes.length === 0) return null;

    return (
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-6 h-6 text-yellow-400" />
          <h3 className="text-lg font-semibold text-white">Password Settings</h3>
        </div>
        
        <p className="text-sm text-gray-400 mb-4">
          To change your password, please use the account recovery flow.
        </p>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${themeColors.mainBg || 'bg-slate-800'}`}>
        <Loader className="w-8 h-8 animate-spin text-yellow-400" />
      </div>
    );
  }

  if (!flow) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${themeColors.mainBg || 'bg-slate-800'}`}>
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-white mb-4">Failed to load settings</p>
          {error && (
            <p className="text-red-300 text-sm mb-4">{error}</p>
          )}
          <div className="space-y-2">
            <button
              onClick={() => window.location.reload()}
              className="floating-button px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-all duration-200 w-full"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="floating-button px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg transition-all duration-200 w-full"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render WebAuthn registration form
  const renderWebAuthnRegistrationForm = () => {
    if (!flow) return null;
    
    // Find WebAuthn nodes
    const webauthnNodes = flow.ui.nodes.filter(n => 
      n.group === 'webauthn' || 
      n.attributes?.name?.includes('webauthn')
    );
    
    if (webauthnNodes.length === 0) {
      return (
        <div className="p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
          <p className="text-yellow-300">WebAuthn is not available in the current flow.</p>
        </div>
      );
    }
    
    // Check if we have the trigger node
    const triggerNode = flow.ui.nodes.find(n => 
      n.attributes?.name === 'webauthn_register_trigger'
    );
    
    return (
      <div className="space-y-4">
        <form 
          id="webauthn-registration-form"
          action={flow.ui.action} 
          method="POST"
          className="space-y-4"
        >
          {/* Render all nodes from Kratos */}
          {flow.ui.nodes.map((node, idx) => {
            // Hidden inputs
            if (node.type === 'input' && node.attributes.type === 'hidden') {
              return (
                <input
                  key={idx}
                  type="hidden"
                  name={node.attributes.name}
                  value={node.attributes.value || ''}
                />
              );
            }
            
            // Display name input
            if (node.attributes?.name === 'webauthn_register_displayname') {
              return (
                <div key={idx}>
                  <label className="block text-gray-300 mb-2 text-sm font-medium">
                    Passkey Name
                  </label>
                  <input
                    type="text"
                    name={node.attributes.name}
                    placeholder="e.g., MacBook Pro, iPhone, YubiKey"
                    defaultValue="My Passkey"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Give your passkey a name to identify it later
                  </p>
                </div>
              );
            }
            
            // Register trigger button
            if (node.attributes?.name === 'webauthn_register_trigger') {
              // Check if we have WebAuthn options
              const hasOptions = node.attributes.value && node.attributes.value !== '';
              
              return (
                <button
                  key={idx}
                  type="submit"
                  name={node.attributes.name}
                  value={node.attributes.value || ''}
                  onClick={(e) => {
                    console.log('🔐 WebAuthn register button clicked');
                    console.log('Button value:', node.attributes.value);
                    console.log('Has options:', hasOptions);
                    // Let the form submit naturally
                  }}
                  className="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
                >
                  <Key className="w-5 h-5" />
                  <span>Register New Passkey</span>
                </button>
              );
            }
            
            // WebAuthn register input (hidden, filled by script)
            if (node.attributes?.name === 'webauthn_register') {
              return (
                <input
                  key={idx}
                  type="hidden"
                  name={node.attributes.name}
                  value=""
                />
              );
            }
            
            // Script nodes
            if (node.type === 'script') {
              console.log('🔐 Script node found:', node);
              // Render the script node to ensure it executes
              if (node.attributes?.src) {
                return (
                  <script
                    key={idx}
                    src={node.attributes.src}
                    async={node.attributes.async}
                    crossOrigin={node.attributes.crossorigin}
                    referrerPolicy={node.attributes.referrerpolicy}
                    type={node.attributes.type || 'text/javascript'}
                  />
                );
              } else if (node.attributes?.id === 'webauthn_script') {
                // Inline script content
                return (
                  <div
                    key={idx}
                    dangerouslySetInnerHTML={{
                      __html: `<script>${node.attributes.innerHTML || ''}</script>`
                    }}
                  />
                );
              }
              return null;
            }
            
            return null;
          })}
          
          {/* Method field */}
          <input type="hidden" name="method" value="webauthn" />
        </form>
        
        {/* Debug: Show script nodes */}
        {flow.ui.nodes.filter(n => n.type === 'script').length > 0 && (
          <div className="mt-4 p-3 bg-gray-800 rounded text-xs">
            <p className="text-gray-400 mb-2">WebAuthn Scripts Detected:</p>
            {flow.ui.nodes
              .filter(n => n.type === 'script')
              .map((node, idx) => (
                <div key={idx} className="text-gray-500">
                  Script {idx + 1}: {node.attributes.src || 'inline script'}
                </div>
              ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`min-h-screen p-4 ${themeColors.mainBg || 'bg-slate-800'}`}>
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8 glass-subtle p-6 rounded-xl backdrop-blur-sm">
          <button
            onClick={() => navigate('/dashboard/user')}
            className="flex items-center gap-2 text-gray-400 hover:text-white mb-4 transition-colors duration-200"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>
          
          <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
          <p className="text-gray-300">Manage your account security and preferences</p>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 p-4 glass-subtle border border-red-500/30 rounded-lg flex items-center gap-3 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 glass-subtle border border-green-500/30 rounded-lg flex items-center gap-3 backdrop-blur-sm">
            <Shield className="w-5 h-5 text-green-400" />
            <span className="text-green-300">{success}</span>
          </div>
        )}

        {/* Settings Sections */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="p-8">
            {/* WebAuthn/Passkey Section */}
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-4">
                <Key className="w-6 h-6 text-blue-400" />
                <h3 className="text-lg font-semibold text-white">Passkey Management</h3>
              </div>
              
              {/* Show existing passkeys from flow data */}
              {flow && (() => {
                // Find existing WebAuthn credentials in the flow
                const webauthnNodes = flow.ui.nodes.filter(n => 
                  n.group === 'webauthn' && 
                  n.attributes?.name === 'webauthn_remove'
                );
                
                console.log('🔐 WebAuthn remove nodes found:', webauthnNodes.length);
                
                if (webauthnNodes.length > 0) {
                  return (
                    <div className="mb-6 space-y-2">
                      <p className="text-sm text-gray-400">Your Registered Passkeys:</p>
                      {webauthnNodes.map((node, index) => {
                        // Extract passkey info from node meta
                        const displayName = node.meta?.label?.text || `Passkey ${index + 1}`;
                        const credentialId = node.attributes?.value;
                        
                        return (
                          <div key={credentialId || index} className="p-3 bg-slate-700/50 border border-slate-600 rounded-lg hover:bg-slate-700/70 transition-all duration-200">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-white font-medium">{displayName}</p>
                                <p className="text-xs text-gray-400">
                                  Credential ID: {typeof credentialId === 'string' ? credentialId.substring(0, 20) + '...' : 'N/A'}
                                </p>
                              </div>
                              <Key className="w-5 h-5 text-yellow-400" />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                }
                
                // Also check for a success message that a passkey was just added
                const hasSuccessMessage = flow.ui.messages?.some(m => 
                  m.type === 'success' && m.text?.includes('successfully')
                );
                
                if (hasSuccessMessage) {
                  return (
                    <div className="mb-6 p-3 bg-green-900/30 border border-green-700 rounded-lg">
                      <p className="text-green-300 text-sm">✓ Passkey registered successfully! Refresh to see it.</p>
                    </div>
                  );
                }
                
                return null;
              })()}
              
              <div className="p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg mb-4">
                <p className="text-blue-300 mb-2">Add a new passkey to your account</p>
                <p className="text-gray-300 text-sm">Use your fingerprint, face, or security key for quick and secure sign-in.</p>
              </div>

              {/* Render Kratos WebAuthn form */}
              {flow && renderWebAuthnRegistrationForm()}

              {/* Debug info */}
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300">Debug: View Flow Data</summary>
                <div className="mt-2 space-y-2">
                  <div className="p-2 bg-gray-800 rounded">
                    <p className="text-xs text-gray-400 mb-1">Flow State: {flow?.state}</p>
                    <p className="text-xs text-gray-400 mb-1">Flow ID: {flow?.id}</p>
                    <p className="text-xs text-gray-400 mb-1">Messages: {flow?.ui?.messages?.length || 0}</p>
                  </div>
                  <details>
                    <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-300">WebAuthn Nodes</summary>
                    <pre className="mt-1 p-2 bg-gray-800 rounded text-xs text-gray-300 overflow-auto">
                      {flow && JSON.stringify(flow.ui.nodes.filter(n => n.group === 'webauthn').map(n => ({
                        type: n.type,
                        name: n.attributes?.name,
                        node_type: n.attributes?.node_type,
                        value: typeof n.attributes?.value === 'string' ? n.attributes.value.substring(0, 50) : n.attributes?.value,
                        meta: n.meta
                      })), null, 2)}
                    </pre>
                  </details>
                  <details>
                    <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-300">All Nodes</summary>
                    <pre className="mt-1 p-2 bg-gray-800 rounded text-xs text-gray-300 overflow-auto">
                      {flow && JSON.stringify(flow.ui.nodes.map(n => ({
                        type: n.type,
                        group: n.group,
                        name: n.attributes?.name,
                        node_type: n.attributes?.node_type,
                        value: typeof n.attributes?.value === 'string' ? n.attributes.value.substring(0, 50) : n.attributes?.value
                      })), null, 2)}
                    </pre>
                  </details>
                </div>
              </details>
            </div>
            
            {renderProfileSection()}
            {renderPasswordSection()}
          </div>
        </div>

        {/* Debug Info Card */}
        <div className="mt-8 glass-card rounded-2xl overflow-hidden">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Debug Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">WebAuthn Support</p>
                <p className="text-sm text-white">
                  {window.PublicKeyCredential ? '✅ Supported' : '❌ Not Supported'}
                </p>
              </div>
              
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Kratos Script</p>
                <p className="text-sm text-white">
                  {scriptLoaded ? '✅ Loaded' : '⏳ Loading...'}
                </p>
              </div>
              
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">User Email</p>
                <p className="text-sm text-white">{identity?.traits?.email || 'Unknown'}</p>
              </div>
              
              <div className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Flow State</p>
                <p className="text-sm text-white">{flow?.state || 'No flow'}</p>
              </div>
            </div>
            
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300">View Detailed Flow Data</summary>
              <div className="mt-2 space-y-2">
                <details>
                  <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-300">WebAuthn Nodes</summary>
                  <pre className="mt-1 p-2 bg-gray-800 rounded text-xs text-gray-300 overflow-auto max-h-48">
                    {flow && JSON.stringify(flow.ui.nodes.filter(n => n.group === 'webauthn').map(n => ({
                      type: n.type,
                      name: n.attributes?.name,
                      value: typeof n.attributes?.value === 'string' ? n.attributes.value.substring(0, 50) : n.attributes?.value,
                      meta: n.meta
                    })), null, 2)}
                  </pre>
                </details>
              </div>
            </details>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KratosSettings;