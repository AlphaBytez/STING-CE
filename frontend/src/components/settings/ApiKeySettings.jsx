import React, { useState, useEffect } from 'react';
import { 
  Key, 
  Plus, 
  Eye, 
  Copy, 
  Trash2, 
  Edit3,
  Calendar,
  Activity,
  Shield,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import axios from 'axios';
import {
  handleReturnFromAuth,
  checkOperationAuth,
  clearAuthMarker,
  handleAuthError,
  OPERATIONS
} from '../../utils/tieredAuth';

const ApiKeySettings = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createdApiKey, setCreatedApiKey] = useState(null); // Store newly created key secret
  const [selectedKey, setSelectedKey] = useState(null);
  const [showUsageModal, setShowUsageModal] = useState(false);
  const [usage, setUsage] = useState(null);

  // Create form state
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    scopes: ['read'],
    permissions: {},
    expires_in_days: null,
    rate_limit_per_minute: 60
  });

  useEffect(() => {
    // Handle return from authentication flow
    const justAuthenticated = handleReturnFromAuth(OPERATIONS.CREATE_API_KEY.name);

    if (justAuthenticated) {
      setError(null); // Clear any previous errors
    }

    // Always load API keys for viewing - no pre-auth needed for read operations
    loadApiKeys();
  }, []);

  // Use centralized tiered auth utilities

  const handleCreateApiKeyClick = async () => {
    // Check authentication BEFORE opening the form (prevent data loss)
    const canProceed = await checkOperationAuth(OPERATIONS.CREATE_API_KEY.name, OPERATIONS.CREATE_API_KEY.tier);

    if (canProceed) {
      // User is authorized, open the form
      console.log('✅ User authorized for API key creation, opening form');
      setShowCreateModal(true);
    }
    // If not authorized, user was redirected to security-upgrade
  };

  const loadApiKeys = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/keys', {
        withCredentials: true
      });
      // Filter to only show active keys (deleted keys have is_active: false)
      const activeKeys = (response.data.api_keys || []).filter(key => key.is_active);
      setApiKeys(activeKeys);
      setError(null); // Clear any previous errors
    } catch (err) {
      // Handle 404 as "no keys yet" rather than an error
      if (err.response?.status === 404) {
        setApiKeys([]);
        setError(null); // Don't show error for 404
      } else {
        setError(err.response?.data?.error || 'Failed to load API keys');
      }
    } finally {
      setLoading(false);
    }
  };

  const createApiKey = async (e) => {
    e.preventDefault();

    // Authentication already verified when form was opened
    console.log('🔄 Creating API key (authentication pre-verified)');

    try {
      const response = await axios.post('/api/keys', createForm, {
        withCredentials: true
      });

      setCreatedApiKey(response.data);
      setCreateForm({
        name: '',
        description: '',
        scopes: ['read'],
        permissions: {},
        expires_in_days: null,
        rate_limit_per_minute: 60
      });

      // Clear auth markers since operation succeeded
      clearAuthMarker(OPERATIONS.CREATE_API_KEY.name);

      loadApiKeys();
    } catch (err) {
      // Enhanced error handling to display full error information
      let errorMessage = 'Failed to create API key';
      let errorDetails = null;

      if (err.response?.data) {
        const errorData = err.response.data;
        errorMessage = errorData.error || errorMessage;

        // Add additional details if available
        if (errorData.message) {
          errorDetails = errorData.message;
        }

        // Handle specific error types
        if (errorData.type === 'validation_error') {
          errorMessage = `Validation Error: ${errorMessage}`;
        } else if (errorData.type === 'server_error') {
          errorMessage = `Server Error: ${errorMessage}`;
        }
      }

      // Combine message and details for display
      const fullError = errorDetails ? `${errorMessage}. ${errorDetails}` : errorMessage;
      setError(fullError);

      console.error('❌ API key creation failed:', {
        status: err.response?.status,
        error: errorMessage,
        details: errorDetails,
        type: err.response?.data?.type
      });
    }
  };

  const deleteApiKey = async (keyId, keyName) => {
    if (!window.confirm(`Are you sure you want to delete "${keyName}"?`)) {
      return;
    }

    try {
      await axios.delete(`/api/keys/${keyId}`, {
        withCredentials: true
      });
      loadApiKeys();
    } catch (err) {
      // Handle AAL2 step-up requirement
      if (err.response?.status === 403 && err.response?.data?.code === 'aal2_required') {
        // User needs AAL2 step-up for this sensitive operation
        console.log('🔒 AAL2 step-up required for API key deletion');
        window.location.href = '/security-upgrade?reason=api_key_deletion&return_to=' +
          encodeURIComponent('/dashboard/settings?tab=security');
        return;
      }

      setError(err.response?.data?.error || 'Failed to delete API key');
    }
  };

  const loadUsage = async (keyId) => {
    try {
      const response = await axios.get(`/api/keys/${keyId}/usage`, {
        withCredentials: true
      });
      setUsage(response.data);
      setShowUsageModal(true);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load usage data');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never expires';
    return new Date(dateString).toLocaleDateString();
  };

  const getScopeColor = (scope) => {
    switch (scope) {
      case 'read': return 'text-green-400';
      case 'write': return 'text-yellow-400';
      case 'admin': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getScopeIcon = (scope) => {
    switch (scope) {
      case 'read': return <Eye className="w-3 h-3" />;
      case 'write': return <Edit3 className="w-3 h-3" />;
      case 'admin': return <Shield className="w-3 h-3" />;
      default: return <Key className="w-3 h-3" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Key className="w-5 h-5 text-yellow-400" />
            API Keys
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Manage API keys for programmatic access to STING
          </p>
        </div>
        <button
          onClick={handleCreateApiKeyClick}
          className="px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-300">
            <AlertCircle className="w-4 h-4" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-sm text-red-400 mt-2">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-400 underline text-xs mt-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* API Keys List */}
      <div className="space-y-4">
        {apiKeys.length === 0 ? (
          <div className="text-center py-8">
            <Key className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-400 mb-2">No API Keys</h3>
            <p className="text-sm text-gray-500 mb-4">Create your first API key to get started</p>
            <button
              onClick={handleCreateApiKeyClick}
              className="px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium"
            >
              Create API Key
            </button>
          </div>
        ) : (
          apiKeys.map((key) => (
            <div key={key.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-medium text-white">{key.name}</h3>
                    <div className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${
                      key.is_active 
                        ? key.is_expired 
                          ? 'bg-red-900/50 text-red-300'
                          : 'bg-green-900/50 text-green-300'
                        : 'bg-gray-900/50 text-gray-400'
                    }`}>
                      {key.is_active ? (
                        key.is_expired ? (
                          <>
                            <AlertCircle className="w-3 h-3" />
                            Expired
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-3 h-3" />
                            Active
                          </>
                        )
                      ) : (
                        <>
                          <Clock className="w-3 h-3" />
                          Inactive
                        </>
                      )}
                    </div>
                  </div>
                  
                  {key.description && (
                    <p className="text-sm text-gray-400 mb-3">{key.description}</p>
                  )}
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>ID: {key.key_id}</span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Created: {formatDate(key.created_at)}
                    </span>
                    {key.expires_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Expires: {formatDate(key.expires_at)}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Activity className="w-3 h-3" />
                      Used {key.usage_count} times
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-xs text-gray-400">Scopes:</span>
                    {key.scopes.map((scope) => (
                      <span
                        key={scope}
                        className={`px-2 py-1 rounded text-xs font-medium ${getScopeColor(scope)} bg-slate-700/50 flex items-center gap-1`}
                      >
                        {getScopeIcon(scope)}
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setSelectedKey(key);
                      loadUsage(key.key_id);
                    }}
                    className="p-2 text-gray-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                    title="View Usage"
                  >
                    <Activity className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteApiKey(key.key_id, key.name)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-slate-700 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0}}>
          <div className="bg-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto relative transform">
            <div className="flex items-center justify-between p-6 border-b border-slate-700">
              <h2 className="text-xl font-semibold text-white">Create API Key</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            
            <form onSubmit={createApiKey} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                  placeholder="e.g., Production API, Test Integration"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                  rows={3}
                  placeholder="Describe what this API key will be used for"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Scopes
                </label>
                <div className="space-y-2">
                  {['read', 'write', 'admin'].map(scope => (
                    <label key={scope} className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={createForm.scopes.includes(scope)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setCreateForm(prev => ({
                              ...prev,
                              scopes: [...prev.scopes, scope]
                            }));
                          } else {
                            setCreateForm(prev => ({
                              ...prev,
                              scopes: prev.scopes.filter(s => s !== scope)
                            }));
                          }
                        }}
                        className="rounded border-gray-600 bg-slate-700 text-yellow-500 focus:ring-yellow-500"
                      />
                      <span className={`text-sm ${getScopeColor(scope)} flex items-center gap-2`}>
                        {getScopeIcon(scope)}
                        <span className="font-medium">{scope}</span>
                        <span className="text-gray-400">
                          {scope === 'read' && '- View data and resources'}
                          {scope === 'write' && '- Create and modify resources'}
                          {scope === 'admin' && '- Full administrative access'}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Rate Limit (per minute)
                  </label>
                  <input
                    type="number"
                    value={createForm.rate_limit_per_minute}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, rate_limit_per_minute: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    min="1"
                    max="1000"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Expires in (days)
                  </label>
                  <input
                    type="number"
                    value={createForm.expires_in_days || ''}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, expires_in_days: e.target.value ? parseInt(e.target.value) : null }))}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    placeholder="Never"
                    min="1"
                    max="365"
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium"
                >
                  Create API Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Created API Key Modal */}
      {createdApiKey && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0}}>
          <div className="bg-slate-800 rounded-2xl w-full max-w-2xl relative transform">
            <div className="p-6 border-b border-slate-700">
              <h2 className="text-xl font-semibold text-white">API Key Created Successfully</h2>
              <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-3 mt-4">
                <div className="flex items-center gap-2 text-yellow-300 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  <span className="font-medium">Important</span>
                </div>
                <p className="text-sm text-yellow-200">
                  {createdApiKey.warning}
                </p>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  API Key Name
                </label>
                <div className="p-3 bg-slate-700 rounded-lg text-white">
                  {createdApiKey.name}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  API Key Secret
                </label>
                <div className="flex items-center gap-2">
                  <div className="flex-1 p-3 bg-slate-700 rounded-lg text-white font-mono text-sm break-all">
                    {createdApiKey.secret}
                  </div>
                  <button
                    onClick={() => copyToClipboard(createdApiKey.secret)}
                    className="p-3 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
                <h4 className="text-blue-300 font-medium mb-2">Usage Example</h4>
                <code className="text-sm text-blue-200 bg-slate-900/50 p-2 rounded block">
                  curl -H "Authorization: Bearer {createdApiKey.secret}" https://localhost:8443/api/keys/validate
                </code>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 p-6 border-t border-slate-700">
              <button
                onClick={() => setCreatedApiKey(null)}
                className="px-6 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium"
              >
                I've Saved the Key
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Usage Modal */}
      {showUsageModal && usage && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0}}>
          <div className="bg-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-y-auto relative transform">
            <div className="flex items-center justify-between p-6 border-b border-slate-700">
              <h2 className="text-xl font-semibold text-white">
                Usage Statistics: {selectedKey?.name}
              </h2>
              <button
                onClick={() => setShowUsageModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="text-2xl font-bold text-white">{usage.statistics.total_requests}</div>
                  <div className="text-sm text-gray-400">Total Requests</div>
                </div>
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-400">{usage.statistics.successful_requests}</div>
                  <div className="text-sm text-gray-400">Successful</div>
                </div>
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-400">{usage.statistics.error_rate}%</div>
                  <div className="text-sm text-gray-400">Error Rate</div>
                </div>
              </div>
              
              {/* Recent Logs */}
              <div>
                <h3 className="text-lg font-medium text-white mb-4">Recent Activity</h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {usage.recent_logs.map((log) => (
                    <div key={log.id} className="bg-slate-700 rounded p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-white font-mono">{log.method} {log.endpoint}</span>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            log.status_code < 400 ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                          }`}>
                            {log.status_code}
                          </span>
                          <span className="text-gray-400">{new Date(log.timestamp).toLocaleString()}</span>
                        </div>
                      </div>
                      {log.error_message && (
                        <div className="text-red-400 text-xs mt-1">{log.error_message}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiKeySettings;