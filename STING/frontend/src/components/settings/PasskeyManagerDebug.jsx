import React, { useState, useEffect } from 'react';
import { Key, Shield, Loader, AlertCircle, Info } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasskeyManagerDebug = () => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [flowData, setFlowData] = useState(null);
  const [debugInfo, setDebugInfo] = useState('');

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

  // Debug: Create settings flow and examine it
  const debugSettingsFlow = async () => {
    setError('');
    setDebugInfo('Creating settings flow...');

    try {
      // Step 1: Create settings flow
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      setFlowData(flow);
      
      // Log the entire flow structure
      console.log('🔍 Full settings flow:', JSON.stringify(flow, null, 2));
      
      // Analyze the flow
      const analysis = {
        flowId: flow.id,
        state: flow.state,
        type: flow.type,
        methods: Object.keys(flow.methods || {}),
        totalNodes: flow.ui.nodes.length,
        groups: [...new Set(flow.ui.nodes.map(n => n.group))],
        webauthnNodes: flow.ui.nodes.filter(n => n.group === 'webauthn'),
        nodesByType: {}
      };

      // Count nodes by type
      flow.ui.nodes.forEach(node => {
        const type = node.type;
        if (!analysis.nodesByType[type]) {
          analysis.nodesByType[type] = 0;
        }
        analysis.nodesByType[type]++;
      });

      // Look specifically for WebAuthn nodes
      const webauthnInfo = {
        total: analysis.webauthnNodes.length,
        nodes: analysis.webauthnNodes.map(n => ({
          type: n.type,
          attributes: {
            name: n.attributes?.name,
            type: n.attributes?.type,
            value: n.attributes?.value,
            node_type: n.attributes?.node_type,
            disabled: n.attributes?.disabled,
            label: n.meta?.label?.text
          },
          meta: n.meta
        }))
      };

      setDebugInfo(JSON.stringify({
        analysis,
        webauthnInfo,
        messages: flow.ui.messages || []
      }, null, 2));

      // Check if user needs to verify email first
      const hasVerifiableAddresses = identity?.verifiable_addresses?.length > 0;
      const isEmailVerified = identity?.verifiable_addresses?.[0]?.verified === true;
      
      if (!hasVerifiableAddresses || isEmailVerified) {
        console.log('✅ Email verification not required or already verified');
      } else {
        console.log('⚠️ Email verification may be required');
        setError('Email verification may be required before setting up passkeys');
      }

    } catch (err) {
      console.error('Debug error:', err);
      setError(`Debug error: ${err.message}`);
      setDebugInfo(JSON.stringify(err.response?.data || err, null, 2));
    }
  };

  // Try to register with the direct Kratos UI
  const openKratosSettings = () => {
    window.open('/.ory/ui/settings', '_blank');
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
                <h1 className="text-2xl font-bold text-white">Passkey Debug Panel</h1>
                <p className="text-gray-400 text-sm mt-1">
                  Debug WebAuthn registration issues
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

          {/* Debug Actions */}
          <div className="mb-8 space-y-4">
            <div className="p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
              <h3 className="text-white font-semibold mb-3">Debug Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={debugSettingsFlow}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  Analyze Settings Flow
                </button>
                <button
                  onClick={openKratosSettings}
                  className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
                >
                  Open Kratos Settings UI
                </button>
              </div>
            </div>

            {/* Identity Info */}
            <div className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg">
              <h3 className="text-white font-semibold mb-3">Identity Information</h3>
              <div className="text-sm text-gray-300 space-y-1">
                <p>Email: {identity?.traits?.email || 'Unknown'}</p>
                <p>Verified: {identity?.verifiable_addresses?.[0]?.verified ? '✅ Yes' : '❌ No'}</p>
                <p>WebAuthn Credentials: {identity?.credentials?.webauthn?.length || 0}</p>
                <p>Password Set: {identity?.credentials?.password ? '✅ Yes' : '❌ No'}</p>
              </div>
            </div>
          </div>

          {/* Debug Output */}
          {debugInfo && (
            <div className="mb-8">
              <h3 className="text-white font-semibold mb-3">Debug Information</h3>
              <pre className="p-4 bg-slate-900 border border-slate-700 rounded-lg overflow-x-auto text-xs text-gray-300">
                {debugInfo}
              </pre>
            </div>
          )}

          {/* Flow Data */}
          {flowData && (
            <div className="mb-8">
              <h3 className="text-white font-semibold mb-3">Raw Flow Data</h3>
              <details className="p-4 bg-slate-900 border border-slate-700 rounded-lg">
                <summary className="cursor-pointer text-yellow-400">Click to expand</summary>
                <pre className="mt-3 overflow-x-auto text-xs text-gray-300">
                  {JSON.stringify(flowData, null, 2)}
                </pre>
              </details>
            </div>
          )}

          {/* Existing Passkeys */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Current Passkeys</h2>
            
            {passkeys.length === 0 ? (
              <div className="p-6 bg-slate-700/30 border border-slate-600/50 rounded-lg text-center">
                <Shield className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                <p className="text-gray-400">No passkeys registered yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {passkeys.map((passkey) => (
                  <div
                    key={passkey.id}
                    className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Key className="w-5 h-5 text-yellow-400" />
                      <div>
                        <p className="text-white font-medium">{passkey.display_name}</p>
                        <p className="text-xs text-gray-400">
                          Added: {formatDate(passkey.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Info Section */}
          <div className="p-4 bg-amber-900/20 border border-amber-700/50 rounded-lg">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-300">
                <p className="font-semibold mb-2">Troubleshooting Tips:</p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>Ensure your email is verified before setting up passkeys</li>
                  <li>Check browser console for JavaScript errors</li>
                  <li>Try using the Kratos Settings UI directly</li>
                  <li>Verify WebAuthn is enabled in kratos.yml</li>
                  <li>Check that the RP ID matches your domain</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PasskeyManagerDebug;