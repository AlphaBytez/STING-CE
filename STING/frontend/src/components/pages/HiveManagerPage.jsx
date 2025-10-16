import React, { useState, useEffect } from 'react';
import GlassCard from '../common/GlassCard';
import { 
  Plus, 
  Settings, 
  Upload,
  FolderOpen,
  FileText,
  RefreshCw,
  Activity,
  Shield,
  Users,
  Hexagon,
  Database,
  Trash2,
  Edit,
  ChevronRight,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { honeyJarApi } from '../../services/knowledgeApi';

const HiveManagerPage = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedHoneyJar, setSelectedHoneyJar] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [honeyJars, setHoneyJars] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [newJarData, setNewJarData] = useState({
    name: '',
    description: '',
    type: 'public',
    tags: []
  });
  const [creating, setCreating] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadingTo, setUploadingTo] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Load honey jars on component mount
  useEffect(() => {
    loadHoneyJars();
  }, []);

  const loadHoneyJars = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await honeyJarApi.getHoneyJars(1, 100); // Get all honey jars
      
      // Handle both direct array response and paginated response
      const honeyJarData = Array.isArray(response) ? response : (response.items || []);
      setHoneyJars(honeyJarData);
    } catch (err) {
      console.error('Failed to load honey jars:', err);
      setError('Failed to load honey jars. Some features may not work correctly.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadHoneyJars();
    setRefreshing(false);
  };

  const handleCreateHoneyJar = async () => {
    if (!newJarData.name.trim()) {
      setError('Please enter a name for the honey jar');
      return;
    }

    setCreating(true);
    try {
      await honeyJarApi.createHoneyJar({
        ...newJarData,
        tags: newJarData.tags.length > 0 ? newJarData.tags : ['general']
      });
      await loadHoneyJars(); // Refresh the list
      setShowCreateModal(false);
      // Reset form
      setNewJarData({
        name: '',
        description: '',
        type: 'public',
        tags: []
      });
      setError(null);
    } catch (err) {
      console.error('Failed to create honey jar:', err);
      setError('Failed to create honey jar: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteHoneyJar = async (id) => {
    if (!window.confirm('Are you sure you want to delete this honey jar? This action cannot be undone.')) {
      return;
    }
    try {
      await honeyJarApi.deleteHoneyJar(id);
      await loadHoneyJars(); // Refresh the list
      setError(null);
    } catch (err) {
      console.error('Failed to delete honey jar:', err);
      setError('Failed to delete honey jar. Please try again.');
    }
  };

  const handleUploadDocuments = async () => {
    if (!uploadingTo || selectedFiles.length === 0) {
      setError('Please select a honey jar and files to upload');
      return;
    }

    setUploading(true);
    try {
      const result = await honeyJarApi.uploadDocuments(
        uploadingTo,
        selectedFiles,
        { tags: ['uploaded', 'bulk'] }
      );

      if (result.documents_uploaded > 0) {
        setError(null);
        setShowUploadModal(false);
        setSelectedFiles([]);
        setUploadingTo(null);
        await loadHoneyJars(); // Refresh stats

        // Show success message
        setError(`✅ Successfully uploaded ${result.documents_uploaded} of ${result.total_files} documents`);
        setTimeout(() => setError(null), 5000);
      } else {
        setError('Failed to upload documents. Please check the files and try again.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  // Calculate real-time stats from loaded honey jars
  const honeyJarStats = {
    total: honeyJars.length,
    active: honeyJars.filter(jar => jar.status === 'active').length,
    processing: honeyJars.filter(jar => jar.status === 'processing').length,
    totalDocuments: honeyJars.reduce((sum, jar) => sum + (jar.stats?.document_count || 0), 0),
    totalEmbeddings: honeyJars.reduce((sum, jar) => sum + (jar.stats?.embedding_count || 0), 0),
    totalStorage: honeyJars.reduce((sum, jar) => sum + (jar.stats?.total_size_bytes || 0), 0),
    avgQueryTime: honeyJars.length > 0
      ? (honeyJars.reduce((sum, jar) => sum + (jar.stats?.average_query_time || 0), 0) / honeyJars.length).toFixed(2)
      : 0,
    lastSync: new Date().toLocaleTimeString()
  };

  // Generate recent activity from actual honey jar data
  const recentActivity = honeyJars.length > 0 ? [
    {
      id: 1,
      action: "Honey Jars Loaded",
      honeyJar: `${honeyJars.length} total jars`,
      user: "System",
      timestamp: new Date().toLocaleTimeString(),
      status: "completed",
      details: `${honeyJarStats.totalDocuments} documents, ${honeyJarStats.totalEmbeddings} embeddings`
    },
    ...honeyJars.slice(0, 2).map((jar, idx) => ({
      id: idx + 2,
      action: jar.stats?.document_count > 0 ? "Documents indexed" : "Honey jar created",
      honeyJar: jar.name,
      user: jar.owner || "System",
      timestamp: jar.last_updated ? new Date(jar.last_updated).toLocaleString() : "Recently",
      status: jar.status === "active" ? "completed" : "processing",
      details: `${jar.stats?.document_count || 0} documents, ${jar.stats?.embedding_count || 0} embeddings`
    }))
  ] : [
    {
      id: 1,
      action: "No activity",
      honeyJar: "N/A",
      user: "System",
      timestamp: new Date().toLocaleTimeString(),
      status: "completed",
      details: "Create a honey jar to get started"
    }
  ];

  // Processing queue placeholder - will need backend endpoint
  const processingQueue = [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-8 h-8 text-yellow-500" />
          <h1 className="text-3xl font-bold text-white">Hive Manager</h1>
        </div>
        <p className="text-gray-400">Create, configure, and manage your knowledge bases</p>
      </div>

      {/* Error and Loading States */}
      <div className="mb-8">
        {error && (
          <div className="mt-3 p-3 bg-red-900/20 border border-red-600/50 rounded-lg">
            <p className="text-red-400 text-sm">⚠️ {error}</p>
          </div>
        )}
        {loading && (
          <div className="mt-3 flex items-center gap-2 text-sm text-gray-400">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-500"></div>
            Loading hive data...
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <button
          onClick={() => setShowCreateModal(true)}
          className="floating-button bg-gradient-to-br from-yellow-500 to-amber-600 hover:from-yellow-600 hover:to-amber-700 border-yellow-400/30 shadow-lg shadow-yellow-500/20 text-black p-4 rounded-lg flex items-center justify-center gap-3 font-semibold"
        >
          <Plus className="w-5 h-5" />
          <span className="font-medium">Create Honey Jar</span>
        </button>
        <button
          onClick={() => setShowUploadModal(true)}
          disabled={honeyJars.length === 0}
          className="floating-button bg-gray-800/50 hover:bg-gray-700/50 border-gray-700 hover:border-gray-600 text-gray-300 p-4 rounded-lg flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          title={honeyJars.length === 0 ? 'Create a honey jar first' : 'Upload documents'}
        >
          <Upload className="w-5 h-5" />
          <span className="font-medium">Bulk Upload</span>
        </button>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="floating-button bg-gray-800/50 hover:bg-gray-700/50 border-gray-700 hover:border-gray-600 text-gray-300 p-4 rounded-lg flex items-center justify-center gap-3 disabled:opacity-50"
          title="Refresh honey jar data"
        >
          <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          <span className="font-medium">{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Stats Overview */}
      <div className="dashboard-card p-6 mb-8">
        <h2 className="text-lg font-semibold text-white mb-4">Hive Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-white">{honeyJarStats.total}</p>
            <p className="text-sm text-gray-400">Total Honey Jars</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-400">{honeyJarStats.active}</p>
            <p className="text-sm text-gray-400">Active</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-400">{honeyJarStats.processing}</p>
            <p className="text-sm text-gray-400">Processing</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-white">{honeyJarStats.totalDocuments}</p>
            <p className="text-sm text-gray-400">Documents</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-white">{honeyJarStats.totalEmbeddings.toLocaleString()}</p>
            <p className="text-sm text-gray-400">Embeddings</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-white">
              {honeyJarStats.totalStorage > 1024 * 1024 * 1024
                ? `${(honeyJarStats.totalStorage / (1024 * 1024 * 1024)).toFixed(2)} GB`
                : honeyJarStats.totalStorage > 1024 * 1024
                ? `${(honeyJarStats.totalStorage / (1024 * 1024)).toFixed(2)} MB`
                : `${(honeyJarStats.totalStorage / 1024).toFixed(2)} KB`}
            </p>
            <p className="text-sm text-gray-400">Storage Used</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-white">{honeyJarStats.avgQueryTime} ms</p>
            <p className="text-sm text-gray-400">Avg Query Time</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700 mb-6">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'overview' 
                ? 'border-yellow-400 text-yellow-400' 
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'activity' 
                ? 'border-yellow-400 text-yellow-400' 
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Recent Activity
          </button>
          <button
            onClick={() => setActiveTab('processing')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'processing' 
                ? 'border-yellow-400 text-yellow-400' 
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Processing Queue
          </button>
          <button
            onClick={() => setActiveTab('permissions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'permissions' 
                ? 'border-yellow-400 text-yellow-400' 
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Permissions
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Storage Usage */}
          <div className="dashboard-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-400" />
              Storage Usage by Honey Jar
            </h3>
            <div className="space-y-3">
              {honeyJars.length > 0 ? (
                honeyJars
                  .sort((a, b) => (b.stats?.total_size_bytes || 0) - (a.stats?.total_size_bytes || 0))
                  .slice(0, 5) // Show top 5 honey jars by size
                  .map((jar) => {
                    const sizeBytes = jar.stats?.total_size_bytes || 0;
                    const sizeFormatted = sizeBytes > 1024 * 1024
                      ? `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
                      : `${(sizeBytes / 1024).toFixed(1)} KB`;
                    const percentage = honeyJarStats.totalStorage > 0
                      ? (sizeBytes / honeyJarStats.totalStorage) * 100
                      : 0;

                    return (
                      <div key={jar.id}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-300 truncate" title={jar.name}>
                            {jar.name}
                          </span>
                          <span className="text-gray-400">{sizeFormatted}</span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                            style={{width: `${Math.min(percentage, 100)}%`}}
                          ></div>
                        </div>
                      </div>
                    );
                  })
              ) : (
                <p className="text-gray-400 text-sm">No honey jars found. Create one to get started.</p>
              )}
            </div>
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="flex justify-between">
                <span className="font-medium text-gray-300">Total Storage</span>
                <span className="font-medium text-white">
                  {honeyJarStats.totalStorage > 1024 * 1024 * 1024
                    ? `${(honeyJarStats.totalStorage / (1024 * 1024 * 1024)).toFixed(2)} GB`
                    : honeyJarStats.totalStorage > 1024 * 1024
                    ? `${(honeyJarStats.totalStorage / (1024 * 1024)).toFixed(2)} MB`
                    : `${(honeyJarStats.totalStorage / 1024).toFixed(2)} KB`}
                  {' of 5 GB'}
                </span>
              </div>
            </div>
          </div>

          {/* Document Types */}
          <div className="dashboard-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-400" />
              Honey Jar Overview
            </h3>
            {honeyJars.length > 0 ? (
              <div className="space-y-3">
                {honeyJars.slice(0, 4).map((jar) => (
                  <div key={jar.id} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-yellow-600/20 rounded-lg flex items-center justify-center">
                        <Hexagon className="w-5 h-5 text-yellow-400" />
                      </div>
                      <div>
                        <p className="font-semibold text-white truncate" title={jar.name}>
                          {jar.name}
                        </p>
                        <p className="text-xs text-gray-400">
                          {jar.stats?.document_count || 0} docs • {jar.stats?.embedding_count || 0} embeddings
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedHoneyJar(jar)}
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        title="View Details"
                      >
                        <FolderOpen className="w-4 h-4 text-gray-400" />
                      </button>
                      <button
                        onClick={() => handleDeleteHoneyJar(jar.id)}
                        className="p-1 hover:bg-red-900/50 rounded transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </div>
                ))}
                {honeyJars.length > 4 && (
                  <p className="text-sm text-gray-400 text-center mt-2">
                    And {honeyJars.length - 4} more honey jars...
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <Hexagon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No honey jars found</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-3 text-yellow-400 hover:text-yellow-300 text-sm"
                >
                  Create your first honey jar
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="dashboard-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-400" />
            Recent Activity
          </h3>
          <div className="space-y-4">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="stats-card p-4 flex items-start gap-4">
                <div className={`p-2 rounded-lg ${
                  activity.status === 'completed' ? 'bg-green-600/20' : 'bg-orange-600/20'
                }`}>
                  {activity.status === 'completed' ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : (
                    <RefreshCw className="w-5 h-5 text-orange-400 animate-spin" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medium text-white">{activity.action}</h4>
                    <span className="text-sm text-gray-400">{activity.timestamp}</span>
                  </div>
                  <p className="text-sm text-gray-300 mb-1">{activity.details}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Hexagon className="w-3 h-3" />
                      {activity.honeyJar}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {activity.user}
                    </span>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'processing' && (
        <div className="dashboard-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-orange-400" />
            Processing Queue
          </h3>
          {processingQueue.length > 0 ? (
            <div className="space-y-4">
              {processingQueue.map((item) => (
                <div key={item.id} className="stats-card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="font-medium text-white">{item.fileName}</h4>
                      <p className="text-sm text-gray-300">
                        Honey Jar: {item.honeyJar} • {item.status}
                      </p>
                    </div>
                    <span className="text-sm text-gray-400">ETA: {item.estimatedTime}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-yellow-400 h-2 rounded-full transition-all duration-300"
                      style={{width: `${item.progress}%`}}
                    ></div>
                  </div>
                  <div className="mt-2 text-right">
                    <span className="text-sm text-gray-300">{item.progress}%</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-gray-300 font-medium">All documents processed</p>
              <p className="text-gray-400 text-sm mt-1">
                No documents are currently being processed.
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'permissions' && (
        <div className="dashboard-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-400" />
            Permissions Management
          </h3>
          <div className="bg-yellow-600/20 border border-yellow-600/50 rounded-lg p-4 mb-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-yellow-300">
                  Permissions management allows you to control access to your Honey Jars.
                  Configure team access, user permissions, and integration with LDAP/SAML/OIDC.
                </p>
              </div>
            </div>
          </div>
          <p className="text-gray-400">Permission management interface coming soon...</p>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="dashboard-card p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-400" />
              Upload Documents to Honey Jar
            </h3>

            {error && (
              <div className="mb-4 p-3 bg-red-900/20 border border-red-600/50 rounded-lg">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Select Honey Jar *</label>
                <select
                  value={uploadingTo || ''}
                  onChange={(e) => setUploadingTo(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 [&>option]:bg-gray-800 [&>option]:text-white"
                  disabled={uploading}
                >
                  <option value="">Choose a honey jar...</option>
                  {honeyJars.map((jar) => (
                    <option key={jar.id} value={jar.id}>
                      {jar.name} ({jar.stats?.document_count || 0} docs)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Select Files *</label>
                <input
                  type="file"
                  multiple
                  onChange={(e) => setSelectedFiles(Array.from(e.target.files))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-yellow-500 file:text-black hover:file:bg-yellow-600"
                  disabled={uploading}
                  accept=".pdf,.txt,.md,.doc,.docx,.json,.html"
                />
                {selectedFiles.length > 0 && (
                  <p className="mt-2 text-sm text-gray-400">
                    {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected
                    ({(selectedFiles.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(2)} MB total)
                  </p>
                )}
              </div>

              <div className="bg-yellow-600/20 border border-yellow-600/50 rounded-lg p-3">
                <p className="text-sm text-yellow-300">
                  <strong>Supported formats:</strong> PDF, TXT, MD, DOC, DOCX, JSON, HTML
                </p>
                <p className="text-sm text-yellow-300 mt-1">
                  Documents will be processed and indexed for semantic search.
                </p>
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFiles([]);
                  setUploadingTo(null);
                  setError(null);
                }}
                disabled={uploading}
                className="flex-1 py-2 px-4 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadDocuments}
                disabled={uploading || !uploadingTo || selectedFiles.length === 0}
                className="flex-1 py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>Upload Documents</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="dashboard-card p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
              <Hexagon className="w-5 h-5 text-yellow-400" />
              Create New Honey Jar
            </h3>
            <p className="text-gray-400 mb-4">Configure and create a new knowledge base for your documents.</p>

            {error && (
              <div className="mb-4 p-3 bg-red-900/20 border border-red-600/50 rounded-lg">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
                <input
                  type="text"
                  value={newJarData.name}
                  onChange={(e) => setNewJarData({...newJarData, name: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-400"
                  placeholder="e.g., Product Documentation"
                  disabled={creating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={newJarData.description}
                  onChange={(e) => setNewJarData({...newJarData, description: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-400"
                  rows="3"
                  placeholder="Describe the purpose of this knowledge base"
                  disabled={creating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
                <select
                  value={newJarData.type}
                  onChange={(e) => setNewJarData({...newJarData, type: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 [&>option]:bg-gray-800 [&>option]:text-white"
                  disabled={creating}
                >
                  <option value="public">Public - Accessible to all users</option>
                  <option value="private">Private - Only you can access</option>
                  <option value="team">Team - Shared with your team</option>
                  <option value="restricted">Restricted - Specific users only</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Tags (optional)</label>
                <input
                  type="text"
                  value={newJarData.tags.join(', ')}
                  onChange={(e) => setNewJarData({
                    ...newJarData,
                    tags: e.target.value.split(',').map(t => t.trim()).filter(t => t)
                  })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-400"
                  placeholder="e.g., docs, api, guides (comma separated)"
                  disabled={creating}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setError(null);
                  setNewJarData({
                    name: '',
                    description: '',
                    type: 'public',
                    tags: []
                  });
                }}
                disabled={creating}
                className="flex-1 py-2 px-4 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateHoneyJar}
                disabled={creating || !newJarData.name.trim()}
                className="flex-1 py-2 px-4 bg-yellow-500 text-black rounded-lg hover:bg-yellow-600 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>Create Honey Jar</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HiveManagerPage;