import React, { useState, useEffect, useRef } from 'react';
import { Search, Database, Lock, Unlock, ChevronDown, Check, X } from 'lucide-react';
import HoneyIcon from '../icons/HoneyIcon';
import { api } from '../../utils/apiClient';
import { honeyJarApi } from '../../services/knowledgeApi';

/**
 * HoneyJarSelector - Component for selecting and viewing honey jar context
 * Replaces the Nectar Flow section in Grains
 */
const HoneyJarSelector = ({ currentHoneyJar, onHoneyJarChange, className = '' }) => {
  const [honeyJars, setHoneyJars] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const dropdownRef = useRef(null);

  // Load available honey jars
  useEffect(() => {
    loadHoneyJars();
  }, []);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
        setSearchQuery('');
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isDropdownOpen]);

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
      setError('Failed to load honey jars');
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
    setIsDropdownOpen(false);
    setSearchQuery('');
  };

  const clearSelection = () => {
    onHoneyJarChange(null);
    setSearchQuery('');
  };

  return (
    <div className={className}>
      <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
        <Database className="w-4 h-4 text-yellow-400" />
        <HoneyIcon size={16} color="rgb(251 191 36)" />
        Honey Jar Context
      </h4>

      {/* Current Selection or Dropdown */}
      <div className="relative">
        {currentHoneyJar ? (
          // Show current honey jar info
          <div className="glass-card p-3 rounded-lg">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <h5 className="text-sm font-medium text-yellow-400 truncate">
                  {currentHoneyJar.name}
                </h5>
                <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                  {currentHoneyJar.description}
                </p>
                <div className="flex items-center gap-3 mt-2 text-xs">
                  <span className="text-gray-500">
                    {currentHoneyJar.stats?.document_count || 0} docs
                  </span>
                  <span className="flex items-center gap-1 text-gray-500">
                    {currentHoneyJar.type === 'public' ? (
                      <Unlock className="w-3 h-3" />
                    ) : (
                      <Lock className="w-3 h-3" />
                    )}
                    {currentHoneyJar.type || 'private'}
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-1">
                <button
                  onClick={() => setIsDropdownOpen(true)}
                  className="p-1 hover:bg-gray-600 rounded transition-colors"
                  title="Change honey jar"
                >
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                </button>
                <button
                  onClick={clearSelection}
                  className="p-1 hover:bg-gray-600 rounded transition-colors"
                  title="Clear context"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Show dropdown trigger
          <button
            onClick={() => setIsDropdownOpen(true)}
            className="w-full glass-card p-3 rounded-lg hover:bg-gray-600/50 transition-all flex items-center justify-between"
          >
            <span className="text-sm text-gray-400">Select a honey jar...</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
        )}

        {/* Dropdown Menu */}
        {isDropdownOpen && (
          <div 
            ref={dropdownRef}
            className="absolute top-full mt-2 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg max-h-80 overflow-hidden animate-fade-in-scale"
            style={{ zIndex: 10000, backgroundColor: 'rgba(31, 41, 55, 0.95)' }}>
            {/* Search Bar */}
            <div className="p-3 border-b border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search honey jars..."
                  className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  autoFocus
                />
              </div>
            </div>

            {/* Honey Jar List */}
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center text-gray-400 text-sm">
                  Loading honey jars...
                </div>
              ) : error ? (
                <div className="p-4 text-center text-red-400 text-sm">
                  {error}
                </div>
              ) : filteredJars.length === 0 ? (
                <div className="p-4 text-center text-gray-400 text-sm">
                  {searchQuery ? 'No matching honey jars found' : 'No honey jars available'}
                </div>
              ) : (
                <div className="p-2">
                  {filteredJars.map((jar) => (
                    <button
                      key={jar.id}
                      onClick={() => handleSelectJar(jar)}
                      className={`w-full p-3 rounded-lg hover:bg-gray-600/50 transition-all text-left mb-1 ${
                        currentHoneyJar?.id === jar.id ? 'bg-gray-600/50' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h5 className="text-sm font-medium text-white truncate flex items-center gap-2">
                            {jar.name}
                            {currentHoneyJar?.id === jar.id && (
                              <Check className="w-3 h-3 text-green-400" />
                            )}
                          </h5>
                          <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                            {jar.description}
                          </p>
                          <div className="flex items-center gap-3 mt-2">
                            <span className="text-xs text-gray-500">
                              {jar.stats?.document_count || 0} docs
                            </span>
                            <span className="flex items-center gap-1 text-xs text-gray-500">
                              {jar.type === 'public' ? (
                                <Unlock className="w-3 h-3" />
                              ) : (
                                <Lock className="w-3 h-3" />
                              )}
                              {jar.type || 'private'}
                            </span>
                            {jar.tags && jar.tags.length > 0 && (
                              <div className="flex gap-1">
                                {jar.tags.slice(0, 2).map((tag, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-0.5 bg-gray-700 text-xs rounded text-gray-300"
                                  >
                                    {tag}
                                  </span>
                                ))}
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

            {/* Close button */}
            <div className="p-3 border-t border-gray-700">
              <button
                onClick={() => {
                  setIsDropdownOpen(false);
                  setSearchQuery('');
                }}
                className="w-full py-2 px-3 text-sm text-gray-400 hover:text-white hover:bg-gray-600 rounded-lg transition-all"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Access Info */}
      {currentHoneyJar && (
        <div className="mt-3 p-2 bg-gray-700/50 rounded-lg">
          <p className="text-xs text-gray-400">
            {currentHoneyJar.type === 'public' ? (
              <>
                <Unlock className="w-3 h-3 inline mr-1" />
                Public access - Available to all users
              </>
            ) : (
              <>
                <Lock className="w-3 h-3 inline mr-1" />
                Restricted - Requires permission
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
};

export default HoneyJarSelector;