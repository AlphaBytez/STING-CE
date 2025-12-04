/**
 * IntegratedTOTPSetup - In-app TOTP setup without Kratos UI redirect
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import QRCode from 'qrcode';

const IntegratedTOTPSetup = ({ onComplete, onSetupComplete, onCancel }) => {
  const navigate = useNavigate();
  
  // Setup state
  const [step, setStep] = useState('init'); // init, qr, verify, complete
  const [flowData, setFlowData] = useState(null);
  const [totpSecret, setTotpSecret] = useState(null);
  const [totpURI, setTotpURI] = useState(null);
  const [qrCodeDataURL, setQrCodeDataURL] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  
  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  /**
   * Initialize TOTP setup flow
   */
  const initializeTOTPSetup = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      // REVERTED: Use browser endpoint with Accept header for JSON responses
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      if (flowResponse.data) {
        setFlowData(flowResponse.data);
        console.log('🔐 TOTP setup flow initialized:', flowResponse.data.id);
        
        // Request TOTP setup
        await requestTOTPSetup(flowResponse.data);
      }
    } catch (error) {
      console.error('🔐 Failed to initialize TOTP setup:', error);
      setError('Failed to initialize TOTP setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Request TOTP secret and QR code
   */
  const requestTOTPSetup = async (flow) => {
    try {
      const formData = new URLSearchParams();
      formData.append('method', 'totp');
      
      // Add CSRF token
      const csrfToken = flow.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(
        flow.ui.action,
        formData.toString(),
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      if (response.data?.ui) {
        // Extract TOTP details from response
        const totpNode = response.data.ui.nodes.find(
          n => n.attributes?.id === 'totp_secret_key' || 
               n.meta?.label?.text?.includes('secret')
        );
        
        const uriNode = response.data.ui.nodes.find(
          n => n.attributes?.text?.text?.includes('otpauth://') ||
               n.attributes?.src?.includes('data:image')
        );
        
        if (totpNode || uriNode) {
          // Extract secret
          const secret = totpNode?.attributes?.text?.text || 
                        totpNode?.attributes?.value ||
                        extractSecretFromURI(uriNode?.attributes?.text?.text);
          
          setTotpSecret(secret);
          
          // Extract or generate URI
          const uri = uriNode?.attributes?.text?.text || 
                     generateTOTPURI(secret);
          setTotpURI(uri);
          
          // Generate QR code
          await generateQRCode(uri);
          
          setFlowData(response.data);
          setStep('qr');
        } else {
          // Fallback: Try our backend endpoint
          await fetchTOTPFromBackend();
        }
      }
    } catch (error) {
      console.error('🔐 Failed to request TOTP setup:', error);
      setError('Failed to generate TOTP secret. Please try again.');
    }
  };

  /**
   * Fallback: Fetch TOTP details from backend
   */
  const fetchTOTPFromBackend = async () => {
    try {
      const response = await axios.post('/api/totp/generate', {}, {
        withCredentials: true
      });
      
      if (response.data) {
        setTotpSecret(response.data.secret);
        setTotpURI(response.data.uri);
        await generateQRCode(response.data.uri);
        setStep('qr');
      }
    } catch (error) {
      console.error('🔐 Backend TOTP generation failed:', error);
      setError('Unable to generate TOTP secret. Please contact support.');
    }
  };

  /**
   * Generate TOTP URI if not provided
   */
  const generateTOTPURI = (secret) => {
    const issuer = 'Hive';
    const accountName = flowData?.identity?.traits?.email || 'user';
    return `otpauth://totp/${issuer}:${accountName}?secret=${secret}&issuer=${issuer}`;
  };

  /**
   * Extract secret from URI
   */
  const extractSecretFromURI = (uri) => {
    if (!uri) return null;
    const match = uri.match(/secret=([A-Z2-7]+)/);
    return match ? match[1] : null;
  };

  /**
   * Generate QR code from URI
   */
  const generateQRCode = async (uri) => {
    try {
      const dataURL = await QRCode.toDataURL(uri, {
        width: 256,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#FFFFFF'
        }
      });
      setQrCodeDataURL(dataURL);
    } catch (error) {
      console.error('🔐 Failed to generate QR code:', error);
    }
  };

  /**
   * Verify TOTP code
   */
  const handleVerifyCode = async (e) => {
    e.preventDefault();
    if (!verificationCode || verificationCode.length !== 6) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const formData = new URLSearchParams();
      formData.append('totp_code', verificationCode);
      formData.append('method', 'totp');
      
      // Add CSRF token
      const csrfToken = flowData.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await axios.post(
        flowData.ui.action,
        formData.toString(),
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      if (response.status === 200 || response.data?.state === 'success') {
        // Extract backup codes if provided
        const backupCodesNode = response.data?.ui?.nodes?.find(
          n => n.meta?.label?.id === 'secrets.lookup.codes' ||
               n.attributes?.name === 'lookup_secret_codes'
        );
        
        if (backupCodesNode) {
          const codes = backupCodesNode.attributes?.value?.split(',') || [];
          setBackupCodes(codes);
        }
        
        setStep('complete');
        setSuccessMessage('TOTP authentication has been successfully enabled!');
        
        // If this is part of an enrollment flow (has callback), auto-proceed to next step
        if (onSetupComplete || onComplete) {
          console.log('🔒 TOTP verified successfully, auto-proceeding to next enrollment step...');
          setTimeout(() => {
            handleComplete();
          }, 1500); // Brief delay to show success message
        }
      } else if (response.data?.ui?.messages) {
        const errorMsg = response.data.ui.messages.find(
          m => m.type === 'error'
        )?.text;
        setError(errorMsg || 'Invalid verification code. Please try again.');
      } else {
        setError('Verification failed. Please try again.');
      }
    } catch (error) {
      console.error('🔐 TOTP verification failed:', error);
      setError('Failed to verify TOTP code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Complete setup
   */
  const handleComplete = async () => {
    const completionCallback = onSetupComplete || onComplete;
    
    if (completionCallback) {
      // Check current session AAL before reporting completion
      try {
        const sessionResponse = await fetch('/.ory/sessions/whoami', {
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });
        
        let sessionAAL = 'aal1';
        if (sessionResponse.ok) {
          const session = await sessionResponse.json();
          sessionAAL = session.authenticator_assurance_level || session.aal || 'aal1';
          console.log('🔒 IntegratedTOTPSetup completion - current AAL:', sessionAAL);
        }
        
        completionCallback('totp', { 
          hasTOTP: true, 
          backupCodes, 
          aal: sessionAAL,
          sessionStatus: sessionResponse.ok ? 'valid' : 'invalid'
        });
      } catch (error) {
        console.error('🔒 Error checking session AAL during TOTP completion:', error);
        completionCallback('totp', { hasTOTP: true, backupCodes, aal: 'unknown' });
      }
    } else {
      // Stay in enrollment flow - redirect to continue enrollment
      navigate('/enrollment');
    }
  };

  /**
   * Cancel setup
   */
  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      // Return to enrollment main page on cancel
      navigate('/enrollment');
    }
  };

  // Initialize on mount
  useEffect(() => {
    initializeTOTPSetup();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-2xl border border-white/20">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Set Up Two-Factor Authentication
          </h1>
          <p className="text-gray-300">
            Enhance your account security with TOTP authentication
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-500/20 border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6">
            {successMessage}
          </div>
        )}

        {/* Loading State */}
        {isLoading && step === 'init' && (
          <div className="text-center py-12">
            <div className="text-white text-xl">Initializing TOTP setup...</div>
          </div>
        )}

        {/* QR Code Step */}
        {step === 'qr' && (
          <div className="space-y-6">
            <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Step 1: Scan QR Code
              </h2>
              
              <div className="grid md:grid-cols-2 gap-6">
                {/* QR Code */}
                <div className="flex flex-col items-center">
                  {qrCodeDataURL ? (
                    <img
                      src={qrCodeDataURL}
                      alt="TOTP QR Code"
                      className="bg-white p-4 rounded-lg"
                    />
                  ) : (
                    <div className="bg-white/10 w-64 h-64 rounded-lg flex items-center justify-center">
                      <p className="text-gray-400">Generating QR code...</p>
                    </div>
                  )}
                </div>
                
                {/* Instructions */}
                <div className="text-gray-300 space-y-3">
                  <p>Scan this QR code with your authenticator app:</p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    <li>Google Authenticator</li>
                    <li>Microsoft Authenticator</li>
                    <li>Authy</li>
                    <li>1Password</li>
                    <li>Or any TOTP-compatible app</li>
                  </ul>
                  
                  {/* Manual Entry */}
                  {totpSecret && (
                    <div className="mt-4 p-3 bg-gray-800/50 rounded-lg">
                      <p className="text-xs text-gray-400 mb-1">Can't scan? Enter manually:</p>
                      <code className="text-yellow-300 text-xs break-all">{totpSecret}</code>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-purple-900/20 border border-purple-600/30 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Step 2: Verify Setup
              </h2>
              
              <form onSubmit={handleVerifyCode} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Enter the 6-digit code from your app
                  </label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 text-center text-2xl tracking-widest"
                    placeholder="000000"
                    maxLength="6"
                    required
                    disabled={isLoading}
                    autoFocus
                  />
                </div>
                
                <div className="flex gap-4">
                  <button
                    type="submit"
                    disabled={isLoading || verificationCode.length !== 6}
                    className="flex-1 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
                  >
                    {isLoading ? 'Verifying...' : 'Verify & Enable'}
                  </button>
                  
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="space-y-6">
            <div className="bg-green-900/20 border border-green-600/30 rounded-lg p-6 text-center">
              <div className="text-6xl mb-4">✅</div>
              <h2 className="text-2xl font-bold text-white mb-2">
                TOTP Successfully Enabled!
              </h2>
              <p className="text-gray-300">
                Your account is now protected with two-factor authentication.
              </p>
            </div>

            {/* Backup Codes */}
            {backupCodes.length > 0 && (
              <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-yellow-300 mb-3">
                  ⚠️ Save Your Backup Codes
                </h3>
                <p className="text-gray-300 mb-4">
                  Store these codes in a safe place. Each code can be used once if you lose access to your authenticator app.
                </p>
                <div className="grid grid-cols-2 gap-2 p-4 bg-gray-800/50 rounded-lg">
                  {backupCodes.map((code, index) => (
                    <code key={index} className="text-yellow-300 font-mono">
                      {code}
                    </code>
                  ))}
                </div>
                <button
                  onClick={() => {
                    const codesText = backupCodes.join('\n');
                    navigator.clipboard.writeText(codesText);
                    setSuccessMessage('Backup codes copied to clipboard!');
                  }}
                  className="mt-4 bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-lg text-sm"
                >
                  Copy Backup Codes
                </button>
              </div>
            )}

            <button
              onClick={handleComplete}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              Continue to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntegratedTOTPSetup;