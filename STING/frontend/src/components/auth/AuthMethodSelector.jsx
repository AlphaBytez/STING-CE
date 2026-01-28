/**
 * Authentication Method Selector Component
 * 
 * Provides intelligent authentication method selection with:
 * - Industry-standard preference hierarchy (Passkey > TOTP > Recovery)
 * - Contextual recommendations based on user situation
 * - Graceful fallback handling
 * - User preference learning and storage
 */

import React, { useState, useEffect } from 'react';
import authMethodPreferenceService from '../../services/authMethodPreferenceService';

const AuthMethodSelector = ({ 
  availableMethods = {},
  user = null,
  onMethodSelected,
  showAsButtons = false,
  className = ""
}) => {
  const [recommendation, setRecommendation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAllOptions, setShowAllOptions] = useState(false);

  useEffect(() => {
    async function loadRecommendation() {
      try {
        setIsLoading(true);
        
        const result = await authMethodPreferenceService.getPreferredMethod(
          user,
          availableMethods,
          {} // Will be fetched internally
        );
        
        setRecommendation(result);
        setShowAllOptions(result.shouldPromptUserChoice);
        
      } catch (error) {
        console.error('Failed to get auth method recommendation:', error);
        
        // Fallback recommendation
        setRecommendation({
          primary: availableMethods.passkey ? 'passkey' : 'totp',
          fallback: 'recovery_codes',
          reasoning: { primary: 'fallback', fallback: 'fallback' },
          contextualMessage: 'Choose your authentication method'
        });
        
      } finally {
        setIsLoading(false);
      }
    }

    if (Object.keys(availableMethods).length > 0) {
      loadRecommendation();
    }
  }, [availableMethods, user]);

  const handleMethodSelection = (method) => {
    // Save user preference
    authMethodPreferenceService.setUserPreference(method, {
      availableMethods,
      selectedAt: Date.now()
    });
    
    // Hide options after selection
    setShowAllOptions(false);
    
    // Notify parent component
    if (onMethodSelected) {
      onMethodSelected(method);
    }
  };

  const getMethodIcon = (method) => {
    const icons = {
      passkey: '🔐',
      totp: '📱',
      recovery_codes: '🔑'
    };
    return icons[method] || '🔒';
  };

  const getMethodLabel = (method) => {
    const labels = {
      passkey: 'Passkey',
      totp: 'Authenticator App',
      recovery_codes: 'Recovery Code'
    };
    return labels[method] || method;
  };

  const getMethodDescription = (method, reasoning) => {
    const descriptions = {
      passkey: {
        most_secure_frictionless: 'Most secure and convenient option',
        enhanced_security: 'Best security for sensitive operations',
        mobile_optimized: 'Optimized for mobile devices',
        user_preference: 'Your preferred method',
        default: 'Secure biometric authentication'
      },
      totp: {
        reliable_cross_device: 'Works reliably across all devices',
        reliable_during_updates: 'Most reliable during service updates',
        user_preference: 'Your preferred method',
        default: 'Time-based authentication codes'
      },
      recovery_codes: {
        emergency_access: 'For emergency access only',
        default: 'Single-use backup codes'
      }
    };
    
    const methodDescriptions = descriptions[method] || {};
    return methodDescriptions[reasoning] || methodDescriptions.default || '';
  };

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <div className="flex items-center gap-2 text-gray-400">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading authentication options...</span>
        </div>
      </div>
    );
  }

  if (!recommendation) {
    return (
      <div className={`p-4 text-center text-gray-400 ${className}`}>
        No authentication methods available
      </div>
    );
  }

  // Get UI configuration
  const methodUI = authMethodPreferenceService.getMethodSelectionUI(
    availableMethods,
    recommendation
  );

  // Single method display (when user has preference or only one option)
  if (!showAllOptions && recommendation.primary) {
    const primaryMethod = methodUI.options.find(opt => opt.method === recommendation.primary);
    
    if (!primaryMethod) {
      return (
        <div className={`p-4 text-center text-gray-400 ${className}`}>
          Recommended method not available
        </div>
      );
    }

    return (
      <div className={`${className}`}>
        {/* Contextual message */}
        {recommendation.contextualMessage && (
          <div className="mb-3 text-sm text-gray-300 text-center">
            {recommendation.contextualMessage}
          </div>
        )}

        {/* Primary method button */}
        <div
          onClick={() => handleMethodSelection(recommendation.primary)}
          className="w-full p-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 border border-blue-500/30 rounded-xl cursor-pointer transition-all duration-200 transform hover:scale-[1.02]"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{primaryMethod.icon}</span>
            <div className="flex-1">
              <div className="font-semibold text-white">{primaryMethod.label}</div>
              <div className="text-sm text-blue-100">
                {getMethodDescription(recommendation.primary, recommendation.reasoning.primary)}
              </div>
            </div>
            <svg className="w-5 h-5 text-blue-200" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {/* Show other options link */}
        {methodUI.options.length > 1 && (
          <div className="mt-3 text-center">
            <button
              onClick={() => setShowAllOptions(true)}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Use a different method
            </button>
          </div>
        )}
      </div>
    );
  }

  // Multiple methods display (choice interface)
  return (
    <div className={`${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white mb-2">
          Choose Authentication Method
        </h3>
        <p className="text-sm text-gray-300">
          You have multiple authentication methods available. Choose your preferred option:
        </p>
      </div>

      <div className="space-y-3">
        {methodUI.options.map((option) => (
          <div
            key={option.method}
            onClick={() => handleMethodSelection(option.method)}
            className={`p-4 border rounded-xl cursor-pointer transition-all duration-200 transform hover:scale-[1.01] ${
              option.isPrimary
                ? 'bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-blue-500/50 hover:border-blue-400'
                : 'bg-gray-800/50 border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{option.icon}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">{option.label}</span>
                  {option.isPrimary && (
                    <span className="px-2 py-1 text-xs bg-blue-500/30 text-blue-300 rounded-full">
                      Recommended
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  {getMethodDescription(
                    option.method,
                    option.isPrimary ? recommendation.reasoning.primary : 'default'
                  )}
                </div>
              </div>
              <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          </div>
        ))}
      </div>

      {/* Context information */}
      {recommendation.reasoning.primary === 'reliable_during_updates' && (
        <div className="mt-4 p-3 bg-yellow-900/30 border border-yellow-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-yellow-300">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">Service Update Mode</span>
          </div>
          <p className="text-sm text-yellow-200/80 mt-1">
            TOTP is recommended during service updates for maximum reliability.
          </p>
        </div>
      )}
    </div>
  );
};

export default AuthMethodSelector;