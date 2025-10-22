import React from 'react';
import { useKratos } from '../auth/KratosProvider';

/**
 * PremiumFeature - Example premium feature requiring premium account type
 */
const PremiumFeature = () => {
  const { identity, accountType } = useKratos();
  
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-white mb-6">Premium Feature</h1>
          
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-yellow-400">Premium Access</h2>
              <span className="bg-yellow-600 text-white px-3 py-1 rounded text-sm">
                Premium
              </span>
            </div>
            
            <p className="text-gray-300 mb-4">
              Congratulations {identity?.traits?.name?.first || identity?.traits?.email || 'User'}!
              You have access to this premium feature with your {accountType} account.
            </p>
            
            <div className="bg-yellow-900 bg-opacity-30 border border-yellow-800 rounded p-4 mb-4">
              <p className="text-yellow-300">
                Premium feature content would go here. This could be advanced functionality,
                increased limits, or special tools only available to premium subscribers.
              </p>
            </div>
            
            <div className="bg-gray-600 p-4 rounded">
              <h3 className="font-semibold text-white mb-2">Premium Benefits</h3>
              <ul className="list-disc list-inside text-gray-300">
                <li>Higher usage limits</li>
                <li>Priority support</li>
                <li>Advanced analytics</li>
                <li>Custom reporting</li>
                <li>Enhanced security features</li>
              </ul>
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

export default PremiumFeature;