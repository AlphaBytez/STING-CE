import React from 'react';
import { useKratos } from '../auth/KratosProvider';

/**
 * EnterpriseFeature - Example enterprise feature requiring enterprise account type
 */
const EnterpriseFeature = () => {
  const { identity, accountType } = useKratos();
  
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-white mb-6">Enterprise Feature</h1>
          
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-yellow-400">Enterprise Access</h2>
              <span className="bg-purple-600 text-white px-3 py-1 rounded text-sm">
                Enterprise
              </span>
            </div>
            
            <p className="text-gray-300 mb-4">
              Welcome to enterprise-level features, {identity?.traits?.name?.first || identity?.traits?.email || 'User'}!
              Your {accountType} account unlocks our most powerful capabilities.
            </p>
            
            <div className="bg-purple-900 bg-opacity-30 border border-purple-800 rounded p-4 mb-4">
              <p className="text-purple-300">
                Enterprise feature content would go here. This could include advanced integrations,
                organization management tools, or specialized enterprise-grade functionality.
              </p>
            </div>
            
            <div className="bg-gray-600 p-4 rounded">
              <h3 className="font-semibold text-white mb-2">Enterprise Benefits</h3>
              <ul className="list-disc list-inside text-gray-300">
                <li>Unlimited usage</li>
                <li>Dedicated account manager</li>
                <li>Custom integration development</li>
                <li>SSO and advanced security</li>
                <li>SLA guarantees</li>
                <li>Custom training and onboarding</li>
                <li>Early access to new features</li>
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

export default EnterpriseFeature;