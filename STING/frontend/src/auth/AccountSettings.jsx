import React, { useState, useEffect } from 'react';
import { useKratos } from './KratosProvider';

/**
 * AccountSettings - Component for managing user account settings
 * 
 * This component integrates with Kratos for core identity management
 * but extends it with application-specific account settings
 */
const AccountSettings = () => {
  const { 
    identity, 
    accountType, 
    updateAccountType, 
    kratosUrl 
  } = useKratos();
  
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateMessage, setUpdateMessage] = useState('');
  const [currentTheme, setCurrentTheme] = useState('modern');
  
  // Detect theme
  useEffect(() => {
    const theme = document.documentElement.getAttribute('data-theme') || 
                 (document.body.className.includes('retro-terminal') ? 'retro-terminal' :
                  document.body.className.includes('retro-performance') ? 'retro-performance' : 'modern');
    setCurrentTheme(theme);
  }, []);

  // Theme-aware styling
  const getThemeClasses = () => {
    switch (currentTheme) {
      case 'retro-terminal':
        return {
          container: "p-6 max-w-lg mx-auto bg-black border-2 border-green-500 rounded-none shadow-lg font-mono",
          title: "text-xl font-bold mb-4 text-green-400",
          subtitle: "text-lg font-semibold mb-2 text-green-300",
          text: "text-green-400",
          textSecondary: "text-green-600",
          card: "bg-gray-900 border border-green-500 p-4 rounded-none mb-4",
          button: {
            primary: "bg-green-600 hover:bg-green-500 text-black font-bold py-2 px-4 rounded-none border border-green-500",
            secondary: "bg-transparent border border-green-500 text-green-400 hover:bg-green-900 py-2 px-4 rounded-none",
            active: "bg-green-500 text-black border border-green-400",
            inactive: "bg-gray-800 border border-green-600 hover:bg-gray-700 text-green-400"
          },
          error: "bg-red-900 bg-opacity-50 border border-red-500 text-red-300",
          success: "bg-green-900 bg-opacity-50 border border-green-500 text-green-300"
        };
      case 'retro-performance':
        return {
          container: "p-6 max-w-lg mx-auto bg-gray-900 border border-yellow-500 rounded-lg shadow-lg",
          title: "text-xl font-bold mb-4 text-yellow-100",
          subtitle: "text-lg font-semibold mb-2 text-yellow-400",
          text: "text-yellow-100",
          textSecondary: "text-yellow-600",
          card: "bg-gray-800 border border-yellow-600 p-4 rounded mb-4",
          button: {
            primary: "bg-yellow-600 hover:bg-yellow-500 text-black font-semibold py-2 px-4 rounded",
            secondary: "bg-transparent border border-yellow-500 text-yellow-400 hover:bg-yellow-900 py-2 px-4 rounded",
            active: "bg-yellow-500 text-black border border-yellow-400",
            inactive: "bg-gray-700 border border-yellow-600 hover:bg-gray-600 text-yellow-100"
          },
          error: "bg-red-900 bg-opacity-30 border border-red-600 text-red-300",
          success: "bg-green-900 bg-opacity-30 border border-green-600 text-green-300"
        };
      default: // modern
        return {
          container: "p-6 max-w-lg mx-auto sting-glass-card sting-glass-strong text-white",
          title: "text-xl font-bold mb-4 text-white",
          subtitle: "text-lg font-semibold mb-2 text-blue-400",
          text: "text-white",
          textSecondary: "text-gray-400",
          card: "bg-gray-800/50 border border-gray-600 p-4 rounded mb-4",
          button: {
            primary: "bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors",
            secondary: "bg-gray-700 hover:bg-gray-600 text-gray-300 py-2 px-4 rounded transition-colors",
            active: "bg-green-700 text-white",
            inactive: "bg-gray-600 hover:bg-gray-500 text-white"
          },
          error: "bg-red-900 bg-opacity-30 text-red-300 border border-red-800",
          success: "bg-green-900 bg-opacity-30 text-green-300 border border-green-800"
        };
    }
  };

  const theme = getThemeClasses();
  
  // Handle account type update
  const handleAccountTypeChange = async (newType) => {
    if (newType === accountType) return;
    
    setIsUpdating(true);
    setUpdateMessage('');
    
    try {
      const success = await updateAccountType(newType);
      if (success) {
        setUpdateMessage(`Account type updated to ${newType}`);
      } else {
        setUpdateMessage('Failed to update account type. Please try again.');
      }
    } catch (err) {
      setUpdateMessage('An error occurred. Please try again later.');
      console.error('Account type update error:', err);
    } finally {
      setIsUpdating(false);
    }
  };
  
  // Handle redirection to Kratos settings flow
  const openKratosSettings = () => {
    const returnTo = encodeURIComponent(window.location.href);
    window.location.href = `${kratosUrl}/self-service/settings/browser?return_to=${returnTo}`;
  };
  
  // If no identity, show error
  if (!identity) {
    return (
      <div className={theme.container}>
        <h2 className={theme.title}>Account Settings</h2>
        <p className="text-red-400">User information not available. Please log in again.</p>
      </div>
    );
  }
  
  return (
    <div className={theme.container}>
      <h2 className={theme.title}>Account Settings</h2>
      
      {/* Identity Information (from Kratos) */}
      <div className="mb-6">
        <h3 className={theme.subtitle}>Identity Information</h3>
        <div className={theme.card}>
          <p className="mb-2"><span className={theme.textSecondary}>Email:</span> <span className={theme.text}>{identity.traits.email}</span></p>
          {identity.traits.name && (
            <p className="mb-2">
              <span className={theme.textSecondary}>Name:</span> 
              <span className={theme.text}> {identity.traits.name.first} {identity.traits.name.last}</span>
            </p>
          )}
          <p className="mb-2">
            <span className={theme.textSecondary}>Verified:</span> 
            <span className={theme.text}> {identity.verifiable_addresses?.some(a => a.verified) ? 'Yes' : 'No'}</span>
          </p>
        </div>
        
        <button
          onClick={openKratosSettings}
          className={theme.button.primary}
        >
          Update Profile & Password
        </button>
      </div>
      
      {/* Account Type (App-specific) */}
      <div className="mb-6">
        <h3 className={theme.subtitle}>Account Type</h3>
        <div className={theme.card}>
          <p className="mb-2">
            <span className={theme.textSecondary}>Current Plan:</span> 
            <span className={`capitalize ml-2 ${theme.text}`}>{accountType || 'Standard'}</span>
          </p>
          
          <div className="mt-4">
            <div className={`mb-2 ${theme.text}`}>Change account type:</div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleAccountTypeChange('standard')}
                disabled={accountType === 'standard' || isUpdating}
                className={`${
                  accountType === 'standard' ? theme.button.active : theme.button.inactive
                } disabled:opacity-50`}
              >
                Standard
              </button>
              
              <button
                onClick={() => handleAccountTypeChange('premium')}
                disabled={accountType === 'premium' || isUpdating}
                className={`${
                  accountType === 'premium' ? theme.button.active : theme.button.secondary
                } disabled:opacity-50`}
              >
                Premium
              </button>
              
              <button
                onClick={() => handleAccountTypeChange('enterprise')}
                disabled={accountType === 'enterprise' || isUpdating}
                className={`${
                  accountType === 'enterprise' ? theme.button.active : 
                  currentTheme === 'retro-terminal' ? 'bg-purple-800 border border-green-600 hover:bg-purple-700 text-green-400 py-2 px-4 rounded-none' :
                  currentTheme === 'retro-performance' ? 'bg-purple-700 border border-yellow-600 hover:bg-purple-600 text-yellow-100 py-2 px-4 rounded' :
                  'bg-purple-600 hover:bg-purple-500 text-white py-2 px-4 rounded transition-colors'
                } disabled:opacity-50`}
              >
                Enterprise
              </button>
            </div>
          </div>
          
          {isUpdating && (
            <div className="mt-4 text-center">
              <div className={`${currentTheme === 'retro-performance' ? '' : 'animate-spin'} inline-block w-6 h-6 border-t-2 border-b-2 ${
                currentTheme === 'retro-terminal' ? 'border-green-400' :
                currentTheme === 'retro-performance' ? 'border-yellow-400' :
                'border-blue-400'
              } rounded-full`}></div>
              <p className={`mt-2 ${theme.text}`}>Updating account type...</p>
            </div>
          )}
          
          {updateMessage && (
            <div className={`mt-4 p-2 rounded ${
              updateMessage.includes('Failed') || updateMessage.includes('error')
                ? theme.error
                : theme.success
            }`}>
              {updateMessage}
            </div>
          )}
        </div>
      </div>
      
      {/* App-specific settings can go here */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2 text-yellow-400">Application Settings</h3>
        <div className="bg-gray-700 p-4 rounded">
          <p className="text-gray-400 italic">
            Add your app-specific settings here (notifications, preferences, etc.)
          </p>
          
          {/* Example checkbox settings */}
          <div className="mt-4">
            <label className="flex items-center space-x-2">
              <input type="checkbox" className="form-checkbox rounded" />
              <span>Enable email notifications</span>
            </label>
          </div>
          
          <div className="mt-2">
            <label className="flex items-center space-x-2">
              <input type="checkbox" className="form-checkbox rounded" />
              <span>Enable dark mode</span>
            </label>
          </div>
        </div>
      </div>
      
      {/* Account Deletion */}
      <div>
        <h3 className="text-lg font-semibold mb-2 text-red-400">Danger Zone</h3>
        <div className="bg-red-900 bg-opacity-30 border border-red-800 p-4 rounded">
          <p className="mb-4">
            Delete your account and all associated data. This action is irreversible.
          </p>
          <button 
            className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded"
            onClick={() => {
              // Open Kratos account deletion flow or your custom implementation
              if (window.confirm('Are you sure you want to delete your account? This cannot be undone.')) {
                // Implement your account deletion logic here
              }
            }}
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
};

export default AccountSettings;