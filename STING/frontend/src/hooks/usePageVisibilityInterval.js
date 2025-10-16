import { useEffect, useRef } from 'react';

/**
 * GPU-Optimized Interval Hook
 * Only runs intervals when page is visible, dramatically reducing GPU usage
 */
export const usePageVisibilityInterval = (callback, delay, dependencies = []) => {
  const intervalRef = useRef();
  const callbackRef = useRef(callback);

  // Update callback ref when it changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const tick = () => callbackRef.current();

    const startInterval = () => {
      if (intervalRef.current) return; // Already running
      intervalRef.current = setInterval(tick, delay);
    };

    const stopInterval = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        console.log('🔋 Page hidden - pausing interval to save GPU');
        stopInterval();
      } else {
        console.log('👁️ Page visible - resuming interval');
        startInterval();
        tick(); // Run immediately when page becomes visible
      }
    };

    // Start interval if page is visible
    if (!document.hidden) {
      startInterval();
    }

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopInterval();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [delay, ...dependencies]);

  // Manual control functions
  const pause = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const resume = () => {
    if (!intervalRef.current && !document.hidden) {
      intervalRef.current = setInterval(() => callbackRef.current(), delay);
    }
  };

  return { pause, resume };
};

/**
 * Aggressive GPU Optimization Hook
 * For when you really need to save GPU (increases intervals when page not focused)
 */
export const useAggressiveInterval = (callback, normalDelay, hiddenDelay = normalDelay * 4) => {
  const intervalRef = useRef();
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const tick = () => callbackRef.current();

    const setCurrentInterval = (delay) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      intervalRef.current = setInterval(tick, delay);
    };

    const handleVisibilityChange = () => {
      const delay = document.hidden ? hiddenDelay : normalDelay;
      console.log(`🔋 Switching interval to ${delay}ms (page ${document.hidden ? 'hidden' : 'visible'})`);
      setCurrentInterval(delay);
    };

    // Start with appropriate delay
    setCurrentInterval(document.hidden ? hiddenDelay : normalDelay);

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [normalDelay, hiddenDelay]);
};