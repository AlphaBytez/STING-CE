import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Input, Button, Spin, Tooltip } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  CopyOutlined,
  CheckOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { REPORT_TEMPLATES } from '../../../services/externalAiApi';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Get template by ID from REPORT_TEMPLATES
 */
const getTemplateById = (id) => {
  const templateArray = Object.entries(REPORT_TEMPLATES).map(([key, value]) => ({
    key,
    ...value,
  }));
  return templateArray.find(t => t.id === id) || null;
};

/**
 * MobileTemplateDetail - Mobile template detail/edit page
 * Template content viewer with syntax highlighting, edit, copy, and use for report
 */
const MobileTemplateDetail = () => {
  const { templateId } = useParams();
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [template, setTemplate] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [editedDescription, setEditedDescription] = useState('');
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);

  // Fetch template
  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    try {
      // Simulate API fetch
      await new Promise(resolve => setTimeout(resolve, 300));

      if (templateId === 'new') {
        // New template
        setTemplate({
          id: 'new',
          title: 'New Template',
          description: 'Enter template description',
          category: 'analytics',
          template: 'Enter your template content here with {{PLACEHOLDERS}}',
        });
        setEditedName('New Template');
        setEditedDescription('Enter template description');
      } else {
        const fetchedTemplate = getTemplateById(templateId);
        if (!fetchedTemplate) {
          message.error('Template not found');
          navigate('/m/templates');
          return;
        }
        setTemplate(fetchedTemplate);
        setEditedName(fetchedTemplate.title);
        setEditedDescription(fetchedTemplate.description);
      }
    } catch (error) {
      console.error('Failed to fetch template:', error);
      message.error('Failed to load template');
      navigate('/m/templates');
    } finally {
      setLoading(false);
    }
  }, [templateId, navigate]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(template?.template || '');
      setCopied(true);
      message.success('Template copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      message.error('Failed to copy template');
    }
  };

  // Handle save edits
  const handleSave = async () => {
    if (!editedName.trim()) {
      message.error('Template name is required');
      return;
    }

    setSaving(true);
    try {
      // Simulate API save
      await new Promise(resolve => setTimeout(resolve, 500));

      setTemplate((prev) => ({
        ...prev,
        title: editedName,
        description: editedDescription,
      }));

      setIsEditing(false);
      message.success('Template saved');
    } catch (error) {
      console.error('Failed to save template:', error);
      message.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  // Handle use template for report
  const handleUseTemplate = () => {
    message.info('Redirecting to report creation...');
    navigate(`/m/reports/new?template=${templateId}`);
  };

  // Cancel editing
  const handleCancelEdit = () => {
    if (template) {
      setEditedName(template.title);
      setEditedDescription(template.description);
    }
    setIsEditing(false);
  };

  // Format template content for display
  const formatTemplateContent = (content) => {
    if (!content) return '';
    return content.trim();
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  // Not found state
  if (!template) {
    return (
      <div className="mobile-page mobile-empty-state">
        <FileTextOutlined style={{ fontSize: 48, color: 'var(--mobile-text-tertiary)', marginBottom: 16 }} />
        <p style={{ color: 'var(--mobile-text-secondary)' }}>Template not found</p>
        <Button type="primary" onClick={() => navigate('/m/templates')}>
          Back to Templates
        </Button>
      </div>
    );
  }

  return (
    <div className="mobile-page">
      {/* Header with back button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--mobile-space-md)',
          marginBottom: 'var(--mobile-space-lg)',
        }}
      >
        <button
          onClick={() => navigate('/m/templates')}
          style={{
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
            padding: 'var(--mobile-space-sm)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-label="Go back"
        >
          <ArrowLeftOutlined style={{ color: 'var(--mobile-text-primary)' }} />
        </button>

        <h1 className="mobile-page-title" style={{ flex: 1, marginBottom: 0 }}>
          {isEditing ? 'Edit Template' : template.title}
        </h1>

        {!isEditing && templateId !== 'new' && (
          <Tooltip title="Edit">
            <button
              onClick={() => setIsEditing(true)}
              style={{
                background: 'var(--mobile-surface)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                padding: 'var(--mobile-space-sm)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              aria-label="Edit template"
            >
              <EditOutlined style={{ color: 'var(--mobile-text-primary)' }} />
            </button>
          </Tooltip>
        )}
      </div>

      {/* Template Info Card */}
      <div className="mobile-card" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        {isEditing ? (
          // Edit mode
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-md)' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  marginBottom: 'var(--mobile-space-xs)',
                  fontSize: 'var(--mobile-font-sm)',
                  color: 'var(--mobile-text-secondary)',
                }}
              >
                Template Name
              </label>
              <Input
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                placeholder="Enter template name"
                size="large"
              />
            </div>
            <div>
              <label
                style={{
                  display: 'block',
                  marginBottom: 'var(--mobile-space-xs)',
                  fontSize: 'var(--mobile-font-sm)',
                  color: 'var(--mobile-text-secondary)',
                }}
              >
                Description
              </label>
              <Input.TextArea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                placeholder="Enter template description"
                rows={3}
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--mobile-space-sm)' }}>
              <Button
                onClick={handleCancelEdit}
                style={{ flex: 1 }}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                type="primary"
                onClick={handleSave}
                style={{ flex: 1 }}
                loading={saving}
                icon={<SaveOutlined />}
              >
                Save
              </Button>
            </div>
          </div>
        ) : (
          // View mode
          <div>
            <p
              style={{
                color: 'var(--mobile-text-secondary)',
                fontSize: 'var(--mobile-font-sm)',
                marginBottom: 'var(--mobile-space-md)',
              }}
            >
              {template.description}
            </p>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--mobile-space-sm)',
              }}
            >
              <span
                style={{
                  padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                  background: 'var(--mobile-surface)',
                  borderRadius: 'var(--mobile-radius-sm, 4px)',
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              >
                Category: {template.category}
              </span>
              <span
                style={{
                  padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                  background: 'var(--mobile-surface)',
                  borderRadius: 'var(--mobile-radius-sm, 4px)',
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              >
                Est. Time: {template.estimatedTime}
              </span>
              <span
                style={{
                  padding: 'var(--mobile-space-xs) var(--mobile-space-sm)',
                  background: 'var(--mobile-surface)',
                  borderRadius: 'var(--mobile-radius-sm, 4px)',
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              >
                Privacy: {template.privacyLevel}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Template Content */}
      <div style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--mobile-space-sm)',
          }}
        >
          <h2
            style={{
              fontSize: 'var(--mobile-font-md)',
              fontWeight: 600,
              color: 'var(--mobile-text-primary)',
              margin: 0,
            }}
          >
            Template Content
          </h2>

          {!isEditing && templateId !== 'new' && (
            <Tooltip title={copied ? 'Copied!' : 'Copy to clipboard'}>
              <button
                onClick={handleCopy}
                style={{
                  background: copied ? 'var(--mobile-success)' : 'var(--mobile-surface)',
                  border: '1px solid var(--mobile-border)',
                  borderRadius: 'var(--mobile-radius-md, 8px)',
                  padding: 'var(--mobile-space-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s',
                }}
                aria-label="Copy template"
              >
                {copied ? (
                  <CheckOutlined style={{ color: '#fff' }} />
                ) : (
                  <CopyOutlined style={{ color: 'var(--mobile-text-primary)' }} />
                )}
              </button>
            </Tooltip>
          )}
        </div>

        <div
          className="mobile-card"
          style={{
            background: 'var(--mobile-code-bg)',
            padding: 'var(--mobile-space-md)',
            fontFamily: 'var(--mobile-font-mono, monospace)',
            fontSize: 'var(--mobile-font-sm)',
            lineHeight: 1.6,
            color: 'var(--mobile-text-primary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: 300,
            overflowY: 'auto',
          }}
        >
          {isEditing ? (
            <Input.TextArea
              value={template.template}
              onChange={(e) => setTemplate({ ...template, template: e.target.value })}
              placeholder="Enter template content..."
              rows={10}
              style={{
                fontFamily: 'var(--mobile-font-mono, monospace)',
                background: 'var(--mobile-surface)',
                border: '1px solid var(--mobile-border)',
              }}
            />
          ) : (
            formatTemplateContent(template.template)
          )}
        </div>
      </div>

      {/* Action Buttons */}
      {templateId !== 'new' && (
        <div style={{ display: 'flex', gap: 'var(--mobile-space-sm)' }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleUseTemplate}
            style={{ flex: 1, height: 48 }}
          >
            Use Template
          </Button>
        </div>
      )}

      {/* New Template - Save Button */}
      {templateId === 'new' && (
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
          style={{ width: '100%', height: 48 }}
        >
          Save Template
        </Button>
      )}
    </div>
  );
};

export default MobileTemplateDetail;
