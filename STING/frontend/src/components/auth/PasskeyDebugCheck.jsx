import React, { useState } from 'react';
import apiClient from '../../utils/apiClient';

const PasskeyDebugCheck = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const checkPasskeys = async () => {
    if (!email) {
      setError('Please enter an email address');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await apiClient.post('/api/webauthn/debug/check-passkeys', {
        email: email
      });

      setResult(response.data);
    } catch (err) {
      console.error('Debug check error:', err);
      if (err.response?.data) {
        setError(JSON.stringify(err.response.data, null, 2));
      } else {
        setError('Failed to check passkeys: ' + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Passkey Debug Check</h1>
        
        <div className="bg-slate-800 rounded-lg p-6 mb-8">
          <div className="mb-4">
            <label className="block text-gray-300 mb-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="w-full px-4 py-2 bg-slate-700 text-white rounded border border-slate-600 focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          
          <button
            onClick={checkPasskeys}
            disabled={loading}
            className="px-6 py-2 bg-yellow-500 text-black rounded hover:bg-yellow-400 disabled:opacity-50"
          >
            {loading ? 'Checking...' : 'Check Passkeys'}
          </button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-4">
            <h3 className="text-red-300 font-bold mb-2">Error:</h3>
            <pre className="text-red-200 whitespace-pre-wrap font-mono text-sm">{error}</pre>
          </div>
        )}

        {result && (
          <div className="bg-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Results:</h2>
            
            {result.user && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-yellow-400 mb-2">User Info:</h3>
                <div className="bg-slate-700 rounded p-4">
                  <p className="text-gray-300">Email: {result.user.email}</p>
                  <p className="text-gray-300">Username: {result.user.username}</p>
                  <p className="text-gray-300">User ID: {result.user.id}</p>
                  <p className="text-gray-300">Kratos ID: {result.user.kratos_id || 'Not set'}</p>
                </div>
              </div>
            )}

            {result.passkeys && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-yellow-400 mb-2">Passkeys:</h3>
                <div className="bg-slate-700 rounded p-4">
                  <p className="text-gray-300 mb-2">Total: {result.passkeys.total}</p>
                  <p className="text-gray-300 mb-4">Active: {result.passkeys.active}</p>
                  
                  {result.passkeys.details && result.passkeys.details.length > 0 ? (
                    <div>
                      <h4 className="text-gray-400 font-semibold mb-2">Passkey Details:</h4>
                      {result.passkeys.details.map((passkey, index) => (
                        <div key={index} className="mb-4 p-3 bg-slate-600 rounded">
                          <p className="text-gray-300">Name: {passkey.name}</p>
                          <p className="text-gray-300">Status: <span className={passkey.is_active ? 'text-green-400' : 'text-red-400'}>{passkey.status}</span></p>
                          <p className="text-gray-300">Created: {new Date(passkey.created_at).toLocaleString()}</p>
                          <p className="text-gray-300">Last Used: {passkey.last_used_at ? new Date(passkey.last_used_at).toLocaleString() : 'Never'}</p>
                          <p className="text-gray-300">Usage Count: {passkey.usage_count}</p>
                          <p className="text-gray-300 text-xs mt-2">Credential ID: {passkey.credential_id.substring(0, 20)}...</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-orange-400">No passkeys found for this user!</p>
                  )}
                </div>
              </div>
            )}

            {result.debug_info && (
              <div>
                <h3 className="text-lg font-semibold text-yellow-400 mb-2">Debug Info:</h3>
                <div className="bg-slate-700 rounded p-4">
                  <pre className="text-gray-300 whitespace-pre-wrap font-mono text-sm">
                    {JSON.stringify(result.debug_info, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PasskeyDebugCheck;