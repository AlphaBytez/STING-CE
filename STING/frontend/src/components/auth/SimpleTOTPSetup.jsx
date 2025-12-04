/**
 * SimpleTOTPSetup - Reliable TOTP setup using backend API
 * Eliminates Kratos flow management issues by using server-side proxy
 */

import React, { useState, useEffect } from 'react';
import { Smartphone, Shield, AlertCircle } from 'lucide-react';
import axios from 'axios';
import QRCode from 'qrcode';

const SimpleTOTPSetup = ({ onSetupComplete, onCancel }) => {
  const [step, setStep] = useState('init'); // init, qr, verify, complete
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [qrCodeDataURL, setQrCodeDataURL] = useState('');
  const [verificationCode, setVerificationCode] = useState('');

  /**
   * Initialize TOTP setup using backend API
   */
  const initializeTOTP = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      console.log('🔐 Initializing TOTP setup via backend API...');
      
      const response = await axios.post('/api/totp-enrollment/setup/begin', {}, {
        withCredentials: true,
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.data.success) {
        const { totp_secret } = response.data;
        setTotpSecret(totp_secret);
        
        // Generate QR code
        const totpUrl = `otpauth://totp/Hive:${getUserEmail()}?secret=${totp_secret}&issuer=Hive`;
        const qrDataUrl = await QRCode.toDataURL(totpUrl);
        setQrCodeDataURL(qrDataUrl);
        
        setStep('qr');
        console.log('✅ TOTP setup initialized successfully');
      } else {
        setError('Failed to initialize TOTP setup');
      }
    } catch (error) {
      console.error('❌ TOTP setup initialization failed:', error);
      setError('Failed to initialize TOTP setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Verify TOTP code using backend API
   */
  const verifyTOTP = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      console.log('🔐 Verifying TOTP code via backend API...');
      
      // CRITICAL FIX: Call AAL2 verification endpoint, not enrollment endpoint
      // This ensures verify_aal2_challenge() is called and Redis AAL2 verification is stored
      const response = await axios.post('/api/totp/verify-totp', {
        totp_code: verificationCode
      }, {
        withCredentials: true,
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.data.success) {
        console.log('✅ TOTP verification successful');
        setStep('complete');
        
        // Call completion callback
        if (onSetupComplete) {
          setTimeout(() => {
            onSetupComplete('totp', { 
              hasTOTP: true, 
              method: 'backend-api',
              verified: true 
            });
          }, 1000);
        }
      } else {
        setError(response.data.error || 'Invalid verification code');
      }
    } catch (error) {
      console.error('❌ TOTP verification failed:', error);
      if (error.response?.status === 400) {
        setError(error.response.data?.error || 'Invalid verification code');
      } else {
        setError('Verification failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to get user email from session storage or other source
  const getUserEmail = () => {
    // This should match however the app stores current user email
    return 'admin@sting.local'; // Placeholder - should get from auth context
  };

  // Auto-initialize on mount
  useEffect(() => {
    initializeTOTP();
  }, []);

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium">Setup Error</p>
            <p className="text-sm opacity-90">{error}</p>
          </div>
        </div>
      )}

      {step === 'init' && (
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-400 mx-auto mb-4"></div>
          <p className="text-gray-400">Initializing TOTP setup...</p>
        </div>
      )}

      {step === 'qr' && (
        <div>
          <div className="text-center mb-6">
            <Smartphone className="w-12 h-12 text-purple-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white">Scan QR Code</h3>
            <p className="text-gray-400 text-sm">
              Use your authenticator app (Google Authenticator, Authy, etc.)
            </p>
          </div>

          <div className="flex flex-col items-center space-y-6">
            <div className="bg-white p-4 rounded-lg">
              {qrCodeDataURL && (
                <img 
                  src={qrCodeDataURL} 
                  alt="TOTP QR Code" 
                  className="w-48 h-48"
                />
              )}
            </div>

            {/* Manual entry option */}
            {totpSecret && (
              <div className="w-full p-3 bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-400 mb-2">Can't scan? Enter manually:</p>
                <code className="text-yellow-300 text-xs break-all">{totpSecret}</code>
              </div>
            )}

            {/* Verification step */}
            <div className="w-full space-y-4">
              <p className="text-white font-medium">Enter the 6-digit code from your app:</p>
              
              <input
                type="text"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 text-center text-2xl tracking-widest"
                placeholder="000000"
                maxLength="6"
                disabled={isLoading}
                autoFocus
              />

              <button
                onClick={verifyTOTP}
                disabled={isLoading || verificationCode.length !== 6}
                className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    <span>Verify & Complete Setup</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'complete' && (
        <div className="text-center">
          <Shield className="w-12 h-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">TOTP Setup Complete!</h3>
          <p className="text-gray-400">Your authenticator app is now configured.</p>
        </div>
      )}
    </div>
  );
};

export default SimpleTOTPSetup;