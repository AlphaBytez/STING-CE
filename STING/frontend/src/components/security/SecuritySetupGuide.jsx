import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Shield, Key, Smartphone, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

/**
 * SecuritySetupGuide - Provides guided security method setup with clear messaging
 * 
 * Triggered by the security gate when users need to set up authentication methods
 */
const SecuritySetupGuide = ({ securityStatus }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);
  
  // Get security status from route state (passed by UnifiedProtectedRoute)
  const routeSecurityStatus = location.state?.securityStatus;
  const isRequired = location.state?.isRequired;
  const fromRoute = location.state?.from;
  
  // Use provided status or route status
  const status = securityStatus || routeSecurityStatus;
  
  useEffect(() => {
    if (status) {
      console.log('🛡️ SecuritySetupGuide loaded with status:', status);
      console.log('🛡️ SecuritySetupGuide currentMethods:', status.currentMethods);
      console.log('🛡️ SecuritySetupGuide requiredMethods:', status.requiredMethods);
    }
  }, [status]);

  if (!status || status.meetsRequirements || dismissed) {
    return null;
  }

  const handleDismiss = () => {
    if (status.allowDismiss) {
      setDismissed(true);
      // Navigate back to intended destination if available
      if (fromRoute?.pathname) {
        navigate(fromRoute.pathname);
      }
    }
  };

  const getMethodIcon = (method) => {
    switch (method) {
      case 'passkey': return <Key className="w-5 h-5" />;
      case 'totp': return <Smartphone className="w-5 h-5" />;
      case 'hardware key': return <Key className="w-5 h-5" />;
      default: return <Shield className="w-5 h-5" />;
    }
  };

  const getMethodName = (method) => {
    switch (method) {
      case 'passkey': return 'Passkey (Face ID/Touch ID)';
      case 'totp': return 'Authenticator App (TOTP)';
      case 'hardware key': return 'Hardware Key (YubiKey)';
      default: return method;
    }
  };

  const getUrgencyStyles = (urgency) => {
    switch (urgency) {
      case 'high':
        return {
          border: 'border-red-500',
          bg: 'bg-red-950',
          text: 'text-red-100',
          icon: 'text-red-400'
        };
      case 'medium':
        return {
          border: 'border-yellow-500',
          bg: 'bg-yellow-950',
          text: 'text-yellow-100',
          icon: 'text-yellow-400'
        };
      default:
        return {
          border: 'border-blue-500',
          bg: 'bg-blue-950',
          text: 'text-blue-100',
          icon: 'text-blue-400'
        };
    }
  };

  const styles = getUrgencyStyles(status.urgency);

  return (
    <div className={`${styles.border} ${styles.bg} border-2 rounded-lg p-6 mb-6`}>
      <div className="flex items-start space-x-4">
        {/* Icon based on urgency */}
        <div className={`${styles.icon} flex-shrink-0 mt-1`}>
          {status.urgency === 'high' ? (
            <AlertTriangle className="w-6 h-6" />
          ) : (
            <Shield className="w-6 h-6" />
          )}
        </div>

        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <h3 className={`text-lg font-semibold ${styles.text}`}>
              {status.actionText || 'Security Setup Required'}
            </h3>
            {!isRequired && status.allowDismiss && (
              <button
                onClick={handleDismiss}
                className="text-gray-400 hover:text-gray-300 text-sm"
              >
                Dismiss
              </button>
            )}
          </div>

          {/* Message */}
          <p className={`${styles.text} mb-4`}>
            {status.message}
          </p>

          {/* Current Methods Status */}
          {status.currentMethods && (
            <div className="mb-4">
              <h4 className={`text-sm font-medium ${styles.text} mb-2`}>Current Security Methods:</h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(status.currentMethods).map(([method, enabled]) => (
                  <div
                    key={method}
                    className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs ${
                      enabled
                        ? 'bg-green-900 text-green-200 border border-green-700'
                        : 'bg-gray-800 text-gray-400 border border-gray-600'
                    }`}
                  >
                    {getMethodIcon(method)}
                    <span>{getMethodName(method)}</span>
                    {enabled ? (
                      <CheckCircle className="w-3 h-3 text-green-400" />
                    ) : (
                      <Clock className="w-3 h-3 text-gray-500" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Required Methods */}
          {status.requiredMethods && status.requiredMethods.length > 0 && (
            <div className="mb-4">
              <h4 className={`text-sm font-medium ${styles.text} mb-2`}>Required to set up:</h4>
              <div className="flex flex-wrap gap-2">
                {status.requiredMethods.map((method) => (
                  <div
                    key={method}
                    className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs bg-orange-900 text-orange-200 border border-orange-700"
                  >
                    {getMethodIcon(method)}
                    <span>{getMethodName(method)}</span>
                    <AlertTriangle className="w-3 h-3 text-orange-400" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Methods */}
          {status.recommendedMethods && status.recommendedMethods.length > 0 && (
            <div className="mb-4">
              <h4 className={`text-sm font-medium ${styles.text} mb-2`}>Recommended for backup:</h4>
              <div className="flex flex-wrap gap-2">
                {status.recommendedMethods.map((method) => (
                  <div
                    key={method}
                    className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs bg-blue-900 text-blue-200 border border-blue-700"
                  >
                    {getMethodIcon(method)}
                    <span>{getMethodName(method)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Grace Period */}
          {status.gracePeriod && (
            <div className={`text-sm ${styles.text} opacity-75`}>
              <Clock className="w-4 h-4 inline mr-1" />
              Setup grace period: {status.gracePeriod} days
            </div>
          )}

          {/* Hardware Key Recommendation */}
          {status.suggestions?.backup && (
            <div className="mt-4 p-3 bg-purple-950 border border-purple-700 rounded-lg">
              <h4 className="text-sm font-medium text-purple-200 mb-2">💡 Backup Method Options:</h4>
              <div className="space-y-2 text-xs text-purple-300">
                <div className="flex items-center space-x-2">
                  <Key className="w-4 h-4 text-purple-400" />
                  <span><strong>Hardware Key (Recommended):</strong> YubiKey, Google Titan, or built-in security keys</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Smartphone className="w-4 h-4 text-purple-400" />
                  <span><strong>TOTP App:</strong> Google Authenticator, Authy, or 1Password</span>
                </div>
              </div>
            </div>
          )}

          {/* Benefits Display */}
          {status.suggestions?.benefits && (
            <div className="mt-4 p-3 bg-green-950 border border-green-700 rounded-lg">
              <h4 className="text-sm font-medium text-green-200 mb-2">🚀 Why 3-Factor Security?</h4>
              <ul className="space-y-1 text-xs text-green-300">
                {status.suggestions.benefits.map((benefit, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-green-400 mt-0.5">•</span>
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3 mt-4">
            {(status.requiredMethods?.includes('passkey') || status.currentMethods?.passkey === false) && (
              <button
                onClick={() => document.getElementById('passkey-setup-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-sm font-medium transition-colors"
              >
                Set Up Passkey
              </button>
            )}
            
            {(status.requiredMethods?.some(m => m.includes('totp')) || status.currentMethods?.totp === false) && (
              <button
                onClick={() => document.getElementById('totp-setup-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 text-sm font-medium transition-colors"
              >
                Set Up Backup Method
              </button>
            )}

            {fromRoute?.pathname && fromRoute.pathname !== '/dashboard/settings/security' && (
              <button
                onClick={() => navigate(fromRoute.pathname)}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 text-sm font-medium transition-colors"
                disabled={!status.allowDismiss}
              >
                {status.allowDismiss ? 'Continue to Dashboard' : 'Setup Required'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecuritySetupGuide;