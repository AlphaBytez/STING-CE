import React, { useState, useEffect } from 'react';
import {
  Settings,
  Shield,
  Clock,
  Database,
  AlertTriangle,
  CheckCircle,
  Save,
  RefreshCw,
  Plus,
  Trash2,
  Edit,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Bell
} from 'lucide-react';

/**
 * Enhanced PII Settings Framework Component
 * Provides comprehensive configuration for PII compliance profiles including:
 * - Sensitivity levels and thresholds
 * - Automated actions and workflows
 * - Data retention policies
 * - Notification preferences
 * - Custom rule templates
 */
const PIISettingsFramework = ({ profileId, onSave, onClose }) => {
  const [settings, setSettings] = useState({
    profile: {
      id: profileId,
      name: '',
      description: '',
      active: true,
      priority: 'medium'
    },
    sensitivity: {
      detection_threshold: 0.75,
      confidence_threshold: 0.85,
      pattern_matching_mode: 'strict', // strict, balanced, permissive
      context_analysis_enabled: true,
      false_positive_reduction: true,
      minimum_match_length: 3
    },
    actions: {
      immediate_actions: {
        quarantine_data: true,
        notify_admin: true,
        block_processing: false,
        create_audit_log: true
      },
      automated_workflows: {
        data_classification: true,
        encryption_trigger: true,
        access_restriction: false,
        compliance_tagging: true
      },
      escalation_rules: {
        high_risk_escalation: true,
        multiple_detections_escalation: true,
        escalation_threshold: 5,
        escalation_timeframe: 3600 // seconds
      }
    },
    retention: {
      data_retention_enabled: true,
      retention_period_days: 2555, // 7 years default
      automatic_deletion: false,
      archive_before_deletion: true,
      retention_exceptions: [],
      purge_logs_after_days: 365,
      compliance_hold_enabled: false
    },
    notifications: {
      email_alerts: {
        enabled: true,
        recipients: [],
        alert_frequency: 'immediate', // immediate, hourly, daily, weekly
        include_context: false,
        severity_threshold: 'medium'
      },
      dashboard_alerts: {
        enabled: true,
        show_statistics: true,
        show_trends: true,
        alert_persistence_days: 30
      },
      audit_notifications: {
        enabled: true,
        include_remediation_actions: true,
        notify_on_pattern_updates: true
      }
    },
    advanced: {
      machine_learning_enhancement: false,
      pattern_learning_enabled: false,
      contextual_analysis_depth: 'medium', // shallow, medium, deep
      cross_document_correlation: false,
      api_integration_enabled: false,
      custom_preprocessing_rules: [],
      performance_optimization: 'balanced' // speed, balanced, accuracy
    }
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [isDirty, setIsDirty] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [testResults, setTestResults] = useState(null);

  useEffect(() => {
    if (profileId) {
      loadSettings();
    }
  }, [profileId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/pii/profile/${profileId}/settings`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setSettings(prev => ({ ...prev, ...data.settings }));
      }
    } catch (error) {
      console.error('Error loading PII settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSettingChange = (path, value) => {
    const pathArray = path.split('.');
    setSettings(prev => {
      const newSettings = { ...prev };
      let current = newSettings;
      
      for (let i = 0; i < pathArray.length - 1; i++) {
        current[pathArray[i]] = { ...current[pathArray[i]] };
        current = current[pathArray[i]];
      }
      
      current[pathArray[pathArray.length - 1]] = value;
      return newSettings;
    });
    
    setIsDirty(true);
  };

  const validateSettings = () => {
    const newErrors = {};
    
    // Profile validation
    if (!settings.profile.name.trim()) {
      newErrors['profile.name'] = 'Profile name is required';
    }
    
    // Sensitivity validation
    if (settings.sensitivity.detection_threshold < 0.1 || settings.sensitivity.detection_threshold > 1.0) {
      newErrors['sensitivity.detection_threshold'] = 'Threshold must be between 0.1 and 1.0';
    }
    
    // Retention validation
    if (settings.retention.retention_period_days < 1) {
      newErrors['retention.retention_period_days'] = 'Retention period must be at least 1 day';
    }
    
    // Notifications validation
    if (settings.notifications.email_alerts.enabled && settings.notifications.email_alerts.recipients.length === 0) {
      newErrors['notifications.email_alerts.recipients'] = 'At least one recipient required when email alerts are enabled';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateSettings()) {
      return;
    }
    
    try {
      setLoading(true);
      
      const response = await fetch(`/api/pii/profile/${profileId}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        setIsDirty(false);
        onSave && onSave(settings);
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving PII settings:', error);
      alert('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  const testConfiguration = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`/api/pii/profile/${profileId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        const results = await response.json();
        setTestResults(results);
      }
    } catch (error) {
      console.error('Error testing configuration:', error);
    } finally {
      setLoading(false);
    }
  };

  const SettingGroup = ({ title, description, children, icon: Icon }) => (
    <div className="dashboard-card p-4 mb-4">
      <div className="flex items-center space-x-3 mb-4">
        {Icon && (
          <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
            <Icon className="w-5 h-5" />
          </div>
        )}
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {description && <p className="text-gray-400 text-sm">{description}</p>}
        </div>
      </div>
      <div className="space-y-4">
        {children}
      </div>
    </div>
  );

  const ToggleSwitch = ({ label, description, checked, onChange, disabled = false }) => (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <label className="text-white font-medium">{label}</label>
        {description && <p className="text-gray-400 text-sm mt-1">{description}</p>}
      </div>
      <button
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-amber-500' : 'bg-gray-600'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );

  const SliderInput = ({ label, value, onChange, min = 0, max = 1, step = 0.1, suffix = '' }) => (
    <div>
      <div className="flex justify-between mb-2">
        <label className="text-white font-medium">{label}</label>
        <span className="text-gray-400">{value}{suffix}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-amber"
      />
    </div>
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">PII Configuration Settings</h1>
          <p className="text-gray-400">Configure advanced PII detection and compliance settings</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={testConfiguration}
            disabled={loading}
            className="px-4 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Test Config</span>
          </button>
          <button
            onClick={handleSave}
            disabled={loading || !isDirty}
            className="px-4 py-2 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded-lg transition-colors flex items-center space-x-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>Save Changes</span>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 rounded-lg transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Profile Settings */}
      <SettingGroup title="Profile Configuration" description="Basic profile information and priority" icon={Settings}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-white font-medium mb-2">Profile Name</label>
            <input
              type="text"
              value={settings.profile.name}
              onChange={(e) => handleSettingChange('profile.name', e.target.value)}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400"
              placeholder="e.g., HIPAA Compliance Profile"
            />
            {errors['profile.name'] && (
              <p className="text-red-400 text-sm mt-1">{errors['profile.name']}</p>
            )}
          </div>
          <div>
            <label className="block text-white font-medium mb-2">Priority Level</label>
            <select
              value={settings.profile.priority}
              onChange={(e) => handleSettingChange('profile.priority', e.target.value)}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
        
        <div>
          <label className="block text-white font-medium mb-2">Description</label>
          <textarea
            value={settings.profile.description}
            onChange={(e) => handleSettingChange('profile.description', e.target.value)}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400"
            rows={3}
            placeholder="Describe the purpose and scope of this compliance profile..."
          />
        </div>

        <ToggleSwitch
          label="Active Profile"
          description="Enable this profile for PII detection"
          checked={settings.profile.active}
          onChange={(value) => handleSettingChange('profile.active', value)}
        />
      </SettingGroup>

      {/* Sensitivity Settings */}
      <SettingGroup title="Detection Sensitivity" description="Configure pattern matching thresholds and accuracy" icon={Shield}>
        <SliderInput
          label="Detection Threshold"
          value={settings.sensitivity.detection_threshold}
          onChange={(value) => handleSettingChange('sensitivity.detection_threshold', value)}
          min={0.1}
          max={1.0}
          step={0.05}
        />
        
        <SliderInput
          label="Confidence Threshold"
          value={settings.sensitivity.confidence_threshold}
          onChange={(value) => handleSettingChange('sensitivity.confidence_threshold', value)}
          min={0.1}
          max={1.0}
          step={0.05}
        />

        <div>
          <label className="block text-white font-medium mb-2">Pattern Matching Mode</label>
          <select
            value={settings.sensitivity.pattern_matching_mode}
            onChange={(e) => handleSettingChange('sensitivity.pattern_matching_mode', e.target.value)}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
          >
            <option value="strict">Strict - Highest accuracy, fewer matches</option>
            <option value="balanced">Balanced - Good balance of accuracy and coverage</option>
            <option value="permissive">Permissive - More matches, higher false positive risk</option>
          </select>
        </div>

        <ToggleSwitch
          label="Context Analysis"
          description="Analyze surrounding text for better accuracy"
          checked={settings.sensitivity.context_analysis_enabled}
          onChange={(value) => handleSettingChange('sensitivity.context_analysis_enabled', value)}
        />

        <ToggleSwitch
          label="False Positive Reduction"
          description="Use ML techniques to reduce false positives"
          checked={settings.sensitivity.false_positive_reduction}
          onChange={(value) => handleSettingChange('sensitivity.false_positive_reduction', value)}
        />
      </SettingGroup>

      {/* Action Settings */}
      <SettingGroup title="Automated Actions" description="Define what happens when PII is detected" icon={AlertTriangle}>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h4 className="text-white font-medium mb-3">Immediate Actions</h4>
            <div className="space-y-3">
              <ToggleSwitch
                label="Quarantine Data"
                description="Isolate detected PII data"
                checked={settings.actions.immediate_actions.quarantine_data}
                onChange={(value) => handleSettingChange('actions.immediate_actions.quarantine_data', value)}
              />
              <ToggleSwitch
                label="Notify Administrator"
                description="Send immediate alert to admin"
                checked={settings.actions.immediate_actions.notify_admin}
                onChange={(value) => handleSettingChange('actions.immediate_actions.notify_admin', value)}
              />
              <ToggleSwitch
                label="Block Processing"
                description="Stop further processing of data"
                checked={settings.actions.immediate_actions.block_processing}
                onChange={(value) => handleSettingChange('actions.immediate_actions.block_processing', value)}
              />
              <ToggleSwitch
                label="Create Audit Log"
                description="Log detection event for compliance"
                checked={settings.actions.immediate_actions.create_audit_log}
                onChange={(value) => handleSettingChange('actions.immediate_actions.create_audit_log', value)}
              />
            </div>
          </div>

          <div>
            <h4 className="text-white font-medium mb-3">Automated Workflows</h4>
            <div className="space-y-3">
              <ToggleSwitch
                label="Data Classification"
                description="Automatically classify detected data"
                checked={settings.actions.automated_workflows.data_classification}
                onChange={(value) => handleSettingChange('actions.automated_workflows.data_classification', value)}
              />
              <ToggleSwitch
                label="Encryption Trigger"
                description="Automatically encrypt sensitive data"
                checked={settings.actions.automated_workflows.encryption_trigger}
                onChange={(value) => handleSettingChange('actions.automated_workflows.encryption_trigger', value)}
              />
              <ToggleSwitch
                label="Access Restriction"
                description="Restrict access to detected PII"
                checked={settings.actions.automated_workflows.access_restriction}
                onChange={(value) => handleSettingChange('actions.automated_workflows.access_restriction', value)}
              />
              <ToggleSwitch
                label="Compliance Tagging"
                description="Tag data with compliance metadata"
                checked={settings.actions.automated_workflows.compliance_tagging}
                onChange={(value) => handleSettingChange('actions.automated_workflows.compliance_tagging', value)}
              />
            </div>
          </div>
        </div>

        <div className="border-t border-gray-700 pt-4 mt-4">
          <h4 className="text-white font-medium mb-3">Escalation Rules</h4>
          <div className="grid grid-cols-3 gap-4">
            <ToggleSwitch
              label="High Risk Escalation"
              description="Escalate high-risk detections"
              checked={settings.actions.escalation_rules.high_risk_escalation}
              onChange={(value) => handleSettingChange('actions.escalation_rules.high_risk_escalation', value)}
            />
            
            <div>
              <label className="block text-white font-medium mb-2">Escalation Threshold</label>
              <input
                type="number"
                value={settings.actions.escalation_rules.escalation_threshold}
                onChange={(e) => handleSettingChange('actions.escalation_rules.escalation_threshold', parseInt(e.target.value))}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                min={1}
                max={100}
              />
            </div>

            <div>
              <label className="block text-white font-medium mb-2">Timeframe (minutes)</label>
              <input
                type="number"
                value={Math.floor(settings.actions.escalation_rules.escalation_timeframe / 60)}
                onChange={(e) => handleSettingChange('actions.escalation_rules.escalation_timeframe', parseInt(e.target.value) * 60)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                min={1}
                max={1440}
              />
            </div>
          </div>
        </div>
      </SettingGroup>

      {/* Retention Settings */}
      <SettingGroup title="Data Retention Policy" description="Configure how long PII data and logs are retained" icon={Clock}>
        <ToggleSwitch
          label="Enable Data Retention"
          description="Apply retention policies to detected PII data"
          checked={settings.retention.data_retention_enabled}
          onChange={(value) => handleSettingChange('retention.data_retention_enabled', value)}
        />

        {settings.retention.data_retention_enabled && (
          <div className="space-y-4 ml-4 border-l-2 border-gray-700 pl-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-white font-medium mb-2">Retention Period (days)</label>
                <input
                  type="number"
                  value={settings.retention.retention_period_days}
                  onChange={(e) => handleSettingChange('retention.retention_period_days', parseInt(e.target.value))}
                  className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                  min={1}
                  max={36500} // 100 years
                />
                <p className="text-gray-400 text-sm mt-1">
                  Approximately {Math.floor(settings.retention.retention_period_days / 365)} years
                </p>
              </div>

              <div>
                <label className="block text-white font-medium mb-2">Log Retention (days)</label>
                <input
                  type="number"
                  value={settings.retention.purge_logs_after_days}
                  onChange={(e) => handleSettingChange('retention.purge_logs_after_days', parseInt(e.target.value))}
                  className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                  min={1}
                  max={3650} // 10 years
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <ToggleSwitch
                label="Automatic Deletion"
                description="Automatically delete after retention period"
                checked={settings.retention.automatic_deletion}
                onChange={(value) => handleSettingChange('retention.automatic_deletion', value)}
              />

              <ToggleSwitch
                label="Archive Before Deletion"
                description="Archive data before permanent deletion"
                checked={settings.retention.archive_before_deletion}
                onChange={(value) => handleSettingChange('retention.archive_before_deletion', value)}
              />

              <ToggleSwitch
                label="Compliance Hold"
                description="Override retention for legal holds"
                checked={settings.retention.compliance_hold_enabled}
                onChange={(value) => handleSettingChange('retention.compliance_hold_enabled', value)}
              />
            </div>
          </div>
        )}
      </SettingGroup>

      {/* Notification Settings */}
      <SettingGroup title="Notification Preferences" description="Configure how and when you receive PII alerts" icon={Bell}>
        <div className="space-y-6">
          {/* Email Alerts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium">Email Alerts</h4>
              <ToggleSwitch
                label=""
                checked={settings.notifications.email_alerts.enabled}
                onChange={(value) => handleSettingChange('notifications.email_alerts.enabled', value)}
              />
            </div>
            
            {settings.notifications.email_alerts.enabled && (
              <div className="space-y-3 ml-4 border-l-2 border-gray-700 pl-4">
                <div>
                  <label className="block text-white font-medium mb-2">Alert Frequency</label>
                  <select
                    value={settings.notifications.email_alerts.alert_frequency}
                    onChange={(e) => handleSettingChange('notifications.email_alerts.alert_frequency', e.target.value)}
                    className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                  >
                    <option value="immediate">Immediate</option>
                    <option value="hourly">Hourly Summary</option>
                    <option value="daily">Daily Summary</option>
                    <option value="weekly">Weekly Summary</option>
                  </select>
                </div>

                <div>
                  <label className="block text-white font-medium mb-2">Severity Threshold</label>
                  <select
                    value={settings.notifications.email_alerts.severity_threshold}
                    onChange={(e) => handleSettingChange('notifications.email_alerts.severity_threshold', e.target.value)}
                    className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                  >
                    <option value="low">Low and above</option>
                    <option value="medium">Medium and above</option>
                    <option value="high">High and above</option>
                    <option value="critical">Critical only</option>
                  </select>
                </div>

                <ToggleSwitch
                  label="Include Context"
                  description="Include detected text in alerts (security risk)"
                  checked={settings.notifications.email_alerts.include_context}
                  onChange={(value) => handleSettingChange('notifications.email_alerts.include_context', value)}
                />
              </div>
            )}
          </div>

          {/* Dashboard Alerts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium">Dashboard Alerts</h4>
              <ToggleSwitch
                label=""
                checked={settings.notifications.dashboard_alerts.enabled}
                onChange={(value) => handleSettingChange('notifications.dashboard_alerts.enabled', value)}
              />
            </div>
            
            {settings.notifications.dashboard_alerts.enabled && (
              <div className="space-y-3 ml-4 border-l-2 border-gray-700 pl-4">
                <ToggleSwitch
                  label="Show Statistics"
                  description="Display PII detection statistics on dashboard"
                  checked={settings.notifications.dashboard_alerts.show_statistics}
                  onChange={(value) => handleSettingChange('notifications.dashboard_alerts.show_statistics', value)}
                />
                
                <ToggleSwitch
                  label="Show Trends"
                  description="Display detection trend analytics"
                  checked={settings.notifications.dashboard_alerts.show_trends}
                  onChange={(value) => handleSettingChange('notifications.dashboard_alerts.show_trends', value)}
                />

                <div>
                  <label className="block text-white font-medium mb-2">Alert Persistence (days)</label>
                  <input
                    type="number"
                    value={settings.notifications.dashboard_alerts.alert_persistence_days}
                    onChange={(e) => handleSettingChange('notifications.dashboard_alerts.alert_persistence_days', parseInt(e.target.value))}
                    className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
                    min={1}
                    max={365}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </SettingGroup>

      {/* Advanced Settings */}
      <SettingGroup title="Advanced Configuration" description="Advanced features and performance tuning" icon={Database}>
        <div className="space-y-4">
          <ToggleSwitch
            label="Machine Learning Enhancement"
            description="Use ML models to improve detection accuracy (requires additional resources)"
            checked={settings.advanced.machine_learning_enhancement}
            onChange={(value) => handleSettingChange('advanced.machine_learning_enhancement', value)}
          />

          <ToggleSwitch
            label="Pattern Learning"
            description="Learn from detected patterns to improve future detection"
            checked={settings.advanced.pattern_learning_enabled}
            onChange={(value) => handleSettingChange('advanced.pattern_learning_enabled', value)}
          />

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-white font-medium mb-2">Contextual Analysis Depth</label>
              <select
                value={settings.advanced.contextual_analysis_depth}
                onChange={(e) => handleSettingChange('advanced.contextual_analysis_depth', e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="shallow">Shallow - Fast, basic context</option>
                <option value="medium">Medium - Balanced analysis</option>
                <option value="deep">Deep - Comprehensive analysis</option>
              </select>
            </div>

            <div>
              <label className="block text-white font-medium mb-2">Performance Optimization</label>
              <select
                value={settings.advanced.performance_optimization}
                onChange={(e) => handleSettingChange('advanced.performance_optimization', e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="speed">Speed - Fastest processing</option>
                <option value="balanced">Balanced - Good speed and accuracy</option>
                <option value="accuracy">Accuracy - Most accurate, slower</option>
              </select>
            </div>

            <div className="flex items-center space-x-4">
              <ToggleSwitch
                label="Cross-Document Correlation"
                description="Analyze patterns across multiple documents"
                checked={settings.advanced.cross_document_correlation}
                onChange={(value) => handleSettingChange('advanced.cross_document_correlation', value)}
              />
            </div>
          </div>
        </div>
      </SettingGroup>

      {/* Test Results */}
      {testResults && (
        <div className="dashboard-card p-4 mb-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span>Configuration Test Results</span>
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-400">Performance Score:</span>
              <div className="text-2xl font-bold text-green-400">{testResults.performance_score}%</div>
            </div>
            <div>
              <span className="text-gray-400">Accuracy Estimate:</span>
              <div className="text-2xl font-bold text-blue-400">{testResults.accuracy_estimate}%</div>
            </div>
            <div>
              <span className="text-gray-400">Resource Usage:</span>
              <div className="text-lg text-yellow-400">{testResults.resource_usage}</div>
            </div>
            <div>
              <span className="text-gray-400">Compliance Status:</span>
              <div className="text-lg text-green-400">{testResults.compliance_status}</div>
            </div>
          </div>
          
          {testResults.recommendations && testResults.recommendations.length > 0 && (
            <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded">
              <h4 className="text-blue-400 font-medium mb-2">Recommendations:</h4>
              <ul className="text-blue-300 text-sm space-y-1">
                {testResults.recommendations.map((rec, index) => (
                  <li key={index}>• {rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PIISettingsFramework;