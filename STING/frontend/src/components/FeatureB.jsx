import React from 'react';
import { useKratos } from '../auth/KratosProvider';

/**
 * FeatureB - Another example feature available to all account types
 */
const FeatureB = () => {
  const { identity } = useKratos();
  
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-white mb-6">Feature B</h1>
          
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-yellow-400 mb-4">Standard Feature</h2>
            <p className="text-gray-300 mb-4">
              This is another standard feature available to all account types. 
              Welcome, {identity?.traits?.name?.first || identity?.traits?.email || 'User'}!
            </p>
            <div className="bg-green-900 bg-opacity-30 border border-green-800 rounded p-4">
              <p className="text-green-300">
                Feature B functionality would go here. This represents another core
                feature of your application available to all users.
              </p>
            </div>
          </div>
          
          <button
            onClick={() => window.history.back()}
            className="bg-gray-600 hover:bg-gray-500 text-white py-2 px-4 rounded"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeatureB;