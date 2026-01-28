import React, { useState, useEffect, useCallback } from 'react';
import {
  Wrench,
  Power,
  PowerOff,
  Clock,
  Calendar,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  History,
  Plus,
  Trash2,
  Edit,
  RefreshCw
} from 'lucide-react';

// Native date formatting helpers (no external dependencies)
const formatDateFull = (date) => {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const d = new Date(date);
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
};

const formatDistanceToNowHelper = (date) => {
  const now = new Date();
  const target = new Date(date);
  const diffMs = now - target;
  const diffMins = Math.abs(Math.round(diffMs / 60000));
  const isPast = diffMs > 0;
  
  let result;
  if (diffMins < 60) {
    result = `${diffMins} minute${diffMins !== 1 ? 's' : ''}`;
  } else {
    const diffHours = Math.round(diffMins / 60);
    if (diffHours < 24) {
      result = `${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
    } else {
      const diffDays = Math.round(diffHours / 24);
      result = `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
    }
  }
  return isPast ? `${result} ago` : `in ${result}`;
};

const MaintenanceManager = () => {
  const [maintenanceState, setMaintenanceState] = useState(null);
  const [scheduledMaintenance, setScheduledMaintenance] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showEnableModal, setShowEnableModal] = useState(false);

  // Form state for enabling maintenance
  const [enableForm, setEnableForm] = useState({
    message: 'System maintenance in progress. Please try again later.',
    duration_minutes: 60,
    allow_admins: true,
    immediate: true
  });

  // Form state for scheduling maintenance
  const [scheduleForm, setScheduleForm] = useState({
    start_time: '',
    end_time: '',
    message: 'Scheduled system maintenance',
    notify_users: true
  });

  const fetchMaintenanceStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/maintenance', {
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to fetch maintenance status');
      
      const data = await response.json();
      setMaintenanceState(data.current_state);
      setScheduledMaintenance(data.scheduled || []);
      setHistory(data.history || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching maintenance status:', err);
      setError('Failed to load maintenance status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMaintenanceStatus();
    
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchMaintenanceStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchMaintenanceStatus]);

  const handleEnableMaintenance = async () => {
    setActionLoading(true);
    try {
      const payload = {
        message: enableForm.message,
        allow_admins: enableForm.allow_admins
      };

      if (!enableForm.immediate) {
        payload.start_time = enableForm.start_time;
      }

      if (enableForm.duration_minutes) {
        payload.duration_minutes = parseInt(enableForm.duration_minutes);
      }

      const response = await fetch('/api/admin/maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to enable maintenance');
      }

      await fetchMaintenanceStatus();
      setShowEnableModal(false);
      setEnableForm({
        message: 'System maintenance in progress. Please try again later.',
        duration_minutes: 60,
        allow_admins: true,
        immediate: true
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisableMaintenance = async () => {
    if (!window.confirm('Are you sure you want to disable maintenance mode?')) {
      return;
    }

    setActionLoading(true);
    try {
      const response = await fetch('/api/admin/maintenance', {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to disable maintenance');
      }

      await fetchMaintenanceStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleScheduleMaintenance = async () => {
    setActionLoading(true);
    try {
      const response = await fetch('/api/admin/maintenance/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(scheduleForm)
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to schedule maintenance');
      }

      await fetchMaintenanceStatus();
      setShowScheduleModal(false);
      setScheduleForm({
        start_time: '',
        end_time: '',
        message: 'Scheduled system maintenance',
        notify_users: true
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelScheduled = async (windowId) => {
    if (!window.confirm('Cancel this scheduled maintenance window?')) {
      return;
    }

    setActionLoading(true);
    try {
      const response = await fetch(`/api/admin/maintenance/schedule/${windowId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to cancel scheduled maintenance');

      await fetchMaintenanceStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      return formatDateFull(isoString);
    } catch {
      return isoString;
    }
  };

  const isMaintenanceActive = maintenanceState?.enabled === true;

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
        <span className="ml-3 text-gray-400">Loading maintenance status...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span className="text-red-300">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Current Status Card */}
      <div className={`rounded-2xl p-6 border ${
        isMaintenanceActive 
          ? 'bg-orange-500/10 border-orange-500/30' 
          : 'bg-green-500/10 border-green-500/30'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {isMaintenanceActive ? (
              <Wrench className="w-8 h-8 text-orange-400" />
            ) : (
              <CheckCircle className="w-8 h-8 text-green-400" />
            )}
            <div>
              <h2 className="text-xl font-semibold text-white">
                System Status
              </h2>
              <p className={isMaintenanceActive ? 'text-orange-300' : 'text-green-300'}>
                {isMaintenanceActive ? 'Maintenance Mode Active' : 'Operational'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={fetchMaintenanceStatus}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
              title="Refresh status"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            
            {isMaintenanceActive ? (
              <button
                onClick={handleDisableMaintenance}
                disabled={actionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {actionLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Power className="w-4 h-4" />
                )}
                End Maintenance
              </button>
            ) : (
              <button
                onClick={() => setShowEnableModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg font-medium transition-colors"
              >
                <PowerOff className="w-4 h-4" />
                Enable Maintenance
              </button>
            )}
          </div>
        </div>

        {/* Active Maintenance Details */}
        {isMaintenanceActive && (
          <div className="mt-4 p-4 bg-black/20 rounded-xl space-y-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-white font-medium">User Message:</p>
                <p className="text-gray-300">{maintenanceState.message}</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Enabled At</span>
                <p className="text-white">{formatDateTime(maintenanceState.enabled_at)}</p>
              </div>
              <div>
                <span className="text-gray-500">Enabled By</span>
                <p className="text-white">{maintenanceState.updated_by || 'Unknown'}</p>
              </div>
              <div>
                <span className="text-gray-500">End Time</span>
                <p className="text-white">
                  {maintenanceState.end_time 
                    ? formatDateTime(maintenanceState.end_time)
                    : 'Manual disable required'}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Admin Bypass</span>
                <p className="text-white">
                  {maintenanceState.allow_admins ? (
                    <span className="text-green-400">Enabled</span>
                  ) : (
                    <span className="text-red-400">Disabled</span>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Scheduled Maintenance */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Calendar className="w-6 h-6 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Scheduled Maintenance</h2>
          </div>
          <button
            onClick={() => setShowScheduleModal(true)}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Schedule
          </button>
        </div>

        {scheduledMaintenance.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No scheduled maintenance windows</p>
        ) : (
          <div className="space-y-3">
            {scheduledMaintenance.map((window) => (
              <div
                key={window.id}
                className="flex items-center justify-between p-4 bg-gray-900/50 rounded-xl border border-gray-700/30"
              >
                <div className="flex items-center gap-4">
                  <Clock className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-white font-medium">{window.message}</p>
                    <p className="text-gray-400 text-sm">
                      {formatDateTime(window.start_time)} - {formatDateTime(window.end_time)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    by {window.scheduled_by}
                  </span>
                  <button
                    onClick={() => handleCancelScheduled(window.id)}
                    className="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Cancel"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* History */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
        <div className="flex items-center gap-3 mb-4">
          <History className="w-6 h-6 text-purple-400" />
          <h2 className="text-lg font-semibold text-white">Maintenance History</h2>
        </div>

        {history.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No maintenance history</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.slice(0, 10).map((event, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-900/30 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {event.type === 'enabled' ? (
                    <PowerOff className="w-4 h-4 text-orange-400" />
                  ) : (
                    <Power className="w-4 h-4 text-green-400" />
                  )}
                  <span className="text-white capitalize">{event.type}</span>
                  <span className="text-gray-500">by {event.user}</span>
                </div>
                <span className="text-gray-500 text-sm">
                  {formatDistanceToNowHelper(event.timestamp)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Enable Maintenance Modal */}
      {showEnableModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center gap-3 mb-6">
              <Wrench className="w-6 h-6 text-orange-400" />
              <h3 className="text-xl font-semibold text-white">Enable Maintenance Mode</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  User Message
                </label>
                <textarea
                  value={enableForm.message}
                  onChange={(e) => setEnableForm({ ...enableForm, message: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                  rows={3}
                  placeholder="Message shown to users..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Duration (minutes)
                </label>
                <input
                  type="number"
                  value={enableForm.duration_minutes}
                  onChange={(e) => setEnableForm({ ...enableForm, duration_minutes: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                  placeholder="Leave empty for manual disable"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty to require manual disable
                </p>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="allow_admins"
                  checked={enableForm.allow_admins}
                  onChange={(e) => setEnableForm({ ...enableForm, allow_admins: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-amber-500 focus:ring-amber-500"
                />
                <label htmlFor="allow_admins" className="text-gray-300">
                  Allow admin bypass
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowEnableModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEnableMaintenance}
                disabled={actionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {actionLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <PowerOff className="w-4 h-4" />
                )}
                Enable Maintenance
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Maintenance Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md border border-gray-700">
            <div className="flex items-center gap-3 mb-6">
              <Calendar className="w-6 h-6 text-blue-400" />
              <h3 className="text-xl font-semibold text-white">Schedule Maintenance</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Start Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduleForm.start_time}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, start_time: new Date(e.target.value).toISOString() })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  End Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduleForm.end_time}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, end_time: new Date(e.target.value).toISOString() })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Message
                </label>
                <textarea
                  value={scheduleForm.message}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, message: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                  rows={2}
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="notify_users"
                  checked={scheduleForm.notify_users}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, notify_users: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-amber-500 focus:ring-amber-500"
                />
                <label htmlFor="notify_users" className="text-gray-300">
                  Notify users in advance
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleScheduleMaintenance}
                disabled={actionLoading || !scheduleForm.start_time || !scheduleForm.end_time}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {actionLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Calendar className="w-4 h-4" />
                )}
                Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MaintenanceManager;
