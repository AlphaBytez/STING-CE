import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Shield,
  AlertCircle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Database,
  Activity
} from 'lucide-react';
import axios from 'axios';

const PIIMonitorDashboard = () => {
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchDiagnostics();

    if (autoRefresh) {
      const interval = setInterval(fetchDiagnostics, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchDiagnostics = async () => {
    try {
      const response = await axios.get('/api/pii/diagnostics');
      setDiagnostics(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch PII diagnostics');
      console.error('PII diagnostics error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-500';
      case 'degraded': return 'text-yellow-500';
      case 'unhealthy': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5" />;
      case 'degraded': return <AlertCircle className="w-5 h-5" />;
      case 'unhealthy': return <XCircle className="w-5 h-5" />;
      default: return <Activity className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-6 h-6 animate-spin" />
        <span className="ml-2">Loading PII diagnostics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  const cacheStats = diagnostics?.diagnostics?.cache_diagnostics?.cache_stats || {};
  const hitRate = diagnostics?.hit_rate || 0;
  const activeConversations = diagnostics?.diagnostics?.active_conversations || 0;
  const recommendations = diagnostics?.recommendations || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Shield className="w-6 h-6 text-blue-500" />
          <h2 className="text-2xl font-bold">PII Protection Monitor</h2>
        </div>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Auto-refresh</span>
          </label>
          <button
            onClick={fetchDiagnostics}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Health Status */}
            <div className="flex items-center space-x-3">
              <div className={getHealthColor(diagnostics?.status)}>
                {getHealthIcon(diagnostics?.status)}
              </div>
              <div>
                <p className="text-sm text-gray-500">Overall Health</p>
                <p className="text-lg font-semibold capitalize">{diagnostics?.status || 'Unknown'}</p>
              </div>
            </div>

            {/* Hit Rate */}
            <div>
              <p className="text-sm text-gray-500">Cache Hit Rate</p>
              <div className="flex items-center space-x-2 mt-1">
                <Progress value={hitRate * 100} className="flex-1" />
                <span className="text-lg font-semibold">{(hitRate * 100).toFixed(1)}%</span>
              </div>
            </div>

            {/* Active Conversations */}
            <div>
              <p className="text-sm text-gray-500">Active Conversations</p>
              <p className="text-lg font-semibold">{activeConversations}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cache Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Cache Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Hits</span>
                <TrendingUp className="w-4 h-4 text-green-500" />
              </div>
              <p className="text-2xl font-bold text-green-600">{cacheStats.hits || 0}</p>
            </div>

            <div className="bg-red-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Misses</span>
                <TrendingDown className="w-4 h-4 text-red-500" />
              </div>
              <p className="text-2xl font-bold text-red-600">{cacheStats.misses || 0}</p>
            </div>

            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Errors</span>
                <AlertCircle className="w-4 h-4 text-yellow-500" />
              </div>
              <p className="text-2xl font-bold text-yellow-600">{cacheStats.errors || 0}</p>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Fallback Used</span>
                <Database className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-bold text-blue-600">{cacheStats.fallback_used || 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Redis Connection Status */}
      <Card>
        <CardHeader>
          <CardTitle>Redis Connection</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-3">
            <div className={diagnostics?.diagnostics?.cache_diagnostics?.redis_connected ?
              'text-green-500' : 'text-red-500'}>
              {diagnostics?.diagnostics?.cache_diagnostics?.redis_connected ?
                <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
            </div>
            <span>
              Redis is {diagnostics?.diagnostics?.cache_diagnostics?.redis_connected ?
                'connected' : 'disconnected'}
            </span>
            {diagnostics?.diagnostics?.cache_diagnostics?.reconnect_attempts > 0 && (
              <Badge variant="outline">
                {diagnostics.diagnostics.cache_diagnostics.reconnect_attempts} reconnect attempts
              </Badge>
            )}
          </div>

          {diagnostics?.diagnostics?.cache_diagnostics?.local_cache_size > 0 && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm">
                Local cache active with {diagnostics.diagnostics.cache_diagnostics.local_cache_size} entries
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>System Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recommendations.map((recommendation, index) => (
                <Alert key={index} variant="warning">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{recommendation}</AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Last Error */}
      {cacheStats.last_error && (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">Last Error</CardTitle>
          </CardHeader>
          <CardContent>
            <code className="text-sm bg-red-50 p-2 rounded block overflow-x-auto">
              {cacheStats.last_error}
            </code>
          </CardContent>
        </Card>
      )}

      {/* Configuration Info */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">PII Protection:</span>
              <Badge variant={diagnostics?.diagnostics?.enabled ? 'success' : 'secondary'} className="ml-2">
                {diagnostics?.diagnostics?.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <div>
              <span className="text-gray-500">Protection Mode:</span>
              <span className="ml-2 font-medium">External (Strict)</span>
            </div>
            <div>
              <span className="text-gray-500">Cache TTL:</span>
              <span className="ml-2 font-medium">5 minutes (default)</span>
            </div>
            <div>
              <span className="text-gray-500">Error TTL:</span>
              <span className="ml-2 font-medium">1 hour (extended)</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PIIMonitorDashboard;