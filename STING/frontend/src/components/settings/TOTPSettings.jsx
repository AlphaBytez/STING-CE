import React, { useState, useEffect } from 'react';
import { Smartphone, Shield, AlertCircle, CheckCircle, X, Info } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';

const TOTPSettings = () => {
  const { identity } = useKratos();
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showInfo, setShowInfo] = useState(false);

  useEffect(() => {
    checkTOTPStatus();
  }, [identity]);

  const checkTOTPStatus = async () => {
    try {
      if (identity && identity.credentials) {
        // Check if TOTP is configured
        const hasTOTP = identity.credentials.totp && identity.credentials.totp.length > 0;
        setTotpEnabled(hasTOTP);
      }
    } catch (error) {
      console.error('Error checking TOTP status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTOTPSetup = () => {
    // For now, redirect to Kratos UI for TOTP management
    // In production, you would implement the full flow here
    window.open('/kratos/settings?tab=totp', '_blank');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="text-gray-400">Loading TOTP settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Smartphone className="w-6 h-6 text-yellow-400" />
          <div>
            <p className="font-medium text-white">Authenticator App (TOTP)</p>
            <p className="text-sm text-gray-300">
              Use an authenticator app for two-factor authentication
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            title="More information"
          >
            <Info className="w-5 h-5" />
          </button>
          <button
            onClick={handleTOTPSetup}
            className={`px-4 py-2 rounded-lg transition-colors ${
              totpEnabled
                ? 'bg-gray-600 text-white hover:bg-gray-700'
                : 'bg-yellow-500 text-black hover:bg-yellow-600'
            }`}
          >
            {totpEnabled ? 'Manage 2FA' : 'Enable 2FA'}
          </button>
        </div>
      </div>

      {totpEnabled && (
        <div className="flex items-center space-x-2 text-green-400 text-sm">
          <CheckCircle className="w-4 h-4" />
          <span>Two-factor authentication is enabled</span>
        </div>
      )}

      {showInfo && (
        <div className="mt-4 p-4 bg-gray-700 rounded-lg">
          <h4 className="text-white font-medium mb-2">About Authenticator Apps</h4>
          <p className="text-sm text-gray-300 mb-3">
            Authenticator apps generate time-based one-time passwords (TOTP) that provide an extra layer of security for your account.
          </p>
          <p className="text-sm text-gray-300 mb-2">Popular authenticator apps include:</p>
          <ul className="list-disc list-inside text-sm text-gray-300 ml-4 space-y-1">
            <li>Google Authenticator</li>
            <li>Microsoft Authenticator</li>
            <li>Authy</li>
            <li>1Password</li>
            <li>Bitwarden Authenticator</li>
          </ul>
          <p className="text-sm text-gray-400 mt-3">
            Click "Enable 2FA" to set up your authenticator app. You'll be redirected to the security settings page where you can scan a QR code with your chosen app.
          </p>
        </div>
      )}
    </div>
  );
};

export default TOTPSettings;