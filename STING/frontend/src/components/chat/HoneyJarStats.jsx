import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, Database, Clock, ChevronDown, ChevronUp, Shield, FileText, Loader } from 'lucide-react';
import HoneyIcon from '../icons/HoneyIcon';
import apiClient from '../../utils/apiClient';

/**
 * HoneyJarStats - Quick stats view for honey jar activity
 * Shows recent activity, trends, and usage statistics
 * Supports collapsed/expanded states for space efficiency
 */
const HoneyJarStats = ({ currentHoneyJar, className = '', defaultCollapsed = false }) => {
  const [stats, setStats] = useState(null);
  const [encryptionStats, setEncryptionStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(() => {
    // Load collapsed state from localStorage
    const saved = localStorage.getItem('honeyJarStats_collapsed');
    return saved !== null ? JSON.parse(saved) : defaultCollapsed;
  });

  // Fetch encryption status
  const fetchEncryptionStatus = async () => {
    try {
      const response = await apiClient.get('/api/files/encryption/status');
      if (response.data?.success) {
        setEncryptionStats(response.data.data);
      }
    } catch (error) {
      console.warn('Failed to fetch encryption status:', error);
    }
  };

  // Real data with encryption status
  useEffect(() => {
    if (currentHoneyJar) {
      setLoading(true);
      
      // Fetch encryption status
      fetchEncryptionStatus();
      
      // Simulate honey jar stats - replace with real API when available
      setTimeout(() => {
        setStats({
          documentsCount: 38,
          documentsGrowth: 12,
          avgProcessingTime: 0.8,
          lastUpdated: '2 hours ago'
        });
        
        setRecentActivity([
          { time: '2 min ago', action: 'Upload', detail: 'Document processed & encrypted' },
          { time: '15 min ago', action: 'Query', detail: 'Bee Chat context search' },
          { time: '1 hour ago', action: 'Encrypt', detail: 'User files secured' },
          { time: '3 hours ago', action: 'Backup', detail: 'Honey Reserve maintenance' }
        ]);
        
        setLoading(false);
      }, 500);
    } else {
      setStats(null);
      setRecentActivity([]);
      // Still fetch encryption status for general info
      fetchEncryptionStatus();
    }
  }, [currentHoneyJar]);

  // Toggle collapse state
  const toggleCollapse = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    // Save to localStorage
    localStorage.setItem('honeyJarStats_collapsed', JSON.stringify(newState));
  };

  if (!currentHoneyJar) {
    return (
      <div className={`glass-card p-4 rounded-lg ${className}`}>
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={toggleCollapse}
        >
          <h4 className="text-sm font-medium text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-yellow-400" />
            <HoneyIcon size={16} color="rgb(251 191 36)" />
            Honey Jar Activity
          </h4>
          {isCollapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />}
        </div>
        {!isCollapsed && (
          <p className="text-xs text-gray-400 text-center py-4 mt-2">
            Select a honey jar to view activity stats
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={`glass-card p-4 rounded-lg ${className}`}>
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={toggleCollapse}
      >
        <h4 className="text-sm font-medium text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-yellow-400" />
          <HoneyIcon size={16} color="rgb(251 191 36)" />
          Activity Stats
        </h4>
        {isCollapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />}
      </div>

      {/* Collapsed view - show minimal stats */}
      {isCollapsed && (stats || encryptionStats) && !loading && (
        <div className="mt-2 flex items-center justify-between text-xs">
          {stats ? (
            <>
              <span className="text-gray-400">
                <span className="text-white font-medium">{stats.documentsCount}</span> docs
              </span>
              <span className="text-gray-400">
                <span className="text-white font-medium">{stats.avgProcessingTime}s</span> avg
              </span>
              <span className="text-green-400">+{stats.documentsGrowth}%</span>
            </>
          ) : encryptionStats && (
            <>
              <span className="text-gray-400">
                <Shield className="w-3 h-3 inline mr-1" />
                <span className="text-white font-medium">{encryptionStats.cache_stats?.active_keys || 0}</span> keys
              </span>
              <span className="text-green-400">
                {encryptionStats.encryption_enabled ? 'Secured' : 'Disabled'}
              </span>
            </>
          )}
        </div>
      )}

      {/* Expanded view - show full stats */}
      {!isCollapsed && (loading ? (
        <div className="text-center py-4 mt-2">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-yellow-500 mx-auto"></div>
        </div>
      ) : (
        <>
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-2 mt-2 mb-3">
            {stats ? (
              <>
                <div className="bg-gray-700/50 rounded p-2">
                  <div className="flex items-center justify-between">
                    <FileText className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-green-400">+{stats.documentsGrowth}%</span>
                  </div>
                  <p className="text-lg font-semibold text-white mt-1">{stats.documentsCount}</p>
                  <p className="text-xs text-gray-400">Documents</p>
                </div>
                
                <div className="bg-gray-700/50 rounded p-2">
                  <div className="flex items-center justify-between">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  </div>
                  <p className="text-lg font-semibold text-white mt-1">{stats.avgProcessingTime}s</p>
                  <p className="text-xs text-gray-400">Processing</p>
                </div>
              </>
            ) : encryptionStats && (
              <>
                <div className="bg-gray-700/50 rounded p-2">
                  <div className="flex items-center justify-between">
                    <Shield className="w-3 h-3 text-gray-400" />
                    <span className={`text-xs ${encryptionStats.encryption_enabled ? 'text-green-400' : 'text-red-400'}`}>
                      {encryptionStats.encryption_enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-lg font-semibold text-white mt-1">{encryptionStats.cache_stats?.active_keys || 0}</p>
                  <p className="text-xs text-gray-400">Active Keys</p>
                </div>
                
                <div className="bg-gray-700/50 rounded p-2">
                  <div className="flex items-center justify-between">
                    <Database className="w-3 h-3 text-gray-400" />
                    <Loader className="w-3 h-3 text-blue-400" />
                  </div>
                  <p className="text-lg font-semibold text-white mt-1">{encryptionStats.cache_stats?.total_cached || 0}</p>
                  <p className="text-xs text-gray-400">Cached</p>
                </div>
              </>
            )}
          </div>

          {/* Recent Activity */}
          <div>
            <h5 className="text-xs font-medium text-gray-400 mb-2">Recent Activity</h5>
            <div className="space-y-2">
              {recentActivity.map((activity, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs">
                  <span className="text-gray-500 whitespace-nowrap">{activity.time}</span>
                  <div className="flex-1">
                    <span className="text-yellow-400">{activity.action}:</span>
                    <span className="text-gray-300 ml-1">{activity.detail}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Encryption Status */}
          {encryptionStats && (
            <div className="mt-3 pt-3 border-t border-gray-700">
              <h5 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Encryption Status
              </h5>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Algorithm:</span>
                  <span className="text-white">{encryptionStats.algorithm || 'AES-256-GCM'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Key Derivation:</span>
                  <span className="text-white">{encryptionStats.key_derivation || 'HKDF-SHA256'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Supported Types:</span>
                  <span className="text-white">{encryptionStats.supported_file_types?.length || 6} types</span>
                </div>
              </div>
            </div>
          )}
        </>
      ))}
    </div>
  );
};

export default HoneyJarStats;