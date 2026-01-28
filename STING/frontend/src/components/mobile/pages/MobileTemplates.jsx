import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Input, Tag } from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SecurityScanOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { REPORT_TEMPLATES } from '../../../services/externalAiApi';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Template categories with icons and colors
 */
const TEMPLATE_CATEGORIES = [
  { key: 'all', label: 'All', color: 'var(--mobile-primary)' },
  { key: 'analytics', label: 'Analytics', color: '#1890ff', icon: <BarChartOutlined /> },
  { key: 'security', label: 'Security', color: '#fa541c', icon: <SecurityScanOutlined /> },
  { key: 'business', label: 'Business', color: '#52c41a', icon: <ShopOutlined /> },
];

/**
 * Convert template object to array format
 */
const getTemplateArray = () => {
  return Object.entries(REPORT_TEMPLATES).map(([key, value]) => ({
    key,
    ...value,
  }));
};

/**
 * MobileTemplates - Mobile templates list page
 * Grid of template cards with preview, categories, search/filter, and FAB to create
 */
const MobileTemplates = () => {
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      // In production, this would fetch from API
      // For now, use REPORT_TEMPLATES as the data source
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate loading
      const templateArray = getTemplateArray();
      setTemplates(templateArray);
      setFilteredTemplates(templateArray);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      message.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Filter templates by category and search query
  useEffect(() => {
    let result = templates;

    // Filter by category
    if (selectedCategory !== 'all') {
      result = result.filter(t => t.category === selectedCategory);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        t =>
          t.title.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query)
      );
    }

    setFilteredTemplates(result);
  }, [templates, selectedCategory, searchQuery]);

  // Handle template click
  const handleTemplateClick = (templateId) => {
    navigate(`/m/templates/${templateId}`);
  };

  // Handle create new template
  const handleCreateTemplate = () => {
    navigate('/m/templates/new');
  };

  // Get category color/style
  const getCategoryStyle = (category) => {
    const cat = TEMPLATE_CATEGORIES.find(c => c.key === category);
    return cat?.color || 'var(--mobile-primary)';
  };

  // Get category icon
  const getCategoryIcon = (category) => {
    const cat = TEMPLATE_CATEGORIES.find(c => c.key === category);
    return cat?.icon || <FileTextOutlined />;
  };

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
          Templates
        </h1>
        <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
          Create reports from ready-made templates
        </p>
      </div>

      {/* Search */}
      <div style={{ marginBottom: 'var(--mobile-space-md)' }}>
        <Input
          placeholder="Search templates..."
          prefix={<SearchOutlined style={{ color: 'var(--mobile-text-tertiary)' }} />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="mobile-search-input"
          style={{
            background: 'var(--mobile-surface)',
            border: '1px solid var(--mobile-border)',
            borderRadius: 'var(--mobile-radius-md, 8px)',
          }}
        />
      </div>

      {/* Category Filter */}
      <div style={{ marginBottom: 'var(--mobile-space-lg)', overflowX: 'auto' }}>
        <div style={{ display: 'flex', gap: 'var(--mobile-space-sm)' }}>
          {TEMPLATE_CATEGORIES.map((category) => (
            <Tag
              key={category.key}
              onClick={() => setSelectedCategory(category.key)}
              style={{
                margin: 0,
                padding: 'var(--mobile-space-xs) var(--mobile-space-md)',
                borderRadius: 'var(--mobile-radius-lg, 16px)',
                border: 'none',
                cursor: 'pointer',
                background: selectedCategory === category.key ? category.color : 'var(--mobile-surface)',
                color: selectedCategory === category.key ? '#fff' : 'var(--mobile-text-secondary)',
                whiteSpace: 'nowrap',
                fontSize: 'var(--mobile-font-sm)',
              }}
            >
              {category.icon}
              <span style={{ marginLeft: 4 }}>{category.label}</span>
            </Tag>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      {filteredTemplates.length === 0 ? (
        <div className="mobile-empty-state">
          <FileTextOutlined style={{ fontSize: 48, color: 'var(--mobile-text-tertiary)', marginBottom: 16 }} />
          <p style={{ color: 'var(--mobile-text-secondary)' }}>No templates found</p>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                marginTop: 'var(--mobile-space-md)',
                padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
                background: 'var(--mobile-primary)',
                border: 'none',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              Clear Search
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--mobile-space-md)' }}>
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              className="mobile-card mobile-template-card"
              onClick={() => handleTemplateClick(template.id)}
              style={{ cursor: 'pointer' }}
            >
              {/* Category Icon */}
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--mobile-radius-md, 8px)',
                  background: `${getCategoryStyle(template.category)}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 'var(--mobile-space-sm)',
                }}
              >
                <span style={{ fontSize: 20, color: getCategoryStyle(template.category) }}>
                  {getCategoryIcon(template.category)}
                </span>
              </div>

              {/* Template Title */}
              <h3
                style={{
                  fontSize: 'var(--mobile-font-sm)',
                  fontWeight: 600,
                  color: 'var(--mobile-text-primary)',
                  marginBottom: 'var(--mobile-space-xs)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {template.title}
              </h3>

              {/* Template Description */}
              <p
                style={{
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-secondary)',
                  marginBottom: 'var(--mobile-space-sm)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {template.description}
              </p>

              {/* Meta Info */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: 'var(--mobile-font-xs)',
                  color: 'var(--mobile-text-tertiary)',
                }}
              >
                <Tag
                  style={{
                    margin: 0,
                    padding: '2px 6px',
                    borderRadius: 'var(--mobile-radius-sm, 4px)',
                    background: `${getCategoryStyle(template.category)}20`,
                    color: getCategoryStyle(template.category),
                    fontSize: 'var(--mobile-font-xs)',
                  }}
                >
                  {template.category}
                </Tag>
                <span>{template.estimatedTime}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* FAB for creating new template */}
      <button
        className="mobile-fab"
        onClick={handleCreateTemplate}
        aria-label="Create new template"
      >
        <PlusOutlined style={{ fontSize: 24 }} />
      </button>
    </div>
  );
};

export default MobileTemplates;
