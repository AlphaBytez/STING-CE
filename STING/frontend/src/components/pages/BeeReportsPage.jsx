import React, { useState, useEffect, useCallback } from 'react';
import { Button, Table, Tag, Progress, Input, Select, Tooltip, Badge, Space, message, Modal, Tabs, Alert } from 'antd';
import ScrollToTopButton from '../common/ScrollToTopButton';
import {
  FileTextOutlined,
  DownloadOutlined,
  ShareAltOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  PlusOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileOutlined,
  ReloadOutlined,
  SettingOutlined,
  SafetyOutlined,
  ShoppingCartOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import reportApi from '../../services/reportApi';
import ReportTemplateManager from '../reports/ReportTemplateManager';
import ReportViewer from '../reports/ReportViewer';
import ReportShareModal from '../reports/ReportShareModal';
import TierBadge, { TierIndicator, OPERATION_TIERS } from '../common/TierBadge';
import {
  handleReturnFromAuth,
  checkOperationAuth,
  clearAuthMarker,
  storeOperationContext,
  getStoredOperationContext,
  shouldRetryOperation,
  OPERATIONS
} from '../../utils/tieredAuth';
import axios from 'axios';

const { Search } = Input;
const { Option } = Select;

// Define operations for reports
const REPORT_OPERATIONS = {
  VIEW_REPORTS: {
    name: 'VIEW_REPORTS',
    tier: 2,
    description: 'View generated reports'
  },
  CREATE_REPORT: {
    name: 'CREATE_REPORT',
    tier: 2,
    description: 'Generate new reports'
  },
  DOWNLOAD_REPORT: {
    name: 'DOWNLOAD_REPORT',
    tier: 2,  // Changed from 3 to match backend @require_auth_method(['webauthn', 'totp'])
    description: 'Download report files'
  },
  SHARE_REPORT: {
    name: 'SHARE_REPORT',
    tier: 3,
    description: 'Share reports with others'
  },
  DELETE_REPORT: {
    name: 'DELETE_REPORT',
    tier: 3,
    description: 'Delete reports'
  }
};

const BeeReportsPage = () => {
  const navigate = useNavigate();
  const { identity, user } = useUnifiedAuth();

  // All other hooks - MOVED TO TOP
  const [searchTerm, setSearchTerm] = useState('');
  const [templateSearchTerm, setTemplateSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [activeTab, setActiveTab] = useState('reports');
  const [showAllTemplates, setShowAllTemplates] = useState(false);
  
  // State for API data
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [userReports, setUserReports] = useState([]);
  const [availableTemplates, setAvailableTemplates] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [reportQueue, setReportQueue] = useState([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });
  
  // Poll interval for queue updates
  const [pollInterval, setPollInterval] = useState(null);
  
  // Report viewer state
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportViewerOpen, setReportViewerOpen] = useState(false);
  
  // Report share state
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [reportToShare, setReportToShare] = useState(null);

  // Basket state - track which reports have been added
  const [basketAddedReports, setBasketAddedReports] = useState(new Set());
  
  // Handle return from authentication flow and auto-retry operations
  useEffect(() => {
    // Check for each operation if user just returned from authentication
    Object.values(REPORT_OPERATIONS).forEach(operation => {
      if (shouldRetryOperation(operation.name)) {
        console.log(`🔄 Auto-retrying operation after authentication: ${operation.name}`);

        // Get stored context
        const context = getStoredOperationContext(operation.name);

        // Set auth marker (include tier for shared tier-level caching)
        handleReturnFromAuth(operation.name, operation.tier);

        // Auto-retry the operation based on its type
        setTimeout(() => {
          switch (operation.name) {
            case REPORT_OPERATIONS.CREATE_REPORT.name:
              if (context?.templateId) {
                handleGenerateReport(context.templateId);
              }
              break;
            case REPORT_OPERATIONS.DOWNLOAD_REPORT.name:
              if (context?.reportId) {
                handleDownload(context.reportId);
              }
              break;
            case REPORT_OPERATIONS.SHARE_REPORT.name:
              if (context?.reportId) {
                handleShare(context.reportId);
              }
              break;
            case REPORT_OPERATIONS.VIEW_REPORTS.name:
              if (context?.reportId) {
                handleView(context.reportId);
              }
              break;
            case REPORT_OPERATIONS.DELETE_REPORT.name:
              if (context?.reportId) {
                handleCancel(context.reportId);
              }
              break;
            default:
              console.log(`⚠️ Unknown operation for auto-retry: ${operation.name}`);
          }
        }, 100); // Small delay to ensure page is fully loaded
      }
    });
  }, []);

  // Tiered authentication for report operations
  const protectReportOperation = async (operationKey, additionalData = {}) => {
    const operation = REPORT_OPERATIONS[operationKey];
    if (!operation) {
      // Unknown report operation
      return false;
    }

    // Checking tier authentication

    const canProceed = await checkOperationAuth(operation.name, operation.tier);

    if (canProceed) {
      // Authentication verified
      return true;
    } else {
      // Authentication failed
      return false;
    }
  };

  // Load report templates with resilient API pattern
  const loadTemplates = useCallback(async () => {
    try {
      const response = await reportApi.getTemplates(filterType === 'all' ? null : filterType);
      if (response.success) {
        setAvailableTemplates(response.data.templates || []);
      }
    } catch (error) {
      console.error('Templates API error:', error.response?.status, error.message);
      // Clear templates on error - user is not authenticated
      setAvailableTemplates([]);
    }
  }, [filterType]);

  // Load user reports
  const loadReports = useCallback(async (page = 1, pageSize = 10) => {
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      const params = {
        limit: pageSize,
        offset,
        status: filterStatus === 'all' ? undefined : filterStatus
      };
      
      const response = await reportApi.listReports(params);
      if (response.success) {
        setUserReports(response.data.reports || []);
        setPagination({
          current: page,
          pageSize,
          total: response.data.pagination?.total || 0
        });
      }
    } catch (error) {
      console.error('Reports API error:', error.response?.status, error.message);

      // Check if this is an authentication error
      if (error.response?.status === 401 || error.response?.status === 403) {
        console.log('🔐 Authentication required for reports - redirecting to security upgrade');

        // Store context for after authentication
        storeOperationContext(REPORT_OPERATIONS.VIEW_REPORTS.name, {
          page,
          pageSize,
          returnTo: '/dashboard/reports'
        });

        // Immediately redirect to authentication (checkOperationAuth always redirects)
        checkOperationAuth(
          REPORT_OPERATIONS.VIEW_REPORTS.name,
          REPORT_OPERATIONS.VIEW_REPORTS.tier
        );

        // Don't clear reports - user will return after auth
        console.log('🔄 User being redirected to authentication');
        return;
      }

      // Clear reports on non-auth errors
      setUserReports([]);
      setPagination({
        current: page,
        pageSize,
        total: 0
      });
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  // Load queue status
  const loadQueueStatus = useCallback(async () => {
    try {
      const response = await reportApi.getQueueStatus();
      if (response.success) {
        setQueueStatus(response.data);
      }
    } catch (error) {
      console.error('Queue status API error:', error.response?.status, error.message);

      // Check if this is an authentication error
      if (error.response?.status === 401 || error.response?.status === 403) {
        console.log('🔐 Authentication required for queue status - will be handled by reports auth check');
        // Don't trigger separate auth for queue status - let reports auth handle it
        return;
      }

      // Clear queue status on non-auth errors
      setQueueStatus(null);
    }
  }, []);

  // Initial data load - only run once on mount
  useEffect(() => {
    loadTemplates();
    loadReports();
    loadQueueStatus();
  }, []); // Empty dependency array for initial load only

  // Reload when filters change
  useEffect(() => {
    loadTemplates();
  }, [filterType]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadReports();
  }, [filterStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  // Set up polling for active reports
  useEffect(() => {
    const newReportQueue = userReports.filter(report => 
      ['pending', 'queued', 'processing'].includes(report.status)
    );
    setReportQueue(newReportQueue);
    
    const hasActiveReports = newReportQueue.length > 0;
    
    if (hasActiveReports && !pollInterval) {
      // Start polling every 5 seconds
      const interval = setInterval(() => {
        loadReports(pagination.current, pagination.pageSize);
        loadQueueStatus();
      }, 5000);
      setPollInterval(interval);
    } else if (!hasActiveReports && pollInterval) {
      // Stop polling
      clearInterval(pollInterval);
      setPollInterval(null);
    }
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [userReports, pollInterval, loadReports, loadQueueStatus, pagination]);

  // Refresh data
  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      loadTemplates(),
      loadReports(pagination.current, pagination.pageSize),
      loadQueueStatus()
    ]);
    setRefreshing(false);
    message.success('Data refreshed');
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'queued':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'processing':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <FileOutlined />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'queued': return 'orange';
      case 'processing': return 'blue';
      case 'completed': return 'green';
      case 'failed': return 'red';
      default: return 'default';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'security': return 'red';
      case 'analytics': return 'blue';
      case 'compliance': return 'purple';
      case 'performance': return 'green';
      default: return 'default';
    }
  };

  const handleGenerateReport = async (templateId) => {
    // Check authentication BEFORE attempting generation (Tier 2 - basic operation)
    const canProceed = await protectReportOperation('CREATE_REPORT', { templateId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Generating report (authentication pre-verified)');

      // Find template details
      const template = availableTemplates.find(t => t.id === templateId);
      if (!template) {
        message.error('Template not found');
        return;
      }

      // Generate the report directly
      const response = await reportApi.generateReport(template.id, {
        title: `${template.display_name || template.name} - ${new Date().toLocaleDateString()}`,
        description: template.description
      });

      if (response.success) {
        message.success('Report queued for generation');

        // Clear auth markers since operation succeeded
        clearAuthMarker(REPORT_OPERATIONS.CREATE_REPORT.name);

        await loadReports(1, pagination.pageSize); // Refresh to show new report
      }
    } catch (error) {
      console.error('❌ Report generation failed:', error);
      message.error('Failed to generate report');
    }
  };


  const handleDownload = async (reportId) => {
    // Let backend handle AAL2 check via decorator - it will return 403 if insufficient
    // The apiClient interceptor will catch 403 and redirect to security-upgrade if needed
    try {
      console.log('🔄 Downloading report (backend will verify AAL2)');

      await reportApi.downloadReport(reportId);
      message.success('Report downloaded successfully');

      // Clear auth markers since operation succeeded (if any were set)
      clearAuthMarker(REPORT_OPERATIONS.DOWNLOAD_REPORT.name);

      // Update download count locally
      setUserReports(prev =>
        prev.map(report =>
          report.id === reportId
            ? { ...report, download_count: (report.download_count || 0) + 1 }
            : report
        )
      );
    } catch (error) {
      console.error('❌ Report download failed:', error);
      message.error('Failed to download report');
    }
  };

  const handleShare = async (reportId) => {
    // Check authentication BEFORE attempting share (Tier 3 - sensitive operation)
    const canProceed = await protectReportOperation('SHARE_REPORT', { reportId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Opening report share (authentication pre-verified)');

      // Find the report
      const report = userReports.find(r => r.id === reportId);

      // Clear auth markers since operation succeeded
      clearAuthMarker(REPORT_OPERATIONS.SHARE_REPORT.name);

      // Open share modal
      setReportToShare(report);
      setShareModalOpen(true);

    } catch (error) {
      console.error('❌ Report share failed:', error);
      message.error('Failed to open share dialog');
    }
  };

  const handleView = async (reportId) => {
    // Check authentication BEFORE attempting view (Tier 2 - basic operation)
    const canProceed = await protectReportOperation('VIEW_REPORTS', { reportId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Opening report viewer (authentication pre-verified)');

      // Find the report
      const report = userReports.find(r => r.id === reportId);
      if (!report) {
        message.error('Report not found');
        return;
      }

      // Clear auth markers since operation succeeded
      clearAuthMarker(REPORT_OPERATIONS.VIEW_REPORTS.name);

      // Open report viewer
      setSelectedReport(report);
      setReportViewerOpen(true);

    } catch (error) {
      console.error('❌ Report view failed:', error);
      message.error('Failed to open report viewer');
    }
  };

  const handleCancel = async (reportId) => {
    // Check authentication BEFORE attempting cancel (Tier 3 - sensitive operation)
    const canProceed = await protectReportOperation('DELETE_REPORT', { reportId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Cancelling report (authentication pre-verified)');

      // Check if this is a demo report (numeric ID or string ID without UUID format)
      const isDemo = typeof reportId === 'number' || !reportId.includes('-');

      if (isDemo) {
        message.warning('Cannot cancel demo reports. Only real reports can be cancelled.');
        return;
      }

      const response = await reportApi.cancelReport(reportId);
      if (response.success) {
        message.success('Report cancelled successfully');

        // Clear auth markers since operation succeeded
        clearAuthMarker(REPORT_OPERATIONS.DELETE_REPORT.name);

        await loadReports(pagination.current, pagination.pageSize);
      }
    } catch (error) {
      console.error('❌ Report cancellation failed:', error);
      message.error('Failed to cancel report');
    }
  };

  const handleRetry = async (reportId) => {
    // Check authentication BEFORE attempting retry (Tier 2 - basic operation)
    const canProceed = await protectReportOperation('CREATE_REPORT', { reportId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Retrying report generation (authentication pre-verified)');

      const response = await reportApi.retryReport(reportId);
      if (response.success) {
        message.success('Report queued for retry');

        // Clear auth markers since operation succeeded
        clearAuthMarker(REPORT_OPERATIONS.CREATE_REPORT.name);

        await loadReports(pagination.current, pagination.pageSize);
      }
    } catch (error) {
      console.error('❌ Report retry failed:', error);
      message.error('Failed to retry report');
    }
  };

  // Add report to basket (private space / external storage)
  const handleAddToBasket = async (report) => {
    try {
      // Generate filename from report title and date
      const timestamp = new Date(report.created_at).toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const sanitizedTitle = (report.title || 'report').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30);
      const filename = `${sanitizedTitle}_${timestamp}.md`;

      // Build report content for basket storage
      const reportContent = `# ${report.title}

**Generated:** ${new Date(report.created_at).toLocaleString()}
**Status:** ${report.status}
**Type:** ${report.template?.category || 'analytics'}

## Description
${report.description || 'No description provided'}

## Report Details
- **Report ID:** ${report.id}
- **Template:** ${report.template?.name || 'Unknown'}
- **File Size:** ${report.result_size_bytes ? `${(report.result_size_bytes / 1024).toFixed(2)} KB` : 'N/A'}
- **Downloads:** ${report.download_count || 0}

---
*This report was exported to your Basket from Hive Bee Reports.*
*For the full report content, use the Download feature.*
`;

      const response = await fetch('/api/basket/add-report', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: filename,
          content: reportContent,
          content_type: 'text/markdown',
          metadata: {
            source: 'bee_reports_page',
            report_id: report.id,
            report_title: report.title,
            report_status: report.status,
            template_category: report.template?.category,
            created_at: report.created_at,
            exported_at: new Date().toISOString()
          }
        })
      });

      if (response.ok) {
        setBasketAddedReports(prev => new Set([...prev, report.id]));
        message.success('Report added to your Basket');
        console.log('📦 Report added to basket:', filename);
      } else {
        // Still mark as added for UX
        setBasketAddedReports(prev => new Set([...prev, report.id]));
        message.info('Report marked for export');
      }
    } catch (error) {
      console.error('Error adding report to basket:', error);
      // Mark as added anyway for better UX
      setBasketAddedReports(prev => new Set([...prev, report.id]));
      message.info('Report marked for export');
    }
  };

  // Filter reports based on search and filters
  const filteredUserReports = userReports.filter(report => {
    const matchesSearch = report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (report.description || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || report.status === filterStatus;
    const matchesType = filterType === 'all' || (report.template?.category || 'analytics') === filterType;

    // Smart filtering: Only show downloadable reports for better UX
    const isDownloadable = report.status === 'completed' &&
                          report.result_file_id &&
                          report.result_file_id !== null;

    // For 'completed' filter, only show actually downloadable reports
    // For other statuses (pending/processing), show all for progress tracking
    const shouldShow = filterStatus === 'completed' ? isDownloadable : true;

    return matchesSearch && matchesStatus && matchesType && shouldShow;
  });

  const filteredAvailableTemplates = availableTemplates.filter(template => {
    // Add null checks to prevent crashes when template properties are undefined
    const displayName = template.display_name || template.name || '';
    const description = template.description || '';
    const matchesSearch = displayName.toLowerCase().includes(templateSearchTerm.toLowerCase()) ||
                         description.toLowerCase().includes(templateSearchTerm.toLowerCase());
    const matchesType = filterType === 'all' || template.category === filterType;
    return matchesSearch && matchesType;
  });

  // Show only first 3 templates by default, all when expanded
  const displayedTemplates = showAllTemplates ? filteredAvailableTemplates : filteredAvailableTemplates.slice(0, 3);

  // Columns for user reports table
  const userReportsColumns = [
    {
      title: 'Report',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <div>
          <div className="font-medium text-white">{text}</div>
          <div className="text-sm text-gray-400">{record.description || 'No description'}</div>
        </div>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      render: (_, record) => (
        <Tag color={getTypeColor(record.template?.category || 'analytics')}>
          {record.template?.category || 'analytics'}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>{status}</Tag>
          {status === 'failed' && record.error_message && (
            <Tooltip title={record.error_message}>
              <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
            </Tooltip>
          )}
          {status === 'processing' && record.progress_percentage > 0 && (
            <span className="text-gray-400 text-sm">
              ({record.progress_percentage}%)
            </span>
          )}
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => (
        <span className="text-gray-300">
          {date ? new Date(date).toLocaleDateString() : '-'}
        </span>
      ),
    },
    {
      title: 'Size',
      dataIndex: 'result_size_bytes',
      key: 'result_size_bytes',
      render: (size) => {
        if (!size) return <span className="text-gray-300">-</span>;
        // Convert bytes to human readable
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(size) / Math.log(1024));
        return (
          <span className="text-gray-300">
            {(size / Math.pow(1024, i)).toFixed(2)} {sizes[i]}
          </span>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'completed' && record.result_file_id && (
            <>
              <Tooltip title="View Report">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => handleView(record.id)}
                  className="text-gray-400 hover:text-yellow-400"
                />
              </Tooltip>
              <Tooltip title={`Download (${record.download_count || 0} downloads)`}>
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownload(record.id)}
                  className="text-gray-400 hover:text-green-400"
                />
              </Tooltip>
              <Tooltip title={basketAddedReports.has(record.id) ? "Added to Basket" : "Add to Basket"}>
                <Button
                  type="text"
                  icon={<ShoppingCartOutlined />}
                  onClick={() => handleAddToBasket(record)}
                  className={basketAddedReports.has(record.id)
                    ? "text-green-400"
                    : "text-gray-400 hover:text-amber-400"}
                  disabled={basketAddedReports.has(record.id)}
                />
              </Tooltip>
              <Tooltip title="Share">
                <Button
                  type="text"
                  icon={<ShareAltOutlined />}
                  onClick={() => handleShare(record.id)}
                  className="text-gray-400 hover:text-yellow-400"
                />
              </Tooltip>
            </>
          )}
          {record.status === 'completed' && !record.result_file_id && (
            <Tooltip title="Report completed but file not available">
              <Button
                type="text"
                icon={<DownloadOutlined />}
                disabled
                className="text-gray-600"
              />
            </Tooltip>
          )}
          {(record.status === 'queued' || record.status === 'processing') && (
            <Tooltip title="Cancel">
              <Button 
                type="text" 
                size="small"
                danger
                onClick={() => handleCancel(record.id)}
                className="text-red-400 hover:text-red-500"
              >
                Cancel
              </Button>
            </Tooltip>
          )}
          {record.status === 'failed' && (
            <Button 
              type="primary" 
              size="small"
              onClick={() => handleRetry(record.id)}
              className="floating-button bg-red-500 hover:bg-red-600 border-red-500 hover:border-red-600"
            >
              Retry
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Check if user is admin
  const isAdmin = identity?.traits?.role === 'admin';

  const tabItems = [
    {
      key: 'reports',
      label: (
        <div className="flex items-center gap-2">
          <FileTextOutlined />
          <span>Reports</span>
        </div>
      ),
      children: renderReportsContent()
    },
    {
      key: 'templates',
      label: (
        <div className="flex items-center gap-2">
          <SettingOutlined />
          <span>Templates</span>
        </div>
      ),
      children: <ReportTemplateManager />
    }
  ];

  function renderReportsContent() {
    return (
      <>
        {/* Search and Filter Bar */}
        <div className="dashboard-card p-6 mb-6 rounded-xl">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-64">
              <Search
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full max-w-md dark-search-input"
              />
            </div>
            <Select
              value={filterStatus}
              onChange={(value) => {
                setFilterStatus(value);
                loadReports(1, pagination.pageSize);
              }}
              className="min-w-32 dark-select"
              placeholder="Status"
              dropdownClassName="dark-dropdown"
              popupClassName="dark-dropdown-popup"
            >
              <Option value="all">All Status</Option>
              <Option value="pending">Pending</Option>
              <Option value="queued">Queued</Option>
              <Option value="processing">Processing</Option>
              <Option value="completed">Completed</Option>
              <Option value="failed">Failed</Option>
              <Option value="cancelled">Cancelled</Option>
            </Select>
            <Select
              value={filterType}
              onChange={(value) => {
                setFilterType(value);
                loadTemplates();
              }}
              className="min-w-32 dark-select"
              placeholder="Type"
              dropdownClassName="dark-dropdown"
              popupClassName="dark-dropdown-popup"
            >
              <Option value="all">All Types</Option>
              <Option value="security">Security</Option>
              <Option value="analytics">Analytics</Option>
              <Option value="compliance">Compliance</Option>
              <Option value="performance">Performance</Option>
              <Option value="storage">Storage</Option>
            </Select>
            <Button 
              type="text"
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={handleRefresh}
              className="text-gray-400 hover:text-yellow-400"
              disabled={refreshing}
            >
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Report Queue */}
          <div className="lg:col-span-1">
            <div className="dashboard-card p-6 h-full rounded-xl">
              <div className="flex items-center gap-3 mb-6">
                <LoadingOutlined className="text-yellow-400 text-xl" />
                <h3 className="text-xl font-semibold text-white">Report Queue</h3>
                <Badge 
                  count={reportQueue.length} 
                  style={{ backgroundColor: '#eab308', color: '#000' }}
                />
              </div>
              {reportQueue.length === 0 ? (
                <div className="text-center py-8">
                  <ClockCircleOutlined className="text-6xl text-gray-600 mb-4" />
                  <div className="text-gray-400">
                    No reports in queue
                  </div>
                  {queueStatus && (
                    <div className="text-sm text-gray-500 mt-2">
                      {queueStatus.total_pending} pending • {queueStatus.currently_processing} processing
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {reportQueue.map((report) => (
                    <div key={report.id} className="stats-card p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-white text-sm">{report.title}</h4>
                        <Tag color={getStatusColor(report.status)} className="ml-2">
                          {report.status}
                        </Tag>
                      </div>
                      <p className="text-gray-400 text-xs mb-3">
                        {report.description || 'Processing...'}
                      </p>
                      {report.status === 'processing' && report.progress_percentage > 0 && (
                        <div className="space-y-2">
                          <Progress 
                            percent={report.progress_percentage} 
                            size="small" 
                            status="active"
                            strokeColor="#eab308"
                          />
                          {report.estimated_completion && (
                            <p className="text-gray-500 text-xs">
                              Est. completion: {new Date(report.estimated_completion).toLocaleTimeString()}
                            </p>
                          )}
                        </div>
                      )}
                      {report.status === 'queued' && (
                        <div className="text-gray-500 text-xs">
                          {report.queue_position && (
                            <p>Position in queue: #{report.queue_position}</p>
                          )}
                          {report.estimated_completion && (
                            <p>Est. start: {new Date(report.estimated_completion).toLocaleTimeString()}</p>
                          )}
                        </div>
                      )}
                      <div className="mt-2 flex justify-end">
                        <Button
                          type="text"
                          size="small"
                          danger
                          onClick={() => handleCancel(report.id)}
                          className="text-red-400 hover:text-red-500 text-xs"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* View All Pending Reports Button */}
              {(reportQueue.length > 0 || queueStatus?.total_pending > 0) && (
                <div className="mt-4 border-t border-gray-700 pt-4">
                  <Button
                    type="primary"
                    block
                    icon={<FileTextOutlined />}
                    onClick={() => {
                      setFilterStatus('pending');
                      // Scroll to the My Reports table
                      setTimeout(() => {
                        const tableElement = document.querySelector('.dark-table');
                        if (tableElement) {
                          tableElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                      }, 100);
                    }}
                    className="floating-button bg-yellow-500 hover:bg-yellow-600 border-yellow-500 hover:border-yellow-600 text-black font-medium"
                  >
                    View All Pending Reports
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Available Reports */}
          <div className="lg:col-span-2">
            <div className="dashboard-card p-6 h-full rounded-xl">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <FileTextOutlined className="text-yellow-400 text-xl" />
                  <h3 className="text-xl font-semibold text-white">Available Reports</h3>
                  <Badge 
                    count={filteredAvailableTemplates.length} 
                    style={{ backgroundColor: '#1890ff', color: '#fff' }}
                  />
                </div>
                <div className="flex items-center gap-3">
                  <Search
                    placeholder="Search templates..."
                    value={templateSearchTerm}
                    onChange={(e) => setTemplateSearchTerm(e.target.value)}
                    className="w-48 dark-search-input"
                    size="small"
                  />
                </div>
              </div>
              
              {filteredAvailableTemplates.length === 0 ? (
                <div className="text-center py-8">
                  <FileTextOutlined className="text-6xl text-gray-600 mb-4" />
                  <div className="text-gray-400">
                    {templateSearchTerm ? 'No templates match your search' : 'No report templates available'}
                  </div>
                  {templateSearchTerm && (
                    <Button 
                      type="text" 
                      onClick={() => setTemplateSearchTerm('')}
                      className="text-yellow-400 hover:text-yellow-300 mt-2"
                    >
                      Clear search
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 p-2 transition-all duration-300 ${
                    !showAllTemplates && filteredAvailableTemplates.length > 3 ? 'overflow-hidden' : ''
                  }`} style={{ 
                    maxHeight: !showAllTemplates && filteredAvailableTemplates.length > 3 ? '340px' : 'none' 
                  }}>
                    {displayedTemplates.map((template) => (
                      <div key={template.id} className="dashboard-card p-4 text-center hover:transform hover:scale-[1.02] hover:-translate-y-1 transition-all duration-200 rounded-xl">
                        <div className="text-4xl text-yellow-400 mb-4">
                          {template.output_formats?.includes('pdf') ? <FilePdfOutlined /> :
                           template.output_formats?.includes('xlsx') ? <FileExcelOutlined /> :
                           <FileTextOutlined />}
                        </div>
                        <h4 className="font-medium text-white mb-2 text-sm">
                          {template.display_name}
                        </h4>
                        <p className="text-gray-400 text-xs mb-4 line-clamp-3">
                          {template.description}
                        </p>
                        <div className="space-y-2 mb-4">
                          <Tag color={getTypeColor(template.category)}>{template.category}</Tag>
                          {template.is_premium && <Tag color="gold">Premium</Tag>}
                          {template.requires_scrambling && (
                            <Tooltip title="This report includes PII protection">
                              <Tag color="green">Protected</Tag>
                            </Tooltip>
                          )}
                          <p className="text-gray-500 text-xs">
                            ~{template.estimated_time_minutes} minutes
                          </p>
                        </div>
                        <Button 
                          type="primary" 
                          size="small"
                          icon={<PlusOutlined />}
                          onClick={() => handleGenerateReport(template.id)}
                          className="floating-button bg-yellow-500 hover:bg-yellow-600 border-yellow-500 hover:border-yellow-600 text-black font-medium w-full"
                          disabled={template.required_role === 'admin' && !window.isAdmin}
                        >
                          Generate
                        </Button>
                      </div>
                    ))}
                  </div>
                  
                  {filteredAvailableTemplates.length > 3 && (
                    <div className="mt-4 text-center">
                      <Button
                        type="text"
                        onClick={() => setShowAllTemplates(!showAllTemplates)}
                        className="text-yellow-400 hover:text-yellow-300"
                      >
                        {showAllTemplates 
                          ? `Show Less (${displayedTemplates.length}/${filteredAvailableTemplates.length})`
                          : `Show All Templates (${filteredAvailableTemplates.length - 3} more)`
                        }
                      </Button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* User Reports Table */}
        <div className="dashboard-card p-6 rounded-xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <FileTextOutlined className="text-yellow-400 text-xl" />
              <h3 className="text-xl font-semibold text-white">My Reports</h3>
              <Badge 
                count={pagination.total || 0} 
                style={{ backgroundColor: '#eab308', color: '#000' }}
              />
              {filterStatus !== 'all' && (
                <Tag color="orange" className="ml-2">
                  Showing: {filterStatus}
                </Tag>
              )}
            </div>
            {filterStatus !== 'all' && (
              <Button
                type="text"
                size="small"
                onClick={() => setFilterStatus('all')}
                className="text-gray-400 hover:text-yellow-400"
              >
                Show All Reports
              </Button>
            )}
          </div>
          <div className="overflow-x-auto">
            <Table
              columns={userReportsColumns}
              dataSource={filteredUserReports}
              rowKey="id"
              loading={loading}
              pagination={{
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                showSizeChanger: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} reports`,
                onChange: (page, pageSize) => {
                  setPagination(prev => ({ ...prev, current: page, pageSize }));
                  loadReports(page, pageSize);
                },
                onShowSizeChange: (current, size) => {
                  setPagination(prev => ({ ...prev, current: 1, pageSize: size }));
                  loadReports(1, size);
                }
              }}
              className="dark-table modern-glass-table reports-table"
              style={{
                backgroundColor: 'transparent',
                '--ant-table-bg': 'transparent',
                '--ant-table-header-bg': 'rgba(55, 65, 81, 0.8)',
                '--ant-table-row-hover-bg': 'rgba(75, 85, 99, 0.5)',
                '--ant-table-tbody-tr-hover-bg': 'rgba(75, 85, 99, 0.5)',
                '--ant-table-header-color': '#e2e8f0',
                '--ant-table-body-sort-bg': 'rgba(55, 65, 81, 0.6)',
                '--ant-pagination-item-bg': 'rgba(55, 65, 81, 0.8)',
                '--ant-pagination-item-link-bg': 'rgba(55, 65, 81, 0.8)',
                '--ant-table-tbody-tr-bg': 'transparent',
                '--ant-table-cell-bg': 'transparent'
              }}
              locale={{
                emptyText: (
                  <div className="text-center py-8">
                    <FileTextOutlined className="text-4xl text-gray-600 mb-4" />
                    <div className="text-gray-400">No reports found</div>
                    <Button 
                      type="primary" 
                      className="mt-4 floating-button bg-yellow-500 hover:bg-yellow-600 border-yellow-500 hover:border-yellow-600 text-black font-medium"
                      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                    >
                      Generate Your First Report
                    </Button>
                    </div>
                )
              }}
            />
          </div>
        </div>
      </>
    );
  }


  return (
    <div className="bee-reports-page p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="text-yellow-400 text-3xl">
            <FileTextOutlined />
          </div>
          <h1 className="text-3xl font-bold text-white">Bee Reports</h1>
        </div>
        <p className="text-gray-400">
          Generate, view, and manage security and analytics reports
        </p>
      </div>

      {/* Security Notice with Tier Information */}
      <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <SafetyOutlined className="text-blue-400 text-lg mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-blue-300 font-medium mb-2">Tiered Security Model</h3>
            <p className="text-blue-200/80 text-sm leading-relaxed mb-3">
              Reports are protected by a progressive security model. Different operations require different authentication levels:
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TierBadge tier={2} size="xs" />
                <span className="text-blue-200 text-sm">View reports, Generate new reports</span>
              </div>
              <div className="flex items-center gap-2">
                <TierBadge tier={3} size="xs" />
                <span className="text-blue-200 text-sm">Download, Share, Cancel reports</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Component */}
      <Tabs 
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        className="reports-tabs modern-glass-tabs"
        size="large"
        style={{
          '--ant-tabs-tab-color': '#d1d5db',
          '--ant-tabs-tab-color-hover': '#f59e0b',
          '--ant-tabs-tab-color-active': '#f59e0b',
          '--ant-tabs-tab-bg': 'transparent',
          '--ant-tabs-content-bg': 'transparent',
          '--ant-tabs-ink-bar-color': '#f59e0b',
          '--ant-tabs-horizontal-gutter': '32px',
          '--ant-tabs-card-gutter': '2px',
          paddingBottom: '8px',
          marginBottom: '16px'
        }}
      />


      {/* Report Viewer Modal */}
      <ReportViewer
        reportId={selectedReport?.id}
        reportName={selectedReport?.title}
        isOpen={reportViewerOpen}
        onClose={() => {
          setReportViewerOpen(false);
          setSelectedReport(null);
        }}
      />

      {/* Report Share Modal */}
      <ReportShareModal
        reportId={reportToShare?.id}
        reportName={reportToShare?.title}
        isOpen={shareModalOpen}
        onClose={() => {
          setShareModalOpen(false);
          setReportToShare(null);
        }}
      />

      {/* Scroll to Top Button */}
      <ScrollToTopButton />

    </div>
  );
};

export default BeeReportsPage;