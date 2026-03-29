import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Modal, Input } from 'antd';
import {
  FolderOutlined,
  PlusOutlined,
  MoreOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { honeyJarApi } from '../../../services/knowledgeApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Format relative time
 */
const formatRelativeTime = (dateString) => {
  if (!dateString) return 'Never';
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
 * MobileHoneyJars - Mobile honey jars list page
 * Honey jar listings optimized for mobile with grid view and FAB for creating new jars
 */
const MobileHoneyJars = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [honeyJars, setHoneyJars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newJarName, setNewJarName] = useState('');
  const [newJarDescription, setNewJarDescription] = useState('');

  // Fetch honey jars
  const fetchHoneyJars = useCallback(async () => {
    setLoading(true);
    try {
      const response = await honeyJarApi.getHoneyJars(1, 50);
      // Handle different response formats
      const jars = response.honey_jars || response.items || response || [];
      setHoneyJars(jars);
    } catch (error) {
      console.error('Failed to fetch honey jars:', error);
      message.error('Failed to load honey jars');

      // Fallback mock data
      setHoneyJars([
        {
          id: 'demo-1',
          name: 'Demo Knowledge Base',
          description: 'Sample honey jar for demonstration',
          document_count: 5,
          updated_at: new Date().toISOString(),
        },
        {
          id: 'demo-2',
          name: 'Project Documents',
          description: 'Technical specifications and docs',
          document_count: 12,
          updated_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'demo-3',
          name: 'Meeting Notes',
          description: 'Team meeting summaries',
          document_count: 8,
          updated_at: new Date(Date.now() - 172800000).toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchHoneyJars();
  }, [fetchHoneyJars]);

  // Handle create honey jar
  const handleCreateJar = async () => {
    if (!newJarName.trim()) {
      message.warning('Please enter a name for the honey jar');
      return;
    }

    setCreating(true);
    try {
      const newJar = await honeyJarApi.createHoneyJar({
        name: newJarName.trim(),
        description: newJarDescription.trim(),
      });

      message.success('Honey jar created successfully');
      setShowCreateModal(false);
      setNewJarName('');
      setNewJarDescription('');
      fetchHoneyJars();
    } catch (error) {
      console.error('Failed to create honey jar:', error);
      message.error('Failed to create honey jar');
    } finally {
      setCreating(false);
    }
  };

  // Handle delete honey jar
  const handleDeleteJar = (jar, e) => {
    e?.stopPropagation();
    Modal.confirm({
      title: 'Delete Honey Jar',
      content: `Are you sure you want to delete "${jar.name}"? This will permanently remove all documents in this jar.`,
      okText: 'Delete',
      okButtonProps: { danger: true },
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await honeyJarApi.deleteHoneyJar(jar.id);
          message.success('Honey jar deleted');
          fetchHoneyJars();
        } catch (error) {
          console.error('Failed to delete honey jar:', error);
          message.error('Failed to delete honey jar');
        }
      },
    });
  };

  // Handle jar click
  const handleJarClick = (jar) => {
    navigate(`/m/honey-jars/${jar.id}`);
  };

  // Open create modal
  const handleOpenCreateModal = () => {
    setShowCreateModal(true);
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-basket-header">
        <h1 className="mobile-page-title" style={{ marginBottom: 0 }}>Honey Jars</h1>
      </div>

      {/* Honey Jars Grid */}
      {honeyJars.length === 0 ? (
        <div className="mobile-basket-empty">
          <FolderOutlined className="mobile-basket-empty-icon" />
          <div className="mobile-basket-empty-title">No honey jars</div>
          <div className="mobile-basket-empty-text">
            Create a honey jar to organize and manage your documents
          </div>
          <button
            className="mobile-basket-upload"
            onClick={handleOpenCreateModal}
          >
            <PlusOutlined />
            Create Honey Jar
          </button>
        </div>
      ) : (
        <div className="mobile-card-grid-2" style={{ paddingBottom: '80px' }}>
          {honeyJars.map((jar) => (
            <div
              key={jar.id}
              className="mobile-card"
              onClick={() => handleJarClick(jar)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                padding: 'var(--mobile-space-md, 16px)',
                minHeight: '120px',
              }}
            >
              {/* Icon and Actions Row */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 'var(--mobile-space-sm)',
                }}
              >
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--mobile-radius-md)',
                    background: 'var(--mobile-elevated)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--mobile-primary)',
                    fontSize: '20px',
                  }}
                >
                  <FolderOutlined />
                </div>
                <div style={{ position: 'relative' }}>
                  <button
                    className="mobile-basket-item-btn"
                    onClick={(e) => e.stopPropagation()}
                    aria-label="More options"
                    style={{ width: '28px', height: '28px' }}
                  >
                    <MoreOutlined />
                  </button>
                </div>
              </div>

              {/* Jar Name */}
              <div
                style={{
                  fontWeight: 600,
                  color: 'var(--mobile-text-primary)',
                  fontSize: 'var(--mobile-font-md)',
                  marginBottom: 'var(--mobile-space-xs)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {jar.name}
              </div>

              {/* Document Count */}
              <div
                style={{
                  fontSize: 'var(--mobile-font-sm)',
                  color: 'var(--mobile-text-secondary)',
                  marginBottom: 'var(--mobile-space-sm)',
                }}
              >
                {jar.document_count || 0} documents
              </div>

              {/* Last Updated */}
              <div
                style={{
                  marginTop: 'auto',
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              >
                Updated {formatRelativeTime(jar.updated_at)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* FAB - Create New Honey Jar */}
      <button
        className="mobile-action-button"
        onClick={handleOpenCreateModal}
        aria-label="Create new honey jar"
      >
        <PlusOutlined />
      </button>

      {/* Create Honey Jar Modal */}
      <Modal
        title="Create New Honey Jar"
        open={showCreateModal}
        onCancel={() => {
          setShowCreateModal(false);
          setNewJarName('');
          setNewJarDescription('');
        }}
        footer={[
          <button
            key="cancel"
            onClick={() => {
              setShowCreateModal(false);
              setNewJarName('');
              setNewJarDescription('');
            }}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: 'var(--mobile-surface)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md)',
              color: 'var(--mobile-text-primary)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>,
          <button
            key="create"
            onClick={handleCreateJar}
            disabled={creating || !newJarName.trim()}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-lg)',
              background: 'var(--mobile-primary)',
              border: 'none',
              borderRadius: 'var(--mobile-radius-md)',
              color: 'var(--mobile-text-inverse)',
              cursor: creating ? 'not-allowed' : 'pointer',
              opacity: creating ? 0.6 : 1,
            }}
          >
            {creating ? 'Creating...' : 'Create'}
          </button>,
        ]}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-md)' }}>
          <div>
            <label
              style={{
                display: 'block',
                marginBottom: 'var(--mobile-space-xs)',
                color: 'var(--mobile-text-secondary)',
                fontSize: 'var(--mobile-font-sm)',
              }}
            >
              Name *
            </label>
            <Input
              placeholder="Enter honey jar name"
              value={newJarName}
              onChange={(e) => setNewJarName(e.target.value)}
              style={{
                background: 'var(--mobile-elevated)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md)',
                color: 'var(--mobile-text-primary)',
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: 'block',
                marginBottom: 'var(--mobile-space-xs)',
                color: 'var(--mobile-text-secondary)',
                fontSize: 'var(--mobile-font-sm)',
              }}
            >
              Description
            </label>
            <Input.TextArea
              placeholder="Enter description (optional)"
              rows={3}
              value={newJarDescription}
              onChange={(e) => setNewJarDescription(e.target.value)}
              style={{
                background: 'var(--mobile-elevated)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md)',
                color: 'var(--mobile-text-primary)',
                resize: 'none',
              }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MobileHoneyJars;
