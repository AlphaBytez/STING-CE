import React, { useState, useEffect, useCallback } from 'react';
import { Wrench, Clock, X, AlertTriangle } from 'lucide-react';

// Native date formatting helpers (no external dependencies)
const formatDate = (date) => {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const d = new Date(date);
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
};

const formatDistanceToNow = (date) => {
  const now = new Date();
  const target = new Date(date);
  const diffMs = target - now;
  const diffMins = Math.round(diffMs / 60000);
  
  if (diffMins < 0) return 'ended';
  if (diffMins < 60) return `in ${diffMins} minute${diffMins !== 1 ? 's' : ''}`;
  const diffHours = Math.round(diffMins / 60);
  if (diffHours < 24) return `in ${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
  const diffDays = Math.round(diffHours / 24);
  return `in ${diffDays} day${diffDays !== 1 ? 's' : ''}`;
};

/**
 * MaintenanceBanner - Shows maintenance status to all users
 * 
 * Features:
 * - Shows upcoming scheduled maintenance warnings
 * - Shows active maintenance status with estimated end time
 * - Dismissable (remembers in session)
 * - Auto-refreshes status
 */
const MaintenanceBanner = ({ className = '' }) => {
  const [maintenanceStatus, setMaintenanceStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchMaintenanceStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/maintenance/status', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setMaintenanceStatus(data);
      }
    } catch (err) {
      // Silently fail - don't disrupt user experience
      console.debug('Maintenance status check failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMaintenanceStatus();
    
    // Poll every 60 seconds
    const interval = setInterval(fetchMaintenanceStatus, 60000);
    return () => clearInterval(interval);
  }, [fetchMaintenanceStatus]);

  // Check if dismissed in this session
  useEffect(() => {
    const dismissedKey = sessionStorage.getItem('maintenance_banner_dismissed');
    if (dismissedKey) {
      setDismissed(true);
    }
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem('maintenance_banner_dismissed', 'true');
  };

  // Don't show anything if loading, dismissed, or no maintenance
  if (loading || dismissed || !maintenanceStatus?.maintenance_mode) {
    return null;
  }

  const { message, estimated_end, status } = maintenanceStatus;

  const formatEndTimeInfo = (isoString) => {
    if (!isoString) return null;
    try {
      const endDate = new Date(isoString);
      return {
        formatted: formatDate(endDate),
        relative: formatDistanceToNow(endDate)
      };
    } catch {
      return null;
    }
  };

  const endTimeInfo = formatEndTimeInfo(estimated_end);

  return (
    <div className={`bg-gradient-to-r from-orange-600 to-amber-600 text-white px-4 py-3 ${className}`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="flex-shrink-0 p-1.5 bg-white/20 rounded-lg">
            <Wrench className="w-5 h-5" />
          </div>
          
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold">System Maintenance</span>
              {endTimeInfo && (
                <span className="flex items-center gap-1 text-sm text-orange-100">
                  <Clock className="w-4 h-4" />
                  Estimated end: {endTimeInfo.relative}
                </span>
              )}
            </div>
            <p className="text-sm text-orange-100 truncate">
              {message}
            </p>
          </div>
        </div>
        
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1.5 hover:bg-white/20 rounded-lg transition-colors"
          title="Dismiss"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

/**
 * ScheduledMaintenanceWarning - Shows upcoming maintenance warning
 * Shows 24 hours before scheduled maintenance
 */
export const ScheduledMaintenanceWarning = ({ className = '' }) => {
  const [scheduledMaintenance, setScheduledMaintenance] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const fetchScheduled = async () => {
      try {
        const response = await fetch('/api/admin/maintenance/status', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          // Check if there's scheduled maintenance in the next 24 hours
          if (data.scheduled_start) {
            const startDate = new Date(data.scheduled_start);
            const now = new Date();
            const hoursUntil = (startDate - now) / (1000 * 60 * 60);
            
            if (hoursUntil > 0 && hoursUntil <= 24) {
              setScheduledMaintenance({
                start: data.scheduled_start,
                end: data.scheduled_end,
                message: data.scheduled_message
              });
            }
          }
        }
      } catch (err) {
        console.debug('Scheduled maintenance check failed:', err);
      }
    };

    fetchScheduled();
    const interval = setInterval(fetchScheduled, 5 * 60 * 1000); // Every 5 minutes
    return () => clearInterval(interval);
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem('scheduled_maintenance_dismissed', scheduledMaintenance?.start || 'true');
  };

  if (dismissed || !scheduledMaintenance) {
    return null;
  }

  const startTime = formatDate(new Date(scheduledMaintenance.start));
  const timeUntil = formatDistanceToNow(new Date(scheduledMaintenance.start));

  return (
    <div className={`bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-4 py-3 ${className}`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <div>
            <span className="font-semibold">Scheduled Maintenance</span>
            <p className="text-sm text-blue-100">
              System maintenance scheduled {timeUntil} ({startTime}).
              {scheduledMaintenance.message && ` ${scheduledMaintenance.message}`}
            </p>
          </div>
        </div>
        
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1.5 hover:bg-white/20 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default MaintenanceBanner;
