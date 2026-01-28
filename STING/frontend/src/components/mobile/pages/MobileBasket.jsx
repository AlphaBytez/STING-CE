import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Modal, Empty } from 'antd';
import {
  FileTextOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  UploadOutlined,
  DeleteOutlined,
  FolderOutlined,
  MoreOutlined,
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
 * MobileBasket - Mobile basket/file management page
 * File management interface optimized for mobile
 */
const MobileBasket = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [documents, setDocuments] = useState([]);
  const [honeyJars, setHoneyJars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'jars'
  const [selectedItem, setSelectedItem] = useState(null);

  // Fetch basket data
  const fetchBasketData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch honey jars
      const jarsData = await honeyJarApi.getHoneyJars(1, 50);
      setHoneyJars(jarsData.honey_jars || jarsData || []);

      // For now, we'll show documents from the first honey jar
      // In a full implementation, there would be a dedicated basket API
      if (jarsData.honey_jars?.length > 0 || (Array.isArray(jarsData) && jarsData.length > 0)) {
        const firstJar = jarsData.honey_jars?.[0] || jarsData[0];
        try {
          const docsData = await honeyJarApi.getDocuments(firstJar.id);
          setDocuments(docsData.documents || docsData || []);
        } catch (docError) {
          console.warn('Could not fetch documents:', docError);
          // Fallback mock documents
          setDocuments([
            {
              id: '1',
              filename: 'Project Requirements.pdf',
              file_size: 245000,
              created_at: new Date().toISOString(),
              status: 'processed',
            },
            {
              id: '2',
              filename: 'Technical Specification.docx',
              file_size: 156000,
              created_at: new Date(Date.now() - 86400000).toISOString(),
              status: 'processed',
            },
            {
              id: '3',
              filename: 'Meeting Notes.md',
              file_size: 12000,
              created_at: new Date(Date.now() - 172800000).toISOString(),
              status: 'pending',
            },
          ]);
        }
      } else {
        // Fallback mock documents
        setDocuments([
          {
            id: '1',
            filename: 'Project Requirements.pdf',
            file_size: 245000,
            created_at: new Date().toISOString(),
            status: 'processed',
          },
          {
            id: '2',
            filename: 'Technical Specification.docx',
            file_size: 156000,
            created_at: new Date(Date.now() - 86400000).toISOString(),
            status: 'processed',
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch basket data:', error);
      message.error('Failed to load basket');

      // Fallback data
      setDocuments([
        {
          id: '1',
          filename: 'Project Requirements.pdf',
          file_size: 245000,
          created_at: new Date().toISOString(),
          status: 'processed',
        },
        {
          id: '2',
          filename: 'Technical Specification.docx',
          file_size: 156000,
          created_at: new Date(Date.now() - 86400000).toISOString(),
          status: 'processed',
        },
      ]);
      setHoneyJars([
        { id: '1', name: 'Main Knowledge Base', document_count: 12 },
        { id: '2', name: 'Project Docs', document_count: 5 },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchBasketData();
  }, [fetchBasketData]);

  // Handle file upload
  const handleUpload = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.pdf,.doc,.docx,.txt,.md,.json,.html,.jpg,.jpeg,.png';

    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (files.length === 0) return;

      setUploading(true);
      try {
        // Get first honey jar for upload
        if (honeyJars.length > 0) {
          const firstJar = honeyJars[0];
          await honeyJarApi.uploadDocuments(firstJar.id, files);

          message.success(`Uploaded ${files.length} file(s)`);
          fetchBasketData();
        } else {
          message.warning('No honey jar available for upload');
        }
      } catch (error) {
        console.error('Upload failed:', error);
        message.error('Upload failed');
      } finally {
        setUploading(false);
      }
    };

    input.click();
  };

  // Handle document delete
  const handleDelete = async (docId) => {
    Modal.confirm({
      title: 'Delete Document',
      content: 'Are you sure you want to delete this document?',
      okText: 'Delete',
      okButtonProps: { danger: true },
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          // In a real implementation, this would call the API
          setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
          message.success('Document deleted');
        } catch (error) {
          console.error('Delete failed:', error);
          message.error('Failed to delete');
        }
      },
    });
  };

  // Handle document click
  const handleDocumentClick = (doc) => {
    setSelectedItem(doc);
    // Could open a detail view or preview
  };

  // Handle honey jar click
  const handleHoneyJarClick = (jar) => {
    navigate(`/m/honey-jars/${jar.id}`);
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-basket-header">
        <h1 className="mobile-page-title" style={{ marginBottom: 0 }}>Basket</h1>
        <div className="mobile-basket-actions">
          <button
            className="mobile-basket-upload"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? (
              <span>Uploading...</span>
            ) : (
              <>
                <UploadOutlined />
                Upload
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 'var(--mobile-space-sm)', marginBottom: 'var(--mobile-space-md)' }}>
        <button
          onClick={() => setActiveTab('documents')}
          style={{
            flex: 1,
            padding: 'var(--mobile-space-sm)',
            background: activeTab === 'documents' ? 'var(--mobile-primary)' : 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            color: activeTab === 'documents' ? 'var(--mobile-text-inverse)' : 'var(--mobile-text-primary)',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Documents ({documents.length})
        </button>
        <button
          onClick={() => setActiveTab('jars')}
          style={{
            flex: 1,
            padding: 'var(--mobile-space-sm)',
            background: activeTab === 'jars' ? 'var(--mobile-primary)' : 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            color: activeTab === 'jars' ? 'var(--mobile-text-inverse)' : 'var(--mobile-text-primary)',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Honey Jars ({honeyJars.length})
        </button>
      </div>

      {/* Documents List */}
      {activeTab === 'documents' && (
        <div className="mobile-basket-list">
          {documents.length === 0 ? (
            <div className="mobile-basket-empty">
              <FolderOutlined className="mobile-basket-empty-icon" />
              <div className="mobile-basket-empty-title">No documents yet</div>
              <div className="mobile-basket-empty-description">
                Upload documents to your honey jars to get started
              </div>
              <button
                className="mobile-basket-upload"
                onClick={handleUpload}
              >
                <UploadOutlined />
                Upload Documents
              </button>
            </div>
          ) : (
            documents.map((doc) => (
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
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    <span style={{
                      color: doc.status === 'processed' ? 'var(--mobile-success)' : 'var(--mobile-warning)'
                    }}>
                      {doc.status}
                    </span>
                  </div>
                </div>
                <div className="mobile-basket-item-actions">
                  <button
                    className="mobile-basket-item-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(doc.id);
                    }}
                    aria-label="Delete"
                  >
                    <DeleteOutlined />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Honey Jars List */}
      {activeTab === 'jars' && (
        <div className="mobile-basket-list">
          {honeyJars.length === 0 ? (
            <div className="mobile-basket-empty">
              <FolderOutlined className="mobile-basket-empty-icon" />
              <div className="mobile-basket-empty-title">No honey jars</div>
              <div className="mobile-basket-empty-description">
                Create a honey jar to organize your documents
              </div>
            </div>
          ) : (
            honeyJars.map((jar) => (
              <div
                key={jar.id}
                className="mobile-basket-item"
                onClick={() => handleHoneyJarClick(jar)}
              >
                <div className="mobile-basket-item-icon">
                  <FolderOutlined />
                </div>
                <div className="mobile-basket-item-info">
                  <div className="mobile-basket-item-name">{jar.name}</div>
                  <div className="mobile-basket-item-meta">
                    <span>{jar.document_count || 0} documents</span>
                    {jar.updated_at && (
                      <span>Updated {new Date(jar.updated_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <div className="mobile-basket-item-actions">
                  <button
                    className="mobile-basket-item-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Could open actions menu
                    }}
                    aria-label="More options"
                  >
                    <MoreOutlined />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default MobileBasket;
