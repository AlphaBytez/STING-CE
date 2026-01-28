import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Spin } from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  FileOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { searchApi } from '../../../services/knowledgeApi';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * Filter options for search
 */
const SEARCH_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'documents', label: 'Documents' },
  { key: 'honey_jars', label: 'Honey Jars' },
  { key: 'reports', label: 'Reports' },
  { key: 'templates', label: 'Templates' },
];

/**
 * Get icon for result type
 */
const getResultIcon = (type) => {
  switch (type) {
    case 'document':
      return <FileTextOutlined />;
    case 'honey_jar':
      return <AppstoreOutlined />;
    case 'report':
      return <DatabaseOutlined />;
    case 'template':
      return <FileOutlined />;
    default:
      return <FileOutlined />;
  }
};

/**
 * MobileSearch - Mobile search page
 * Search interface optimized for mobile with filters and real-time results
 */
const MobileSearch = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');
  const [recentSearches, setRecentSearches] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }

    const timer = setTimeout(() => {
      performSearch(query, activeFilter);
    }, 300);

    return () => clearTimeout(timer);
  }, [query, activeFilter]);

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('sting-mobile-recent-searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse recent searches:', e);
      }
    }
  }, []);

  // Perform search
  const performSearch = async (searchQuery, filter) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setHasSearched(true);

    try {
      const response = await searchApi.search(searchQuery, {
        filters: filter !== 'all' ? { type: filter } : {},
        topK: 20,
      });

      setResults(response.results || []);
    } catch (error) {
      console.error('Search failed:', error);
      message.error('Search failed');

      // Fallback mock results
      setResults([
        {
          id: '1',
          type: 'document',
          title: `${searchQuery} - Project Notes`,
          preview: 'This document contains information about...',
          source: 'Honey Jar 1',
          score: 0.95,
        },
        {
          id: '2',
          type: 'honey_jar',
          title: `${searchQuery} Knowledge Base`,
          preview: 'A collection of documents related to...',
          source: 'My Honey Jars',
          score: 0.87,
        },
        {
          id: '3',
          type: 'report',
          title: `${searchQuery} Analysis Report`,
          preview: 'This report provides insights on...',
          source: 'Reports',
          score: 0.82,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handle search submit
  const handleSearch = (e) => {
    e?.preventDefault();
    if (query.trim()) {
      // Add to recent searches
      const updated = [query, ...recentSearches.filter(s => s !== query)].slice(0, 10);
      setRecentSearches(updated);
      localStorage.setItem('sting-mobile-recent-searches', JSON.stringify(updated));

      // Perform search
      performSearch(query, activeFilter);
    }
  };

  // Handle result click
  const handleResultClick = (result) => {
    switch (result.type) {
      case 'document':
        navigate(`/m/honey-jars/${result.honeyJarId || 'default'}?doc=${result.id}`);
        break;
      case 'honey_jar':
        navigate(`/m/honey-jars/${result.id}`);
        break;
      case 'report':
        navigate(`/m/reports/${result.id}`);
        break;
      case 'template':
        navigate(`/m/templates/${result.id}`);
        break;
      default:
        break;
    }
  };

  // Clear search
  const handleClearSearch = () => {
    setQuery('');
    setResults([]);
    setHasSearched(false);
  };

  // Handle recent search click
  const handleRecentSearchClick = (search) => {
    setQuery(search);
    setActiveFilter('all');
  };

  return (
    <div className="mobile-page">
      <h1 className="mobile-page-title">Search</h1>

      {/* Search Input */}
      <div className="mobile-search-container">
        <div className="mobile-search-input-wrapper">
          <SearchOutlined className="mobile-search-icon" />
          <form onSubmit={handleSearch} style={{ width: '100%' }}>
            <input
              type="text"
              className="mobile-search-input"
              placeholder="Search documents, honey jars, reports..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>
          {query && (
            <button
              onClick={handleClearSearch}
              style={{
                position: 'absolute',
                right: 'var(--mobile-space-md)',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--mobile-text-tertiary)',
                cursor: 'pointer',
              }}
            >
              <CloseOutlined />
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="mobile-search-filters">
          {SEARCH_FILTERS.map((filter) => (
            <button
              key={filter.key}
              className={`mobile-search-filter ${activeFilter === filter.key ? 'active' : ''}`}
              onClick={() => setActiveFilter(filter.key)}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      <div className="mobile-search-results" style={{ marginTop: 'var(--mobile-space-md)' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 'var(--mobile-space-xl)' }}>
            <Spin />
            <p style={{ color: 'var(--mobile-text-secondary)', marginTop: 'var(--mobile-space-sm)' }}>
              Searching...
            </p>
          </div>
        ) : hasSearched ? (
          results.length > 0 ? (
            <>
              <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)', marginBottom: 'var(--mobile-space-sm)' }}>
                {results.length} results found
              </p>
              {results.map((result) => (
                <div
                  key={result.id}
                  className="mobile-search-result-item"
                  onClick={() => handleResultClick(result)}
                >
                  <div className="mobile-search-result-icon">
                    {getResultIcon(result.type)}
                  </div>
                  <div className="mobile-search-result-content">
                    <div className="mobile-search-result-title">{result.title}</div>
                    <div className="mobile-search-result-preview">{result.preview}</div>
                    <div className="mobile-search-result-meta">
                      {result.source} {result.score && `• ${Math.round(result.score * 100)}% match`}
                    </div>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="mobile-empty-state">
              <SearchOutlined className="mobile-empty-state-icon" />
              <div className="mobile-empty-state-title">No results found</div>
              <div className="mobile-empty-state-description">
                Try different keywords or clear filters
              </div>
            </div>
          )
        ) : (
          /* Recent Searches */
          recentSearches.length > 0 && (
            <div className="mobile-section">
              <h2 className="mobile-section-title">Recent Searches</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-xs)' }}>
                {recentSearches.map((search, index) => (
                  <button
                    key={index}
                    onClick={() => handleRecentSearchClick(search)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--mobile-space-md)',
                      padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
                      background: 'var(--mobile-surface)',
                      border: '1px solid var(--mobile-border)',
                      borderRadius: 'var(--mobile-radius-md, 8px)',
                      color: 'var(--mobile-text-primary)',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    <SearchOutlined style={{ color: 'var(--mobile-text-tertiary)' }} />
                    <span style={{ flex: 1 }}>{search}</span>
                  </button>
                ))}
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default MobileSearch;
