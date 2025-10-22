import React, { useState, useEffect } from 'react';
import { Save, X, Plus, Trash2, Code, FileText, Settings, Shield } from 'lucide-react';
import { Select, Checkbox } from 'antd';
import { useNotifications } from '../../context/NotificationContext';
import { useKratos } from '../../auth/KratosProvider';
import api from '../../services/api';

const { Option } = Select;

// JSON editor for template configuration
const JsonEditor = ({ value, onChange, placeholder }) => {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setText(e.target.value);
    try {
      const parsed = JSON.parse(e.target.value);
      onChange(parsed);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="relative">
      <textarea
        value={text}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full h-64 bg-gray-900 text-gray-100 font-mono text-sm p-4 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none resize-y"
        spellCheck={false}
      />
      {error && (
        <div className="absolute bottom-2 right-2 text-xs text-red-400 bg-gray-800 px-2 py-1 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

// Parameter editor component
const ParameterEditor = ({ parameters, onChange }) => {
  const addParameter = () => {
    const newParam = {
      name: `param_${Date.now()}`,
      type: 'string',
      label: 'New Parameter',
      required: false,
      default: '',
      description: ''
    };
    onChange([...parameters, newParam]);
  };

  const updateParameter = (index, field, value) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const removeParameter = (index) => {
    onChange(parameters.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-100">Parameters</h3>
        <button
          onClick={addParameter}
          className="flex items-center space-x-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Add Parameter</span>
        </button>
      </div>

      <div className="space-y-3">
        {parameters.map((param, index) => (
          <div
            key={index}
            className="p-4 bg-gray-800 rounded-lg space-y-3 animate-fade-in-up"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1 grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={param.name}
                  onChange={(e) => updateParameter(index, 'name', e.target.value)}
                  placeholder="Parameter name"
                  className="bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm"
                />
                <Select
                  value={param.type}
                  onChange={(value) => updateParameter(index, 'type', value)}
                  className="min-w-32"
                  size="small"
                  style={{ 
                    backgroundColor: 'rgba(55, 65, 81, 0.8)',
                    borderColor: 'rgba(75, 85, 99, 0.5)',
                    color: '#e2e8f0'
                  }}
                  dropdownStyle={{
                    backgroundColor: 'rgba(55, 65, 81, 0.95)',
                    borderColor: 'rgba(75, 85, 99, 0.5)'
                  }}
                >
                  <Option value="string">String</Option>
                  <Option value="number">Number</Option>
                  <Option value="boolean">Boolean</Option>
                  <Option value="date">Date</Option>
                  <Option value="select">Select</Option>
                  <Option value="multiselect">Multi-select</Option>
                </Select>
              </div>
              <button
                onClick={() => removeParameter(index)}
                className="ml-3 p-2 text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <input
              type="text"
              value={param.label}
              onChange={(e) => updateParameter(index, 'label', e.target.value)}
              placeholder="Display label"
              className="w-full bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm"
            />

            <textarea
              value={param.description}
              onChange={(e) => updateParameter(index, 'description', e.target.value)}
              placeholder="Description (optional)"
              className="w-full bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm resize-none"
              rows={2}
            />

            <div className="flex items-center space-x-4">
              <Checkbox
                checked={param.required}
                onChange={(e) => updateParameter(index, 'required', e.target.checked)}
                className="text-sm text-gray-300"
              >
                Required
              </Checkbox>

              {param.type === 'select' || param.type === 'multiselect' ? (
                <input
                  type="text"
                  value={param.options?.join(', ') || ''}
                  onChange={(e) => updateParameter(index, 'options', e.target.value.split(',').map(o => o.trim()))}
                  placeholder="Options (comma-separated)"
                  className="flex-1 bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm"
                />
              ) : (
                <input
                  type="text"
                  value={param.default || ''}
                  onChange={(e) => updateParameter(index, 'default', e.target.value)}
                  placeholder="Default value"
                  className="flex-1 bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm"
                />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ReportTemplateEditor = ({ template, onSave, onCancel }) => {
  const { showNotification } = useNotifications();
  const { identity } = useKratos();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');

  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    category: 'custom',
    generator_class: '',
    parameters: [],
    template_config: {},
    output_formats: ['pdf', 'csv', 'json'],
    estimated_time_minutes: 5,
    requires_scrambling: true,
    scrambling_profile: 'gdpr_compliant',
    security_level: 'standard',
    required_role: 'user',
    is_active: true,
    ...template
  });

  const handleSubmit = async () => {
    try {
      setLoading(true);

      // Validate required fields
      if (!formData.name || !formData.display_name || !formData.generator_class) {
        showNotification('error', 'Please fill in all required fields');
        return;
      }

      await onSave(formData);
    } catch (error) {
      console.error('Error saving template:', error);
      showNotification('error', 'Failed to save template');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'basic', label: 'Basic Info', icon: FileText },
    { id: 'parameters', label: 'Parameters', icon: Settings },
    { id: 'config', label: 'Configuration', icon: Code },
    { id: 'security', label: 'Security', icon: Shield }
  ];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className="bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden animate-fade-in-scale"
      >
        {/* Header */}
        <div className="bg-gray-800 px-6 py-4 flex justify-between items-center border-b border-gray-700">
          <h2 className="text-xl font-semibold text-gray-100">
            {template ? 'Edit Report Template' : 'Create Report Template'}
          </h2>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-6 py-3 transition-colors ${
                  activeTab === tab.id
                    ? 'bg-gray-800 text-primary-400 border-b-2 border-primary-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {activeTab === 'basic' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Template Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., honey_jar_summary"
                    className="w-full bg-gray-800 text-gray-100 px-4 py-2 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Display Name *
                  </label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    placeholder="e.g., Honey Jar Summary Report"
                    className="w-full bg-gray-800 text-gray-100 px-4 py-2 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this report does..."
                  className="w-full bg-gray-800 text-gray-100 px-4 py-2 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none resize-none"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Category
                  </label>
                  <Select
                    value={formData.category}
                    onChange={(value) => setFormData({ ...formData, category: value })}
                    className="w-full"
                    style={{ 
                      backgroundColor: 'rgba(55, 65, 81, 0.8)',
                      borderColor: 'rgba(75, 85, 99, 0.5)',
                      color: '#e2e8f0'
                    }}
                    dropdownStyle={{
                      backgroundColor: 'rgba(55, 65, 81, 0.95)',
                      borderColor: 'rgba(75, 85, 99, 0.5)'
                    }}
                  >
                    <Option value="analytics">Analytics</Option>
                    <Option value="security">Security</Option>
                    <Option value="compliance">Compliance</Option>
                    <Option value="custom">Custom</Option>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Generator Class *
                  </label>
                  <input
                    type="text"
                    value={formData.generator_class}
                    onChange={(e) => setFormData({ ...formData, generator_class: e.target.value })}
                    placeholder="e.g., HoneyJarSummaryGenerator"
                    className="w-full bg-gray-800 text-gray-100 px-4 py-2 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Est. Time (minutes)
                  </label>
                  <input
                    type="number"
                    value={formData.estimated_time_minutes}
                    onChange={(e) => setFormData({ ...formData, estimated_time_minutes: parseInt(e.target.value) || 5 })}
                    min={1}
                    className="w-full bg-gray-800 text-gray-100 px-4 py-2 rounded-lg border border-gray-700 focus:border-primary-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Output Formats
                </label>
                <div className="flex space-x-4">
                  {['pdf', 'csv', 'json', 'xlsx', 'html'].map((format) => (
                    <Checkbox
                      key={format}
                      checked={formData.output_formats.includes(format)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({
                            ...formData,
                            output_formats: [...formData.output_formats, format]
                          });
                        } else {
                          setFormData({
                            ...formData,
                            output_formats: formData.output_formats.filter(f => f !== format)
                          });
                        }
                      }}
                      className="text-gray-300"
                    >
                      <span className="text-gray-300 text-sm uppercase">{format}</span>
                    </Checkbox>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'parameters' && (
            <ParameterEditor
              parameters={formData.parameters}
              onChange={(parameters) => setFormData({ ...formData, parameters })}
            />
          )}

          {activeTab === 'config' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-100 mb-3">Template Configuration</h3>
                <p className="text-sm text-gray-400 mb-4">
                  Define additional configuration for your report generator (e.g., queries, filters, etc.)
                </p>
                <JsonEditor
                  value={formData.template_config}
                  onChange={(template_config) => setFormData({ ...formData, template_config })}
                  placeholder="Enter JSON configuration..."
                />
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Required Role
                  </label>
                  <Select
                    value={formData.required_role}
                    onChange={(value) => setFormData({ ...formData, required_role: value })}
                    className="w-full"
                    style={{ 
                      backgroundColor: 'rgba(55, 65, 81, 0.8)',
                      borderColor: 'rgba(75, 85, 99, 0.5)',
                      color: '#e2e8f0'
                    }}
                    dropdownStyle={{
                      backgroundColor: 'rgba(55, 65, 81, 0.95)',
                      borderColor: 'rgba(75, 85, 99, 0.5)'
                    }}
                  >
                    <Option value="user">User</Option>
                    <Option value="analyst">Analyst</Option>
                    <Option value="admin">Admin</Option>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Security Level
                  </label>
                  <Select
                    value={formData.security_level}
                    onChange={(value) => setFormData({ ...formData, security_level: value })}
                    className="w-full"
                    style={{ 
                      backgroundColor: 'rgba(55, 65, 81, 0.8)',
                      borderColor: 'rgba(75, 85, 99, 0.5)',
                      color: '#e2e8f0'
                    }}
                    dropdownStyle={{
                      backgroundColor: 'rgba(55, 65, 81, 0.95)',
                      borderColor: 'rgba(75, 85, 99, 0.5)'
                    }}
                  >
                    <Option value="standard">Standard</Option>
                    <Option value="high">High</Option>
                    <Option value="critical">Critical</Option>
                  </Select>
                </div>
              </div>

              <div>
                <Checkbox
                  checked={formData.requires_scrambling}
                  onChange={(e) => setFormData({ ...formData, requires_scrambling: e.target.checked })}
                  className="text-gray-300"
                >
                  Require PII Scrambling
                </Checkbox>
              </div>

              {formData.requires_scrambling && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Scrambling Profile
                  </label>
                  <Select
                    value={formData.scrambling_profile}
                    onChange={(value) => setFormData({ ...formData, scrambling_profile: value })}
                    className="w-full"
                    style={{ 
                      backgroundColor: 'rgba(55, 65, 81, 0.8)',
                      borderColor: 'rgba(75, 85, 99, 0.5)',
                      color: '#e2e8f0'
                    }}
                    dropdownStyle={{
                      backgroundColor: 'rgba(55, 65, 81, 0.95)',
                      borderColor: 'rgba(75, 85, 99, 0.5)'
                    }}
                  >
                    <Option value="gdpr_compliant">GDPR Compliant</Option>
                    <Option value="hipaa_compliant">HIPAA Compliant</Option>
                    <Option value="full_anonymization">Full Anonymization</Option>
                  </Select>
                </div>
              )}

              <div>
                <Checkbox
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="text-gray-300"
                >
                  Template is Active
                </Checkbox>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-800 px-6 py-4 flex justify-end space-x-3 border-t border-gray-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center space-x-2 px-6 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving...' : 'Save Template'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportTemplateEditor;