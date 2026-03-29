import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Spin, Dropdown, Progress } from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  ReloadOutlined,
  FilePdfOutlined,
  FileMarkdownOutlined,
  Html5Outlined,
  ShareAltOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ShoppingCartOutlined,
} from '@ant-design/icons';
import reportApi from '../../../services/reportApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Get status configuration for display
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
  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * MobileReportDetail - Mobile report detail page
 * Full report content display with export options - parity with desktop
 */
const MobileReportDetail = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [addedToBasket, setAddedToBasket] = useState(false);

  // Fetch report data using reportApi - same as desktop
  const fetchReport = useCallback(async () => {
    if (!reportId) {
      navigate('/m/reports');
      return;
    }

    setLoading(true);
    try {
      const response = await reportApi.getReport(reportId);

      if (response.success && response.data) {
        const reportData = response.data;
        setReport({
          id: reportId,
          title: reportData.title || 'Untitled Report',
          description: reportData.description || '',
          status: reportData.status || 'completed',
          created_at: reportData.created_at || new Date().toISOString(),
          completed_at: reportData.completed_at,
          template: reportData.template,
          result_file_id: reportData.result_file_id,
          result_size_bytes: reportData.result_size_bytes,
          download_count: reportData.download_count || 0,
          progress_percentage: reportData.progress_percentage,
          status_message: reportData.status_message,
          error_message: reportData.error_message,
        });
      } else {
        message.error('Report not found');
        navigate('/m/reports');
      }
    } catch (error) {
      console.error('Failed to fetch report:', error);
      message.error('Failed to load report');
      navigate('/m/reports');
    } finally {
      setLoading(false);
    }
  }, [reportId, navigate]);

  // Poll for status updates if report is still processing
  useEffect(() => {
    if (report?.status === 'processing' || report?.status === 'pending' || report?.status === 'queued') {
      const pollInterval = setInterval(async () => {
        try {
          const response = await reportApi.getReport(reportId);
          if (response.success && response.data) {
            const newData = response.data;
            setReport((prev) => ({
              ...prev,
              status: newData.status,
              progress_percentage: newData.progress_percentage,
              status_message: newData.status_message,
              result_file_id: newData.result_file_id,
              completed_at: newData.completed_at,
            }));

            if (newData.status === 'completed') {
              message.success('Report generation completed!');
              clearInterval(pollInterval);
            } else if (newData.status === 'failed') {
              message.error('Report generation failed');
              clearInterval(pollInterval);
            }
          }
        } catch (error) {
          console.error('Status check failed:', error);
        }
      }, 3000); // Poll every 3 seconds

      return () => clearInterval(pollInterval);
    }
  }, [report?.status, reportId]);

  // Initial data fetch
  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Handle download report - same as desktop
  const handleDownload = async () => {
    if (!report || !report.result_file_id) {
      message.warning('Report file not available');
      return;
    }

    setDownloading(true);
    try {
      await reportApi.downloadReport(reportId);
      message.success('Report downloaded successfully');
      // Update local download count
      setReport(prev => ({
        ...prev,
        download_count: (prev.download_count || 0) + 1
      }));
    } catch (error) {
      console.error('Failed to download report:', error);
      message.error('Failed to download report');
    } finally {
      setDownloading(false);
    }
  };

  // Handle add to basket - same as desktop
  const handleAddToBasket = async () => {
    if (!report) return;
    
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
*This report was exported to your Basket from Report Bee (Mobile).*
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
            source: 'mobile_report_detail',
            report_id: report.id,
            report_title: report.title,
            exported_at: new Date().toISOString()
          }
        })
      });

      setAddedToBasket(true);
      message.success(response.ok ? 'Report added to Basket' : 'Report marked for export');
    } catch (error) {
      console.error('Error adding report to basket:', error);
      setAddedToBasket(true);
      message.info('Report marked for export');
    }
  };

  // Handle retry failed report
  const handleRetry = async () => {
    try {
      const response = await reportApi.retryReport(reportId);
      if (response.success) {
        message.success('Report queued for retry');
        setReport(prev => ({ ...prev, status: 'pending' }));
      }
    } catch (error) {
      console.error('Failed to retry report:', error);
      message.error('Failed to retry report');
    }
  };

  // Handle cancel report
  const handleCancel = async () => {
    try {
      const response = await reportApi.cancelReport(reportId);
      if (response.success) {
        message.success('Report cancelled');
        navigate('/m/reports');
      }
    } catch (error) {
      console.error('Failed to cancel report:', error);
      message.error('Failed to cancel report');
    }
  };

  // Handle copy report info
  const handleCopy = async () => {
    if (!report) return;
    
    const textToCopy = `Report: ${report.title}\nStatus: ${report.status}\nCreated: ${formatDate(report.created_at)}\nID: ${report.id}`;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      message.success('Report info copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      message.error('Failed to copy');
    }
  };

  // Format file size helper
  const formatFileSize = (bytes) => {
    if (!bytes) return null;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  // Handle processing/pending/queued state
  if (report?.status === 'processing' || report?.status === 'pending' || report?.status === 'queued') {
    const statusConfig = getStatusConfig(report.status);
    return (
      <div style={{ padding: '0', minHeight: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <button
            onClick={() => navigate('/m/reports')}
            style={{
              background: '#2a3142',
              border: '1px solid #3a4356',
              borderRadius: '8px',
              padding: '8px',
              color: '#f1f5f9',
              cursor: 'pointer',
            }}
          >
            <ArrowLeftOutlined />
          </button>
          <h1 style={{ margin: 0, flex: 1, fontSize: '18px', fontWeight: 600, color: '#f1f5f9' }}>
            Generating Report...
          </h1>
        </div>

        {/* Processing State Card */}
        <div style={{
          background: '#2a3142',
          borderRadius: '12px',
          border: '1px solid #3a4356',
          padding: '24px',
          textAlign: 'center',
        }}>
          <LoadingOutlined style={{ fontSize: '48px', color: '#eab308', marginBottom: '16px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#f1f5f9' }}>{report.title}</h3>
          <div style={{ marginBottom: '16px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '14px',
              color: statusConfig.color,
              background: `${statusConfig.color}20`,
              padding: '4px 12px',
              borderRadius: '16px',
            }}>
              {statusConfig.icon}
              {statusConfig.label}
            </span>
          </div>
          
          {report.status_message && (
            <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px', fontStyle: 'italic' }}>
              {report.status_message}
            </p>
          )}
          
          {report.progress_percentage > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <Progress 
                percent={report.progress_percentage} 
                size="small" 
                status="active"
                strokeColor={{ '0%': '#f59e0b', '100%': '#10b981' }}
                trailColor="#374151"
              />
            </div>
          )}

          <p style={{ color: '#64748b', fontSize: '12px', marginBottom: '16px' }}>
            Report generation may take a few minutes depending on data complexity.
          </p>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={() => navigate('/m/reports')}
              style={{
                padding: '10px 20px',
                background: 'transparent',
                border: '1px solid #3a4356',
                borderRadius: '8px',
                color: '#f1f5f9',
                cursor: 'pointer',
              }}
            >
              Back to Reports
            </button>
            <button
              onClick={handleCancel}
              style={{
                padding: '10px 20px',
                background: 'transparent',
                border: '1px solid #ef4444',
                borderRadius: '8px',
                color: '#ef4444',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Handle failed state
  if (report?.status === 'failed') {
    return (
      <div style={{ padding: '0', minHeight: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <button
            onClick={() => navigate('/m/reports')}
            style={{
              background: '#2a3142',
              border: '1px solid #3a4356',
              borderRadius: '8px',
              padding: '8px',
              color: '#f1f5f9',
              cursor: 'pointer',
            }}
          >
            <ArrowLeftOutlined />
          </button>
          <h1 style={{ margin: 0, flex: 1, fontSize: '18px', fontWeight: 600, color: '#f1f5f9' }}>
            Report Failed
          </h1>
        </div>

        {/* Failed State Card */}
        <div style={{
          background: '#2a3142',
          borderRadius: '12px',
          border: '1px solid #ef4444',
          padding: '24px',
          textAlign: 'center',
        }}>
          <ExclamationCircleOutlined style={{ fontSize: '48px', color: '#ef4444', marginBottom: '16px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#f1f5f9' }}>{report.title}</h3>
          <p style={{ color: '#ef4444', fontSize: '13px', marginBottom: '16px' }}>
            {report.error_message || 'Report generation failed. Please try again.'}
          </p>
          
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={() => navigate('/m/reports')}
              style={{
                padding: '10px 20px',
                background: 'transparent',
                border: '1px solid #3a4356',
                borderRadius: '8px',
                color: '#f1f5f9',
                cursor: 'pointer',
              }}
            >
              Back to Reports
            </button>
            <button
              onClick={handleRetry}
              style={{
                padding: '10px 20px',
                background: '#ef4444',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Completed report view
  const hasFile = report?.result_file_id;

  return (
    <div style={{ padding: '0', minHeight: '100%', paddingBottom: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <button
          onClick={() => navigate('/m/reports')}
          style={{
            background: '#2a3142',
            border: '1px solid #3a4356',
            borderRadius: '8px',
            padding: '8px',
            color: '#f1f5f9',
            cursor: 'pointer',
          }}
        >
          <ArrowLeftOutlined />
        </button>
        <h1 style={{ margin: 0, flex: 1, fontSize: '18px', fontWeight: 600, color: '#f1f5f9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {report?.title}
        </h1>
      </div>

      {/* Report Info Card */}
      <div style={{
        background: '#2a3142',
        borderRadius: '12px',
        border: '1px solid #3a4356',
        padding: '16px',
        marginBottom: '16px',
      }}>
        {/* Status and Meta */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '12px',
            color: '#52c41a',
            background: 'rgba(82, 196, 26, 0.15)',
            padding: '4px 10px',
            borderRadius: '12px',
          }}>
            <CheckCircleOutlined />
            Completed
          </span>
          {report?.template?.category && (
            <span style={{
              fontSize: '11px',
              color: '#94a3b8',
              background: '#1a1f2e',
              padding: '4px 8px',
              borderRadius: '4px',
            }}>
              {report.template.category}
            </span>
          )}
        </div>

        {/* Description */}
        {report?.description && (
          <p style={{ margin: '0 0 12px 0', color: '#94a3b8', fontSize: '13px', lineHeight: 1.5 }}>
            {report.description}
          </p>
        )}

        {/* Details Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
          <div>
            <span style={{ color: '#64748b' }}>Created: </span>
            <span style={{ color: '#f1f5f9' }}>{formatDate(report?.created_at)}</span>
          </div>
          {report?.completed_at && (
            <div>
              <span style={{ color: '#64748b' }}>Completed: </span>
              <span style={{ color: '#f1f5f9' }}>{formatDate(report.completed_at)}</span>
            </div>
          )}
          {report?.result_size_bytes && (
            <div>
              <span style={{ color: '#64748b' }}>Size: </span>
              <span style={{ color: '#f1f5f9' }}>{formatFileSize(report.result_size_bytes)}</span>
            </div>
          )}
          <div>
            <span style={{ color: '#64748b' }}>Downloads: </span>
            <span style={{ color: '#f1f5f9' }}>{report?.download_count || 0}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}>
        {hasFile && (
          <>
            {/* Download Button - Primary Action */}
            <button
              onClick={handleDownload}
              disabled={downloading}
              style={{
                width: '100%',
                padding: '14px',
                background: downloading ? '#64748b' : '#eab308',
                border: 'none',
                borderRadius: '10px',
                color: '#1a1f2e',
                fontSize: '15px',
                fontWeight: 600,
                cursor: downloading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              {downloading ? (
                <>
                  <Spin size="small" />
                  Downloading...
                </>
              ) : (
                <>
                  <DownloadOutlined style={{ fontSize: '18px' }} />
                  Download Report
                </>
              )}
            </button>

            {/* Secondary Actions Row */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleAddToBasket}
                disabled={addedToBasket}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'transparent',
                  border: '1px solid #3a4356',
                  borderRadius: '10px',
                  color: addedToBasket ? '#52c41a' : '#f1f5f9',
                  fontSize: '14px',
                  cursor: addedToBasket ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <ShoppingCartOutlined />
                {addedToBasket ? 'Added' : 'Add to Basket'}
              </button>
              <button
                onClick={handleCopy}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'transparent',
                  border: '1px solid #3a4356',
                  borderRadius: '10px',
                  color: copied ? '#52c41a' : '#f1f5f9',
                  fontSize: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                {copied ? <CheckCircleOutlined /> : <CopyOutlined />}
                {copied ? 'Copied!' : 'Copy Info'}
              </button>
            </div>
          </>
        )}

        {!hasFile && (
          <div style={{
            padding: '24px',
            background: '#1a1f2e',
            borderRadius: '10px',
            textAlign: 'center',
            color: '#64748b',
          }}>
            <ExclamationCircleOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
            <p style={{ margin: 0, fontSize: '13px' }}>Report file is not available for download.</p>
          </div>
        )}
      </div>

      {/* Template Info */}
      {report?.template && (
        <div style={{
          marginTop: '16px',
          padding: '12px 16px',
          background: '#1a1f2e',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#64748b',
        }}>
          <span style={{ color: '#94a3b8' }}>Template: </span>
          {report.template.display_name || report.template.name}
        </div>
      )}
    </div>
  );
};

export default MobileReportDetail;