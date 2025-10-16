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
import PasskeyStatus from '../auth/PasskeyStatus';

const PasskeySettings = () => {
  const { themeColors } = useTheme();
  const { identity, kratosUrl } = useKratos();
  const navigate = useNavigate();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [stats, setStats] = useState(null);
  
  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [selectedPasskey, setSelectedPasskey] = useState(null);
  const [newPasskeyName, setNewPasskeyName] = useState('');
  const [renameValue, setRenameValue] = useState('');
  const [password, setPassword] = useState('');
  const [processing, setProcessing] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState({ verified: false });

  const apiUrl = window.env?.REACT_APP_API_URL || 'https://localhost:5050';

  // Load passkeys and stats from custom WebAuthn API
  const loadPasskeys = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('PasskeySettings - Loading passkeys...');
      const [passkeysResponse, statsResponse] = await Promise.all([
        fetch('/api/webauthn/passkeys', { 
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        }),
        fetch('/api/webauthn/passkeys/stats', { 
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        })
      ]);

      console.log('PasskeySettings - Passkeys response:', passkeysResponse.status);
      console.log('PasskeySettings - Stats response:', statsResponse.status);

      if (passkeysResponse.ok) {
        const passkeysData = await passkeysResponse.json();
        console.log('PasskeySettings - Passkeys data:', passkeysData);
        setPasskeys(passkeysData.passkeys || []);
      } else if (passkeysResponse.status === 401) {
        setError('Not authenticated');
        return;
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        console.log('PasskeySettings - Stats data:', statsData);
        setStats(statsData);
      }
    } catch (err) {
      setError('Failed to load passkeys');
      console.error('Error loading passkeys:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPasskeys();
    checkVerificationStatus();
  }, []);

  // Check if password has been recently verified
  const checkVerificationStatus = async () => {
    try {
      const response = await fetch('/api/auth/verify-status', {
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        setVerificationStatus(data);
      }
    } catch (err) {
      console.error('Error checking verification status:', err);
    }
  };

  // Verify password
  const handleVerifyPassword = async () => {
    if (!password) {
      setError('Please enter your password');
      return;
    }

    try {
      setProcessing(true);
      setError('');

      const response = await fetch('/api/auth/verify-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ password })
      });

      const data = await response.json();

      if (response.ok && data.verified) {
        setVerificationStatus({ verified: true, remaining_seconds: 300 });
        setVerifyDialogOpen(false);
        setPassword('');
        setSuccess('Password verified. You can now add a passkey.');
        
        // Now open the add passkey dialog
        setAddDialogOpen(true);
      } else {
        setError(data.error || 'Invalid password');
      }
    } catch (err) {
      setError('Failed to verify password');
    } finally {
      setProcessing(false);
    }
  };

  // Add new passkey using custom WebAuthn
  const handleAddPasskey = async () => {
    console.log('🔐 AddPasskey clicked - name:', newPasskeyName, 'trimmed:', newPasskeyName.trim(), 'processing:', processing);
    if (!newPasskeyName.trim()) {
      setError('Please enter a name for your passkey');
      return;
    }

    try {
      setProcessing(true);
      setError('');

      // Begin passkey registration
      const beginResponse = await fetch('/api/webauthn/passkeys/add/begin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newPasskeyName.trim() })
      });

      if (!beginResponse.ok) {
        const errorData = await beginResponse.json();
        throw new Error(errorData.error || 'Failed to begin passkey registration');
      }

      const options = await beginResponse.json();

      // Helper function to decode base64url
      const base64urlDecode = (str) => {
        // Convert base64url to base64
        const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
        // Pad with = if needed
        const padded = base64 + '=='.substring(0, (4 - base64.length % 4) % 4);
        return atob(padded);
      };

      // Create credential using WebAuthn API
      const credential = await navigator.credentials.create({
        publicKey: {
          ...options.publicKey,
          challenge: Uint8Array.from(base64urlDecode(options.publicKey.challenge), c => c.charCodeAt(0)),
          user: {
            ...options.publicKey.user,
            id: Uint8Array.from(base64urlDecode(options.publicKey.user.id), c => c.charCodeAt(0))
          },
          excludeCredentials: options.publicKey.excludeCredentials?.map(cred => ({
            ...cred,
            id: Uint8Array.from(base64urlDecode(cred.id), c => c.charCodeAt(0))
          })) || []
        }
      });

      // Helper function to encode to base64url
      const base64urlEncode = (buffer) => {
        const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
        return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
      };

      // Complete registration
      const completeResponse = await fetch('/api/webauthn/passkeys/add/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          credential: {
            id: credential.id,
            rawId: base64urlEncode(credential.rawId),
            response: {
              attestationObject: base64urlEncode(credential.response.attestationObject),
              clientDataJSON: base64urlEncode(credential.response.clientDataJSON)
            },
            type: credential.type
          },
          challenge_id: options.challenge_id,
          passkey_name: newPasskeyName.trim()
        })
      });

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json();
        throw new Error(errorData.error || 'Failed to complete passkey registration');
      }

      const result = await completeResponse.json();
      setSuccess(result.message || `Passkey "${newPasskeyName}" added successfully!`);
      setAddDialogOpen(false);
      setNewPasskeyName('');
      loadPasskeys(); // Reload the list

    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Passkey creation was cancelled or not allowed');
      } else {
        setError(err.message || 'Failed to add passkey');
      }
      console.error('Error adding passkey:', err);
    } finally {
      setProcessing(false);
    }
  };

  // Rename passkey
  const handleRenamePasskey = async () => {
    if (!renameValue.trim()) {
      setError('Please enter a new name');
      return;
    }

    try {
      setProcessing(true);
      setError('');

      const response = await fetch(`/api/webauthn/passkeys/${selectedPasskey.id}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: renameValue.trim() })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to rename passkey');
      }

      const result = await response.json();
      setSuccess(result.message);
      setRenameDialogOpen(false);
      setSelectedPasskey(null);
      setRenameValue('');
      loadPasskeys(); // Reload the list

    } catch (err) {
      setError(err.message || 'Failed to rename passkey');
    } finally {
      setProcessing(false);
    }
  };

  // Delete passkey
  const handleDeletePasskey = async () => {
    try {
      setProcessing(true);
      setError('');

      const response = await fetch(`/api/webauthn/passkeys/${selectedPasskey.id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete passkey');
      }

      const result = await response.json();
      setSuccess(result.message);
      setDeleteDialogOpen(false);
      setSelectedPasskey(null);
      loadPasskeys(); // Reload the list

    } catch (err) {
      setError(err.message || 'Failed to delete passkey');
    } finally {
      setProcessing(false);
    }
  };

  // Get device icon based on device type
  const getDeviceIcon = (deviceType) => {
    switch (deviceType) {
      case 'platform':
        return <Smartphone className="w-5 h-5 text-blue-400" />;
      case 'cross-platform':
        return <Monitor className="w-5 h-5 text-green-400" />;
      default:
        return <Key className="w-5 h-5 text-yellow-400" />;
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <Loader className="w-8 h-8 animate-spin text-yellow-400" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-blue-400" />
        <h2 className="text-xl font-semibold text-white">Passkey Management</h2>
      </div>

      {/* Show verification status first */}
      <div className="mb-6">
        <PasskeyStatus />
      </div>

      {/* Info about passkeys */}
      <div className="mb-6 p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5" />
          <div className="text-sm">
            <p className="text-blue-300 font-medium mb-2">About Passkeys</p>
            <ul className="text-gray-300 space-y-1 list-disc list-inside">
              <li>Passkeys provide secure, passwordless authentication</li>
              <li>They use biometric or device authentication</li>
              <li>Each passkey is unique to your device</li>
              <li>You can have up to 10 passkeys registered</li>
            </ul>
          </div>
        </div>
      </div>

      {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-700/50 rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-300">{error}</span>
            </div>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

      {success && (
          <div className="mb-4 p-4 bg-green-900/30 border border-green-700/50 rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-green-300">{success}</span>
            </div>
            <button onClick={() => setSuccess('')} className="text-green-400 hover:text-green-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

      {/* Stats */}
      {stats && (
          <div className="mb-6 p-4 bg-gray-800/50 border border-gray-600 rounded-lg">
            <p className="text-sm text-gray-300 mb-1">
              You have {stats.active_passkeys} of {stats.max_passkeys} passkeys configured
            </p>
            {stats.last_used && (
              <p className="text-sm text-gray-400">
                Last used: {formatDate(stats.last_used)}
              </p>
            )}
          </div>
        )}

      {/* Add passkey button */}
      <div className="mb-6">
          <button
            onClick={() => {
              // Check if password verification is needed
              if (!verificationStatus.verified) {
                setVerifyDialogOpen(true);
              } else {
                setAddDialogOpen(true);
              }
            }}
            disabled={stats && !stats.can_add_more}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-black rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-semibold"
          >
            <Plus className="w-4 h-4" />
            Add New Passkey
          </button>
          {stats && !stats.can_add_more && (
            <p className="text-sm text-gray-400 mt-2">
              Maximum passkeys reached
            </p>
          )}
          {verificationStatus.verified && verificationStatus.remaining_seconds > 0 && (
            <p className="text-sm text-green-400 mt-2">
              Password verified. Valid for {Math.floor(verificationStatus.remaining_seconds / 60)} minutes.
            </p>
          )}
        </div>

      {/* Passkeys list */}
      {passkeys.length === 0 ? (
          <div className="text-center py-8">
            <Key className="w-12 h-12 text-gray-500 mx-auto mb-3" />
            <p className="text-gray-400">
              No passkeys configured. Add your first passkey to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {passkeys.map((passkey) => (
              <div key={passkey.id} className="p-4 bg-gray-800/50 border border-gray-600 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0">
                      {getDeviceIcon(passkey.device_type)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-white">{passkey.name}</h4>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          passkey.status === 'active' 
                            ? 'bg-green-900/30 text-green-300 border border-green-700/50' 
                            : 'bg-gray-700 text-gray-300'
                        }`}>
                          {passkey.status || 'active'}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 space-y-1">
                        <p>Created: {formatDate(passkey.created_at)}</p>
                        <p>Last used: {formatDate(passkey.last_used_at)} • Used {passkey.usage_count || 0} times</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setSelectedPasskey(passkey);
                        setRenameValue(passkey.name);
                        setRenameDialogOpen(true);
                      }}
                      className="p-2 text-gray-400 hover:text-blue-400 hover:bg-blue-900/20 rounded-lg transition-colors"
                      title="Rename"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedPasskey(passkey);
                        setDeleteDialogOpen(true);
                      }}
                      disabled={passkeys.length <= 1}
                      className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={passkeys.length <= 1 ? "Cannot delete your last passkey" : "Delete"}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}


      {/* Add Passkey Dialog */}
      {addDialogOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">Add New Passkey</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Passkey Name
                </label>
                <input
                  type="text"
                  value={newPasskeyName}
                  onChange={(e) => {
                    console.log('🔐 Passkey name input changed:', e.target.value);
                    setNewPasskeyName(e.target.value);
                  }}
                  placeholder="e.g., iPhone 15, MacBook Pro, YubiKey"
                  className="w-full p-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                  autoFocus
                />
                <p className="text-sm text-gray-400 mt-1">
                  Give your passkey a descriptive name to identify it later
                </p>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setAddDialogOpen(false);
                    setNewPasskeyName('');
                  }}
                  disabled={processing}
                  className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddPasskey}
                  disabled={processing || !newPasskeyName.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {processing ? <Loader className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  Add Passkey
                </button>
              </div>
            </div>
          </div>
        )}

      {/* Rename Passkey Dialog */}
      {renameDialogOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">Rename Passkey</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  New Name
                </label>
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="w-full p-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                  autoFocus
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setRenameDialogOpen(false);
                    setSelectedPasskey(null);
                    setRenameValue('');
                  }}
                  disabled={processing}
                  className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRenamePasskey}
                  disabled={processing || !renameValue.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {processing ? <Loader className="w-4 h-4 animate-spin" /> : <Edit3 className="w-4 h-4" />}
                  Rename
                </button>
              </div>
            </div>
          </div>
        )}

      {/* Delete Passkey Dialog */}
      {deleteDialogOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">Delete Passkey</h3>
              <div className="mb-4">
                <p className="text-white mb-2">
                  Are you sure you want to delete the passkey "{selectedPasskey?.name}"?
                </p>
                <p className="text-sm text-gray-400">
                  This action cannot be undone. You'll need to set up this device again if you want to use it for authentication.
                </p>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setDeleteDialogOpen(false);
                    setSelectedPasskey(null);
                  }}
                  disabled={processing}
                  className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeletePasskey}
                  disabled={processing}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {processing ? <Loader className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

      {/* Password Verification Dialog */}
      {verifyDialogOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">Verify Your Password</h3>
              <div className="mb-4">
                <p className="text-gray-300 mb-4">
                  For security, please enter your password to add a new passkey.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleVerifyPassword()}
                    placeholder="Enter your password"
                    className="w-full p-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                    autoFocus
                  />
                </div>
                <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-3">
                  <p className="text-sm text-blue-300">
                    <AlertCircle className="inline w-4 h-4 mr-1" />
                    After verification, you'll have 5 minutes to add your passkey.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setVerifyDialogOpen(false);
                    setPassword('');
                    setError('');
                  }}
                  disabled={processing}
                  className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleVerifyPassword}
                  disabled={processing || !password}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {processing ? <Loader className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                  Verify
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export default PasskeySettings;