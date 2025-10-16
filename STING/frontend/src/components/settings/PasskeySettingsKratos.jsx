import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Smartphone, 
  Monitor, 
  Key, 
  Plus, 
  Edit3, 
  Trash2, 
  AlertCircle,
  CheckCircle,
  Clock,
  Shield,
  X,
  Loader
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useKratos } from '../../auth/KratosProvider';

/**
 * PasskeySettingsKratos - Uses Kratos native WebAuthn/passkey management
 * This replaces the custom WebAuthn implementation
 */
const PasskeySettingsKratos = () => {
  const { themeColors } = useTheme();
  const { identity, kratosUrl } = useKratos();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Check if user has passkeys configured
  const hasPasskeys = identity?.credentials?.webauthn?.config?.credentials?.length > 0;
  const passkeyCount = identity?.credentials?.webauthn?.config?.credentials?.length || 0;

  const handleManagePasskeys = () => {
    // Navigate to Kratos settings flow for passkey management
    window.location.href = `${kratosUrl}/self-service/settings/browser`;
  };

  const handleAddPasskey = () => {
    // Navigate to Kratos settings flow to add a new passkey
    window.location.href = `${kratosUrl}/self-service/settings/browser`;
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
                  {hasPasskeys ? `${passkeyCount} Passkey${passkeyCount > 1 ? 's' : ''} Configured` : 'No Passkeys Configured'}
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

        {/* Add/Manage Passkeys Button */}
        <div className="flex flex-col sm:flex-row gap-3">
          {hasPasskeys ? (
            <button
              onClick={handleManagePasskeys}
              className="floating-button flex items-center justify-center px-4 py-2 bg-yellow-500 text-black font-medium rounded-lg hover:bg-yellow-400 transition-colors"
            >
              <Key className="w-4 h-4 mr-2" />
              Manage Passkeys
            </button>
          ) : (
            <button
              onClick={handleAddPasskey}
              className="floating-button flex items-center justify-center px-4 py-2 bg-yellow-500 text-black font-medium rounded-lg hover:bg-yellow-400 transition-colors"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Passkey
            </button>
          )}
        </div>

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

        {/* Error/Success Messages */}
        {error && (
          <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg flex items-center">
            <AlertCircle className="w-4 h-4 text-red-400 mr-2" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
        )}
        
        {success && (
          <div className="mt-4 p-3 bg-green-900/50 border border-green-700 rounded-lg flex items-center">
            <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
            <span className="text-green-300 text-sm">{success}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PasskeySettingsKratos;