import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Spin, Modal, Input, Select, Progress } from 'antd';
import {
  FileTextOutlined,
  PlusOutlined,
  FilterOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  DownloadOutlined,
  EyeOutlined,
  ShareAltOutlined,
  ShoppingCartOutlined,
} from '@ant-design/icons';
import reportApi from '../../../services/reportApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Status filter options
 */
const STATUS_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'queued', label: 'Queued' },
  { key: 'processing', label: 'Processing' },
  { key: 'completed', label: 'Completed' },
  { key: 'failed', label: 'Failed' },
];

/**
 * Get status badge configuration
 */
const getStatusConfig = (status) => {
  switch (status) {
    case 'completed':
      return {
        icon: <CheckCircleOutlined />,
        color: '#52c41a',
        label: 'Completed',
      };
    case 'failed':
      return {
        icon: <ExclamationCircleOutlined />,
        color: '#ff4d4f',
        label: 'Failed',
      };
    case 'queued':
      return {
        icon: <ClockCircleOutlined />,
        color: '#faad14',
        label: 'Queued',
      };
    case 'processing':
    case 'generating':
    case 'pending':
    default:
      return {
        icon: <LoadingOutlined />,
        color: '#1890ff',
        label: status === 'pending' ? 'Pending' : 'Processing',
      };
  }
};

/**
 * Get type color for badges
 */
const getTypeColor = (type) => {
  switch (type) {
    case 'security': return '#ff4d4f';
    case 'analytics': return '#1890ff';
    case 'compliance': return '#722ed1';
    case 'performance': return '#52c41a';
    case 'storage': return '#fa8c16';
    default: return '#8c8c8c';
  }
};

/**
 * Format date for display
 */
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

/**
 * Format file size
 */
const formatFileSize = (bytes) => {
  if (!bytes) return null;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

/**
 * MobileReports - Mobile reports list page
 * Full parity with desktop BeeReportsPage
 */
const MobileReports = () => {
  const navigate = useNavigate();
  const { user, identity } = useUnifiedAuth();

  // State - matching desktop BeeReportsPage
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reports, setReports] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [reportQueue, setReportQueue] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingReport, setCreatingReport] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [basketAddedReports, setBasketAddedReports] = useState(new Set());
  const [showTemplates, setShowTemplates] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  });

  // Load templates - same as desktop
  const loadTemplates = useCallback(async () => {
    try {
      const response = await reportApi.getTemplates();
      if (response.success && response.data?.templates) {
        setTemplates(response.data.templates);
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  }, []);

  // Load reports - same as desktop BeeReportsPage
  const loadReports = useCallback(async (page = 1, pageSize = 20) => {
    try {
      const offset = (page - 1) * pageSize;
      const params = {
        limit: pageSize,
        offset,
        status: statusFilter === 'all' ? undefined : statusFilter
      };
      
      const response = await reportApi.listReports(params);
      
      if (response.success && response.data?.reports) {
        setReports(response.data.reports);
        setPagination({
          current: page,
          pageSize,
          total: response.data.pagination?.total || response.data.reports.length
        });
      } else {
        setReports([]);
        setPagination({ current: 1, pageSize, total: 0 });
      }
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      setReports([]);
    }
  }, [statusFilter]);

  // Load queue status - same as desktop
  const loadQueueStatus = useCallback(async () => {
    try {
      const response = await reportApi.getQueueStatus();
      if (response.success && response.data) {
        setQueueStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to load queue status:', error);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([loadTemplates(), loadReports(), loadQueueStatus()]);
      setLoading(false);
    };
    loadAll();
  }, []);

  // Reload when filters change
  useEffect(() => {
    if (!loading) {
      loadReports();
    }
  }, [statusFilter]);

  // Update report queue when reports change
  useEffect(() => {
    const queue = reports.filter(r => 
      ['pending', 'queued', 'processing'].includes(r.status)
    );
    setReportQueue(queue);
  }, [reports]);

  // Smart polling for active reports - same as desktop
  useEffect(() => {
    const hasProcessing = reportQueue.some(r => r.status === 'processing');
    const hasQueued = reportQueue.some(r => ['pending', 'queued'].includes(r.status));
    
    if (!hasProcessing && !hasQueued) return;
    
    const interval = hasProcessing ? 3000 : 10000;
    const pollInterval = setInterval(() => {
      loadReports(pagination.current, pagination.pageSize);
    }, interval);
    
    return () => clearInterval(pollInterval);
  }, [reportQueue, pagination.current, pagination.pageSize]);

  // Handle report click - view details
  const handleReportClick = (report) => {
    if (['pending', 'queued', 'processing'].includes(report.status)) {
      message.info('Report is still generating. Please wait...');
      return;
    }
    navigate(`/m/reports/${report.id}`);
  };

  // Handle generate report from template - same as desktop
  const handleGenerateReport = async (template) => {
    try {
      setCreatingReport(true);
      const response = await reportApi.generateReport(template.id, {
        title: `${template.display_name || template.name} - ${new Date().toLocaleDateString()}`,
        description: template.description
      });

      if (response.success) {
        message.success('Report queued for generation');
        setShowCreateModal(false);
        setSelectedTemplate(null);
        await loadReports(1, pagination.pageSize);
      }
    } catch (error) {
      console.error('Failed to generate report:', error);
      message.error('Failed to generate report');
    } finally {
      setCreatingReport(false);
    }
  };

  // Handle download report - same as desktop
  const handleDownload = async (e, report) => {
    e.stopPropagation();
    try {
      await reportApi.downloadReport(report.id);
      message.success('Report downloaded successfully');
      // Update local state with new download count
      setReports(prev =>
        prev.map(r =>
          r.id === report.id
            ? { ...r, download_count: (r.download_count || 0) + 1 }
            : r
        )
      );
    } catch (error) {
      console.error('Failed to download report:', error);
      message.error('Failed to download report');
    }
  };

  // Handle add to basket - same as desktop
  const handleAddToBasket = async (e, report) => {
    e.stopPropagation();
    try {
      const timestamp = new Date(report.created_at).toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const sanitizedTitle = (report.title || 'report').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30);
      const filename = `${sanitizedTitle}_${timestamp}.md`;

      const reportContent = `# ${report.title}

**Generated:** ${new Date(report.created_at).toLocaleString()}
**Status:** ${report.status}
**Type:** ${report.template?.category || 'analytics'}

## Description
${report.description || 'No description provided'}

## Report Details
- **Report ID:** ${report.id}
- **Template:** ${report.template?.name || 'Unknown'}
- **File Size:** ${report.result_size_bytes ? formatFileSize(report.result_size_bytes) : 'N/A'}
- **Downloads:** ${report.download_count || 0}

---
*This report was exported to your Basket from Report Bee.*
`;

      const response = await fetch('/api/basket/add-report', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename,
          content: reportContent,
          content_type: 'text/markdown',
          metadata: {
            source: 'mobile_reports_page',
            report_id: report.id,
            report_title: report.title,
            exported_at: new Date().toISOString()
          }
        })
      });

      setBasketAddedReports(prev => new Set([...prev, report.id]));
      message.success(response.ok ? 'Report added to Basket' : 'Report marked for export');
    } catch (error) {
      console.error('Error adding report to basket:', error);
      setBasketAddedReports(prev => new Set([...prev, report.id]));
      message.info('Report marked for export');
    }
  };

  // Handle cancel report - same as desktop
  const handleCancel = async (e, reportId) => {
    e.stopPropagation();
    try {
      const response = await reportApi.cancelReport(reportId);
      if (response.success) {
        message.success('Report cancelled');
        await loadReports(pagination.current, pagination.pageSize);
      }
    } catch (error) {
      console.error('Failed to cancel report:', error);
      message.error('Failed to cancel report');
    }
  };

  // Handle retry failed report - same as desktop
  const handleRetry = async (e, reportId) => {
    e.stopPropagation();
    try {
      const response = await reportApi.retryReport(reportId);
      if (response.success) {
        message.success('Report queued for retry');
        await loadReports(pagination.current, pagination.pageSize);
      }
    } catch (error) {
      console.error('Failed to retry report:', error);
      message.error('Failed to retry report');
    }
  };

  // Handle refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadTemplates(), loadReports(), loadQueueStatus()]);
    setRefreshing(false);
    message.success('Data refreshed');
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div style={{ padding: '0', minHeight: '100%', paddingBottom: '80px' }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '16px' 
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: '#f1f5f9' }}>Report Bee</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
            Generate and manage reports
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            background: '#2a3142',
            border: '1px solid #3a4356',
            borderRadius: '8px',
            padding: '8px',
            color: refreshing ? '#64748b' : '#f1f5f9',
            cursor: refreshing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-label="Refresh reports"
        >
          <ReloadOutlined spin={refreshing} />
        </button>
      </div>

      {/* Queue Status Banner - same as desktop */}
      {queueStatus && (queueStatus.currently_processing > 0 || queueStatus.pending_reports > 0) && (
        <div style={{
          background: 'rgba(234, 179, 8, 0.1)',
          border: '1px solid rgba(234, 179, 8, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <LoadingOutlined style={{ color: '#eab308' }} />
          <span style={{ color: 'rgba(234, 179, 8, 0.8)', fontSize: '13px' }}>
            {queueStatus.currently_processing > 0 && (
              <>{queueStatus.currently_processing} report{queueStatus.currently_processing > 1 ? 's' : ''} generating</>
            )}
            {queueStatus.currently_processing > 0 && queueStatus.pending_reports > 0 && ' • '}
            {queueStatus.pending_reports > 0 && (
              <>{queueStatus.pending_reports} in queue</>
            )}
          </span>
        </div>
      )}

      {/* In Progress Queue - if any */}
      {reportQueue.length > 0 && (
        <div style={{
          background: '#2a3142',
          borderRadius: '12px',
          border: '1px solid #3a4356',
          padding: '16px',
          marginBottom: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <ClockCircleOutlined style={{ color: '#eab308' }} />
            <span style={{ fontWeight: 600, color: '#f1f5f9' }}>In Progress</span>
            <span style={{ 
              background: '#eab308', 
              color: '#1a1f2e', 
              padding: '2px 8px', 
              borderRadius: '10px', 
              fontSize: '11px',
              fontWeight: 600 
            }}>
              {reportQueue.length}
            </span>
          </div>
          {reportQueue.map((report) => (
            <div key={report.id} style={{
              background: '#1a1f2e',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '8px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: '#f1f5f9', fontSize: '13px', fontWeight: 500 }}>{report.title}</span>
                <span style={{ 
                  color: getStatusConfig(report.status).color, 
                  fontSize: '11px',
                  background: `${getStatusConfig(report.status).color}20`,
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}>
                  {report.status}
                </span>
              </div>
              {report.status === 'processing' && (
                <>
                  {report.status_message && (
                    <p style={{ color: '#94a3b8', fontSize: '11px', margin: '0 0 8px 0', fontStyle: 'italic' }}>
                      {report.status_message}
                    </p>
                  )}
                  <Progress 
                    percent={report.progress_percentage || 5} 
                    size="small" 
                    status="active"
                    strokeColor={{ '0%': '#f59e0b', '100%': '#10b981' }}
                    trailColor="#374151"
                  />
                </>
              )}
              <button
                onClick={(e) => handleCancel(e, report.id)}
                style={{
                  marginTop: '8px',
                  padding: '4px 12px',
                  background: 'transparent',
                  border: '1px solid #ef4444',
                  borderRadius: '4px',
                  color: '#ef4444',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Status Filters - Horizontal scroll */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ 
          display: 'flex', 
          gap: '8px', 
          overflowX: 'auto', 
          WebkitOverflowScrolling: 'touch',
          paddingBottom: '4px',
          msOverflowStyle: 'none',
          scrollbarWidth: 'none',
        }}>
          {STATUS_FILTERS.map((filter) => {
            const count = reports.filter(r => {
              if (filter.key === 'all') return true;
              return r.status === filter.key;
            }).length;
            const isActive = statusFilter === filter.key;
            
            return (
              <button
                key={filter.key}
                onClick={() => setStatusFilter(filter.key)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '20px',
                  border: 'none',
                  background: isActive ? '#eab308' : '#2a3142',
                  color: isActive ? '#1a1f2e' : '#94a3b8',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {filter.label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Reports List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {reports.length > 0 ? (
          reports.map((report) => {
            const statusConfig = getStatusConfig(report.status);
            const isCompleted = report.status === 'completed';
            const hasFile = isCompleted && report.result_file_id;
            const isInQueue = ['pending', 'queued', 'processing'].includes(report.status);
            
            return (
              <div
                key={report.id}
                onClick={() => handleReportClick(report)}
                style={{
                  padding: '16px',
                  background: '#2a3142',
                  borderRadius: '12px',
                  border: '1px solid #3a4356',
                  cursor: isInQueue ? 'default' : 'pointer',
                  opacity: isInQueue ? 0.9 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  {/* Icon */}
                  <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '8px',
                    background: '#1a1f2e',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <FileTextOutlined style={{ fontSize: '20px', color: '#eab308' }} />
                  </div>
                  
                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Title and Status */}
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'flex-start', 
                      gap: '8px',
                      marginBottom: '6px',
                    }}>
                      <h3 style={{
                        margin: 0,
                        fontSize: '14px',
                        fontWeight: 500,
                        color: '#f1f5f9',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1,
                      }}>
                        {report.title}
                      </h3>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        color: statusConfig.color,
                        background: `${statusConfig.color}20`,
                        padding: '3px 8px',
                        borderRadius: '12px',
                        flexShrink: 0,
                        fontWeight: 500,
                      }}>
                        {statusConfig.icon}
                        {statusConfig.label}
                      </span>
                    </div>
                    
                    {/* Meta info */}
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '6px',
                      fontSize: '12px',
                      color: '#94a3b8',
                      marginBottom: '8px',
                    }}>
                      {report.template?.category && (
                        <span style={{
                          background: `${getTypeColor(report.template.category)}20`,
                          color: getTypeColor(report.template.category),
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                        }}>
                          {report.template.category}
                        </span>
                      )}
                      <span>{formatDate(report.created_at)}</span>
                      {report.result_size_bytes && (
                        <span>• {formatFileSize(report.result_size_bytes)}</span>
                      )}
                    </div>
                    
                    {/* Progress bar for processing */}
                    {report.status === 'processing' && report.progress_percentage > 0 && (
                      <div style={{ marginBottom: '8px' }}>
                        <Progress 
                          percent={report.progress_percentage} 
                          size="small" 
                          status="active"
                          strokeColor={{ '0%': '#f59e0b', '100%': '#10b981' }}
                          trailColor="#374151"
                          showInfo={false}
                        />
                      </div>
                    )}
                    
                    {/* Error message if failed */}
                    {report.status === 'failed' && report.error_message && (
                      <div style={{ 
                        fontSize: '12px', 
                        color: '#ef4444', 
                        marginBottom: '8px',
                        padding: '8px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderRadius: '6px',
                      }}>
                        {report.error_message}
                      </div>
                    )}
                    
                    {/* Action buttons - same as desktop */}
                    <div style={{ 
                      display: 'flex', 
                      gap: '8px', 
                      marginTop: '4px',
                      flexWrap: 'wrap',
                    }}>
                      {hasFile && (
                        <>
                          <button
                            onClick={(e) => { e.stopPropagation(); navigate(`/m/reports/${report.id}`); }}
                            style={{
                              padding: '6px 12px',
                              background: 'transparent',
                              border: '1px solid #3a4356',
                              borderRadius: '6px',
                              color: '#94a3b8',
                              fontSize: '12px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <EyeOutlined /> View
                          </button>
                          <button
                            onClick={(e) => handleDownload(e, report)}
                            style={{
                              padding: '6px 12px',
                              background: 'transparent',
                              border: '1px solid #3a4356',
                              borderRadius: '6px',
                              color: '#52c41a',
                              fontSize: '12px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <DownloadOutlined /> {report.download_count || 0}
                          </button>
                          <button
                            onClick={(e) => handleAddToBasket(e, report)}
                            disabled={basketAddedReports.has(report.id)}
                            style={{
                              padding: '6px 12px',
                              background: 'transparent',
                              border: '1px solid #3a4356',
                              borderRadius: '6px',
                              color: basketAddedReports.has(report.id) ? '#52c41a' : '#f59e0b',
                              fontSize: '12px',
                              cursor: basketAddedReports.has(report.id) ? 'default' : 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              opacity: basketAddedReports.has(report.id) ? 0.7 : 1,
                            }}
                          >
                            <ShoppingCartOutlined />
                            {basketAddedReports.has(report.id) ? 'Added' : 'Basket'}
                          </button>
                        </>
                      )}
                      {isCompleted && !report.result_file_id && (
                        <span style={{ fontSize: '11px', color: '#64748b', fontStyle: 'italic' }}>
                          File not available
                        </span>
                      )}
                      {report.status === 'failed' && (
                        <button
                          onClick={(e) => handleRetry(e, report.id)}
                          style={{
                            padding: '6px 12px',
                            background: '#ef4444',
                            border: 'none',
                            borderRadius: '6px',
                            color: '#fff',
                            fontSize: '12px',
                            cursor: 'pointer',
                          }}
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '48px 16px',
            color: '#94a3b8',
            textAlign: 'center',
          }}>
            <FileTextOutlined style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }} />
            <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>No reports found</div>
            <div style={{ fontSize: '13px' }}>
              {statusFilter !== 'all'
                ? `No ${statusFilter} reports. Try a different filter.`
                : 'Create your first report to get started.'}
            </div>
          </div>
        )}
      </div>

      {/* Pagination info */}
      {pagination.total > 0 && (
        <div style={{ 
          textAlign: 'center', 
          padding: '16px', 
          color: '#64748b', 
          fontSize: '12px' 
        }}>
          Showing {reports.length} of {pagination.total} reports
        </div>
      )}

      {/* Create Report FAB */}
      <button
        onClick={() => setShowCreateModal(true)}
        aria-label="Create new report"
        style={{
          position: 'fixed',
          bottom: '80px',
          right: '20px',
          width: '56px',
          height: '56px',
          borderRadius: '28px',
          background: '#eab308',
          border: 'none',
          color: '#1a1f2e',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 100,
        }}
      >
        <PlusOutlined style={{ fontSize: '24px' }} />
      </button>

      {/* Create Report Modal - Template Selection like desktop */}
      <Modal
        title="Generate New Report"
        open={showCreateModal}
        onCancel={() => { setShowCreateModal(false); setSelectedTemplate(null); }}
        footer={null}
        width="90%"
        style={{ maxWidth: '400px' }}
      >
        <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {templates.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
              <FileTextOutlined style={{ fontSize: '32px', marginBottom: '12px', opacity: 0.5 }} />
              <p>No templates available</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {templates.map((template) => (
                <div
                  key={template.id}
                  onClick={() => setSelectedTemplate(template)}
                  style={{
                    padding: '16px',
                    background: selectedTemplate?.id === template.id ? 'rgba(234, 179, 8, 0.15)' : '#1a1f2e',
                    borderRadius: '8px',
                    border: selectedTemplate?.id === template.id ? '2px solid #eab308' : '1px solid #3a4356',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <h4 style={{ margin: 0, color: '#f1f5f9', fontSize: '14px', fontWeight: 500 }}>
                      {template.display_name || template.name}
                    </h4>
                    {template.category && (
                      <span style={{
                        background: `${getTypeColor(template.category)}20`,
                        color: getTypeColor(template.category),
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '10px',
                      }}>
                        {template.category}
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, color: '#94a3b8', fontSize: '12px', lineHeight: 1.4 }}>
                    {template.description}
                  </p>
                  {template.estimated_time_minutes && (
                    <p style={{ margin: '8px 0 0 0', color: '#64748b', fontSize: '11px' }}>
                      ~{template.estimated_time_minutes} minutes
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* Generate Button */}
          {selectedTemplate && (
            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #3a4356' }}>
              <button
                onClick={() => handleGenerateReport(selectedTemplate)}
                disabled={creatingReport}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: creatingReport ? '#64748b' : '#eab308',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#1a1f2e',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: creatingReport ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                {creatingReport ? (
                  <>
                    <Spin size="small" />
                    Generating...
                  </>
                ) : (
                  <>
                    <PlusOutlined />
                    Generate {selectedTemplate.display_name || selectedTemplate.name}
                  </>
                )}
              </button>
              <p style={{ margin: '12px 0 0 0', color: '#64748b', fontSize: '11px', textAlign: 'center' }}>
                Report generation may take a few minutes depending on data complexity.
              </p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default MobileReports;