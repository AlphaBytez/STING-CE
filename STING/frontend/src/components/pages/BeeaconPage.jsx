import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, XCircle, Clock, Zap, Eye, Shield, Database, Server, Monitor, X, Brain, Cpu, BarChart3, Search } from 'lucide-react';
import { usePageVisibilityInterval } from '../../hooks/usePageVisibilityInterval';
import StatsCard from '../dashboard/StatsCard';
import NativeDashboard from '../dashboard/NativeDashboard';
import axios from 'axios';

const BeeaconPage = () => {
  const [serviceHealth, setServiceHealth] = useState({});
  const [pollenStats, setPollenStats] = useState({
    totalFiltered: 0,
    piiDetected: 0,
    secretsSanitized: 0,
    auditTrail: 0
  });
  const [systemMetrics, setSystemMetrics] = useState({
    uptime: 'Loading...',
    responseTime: 'Loading...',
    throughput: 'Loading...',
    alerts: 0
  });
  const [showHiveMindModal, setShowHiveMindModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Real API integration for service health and metrics - moved outside useEffect for page visibility hook
  const fetchBeeaconData = async () => {
    try {
      setLoading(true);
      
      // Try authenticated endpoints first, fall back to demo data on any failure
      try {
        const statusResponse = await axios.get('/api/beeacon/status', { timeout: 5000 });
        if (statusResponse.data && statusResponse.data.status === 'success') {
          setServiceHealth(statusResponse.data.data.serviceHealth || {});
          setSystemMetrics(statusResponse.data.data.systemMetrics || {});
        }
      } catch (statusErr) {
        console.log('Status endpoint failed, using demo data:', statusErr.message);
        // Use demo data immediately if any error occurs
        setServiceHealth({
          app: { status: 'healthy', uptime: '7d 12h', lastCheck: '30s ago' },
          database: { status: 'healthy', uptime: '7d 12h', lastCheck: '15s ago' },
          kratos: { status: 'healthy', uptime: '7d 10h', lastCheck: '45s ago' },
          vault: { status: 'healthy', uptime: '7d 12h', lastCheck: '60s ago' },
          knowledge: { status: 'healthy', uptime: '6d 8h', lastCheck: '20s ago' },
          chatbot: { status: 'warning', uptime: '2d 14h', lastCheck: '2m ago' },
          loki: { status: 'healthy', uptime: '5d 3h', lastCheck: '10s ago' },
          grafana: { status: 'healthy', uptime: '5d 3h', lastCheck: '25s ago' },
          promtail: { status: 'healthy', uptime: '5d 3h', lastCheck: '35s ago' }
        });
        setSystemMetrics({
          uptime: '99.8%',
          responseTime: '142ms', 
          throughput: '1.2K/min',
          alerts: 3
        });
      }

      // Try authenticated pollen stats first, fall back to demo data on any failure
      try {
        const pollenResponse = await axios.get('/api/beeacon/pollen-filter/stats', { timeout: 5000 });
        if (pollenResponse.data && pollenResponse.data.status === 'success') {
          setPollenStats(pollenResponse.data.data || {});
        }
      } catch (pollenErr) {
        console.log('Pollen stats endpoint failed, using demo data:', pollenErr.message);
        // Use demo data immediately if any error occurs
        setPollenStats({
          totalFiltered: 1247,
          piiDetected: 89,
          secretsSanitized: 156,
          auditTrail: 2403
        });
      }

      setError(null);
    } catch (err) {
      console.error('Error fetching Beeacon data:', err);
      setError('Failed to load monitoring data. Using demo data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBeeaconData(); // Initial load
  }, []);

  // Use page visibility aware interval for auto-refresh - major GPU savings
  usePageVisibilityInterval(fetchBeeaconData, 30000, []);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'border-green-500/30 bg-green-500/10';
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-500/10';
      case 'error':
        return 'border-red-500/30 bg-red-500/10';
      default:
        return 'border-gray-500/30 bg-gray-500/10';
    }
  };

  const ServiceHealthCard = ({ name, service, icon: Icon }) => (
    <div className={`standard-card p-4 rounded-2xl border ${getStatusColor(service.status)}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-amber-400" />
          <h3 className="font-semibold text-white">{name}</h3>
        </div>
        {getStatusIcon(service.status)}
      </div>
      <div className="space-y-2 text-sm text-gray-300">
        <div className="flex justify-between">
          <span>Uptime:</span>
          <span className="text-green-400">{service.uptime}</span>
        </div>
        <div className="flex justify-between">
          <span>Last Check:</span>
          <span className="text-gray-400">{service.lastCheck}</span>
        </div>
      </div>
    </div>
  );

  // Loading state
  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin text-amber-400">
              <Activity className="w-8 h-8" />
            </div>
            <div className="text-white">Loading Beeacon monitoring data...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="text-amber-400 text-3xl flex items-center">
            <Activity className="w-8 h-8" />
            <Monitor className="w-6 h-6 ml-1" />
          </div>
          <h1 className="text-3xl font-bold text-white">Beeacon Monitoring Stack</h1>
          {error && (
            <div className="ml-4 px-3 py-1 bg-yellow-500/20 border border-yellow-500/30 rounded-lg text-yellow-300 text-sm">
              {error}
            </div>
          )}
        </div>
        <p className="text-gray-400">
          Real-time visibility into your STING hive with intelligent log sanitization and observability
        </p>
      </div>
      
      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-6 md:mb-8">
        <StatsCard 
          title="System Uptime" 
          value={systemMetrics.uptime} 
          color="bg-green-100"
          icon={<CheckCircle className="w-5 h-5 text-green-600" />}
        />
        <StatsCard 
          title="Response Time" 
          value={systemMetrics.responseTime} 
          color="bg-blue-100"
          icon={<Zap className="w-5 h-5 text-blue-600" />}
        />
        <StatsCard 
          title="Log Throughput" 
          value={systemMetrics.throughput} 
          color="bg-amber-100"
          icon={<Activity className="w-5 h-5 text-amber-600" />}
        />
        <StatsCard 
          title="Active Alerts" 
          value={systemMetrics.alerts.toString()} 
          color="bg-red-100"
          icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
        />
      </div>

      {/* Service Health Grid */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Server className="w-6 h-6 text-amber-400" />
          Swarm Status
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <ServiceHealthCard name="Application" service={serviceHealth.app || {}} icon={Server} />
          <ServiceHealthCard name="Database" service={serviceHealth.database || {}} icon={Database} />
          <ServiceHealthCard name="Authentication" service={serviceHealth.kratos || {}} icon={Shield} />
          <ServiceHealthCard name="Vault" service={serviceHealth.vault || {}} icon={Shield} />
          <ServiceHealthCard name="Knowledge" service={serviceHealth.knowledge || {}} icon={Database} />
          <ServiceHealthCard name="Bee Chat" service={serviceHealth.chatbot || {}} icon={Monitor} />
          <ServiceHealthCard name="Loki Logs" service={serviceHealth.loki || {}} icon={Activity} />
          <ServiceHealthCard name="Grafana" service={serviceHealth.grafana || {}} icon={Monitor} />
        </div>
      </div>

      {/* Observability Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-8">
        {/* Pollen Filter Status */}
        <div className="standard-card p-6 rounded-2xl">
          <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" />
            Pollen Filter Activity
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Total Items Filtered</span>
              <span className="text-xl font-bold text-amber-400">{pollenStats.totalFiltered}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">PII Detected</span>
              <span className="text-lg font-bold text-red-400">{pollenStats.piiDetected}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Secrets Sanitized</span>
              <span className="text-lg font-bold text-green-400">{pollenStats.secretsSanitized}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Audit Trail Entries</span>
              <span className="text-lg font-bold text-blue-400">{pollenStats.auditTrail}</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-600">
            <button className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold py-2 px-4 rounded-lg transition-colors">
              View Sanitization Report
            </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="standard-card p-6 rounded-2xl">
          <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            Nectar Analysis Tools
          </h3>
          <div className="grid grid-cols-1 gap-3">
            <button 
              onClick={() => window.open('http://localhost:3001', '_blank')}
              className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/20 border border-blue-500/30 hover:bg-blue-500/30 transition-colors text-left"
            >
              <Monitor className="w-5 h-5 text-blue-400" />
              <div>
                <div className="text-white font-medium">Open Grafana Dashboard</div>
                <div className="text-gray-400 text-sm">View system metrics and alerts</div>
              </div>
            </button>
            
            <button 
              onClick={() => window.open('http://localhost:3001/explore?left=%7B%22datasource%22:%22Loki%22,%22queries%22:%5B%7B%22expr%22:%22%7Bservice_name!%3D%5C%22%5C%22%7D%22%7D%5D%7D', '_blank')}
              className="flex items-center gap-3 p-3 rounded-lg bg-green-500/20 border border-green-500/30 hover:bg-green-500/30 transition-colors text-left"
            >
              <Eye className="w-5 h-5 text-green-400" />
              <div>
                <div className="text-white font-medium">Access Loki Logs</div>
                <div className="text-gray-400 text-sm">Search sanitized log entries</div>
              </div>
            </button>
            
            <button 
              onClick={() => alert('Vault audit trail coming soon! Check Grafana dashboard for now.')}
              className="flex items-center gap-3 p-3 rounded-lg bg-purple-500/20 border border-purple-500/30 hover:bg-purple-500/30 transition-colors text-left"
            >
              <Shield className="w-5 h-5 text-purple-400" />
              <div>
                <div className="text-white font-medium">Vault Audit Trail</div>
                <div className="text-gray-400 text-sm">Review sanitization activity</div>
              </div>
            </button>
            
            <button 
              onClick={async () => {
                try {
                  const response = await axios.post('/api/beeacon/health-report');
                  if (response.data.status === 'success') {
                    alert(`Health report generated: ${response.data.data.id}`);
                  }
                } catch (err) {
                  alert('Failed to generate health report. Please try again.');
                }
              }}
              className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/20 border border-amber-500/30 hover:bg-amber-500/30 transition-colors text-left"
            >
              <Activity className="w-5 h-5 text-amber-400" />
              <div>
                <div className="text-white font-medium">Generate Health Report</div>
                <div className="text-gray-400 text-sm">Export system diagnostics</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Activity Feed */}
      <div className="standard-card p-6 rounded-2xl">
        <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-amber-400" />
          Recent Hive Activity
        </h3>
        <div className="space-y-3">
          {[
            { time: '2 minutes ago', action: 'Pollen Filter sanitized 12 log entries', type: 'security', icon: Shield },
            { time: '5 minutes ago', action: 'Grafana dashboard accessed by admin@sting.local', type: 'info', icon: Monitor },
            { time: '8 minutes ago', action: 'Service restart: Knowledge service recovered', type: 'success', icon: CheckCircle },
            { time: '15 minutes ago', action: 'Alert resolved: High CPU usage normalized', type: 'success', icon: CheckCircle },
            { time: '22 minutes ago', action: 'New Vault reference created for database credentials', type: 'security', icon: Shield },
          ].map((activity, index) => {
            const Icon = activity.icon;
            const typeColors = {
              security: 'text-amber-400',
              info: 'text-blue-400',
              success: 'text-green-400',
              warning: 'text-yellow-400'
            };
            
            return (
              <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-gray-800/50">
                <Icon className={`w-4 h-4 ${typeColors[activity.type]}`} />
                <div className="flex-1">
                  <div className="text-white text-sm">{activity.action}</div>
                  <div className="text-gray-400 text-xs">{activity.time}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Future: HiveMind AI Observability Teaser */}
      <div className="mt-8 p-6 rounded-2xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30">
        <div className="flex items-center gap-3 mb-3">
          <div className="text-2xl">🧠</div>
          <h3 className="text-lg font-semibold text-white">HiveMind AI Observability</h3>
          <span className="px-2 py-1 bg-amber-500 text-black text-xs font-bold rounded-full">ENTERPRISE</span>
        </div>
        <p className="text-gray-300 mb-4">
          Unlock AI-powered insights, anomaly detection, and predictive analytics for your STING hive.
        </p>
        <button 
          onClick={() => setShowHiveMindModal(true)}
          className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black font-semibold py-2 px-4 rounded-lg transition-all"
        >
          Learn More About HiveMind
        </button>
      </div>

      {/* Native Dashboards Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <NativeDashboard
          dashboardType="system-overview"
          title="STING System Overview"
          description="High-level system health and performance metrics"
        />
        
        <NativeDashboard
          dashboardType="auth-audit"
          title="Authentication Audit"
          description="Login attempts, failures, and security events"
        />
        
        <NativeDashboard
          dashboardType="knowledge-metrics"
          title="Knowledge Service Metrics"
          description="Honey jar usage, search performance, document processing"
        />
        
        <NativeDashboard
          dashboardType="pii-compliance"
          title="PII Compliance Dashboard"
          description="Data sanitization metrics and compliance tracking"
        />
      </div>

      {/* HiveMind Information Modal */}
      {showHiveMindModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-gray-900 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          {/* Modal Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <div className="text-amber-400 text-2xl flex items-center">
                <Brain className="w-8 h-8" />
                🧠
              </div>
              <h2 className="text-2xl font-bold text-white">HiveMind AI Observability</h2>
            </div>
            <button 
              onClick={() => setShowHiveMindModal(false)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Modal Content */}
          <div className="p-6">
            <div className="grid md:grid-cols-2 gap-8">
              {/* Left Column - Overview */}
              <div>
                <h3 className="text-xl font-bold text-white mb-4">Intelligent STING Observability</h3>
                <p className="text-gray-300 mb-6">
                  HiveMind is STING's next-generation AI-powered observability platform that transforms 
                  raw system data into actionable intelligence for your security operations.
                </p>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Search className="w-5 h-5 text-amber-400 mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="text-white font-semibold">Anomaly Detection</h4>
                      <p className="text-gray-400 text-sm">
                        ML-powered detection of unusual patterns in user behavior, system performance, and security events
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <BarChart3 className="w-5 h-5 text-amber-400 mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="text-white font-semibold">Predictive Analytics</h4>
                      <p className="text-gray-400 text-sm">
                        Forecast system capacity, predict potential security incidents, and optimize resource allocation
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Cpu className="w-5 h-5 text-amber-400 mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="text-white font-semibold">Intelligent Automation</h4>
                      <p className="text-gray-400 text-sm">
                        Auto-scale resources, trigger alerts, and implement response actions based on AI insights
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-amber-400 mt-1 flex-shrink-0" />
                    <div>
                      <h4 className="text-white font-semibold">Privacy-First AI</h4>
                      <p className="text-gray-400 text-sm">
                        All AI processing respects your data sovereignty with local LLM options and PII protection
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column - Technical Details */}
              <div>
                <h3 className="text-xl font-bold text-white mb-4">Technical Architecture</h3>
                
                <div className="bg-gray-800 rounded-lg p-4 mb-6">
                  <h4 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                    <Monitor className="w-4 h-4" />
                    Beeacon Integration
                  </h4>
                  <p className="text-gray-300 text-sm mb-3">
                    HiveMind seamlessly integrates with your existing Beeacon monitoring stack:
                  </p>
                  <ul className="text-gray-400 text-sm space-y-1">
                    <li>• Real-time Grafana dashboard enhancement</li>
                    <li>• Loki log analysis with AI-powered insights</li>
                    <li>• Pollen Filter intelligence for threat detection</li>
                    <li>• Automated alert prioritization and correlation</li>
                  </ul>
                </div>

                <div className="bg-gray-800 rounded-lg p-4 mb-6">
                  <h4 className="text-amber-400 font-semibold mb-2">🧠 AI Capabilities</h4>
                  <ul className="text-gray-400 text-sm space-y-1">
                    <li>• Local LLM support (Ollama, Hugging Face)</li>
                    <li>• External API integration (OpenAI, Anthropic)</li>
                    <li>• Custom model fine-tuning for your environment</li>
                    <li>• Multi-modal analysis (logs, metrics, events)</li>
                    <li>• Natural language query interface</li>
                  </ul>
                </div>

                <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-lg p-4">
                  <h4 className="text-amber-400 font-semibold mb-2">🚀 Coming Soon</h4>
                  <p className="text-gray-300 text-sm">
                    HiveMind is currently in development. Enable observability services below to prepare 
                    your STING deployment for AI-enhanced monitoring capabilities.
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 mt-8 pt-6 border-t border-gray-700">
              <button 
                onClick={() => setShowHiveMindModal(false)}
                className="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black font-semibold py-3 px-6 rounded-lg transition-all"
              >
                Enable Observability Services
              </button>
              <button 
                onClick={() => setShowHiveMindModal(false)}
                className="px-6 py-3 border border-gray-600 text-gray-300 hover:text-white hover:border-gray-500 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
    </div>
  );
};

export default BeeaconPage;