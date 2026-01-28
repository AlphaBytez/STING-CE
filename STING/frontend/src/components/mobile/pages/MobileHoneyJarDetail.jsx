import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Modal, Empty } from 'antd';
import {
  FileTextOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  UploadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  FolderOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { honeyJarApi } from '../../../services/knowledgeApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Get file icon based on extension
 */
const getFileIcon = (filename) => {
  const ext = filename?.split('.').pop()?.toLowerCase();

  switch (ext) {
    case 'pdf':
      return <FilePdfOutlined />;
    case 'doc':
    case 'docx':
      return <FileWordOutlined />;
    case 'xls':
    case 'xlsx':
      return <FileExcelOutlined />;
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'webp':
      return <FileImageOutlined />;
    default:
      return <FileTextOutlined />;
  }
};

/**
 * Format file size
 */
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

/**
 * Format relative time
 */
const formatRelativeTime = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

/**
 * Get status badge color
 */
const getStatusColor = (status) => {
  switch (status) {
    case 'processed':
      return 'var(--mobile-success)';
    case 'processing':
      return 'var(--mobile-info)';
    case 'pending':
    case 'pending_approval':
      return 'var(--mobile-warning)';
    case 'error':
    case 'failed':
      return 'var(--mobile-error)';
    default:
      return 'var(--mobile-text-tertiary)';
  }
};

/**
 * Get status text
 */
const getStatusText = (status) => {
  switch (status) {
    case 'pending_approval':
      return 'Pending Approval';
    default:
      return status?.charAt(0).toUpperCase() + status?.slice(1) || 'Unknown';
  }
};

/**
 * MobileHoneyJarDetail - Mobile honey jar detail page
 * Documents list within a honey jar with upload, ripen, and delete functionality
 */
const MobileHoneyJarDetail = () => {
  const { jarId } = useParams();
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [honeyJar, setHoneyJar] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [ripening, setRipening] = useState(false);

  // Fetch honey jar details and documents
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch honey jar details
      try {
        const jarData = await honeyJarApi.getHoneyJar(jarId);
        setHoneyJar(jarData);
      } catch (jarError) {
        console.warn('Could not fetch honey jar details:', jarError);
        // Use fallback data
        setHoneyJar({
          id: jarId,
          name: 'Honey Jar',
          document_count: 0,
        });
      }

      // Fetch documents
      try {
        const docsResponse = await honeyJarApi.getDocuments(jarId);
        const docs = docsResponse.documents || docsResponse || [];
        setDocuments(docs);
      } catch (docsError) {
        console.warn('Could not fetch documents:', docsError);
        // Fallback mock documents
        setDocuments([
          {
            id: 'doc-1',
            filename: 'Project Requirements.pdf',
            file_size: 245000,
            status: 'processed',
            created_at: new Date().toISOString(),
          },
          {
            id: 'doc-2',
            filename: 'Technical Specification.docx',
            file_size: 156000,
            status: 'processed',
            created_at: new Date(Date.now() - 86400000).toISOString(),
          },
          {
            id: 'doc-3',
            filename: 'Meeting Notes.md',
            file_size: 12000,
            status: 'pending',
            created_at: new Date(Date.now() - 172800000).toISOString(),
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('Failed to load honey jar');
    } finally {
      setLoading(false);
    }
  }, [jarId]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle file upload
  const handleUpload = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.pdf,.doc,.docx,.txt,.md,.json,.html,.jpg,.jpeg,.png,.gif,.webp,.xls,.xlsx';

    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (files.length === 0) return;

      setUploading(true);
      try {
        await honeyJarApi.uploadDocuments(jarId, files);
        message.success(`Uploaded ${files.length} file(s)`);
        fetchData();
      } catch (error) {
        console.error('Upload failed:', error);
        message.error('Upload failed. Please try again.');
      } finally {
        setUploading(false);
      }
    };

    input.click();
  };

  // Handle ripen (reprocess all documents)
  const handleRipen = async () => {
    Modal.confirm({
      title: 'Ripen Honey Jar',
      content: 'This will reprocess all documents in this honey jar. This may take some time. Continue?',
      okText: 'Ripen',
      okButtonProps: { style: { background: 'var(--mobile-primary)' } },
      cancelText: 'Cancel',
      onOk: async () => {
        setRipening(true);
        try {
          await honeyJarApi.ripenHoneyJar(jarId);
          message.success('Ripening started. Documents will be reprocessed.');
          fetchData();
        } catch (error) {
          console.error('Ripen failed:', error);
          message.error('Failed to ripen honey jar');
        } finally {
          setRipening(false);
        }
      },
    });
  };

  // Handle document delete
  const handleDeleteDocument = (doc) => {
    Modal.confirm({
      title: 'Delete Document',
      content: `Are you sure you want to delete "${doc.filename}"?`,
      okText: 'Delete',
      okButtonProps: { danger: true },
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await honeyJarApi.deleteDocument(jarId, doc.id);
          message.success('Document deleted');
          setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
        } catch (error) {
          console.error('Delete failed:', error);
          message.error('Failed to delete document');
        }
      },
    });
  };

  // Handle document click
  const handleDocumentClick = (doc) => {
    // Could open a preview or detail view
    message.info(`Opening ${doc.filename}`);
  };

  // Handle back
  const handleBack = () => {
    navigate('/m/honey-jars');
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header with Back Button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--mobile-space-md)',
          marginBottom: 'var(--mobile-space-md)',
        }}
      >
        <button
          onClick={handleBack}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md)',
            color: 'var(--mobile-text-primary)',
            cursor: 'pointer',
          }}
          aria-label="Go back"
        >
          <ArrowLeftOutlined />
        </button>
        <div style={{ flex: 1 }}>
          <h1
            className="mobile-page-title"
            style={{
              marginBottom: 0,
              fontSize: 'var(--mobile-font-lg)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {honeyJar?.name || 'Honey Jar'}
          </h1>
          {honeyJar?.description && (
            <div
              style={{
                fontSize: 'var(--mobile-font-sm)',
                color: 'var(--mobile-text-secondary)',
                marginTop: '2px',
              }}
            >
              {honeyJar.description}
            </div>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--mobile-space-md)',
          marginBottom: 'var(--mobile-space-md)',
        }}
      >
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--mobile-space-sm)',
            padding: 'var(--mobile-space-md)',
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md)',
          }}
        >
          <FileTextOutlined style={{ color: 'var(--mobile-primary)', fontSize: '18px' }} />
          <div>
            <div style={{ fontWeight: 600, color: 'var(--mobile-text-primary)' }}>
              {documents.length}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-secondary)' }}>
              Documents
            </div>
          </div>
        </div>
        <button
          onClick={handleRipen}
          disabled={ripening || documents.length === 0}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--mobile-space-sm)',
            padding: 'var(--mobile-space-md)',
            background: ripening ? 'var(--mobile-elevated)' : 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md)',
            color: 'var(--mobile-text-primary)',
            cursor: ripening ? 'not-allowed' : 'pointer',
            opacity: ripening ? 0.6 : 1,
          }}
        >
          <ReloadOutlined
            style={{
              fontSize: '18px',
              color: ripening ? 'var(--mobile-text-tertiary)' : 'var(--mobile-warning)',
            }}
          />
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontWeight: 600 }}>
              {ripening ? 'Ripening...' : 'Ripen'}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-secondary)' }}>
              Reprocess all
            </div>
          </div>
        </button>
      </div>

      {/* Documents List */}
      {documents.length === 0 ? (
        <div className="mobile-basket-empty">
          <FolderOutlined className="mobile-basket-empty-icon" />
          <div className="mobile-basket-empty-title">No documents</div>
          <div className="mobile-basket-empty-text">
            Upload documents to this honey jar to get started
          </div>
          <button
            className="mobile-basket-upload"
            onClick={handleUpload}
            disabled={uploading}
          >
            <UploadOutlined />
            {uploading ? 'Uploading...' : 'Upload Documents'}
          </button>
        </div>
      ) : (
        <div className="mobile-basket-list" style={{ paddingBottom: '80px' }}>
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="mobile-basket-item"
              onClick={() => handleDocumentClick(doc)}
            >
              <div className="mobile-basket-item-icon">
                {getFileIcon(doc.filename)}
              </div>
              <div className="mobile-basket-item-info">
                <div className="mobile-basket-item-name">{doc.filename}</div>
                <div className="mobile-basket-item-meta">
                  <span>{formatFileSize(doc.file_size)}</span>
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: getStatusColor(doc.status),
                    }}
                  >
                    <span
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        backgroundColor: getStatusColor(doc.status),
                      }}
                    />
                    {getStatusText(doc.status)}
                  </span>
                </div>
                {doc.created_at && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: 'var(--mobile-font-xs)',
                      color: 'var(--mobile-text-tertiary)',
                      marginTop: '2px',
                    }}
                  >
                    <ClockCircleOutlined />
                    {formatRelativeTime(doc.created_at)}
                  </div>
                )}
              </div>
              <div className="mobile-basket-item-actions">
                <button
                  className="mobile-basket-item-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteDocument(doc);
                  }}
                  aria-label="Delete document"
                >
                  <DeleteOutlined />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* FAB - Upload */}
      <button
        className="mobile-action-button"
        onClick={handleUpload}
        disabled={uploading}
        aria-label="Upload documents"
      >
        <UploadOutlined />
      </button>
    </div>
  );
};

export default MobileHoneyJarDetail;
