import React from 'react';
import { useLocation } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProvider';

const SettingsDebugInfo = () => {
  const location = useLocation();
  const { identity, kratosUrl } = useKratos();

  return (
    <div className="fixed bottom-4 left-4 bg-gray-800 text-white p-4 rounded-lg shadow-lg max-w-md z-50">
      <h3 className="font-bold mb-2 text-yellow-400">Settings Debug Info</h3>
      <div className="text-sm space-y-1">
        <p><strong>Current Route:</strong> {location.pathname}</p>
        <p><strong>Component:</strong> KratosSettings</p>
        <p><strong>User Email:</strong> {identity?.traits?.email || 'Not loaded'}</p>
        <p><strong>Kratos URL:</strong> {kratosUrl}</p>
        <p><strong>WebAuthn Enabled:</strong> Yes</p>
        <p><strong>Flow ID:</strong> {new URLSearchParams(location.search).get('flow') || 'None'}</p>
      </div>
      <button 
        onClick={() => {
          // Force reload to clear any cached components
          window.location.reload();
        }}
        className="mt-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs"
      >
        Force Reload
      </button>
    </div>
  );
};

export default SettingsDebugInfo;