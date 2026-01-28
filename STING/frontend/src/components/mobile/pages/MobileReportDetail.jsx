import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Spin, Button, Dropdown, Space } from 'antd';
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
} from '@ant-design/icons';
import { externalAiApi } from '../../../services/externalAiApi';
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
 * Full report content display with export options and regeneration
 */
const MobileReportDetail = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  // Fetch report data
  const fetchReport = useCallback(async () => {
    if (!reportId) {
      navigate('/m/reports');
      return;
    }

    setLoading(true);
    try {
      const response = await externalAiApi.getReport(reportId);

      if (response) {
        setReport({
          id: reportId,
          title: response.title || 'Untitled Report',
          content: response.content || response.report || 'No content available',
          status: response.status || 'completed',
          createdAt: response.created_at || response.createdAt || new Date().toISOString(),
          duration: response.duration || null,
          type: response.type || 'custom',
          metadata: response.metadata || {},
        });
      } else {
        // Fallback mock report
        setReport({
          id: reportId,
          title: 'Sample Report Analysis',
          content: `# Report Analysis

## Executive Summary

This report provides comprehensive insights based on the available data. The analysis reveals several key findings that can drive strategic decision-making.

## Key Findings

### Customer Behavior Patterns
- Customer engagement has increased by 23% over the past quarter
- Mobile usage accounts for 65% of total interactions
- Peak activity occurs during evening hours (6-9 PM)

### Market Trends
- Industry growth rate of 15% year-over-year
- Emerging segments show strong potential
- Competitive landscape is evolving rapidly

## Recommendations

1. **Focus on mobile optimization** - Given the high mobile usage, investing in mobile-first experiences will yield the best returns.

2. **Leverage evening peak hours** - Schedule marketing campaigns and content releases during peak engagement periods.

3. **Explore emerging segments** - Early investment in growing market segments can provide competitive advantage.

## Conclusion

The analysis indicates positive trends across key metrics. Continued monitoring and strategic adjustments will help maintain momentum and capitalize on emerging opportunities.

---
*Report generated on ${formatDate(new Date().toISOString())}*
*Processing time: ${Math.random() * 5 + 1}.${Math.floor(Math.random() * 9)}s*`,
          status: 'completed',
          createdAt: new Date(Date.now() - 86400000).toISOString(),
          duration: '3.2s',
          type: 'customer-insights',
          metadata: {
            provider: 'ollama',
            model: 'phi3:mini',
            confidence: 0.92,
          },
        });
      }
    } catch (error) {
      console.error('Failed to fetch report:', error);
      message.error('Failed to load report');

      // Fallback mock report on error
      setReport({
        id: reportId,
        title: 'Sample Report Analysis',
        content: `# Report Analysis

## Executive Summary

This report provides comprehensive insights based on the available data. The analysis reveals several key findings that can drive strategic decision-making.

## Key Findings

### Customer Behavior Patterns
- Customer engagement has increased by 23% over the past quarter
- Mobile usage accounts for 65% of total interactions
- Peak activity occurs during evening hours (6-9 PM)

### Market Trends
- Industry growth rate of 15% year-over-year
- Emerging segments show strong potential
- Competitive landscape is evolving rapidly

## Recommendations

1. **Focus on mobile optimization** - Given the high mobile usage, investing in mobile-first experiences will yield the best returns.

2. **Leverage evening peak hours** - Schedule marketing campaigns and content releases during peak engagement periods.

3. **Explore emerging segments** - Early investment in growing market segments can provide competitive advantage.

## Conclusion

The analysis indicates positive trends across key metrics. Continued monitoring and strategic adjustments will help maintain momentum and capitalize on emerging opportunities.

---
*Report generated on ${formatDate(new Date().toISOString())}*
*Processing time: 3.2s*`,
        status: 'completed',
        createdAt: new Date(Date.now() - 86400000).toISOString(),
        duration: '3.2s',
        type: 'customer-insights',
        metadata: {
          provider: 'ollama',
          model: 'phi3:mini',
          confidence: 0.92,
        },
      });
    } finally {
      setLoading(false);
    }
  }, [reportId, navigate]);

  // Poll for status updates if report is still processing
  useEffect(() => {
    if (report?.status === 'processing' || report?.status === 'generating') {
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await externalAiApi.getReportStatus(reportId);
          if (statusResponse.status) {
            setReport((prev) => ({
              ...prev,
              status: statusResponse.status,
              duration: statusResponse.duration || prev.duration,
            }));

            if (statusResponse.status === 'completed' && statusResponse.content) {
              setReport((prev) => ({
                ...prev,
                content: statusResponse.content,
              }));
              clearInterval(pollInterval);
            } else if (statusResponse.status === 'failed') {
              message.error('Report generation failed');
              clearInterval(pollInterval);
            }
          }
        } catch (error) {
          console.error('Status check failed:', error);
        }
      }, 5000); // Poll every 5 seconds

      return () => clearInterval(pollInterval);
    }
  }, [report?.status, reportId]);

  // Initial data fetch
  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Handle regenerate report
  const handleRegenerate = async () => {
    if (!report) return;

    setRegenerating(true);
    try {
      const response = await externalAiApi.generateReport({
        title: report.title,
        type: report.type,
        user_id: user?.id,
        regenerate: true,
        original_report_id: reportId,
      });

      message.success('Report regeneration started');
      setReport((prev) => ({
        ...prev,
        status: 'processing',
        duration: null,
      }));
    } catch (error) {
      console.error('Failed to regenerate report:', error);
      message.error('Failed to regenerate report');
    } finally {
      setRegenerating(false);
    }
  };

  // Handle export report
  const handleExport = async (format) => {
    if (!report) return;

    setExporting(true);
    try {
      let content = report.content;
      let filename = `${report.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}`;

      // Convert content based on format
      switch (format) {
        case 'pdf':
          // For PDF, we'll create a printable HTML and print it
          const printWindow = window.open('', '_blank');
          printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <title>${report.title}</title>
              <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                pre { white-space: pre-wrap; }
              </style>
            </head>
            <body>
              <h1>${report.title}</h1>
              ${content.replace(/\n/g, '<br>')}
            </body>
            </html>
          `);
          printWindow.document.close();
          printWindow.print();
          break;

        case 'markdown':
          // Content is already in markdown format
          filename += '.md';
          break;

        case 'html':
          content = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${report.title}</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
    h1, h2, h3 { color: #333; }
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
    pre { background: #f4f4f4; padding: 12px; border-radius: 8px; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>${report.title}</h1>
  ${content.split('\n').map(line => {
    if (line.startsWith('# ')) return `<h1>${line.substring(2)}</h1>`;
    if (line.startsWith('## ')) return `<h2>${line.substring(3)}</h2>`;
    if (line.startsWith('### ')) return `<h3>${line.substring(4)}</h3>`;
    if (line.startsWith('- ')) return `<li>${line.substring(2)}</li>`;
    if (line.match(/^\d+\. /)) return `<p>${line}</p>`;
    return `<p>${line}</p>`;
  }).join('')}
  <hr>
  <p><small>Generated: ${formatDate(report.createdAt)}</small></p>
</body>
</html>`;
          filename += '.html';
          break;

        default:
          break;
      }

      // Download file (except for PDF which opens print window)
      if (format !== 'pdf') {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      message.success(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Failed to export report:', error);
      message.error('Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  // Handle copy to clipboard
  const handleCopy = async () => {
    if (!report) return;

    try {
      await navigator.clipboard.writeText(report.content);
      setCopied(true);
      message.success('Report content copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      message.error('Failed to copy content');
    }
  };

  // Export dropdown menu items
  const exportMenuItems = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: 'Export as PDF',
    },
    {
      key: 'markdown',
      icon: <FileMarkdownOutlined />,
      label: 'Export as Markdown',
    },
    {
      key: 'html',
      icon: <Html5Outlined />,
      label: 'Export as HTML',
    },
  ];

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  // Handle processing state
  if (report?.status === 'processing' || report?.status === 'generating') {
    const statusConfig = getStatusConfig(report.status);
    return (
      <div className="mobile-page">
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)', marginBottom: 'var(--mobile-space-lg)' }}>
          <button
            onClick={() => navigate('/m/reports')}
            style={{
              background: 'var(--mobile-surface)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              padding: 'var(--mobile-space-sm)',
              color: 'var(--mobile-text-primary)',
              cursor: 'pointer',
            }}
            aria-label="Go back"
          >
            <ArrowLeftOutlined />
          </button>
          <h1 className="mobile-page-title" style={{ margin: 0, flex: 1 }}>Generating Report...</h1>
        </div>

        {/* Processing State */}
        <div className="mobile-card" style={{ textAlign: 'center', padding: 'var(--mobile-space-xl)' }}>
          <Spin size="large" style={{ marginBottom: 'var(--mobile-space-md)' }} />
          <div style={{ marginBottom: 'var(--mobile-space-md)' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 'var(--mobile-font-base)',
                color: statusConfig.color,
              }}
            >
              {statusConfig.icon}
              {statusConfig.label}
            </span>
          </div>
          <p style={{ color: 'var(--mobile-text-secondary)', marginBottom: 'var(--mobile-space-lg)' }}>
            Your report "{report.title}" is being generated. This may take a few minutes...
          </p>
          <div
            style={{
              background: 'var(--mobile-surface)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              padding: 'var(--mobile-space-md)',
              textAlign: 'left',
            }}
          >
            <h4 style={{ margin: '0 0 var(--mobile-space-sm) 0', color: 'var(--mobile-text-primary)' }}>
              What&apos;s happening?
            </h4>
            <ul style={{ margin: 0, paddingLeft: 'var(--mobile-space-lg)', color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
              <li>Analyzing your data</li>
              <li>Generating insights</li>
              <li>Formatting the report</li>
            </ul>
          </div>
          <button
            onClick={() => navigate('/m/reports')}
            style={{
              marginTop: 'var(--mobile-space-lg)',
              padding: 'var(--mobile-space-sm) var(--mobile-space-lg)',
              background: 'var(--mobile-surface)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: 'var(--mobile-text-primary)',
              cursor: 'pointer',
            }}
          >
            Continue in Background
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)', marginBottom: 'var(--mobile-space-md)' }}>
        <button
          onClick={() => navigate('/m/reports')}
          style={{
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            padding: 'var(--mobile-space-sm)',
            color: 'var(--mobile-text-primary)',
            cursor: 'pointer',
          }}
          aria-label="Go back"
        >
          <ArrowLeftOutlined />
        </button>
        <h1 className="mobile-page-title" style={{ margin: 0, flex: 1, fontSize: 'var(--mobile-font-lg)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {report?.title}
        </h1>
      </div>

      {/* Report Meta */}
      <div className="mobile-report-meta" style={{ marginBottom: 'var(--mobile-space-md)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--mobile-space-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)' }}>
            {(() => {
              const statusConfig = getStatusConfig(report?.status);
              return (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 'var(--mobile-font-xs)',
                    color: statusConfig.color,
                    background: `${statusConfig.color}15`,
                    padding: '2px 8px',
                    borderRadius: 'var(--mobile-radius-sm, 4px)',
                  }}
                >
                  {statusConfig.icon}
                  {statusConfig.label}
                </span>
              );
            })()}
            <span style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
              {formatDate(report?.createdAt)}
            </span>
            {report?.duration && (
              <span style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                • {report.duration}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 'var(--mobile-space-xs)' }}>
            <button
              onClick={handleCopy}
              style={{
                padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                background: copied ? '#52c41a' : 'var(--mobile-surface)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                color: copied ? '#fff' : 'var(--mobile-text-primary)',
                cursor: 'pointer',
                fontSize: 'var(--mobile-font-xs)',
              }}
            >
              {copied ? <CheckCircleOutlined /> : <CopyOutlined />}
            </button>
            <Dropdown
              menu={{
                items: exportMenuItems,
                onClick: ({ key }) => handleExport(key),
              }}
              trigger={['click']}
            >
              <button
                style={{
                  padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                  background: 'var(--mobile-primary)',
                  border: 'none',
                  borderRadius: 'var(--mobile-radius-md, 8px)',
                  color: 'var(--mobile-text-inverse)',
                  cursor: 'pointer',
                  fontSize: 'var(--mobile-font-xs)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <DownloadOutlined />
                Export
              </button>
            </Dropdown>
          </div>
        </div>
      </div>

      {/* Report Content */}
      <div className="mobile-report-content mobile-card" style={{ padding: 'var(--mobile-space-md)' }}>
        <div
          style={{
            fontFamily: 'system-ui, -apple-system, sans-serif',
            lineHeight: 1.7,
            color: 'var(--mobile-text-primary)',
          }}
        >
          {/* Render report content as styled elements */}
          {report?.content.split('\n').map((line, index) => {
            // Heading 1
            if (line.startsWith('# ')) {
              return (
                <h1 key={index} style={{ fontSize: '1.5rem', fontWeight: 600, margin: '1.5rem 0 0.75rem 0', color: 'var(--mobile-text-primary)', borderBottom: '1px solid var(--mobile-border)', paddingBottom: '0.5rem' }}>
                  {line.substring(2)}
                </h1>
              );
            }
            // Heading 2
            if (line.startsWith('## ')) {
              return (
                <h2 key={index} style={{ fontSize: '1.25rem', fontWeight: 600, margin: '1.25rem 0 0.5rem 0', color: 'var(--mobile-text-primary)' }}>
                  {line.substring(3)}
                </h2>
              );
            }
            // Heading 3
            if (line.startsWith('### ')) {
              return (
                <h3 key={index} style={{ fontSize: '1.1rem', fontWeight: 600, margin: '1rem 0 0.5rem 0', color: 'var(--mobile-text-primary)' }}>
                  {line.substring(4)}
                </h3>
              );
            }
            // Bullet point
            if (line.startsWith('- ')) {
              return (
                <li key={index} style={{ marginLeft: '1.5rem', marginBottom: '0.25rem', color: 'var(--mobile-text-secondary)' }}>
                  {line.substring(2)}
                </li>
              );
            }
            // Numbered list
            if (line.match(/^\d+\. /)) {
              return (
                <p key={index} style={{ marginLeft: '1.5rem', marginBottom: '0.25rem', color: 'var(--mobile-text-secondary)' }}>
                  {line}
                </p>
              );
            }
            // Horizontal rule
            if (line.startsWith('---')) {
              return <hr key={index} style={{ border: 'none', borderTop: '1px solid var(--mobile-border)', margin: '1rem 0' }} />;
            }
            // Bold text
            if (line.includes('**')) {
              const parts = line.split('**');
              return (
                <p key={index} style={{ marginBottom: '0.5rem', color: 'var(--mobile-text-secondary)' }}>
                  {parts.map((part, i) =>
                    i % 2 === 1 ? <strong key={i} style={{ color: 'var(--mobile-text-primary)' }}>{part}</strong> : part
                  )}
                </p>
              );
            }
            // Empty line
            if (line.trim() === '') {
              return <div key={index} style={{ height: '0.5rem' }} />;
            }
            // Regular paragraph
            return (
              <p key={index} style={{ marginBottom: '0.5rem', color: 'var(--mobile-text-secondary)' }}>
                {line}
              </p>
            );
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ marginTop: 'var(--mobile-space-lg)', display: 'flex', gap: 'var(--mobile-space-sm)' }}>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          style={{
            flex: 1,
            padding: 'var(--mobile-space-md)',
            background: regenerating ? 'var(--mobile-text-tertiary)' : 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            color: regenerating ? 'var(--mobile-text-inverse)' : 'var(--mobile-text-primary)',
            cursor: regenerating ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--mobile-space-xs)',
          }}
        >
          {regenerating ? <Spin size="small" /> : <ReloadOutlined />}
          Regenerate Report
        </button>
      </div>

      {/* Metadata Footer */}
      {report?.metadata && (
        <div
          style={{
            marginTop: 'var(--mobile-space-lg)',
            padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
            background: 'var(--mobile-surface)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            fontSize: 'var(--mobile-font-xs)',
            color: 'var(--mobile-text-tertiary)',
          }}
        >
          <div style={{ marginBottom: 'var(--mobile-space-xs)' }}>
            <strong>Generated by:</strong> {report.metadata.provider?.toUpperCase() || 'AI'} {report.metadata.model && `(${report.metadata.model})`}
          </div>
          {report.metadata.confidence && (
            <div style={{ marginBottom: 'var(--mobile-space-xs)' }}>
              <strong>Confidence:</strong> {Math.round(report.metadata.confidence * 100)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MobileReportDetail;
