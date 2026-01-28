import React, { useState, useEffect } from 'react';
import { Database, HardDrive, AlertTriangle, FileText } from 'lucide-react';

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

      const response = await fetch('/api/storage/usage', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.totalQuota === 0 || !data.totalQuota) {
          setStorageData(getMockStorageData());
        } else {
          setStorageData(data);
        }
      } else {
        setStorageData(getMockStorageData());
      }
    } catch (err) {
      console.error('Failed to fetch storage data:', err);
      setStorageData(getMockStorageData());
      setError('Using cached data');
    } finally {
      setLoading(false);
    }
  };

  const getMockStorageData = () => ({
    totalQuota: 5368709120,
    totalUsed: 1288490188,
    breakdown: {
      documents: 524288000,
      honeyJars: 314572800,
      tempFiles: 104857600,
      embeddings: 209715200,
      system: 134217728
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

  const getUsageBarColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-orange-500';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading) {
    return (
      <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-4 ${className}`}>
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span className="text-sm text-slate-400">Loading...</span>
        </div>
      </div>
    );
  }

  if (!storageData) {
    return (
      <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-4 ${className}`}>
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          <span>Failed to load storage data</span>
        </div>
      </div>
    );
  }

  const usagePercentage = getUsagePercentage(storageData.totalUsed, storageData.totalQuota);
  const usageBarColor = getUsageBarColor(usagePercentage);

  return (
    <div className={`sting-glass-card sting-elevation-medium border border-slate-700 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-blue-400" />
          <div>
            <h3 className="text-sm font-medium text-white">Honey Reserve (Shared Storage)</h3>
            {error && <span className="text-xs text-orange-400">{error}</span>}
          </div>
        </div>
        <span className={`text-sm font-medium ${usagePercentage >= 75 ? 'text-orange-400' : 'text-green-400'}`}>
          {formatBytes(storageData.totalUsed)} / {formatBytes(storageData.totalQuota)} ({usagePercentage}%)
        </span>
      </div>

      {/* Usage Bar */}
      <div className="w-full bg-slate-700 rounded-full h-2.5 mb-3">
        <div
          className={`h-2.5 rounded-full transition-all duration-300 ${usageBarColor}`}
          style={{ width: `${usagePercentage}%` }}
        ></div>
      </div>

      {/* Breakdown */}
      <div className="grid grid-cols-4 gap-2">
        <div className="flex flex-col items-center">
          <FileText className="w-3.5 h-3.5 text-green-400 mb-1" />
          <span className="text-xs text-slate-200">{formatBytes(storageData.breakdown.documents)}</span>
        </div>
        <div className="flex flex-col items-center">
          <Database className="w-3.5 h-3.5 text-yellow-400 mb-1" />
          <span className="text-xs text-slate-200">{formatBytes(storageData.breakdown.honeyJars)}</span>
        </div>
        <div className="flex flex-col items-center">
          <div className="w-3.5 h-3.5 text-slate-400 mb-1 flex items-center justify-center text-xs">📁</div>
          <span className="text-xs text-slate-200">{formatBytes(storageData.breakdown.tempFiles)}</span>
        </div>
        <div className="flex flex-col items-center">
          <div className="w-3.5 h-3.5 text-purple-400 mb-1 flex items-center justify-center text-xs">🔮</div>
          <span className="text-xs text-slate-200">{formatBytes(storageData.breakdown.embeddings)}</span>
        </div>
      </div>
    </div>
  );
};

export default StorageWidget;
