// src/components/user/AccountDeletion.jsx
import React, { useState } from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';

const AccountDeletion = () => {
  const { identity, kratosUrl } = useKratos();
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteRequest = () => {
    setIsConfirmOpen(true);
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setError('');

    if (confirmation !== 'DELETE') {
        setError('Please type DELETE to confirm account deletion');
        return;
    }

    setIsDeleting(true);
    try {
        // In a real implementation, you would use Kratos API to delete the account
        // For example, starting a settings flow for account deletion

        // Example implementation (not actually implemented here):
        // 1. Verify current password with Kratos
        // 2. Initiate account deletion through API call
        
        setError('This feature is not implemented in the demo');
        setIsDeleting(false);
    } catch (err) {
        setError('Failed to initiate account deletion. Please try again.');
        setIsDeleting(false);
    }
};


  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mb-4">
          <Trash2 className="w-6 h-6 text-red-600" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900">Delete Account</h2>
        <p className="mt-2 text-gray-600">
          Once you delete your account, there is no going back. Please be certain.
        </p>
      </div>

      {!isConfirmOpen ? (
        <div className="text-center">
          <button
            onClick={handleDeleteRequest}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 
                     transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Delete Account
          </button>
        </div>
      ) : (
        <>
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-3 text-red-600 mb-3">
              <AlertTriangle className="w-5 h-5" />
              <h3 className="font-semibold">Warning: This action cannot be undone</h3>
            </div>
            <ul className="text-sm text-red-600 list-disc pl-5 space-y-1">
              <li>All your data will be permanently deleted</li>
              <li>You will lose access to all teams and projects</li>
              <li>Your username will become available to others</li>
              <li>This action is permanent and cannot be reversed</li>
            </ul>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-900 text-red-300 rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleDeleteAccount} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-red-500 focus:border-red-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type DELETE to confirm
              </label>
              <input
                type="text"
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-red-500 focus:border-red-500"
                placeholder="Type DELETE"
                required
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setIsConfirmOpen(false)}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 
                         transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isDeleting || confirmation !== 'DELETE'}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 
                         transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 
                         focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? 'Deleting Account...' : 'Permanently Delete Account'}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
};

export default AccountDeletion;