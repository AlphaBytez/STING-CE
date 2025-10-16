import React, { useState, useEffect } from 'react';
import { Zap, Clock, TrendingUp, AlertTriangle } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { usePageVisibilityInterval } from '../../hooks/usePageVisibilityInterval';

const PerformanceMetrics = () => {
  const [metrics, setMetrics] = useState({
    responseTime: [],
    throughput: [],
    errorRate: [],
    activeUsers: 0,
  });
  const [timeRange, setTimeRange] = useState('1h');
  const [loading, setLoading] = useState(true);

  // Generate performance data - moved outside useEffect for page visibility hook
  const generateData = () => {
    const now = Date.now();
    const points = 20;
    const interval = timeRange === '1h' ? 3 : timeRange === '24h' ? 72 : 24; // minutes
    
    const data = Array.from({ length: points }, (_, i) => {
      const time = new Date(now - (points - i - 1) * interval * 60000);
      return {
        time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        responseTime: 50 + Math.random() * 100,
        throughput: 800 + Math.random() * 400,
        errorRate: Math.random() * 5,
      };
    });

    setMetrics({
      responseTime: data,
      throughput: data,
      errorRate: data,
      activeUsers: Math.floor(200 + Math.random() * 100),
    });
    setLoading(false);
  };

  useEffect(() => {
    generateData(); // Initial load
  }, [timeRange]);

  // Use page visibility aware interval for performance data updates - major GPU savings
  usePageVisibilityInterval(generateData, 5000, [timeRange]);

  const getAverageResponseTime = () => {
    if (!metrics.responseTime.length) return 0;
    const sum = metrics.responseTime.reduce((acc, item) => acc + item.responseTime, 0);
    return Math.round(sum / metrics.responseTime.length);
  };

  const getAverageThroughput = () => {
    if (!metrics.throughput.length) return 0;
    const sum = metrics.throughput.reduce((acc, item) => acc + item.throughput, 0);
    return Math.round(sum / metrics.throughput.length);
  };

  if (loading) {
    return (
      <div className="dashboard-card p-6 animate-pulse">
        <div className="h-6 bg-gray-800/50 rounded w-40 mb-6"></div>
        <div className="h-48 bg-gray-800/50 rounded"></div>
      </div>
    );
  }

  return (
    <div className="dashboard-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Zap className="w-6 h-6 text-yellow-400" />
          <h3 className="text-lg font-semibold text-white">Performance Metrics</h3>
        </div>
        <div className="flex gap-2">
          {['1h', '24h', '7d'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                timeRange === range
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  : 'bg-gray-700/50 text-gray-400 hover:text-white'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-gray-400">Avg Response</span>
          </div>
          <p className="text-2xl font-bold text-white">{getAverageResponseTime()}ms</p>
        </div>
        
        <div className="bg-gray-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-xs text-gray-400">Throughput</span>
          </div>
          <p className="text-2xl font-bold text-white">{getAverageThroughput()}/s</p>
        </div>
        
        <div className="bg-gray-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-xs text-gray-400">Error Rate</span>
          </div>
          <p className="text-2xl font-bold text-white">0.5%</p>
        </div>
        
        <div className="bg-gray-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-xs text-gray-400">Active Users</span>
          </div>
          <p className="text-2xl font-bold text-white">{metrics.activeUsers}</p>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={metrics.responseTime}>
            <defs>
              <linearGradient id="colorResponse" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#fbbf24" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="time" 
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1f2937', 
                border: '1px solid #374151',
                borderRadius: '8px'
              }}
              labelStyle={{ color: '#d1d5db' }}
            />
            <Area 
              type="monotone" 
              dataKey="responseTime" 
              stroke="#fbbf24" 
              fillOpacity={1} 
              fill="url(#colorResponse)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PerformanceMetrics;