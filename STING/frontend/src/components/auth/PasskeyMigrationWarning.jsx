import React, { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

/**
 * PasskeyMigrationWarning - Shows a warning when passkey authentication fails
 * This helps users understand they need to clear old passkeys after system changes
 */
const PasskeyMigrationWarning = ({ show, onClose }) => {
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    if (show) {
      setIsVisible(true);
      // Store that we've shown this warning
      sessionStorage.setItem('passkey_warning_shown', 'true');
    }
  }, [show]);
  
  if (!isVisible) return null;
  
  const handleClose = () => {
    setIsVisible(false);
    if (onClose) onClose();
  };
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="relative max-w-lg w-full bg-gray-800 rounded-lg shadow-xl border border-yellow-500/50 animate-slide-up">
        <div className="p-6">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              <AlertTriangle className="h-6 w-6 text-yellow-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white mb-2">
                Passkey Authentication Failed
              </h3>
              <div className="text-sm text-gray-300 space-y-3">
                <p>
                  Your browser is trying to use an old passkey that is no longer valid. This typically happens after:
                </p>
                <ul className="list-disc list-inside space-y-1 text-gray-400">
                  <li>System reinstallation or migration</li>
                  <li>Authentication system changes</li>
                  <li>Security updates that reset credentials</li>
                  <li>Database restoration from backup</li>
                </ul>
                <div className="mt-3 p-2 bg-red-900/30 rounded text-sm">
                  <p className="text-red-400">
                    <strong>Note:</strong> Your browser still remembers the old passkey, but the server no longer recognizes it.
                  </p>
                </div>
                <div className="bg-gray-900/50 rounded p-3 mt-4">
                  <p className="font-semibold text-yellow-400 mb-2">To fix this:</p>
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    <li>
                      <span className="font-medium">Clear your browser's saved passkeys:</span>
                      <div className="ml-6 mt-1 text-gray-400">
                        Chrome/Edge: Go to{' '}
                        <code className="bg-gray-700 px-1 py-0.5 rounded text-xs">
                          chrome://settings/passkeys
                        </code>
                      </div>
                    </li>
                    <li>Delete all passkeys for <code className="bg-gray-700 px-1 py-0.5 rounded text-xs">localhost</code></li>
                    <li>Login with your password</li>
                    <li>Set up a new passkey in your account settings</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-6 flex justify-end space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white transition-colors"
            >
              I'll login with password
            </button>
            <button
              onClick={() => {
                window.open('chrome://settings/passkeys', '_blank');
                handleClose();
              }}
              className="px-4 py-2 text-sm font-medium bg-yellow-600 text-black rounded hover:bg-yellow-500 transition-colors"
            >
              Open Passkey Settings
            </button>
          </div>
        </div>
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};

export default PasskeyMigrationWarning;