import React, { useState } from 'react';
import { Search, X } from 'lucide-react';
import UniversalSearch from './UniversalSearch';

const SearchWidget = () => {
  const [showModal, setShowModal] = useState(false);
  const [query, setQuery] = useState('');

  const handleQuickSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setShowModal(true);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
  };

  return (
    <>
      {/* Quick Search Bar */}
      <div className="relative">
        <form onSubmit={handleQuickSearch}>
          <div className="relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search honey jars..."
              className="w-full pl-9 pr-4 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-amber-400 focus:border-transparent text-sm"
              onFocus={() => {
                if (query.trim()) {
                  setShowModal(true);
                }
              }}
            />
          </div>
        </form>
      </div>

      {/* Search Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-20">
          <div className="w-full max-w-4xl mx-4 max-h-[80vh] overflow-hidden">
            <UniversalSearch 
              isModal={true} 
              onClose={handleCloseModal}
              initialQuery={query}
            />
          </div>
        </div>
      )}

      {/* Global Search Shortcut Listener */}
      <GlobalSearchShortcut onOpenSearch={() => setShowModal(true)} />
    </>
  );
};

// Component to handle global keyboard shortcuts
const GlobalSearchShortcut = ({ onOpenSearch }) => {
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux) to open search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onOpenSearch();
      }
      // Escape to close (handled by the modal itself)
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onOpenSearch]);

  return null;
};

export default SearchWidget;