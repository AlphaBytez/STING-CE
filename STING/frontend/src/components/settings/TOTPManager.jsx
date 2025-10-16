import React, { useState, useEffect } from 'react';
import { Smartphone, Shield, AlertCircle, CheckCircle, X, Info, Loader, QrCode, Copy } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import securityGateService from '../../services/securityGateService';
import { checkKratosSession } from '../../utils/kratosSession';
import axios from 'axios';

const TOTPManager = ({ isEnrollmentMode = false, onSetupComplete = null }) => {
  const { themeColors } = useTheme();
  const { identity, checkSession, refreshSession } = useKratos();
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showInfo, setShowInfo] = useState(false);
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [qrData, setQrData] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [settingsFlow, setSettingsFlow] = useState(null);
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [showRecoveryCodes, setShowRecoveryCodes] = useState(false);

  useEffect(() => {
    checkTOTPStatus();
  }, [identity]);

  const checkTOTPStatus = async () => {
    try {
      setIsLoading(true);
      
      // Create or get settings flow to check TOTP status 
      // FIXED: Use API endpoint for JSON responses, not browser endpoint
      const flowResponse = await fetch('/.ory/self-service/settings/browser', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!flowResponse.ok) {
        throw new Error(`Settings flow failed: ${flowResponse.status}`);
      }
      
      const flow = await flowResponse.json();
      setSettingsFlow(flow);
      
      // Check for TOTP nodes
      const totpNodes = flow.ui.nodes.filter(n => n.group === 'totp');
      const totpSetupNode = totpNodes.find(n => 
        n.attributes?.name === 'totp_qr' || 
        n.attributes?.name === 'totp_secret_key'
      );
      
      // Check if TOTP unlink is available (means TOTP is enabled)
      const totpUnlinkNode = totpNodes.find(n => 
        n.attributes?.name === 'totp_unlink' && 
        n.attributes?.type === 'submit'
      );
      
      setTotpEnabled(!!totpUnlinkNode);
      
    } catch (error) {
      console.error('Error checking TOTP status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startTOTPSetup = async () => {
    setError('');
    setSuccess('');
    setIsSettingUp(true);
    
    try {
      // Get fresh settings flow via Kratos API
      // FIXED: Use API endpoint for JSON responses, not browser endpoint
      const flowResponse = await fetch('/.ory/self-service/settings/browser', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!flowResponse.ok) {
        throw new Error(`Settings flow failed: ${flowResponse.status}`);
      }
      
      const flow = await flowResponse.json();
      setSettingsFlow(flow);
      
      // Find TOTP setup nodes
      const totpNodes = flow.ui.nodes.filter(n => n.group === 'totp');
      
      // Find the QR code data
      const qrNode = totpNodes.find(n => n.attributes?.id === 'totp_qr');
      const secretNode = totpNodes.find(n => n.attributes?.id === 'totp_secret_key');
      
      if (qrNode && qrNode.attributes?.src) {
        setQrData({
          qrImage: qrNode.attributes.src,
          secret: secretNode?.attributes?.text?.text || ''
        });
      } else {
        // Need to trigger TOTP setup first
        const totpCodeNode = totpNodes.find(n => n.attributes?.name === 'totp_code');
        if (totpCodeNode) {
          // TOTP setup is already initiated, just show the form
          setQrData({ needsCode: true });
        } else {
          // Trigger TOTP setup
          await triggerTOTPSetup(flow);
        }
      }
      
    } catch (err) {
      console.error('Error starting TOTP setup:', err);
      setError('Failed to start 2FA setup. Please try again.');
      setIsSettingUp(false);
    }
  };

  const triggerTOTPSetup = async (flow) => {
    try {
      // Find the TOTP setup trigger
      const totpNodes = flow.ui.nodes.filter(n => n.group === 'totp');
      const setupNode = totpNodes.find(n => 
        n.attributes?.name === 'totp_secret_key' && 
        n.type === 'input'
      );
      
      if (!setupNode) {
        // Need to submit the form to trigger TOTP setup
        const csrfToken = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;
        
        const formData = new URLSearchParams();
        formData.append('csrf_token', csrfToken);
        formData.append('method', 'totp');
        
        console.log('🔐 TOTP Setup: Posting to URL:', flow.ui.action);
        console.log('🔐 TOTP Setup: Form data:', Object.fromEntries(formData));
        
        // Use fetch instead of axios to avoid AJAX headers that cause CSRF issues
        const response = await fetch(flow.ui.action, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          credentials: 'include',
          body: formData
        });
        
        // Get the updated flow with QR code
        const updatedFlow = await response.json();
        const qrNode = updatedFlow.ui.nodes.find(n => n.attributes?.id === 'totp_qr');
        const secretNode = updatedFlow.ui.nodes.find(n => n.attributes?.id === 'totp_secret_key');
        
        if (qrNode && qrNode.attributes?.src) {
          setQrData({
            qrImage: qrNode.attributes.src,
            secret: secretNode?.attributes?.text?.text || ''
          });
          setSettingsFlow(updatedFlow);
        }
      }
    } catch (err) {
      console.error('Error triggering TOTP setup:', err);
      throw err;
    }
  };

  const verifyTOTP = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter a 6-digit code from your authenticator app');
      return;
    }
    
    setError('');
    
    try {
      const csrfToken = settingsFlow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;
      
      const formData = new URLSearchParams();
      formData.append('csrf_token', csrfToken);
      formData.append('totp_code', verificationCode);
      formData.append('method', 'totp');
      
      // Use fetch instead of axios to avoid AJAX headers that cause CSRF issues
      const response = await fetch(settingsFlow.ui.action, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: formData
      });
      
      const responseData = response.ok ? await response.json() : null;
      
      if (response.status === 200 || response.status === 303) {
        // Check for recovery codes in the response
        const lookupNodes = responseData?.ui?.nodes?.filter(n => 
          n.group === 'lookup_secret' && 
          n.attributes?.name === 'lookup_secret_codes'
        );
        
        if (lookupNodes && lookupNodes.length > 0) {
          // Extract recovery codes from the response
          const codes = lookupNodes[0].attributes?.value || [];
          if (codes.length > 0) {
            setRecoveryCodes(codes);
            setShowRecoveryCodes(true);
            setSuccess('Two-factor authentication enabled! Please save your recovery codes. You can now set up passkeys below.');
          } else {
            setSuccess('Two-factor authentication enabled successfully! You can now set up passkeys below.');
          }
        } else {
          setSuccess('Two-factor authentication enabled successfully! You can now set up passkeys below.');
        }
        
        setIsSettingUp(false);
        setQrData(null);
        setVerificationCode('');
        
        // CRITICAL: Refresh session data after TOTP setup to prevent logout
        console.log('🔐 TOTP Setup Complete: Refreshing session data to prevent disconnect');
        setTimeout(async () => {
          await checkTOTPStatus();
          
          // Try to refresh authentication context instead of full page reload
          try {
            console.log('🔐 TOTP: Attempting to refresh authentication context');
            
            // Use Kratos provider to refresh session instead of page reload
            if (refreshSession) {
              const refreshSuccess = await refreshSession();
              if (refreshSuccess) {
                console.log('🔐 TOTP: Successfully refreshed session via provider');
              } else {
                console.log('🔐 TOTP: Provider refresh failed, will reload page');
                setTimeout(() => window.location.reload(), 1000);
              }
            } else {
              console.log('🔐 TOTP: Provider refresh not available, will reload page');
              setTimeout(() => window.location.reload(), 1000);
            }
          } catch (error) {
            console.error('🔐 TOTP: Error refreshing session, reloading page:', error);
            window.location.reload();
          }
        }, 1000);
        
        // Call enrollment completion callback if provided
        if (isEnrollmentMode && onSetupComplete) {
          setTimeout(() => {
            onSetupComplete('totp');
          }, 1500);
        }
        
        // Mark TOTP as recently set up for passkey manager
        sessionStorage.setItem('totp_recently_setup', 'true');
        localStorage.setItem('totp_setup_complete', 'true');
        
        // CRITICAL: Refresh session data after successful TOTP setup
        // This prevents logout issues due to AAL level changes
        try {
          console.log('🔐 Refreshing session data after TOTP setup...');
          await checkSession(); // Refresh Kratos session
          
          // CRITICAL: Clear SecurityGateService cache to prevent redirect loops
          console.log('🔐 Clearing SecurityGateService cache after TOTP setup...');
          securityGateService.clearCache(identity?.traits?.email);
          
          // Emit event to trigger AAL status refresh across the app
          window.dispatchEvent(new CustomEvent('aal-status-refresh'));
          
          console.log('✅ Session and AAL status refreshed after TOTP setup');
        } catch (refreshError) {
          console.error('⚠️ Error refreshing session after TOTP setup:', refreshError);
          // Don't fail the setup, just log the error
        }
      } else if (responseData?.ui?.messages) {
        const errorMsg = responseData.ui.messages.find(m => m.type === 'error');
        setError(errorMsg?.text || 'Invalid code. Please try again.');
      } else {
        setError('Failed to verify code. Please try again.');
      }
    } catch (err) {
      console.error('Error verifying TOTP:', err);
      setError('Failed to verify code. Please try again.');
    }
  };

  const disableTOTP = async () => {
    if (!window.confirm('Are you sure you want to disable two-factor authentication?')) {
      return;
    }
    
    setError('');
    setSuccess('');
    
    try {
      const csrfToken = settingsFlow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;
      
      const formData = new URLSearchParams();
      formData.append('csrf_token', csrfToken);
      formData.append('totp_unlink', 'true');
      
      await axios.post(settingsFlow.ui.action, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true
      });
      
      setSuccess('Two-factor authentication disabled');
      setTotpEnabled(false);
      setTimeout(() => {
        checkTOTPStatus();
      }, 1000);
    } catch (err) {
      console.error('Error disabling TOTP:', err);
      setError('Failed to disable 2FA');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Secret key copied to clipboard');
    setTimeout(() => setSuccess(''), 3000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="w-8 h-8 animate-spin text-yellow-400" />
      </div>
    );
  }

  return (
    <div className={`max-w-4xl mx-auto p-6 ${themeColors.mainBg || 'bg-slate-800'}`}>
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Smartphone className="w-8 h-8 text-yellow-400" />
              <div>
                <h1 className="text-2xl font-bold text-white">Two-Factor Authentication</h1>
                <p className="text-gray-400 text-sm mt-1">
                  Secure your account with authenticator app
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowInfo(!showInfo)}
              className="p-2 text-gray-400 hover:text-white transition-colors"
              title="More information"
            >
              <Info className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          {error && (
            <div className="mb-6 p-4 glass-subtle border border-red-500/30 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="text-red-300">{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 glass-subtle border border-green-500/30 rounded-lg flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
              <span className="text-green-300">{success}</span>
            </div>
          )}

          {/* Info Section */}
          {showInfo && (
            <div className="mb-6 p-4 bg-gray-700/50 rounded-lg">
              <h4 className="text-white font-medium mb-2">About Authenticator Apps</h4>
              <p className="text-sm text-gray-300 mb-3">
                Authenticator apps generate time-based one-time passwords (TOTP) that provide an extra layer of security.
              </p>
              <p className="text-sm text-gray-300 mb-2">Compatible apps include:</p>
              <ul className="list-disc list-inside text-sm text-gray-300 ml-4 space-y-1">
                <li>Google Authenticator</li>
                <li>Microsoft Authenticator</li>
                <li>Authy</li>
                <li>1Password</li>
                <li>Bitwarden</li>
              </ul>
            </div>
          )}

          {/* Current Status */}
          <div className="mb-6">
            {totpEnabled ? (
              <div className="p-4 bg-green-900/20 border border-green-700/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-6 h-6 text-green-400" />
                    <div>
                      <p className="text-green-300 font-medium">2FA is enabled</p>
                      <p className="text-green-400/70 text-sm">Your account is protected with two-factor authentication</p>
                    </div>
                  </div>
                  <button
                    onClick={disableTOTP}
                    className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
                  >
                    Disable 2FA
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-6 h-6 text-yellow-400" />
                    <div>
                      <p className="text-yellow-300 font-medium">2FA is not enabled</p>
                      <p className="text-yellow-400/70 text-sm">Enable two-factor authentication for enhanced security</p>
                    </div>
                  </div>
                  <button
                    onClick={startTOTPSetup}
                    disabled={isSettingUp}
                    className="px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isSettingUp ? 'Setting up...' : 'Enable 2FA'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Setup Flow */}
          {isSettingUp && qrData && (
            <div className="mt-6 p-6 bg-blue-900/20 border border-blue-700/50 rounded-lg">
              <h3 className="text-lg font-semibold text-white mb-4">Set up your authenticator app</h3>
              
              {qrData.qrImage && (
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <p className="text-gray-300 mb-3">1. Scan this QR code with your authenticator app:</p>
                    <div className="bg-white p-4 rounded-lg inline-block">
                      <img src={qrData.qrImage} alt="TOTP QR Code" className="w-48 h-48" />
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-gray-300 mb-3">2. Or enter this secret key manually:</p>
                    {qrData.secret && (
                      <div className="flex items-center gap-2 mb-4">
                        <code className="flex-1 p-2 bg-gray-800 rounded text-xs text-gray-300 break-all">
                          {qrData.secret}
                        </code>
                        <button
                          onClick={() => copyToClipboard(qrData.secret)}
                          className="p-2 text-gray-400 hover:text-white transition-colors"
                          title="Copy secret key"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                    
                    <p className="text-gray-300 mb-3">3. Enter the 6-digit code from your app:</p>
                    <div className="space-y-3">
                      <input
                        type="text"
                        value={verificationCode}
                        onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        placeholder="000000"
                        className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-center text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-yellow-400"
                        maxLength="6"
                      />
                      <button
                        onClick={verifyTOTP}
                        disabled={verificationCode.length !== 6}
                        className="w-full px-6 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Verify
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {qrData.needsCode && (
                <div>
                  <p className="text-gray-300 mb-3">Enter the 6-digit code from your authenticator app:</p>
                  <div className="space-y-3 max-w-sm">
                    <input
                      type="text"
                      value={verificationCode}
                      onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-center text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-yellow-400"
                      maxLength="6"
                    />
                    <button
                      onClick={verifyTOTP}
                      disabled={verificationCode.length !== 6}
                      className="w-full px-6 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Verify
                    </button>
                  </div>
                </div>
              )}
              
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => {
                    setIsSettingUp(false);
                    setQrData(null);
                    setVerificationCode('');
                    setError('');
                  }}
                  className="text-gray-400 hover:text-white text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Recovery Codes Display */}
          {showRecoveryCodes && recoveryCodes.length > 0 && (
            <div className="mt-6 p-6 bg-red-900/20 border border-red-700/50 rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Your Recovery Codes</h3>
                <button
                  onClick={() => setShowRecoveryCodes(false)}
                  className="p-1 text-gray-400 hover:text-white"
                  title="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="bg-red-950/30 p-4 rounded-lg border border-red-800/50 mb-4">
                <div className="flex items-start gap-3 mb-3">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-red-300">
                    <p className="font-semibold mb-1">SAVE THESE CODES NOW!</p>
                    <p>Each code can only be used once. Store them in a secure location.</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-2 mb-4">
                {recoveryCodes.map((code, index) => (
                  <div 
                    key={index} 
                    className="p-3 bg-gray-800 border border-gray-600 rounded font-mono text-center text-white"
                  >
                    {code}
                  </div>
                ))}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const codeText = recoveryCodes.join('\n');
                    navigator.clipboard.writeText(codeText);
                    setSuccess('Recovery codes copied to clipboard');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy All Codes
                </button>
                <button
                  onClick={() => {
                    const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(
                      `STING Recovery Codes\n\n${recoveryCodes.join('\n')}\n\nKeep these codes safe! Each can only be used once.`
                    );
                    const downloadAnchorNode = document.createElement('a');
                    downloadAnchorNode.setAttribute("href", dataStr);
                    downloadAnchorNode.setAttribute("download", "sting-recovery-codes.txt");
                    document.body.appendChild(downloadAnchorNode);
                    downloadAnchorNode.click();
                    downloadAnchorNode.remove();
                  }}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  Download as File
                </button>
              </div>
            </div>
          )}

          {/* Important Notice */}
          {totpEnabled && (
            <div className="mt-6 p-4 bg-amber-900/20 border border-amber-700/50 rounded-lg">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-300">
                  <p className="font-semibold mb-1">Important:</p>
                  <p>Two-factor authentication is now enabled. You'll be prompted for a code from your authenticator app during login. If you lose access to your authenticator app, you can use your recovery codes to regain access.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TOTPManager;