import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Loader,
  FileText,
  Zap,
  TrendingUp,
  Database,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import './NectarFlow.css';

const NectarFlow = () => {
  const { themeColors } = useTheme();
  const [flowStats, setFlowStats] = useState({
    activeProcessing: 5,
    queueLength: 12,
    completedToday: 47,
    processingRate: 3.2,
    averageTime: 45,
    errorRate: 0.02
  });
  
  const [activeJobs, setActiveJobs] = useState([
    {
      id: '1',
      fileName: 'technical-documentation.pdf',
      fileType: 'PDF',
      status: 'processing',
      progress: 65,
      honeyPot: 'Engineering Docs',
      startTime: new Date(Date.now() - 180000),
      estimatedCompletion: 2
    },
    {
      id: '2',
      fileName: 'research-paper-2025.docx',
      fileType: 'DOCX',
      status: 'chunking',
      progress: 30,
      honeyPot: 'Research Papers',
      startTime: new Date(Date.now() - 60000),
      estimatedCompletion: 4
    },
    {
      id: '3',
      fileName: 'api-reference.md',
      fileType: 'Markdown',
      status: 'embedding',
      progress: 85,
      honeyPot: 'API Documentation',
      startTime: new Date(Date.now() - 240000),
      estimatedCompletion: 1
    }
  ]);

  const [queuedJobs, setQueuedJobs] = useState([
    { id: '4', fileName: 'user-manual.pdf', fileType: 'PDF', honeyPot: 'Product Docs', queuePosition: 1 },
    { id: '5', fileName: 'meeting-notes.txt', fileType: 'TXT', honeyPot: 'Internal Notes', queuePosition: 2 },
    { id: '6', fileName: 'architecture-diagram.html', fileType: 'HTML', honeyPot: 'Technical Specs', queuePosition: 3 }
  ]);

  const [isRefreshing, setIsRefreshing] = useState(false);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveJobs(jobs => 
        jobs.map(job => ({
          ...job,
          progress: Math.min(100, job.progress + Math.random() * 5)
        }))
      );
      
      setFlowStats(stats => ({
        ...stats,
        processingRate: (Math.random() * 2 + 2).toFixed(1),
        activeProcessing: Math.floor(Math.random() * 3) + 3
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'processing': return 'text-blue-400';
      case 'chunking': return 'text-yellow-400';
      case 'embedding': return 'text-purple-400';
      case 'completed': return 'text-green-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'processing': return <Loader className="w-4 h-4 animate-spin" />;
      case 'chunking': return <FileText className="w-4 h-4" />;
      case 'embedding': return <Database className="w-4 h-4" />;
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'error': return <AlertCircle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const formatTime = (date) => {
    const minutes = Math.floor((Date.now() - date) / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  };

  return (
    <div className="nectar-flow-dashboard">
      {/* Header */}
      <div className="nectar-flow-header">
        <div className="flex items-center gap-3">
          <div className="nectar-icon">
            <Zap className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Nectar Flow Monitor</h2>
            <p className="text-sm text-gray-400">Real-time knowledge processing pipeline</p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="refresh-button"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon bg-blue-900/30">
            <Activity className="w-5 h-5 text-blue-400" />
          </div>
          <div className="stat-content">
            <p className="stat-value">{flowStats.activeProcessing}</p>
            <p className="stat-label">Active Jobs</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-yellow-900/30">
            <Clock className="w-5 h-5 text-yellow-400" />
          </div>
          <div className="stat-content">
            <p className="stat-value">{flowStats.queueLength}</p>
            <p className="stat-label">In Queue</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-green-900/30">
            <CheckCircle className="w-5 h-5 text-green-400" />
          </div>
          <div className="stat-content">
            <p className="stat-value">{flowStats.completedToday}</p>
            <p className="stat-label">Completed Today</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-purple-900/30">
            <TrendingUp className="w-5 h-5 text-purple-400" />
          </div>
          <div className="stat-content">
            <p className="stat-value">{flowStats.processingRate}/min</p>
            <p className="stat-label">Processing Rate</p>
          </div>
        </div>
      </div>

      {/* Active Processing */}
      <div className="section-container">
        <h3 className="section-title">
          <span className="flex items-center gap-2">
            <Loader className="w-4 h-4 animate-spin text-blue-400" />
            Active Processing
          </span>
          <span className="text-sm font-normal text-gray-400">
            {activeJobs.length} documents
          </span>
        </h3>

        <div className="jobs-list">
          {activeJobs.map(job => (
            <div key={job.id} className="job-card active">
              <div className="job-header">
                <div className="flex items-center gap-3">
                  <div className={`job-status-icon ${getStatusColor(job.status)}`}>
                    {getStatusIcon(job.status)}
                  </div>
                  <div>
                    <p className="job-filename">{job.fileName}</p>
                    <p className="job-meta">
                      {job.fileType} • {job.honeyPot} • Started {formatTime(job.startTime)}
                    </p>
                  </div>
                </div>
                <span className="job-eta">~{job.estimatedCompletion}m</span>
              </div>
              
              <div className="job-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <span className="progress-text">{Math.round(job.progress)}%</span>
              </div>
              
              <p className="job-status-text">
                Status: <span className={getStatusColor(job.status)}>{job.status}</span>
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Queued Jobs */}
      <div className="section-container">
        <h3 className="section-title">
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-yellow-400" />
            Queued for Processing
          </span>
          <span className="text-sm font-normal text-gray-400">
            {queuedJobs.length} documents waiting
          </span>
        </h3>

        <div className="jobs-list">
          {queuedJobs.map(job => (
            <div key={job.id} className="job-card queued">
              <div className="queue-position">#{job.queuePosition}</div>
              <div className="job-info">
                <p className="job-filename">{job.fileName}</p>
                <p className="job-meta">{job.fileType} • {job.honeyPot}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </div>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="metrics-footer">
        <div className="metric">
          <span className="metric-label">Avg. Processing Time:</span>
          <span className="metric-value">{flowStats.averageTime}s</span>
        </div>
        <div className="metric">
          <span className="metric-label">Error Rate:</span>
          <span className="metric-value text-green-400">{(flowStats.errorRate * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
};

export default NectarFlow;