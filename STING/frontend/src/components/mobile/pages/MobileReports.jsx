import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Spin, Modal, Input, Select } from 'antd';
import {
  FileTextOutlined,
  PlusOutlined,
  FilterOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { externalAiApi, REPORT_TEMPLATES } from '../../../services/externalAiApi';
import reportApi from '../../../services/reportApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Status filter options
 */
const STATUS_FILTERS = [
  { key: 'all', label: 'All' },
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
    case 'processing':
    case 'generating':
    default:
      return {
        icon: <ClockCircleOutlined />,
        color: '#1890ff',
        label: 'Processing',
      };
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
 * MobileReports - Mobile reports list page
 * List all reports with status indicators and filtering options
 */
const MobileReports = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingReport, setCreatingReport] = useState(false);
  const [newReportTitle, setNewReportTitle] = useState('');
  const [newReportType, setNewReportType] = useState('customer-insights');

  // Fetch reports - using same API as desktop BeeReportsPage
  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      // Use the same reportApi.listReports() as desktop
      const params = {
        limit: 50,
        offset: 0,
        status: statusFilter === 'all' ? undefined : statusFilter
      };
      
      const response = await reportApi.listReports(params);
      
      if (response.success && response.data?.reports?.length > 0) {
        // Map API response to component format
        const mappedReports = response.data.reports.map(report => ({
          id: report.id || report.report_id,
          title: report.title || report.name || 'Untitled Report',
          type: report.template_type || report.type || 'general',
          status: report.status || 'completed',
          createdAt: report.created_at || report.createdAt || new Date().toISOString(),
          duration: report.generation_time || report.duration || null,
        }));
        setReports(mappedReports);
      } else {
        // No reports found - show empty state
        setReports([]);
      }
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      // On error, show empty state rather than mock data
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // Initial data fetch
  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Filter reports based on status
  const filteredReports = reports.filter((report) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'processing') return report.status === 'processing' || report.status === 'generating';
    return report.status === statusFilter;
  });

  // Handle report click
  const handleReportClick = (report) => {
    if (report.status === 'processing') {
      message.info('Report is still generating. Please wait...');
      return;
    }
    navigate(`/m/reports/${report.id}`);
  };

  // Handle create new report
  const handleCreateReport = async () => {
    if (!newReportTitle.trim()) {
      message.warning('Please enter a report title');
      return;
    }

    setCreatingReport(false);
    try {
      const response = await externalAiApi.generateReport({
        title: newReportTitle.trim(),
        type: newReportType,
        user_id: user?.id,
        created_at: new Date().toISOString(),
      });

      message.success('Report generation started');
      setShowCreateModal(false);
      setNewReportTitle('');

      // Add new report to list
      const newReport = {
        id: response.report_id || `temp_${Date.now()}`,
        title: newReportTitle.trim(),
        type: newReportType,
        status: 'processing',
        createdAt: new Date().toISOString(),
        duration: null,
      };

      setReports((prev) => [newReport, ...prev]);
    } catch (error) {
      console.error('Failed to create report:', error);
      message.error('Failed to start report generation');
    } finally {
      setCreatingReport(false);
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    fetchReports();
    message.loading('Refreshing...', 0.5);
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div style={{ padding: '0', minHeight: '100%' }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '16px' 
      }}>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: '#f1f5f9' }}>Reports</h1>
        <button
          onClick={handleRefresh}
          style={{
            background: '#2a3142',
            border: '1px solid #3a4356',
            borderRadius: '8px',
            padding: '8px',
            color: '#f1f5f9',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-label="Refresh reports"
        >
          <ReloadOutlined />
        </button>
      </div>

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
              if (filter.key === 'processing') return r.status === 'processing' || r.status === 'generating';
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
        {filteredReports.length > 0 ? (
          filteredReports.map((report) => {
            const statusConfig = getStatusConfig(report.status);
            return (
              <div
                key={report.id}
                onClick={() => handleReportClick(report)}
                style={{
                  padding: '16px',
                  background: '#2a3142',
                  borderRadius: '12px',
                  border: '1px solid #3a4356',
                  cursor: report.status === 'processing' ? 'default' : 'pointer',
                  opacity: report.status === 'processing' ? 0.8 : 1,
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
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      fontSize: '12px',
                      color: '#94a3b8',
                    }}>
                      <span>
                        {REPORT_TEMPLATES[report.type]?.title || report.type} • {formatDate(report.createdAt)}
                      </span>
                      {report.duration && (
                        <span style={{ color: '#64748b' }}>
                          {report.duration}
                        </span>
                      )}
                    </div>
                    
                    {/* Error message if failed */}
                    {report.status === 'failed' && report.error && (
                      <div style={{ 
                        fontSize: '12px', 
                        color: '#ef4444', 
                        marginTop: '8px',
                        padding: '8px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderRadius: '6px',
                      }}>
                        {report.error}
                      </div>
                    )}
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

      {/* Create Report Modal */}
      <Modal
        title="Create New Report"
        open={showCreateModal}
        onCancel={() => setShowCreateModal(false)}
        footer={[
          <button
            key="cancel"
            onClick={() => setShowCreateModal(false)}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: 'var(--mobile-surface)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: 'var(--mobile-text-primary)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>,
          <button
            key="create"
            onClick={handleCreateReport}
            disabled={creatingReport || !newReportTitle.trim()}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: 'var(--mobile-primary)',
              border: 'none',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: 'var(--mobile-text-inverse)',
              cursor: creatingReport || !newReportTitle.trim() ? 'not-allowed' : 'pointer',
              opacity: creatingReport || !newReportTitle.trim() ? 0.6 : 1,
            }}
          >
            {creatingReport ? <Spin size="small" /> : 'Create Report'}
          </button>,
        ]}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-md)' }}>
          <div>
            <label style={{ display: 'block', marginBottom: 'var(--mobile-space-xs)', color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
              Report Title
            </label>
            <Input
              placeholder="Enter report title"
              value={newReportTitle}
              onChange={(e) => setNewReportTitle(e.target.value)}
              onPressEnter={handleCreateReport}
              style={{ borderRadius: 'var(--mobile-radius-md, 8px)' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 'var(--mobile-space-xs)', color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
              Report Type
            </label>
            <Select
              value={newReportType}
              onChange={setNewReportType}
              style={{ width: '100%' }}
              dropdownStyle={{ borderRadius: 'var(--mobile-radius-md, 8px)' }}
            >
              {Object.entries(REPORT_TEMPLATES).map(([key, template]) => (
                <Select.Option key={key} value={key}>
                  {template.title}
                </Select.Option>
              ))}
            </Select>
          </div>
          <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)', background: 'var(--mobile-surface)', padding: 'var(--mobile-space-sm)', borderRadius: 'var(--mobile-radius-md, 8px)' }}>
            <strong>Note:</strong> Report generation may take a few minutes depending on the amount of data and complexity.
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MobileReports;
