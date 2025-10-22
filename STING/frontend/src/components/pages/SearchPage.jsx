import React from 'react';
import UniversalSearch from '../search/UniversalSearch';

const SearchPage = () => {
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Search</h1>
        <p className="text-slate-400">
          Search across all your honey jars and documents using semantic search powered by ChromaDB
        </p>
      </div>
      
      <UniversalSearch />
    </div>
  );
};

export default SearchPage;