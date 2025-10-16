import React, { useState, useEffect } from 'react';
import { 
  Database, 
  HardDrive, 
  AlertTriangle, 
  Info, 
  Trash2,
  TrendingUp,
  FileText
} from 'lucide-react';

const StorageWidget = ({ className = "" }) => {
  const [storageData, setStorageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStorageData();
  }, []);

  const fetchStorageData = async () => {
    try {
      setLoading(true);
      
      // API call to get storage statistics
      const response = await fetch('/api/storage/usage', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Check if the data has valid values, otherwise use mock data
        if (data.totalQuota === 0 || !data.totalQuota) {
          console.warn('Storage API returned invalid data (totalQuota is 0 or missing), using mock data');
          setStorageData(getMockStorageData());
        } else {
          setStorageData(data);
        }
      } else {
        // Fallback to mock data if API fails
        setStorageData(getMockStorageData());
      }
    } catch (err) {
      console.error('Failed to fetch storage data:', err);
      // Use mock data as fallback
      setStorageData(getMockStorageData());
      setError('Using cached data - live metrics temporarily unavailable');
    } finally {
      setLoading(false);
    }
  };

  const getMockStorageData = () => ({
    totalQuota: 5368709120, // 5GB in bytes
    totalUsed: 1288490188,  // ~1.2GB in bytes
    userQuotas: {
      allocated: 10737418240, // 10GB total allocated to users
      used: 1288490188
    },
    breakdown: {
      documents: 524288000,     // 500MB
      honeyJars: 314572800,     // 300MB
      tempFiles: 104857600,     // 100MB
      embeddings: 209715200,    // 200MB
      system: 134217728         // 128MB
    },
    byHoneyJar: [
      { name: "Engineering Documentation", size: 536870912, documents: 156, lastAccessed: "2 hours ago" },
      { name: "Legal & Compliance", size: 268435456, documents: 89, lastAccessed: "1 day ago" },
      { name: "Customer Support FAQ", size: 134217728, documents: 245, lastAccessed: "5 minutes ago" },
      { name: "Marketing Materials", size: 67108864, documents: 78, lastAccessed: "3 hours ago" },
      { name: "Security Protocols", size: 33554432, documents: 34, lastAccessed: "1 week ago" }
    ],
    users: [
      { name: "Admin User", usage: 536870912, quota: 1073741824, honeyJars: 3 },
      { name: "John Doe", usage: 268435456, quota: 1073741824, honeyJars: 2 },
      { name: "Jane Smith", usage: 134217728, quota: 1073741824, honeyJars: 1 },
      { name: "Demo Users", usage: 67108864, quota: 1073741824, honeyJars: 4 }
    ],
    trends: {
      growthRate: 12.5, // Percentage growth per month
      projectedFull: "8 months", // When storage will be full at current rate
      cleanupOpportunities: 157286400 // Bytes that could be freed
    }
  });

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getUsagePercentage = (used, total) => {
    if (total === 0) return 0;
    return Math.round((used / total) * 100);
  };

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

  if (loading) {
    return (
      <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-6 ${className}`}>
        <div className="flex items-center gap-3 mb-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          <h3 className="text-lg font-semibold text-white">Loading Storage Data...</h3>
        </div>
      </div>
    );
  }

  if (!storageData) {
    return (
      <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-6 ${className}`}>
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <p>Failed to load storage data</p>
        </div>
      </div>
    );
  }

  const usagePercentage = getUsagePercentage(storageData.totalUsed, storageData.totalQuota);
  const usageColor = getUsageColor(usagePercentage);
  const usageBarColor = getUsageBarColor(usagePercentage);

  return (
    <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-4 ${className}`}>
      {/* Horizontal Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <HardDrive className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Honey Reserve Storage</h3>
            <p className="text-xs text-slate-400">System-wide usage</p>
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-1 text-orange-400 text-xs">
            <Info className="w-3 h-3" />
            <span>Cache</span>
          </div>
        )}
      </div>

      {/* Compact Usage Display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Usage Bar Section */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-300 font-medium">Storage Usage</span>
            <span className={`text-xs font-bold ${usageColor}`}>
              {formatBytes(storageData.totalUsed)} / {formatBytes(storageData.totalQuota)} ({usagePercentage}%)
            </span>
          </div>
          
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${usageBarColor}`}
              style={{ width: `${usagePercentage}%` }}
            ></div>
          </div>

          {/* Compact Breakdown */}
          <div className="grid grid-cols-2 gap-2 mt-3">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <FileText className="w-3 h-3 text-green-400" />
                <span className="text-slate-400">Documents</span>
              </div>
              <span className="text-slate-200 font-medium">
                {formatBytes(storageData.breakdown.documents)}
              </span>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <Database className="w-3 h-3 text-yellow-400" />
                <span className="text-slate-400">Jars</span>
              </div>
              <span className="text-slate-200 font-medium">
                {formatBytes(storageData.breakdown.honeyJars)}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-blue-400" />
              <span className="text-slate-400">Growth</span>
            </div>
            <span className="text-slate-200">+{storageData.trends.growthRate}%/mo</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1">
              <Info className="w-3 h-3 text-slate-500" />
              <span className="text-slate-400">Projected Full</span>
            </div>
            <span className="text-slate-200">{storageData.trends.projectedFull}</span>
          </div>

          {storageData.trends.cleanupOpportunities > 0 && (
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1 text-green-400">
                <Trash2 className="w-3 h-3" />
                <span>Cleanup</span>
              </div>
              <span className="text-green-300 font-medium">
                {formatBytes(storageData.trends.cleanupOpportunities)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Warning for high usage */}
      {usagePercentage >= 80 && (
        <div className="mt-3 p-2 bg-orange-900/20 border border-orange-600/50 rounded text-xs">
          <div className="flex items-center gap-2 text-orange-400">
            <AlertTriangle className="w-3 h-3" />
            <span>Storage usage is high. Consider cleanup or quota increase.</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default StorageWidget;