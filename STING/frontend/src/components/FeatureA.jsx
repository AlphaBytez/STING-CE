import React from 'react';
import { useKratos } from '../auth/KratosProvider';

/**
 * FeatureA - Example feature available to all account types
 */
const FeatureA = () => {
  const { identity } = useKratos();
  
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-white mb-6">Feature A</h1>
          
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-yellow-400 mb-4">Standard Feature</h2>
            <p className="text-gray-300 mb-4">
              This is a standard feature available to all account types. 
              Welcome, {identity?.traits?.name?.first || identity?.traits?.email || 'User'}!
            </p>
            <div className="bg-blue-900 bg-opacity-30 border border-blue-800 rounded p-4">
              <p className="text-blue-300">
                Feature A functionality would go here. This could be any basic feature
                of your application that all users have access to.
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

export default FeatureA;