import React, { useState, useEffect, useCallback } from 'react';
import { Wrench, Clock, RefreshCw, AlertCircle } from 'lucide-react';

/**
 * MaintenancePage - Full page shown when system is in maintenance mode
 * 
 * Users are redirected here when:
 * - API returns 503 with MAINTENANCE_MODE code
 * - Direct navigation to /maintenance
 * - MaintenanceGate detects active maintenance
 * 
 * @param {Object} initialData - Optional initial maintenance data passed from MaintenanceGate
 */
const MaintenancePage = ({ initialData = null }) => {
  const [status, setStatus] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [countdown, setCountdown] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/system/maintenance/status');
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        
        // If maintenance is over, redirect to home
        if (!data.maintenance_mode) {
          window.location.href = '/';
          return;
        }
        
        // Calculate countdown if end_time exists
        if (data.end_time) {
          // Parse ISO date string natively
          const endDate = new Date(data.end_time);
          const now = new Date();
          const diffMs = endDate - now;
          
          if (diffMs > 0) {
            const hours = Math.floor(diffMs / (1000 * 60 * 60));
            const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
            
            setCountdown({ hours, minutes, seconds, endDate });
          } else {
            setCountdown(null);
          }
        }
      }
    } catch (err) {
      console.error('Failed to check maintenance status:', err);
    } finally {
      setLoading(false);
      setCheckingStatus(false);
    }
  }, []);

  // Initial fetch (skip if we already have data)
  useEffect(() => {
    if (!initialData) {
      fetchStatus();
    }
  }, [fetchStatus, initialData]);

  // Update countdown every second
  useEffect(() => {
    if (!countdown?.endDate) return;

    const timer = setInterval(() => {
      const now = new Date();
      const diffMs = countdown.endDate - now;

      if (diffMs <= 0) {
        // Maintenance should be over, check status
        fetchStatus();
        return;
      }

      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);

      setCountdown(prev => ({
        ...prev,
        hours,
        minutes,
        seconds
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, [countdown?.endDate, fetchStatus]);

  // Periodic status check (every 30 seconds)
  useEffect(() => {
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleCheckStatus = () => {
    setCheckingStatus(true);
    fetchStatus();
  };

  const formatTime = (num) => String(num).padStart(2, '0');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Main Card */}
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-8 text-center">
          {/* Icon */}
          <div className="mb-6 inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-orange-500/20 to-amber-500/20 border border-orange-500/30">
            <Wrench className="w-10 h-10 text-orange-400" />
          </div>

          {/* Title */}
          <h1 className="text-3xl font-bold text-white mb-2">
            System Maintenance
          </h1>

          {/* Message */}
          <p className="text-gray-400 mb-6">
            {status?.message || 'We\'re performing scheduled maintenance to improve your experience.'}
          </p>

          {/* Countdown Timer */}
          {countdown && (
            <div className="mb-6">
              <p className="text-sm text-gray-500 mb-3">Estimated time remaining:</p>
              <div className="flex items-center justify-center gap-2">
                <div className="bg-gray-900/50 rounded-xl px-4 py-3 min-w-[70px]">
                  <span className="text-3xl font-mono font-bold text-orange-400">
                    {formatTime(countdown.hours)}
                  </span>
                  <p className="text-xs text-gray-500 mt-1">Hours</p>
                </div>
                <span className="text-2xl text-gray-600">:</span>
                <div className="bg-gray-900/50 rounded-xl px-4 py-3 min-w-[70px]">
                  <span className="text-3xl font-mono font-bold text-orange-400">
                    {formatTime(countdown.minutes)}
                  </span>
                  <p className="text-xs text-gray-500 mt-1">Minutes</p>
                </div>
                <span className="text-2xl text-gray-600">:</span>
                <div className="bg-gray-900/50 rounded-xl px-4 py-3 min-w-[70px]">
                  <span className="text-3xl font-mono font-bold text-orange-400">
                    {formatTime(countdown.seconds)}
                  </span>
                  <p className="text-xs text-gray-500 mt-1">Seconds</p>
                </div>
              </div>
            </div>
          )}

          {/* No end time - just a message */}
          {!countdown && status?.maintenance_mode && (
            <div className="mb-6 flex items-center justify-center gap-2 text-gray-500">
              <Clock className="w-5 h-5" />
              <span>We'll be back as soon as possible</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleCheckStatus}
              disabled={checkingStatus}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-orange-600 hover:bg-orange-500 disabled:bg-orange-600/50 text-white rounded-xl font-medium transition-colors"
            >
              {checkingStatus ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <RefreshCw className="w-5 h-5" />
                  Check Status
                </>
              )}
            </button>
          </div>
        </div>

        {/* Additional Info */}
        <div className="mt-6 text-center">
          <div className="inline-flex items-center gap-2 text-gray-500 text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>Page auto-refreshes every 30 seconds</span>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-600 text-sm">
          <p>
            Need help? Contact your administrator
          </p>
        </div>
      </div>
    </div>
  );
};

export default MaintenancePage;
