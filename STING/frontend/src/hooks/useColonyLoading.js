import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Hook for managing Colony loading screen state
 * Provides convenient methods for showing/hiding loading with automatic timeouts
 */
export const useColonyLoading = (defaultMessage = "Connecting to your Colony") => {
  const [isVisible, setIsVisible] = useState(false);
  const [message, setMessage] = useState(defaultMessage);
  const [subMessage, setSubMessage] = useState("Securing access to your workspace...");
  const [showProgress, setShowProgress] = useState(false);
  const [progress, setProgress] = useState(0);

  const timeoutRef = useRef(null);
  const progressIntervalRef = useRef(null);

  // Clear timeouts on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, []);

  const showLoading = useCallback((options = {}) => {
    const {
      message: newMessage = defaultMessage,
      subMessage: newSubMessage = "Securing access to your workspace...",
      timeout = null,
      showProgress: newShowProgress = false,
      simulateProgress = false
    } = options;

    setMessage(newMessage);
    setSubMessage(newSubMessage);
    setShowProgress(newShowProgress);
    setProgress(0);
    setIsVisible(true);

    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Clear any existing progress interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    // Auto-hide after timeout
    if (timeout) {
      timeoutRef.current = setTimeout(() => {
        hideLoading();
      }, timeout);
    }

    // Simulate progress if requested
    if (simulateProgress && newShowProgress) {
      let currentProgress = 0;
      progressIntervalRef.current = setInterval(() => {
        currentProgress += Math.random() * 15 + 5; // Random progress between 5-20%
        if (currentProgress >= 100) {
          currentProgress = 100;
          clearInterval(progressIntervalRef.current);
          // Auto-hide when progress completes
          setTimeout(() => hideLoading(), 500);
        }
        setProgress(currentProgress);
      }, 200);
    }
  }, [defaultMessage]);

  const hideLoading = useCallback(() => {
    setIsVisible(false);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  }, []);

  const updateMessage = useCallback((newMessage, newSubMessage = null) => {
    setMessage(newMessage);
    if (newSubMessage !== null) {
      setSubMessage(newSubMessage);
    }
  }, []);

  const updateProgress = useCallback((newProgress) => {
    setProgress(Math.min(100, Math.max(0, newProgress)));
  }, []);

  // Preset loading scenarios
  const showAAL2Loading = useCallback(() => {
    showLoading({
      message: "Verifying Colony permissions",
      subMessage: "Additional authentication required...",
      timeout: 10000 // 10 second timeout for AAL2
    });
  }, [showLoading]);

  const showAuthLoading = useCallback(() => {
    showLoading({
      message: "Connecting to your Colony",
      subMessage: "Establishing secure connection...",
      timeout: 8000 // 8 second timeout for auth
    });
  }, [showLoading]);

  const showPageLoading = useCallback(() => {
    showLoading({
      message: "Loading Colony resources",
      subMessage: "Preparing your workspace...",
      showProgress: true,
      simulateProgress: true
    });
  }, [showLoading]);

  const showDataLoading = useCallback((dataType = "data") => {
    showLoading({
      message: "Loading Colony resources",
      subMessage: `Fetching ${dataType}...`,
      timeout: 5000 // 5 second timeout for data loading
    });
  }, [showLoading]);

  return {
    // State
    isVisible,
    message,
    subMessage,
    showProgress,
    progress,

    // Basic controls
    showLoading,
    hideLoading,
    updateMessage,
    updateProgress,

    // Preset scenarios
    showAAL2Loading,
    showAuthLoading,
    showPageLoading,
    showDataLoading
  };
};

export default useColonyLoading;