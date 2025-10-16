import React, { useState } from 'react';
import { Modal, Tabs, Button, Input, Select, Card, Typography, Space, message, Alert, Divider } from 'antd';
import { 
  ShareAltOutlined, 
  LinkOutlined, 
  MailOutlined, 
  DownloadOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  SafetyOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import reportApi from '../../services/reportApi';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const ReportShareModal = ({ reportId, reportName, isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('link');
  const [shareResult, setShareResult] = useState(null);

  // Link sharing state
  const [linkGenerated, setLinkGenerated] = useState(false);
  const [shareUrl, setShareUrl] = useState('');

  // Email sharing state
  const [emailRecipients, setEmailRecipients] = useState([]);
  const [emailMessage, setEmailMessage] = useState('');
  const [currentEmail, setCurrentEmail] = useState('');

  // Download token state
  const [downloadToken, setDownloadToken] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');

  const handleGenerateLink = async () => {
    try {
      setLoading(true);
      const response = await reportApi.shareReport(reportId, { method: 'link' });
      
      if (response.success) {
        const fullUrl = `${window.location.origin}${response.data.share_url}`;
        setShareUrl(fullUrl);
        setLinkGenerated(true);
        setShareResult(response.data);
        message.success('Shareable link generated successfully');
      }
    } catch (error) {
      message.error('Failed to generate shareable link');
      console.error('Link generation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    message.success('Link copied to clipboard');
  };

  const handleAddEmail = () => {
    if (currentEmail && !emailRecipients.includes(currentEmail)) {
      setEmailRecipients([...emailRecipients, currentEmail]);
      setCurrentEmail('');
    }
  };

  const handleRemoveEmail = (email) => {
    setEmailRecipients(emailRecipients.filter(e => e !== email));
  };

  const handleSendEmail = async () => {
    try {
      setLoading(true);
      const response = await reportApi.shareReport(reportId, {
        method: 'email',
        recipients: emailRecipients,
        message: emailMessage
      });
      
      if (response.success) {
        setShareResult(response.data);
        message.info(response.data.message);
      }
    } catch (error) {
      message.error('Failed to send email');
      console.error('Email sharing error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDownloadToken = async () => {
    try {
      setLoading(true);
      const response = await reportApi.shareReport(reportId, { method: 'download_token' });
      
      if (response.success) {
        setDownloadToken(response.data.download_token);
        setDownloadUrl(response.data.download_url);
        setShareResult(response.data);
        message.success('Download token generated successfully');
      }
    } catch (error) {
      message.error('Failed to generate download token');
      console.error('Download token error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyDownloadUrl = () => {
    const fullUrl = `${window.location.origin}${downloadUrl}`;
    navigator.clipboard.writeText(fullUrl);
    message.success('Download URL copied to clipboard');
  };

  const resetModal = () => {
    setActiveTab('link');
    setShareResult(null);
    setLinkGenerated(false);
    setShareUrl('');
    setEmailRecipients([]);
    setEmailMessage('');
    setCurrentEmail('');
    setDownloadToken('');
    setDownloadUrl('');
  };

  const handleModalClose = () => {
    resetModal();
    onClose();
  };

  const renderLinkTab = () => (
    <div className="space-y-6">
      <Alert
        message="Shareable Link"
        description="Generate a shareable URL that allows other users to access this report. Recipients will need appropriate permissions to view the report."
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        className="mb-4"
      />

      {!linkGenerated ? (
        <div className="text-center py-8">
          <LinkOutlined className="text-6xl text-gray-400 mb-4" />
          <Title level={4} className="text-gray-400 mb-4">Generate Shareable Link</Title>
          <Button 
            type="primary" 
            size="large" 
            icon={<ShareAltOutlined />}
            onClick={handleGenerateLink}
            loading={loading}
            className="bg-yellow-500 hover:bg-yellow-600 border-yellow-500"
          >
            Generate Link
          </Button>
        </div>
      ) : (
        <Card className="bg-gray-800 border-gray-600">
          <div className="space-y-4">
            <div>
              <Text className="text-gray-400 text-sm">Shareable URL:</Text>
              <div className="flex gap-2 mt-2">
                <Input 
                  value={shareUrl} 
                  readOnly 
                  className="flex-1 dark-search-input"
                  style={{
                    backgroundColor: 'rgba(55, 65, 81, 0.8)',
                    borderColor: 'rgba(75, 85, 99, 0.5)',
                    color: '#e2e8f0'
                  }}
                />
                <Button 
                  icon={<CopyOutlined />} 
                  onClick={handleCopyLink}
                  className="text-gray-400 hover:text-yellow-400"
                >
                  Copy
                </Button>
              </div>
            </div>
            
            {shareResult?.expires_at && (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <ClockCircleOutlined />
                <span>Expires: {new Date(shareResult.expires_at).toLocaleDateString()}</span>
              </div>
            )}
            
            <Alert
              message="Security Notice"
              description={shareResult?.message || "Recipients will need to authenticate and have appropriate permissions to access this report."}
              type="warning"
              showIcon
              icon={<SafetyOutlined />}
              className="mt-4"
            />
          </div>
        </Card>
      )}
    </div>
  );

  const renderEmailTab = () => (
    <div className="space-y-6">
      <Alert
        message="Email Sharing"
        description="Share the report directly via email. Recipients will receive instructions on how to access the report."
        type="info"
        showIcon
        icon={<MailOutlined />}
        className="mb-4"
      />

      <div>
        <Text className="text-white text-sm mb-2 block">Recipients:</Text>
        <div className="flex gap-2 mb-3">
          <Input
            placeholder="Enter email address"
            value={currentEmail}
            onChange={(e) => setCurrentEmail(e.target.value)}
            onPressEnter={handleAddEmail}
            className="dark-search-input"
            style={{
              backgroundColor: 'rgba(55, 65, 81, 0.8)',
              borderColor: 'rgba(75, 85, 99, 0.5)',
              color: '#e2e8f0'
            }}
          />
          <Button onClick={handleAddEmail} disabled={!currentEmail}>
            Add
          </Button>
        </div>
        
        {emailRecipients.length > 0 && (
          <div className="space-y-2">
            {emailRecipients.map((email, index) => (
              <div key={index} className="flex justify-between items-center bg-gray-700 px-3 py-2 rounded">
                <Text className="text-white">{email}</Text>
                <Button 
                  type="text" 
                  size="small" 
                  danger 
                  onClick={() => handleRemoveEmail(email)}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <Text className="text-white text-sm mb-2 block">Message (Optional):</Text>
        <TextArea
          placeholder="Add a message for the recipients..."
          value={emailMessage}
          onChange={(e) => setEmailMessage(e.target.value)}
          rows={4}
          className="dark-search-input"
          style={{
            backgroundColor: 'rgba(55, 65, 81, 0.8)',
            borderColor: 'rgba(75, 85, 99, 0.5)',
            color: '#e2e8f0'
          }}
        />
      </div>

      <Button
        type="primary"
        block
        size="large"
        icon={<MailOutlined />}
        onClick={handleSendEmail}
        loading={loading}
        disabled={emailRecipients.length === 0}
        className="bg-blue-500 hover:bg-blue-600 border-blue-500"
      >
        Send Email ({emailRecipients.length} recipient{emailRecipients.length !== 1 ? 's' : ''})
      </Button>

      {shareResult && (
        <Alert
          message="Email Sharing Status"
          description={shareResult.message}
          type="info"
          showIcon
          className="mt-4"
        />
      )}
    </div>
  );

  const renderDownloadTokenTab = () => (
    <div className="space-y-6">
      <Alert
        message="Temporary Download Link"
        description="Generate a temporary download link that allows direct access to the report file without requiring authentication."
        type="info"
        showIcon
        icon={<DownloadOutlined />}
        className="mb-4"
      />

      {!downloadToken ? (
        <div className="text-center py-8">
          <DownloadOutlined className="text-6xl text-gray-400 mb-4" />
          <Title level={4} className="text-gray-400 mb-4">Generate Download Token</Title>
          <Button 
            type="primary" 
            size="large" 
            icon={<DownloadOutlined />}
            onClick={handleGenerateDownloadToken}
            loading={loading}
            className="bg-green-500 hover:bg-green-600 border-green-500"
          >
            Generate Download Link
          </Button>
        </div>
      ) : (
        <Card className="bg-gray-800 border-gray-600">
          <div className="space-y-4">
            <div>
              <Text className="text-gray-400 text-sm">Download URL:</Text>
              <div className="flex gap-2 mt-2">
                <Input 
                  value={`${window.location.origin}${downloadUrl}`} 
                  readOnly 
                  className="flex-1 dark-search-input"
                  style={{
                    backgroundColor: 'rgba(55, 65, 81, 0.8)',
                    borderColor: 'rgba(75, 85, 99, 0.5)',
                    color: '#e2e8f0'
                  }}
                />
                <Button 
                  icon={<CopyOutlined />} 
                  onClick={handleCopyDownloadUrl}
                  className="text-gray-400 hover:text-yellow-400"
                >
                  Copy
                </Button>
              </div>
            </div>
            
            <div>
              <Text className="text-gray-400 text-sm">Token:</Text>
              <div className="bg-gray-700 p-3 rounded mt-2 font-mono text-sm text-gray-300 break-all">
                {downloadToken}
              </div>
            </div>
            
            <Alert
              message="Security Warning"
              description="This link provides direct access to the report file. Share it securely and ensure recipients are trusted. The link expires in 24 hours."
              type="warning"
              showIcon
              icon={<SafetyOutlined />}
              className="mt-4"
            />
          </div>
        </Card>
      )}
    </div>
  );

  const tabItems = [
    {
      key: 'link',
      label: (
        <span className="flex items-center gap-2">
          <LinkOutlined />
          Shareable Link
        </span>
      ),
      children: renderLinkTab()
    },
    {
      key: 'email',
      label: (
        <span className="flex items-center gap-2">
          <MailOutlined />
          Email
        </span>
      ),
      children: renderEmailTab()
    },
    {
      key: 'download',
      label: (
        <span className="flex items-center gap-2">
          <DownloadOutlined />
          Download Token
        </span>
      ),
      children: renderDownloadTokenTab()
    }
  ];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <ShareAltOutlined className="text-yellow-400" />
          <span className="text-white">Share Report</span>
          {reportName && <span className="text-gray-400">- {reportName}</span>}
        </div>
      }
      open={isOpen}
      onCancel={handleModalClose}
      footer={[
        <Button key="close" onClick={handleModalClose}>
          Close
        </Button>
      ]}
      width={700}
      className="dark-modal"
      styles={{
        body: { backgroundColor: '#1f2937', color: '#e5e7eb' },
        header: { backgroundColor: '#374151', color: '#e5e7eb', borderBottom: '1px solid #4b5563' }
      }}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        className="dark-tabs"
        size="large"
        style={{
          '--ant-tabs-tab-color': '#9ca3af',
          '--ant-tabs-tab-color-hover': '#f59e0b',
          '--ant-tabs-tab-color-active': '#f59e0b',
          '--ant-tabs-ink-bar-color': '#f59e0b'
        }}
      />
    </Modal>
  );
};

export default ReportShareModal;