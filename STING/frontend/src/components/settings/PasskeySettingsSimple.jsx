import React from 'react';
import { 
  Key, 
  ExternalLink,
  AlertCircle,
  CheckCircle,
  Shield
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { kratosApi } from '../../utils/kratosConfig';

/**
 * PasskeySettingsSimple - Simplified passkey settings that redirects to Kratos
 * Since custom WebAuthn endpoints are disabled, this component provides
 * information and a link to the Kratos settings page
 */
const PasskeySettingsSimple = () => {
  const { themeColors } = useTheme();
  const { identity } = useKratos();
  const navigate = useNavigate();
  
  // Get passkeys from Kratos identity
  const passkeys = identity?.credentials?.webauthn?.config?.credentials || [];
  const hasPasskeys = passkeys.length > 0;
  
  const handleManagePasskeys = async () => {
    try {
      // Initialize a settings flow with Kratos
      const response = await axios.get(kratosApi.settingsBrowser(), {
        headers: {
          'Accept': 'application/json',
        },
        withCredentials: true,
        maxRedirects: 0,
        validateStatus: (status) => status === 303 || (status >= 200 && status < 300)
      });
      
      // If we get a redirect (303), extract the flow ID and navigate to our KratosSettings component
      if (response.status === 303 && response.headers.location) {
        const locationUrl = new URL(response.headers.location, window.location.origin);
        const flowId = locationUrl.searchParams.get('flow');
        if (flowId) {
          navigate(`/dashboard/settings/security?flow=${flowId}`);
        }
      } else if (response.data && response.data.id) {
        // If we get flow data directly, navigate with the flow ID
        navigate(`/dashboard/settings/security?flow=${response.data.id}`);
      }
    } catch (error) {
      console.error('Failed to initialize settings flow:', error);
      // Try to initiate a new flow by navigating without a flow ID
      // The KratosSettings component will handle creating a new flow
      navigate('/dashboard/settings/security');
    }
  };
  
  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };
  
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
                  Please verify your email address to enable passkey setup.
                </p>
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
                        Added on {formatDate(passkey.added_at)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Manage Passkeys Button */}
        <button
          onClick={handleManagePasskeys}
          className="floating-button flex items-center justify-center px-4 py-2 bg-yellow-500 text-black font-medium rounded-lg hover:bg-yellow-400 transition-colors"
        >
          <Key className="w-4 h-4 mr-2" />
          {hasPasskeys ? 'Manage Passkeys' : 'Add Your First Passkey'}
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

        {/* Temporary Notice */}
        <div className="mt-6 p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-amber-300 mb-1">
                Advanced Settings
              </p>
              <p className="text-sm text-gray-300">
                Click the button above to access advanced passkey management options, including adding new passkeys and removing existing ones.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PasskeySettingsSimple;