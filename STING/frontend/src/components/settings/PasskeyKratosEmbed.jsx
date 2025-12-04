import React, { useState, useEffect } from 'react';
import { 
  Key, 
  AlertCircle,
  CheckCircle,
  Shield,
  Loader,
  RefreshCw
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';
import { kratosApi } from '../../utils/kratosConfig';

/**
 * PasskeyKratosEmbed - Embeds Kratos settings flow for passkey management
 */
const PasskeyKratosEmbed = () => {
  const { themeColors } = useTheme();
  const { identity, refreshIdentity } = useKratos();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [settingsFlow, setSettingsFlow] = useState(null);
  const [flowUrl, setFlowUrl] = useState('');
  
  // Get passkeys from Kratos identity
  const passkeys = identity?.credentials?.webauthn?.config?.credentials || [];
  const hasPasskeys = passkeys.length > 0;
  
  // Initialize settings flow
  useEffect(() => {
    const initializeSettingsFlow = async () => {
      try {
        setLoading(true);
        // Create a new settings flow
        const response = await axios.get(kratosApi.settingsBrowser(), {
          headers: {
            'Accept': 'application/json',
          },
          withCredentials: true,
          maxRedirects: 0,
          validateStatus: (status) => status === 303 || status === 200
        });
        
        // If we get a redirect, extract the flow URL
        if (response.status === 303 && response.headers.location) {
          const location = response.headers.location;
          setFlowUrl(location);
          // Extract flow ID from URL
          const flowMatch = location.match(/flow=([^&]+)/);
          if (flowMatch) {
            // Load the flow data
            const flowResponse = await axios.get(kratosApi.settingsFlow(flowMatch[1]), {
              withCredentials: true
            });
            setSettingsFlow(flowResponse.data);
          }
        } else if (response.data) {
          setSettingsFlow(response.data);
          // Construct the flow URL
          const flowId = response.data.id;
          setFlowUrl(`/.ory/self-service/settings/browser?flow=${flowId}`);
        }
      } catch (err) {
        console.error('Failed to initialize settings flow:', err);
        setError('Failed to load settings. Please refresh the page.');
      } finally {
        setLoading(false);
      }
    };
    
    if (identity) {
      initializeSettingsFlow();
    }
  }, [identity]);

  const handleRefresh = async () => {
    // Refresh identity to get updated passkeys
    if (refreshIdentity) {
      await refreshIdentity();
    }
    window.location.reload();
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="w-6 h-6 animate-spin text-yellow-500" />
        <span className="ml-2 text-white">Loading security settings...</span>
      </div>
    );
  }
  
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
            <button
              onClick={handleRefresh}
              className="p-2 text-gray-400 hover:text-white transition-colors"
              title="Refresh passkey list"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
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
                        Added on {formatDate(passkey.added_at)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Kratos Settings Embed - STING Theme Integrated */}
        {flowUrl && (
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
              Manage Passkeys
            </h3>
            
            {/* Enhanced Kratos Embed with STING Theme Integration */}
            <div className="relative dynamic-card-subtle border border-gray-600 rounded-2xl overflow-hidden">
              {/* Custom overlay styles for Kratos UI */}
              <style jsx>{`
                .kratos-embed-container iframe {
                  background: transparent;
                }
                
                /* Kratos Form Styling to match STING themes */
                .kratos-embed-container iframe::after {
                  content: '';
                  position: absolute;
                  top: 0;
                  left: 0;
                  right: 0;
                  bottom: 0;
                  background: linear-gradient(135deg, rgba(26, 31, 46, 0.95), rgba(15, 23, 42, 0.9));
                  pointer-events: none;
                  z-index: -1;
                }
              `}</style>
              
              {/* STING-themed wrapper for Kratos embed */}
              <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm">
                <div className="p-4 border-b border-gray-600/50">
                  <div className="flex items-center gap-2 text-sm text-gray-300">
                    <Shield className="w-4 h-4 text-yellow-500" />
                    <span>Secure passkey management powered by Ory Kratos</span>
                  </div>
                </div>
                
                <div className="kratos-embed-container relative">
                  <iframe
                    src={flowUrl + '&ui_theme=sting'}
                    className="w-full h-96 bg-transparent"
                    title="Hive Passkey Management"
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                    style={{
                      colorScheme: 'dark',
                      filter: 'invert(0.95) hue-rotate(180deg) brightness(1.1) contrast(0.9)'
                    }}
                  />
                  
                  {/* Kratos UI Theme Overlay */}
                  <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-yellow-500/30 to-transparent"></div>
                    <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-yellow-500/30 to-transparent"></div>
                  </div>
                </div>
                
                {/* Hive branding integration */}
                <div className="p-3 bg-slate-800/30 border-t border-gray-600/30">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Passkey management interface</span>
                    <div className="flex items-center gap-1">
                      <span>Themed for</span>
                      <span className="text-yellow-500 font-medium">Hive</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
              <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="text-amber-200 font-medium mb-1">Enhanced Security Interface</p>
                <p className="text-amber-300/80">
                  This interface is styled to match Hive's design system. Use the form above to add or remove passkeys securely. Changes will be reflected after refreshing.
                </p>
              </div>
            </div>
          </div>
        )}

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

        {/* Error Messages */}
        {error && (
          <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg flex items-center">
            <AlertCircle className="w-4 h-4 text-red-400 mr-2" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PasskeyKratosEmbed;