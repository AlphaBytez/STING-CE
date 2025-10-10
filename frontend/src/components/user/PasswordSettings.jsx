import React, { useState, useEffect } from 'react';
import { Lock, AlertCircle, CheckCircle } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';

const PasswordSettings = () => {
  const { identity, kratosUrl } = useKratos();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChanging, setIsChanging] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    setIsChanging(true);

    try {
      // Call the backend API to change password
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to change password');
      }
      
      setSuccess('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      
      // Check if user needs to be redirected (e.g., if it was a forced password change)
      if (data.redirect) {
        window.location.href = data.redirect;
      }
    } catch (err) {
      console.error('Error changing password:', err);
      setError(err.message || 'Failed to change password. Please try again.');
    } finally {
      setIsChanging(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <h2 className="text-xl font-semibold mb-6">Password Settings</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-900 text-red-300 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-900 text-green-300 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5" />
          {success}
        </div>
      )}

      <form onSubmit={handlePasswordChange} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Current Password
          </label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-600 rounded-lg focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            New Password
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-600 rounded-lg focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Confirm New Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-600 rounded-lg focus:ring-yellow-400 focus:border-yellow-400 placeholder-gray-500"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isChanging}
          className="w-full bg-yellow-400 text-gray-900 py-2 px-4 rounded-lg hover:bg-yellow-500 
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isChanging ? 'Changing Password...' : 'Change Password'}
        </button>

        <div className="mt-4 text-sm text-gray-400">
          <h3 className="font-medium text-gray-300 mb-2">Password Requirements:</h3>
          <ul className="list-disc pl-5 space-y-1">
            <li>At least 8 characters</li>
            <li>Must include uppercase and lowercase letters</li>
            <li>Must include at least one number</li>
            <li>Must include at least one special character</li>
          </ul>
        </div>
      </form>
    </div>
  );
};

export default PasswordSettings;