import React, { useState, useEffect, useRef } from 'react';
import { Search, Database, Lock, Unlock, ChevronDown, Check, X, Loader, Info, Shield } from 'lucide-react';
import HoneyIcon from '../icons/HoneyIcon';
import { api } from '../../utils/apiClient';
import { honeyJarApi } from '../../services/knowledgeApi';

/**
 * HoneyJarContextBar - A clean context bar that sits above the chat input
 * Shows current honey jar selection and allows searching/switching contexts
 */
const HoneyJarContextBar = ({ currentHoneyJar, onHoneyJarChange, onSearchStateChange, className = '' }) => {
  const [honeyJars, setHoneyJars] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const searchRef = useRef(null);
  const inputRef = useRef(null);

  // Don't automatically load honey jars on mount - wait for user interaction
  // This prevents unnecessary auth failures when user lands on Bee Chat page
  // useEffect(() => {
  //   loadHoneyJars();
  // }, []);

  // Focus search input when opened and notify parent
  useEffect(() => {
    if (isSearchOpen && inputRef.current) {
      inputRef.current.focus();
    }
    // Notify parent component about search state
    if (onSearchStateChange) {
      onSearchStateChange(isSearchOpen);
    }
  }, [isSearchOpen, onSearchStateChange]);

  // Handle click outside to close search
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setIsSearchOpen(false);
        setSearchQuery('');
      }
    };

    if (isSearchOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isSearchOpen]);

  const loadHoneyJars = async () => {
    try {
      setLoading(true);
      setError(null);
      // Use same API method as working HoneyJarPage
      const response = await honeyJarApi.getHoneyJars(1, 100);
      const jarData = Array.isArray(response) ? response : (response.items || []);
      setHoneyJars(jarData);
    } catch (err) {
      console.error('Failed to load honey jars:', err);
      
      // Provide clear, actionable error messages based on error type
      if (err.response?.status === 401) {
        setError('Please log in to access honey jars. Click here to sign in.');
        // Show sample public honey jars for demonstration
        setHoneyJars([
          {
            id: 'sample-1',
            name: 'STING Platform Documentation',
            description: 'Core documentation and guides for the STING platform',
            type: 'public',
            tags: ['documentation', 'platform', 'guides'],
            stats: { document_count: 0 }
          },
          {
            id: 'support-general',
            name: 'General Support Knowledge',
            description: 'FAQs, troubleshooting guides, and common solutions',
            type: 'public',
            tags: ['support', 'faq', 'troubleshooting'],
            stats: { document_count: 0 }
          }
        ]);
      } else if (err.response?.status === 403) {
        setError('Session expired. Please refresh the page and try again.');
      } else if (err.response?.status === 503 || err.code === 'ECONNABORTED') {
        setError('Knowledge service is temporarily unavailable. Please try again in a moment.');
      } else if (!err.response) {
        setError('Unable to connect to the knowledge service. Please check your internet connection.');
      } else {
        // Generic error with retry option
        setError('Unable to load honey jars. Click here to retry.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Filter honey jars based on search
  const filteredJars = honeyJars.filter(jar => 
    jar.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    jar.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    jar.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleSelectJar = (jar) => {
    onHoneyJarChange(jar);
    setIsSearchOpen(false);
    setSearchQuery('');
  };

  const clearSelection = () => {
    onHoneyJarChange(null);
    setSearchQuery('');
  };

  return (
    <div className={`honey-jar-context-bar ${className}`}>
      <div className="flex items-center justify-between p-3 bg-gray-800/60 backdrop-blur-sm border-t border-gray-700">
        {/* Current Context Display */}
        <div className="flex items-center gap-3 flex-1">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <HoneyIcon size={16} color="rgb(251 191 36)" />
            <span>Context:</span>
          </div>
          
          {currentHoneyJar ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-full">
                {currentHoneyJar.isSystemDefault ? (
                  <Shield className="w-4 h-4" title="STING System Knowledge (Auto-loaded)" />
                ) : (
                  <Database className="w-4 h-4" />
                )}
                <span className="text-sm font-medium">{currentHoneyJar.name}</span>
                <span className="text-xs opacity-70">({currentHoneyJar.stats?.document_count || 0} docs)</span>
                {currentHoneyJar.isSystemDefault && (
                  <span className="text-xs px-1.5 py-0.5 bg-blue-500/30 text-blue-300 rounded text-[10px]">AUTO</span>
                )}
              </div>
              <button
                onClick={clearSelection}
                className="p-1 hover:bg-gray-700 rounded transition-colors"
                title="Clear context"
              >
                <X className="w-4 h-4 text-gray-400 hover:text-white" />
              </button>
            </div>
          ) : (
            <span className="text-sm text-gray-500 italic">No honey jar selected</span>
          )}
        </div>

        {/* Search/Select Button */}
        <button
          onClick={() => {
            if (!isSearchOpen) {
              // Load honey jars only when user clicks to search
              console.log('🐝 Honey jar search clicked - state:', {
                honeyJarsLength: honeyJars.length,
                loading,
                error: error?.message || null
              });

              if (honeyJars.length === 0) {
                // Always try to load when no honey jars are present
                console.log('🔄 Loading honey jars...');
                setError(null); // Clear any previous errors
                loadHoneyJars();
              }
            }
            setIsSearchOpen(!isSearchOpen);
          }}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
        >
          <Search className="w-4 h-4" />
          <span className="text-sm">Search Honey Jars</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${isSearchOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Search Panel Overlay */}
      {isSearchOpen && (
        <>
          {/* Dark overlay */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setIsSearchOpen(false)}
          />
          
          {/* Search Panel */}
          <div 
            ref={searchRef}
            className="fixed bottom-0 left-0 right-0 bg-gray-800 border-t border-gray-700 shadow-2xl overflow-hidden animate-slide-up z-50"
            style={{ maxHeight: '70vh' }}
          >
          {/* Search Input */}
          <div className="p-4 border-b border-gray-700">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search honey jars by name, description, or tags..."
                className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
              />
            </div>
          </div>

          {/* Results */}
          <div className="max-h-[300px] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <Loader className="w-6 h-6 text-yellow-500 animate-spin mx-auto mb-2" />
                <p className="text-sm text-gray-400">Loading honey jars...</p>
              </div>
            ) : error && honeyJars.length === 0 ? (
              <div className="p-8 text-center">
                <Info className="w-8 h-8 text-yellow-500 mx-auto mb-3" />
                <p className="text-sm text-gray-300 mb-3">{error}</p>
                {error.includes('log in') ? (
                  <button 
                    onClick={() => window.location.href = '/login'}
                    className="px-4 py-2 bg-yellow-500 text-black text-sm font-medium rounded-lg hover:bg-yellow-400 transition-colors"
                  >
                    Sign In
                  </button>
                ) : error.includes('refresh') ? (
                  <button 
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 bg-yellow-500 text-black text-sm font-medium rounded-lg hover:bg-yellow-400 transition-colors"
                  >
                    Refresh Page
                  </button>
                ) : (
                  <button 
                    onClick={loadHoneyJars}
                    className="px-4 py-2 bg-yellow-500 text-black text-sm font-medium rounded-lg hover:bg-yellow-400 transition-colors"
                  >
                    Try Again
                  </button>
                )}
              </div>
            ) : filteredJars.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">
                {searchQuery ? 'No matching honey jars found' : 'No honey jars available'}
              </div>
            ) : (
              <div className="p-2">
                {error && (
                  <div className="p-3 mb-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                    <p className="text-xs text-yellow-400 flex items-center gap-2">
                      <Info className="w-4 h-4" />
                      {error}
                    </p>
                  </div>
                )}
                {filteredJars.map((jar) => (
                  <button
                    key={jar.id}
                    onClick={() => handleSelectJar(jar)}
                    className={`w-full p-3 rounded-lg hover:bg-gray-700 transition-all text-left mb-1 group ${
                      currentHoneyJar?.id === jar.id ? 'bg-gray-700' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Database className="w-4 h-4 text-yellow-400" />
                          <h5 className="text-sm font-medium text-white truncate">
                            {jar.name}
                          </h5>
                          {currentHoneyJar?.id === jar.id && (
                            <Check className="w-4 h-4 text-green-400" />
                          )}
                        </div>
                        <p className="text-xs text-gray-400 line-clamp-2 mb-2">
                          {jar.description}
                        </p>
                        <div className="flex items-center gap-4 text-xs">
                          <span className="text-gray-500">
                            {jar.stats?.document_count || 0} documents
                          </span>
                          <span className="flex items-center gap-1 text-gray-500">
                            {jar.type === 'public' ? (
                              <Unlock className="w-3 h-3" />
                            ) : (
                              <Lock className="w-3 h-3" />
                            )}
                            {jar.type || 'private'}
                          </span>
                          {jar.tags.length > 0 && (
                            <div className="flex gap-1">
                              {jar.tags.slice(0, 3).map((tag, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-gray-600 rounded text-gray-300">
                                  {tag}
                                </span>
                              ))}
                              {jar.tags.length > 3 && (
                                <span className="text-gray-500">+{jar.tags.length - 3}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="p-3 border-t border-gray-700 flex items-center justify-between">
            <button 
              onClick={() => setIsSearchOpen(false)}
              className="text-sm text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <div className="text-xs text-gray-500">
              {filteredJars.length} honey jar{filteredJars.length !== 1 ? 's' : ''} available
            </div>
          </div>
        </div>
        </>
      )}
    </div>
  );
};

export default HoneyJarContextBar;