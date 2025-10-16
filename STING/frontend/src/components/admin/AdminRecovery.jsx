import React, { useState } from 'react';
import {
  Shield,
  Key,
  RefreshCw,
  User,
  AlertTriangle,
  Check,
  Copy,
  Lock
} from 'lucide-react';

const AdminRecovery = () => {
  const [activeTab, setActiveTab] = useState('token');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Form states
  const [targetEmail, setTargetEmail] = useState('admin@sting.local');
  const [recoveryToken, setRecoveryToken] = useState('');
  const [recoverySecret, setRecoverySecret] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [generatePassword, setGeneratePassword] = useState(true);

  const handleGenerateToken = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch('/api/admin/recovery/generate-recovery-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email: targetEmail })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setResult({
          type: 'token',
          token: data.token,
          message: data.message
        });
      } else {
        setError(data.error || 'Failed to generate token');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetWithToken = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch('/api/admin/recovery/reset-with-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: recoveryToken,
          new_password: generatePassword ? null : newPassword
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setResult({
          type: 'password',
          password: data.generated_password || newPassword,
          message: data.message
        });
        setRecoveryToken('');
      } else {
        setError(data.error || 'Failed to reset password');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetWithSecret = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch('/api/admin/recovery/reset-with-secret', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recovery_secret: recoverySecret,
          email: targetEmail,
          new_password: generatePassword ? null : newPassword
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setResult({
          type: 'password',
          password: data.generated_password || newPassword,
          message: data.message
        });
        setRecoverySecret('');
      } else {
        setError(data.error || 'Failed to reset password');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisableTOTP = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch('/api/admin/recovery/disable-totp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email: targetEmail })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setResult({
          type: 'totp',
          message: data.message
        });
      } else {
        setError(data.error || 'Failed to disable TOTP');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // Could add a toast notification here
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-900/20 to-orange-900/20 backdrop-blur-sm rounded-xl p-6 border border-red-800/30">
        <div className="flex items-center space-x-3">
          <Shield className="h-8 w-8 text-red-400" />
          <div>
            <h2 className="text-2xl font-bold text-white">Admin Recovery Tools</h2>
            <p className="text-gray-400 mt-1">Emergency access recovery for administrators</p>
          </div>
        </div>
      </div>

      {/* Alert */}
      <div className="bg-yellow-900/20 border border-yellow-800/30 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 text-yellow-400 mt-0.5" />
          <div className="text-sm text-yellow-200">
            <p className="font-semibold mb-1">Security Notice</p>
            <p>These tools provide emergency access recovery. All actions are logged for audit purposes.</p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-4 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('token')}
          className={`pb-3 px-1 border-b-2 transition-colors ${
            activeTab === 'token'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Recovery Token
        </button>
        <button
          onClick={() => setActiveTab('secret')}
          className={`pb-3 px-1 border-b-2 transition-colors ${
            activeTab === 'secret'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Recovery Secret
        </button>
        <button
          onClick={() => setActiveTab('totp')}
          className={`pb-3 px-1 border-b-2 transition-colors ${
            activeTab === 'totp'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Disable TOTP
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl p-6 border border-gray-800">
        {activeTab === 'token' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Generate Recovery Token</h3>
              <p className="text-gray-400 text-sm mb-4">
                Generate a one-time recovery token that can be used to reset a password without email access.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Target Email
                  </label>
                  <input
                    type="email"
                    value={targetEmail}
                    onChange={(e) => setTargetEmail(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="admin@sting.local"
                  />
                </div>
                
                <button
                  onClick={handleGenerateToken}
                  disabled={loading}
                  className="px-6 py-2 floating-button rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading ? 'Generating...' : 'Generate Token'}
                </button>
              </div>
            </div>

            {result?.type === 'token' && (
              <div className="bg-green-900/20 border border-green-800/30 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-green-400 font-semibold mb-2">Token Generated</p>
                    <code className="block bg-gray-800 p-3 rounded text-xs text-gray-300 break-all">
                      {result.token}
                    </code>
                    <p className="text-sm text-gray-400 mt-2">{result.message}</p>
                  </div>
                  <button
                    onClick={() => copyToClipboard(result.token)}
                    className="ml-4 p-2 text-gray-400 hover:text-white transition-colors"
                  >
                    <Copy className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}

            <div className="border-t border-gray-700 pt-6">
              <h4 className="text-lg font-semibold text-white mb-4">Use Recovery Token</h4>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Recovery Token
                  </label>
                  <input
                    type="text"
                    value={recoveryToken}
                    onChange={(e) => setRecoveryToken(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="Enter recovery token"
                  />
                </div>
                
                <div className="flex items-center space-x-4">
                  <label className="flex items-center text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={generatePassword}
                      onChange={(e) => setGeneratePassword(e.target.checked)}
                      className="mr-2"
                    />
                    Generate secure password
                  </label>
                </div>
                
                {!generatePassword && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="Enter new password"
                    />
                  </div>
                )}
                
                <button
                  onClick={handleResetWithToken}
                  disabled={loading || !recoveryToken}
                  className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Resetting...' : 'Reset Password'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'secret' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Emergency Recovery</h3>
              <p className="text-gray-400 text-sm mb-4">
                Use the master recovery secret for emergency password reset. This should only be used when other methods fail.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Recovery Secret
                  </label>
                  <input
                    type="password"
                    value={recoverySecret}
                    onChange={(e) => setRecoverySecret(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="Enter recovery secret"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Target Email
                  </label>
                  <input
                    type="email"
                    value={targetEmail}
                    onChange={(e) => setTargetEmail(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="admin@sting.local"
                  />
                </div>
                
                <div className="flex items-center space-x-4">
                  <label className="flex items-center text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={generatePassword}
                      onChange={(e) => setGeneratePassword(e.target.checked)}
                      className="mr-2"
                    />
                    Generate secure password
                  </label>
                </div>
                
                {!generatePassword && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="Enter new password"
                    />
                  </div>
                )}
                
                <button
                  onClick={handleResetWithSecret}
                  disabled={loading || !recoverySecret}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Resetting...' : 'Emergency Reset'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'totp' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Disable TOTP/2FA</h3>
              <p className="text-gray-400 text-sm mb-4">
                Remove two-factor authentication for a user who has lost access to their authenticator app.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    User Email
                  </label>
                  <input
                    type="email"
                    value={targetEmail}
                    onChange={(e) => setTargetEmail(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="user@example.com"
                  />
                </div>
                
                <button
                  onClick={handleDisableTOTP}
                  disabled={loading}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Disable TOTP'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Result */}
        {result?.type === 'password' && (
          <div className="mt-6 bg-green-900/20 border border-green-800/30 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <Check className="h-5 w-5 text-green-400" />
                  <p className="text-green-400 font-semibold">Password Reset Successful</p>
                </div>
                <p className="text-sm text-gray-300 mb-2">{result.message}</p>
                {result.password && (
                  <div>
                    <p className="text-sm text-gray-400 mb-1">New password:</p>
                    <code className="block bg-gray-800 p-3 rounded text-sm text-gray-300">
                      {result.password}
                    </code>
                  </div>
                )}
              </div>
              {result.password && (
                <button
                  onClick={() => copyToClipboard(result.password)}
                  className="ml-4 p-2 text-gray-400 hover:text-white transition-colors"
                >
                  <Copy className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>
        )}

        {result?.type === 'totp' && (
          <div className="mt-6 bg-green-900/20 border border-green-800/30 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <Check className="h-5 w-5 text-green-400" />
              <p className="text-green-400 font-semibold">{result.message}</p>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-6 bg-red-900/20 border border-red-800/30 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <p className="text-red-400">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminRecovery;