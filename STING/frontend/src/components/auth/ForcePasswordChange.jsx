import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, AlertCircle, CheckCircle } from 'lucide-react';
import '../../theme/sting-glass-theme.css';
import '../../theme/glass-login-override.css';

const ForcePasswordChange = () => {
  const navigate = useNavigate();
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

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsChanging(true);

    try {
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
      
      setSuccess('Password changed successfully! Setting up TOTP security...');
      
      // Use redirect from backend response or default to security settings
      const redirectUrl = data.redirect || '/settings?tab=security';
      
      // Redirect after successful password change
      setTimeout(() => {
        navigate(redirectUrl);
      }, 2000);
      
    } catch (err) {
      console.error('Error changing password:', err);
      setError(err.message || 'Failed to change password. Please try again.');
    } finally {
      setIsChanging(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background gradient - matches login page */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
      
      {/* Animated background shapes */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      {/* Glass card container */}
      <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-yellow-400 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-gray-900" />
          </div>
          <h2 className="text-2xl font-bold text-white">Password Change Required</h2>
          <p className="text-gray-300 mt-2">
            For security reasons, you must change your password before continuing.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 text-red-300 rounded-lg flex items-center gap-2 border border-red-800/50">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-900/30 text-green-300 rounded-lg flex items-center gap-2 border border-green-800/50">
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
              className="w-full px-4 py-2 bg-gray-800/50 text-white border border-gray-600/50 rounded-lg 
                       focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 
                       placeholder-gray-500 backdrop-blur-sm"
              placeholder="Enter your current password"
              required
              autoFocus
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
              className="w-full px-4 py-2 bg-gray-800/50 text-white border border-gray-600/50 rounded-lg 
                       focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 
                       placeholder-gray-500 backdrop-blur-sm"
              placeholder="Enter your new password"
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
              className="w-full px-4 py-2 bg-gray-800/50 text-white border border-gray-600/50 rounded-lg 
                       focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 
                       placeholder-gray-500 backdrop-blur-sm"
              placeholder="Confirm your new password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isChanging}
            className="w-full bg-yellow-400 text-gray-900 py-3 px-4 rounded-lg hover:bg-yellow-500 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all
                     font-semibold text-lg mt-6"
          >
            {isChanging ? 'Changing Password...' : 'Change Password'}
          </button>
        </form>

        <div className="mt-6 p-4 bg-gray-800/30 rounded-lg text-sm text-gray-400">
          <h3 className="font-medium text-gray-300 mb-2">Password Requirements:</h3>
          <ul className="list-disc pl-5 space-y-1 text-xs">
            <li>At least 8 characters</li>
            <li>Must include uppercase and lowercase letters</li>
            <li>Must include at least one number</li>
            <li>Must include at least one special character</li>
          </ul>
        </div>

        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500">
            This is a one-time security requirement for administrative accounts.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForcePasswordChange;