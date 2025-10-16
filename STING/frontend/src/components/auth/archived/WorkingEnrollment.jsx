import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useKratos } from '../../auth/KratosProviderRefactored';
import '../../theme/sting-glass-theme.css';

const WorkingEnrollment = () => {
  const navigate = useNavigate();
  const { checkSession } = useKratos();
  const [step, setStep] = useState('password'); // 'password' or 'passkey'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  // Handle form input changes
  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  // Handle password form submission
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate passwords match
    if (formData.new_password !== formData.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    // Validate password strength
    if (formData.new_password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      // Call the backend password change endpoint
      const response = await axios.post('/api/auth/change-password', {
        current_password: formData.current_password,
        new_password: formData.new_password
      }, {
        withCredentials: true
      });

      if (response.data.success) {
        // Password changed successfully
        console.log('[WorkingEnrollment] Password changed successfully');
        
        // Move to passkey setup step
        setStep('passkey');
      }
    } catch (err) {
      console.error('Password change error:', err);
      setError(err.response?.data?.error || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeySetup = async () => {
    // Refresh session to get updated identity without force_password_change
    await checkSession();
    
    // Navigate to settings with passkey setup flag
    navigate('/dashboard/settings', { state: { openTab: 'security', setupPasskey: true } });
  };

  const handleSkipPasskey = async () => {
    // Refresh session before navigating
    await checkSession();
    navigate('/dashboard');
  };

  if (step === 'password') {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white">Change Your Password</h2>
            <p className="text-gray-400 mt-2">Please set a new password to continue</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handlePasswordSubmit}>
            <div className="mb-4">
              <label className="block text-gray-300 mb-2">Current Password</label>
              <input
                name="current_password"
                type="password"
                required
                value={formData.current_password}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:border-yellow-400 focus:outline-none transition-colors"
                placeholder="Enter your current password"
              />
            </div>

            <div className="mb-4">
              <label className="block text-gray-300 mb-2">New Password</label>
              <input
                name="new_password"
                type="password"
                required
                value={formData.new_password}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:border-yellow-400 focus:outline-none transition-colors"
                placeholder="Enter your new password"
                minLength="8"
              />
              <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
            </div>

            <div className="mb-6">
              <label className="block text-gray-300 mb-2">Confirm New Password</label>
              <input
                name="confirm_password"
                type="password"
                required
                value={formData.confirm_password}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:border-yellow-400 focus:outline-none transition-colors"
                placeholder="Confirm your new password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 disabled:opacity-50 font-semibold transition-all duration-200 transform hover:scale-105"
            >
              {loading ? 'Changing Password...' : 'Change Password'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (step === 'passkey') {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white">Setup Passkey</h2>
            <p className="text-gray-400 mt-2">Enhance your security with passwordless authentication</p>
          </div>

          <div className="space-y-4">
            <button
              onClick={handlePasskeySetup}
              className="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 font-semibold transition-all duration-200 transform hover:scale-105"
            >
              Setup Passkey Now
            </button>

            <button
              onClick={handleSkipPasskey}
              className="w-full py-2 px-4 text-gray-400 hover:text-gray-300 transition-colors"
            >
              Skip for now
            </button>
          </div>

          <div className="mt-6 text-sm text-gray-400 text-center">
            <p>Passkeys provide a more secure and convenient way to sign in.</p>
            <p className="mt-2">You can always set this up later in your security settings.</p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default WorkingEnrollment;