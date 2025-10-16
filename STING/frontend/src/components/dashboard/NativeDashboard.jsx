import React, { useState, useEffect } from 'react';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Activity, Shield, Users, Database, Zap, AlertTriangle } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const NativeDashboard = ({ dashboardType, title, description }) => {
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardMetrics(dashboardType);
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchDashboardMetrics(dashboardType);
    }, 30000);
    
    return () => clearInterval(interval);
  }, [dashboardType]);

  const fetchDashboardMetrics = async (type) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/metrics/dashboard/${type}`);
      
      if (response.ok) {
        const data = await response.json();
        setMetrics(data.data || {});
        setError(null);
      } else {
        // Fallback to demo data if API not available
        setMetrics(getDemoData(type));
        setError('Using demo data - metrics API not available');
      }
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
      setMetrics(getDemoData(type));
      setError('Using demo data - unable to connect to metrics service');
    } finally {
      setLoading(false);
    }
  };

  const getDemoData = (type) => {
    const demoData = {
      'system-overview': {
        uptime: 99.8,
        memory_usage: 67.5,
        cpu_usage: 23.2,
        api_requests: [150, 200, 180, 220, 190, 240, 210],
        response_time: [120, 115, 130, 125, 118, 140, 122],
        active_sessions: 42,
        service_health: {
          app: 'healthy',
          database: 'healthy', 
          vault: 'healthy',
          kratos: 'healthy',
          knowledge: 'warning',
          chatbot: 'healthy'
        }
      },
      'auth-audit': {
        successful_logins: [45, 52, 38, 67, 41, 59, 48],
        failed_logins: [3, 7, 2, 12, 5, 8, 4],
        auth_methods: {
          password: 35,
          webauthn: 28,
          magic_link: 37
        },
        security_events: [
          { type: 'Suspicious Login', count: 3, severity: 'medium' },
          { type: 'Rate Limited', count: 12, severity: 'low' },
          { type: 'Invalid Token', count: 7, severity: 'medium' }
        ]
      },
      'pii-compliance': {
        pii_detected: [12, 8, 15, 22, 18, 11, 9],
        sanitization_rate: 98.7,
        compliance_scores: {
          gdpr: 94,
          hipaa: 91,
          ccpa: 96
        },
        sanitized_items: {
          logs: 156,
          files: 43,
          reports: 28
        }
      },
      'knowledge-metrics': {
        document_count: 1247,
        search_queries: [34, 42, 28, 51, 39, 45, 37],
        honey_jar_usage: {
          active: 8,
          total: 12,
          storage_used: 67.3
        },
        processing_time: [340, 280, 420, 310, 390, 260, 350]
      }
    };
    
    return demoData[type] || {};
  };

  // Common chart options with STING theme
  const getChartOptions = (type = 'default') => {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { 
            color: '#f1f5f9',
            font: { size: 12 }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fbbf24',
          bodyColor: '#f1f5f9',
          borderColor: '#fbbf24',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { 
            color: '#94a3b8',
            font: { size: 11 }
          },
          grid: { 
            color: 'rgba(148, 163, 184, 0.1)'
          }
        },
        y: {
          ticks: { 
            color: '#94a3b8',
            font: { size: 11 }
          },
          grid: { 
            color: 'rgba(148, 163, 184, 0.1)'
          }
        }
      }
    };

    if (type === 'doughnut') {
      delete baseOptions.scales;
    }

    return baseOptions;
  };

  const renderDashboard = () => {
    switch (dashboardType) {
      case 'system-overview':
        return <SystemOverviewDashboard metrics={metrics} chartOptions={getChartOptions()} getChartOptions={getChartOptions} />;
      case 'auth-audit':
        return <AuthAuditDashboard metrics={metrics} chartOptions={getChartOptions()} getChartOptions={getChartOptions} />;
      case 'pii-compliance':
        return <PIIComplianceDashboard metrics={metrics} chartOptions={getChartOptions()} getChartOptions={getChartOptions} />;
      case 'knowledge-metrics':
        return <KnowledgeMetricsDashboard metrics={metrics} chartOptions={getChartOptions()} getChartOptions={getChartOptions} />;
      default:
        return <GenericDashboard metrics={metrics} chartOptions={getChartOptions()} getChartOptions={getChartOptions} />;
    }
  };

  if (loading) {
    return (
      <div className="dashboard-card p-6 rounded-2xl">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <Activity className="w-6 h-6 text-amber-400 animate-pulse" />
            <span className="text-gray-400">Loading dashboard metrics...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Dashboard Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          {description && (
            <p className="text-gray-400 text-sm mt-1">{description}</p>
          )}
        </div>
        {error && (
          <div className="px-3 py-1 bg-yellow-500/20 border border-yellow-500/30 rounded-lg text-yellow-300 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Dashboard Content */}
      {renderDashboard()}
    </div>
  );
};

// System Overview Dashboard Component
const SystemOverviewDashboard = ({ metrics, chartOptions }) => {
  const timeLabels = ['6h ago', '5h ago', '4h ago', '3h ago', '2h ago', '1h ago', 'Now'];
  
  const requestsData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'API Requests',
        data: metrics.api_requests || [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#fbbf24',
        backgroundColor: 'rgba(251, 191, 36, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  const responseTimeData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'Response Time (ms)',
        data: metrics.response_time || [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6, 182, 212, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      {/* System Health Gauges */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-amber-400" />
          System Health
        </h3>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-300">System Uptime</span>
              <span className="text-green-400">{metrics.uptime || 0}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-green-400 h-2 rounded-full" 
                style={{ width: `${metrics.uptime || 0}%` }}
              ></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-300">Memory Usage</span>
              <span className="text-blue-400">{metrics.memory_usage || 0}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-blue-400 h-2 rounded-full" 
                style={{ width: `${metrics.memory_usage || 0}%` }}
              ></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-300">CPU Usage</span>
              <span className="text-amber-400">{metrics.cpu_usage || 0}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-amber-400 h-2 rounded-full" 
                style={{ width: `${metrics.cpu_usage || 0}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* API Requests Chart */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-400" />
          Request Volume
        </h3>
        <div className="h-48">
          <Line data={requestsData} options={chartOptions} />
        </div>
      </div>

      {/* Service Status */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-amber-400" />
          Service Status
        </h3>
        <div className="space-y-3">
          {Object.entries(metrics.service_health || {}).map(([service, status]) => (
            <div key={service} className="flex items-center justify-between">
              <span className="text-gray-300 capitalize">{service}</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                status === 'healthy' ? 'bg-green-500/20 text-green-400' :
                status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Response Time Chart */}
      <div className="dashboard-card p-6 rounded-2xl lg:col-span-2">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-amber-400" />
          Response Time Trends
        </h3>
        <div className="h-48">
          <Line data={responseTimeData} options={chartOptions} />
        </div>
      </div>

      {/* Active Sessions */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-amber-400" />
          Active Users
        </h3>
        <div className="text-center">
          <div className="text-3xl font-bold text-amber-400 mb-2">
            {metrics.active_sessions || 0}
          </div>
          <div className="text-gray-400 text-sm">Current Sessions</div>
        </div>
      </div>
    </div>
  );
};

// Auth Audit Dashboard Component
const AuthAuditDashboard = ({ metrics, chartOptions, getChartOptions }) => {
  const timeLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  const loginData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'Successful Logins',
        data: metrics.successful_logins || [0, 0, 0, 0, 0, 0, 0],
        backgroundColor: 'rgba(34, 197, 94, 0.8)',
        borderColor: '#22c55e',
        borderWidth: 1
      },
      {
        label: 'Failed Logins',
        data: metrics.failed_logins || [0, 0, 0, 0, 0, 0, 0],
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderColor: '#ef4444',
        borderWidth: 1
      }
    ]
  };

  const authMethodsData = {
    labels: ['Password', 'WebAuthn', 'Magic Link'],
    datasets: [
      {
        data: Object.values(metrics.auth_methods || { password: 0, webauthn: 0, magic_link: 0 }),
        backgroundColor: [
          'rgba(251, 191, 36, 0.8)',
          'rgba(139, 92, 246, 0.8)', 
          'rgba(6, 182, 212, 0.8)'
        ],
        borderColor: [
          '#fbbf24',
          '#8b5cf6',
          '#06b6d4'
        ],
        borderWidth: 2
      }
    ]
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Login Activity */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          Login Activity
        </h3>
        <div className="h-64">
          <Bar data={loginData} options={chartOptions} />
        </div>
      </div>

      {/* Authentication Methods */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-amber-400" />
          Authentication Methods
        </h3>
        <div className="h-64">
          <Doughnut data={authMethodsData} options={getChartOptions('doughnut')} />
        </div>
      </div>

      {/* Security Events */}
      <div className="dashboard-card p-6 rounded-2xl lg:col-span-2">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Security Events
        </h3>
        <div className="space-y-3">
          {(metrics.security_events || []).map((event, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center gap-3">
                <AlertTriangle className={`w-4 h-4 ${
                  event.severity === 'high' ? 'text-red-400' :
                  event.severity === 'medium' ? 'text-yellow-400' :
                  'text-blue-400'
                }`} />
                <span className="text-white">{event.type}</span>
              </div>
              <span className="text-gray-400">{event.count} incidents</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// PII Compliance Dashboard Component  
const PIIComplianceDashboard = ({ metrics, chartOptions }) => {
  const timeLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  const piiDetectionData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'PII Detected',
        data: metrics.pii_detected || [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      {/* PII Detection Trends */}
      <div className="dashboard-card p-6 rounded-2xl lg:col-span-2">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          PII Detection Trends
        </h3>
        <div className="h-48">
          <Line data={piiDetectionData} options={chartOptions} />
        </div>
      </div>

      {/* Compliance Scores */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          Compliance Scores
        </h3>
        <div className="space-y-4">
          {Object.entries(metrics.compliance_scores || {}).map(([framework, score]) => (
            <div key={framework}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300 uppercase">{framework}</span>
                <span className="text-green-400">{score}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-green-400 h-2 rounded-full" 
                  style={{ width: `${score}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sanitization Summary */}
      <div className="dashboard-card p-6 rounded-2xl lg:col-span-3">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-amber-400" />
          Data Sanitization Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(metrics.sanitized_items || {}).map(([type, count]) => (
            <div key={type} className="text-center p-4 bg-gray-800/50 rounded-lg">
              <div className="text-2xl font-bold text-amber-400 mb-1">{count}</div>
              <div className="text-gray-400 text-sm capitalize">Sanitized {type}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Knowledge Metrics Dashboard Component
const KnowledgeMetricsDashboard = ({ metrics, chartOptions }) => {
  const timeLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  const searchData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'Search Queries',
        data: metrics.search_queries || [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6, 182, 212, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Document Statistics */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-amber-400" />
          Knowledge Base Stats
        </h3>
        <div className="space-y-4">
          <div className="text-center p-4 bg-gray-800/50 rounded-lg">
            <div className="text-3xl font-bold text-amber-400 mb-1">
              {metrics.document_count || 0}
            </div>
            <div className="text-gray-400 text-sm">Total Documents</div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-gray-800/50 rounded-lg">
              <div className="text-xl font-bold text-green-400 mb-1">
                {metrics.honey_jar_usage?.active || 0}
              </div>
              <div className="text-gray-400 text-xs">Active Jars</div>
            </div>
            <div className="text-center p-3 bg-gray-800/50 rounded-lg">
              <div className="text-xl font-bold text-blue-400 mb-1">
                {metrics.honey_jar_usage?.storage_used || 0}%
              </div>
              <div className="text-gray-400 text-xs">Storage Used</div>
            </div>
          </div>
        </div>
      </div>

      {/* Search Activity */}
      <div className="dashboard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-amber-400" />
          Search Activity
        </h3>
        <div className="h-48">
          <Line data={searchData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
};

// Generic Dashboard Component
const GenericDashboard = ({ metrics, chartOptions }) => (
  <div className="dashboard-card p-6 rounded-2xl">
    <div className="text-center py-12">
      <Activity className="w-16 h-16 text-gray-500 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-300 mb-2">Dashboard Coming Soon</h3>
      <p className="text-gray-500">This dashboard is being developed.</p>
    </div>
  </div>
);

export default NativeDashboard;