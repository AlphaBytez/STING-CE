import React, { useState, useEffect } from 'react';
import { Button, Modal, Spin, Alert, Tabs, Table, Typography, Tag } from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  EyeOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  BarChartOutlined,
  TableOutlined,
  ShoppingCartOutlined,
  CheckOutlined
} from '@ant-design/icons';
import reportApi from '../../services/reportApi';

const { Text, Title } = Typography;
const { TabPane } = Tabs;

const ReportViewer = ({ reportId, isOpen, onClose, reportName }) => {
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [addedToBasket, setAddedToBasket] = useState(false);

  useEffect(() => {
    if (isOpen && reportId) {
      loadReportData();
      setAddedToBasket(false); // Reset basket state for new report
    }
  }, [isOpen, reportId]);

  const loadReportData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await reportApi.getReportDetails(reportId);
      
      if (response.success) {
        setReportData(response.data.report);
      } else {
        setError('Failed to load report data');
      }
    } catch (err) {
      console.error('Error loading report:', err);
      setError('Failed to load report details');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      await reportApi.downloadReport(reportId);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  // Add report to basket (private space / external storage)
  const handleAddToBasket = async () => {
    if (!reportData) return;

    try {
      const timestamp = new Date(reportData.created_at).toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const sanitizedTitle = (reportData.title || 'report').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30);
      const filename = `${sanitizedTitle}_${timestamp}.md`;

      // Build comprehensive report content for basket storage
      const reportContent = `# ${reportData.title}

**Generated:** ${new Date(reportData.created_at).toLocaleString()}
**Status:** ${reportData.status}
**Type:** ${reportData.template?.category || 'analytics'}

## Description
${reportData.description || 'No description provided'}

## Report Summary
${reportData.result_summary ? Object.entries(reportData.result_summary)
  .map(([key, value]) => `- **${key.replace(/_/g, ' ')}:** ${value}`)
  .join('\n') : 'No summary available'}

## Report Details
- **Report ID:** ${reportData.id}
- **Template:** ${reportData.template?.name || 'Unknown'}
- **File Size:** ${reportData.result_size_bytes ? `${(reportData.result_size_bytes / 1024).toFixed(2)} KB` : 'N/A'}
- **Downloads:** ${reportData.download_count || 0}
- **Created:** ${new Date(reportData.created_at).toLocaleString()}
- **Completed:** ${reportData.completed_at ? new Date(reportData.completed_at).toLocaleString() : 'N/A'}

---
*This report was exported to your Basket from STING Bee Reports.*
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
            source: 'report_viewer',
            report_id: reportData.id,
            report_title: reportData.title,
            report_status: reportData.status,
            template_category: reportData.template?.category,
            created_at: reportData.created_at,
            exported_at: new Date().toISOString()
          }
        })
      });

      setAddedToBasket(true);
      console.log('📦 Report added to basket:', filename);
    } catch (error) {
      console.error('Error adding report to basket:', error);
      setAddedToBasket(true); // Still mark as added for UX
    }
  };

  const renderOverviewTab = () => {
    if (!reportData) return null;

    return (
      <div className="space-y-6">
        {/* Report Header */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <Title level={3} className="text-white mb-2">{reportData.title}</Title>
              <Text className="text-gray-400">{reportData.description}</Text>
            </div>
            <Tag color={getStatusColor(reportData.status)} className="text-sm px-3 py-1">
              {reportData.status}
            </Tag>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="text-center">
              <Text className="text-gray-500 text-sm">Created</Text>
              <div className="text-white font-medium">
                {new Date(reportData.created_at).toLocaleDateString()}
              </div>
            </div>
            <div className="text-center">
              <Text className="text-gray-500 text-sm">Completed</Text>
              <div className="text-white font-medium">
                {reportData.completed_at 
                  ? new Date(reportData.completed_at).toLocaleDateString()
                  : 'In Progress'
                }
              </div>
            </div>
            <div className="text-center">
              <Text className="text-gray-500 text-sm">Size</Text>
              <div className="text-white font-medium">
                {formatFileSize(reportData.result_size_bytes)}
              </div>
            </div>
            <div className="text-center">
              <Text className="text-gray-500 text-sm">Downloads</Text>
              <div className="text-white font-medium">
                {reportData.download_count || 0}
              </div>
            </div>
          </div>
        </div>

        {/* Report Summary */}
        {reportData.result_summary && (
          <div className="bg-gray-800 rounded-lg p-6">
            <Title level={4} className="text-white mb-4 flex items-center">
              <InfoCircleOutlined className="mr-2" />
              Report Summary
            </Title>
            <div className="space-y-3">
              {Object.entries(reportData.result_summary).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <Text className="text-gray-400 capitalize">
                    {key.replace(/_/g, ' ')}
                  </Text>
                  <Text className="text-white">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </Text>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Report Parameters */}
        {reportData.parameters && Object.keys(reportData.parameters).length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6">
            <Title level={4} className="text-white mb-4">Report Parameters</Title>
            <div className="space-y-2">
              {Object.entries(reportData.parameters).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <Text className="text-gray-400 capitalize">
                    {key.replace(/_/g, ' ')}
                  </Text>
                  <Text className="text-white">
                    {String(value)}
                  </Text>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Template Information */}
        {reportData.template && (
          <div className="bg-gray-800 rounded-lg p-6">
            <Title level={4} className="text-white mb-4">Template Details</Title>
            <div className="space-y-2">
              <div className="flex justify-between">
                <Text className="text-gray-400">Template</Text>
                <Text className="text-white">{reportData.template.display_name}</Text>
              </div>
              <div className="flex justify-between">
                <Text className="text-gray-400">Category</Text>
                <Tag color={getTypeColor(reportData.template.category)}>
                  {reportData.template.category}
                </Tag>
              </div>
              <div className="flex justify-between">
                <Text className="text-gray-400">Security Level</Text>
                <Text className="text-white">{reportData.template.security_level}</Text>
              </div>
              {reportData.template.requires_scrambling && (
                <div className="flex justify-between">
                  <Text className="text-gray-400">PII Protection</Text>
                  <Tag color="green">Enabled</Tag>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderDataTab = () => {
    if (!reportData || !reportData.result_summary) {
      return (
        <div className="text-center py-12">
          <TableOutlined className="text-4xl text-gray-600 mb-4" />
          <Text className="text-gray-400">
            No data preview available. Download the report to view complete data.
          </Text>
        </div>
      );
    }

    // Create a simple data preview from the summary
    const summaryData = Object.entries(reportData.result_summary).map(([key, value], index) => ({
      key: index,
      metric: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      value: typeof value === 'number' ? value.toLocaleString() : String(value)
    }));

    const columns = [
      {
        title: 'Metric',
        dataIndex: 'metric',
        key: 'metric',
        className: 'text-white'
      },
      {
        title: 'Value',
        dataIndex: 'value',
        key: 'value',
        className: 'text-white'
      }
    ];

    return (
      <div className="space-y-4">
        <Alert
          message="Data Preview"
          description="This is a summary view. Download the complete report for detailed data and charts."
          type="info"
          showIcon
          className="mb-4"
        />
        
        <Table
          columns={columns}
          dataSource={summaryData}
          pagination={false}
          size="small"
          className="modern-table"
          style={{
            backgroundColor: 'transparent',
            '--ant-table-bg': 'rgba(55, 65, 81, 0.8)',
            '--ant-table-header-bg': 'rgba(75, 85, 99, 0.8)',
            '--ant-table-row-hover-bg': 'rgba(75, 85, 99, 0.5)'
          }}
        />
      </div>
    );
  };

  const renderChartsTab = () => {
    return (
      <div className="text-center py-12">
        <BarChartOutlined className="text-6xl text-gray-600 mb-4" />
        <Title level={4} className="text-gray-400 mb-2">Charts Coming Soon</Title>
        <Text className="text-gray-400">
          Interactive charts and visualizations will be available in a future update.
        </Text>
        <div className="mt-6">
          <Button 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            className="bg-yellow-500 hover:bg-yellow-600 border-yellow-500"
          >
            Download Full Report with Charts
          </Button>
        </div>
      </div>
    );
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'green';
      case 'processing': return 'blue';
      case 'failed': return 'red';
      case 'queued': return 'orange';
      default: return 'default';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'security': return 'red';
      case 'analytics': return 'blue';
      case 'compliance': return 'purple';
      case 'performance': return 'green';
      case 'storage': return 'orange';
      default: return 'default';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <EyeOutlined className="text-yellow-400" />
          <span className="text-white">Report Viewer</span>
          {reportName && <span className="text-gray-400">- {reportName}</span>}
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      footer={[
        <Button
          key="basket"
          icon={addedToBasket ? <CheckOutlined /> : <ShoppingCartOutlined />}
          onClick={handleAddToBasket}
          disabled={addedToBasket}
          className={addedToBasket ? "border-green-500 text-green-500" : ""}
        >
          {addedToBasket ? 'Added to Basket' : 'Add to Basket'}
        </Button>,
        <Button key="download" type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
          Download Report
        </Button>,
        <Button key="close" onClick={onClose}>
          Close
        </Button>
      ]}
      width={900}
      className="dark-modal"
      styles={{
        body: { backgroundColor: '#1f2937', color: '#e5e7eb' },
        header: { backgroundColor: '#374151', color: '#e5e7eb', borderBottom: '1px solid #4b5563' }
      }}
    >
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <Spin size="large" />
        </div>
      ) : error ? (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          className="mb-4"
          action={
            <Button size="small" onClick={loadReportData}>
              Retry
            </Button>
          }
        />
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          className="dark-tabs"
          items={[
            {
              key: 'overview',
              label: (
                <span className="flex items-center gap-2">
                  <InfoCircleOutlined />
                  Overview
                </span>
              ),
              children: renderOverviewTab()
            },
            {
              key: 'data',
              label: (
                <span className="flex items-center gap-2">
                  <TableOutlined />
                  Data Preview
                </span>
              ),
              children: renderDataTab()
            },
            {
              key: 'charts',
              label: (
                <span className="flex items-center gap-2">
                  <BarChartOutlined />
                  Charts
                </span>
              ),
              children: renderChartsTab()
            }
          ]}
        />
      )}
    </Modal>
  );
};

export default ReportViewer;