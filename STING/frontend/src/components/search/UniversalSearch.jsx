import React, { useState, useCallback, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  FileText, 
  Package, 
  Clock,
  Loader,
  Star,
  Eye,
  Download,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  X
} from 'lucide-react';
import api from '../../services/api';

const UniversalSearch = ({ isModal = false, onClose, initialQuery = '' }) => {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    honeyJars: [],
    documentTypes: [],
    dateRange: 'all'
  });
  const [showFilters, setShowFilters] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [expandedResults, setExpandedResults] = useState(new Set());

  // Load search history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('sting-search-history');
    if (saved) {
      try {
        setSearchHistory(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load search history:', e);
      }
    }
  }, []);

  // Save search to history
  const saveToHistory = useCallback((searchQuery) => {
    if (!searchQuery || searchQuery.length < 3) return;
    
    const newHistory = [
      { query: searchQuery, timestamp: Date.now() },
      ...searchHistory.filter(item => item.query !== searchQuery)
    ].slice(0, 10); // Keep last 10 searches
    
    setSearchHistory(newHistory);
    localStorage.setItem('sting-search-history', JSON.stringify(newHistory));
  }, [searchHistory]);

  const performSearch = async (searchQuery = query) => {
    if (!searchQuery || searchQuery.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const searchData = {
        query: searchQuery,
        top_k: 20,  // Changed from 'limit' to match backend parameter
        honey_jar_ids: filters.honeyJars.length > 0 ? filters.honeyJars : undefined,
        filters: {
          document_types: filters.documentTypes,
          date_range: filters.dateRange
        }
      };

      console.log('Performing search:', searchData);
      
      const response = await api.post('/api/knowledge/search', searchData);
      
      if (response.data.results) {
        setResults(response.data.results);
        saveToHistory(searchQuery);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.error || 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    performSearch();
  };

  const handleResultClick = (result) => {
    // Track click
    console.log('Clicked result:', result);
    
    // You could implement navigation to the honey jar or document here
    if (result.metadata?.honey_jar_id) {
      // Navigate to honey jar
      window.open(`/dashboard/honey-jars/${result.metadata.honey_jar_id}`, '_blank');
    }
  };

  const toggleResultExpansion = (resultId) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(resultId)) {
      newExpanded.delete(resultId);
    } else {
      newExpanded.add(resultId);
    }
    setExpandedResults(newExpanded);
  };

  const highlightText = (text, query) => {
    if (!query || !text) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    return text.split(regex).map((part, index) => 
      regex.test(part) ? 
        <mark key={index} className="bg-amber-400/30 text-amber-300 px-1 rounded">
          {part}
        </mark> : part
    );
  };

  const formatScore = (score) => {
    return (score * 100).toFixed(0);
  };

  return (
    <div className={`${isModal ? 'sting-glass-card sting-elevation-high rounded-lg border border-slate-700' : ''} p-6`}>
      {isModal && onClose && (
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Universal Search</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded transition-colors text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across all honey jars and documents..."
            className="w-full pl-10 pr-20 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-amber-400 focus:border-transparent"
          />
          <div className="absolute right-2 top-2 flex gap-2">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded transition-colors ${
                showFilters ? 'bg-amber-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              title="Search filters"
            >
              <Filter className="w-4 h-4" />
            </button>
            <button
              type="submit"
              disabled={loading || !query}
              className="px-4 py-2 bg-amber-600 text-white rounded transition-colors hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-slate-800/50 border border-slate-600 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Document Types
                </label>
                <div className="space-y-2">
                  {['PDF', 'Text', 'Markdown', 'Code', 'Other'].map(type => (
                    <label key={type} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={filters.documentTypes.includes(type)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFilters(prev => ({
                              ...prev,
                              documentTypes: [...prev.documentTypes, type]
                            }));
                          } else {
                            setFilters(prev => ({
                              ...prev,
                              documentTypes: prev.documentTypes.filter(t => t !== type)
                            }));
                          }
                        }}
                        className="mr-2 rounded"
                      />
                      <span className="text-sm text-slate-300">{type}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Date Range
                </label>
                <select
                  value={filters.dateRange}
                  onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value }))}
                  className="w-full p-2 bg-slate-700 border border-slate-600 rounded text-white"
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="year">This Year</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Quick Actions
                </label>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => setFilters({ honeyJars: [], documentTypes: [], dateRange: 'all' })}
                    className="block w-full text-left px-3 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors"
                  >
                    Clear Filters
                  </button>
                  <button
                    type="button"
                    onClick={performSearch}
                    className="block w-full text-left px-3 py-2 text-sm bg-amber-600 hover:bg-amber-700 text-white rounded transition-colors"
                  >
                    Apply & Search
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Search History */}
      {searchHistory.length > 0 && !query && !loading && results.length === 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-medium text-white mb-3">Recent Searches</h3>
          <div className="flex flex-wrap gap-2">
            {searchHistory.slice(0, 5).map((item, index) => (
              <button
                key={index}
                onClick={() => {
                  setQuery(item.query);
                  performSearch(item.query);
                }}
                className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-full text-sm transition-colors flex items-center gap-2"
              >
                <Clock className="w-3 h-3" />
                {item.query}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-400/30 rounded-lg text-red-300">
          <div className="font-medium">Search Error</div>
          <div className="text-sm">{error}</div>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">
              Search Results ({results.length})
            </h3>
            <div className="text-sm text-slate-400">
              Found {results.length} relevant chunks
            </div>
          </div>

          {results.map((result, index) => {
            const isExpanded = expandedResults.has(result.id || index);
            const previewLength = 200;
            const content = result.content || '';
            const shouldTruncate = content.length > previewLength;
            
            return (
              <div
                key={result.id || index}
                className="bg-slate-800/50 border border-slate-600 rounded-lg p-4 hover:border-slate-500 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-amber-400" />
                      <span className="font-medium text-white">
                        {result.metadata?.document_name || result.metadata?.filename || 'Document'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 px-2 py-1 bg-slate-700 rounded text-xs">
                      <Star className="w-3 h-3 text-amber-400" />
                      <span className="text-slate-300">{formatScore(result.score)}%</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {result.metadata?.honey_jar_name && (
                      <span className="px-2 py-1 bg-purple-600/20 text-purple-300 rounded text-xs flex items-center gap-1">
                        <Package className="w-3 h-3" />
                        {result.metadata.honey_jar_name}
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-slate-300 text-sm leading-relaxed">
                  {shouldTruncate && !isExpanded ? (
                    <>
                      {highlightText(content.substring(0, previewLength) + '...', query)}
                      <button
                        onClick={() => toggleResultExpansion(result.id || index)}
                        className="ml-2 text-amber-400 hover:text-amber-300 inline-flex items-center gap-1"
                      >
                        <ChevronDown className="w-3 h-3" />
                        Show more
                      </button>
                    </>
                  ) : (
                    <>
                      {highlightText(content, query)}
                      {shouldTruncate && (
                        <button
                          onClick={() => toggleResultExpansion(result.id || index)}
                          className="ml-2 text-amber-400 hover:text-amber-300 inline-flex items-center gap-1"
                        >
                          <ChevronUp className="w-3 h-3" />
                          Show less
                        </button>
                      )}
                    </>
                  )}
                </div>

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-600">
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    {result.metadata?.chunk_index !== undefined && (
                      <span>Chunk {result.metadata.chunk_index + 1}</span>
                    )}
                    {result.metadata?.document_id && (
                      <span>ID: {result.metadata.document_id.substring(0, 8)}...</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleResultClick(result)}
                      className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-xs transition-colors flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" />
                      View
                    </button>
                    {result.metadata?.honey_jar_id && (
                      <button
                        onClick={() => window.open(`/dashboard/honey-jars/${result.metadata.honey_jar_id}`, '_blank')}
                        className="px-3 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 rounded text-xs transition-colors flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Open Jar
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* No Results */}
      {query && !loading && results.length === 0 && !error && (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No results found</h3>
          <p className="text-slate-400">
            Try adjusting your search terms or removing filters
          </p>
        </div>
      )}

      {/* Empty State */}
      {!query && !loading && results.length === 0 && !error && searchHistory.length === 0 && (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Universal Search</h3>
          <p className="text-slate-400">
            Search across all your honey jars and documents using semantic search powered by ChromaDB
          </p>
          <div className="mt-4 text-sm text-slate-500">
            <strong>Tips:</strong> Use natural language, ask questions, or search for concepts
          </div>
        </div>
      )}
    </div>
  );
};

export default UniversalSearch;