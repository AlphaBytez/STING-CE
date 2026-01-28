import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Modal, Empty } from 'antd';
import {
  FileTextOutlined,
  CheckOutlined,
  CloseOutlined,
  ExclamationCircleOutlined,
  FolderOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SelectOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../../auth/UnifiedAuthProvider';
import apiClient from '../../../../utils/apiClient';
import { resilientGet, resilientPost, fallbackGenerators } from '../../../../utils/resilientApiClient';
import MobileLoadingSpinner from '../../MobileLoadingSpinner';
import '../../../../styles/mobile.css';

/**
 * MobileAdminPending - Mobile pending approvals page
 * Pending document approvals optimized for mobile
 */
const MobileAdminPending = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pendingDocs, setPendingDocs] = useState([]);
  const [honeyJars, setHoneyJars] = useState([]);
  const [selectedHoneyJar, setSelectedHoneyJar] = useState('');
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectingDoc, setRejectingDoc] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  // Fetch honey jars for selection
  const fetchHoneyJars = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/knowledge/honey-jars').catch(() => ({ data: { items: [] } }));
      const jars = response.data?.items || [];
      setHoneyJars(jars);
      if (jars.length > 0 && !selectedHoneyJar) {
        setSelectedHoneyJar(jars[0].id);
      }
      return jars;
    } catch (error) {
      console.error('Failed to fetch honey jars:', error);
      return [];
    }
  }, [selectedHoneyJar]);

  // Fetch pending documents for selected honey jar
  const fetchPendingDocuments = useCallback(async (honeyJarId, showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    setLoading(true);
    try {
      const response = await resilientGet(
        `/api/knowledge/honey-jars/${honeyJarId}/pending-documents`,
        fallbackGenerators.adminPendingDocs(),
        { timeout: 5000 }
      );
      setPendingDocs(response.data?.documents || response.documents || []);
      setSelectedDocs([]);
    } catch (error) {
      console.error('Failed to fetch pending documents:', error);
      message.error('Failed to load pending documents');
      setPendingDocs([]);
    } finally {
      setLoading(false);
      if (showRefresh) setRefreshing(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      const jars = await fetchHoneyJars();
      if (jars.length > 0) {
        await fetchPendingDocuments(jars[0].id);
      } else {
        setLoading(false);
      }
    };
    init();
  }, [fetchHoneyJars, fetchPendingDocuments]);

  // Handle honey jar selection change
  const handleHoneyJarChange = async (honeyJarId) => {
    setSelectedHoneyJar(honeyJarId);
    await fetchPendingDocuments(honeyJarId);
  };

  // Handle refresh
  const handleRefresh = async () => {
    if (selectedHoneyJar) {
      await fetchPendingDocuments(selectedHoneyJar, true);
    }
  };

  // Toggle document selection
  const toggleDocSelection = (docId) => {
    setSelectedDocs(prev =>
      prev.includes(docId)
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  // Toggle all documents
  const toggleAllSelection = () => {
    if (selectedDocs.length === pendingDocs.length) {
      setSelectedDocs([]);
    } else {
      setSelectedDocs(pendingDocs.map(doc => doc.id));
    }
  };

  // Handle approve single document
  const handleApproveDocument = async (doc) => {
    try {
      await resilientPost(
        `/api/knowledge/honey-jars/${selectedHoneyJar}/documents/${doc.id}/approve`,
        null,
        { timeout: 8000 }
      );
      message.success(`Document "${doc.name || doc.filename}" approved`);
      await fetchPendingDocuments(selectedHoneyJar);
    } catch (error) {
      console.error('Failed to approve document:', error);
      message.error('Failed to approve document');
    }
  };

  // Handle bulk approve
  const handleBulkApprove = async () => {
    if (selectedDocs.length === 0) return;

    Modal.confirm({
      title: 'Approve Documents',
      icon: <CheckCircleOutlined style={{ color: 'var(--mobile-success)' }} />,
      content: `Are you sure you want to approve ${selectedDocs.length} document(s)?`,
      okText: 'Approve',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          for (const docId of selectedDocs) {
            await resilientPost(
              `/api/knowledge/honey-jars/${selectedHoneyJar}/documents/${docId}/approve`,
              null,
              { timeout: 8000 }
            );
          }
          message.success(`${selectedDocs.length} documents approved`);
          await fetchPendingDocuments(selectedHoneyJar);
        } catch (error) {
          console.error('Failed to bulk approve:', error);
          message.error('Failed to approve some documents');
        }
      },
    });
  };

  // Show reject modal
  const showRejectModal = (doc) => {
    setRejectingDoc(doc);
    setRejectReason('');
    setRejectModalVisible(true);
  };

  // Handle reject document
  const handleRejectDocument = async () => {
    if (!rejectingDoc) return;

    try {
      const formData = new FormData();
      formData.append('reason', rejectReason);

      await apiClient.post(
        `/api/knowledge/honey-jars/${selectedHoneyJar}/documents/${rejectingDoc.id}/reject`,
        formData,
        { timeout: 8000 }
      );

      message.success(`Document "${rejectingDoc.name || rejectingDoc.filename}" rejected`);
      setRejectModalVisible(false);
      setRejectingDoc(null);
      setRejectReason('');
      await fetchPendingDocuments(selectedHoneyJar);
    } catch (error) {
      console.error('Failed to reject document:', error);
      message.error('Failed to reject document');
    }
  };

  // Handle bulk reject
  const handleBulkReject = async () => {
    if (selectedDocs.length === 0) return;

    Modal.confirm({
      title: 'Reject Documents',
      icon: <CloseCircleOutlined style={{ color: 'var(--mobile-error)' }} />,
      content: `Are you sure you want to reject ${selectedDocs.length} document(s)? This will delete them.`,
      okText: 'Reject',
      cancelText: 'Cancel',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          for (const docId of selectedDocs) {
            await apiClient.post(
              `/api/knowledge/honey-jars/${selectedHoneyJar}/documents/${docId}/reject`,
              new FormData(),
              { timeout: 8000 }
            );
          }
          message.success(`${selectedDocs.length} documents rejected`);
          await fetchPendingDocuments(selectedHoneyJar);
        } catch (error) {
          console.error('Failed to bulk reject:', error);
          message.error('Failed to reject some documents');
        }
      },
    });
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Format date
  const formatDate = (date) => {
    if (!date) return 'Unknown';
    return new Date(date).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-admin-header" style={{ marginBottom: 'var(--mobile-space-md)' }}>
        <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
          Pending Approvals
        </h1>
        <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
          Review and approve uploaded documents
        </p>
      </div>

      {/* Honey Jar Selector */}
      {honeyJars.length > 1 && (
        <div className="mobile-section">
          <label
            style={{
              display: 'block',
              fontSize: 'var(--mobile-font-sm)',
              fontWeight: 500,
              color: 'var(--mobile-text-secondary)',
              marginBottom: 'var(--mobile-space-xs)',
            }}
          >
            Select Honey Jar
          </label>
          <select
            className="mobile-card"
            value={selectedHoneyJar}
            onChange={(e) => handleHoneyJarChange(e.target.value)}
            style={{
              width: '100%',
              padding: 'var(--mobile-space-md)',
              background: 'var(--mobile-surface)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: 'var(--mobile-text-primary)',
              fontSize: 'var(--mobile-font-md)',
              cursor: 'pointer',
            }}
          >
            {honeyJars.map(jar => (
              <option key={jar.id} value={jar.id}>
                {jar.name} ({jar.type})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Bulk Actions */}
      {selectedDocs.length > 0 && (
        <div
          className="mobile-card"
          style={{
            marginBottom: 'var(--mobile-space-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--mobile-elevated)',
            borderColor: 'var(--mobile-primary)',
          }}
        >
          <span style={{ color: 'var(--mobile-text-primary)', fontWeight: 500 }}>
            {selectedDocs.length} selected
          </span>
          <div style={{ display: 'flex', gap: 'var(--mobile-space-sm)' }}>
            <button
              onClick={handleBulkApprove}
              style={{
                padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                background: 'var(--mobile-success)',
                border: 'none',
                borderRadius: 'var(--mobile-radius-sm, 4px)',
                color: '#fff',
                fontSize: 'var(--mobile-font-sm)',
                cursor: 'pointer',
              }}
            >
              Approve All
            </button>
            <button
              onClick={handleBulkReject}
              style={{
                padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                background: 'var(--mobile-error)',
                border: 'none',
                borderRadius: 'var(--mobile-radius-sm, 4px)',
                color: '#fff',
                fontSize: 'var(--mobile-font-sm)',
                cursor: 'pointer',
              }}
            >
              Reject All
            </button>
          </div>
        </div>
      )}

      {/* Pending Documents List */}
      <div className="mobile-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--mobile-space-sm)' }}>
          <h2 className="mobile-section-title" style={{ marginBottom: 0 }}>
            Documents ({pendingDocs.length})
          </h2>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--mobile-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--mobile-space-xs)',
            }}
          >
            <ReloadOutlined spin={refreshing} />
            Refresh
          </button>
        </div>

        {pendingDocs.length === 0 ? (
          <div className="mobile-empty-state">
            <CheckCircleOutlined className="mobile-empty-state-icon" style={{ color: 'var(--mobile-success)' }} />
            <div className="mobile-empty-state-title">All Clear!</div>
            <div className="mobile-empty-state-description">
              No documents are waiting for approval in this honey jar.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-sm)' }}>
            {/* Select All */}
            <div
              className="mobile-card"
              onClick={toggleAllSelection}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--mobile-space-sm)',
                padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
                background: selectedDocs.length === pendingDocs.length ? 'var(--mobile-elevated)' : 'transparent',
                borderColor: selectedDocs.length === pendingDocs.length ? 'var(--mobile-primary)' : undefined,
              }}
            >
              <SelectOutlined style={{ color: selectedDocs.length === pendingDocs.length ? 'var(--mobile-primary)' : 'var(--mobile-text-tertiary)' }} />
              <span style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
                {selectedDocs.length === pendingDocs.length ? 'Deselect All' : 'Select All'}
              </span>
            </div>

            {/* Document Items */}
            {pendingDocs.map((doc) => (
              <div
                key={doc.id}
                className="mobile-card"
                style={{
                  display: 'flex',
                  gap: 'var(--mobile-space-md)',
                  background: selectedDocs.includes(doc.id) ? 'var(--mobile-elevated)' : undefined,
                  borderColor: selectedDocs.includes(doc.id) ? 'var(--mobile-primary)' : undefined,
                }}
                onClick={() => toggleDocSelection(doc.id)}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: 'var(--mobile-radius-sm, 4px)',
                    border: `2px solid ${selectedDocs.includes(doc.id) ? 'var(--mobile-primary)' : 'var(--mobile-border)'}`,
                    background: selectedDocs.includes(doc.id) ? 'var(--mobile-primary)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  {selectedDocs.includes(doc.id) && <CheckOutlined style={{ color: '#fff', fontSize: 12 }} />}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 'var(--mobile-space-xs)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)', flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          width: 36,
                          height: 36,
                          borderRadius: 'var(--mobile-radius-sm, 6px)',
                          background: 'rgba(234, 179, 8, 0.15)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <FileTextOutlined style={{ color: 'var(--mobile-warning)', fontSize: 18 }} />
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {doc.name || doc.filename || 'Untitled Document'}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)', fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <UserOutlined /> {doc.uploadedBy || doc.uploaded_by || 'Unknown'}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <ClockCircleOutlined /> {formatDate(doc.uploadedAt || doc.uploaded_at || doc.createdAt)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--mobile-space-sm)' }}>
                    <span style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>
                      {formatFileSize(doc.size || doc.sizeBytes || doc.size_bytes)}
                    </span>

                    <div style={{ display: 'flex', gap: 'var(--mobile-space-xs)' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApproveDocument(doc);
                        }}
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 'var(--mobile-radius-sm, 6px)',
                          background: 'rgba(93, 155, 99, 0.15)',
                          border: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                        }}
                      >
                        <CheckOutlined style={{ color: 'var(--mobile-success)' }} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          showRejectModal(doc);
                        }}
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 'var(--mobile-radius-sm, 6px)',
                          background: 'rgba(239, 68, 68, 0.15)',
                          border: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                        }}
                      >
                        <CloseOutlined style={{ color: 'var(--mobile-error)' }} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reject Modal */}
      <Modal
        title="Reject Document"
        open={rejectModalVisible}
        onCancel={() => {
          setRejectModalVisible(false);
          setRejectingDoc(null);
          setRejectReason('');
        }}
        onOk={handleRejectDocument}
        okText="Reject"
        okButtonProps={{ danger: true }}
        cancelText="Cancel"
      >
        <div style={{ marginBottom: 'var(--mobile-space-md)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--mobile-space-sm)',
              padding: 'var(--mobile-space-md)',
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              marginBottom: 'var(--mobile-space-md)',
            }}
          >
            <ExclamationCircleOutlined style={{ color: 'var(--mobile-error)', fontSize: 20 }} />
            <div>
              <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                Confirm Rejection
              </div>
              <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                {rejectingDoc?.name || rejectingDoc?.filename}
              </div>
            </div>
          </div>
        </div>

        <label
          style={{
            display: 'block',
            fontSize: 'var(--mobile-font-sm)',
            fontWeight: 500,
            color: 'var(--mobile-text-secondary)',
            marginBottom: 'var(--mobile-space-xs)',
          }}
        >
          Rejection Reason (optional)
        </label>
        <textarea
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          placeholder="Provide feedback to help the uploader understand why this document was rejected..."
          style={{
            width: '100%',
            padding: 'var(--mobile-space-sm)',
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            color: 'var(--mobile-text-primary)',
            fontSize: 'var(--mobile-font-md)',
            minHeight: 80,
            resize: 'vertical',
          }}
        />
      </Modal>
    </div>
  );
};

export default MobileAdminPending;
