import { useState, useCallback } from 'react';

/**
 * Hook for triggering WebAuthn authentication prompts
 * Perfect for protecting sensitive operations like viewing reports or accessing honey jars
 */
export const useWebAuthnPrompt = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState({});
  const [promise, setPromise] = useState(null);

  const promptForAuth = useCallback((options = {}) => {
    return new Promise((resolve, reject) => {
      setConfig({
        title: options.title || "Authentication Required",
        message: options.message || "Please authenticate to continue",
        reason: options.reason || "This action requires verification for security.",
        allowCancel: options.allowCancel !== false,
        theme: options.theme || "modern"
      });
      
      setPromise({ resolve, reject });
      setIsOpen(true);
    });
  }, []);

  const handleSuccess = useCallback(() => {
    if (promise) {
      promise.resolve(true);
      setPromise(null);
    }
    setIsOpen(false);
  }, [promise]);

  const handleError = useCallback((error) => {
    if (promise) {
      promise.reject(error);
      setPromise(null);
    }
    setIsOpen(false);
  }, [promise]);

  const handleClose = useCallback(() => {
    if (promise) {
      promise.reject(new Error('Authentication cancelled'));
      setPromise(null);
    }
    setIsOpen(false);
  }, [promise]);

  return {
    // State
    isOpen,
    config,
    
    // Actions
    promptForAuth,
    handleSuccess,
    handleError,
    handleClose,
    
    // Convenience methods for common use cases
    protectReportAccess: (reportName) => promptForAuth({
      title: "Report Access Verification",
      message: `Authenticate to view "${reportName}"`,
      reason: "Sensitive reports require additional verification.",
      theme: "modern"
    }),
    
    protectHoneyJarAccess: (honeyJarName) => promptForAuth({
      title: "Honey Jar Access",
      message: `Authenticate to access "${honeyJarName}"`,
      reason: "Protected data requires biometric verification.",
      theme: "modern"
    }),
    
    protectBeeAction: (action) => promptForAuth({
      title: "Bee AI Authorization",
      message: `Authorize Bee to ${action}`,
      reason: "AI actions on sensitive data require your permission.",
      theme: "modern"
    })
  };
};

export default useWebAuthnPrompt;