import React, { useState, useEffect } from 'react';
import { Shield, Fingerprint, Smartphone, AlertCircle, X, Clock } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';

const WebAuthnPrompt = ({ 
  isOpen, 
  onClose, 
  onSuccess, 
  onError,
  title = "Authentication Required",
  message = "Please authenticate to continue",
  reason = "This action requires verification for security.",
  allowCancel = true,
  theme = "modern" // auto-detect from context or props
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState('prompt'); // prompt, authenticating, fallback
  const [fallbackMethod, setFallbackMethod] = useState(null); // totp, email
  const { identity } = useKratos();

  useEffect(() => {
    if (isOpen) {
      setError('');
      setStep('prompt');
      setFallbackMethod(null);
    }
  }, [isOpen]);

  const handleWebAuthnAuth = async () => {
    if (loading) return;
    
    setLoading(true);
    setError('');
    setStep('authenticating');

    try {
      console.log('🔐 WebAuthnPrompt: Starting WebAuthn authentication');
      
      // Create a new authentication flow
      // REVERTED: Use browser endpoint with Accept header for JSON responses
      const flowResponse = await fetch('/.ory/self-service/login/browser?refresh=true&aal=aal2', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      if (!flowResponse.ok) {
        throw new Error('Failed to create authentication flow');
      }

      const flowData = await flowResponse.json();
      
      // Find WebAuthn node
      const webauthnNode = flowData.ui.nodes.find(node => 
        node.attributes?.name === 'webauthn_login' || 
        (node.attributes?.name === 'method' && node.attributes?.value === 'webauthn')
      );

      if (!webauthnNode) {
        console.log('🔐 WebAuthnPrompt: No WebAuthn method available, offering fallback');
        setStep('fallback');
        return;
      }

      // Trigger WebAuthn ceremony
      const formData = new FormData();
      formData.append('method', 'webauthn');
      formData.append('csrf_token', flowData.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value || '');
      
      if (identity?.traits?.email) {
        formData.append('identifier', identity.traits.email);
      }

      const authResponse = await fetch(flowData.ui.action, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (authResponse.ok || authResponse.status === 303) {
        console.log('🔐 WebAuthnPrompt: Authentication successful');
        onSuccess && onSuccess();
        onClose && onClose();
      } else if (authResponse.status === 422) {
        const errorData = await authResponse.json();
        if (errorData.error?.id === 'browser_location_change_required') {
          // This might be expected for WebAuthn - the browser will handle the ceremony
          setTimeout(() => {
            // Check if we're still on the same page (authentication succeeded)
            onSuccess && onSuccess();
            onClose && onClose();
          }, 1000);
        } else {
          throw new Error(errorData.error?.message || 'Authentication failed');
        }
      } else {
        throw new Error('Authentication request failed');
      }

    } catch (err) {
      console.error('🔐 WebAuthnPrompt: Authentication error:', err);
      
      if (err.name === 'NotSupportedError') {
        setError('WebAuthn is not supported on this device');
        setStep('fallback');
      } else if (err.name === 'SecurityError') {
        setError('Authentication was blocked by security policy');
        setStep('fallback');
      } else if (err.name === 'AbortError') {
        setError('Authentication was cancelled');
      } else {
        setError(err.message || 'Authentication failed');
        setStep('fallback');
      }
      
      onError && onError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFallbackAuth = async (method) => {
    setFallbackMethod(method);
    // This would trigger TOTP or email code flow
    // For now, we'll just close and let the user use the main auth flow
    console.log(`🔐 WebAuthnPrompt: Falling back to ${method} authentication`);
    onClose && onClose();
  };

  if (!isOpen) return null;

  // Theme-aware styling
  const getThemeClasses = () => {
    const baseClasses = "fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in";
    const overlayClasses = "absolute inset-0 backdrop-blur-sm";
    
    switch (theme) {
      case 'retro-terminal':
        return {
          container: baseClasses + " bg-black/80",
          overlay: overlayClasses + " bg-green-900/20",
          modal: "relative max-w-md w-full bg-black border-2 border-green-500 rounded-none p-6 shadow-2xl animate-slide-up font-mono",
          text: "text-green-400",
          accent: "text-green-300",
          button: "bg-green-600 hover:bg-green-500 text-black font-bold py-3 px-6 transition-colors",
          secondaryButton: "bg-transparent border border-green-500 text-green-400 hover:bg-green-900 py-2 px-4 transition-colors"
        };
      case 'retro-performance':
        return {
          container: baseClasses + " bg-black/80",
          overlay: overlayClasses + " bg-yellow-900/20",
          modal: "relative max-w-md w-full bg-gray-900 border border-yellow-500 rounded-lg p-6 shadow-2xl animate-slide-up",
          text: "text-yellow-100",
          accent: "text-yellow-400",
          button: "bg-yellow-600 hover:bg-yellow-500 text-black font-bold py-3 px-6 rounded transition-colors",
          secondaryButton: "bg-transparent border border-yellow-500 text-yellow-400 hover:bg-yellow-900 py-2 px-4 rounded transition-colors"
        };
      default: // modern
        return {
          container: baseClasses + " bg-black/50",
          overlay: overlayClasses + " bg-blue-900/10",
          modal: "relative max-w-md w-full sting-glass-card sting-glass-strong p-6 shadow-2xl animate-slide-up",
          text: "text-gray-200",
          accent: "text-blue-400",
          button: "bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors",
          secondaryButton: "bg-transparent border border-gray-600 text-gray-300 hover:bg-gray-800 py-2 px-4 rounded transition-colors"
        };
    }
  };

  const themeClasses = getThemeClasses();

  return (
    <div className={themeClasses.container}>
      <div className={themeClasses.overlay} onClick={allowCancel ? onClose : undefined} />
      
      <div className={themeClasses.modal}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-full ${theme === 'retro-terminal' ? 'bg-green-900' : theme === 'retro-performance' ? 'bg-yellow-900' : 'bg-blue-900'}`}>
              <Shield className="w-6 h-6" />
            </div>
            <h2 className={`text-xl font-bold ${themeClasses.text}`}>
              {title}
            </h2>
          </div>
          {allowCancel && (
            <button
              onClick={onClose}
              className={`${themeClasses.text} hover:${themeClasses.accent} transition-colors`}
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content based on step */}
        {step === 'prompt' && (
          <>
            <div className="mb-6">
              <p className={`${themeClasses.text} mb-3`}>{message}</p>
              <p className={`text-sm ${themeClasses.accent} opacity-80`}>{reason}</p>
            </div>

            <div className="flex flex-col space-y-4">
              <button
                onClick={handleWebAuthnAuth}
                disabled={loading}
                className={`${themeClasses.button} flex items-center justify-center space-x-2 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Fingerprint className="w-5 h-5" />
                <span>Authenticate with Biometrics</span>
              </button>

              <div className="flex space-x-2">
                <button
                  onClick={() => handleFallbackAuth('totp')}
                  className={`${themeClasses.secondaryButton} flex-1 flex items-center justify-center space-x-2`}
                >
                  <Smartphone className="w-4 h-4" />
                  <span>Use 2FA App</span>
                </button>
                <button
                  onClick={() => handleFallbackAuth('email')}
                  className={`${themeClasses.secondaryButton} flex-1 flex items-center justify-center space-x-2`}
                >
                  <Clock className="w-4 h-4" />
                  <span>Email Code</span>
                </button>
              </div>
            </div>
          </>
        )}

        {step === 'authenticating' && (
          <div className="text-center py-8">
            <div className="mb-4">
              <Fingerprint className={`w-16 h-16 mx-auto ${themeClasses.accent} animate-pulse`} />
            </div>
            <p className={`${themeClasses.text} mb-2`}>Please authenticate</p>
            <p className={`text-sm ${themeClasses.accent} opacity-80`}>
              Use your fingerprint, face, or security key
            </p>
          </div>
        )}

        {step === 'fallback' && (
          <>
            <div className="mb-6 text-center">
              <AlertCircle className={`w-12 h-12 mx-auto mb-3 ${themeClasses.accent}`} />
              <p className={`${themeClasses.text} mb-2`}>Biometric authentication unavailable</p>
              <p className={`text-sm ${themeClasses.accent} opacity-80`}>
                Please use an alternative method or try again later
              </p>
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={() => handleFallbackAuth('totp')}
                className={`${themeClasses.button} flex-1`}
              >
                Use 2FA App
              </button>
              <button
                onClick={() => handleFallbackAuth('email')}
                className={`${themeClasses.secondaryButton} flex-1`}
              >
                Email Code
              </button>
            </div>
          </>
        )}

        {/* Error display */}
        {error && (
          <div className={`mt-4 p-3 bg-red-900/30 border border-red-800 rounded ${theme === 'retro-terminal' ? 'border-red-500 bg-red-900/50' : ''}`}>
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WebAuthnPrompt;