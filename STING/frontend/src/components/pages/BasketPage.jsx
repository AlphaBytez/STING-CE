import React, { useState, useEffect, useCallback } from 'react';
import { 
  HardDrive, 
  FolderOpen, 
  FileText, 
  Trash2, 
  Archive, 
  Search, 
  Filter,
  Move,
  AlertTriangle,
  CheckCircle,
  Clock,
  Download,
  Eye,
  MoreVertical,
  RefreshCw,
  Zap,
  Database
} from 'lucide-react';
import BasketIcon from '../icons/BasketIcon';

const BasketPage = () => {
  const [basketData, setBasketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('date_desc');
  const [showCleanupModal, setShowCleanupModal] = useState(false);
  const [cleanupType, setCleanupType] = useState('temp_files');
  const [bulkOperation, setBulkOperation] = useState(null);

  // Fetch basket overview data
  const fetchBasketData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use the existing storage APIs instead of non-existent basket endpoint
      const [usageResponse, filesResponse] = await Promise.all([
        fetch('/api/files/honey-reserve/usage', {
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' }
        }),
        fetch('/api/files/', {
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' }
        })
      ]);

      let usageData = null;
      let filesData = { files: [] };

      if (usageResponse.ok) {
        usageData = await usageResponse.json();
      }

      if (filesResponse.ok) {
        filesData = await filesResponse.json();
      }

      // Transform the data to match BasketPage expectations
      const transformedData = {
        user_id: 1,
        storage_quota: usageData?.quota || 1073741824, // 1GB default
        total_used: usageData?.used || 0,
        usage_percentage: usageData ? (usageData.used / usageData.quota) * 100 : 0,
        storage_status: usageData?.status || 'healthy',
        breakdown: {
          documents: usageData?.breakdown?.documents || 0,
          temp_files: usageData?.breakdown?.temp_files || 0,
          other: usageData?.breakdown?.other || 0
        },
        honey_jars: [], // Will be populated from files data
        cleanup_opportunities: [],
        total_cleanup_potential: 0,
        recommendations: [],
        statistics: {
          total_documents: filesData.files?.length || 0,
          total_honey_jars: 0,
          total_temp_files: 0,
          largest_file_size: 0,
          oldest_document: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      setBasketData(transformedData);
    } catch (err) {
      console.error('Failed to fetch basket data:', err);
      setError('Failed to connect to storage service');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBasketData();
  }, [fetchBasketData]);

  // Format bytes helper
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Handle file selection
  const toggleFileSelection = (fileId) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  // Select all files
  const selectAllFiles = () => {
    if (!basketData) return;
    
    const allFileIds = basketData.honey_jars.reduce((acc, jar) => {
      return acc.concat(jar.documents.map(doc => doc.id));
    }, []);
    
    setSelectedFiles(new Set(allFileIds));
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedFiles(new Set());
  };

  // Handle cleanup operation
  const handleCleanup = async (type, dryRun = false) => {
    try {
      const response = await fetch('/api/basket/cleanup', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: type,
          dry_run: dryRun,
          file_ids: type === 'selected_files' ? Array.from(selectedFiles) : undefined
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // Refresh data after cleanup
        await fetchBasketData();
        
        // Clear selection if files were cleaned
        if (type === 'selected_files') {
          clearSelection();
        }
        
        // Show success message (you could add a toast notification here)
        console.log(result.message);
      } else {
        setError(result.error || 'Cleanup failed');
      }
    } catch (err) {
      console.error('Cleanup failed:', err);
      setError('Failed to perform cleanup operation');
    }
  };

  // Handle bulk operations
  const handleBulkOperation = async (operation, targetHoneyJarId = null) => {
    try {
      const response = await fetch('/api/basket/documents/bulk', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation: operation,
          document_ids: Array.from(selectedFiles),
          target_honey_jar_id: targetHoneyJarId
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // Refresh data after operation
        await fetchBasketData();
        clearSelection();
        
        console.log(result.message);
      } else {
        setError(result.error || 'Bulk operation failed');
      }
    } catch (err) {
      console.error('Bulk operation failed:', err);
      setError('Failed to perform bulk operation');
    }
  };

  // Get usage color based on percentage
  const getUsageColor = (percentage) => {
    if (percentage >= 90) return 'text-red-400';
    if (percentage >= 75) return 'text-orange-400';
    if (percentage >= 50) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getUsageBarColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-orange-500';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  // Filter and sort documents
  const getFilteredDocuments = () => {
    if (!basketData) return [];
    
    let allDocuments = basketData.honey_jars.reduce((acc, jar) => {
      return acc.concat(jar.documents.map(doc => ({
        ...doc,
        honey_jar_name: jar.name,
        honey_jar_id: jar.id
      })));
    }, []);

    // Apply search filter
    if (searchQuery) {
      allDocuments = allDocuments.filter(doc => 
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply type filter
    if (filterType !== 'all') {
      const extension = filterType.toLowerCase();
      allDocuments = allDocuments.filter(doc => 
        doc.filename.toLowerCase().endsWith(`.${extension}`)
      );
    }

    // Apply sorting
    switch (sortBy) {
      case 'name_asc':
        allDocuments.sort((a, b) => a.filename.localeCompare(b.filename));
        break;
      case 'name_desc':
        allDocuments.sort((a, b) => b.filename.localeCompare(a.filename));
        break;
      case 'size_asc':
        allDocuments.sort((a, b) => a.size - b.size);
        break;
      case 'size_desc':
        allDocuments.sort((a, b) => b.size - a.size);
        break;
      case 'date_asc':
        allDocuments.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        break;
      case 'date_desc':
      default:
        allDocuments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        break;
    }

    return allDocuments;
  };

  if (loading) {
    return (
      <div className="h-full atmospheric-vignette p-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <h1 className="text-2xl font-bold text-white">Loading Your Basket...</h1>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full atmospheric-vignette p-4">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/20 border border-red-600/50 rounded-lg p-6">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="w-6 h-6" />
              <div>
                <h1 className="text-xl font-semibold">Error Loading Basket</h1>
                <p className="text-sm text-red-300 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={() => {
                setError(null);
                fetchBasketData();
              }}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!basketData) return null;

  const filteredDocuments = getFilteredDocuments();
  const usagePercentage = basketData.usage_percentage;
  const usageColor = getUsageColor(usagePercentage);
  const usageBarColor = getUsageBarColor(usagePercentage);

  return (
    <div className="h-full atmospheric-vignette p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <BasketIcon size={24} className="text-amber-400" />
            <div>
              <h1 className="text-xl font-bold text-white">Your Storage Basket</h1>
              <p className="text-sm text-slate-400">Manage your documents and files</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={fetchBasketData}
              className="p-2 sting-glass-medium hover:sting-glass-strong border border-slate-600 text-slate-300 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Storage Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Main Usage Card */}
          <div className="lg:col-span-2 sting-glass-card sting-elevation-medium rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Storage Usage</h3>
              <span className={`text-sm font-medium ${usageColor}`}>
                {basketData.storage_status.charAt(0).toUpperCase() + basketData.storage_status.slice(1)}
              </span>
            </div>
            
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-300">Used Space</span>
                <span className={`font-bold ${usageColor}`}>
                  {formatBytes(basketData.total_used)} / {formatBytes(basketData.storage_quota)} ({usagePercentage}%)
                </span>
              </div>
              
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div 
                  className={`h-3 rounded-full transition-all duration-300 ${usageBarColor}`}
                  style={{ width: `${Math.min(usagePercentage, 100)}%` }}
                ></div>
              </div>
            </div>

            {/* Storage Breakdown */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-slate-400">Documents</span>
                </div>
                <span className="text-sm text-slate-200 font-medium">
                  {formatBytes(basketData.breakdown.documents)}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-400" />
                  <span className="text-sm text-slate-400">Temp Files</span>
                </div>
                <span className="text-sm text-slate-200 font-medium">
                  {formatBytes(basketData.breakdown.temp_files)}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="sting-glass-card sting-elevation-medium rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Quick Stats</h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-400" />
                  <span className="text-sm text-slate-400">Documents</span>
                </div>
                <span className="text-sm text-slate-200 font-medium">
                  {basketData.statistics.total_documents}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm text-slate-400">Honey Jars</span>
                </div>
                <span className="text-sm text-slate-200 font-medium">
                  {basketData.statistics.total_honey_jars}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-400" />
                  <span className="text-sm text-slate-400">Temp Files</span>
                </div>
                <span className="text-sm text-slate-200 font-medium">
                  {basketData.statistics.total_temp_files}
                </span>
              </div>

              {basketData.cleanup_opportunities.length > 0 && (
                <div className="pt-3 border-t border-slate-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-green-400">
                      <Trash2 className="w-4 h-4" />
                      <span className="text-sm">Cleanup Available</span>
                    </div>
                    <span className="text-sm text-green-300 font-medium">
                      {formatBytes(basketData.total_cleanup_potential)}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowCleanupModal(true)}
                    className="mt-2 text-xs px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                  >
                    Start Cleanup
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Document Management Section */}
        <div className="sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-6">
          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Files</option>
                <option value="pdf">PDF</option>
                <option value="docx">Word</option>
                <option value="txt">Text</option>
                <option value="md">Markdown</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="date_desc">Newest First</option>
                <option value="date_asc">Oldest First</option>
                <option value="name_asc">Name A-Z</option>
                <option value="name_desc">Name Z-A</option>
                <option value="size_desc">Largest First</option>
                <option value="size_asc">Smallest First</option>
              </select>
            </div>
          </div>

          {/* Bulk Actions */}
          {selectedFiles.size > 0 && (
            <div className="bg-blue-900/20 border border-blue-600/50 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-blue-400" />
                  <span className="text-blue-300 font-medium">
                    {selectedFiles.size} file{selectedFiles.size !== 1 ? 's' : ''} selected
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleBulkOperation('delete')}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                  >
                    <Trash2 className="w-3 h-3 inline mr-1" />
                    Delete
                  </button>
                  
                  <button
                    onClick={() => handleBulkOperation('archive')}
                    className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded transition-colors"
                  >
                    <Archive className="w-3 h-3 inline mr-1" />
                    Archive
                  </button>
                  
                  <button
                    onClick={clearSelection}
                    className="px-3 py-1 bg-slate-600 hover:bg-slate-700 text-white text-sm rounded transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Document List */}
          <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center gap-4 px-4 py-2 bg-slate-800/50 rounded-lg text-sm font-medium text-slate-400">
              <input
                type="checkbox"
                checked={selectedFiles.size === filteredDocuments.length && filteredDocuments.length > 0}
                onChange={() => selectedFiles.size === filteredDocuments.length ? clearSelection() : selectAllFiles()}
                className="w-4 h-4"
              />
              <div className="flex-1">Name</div>
              <div className="w-24">Size</div>
              <div className="w-32">Honey Jar</div>
              <div className="w-24">Date</div>
              <div className="w-8"></div>
            </div>

            {/* Document Rows */}
            {filteredDocuments.length > 0 ? (
              filteredDocuments.map((document) => (
                <div
                  key={document.id}
                  className={`flex items-center gap-4 px-4 py-3 border border-slate-700 rounded-lg hover:bg-slate-800/30 transition-colors ${
                    selectedFiles.has(document.id) ? 'bg-blue-900/20 border-blue-600/50' : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(document.id)}
                    onChange={() => toggleFileSelection(document.id)}
                    className="w-4 h-4"
                  />
                  
                  <div className="flex-1 flex items-center gap-3 min-w-0">
                    <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <span className="text-slate-200 truncate" title={document.filename}>
                      {document.filename}
                    </span>
                  </div>
                  
                  <div className="w-24 text-sm text-slate-400">
                    {formatBytes(document.size)}
                  </div>
                  
                  <div className="w-32 text-sm text-slate-400 truncate" title={document.honey_jar_name}>
                    {document.honey_jar_name}
                  </div>
                  
                  <div className="w-24 text-sm text-slate-400">
                    {new Date(document.created_at).toLocaleDateString()}
                  </div>
                  
                  <div className="w-8">
                    <button className="p-1 hover:bg-slate-700 rounded">
                      <MoreVertical className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <FolderOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No documents found</p>
                <p className="text-sm text-slate-500 mt-1">
                  {searchQuery ? 'Try adjusting your search terms' : 'Upload some documents to get started'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Cleanup Modal */}
        {showCleanupModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="sting-glass-card sting-elevation-high border border-slate-700 rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">Storage Cleanup</h3>
              
              <div className="space-y-4 mb-6">
                {basketData.cleanup_opportunities.map((opportunity, index) => (
                  <div key={index} className="p-3 bg-slate-800/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-200">
                        {opportunity.description}
                      </span>
                      <span className="text-sm text-green-400 font-medium">
                        {formatBytes(opportunity.potential_savings)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      {opportunity.count} items
                    </p>
                  </div>
                ))}
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowCleanupModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    handleCleanup('temp_files', false);
                    setShowCleanupModal(false);
                  }}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                  Start Cleanup
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BasketPage;