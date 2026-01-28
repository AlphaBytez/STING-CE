import React, { useState, useEffect } from 'react';
import { ChevronDown, Cpu, HardDrive, Info, CheckCircle, AlertCircle, Eye, Lock } from 'lucide-react';

const BeeSettingsReadOnly = () => {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [serviceStatus, setServiceStatus] = useState({
    status: 'unknown',
    message: ''
  });
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({
    model: true,
    performance: false,
    system: false
  });

  // Fetch available models and current configuration (read-only)
  useEffect(() => {
    fetchModels();
    fetchServiceStatus();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/llm/models');
      if (response.ok) {
        const data = await response.json();
        setModels(data.available_models || []);
        setSelectedModel(data.default_model || '');
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchServiceStatus = async () => {
    try {
      const response = await fetch('/api/llm/health');
      if (response.ok) {
        const data = await response.json();
        setServiceStatus({
          status: 'healthy',
          message: `Service is running (${data.loaded_models ? Object.keys(data.loaded_models).length : 0} models loaded)`
        });
      } else {
        setServiceStatus({
          status: 'unhealthy',
          message: 'LLM service is not responding'
        });
      }
    } catch (error) {
      setServiceStatus({
        status: 'error',
        message: 'Unable to connect to LLM service'
      });
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getStatusIcon = () => {
    switch (serviceStatus.status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'unhealthy':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getModelDescription = (model) => {
    const descriptions = {
      'phi3': 'Best balance of quality and speed. Recommended for most users.',
      'deepseek-1.5b': 'Excellent for coding and reasoning tasks with fast responses.',
      'tinyllama': 'Lightweight and fast. Great for simple conversations.',
      'llama3': 'Powerful model for complex analysis and creative tasks.'
    };
    return descriptions[model] || 'AI language model for chat and assistance.';
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"></div>
          <span className="ml-3 text-gray-400">Loading Bee configuration...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Eye className="w-8 h-8 text-blue-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">🐝 Bee Configuration</h1>
          <p className="text-gray-400">View current AI language model settings and service status</p>
        </div>
      </div>

      {/* Read-only notice */}
      <div className="dashboard-card p-4 bg-blue-900/30 border border-blue-700/50">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-300 mb-1">Read-Only View</h4>
            <p className="text-sm text-blue-400">
              You can view the current Bee configuration but cannot make changes. 
              Contact an administrator if you need different model settings.
            </p>
          </div>
        </div>
      </div>

      {/* Service Status */}
      <div className="dashboard-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <h3 className="font-medium text-white">Service Status</h3>
              <p className="text-sm text-gray-400">{serviceStatus.message}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Lock className="w-4 h-4" />
            <span>Admin Only</span>
          </div>
        </div>
      </div>

      {/* Current Model */}
      <div className="dashboard-card">
        <button
          onClick={() => toggleSection('model')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-yellow-400" />
            <h3 className="font-medium text-white">Current Model Configuration</h3>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSections.model ? 'rotate-180' : ''}`} />
        </button>
          
        {expandedSections.model && (
          <div className="p-4 pt-0 border-t border-gray-600">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Active Model
                </label>
                <div className="w-full p-3 bg-gray-700/50 border border-gray-600 text-white rounded-lg">
                  {selectedModel || 'No model selected'}
                  {selectedModel === 'phi3' && <span className="ml-2 text-sm text-green-400">(Recommended)</span>}
                </div>
                {selectedModel && (
                  <p className="text-sm text-gray-400 mt-2">
                    {getModelDescription(selectedModel)}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {models.map((model) => (
                  <div 
                    key={model}
                    className={`p-3 rounded-lg border ${
                      model === selectedModel 
                        ? 'bg-yellow-900/30 border-yellow-700/50' 
                        : 'bg-gray-800/50 border-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className={`font-medium ${
                        model === selectedModel ? 'text-yellow-300' : 'text-gray-300'
                      }`}>
                        {model}
                        {model === selectedModel && <span className="ml-2 text-xs">(Active)</span>}
                        {model === 'phi3' && <span className="ml-2 text-xs">(Default)</span>}
                      </h4>
                    </div>
                    <p className={`text-sm ${
                      model === selectedModel ? 'text-yellow-400' : 'text-gray-400'
                    }`}>
                      {getModelDescription(model)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Performance Settings */}
      <div className="dashboard-card">
        <button
          onClick={() => toggleSection('performance')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <HardDrive className="w-5 h-5 text-green-500" />
            <h3 className="font-medium text-white">Performance Configuration</h3>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSections.performance ? 'rotate-180' : ''}`} />
        </button>
        
        {expandedSections.performance && (
          <div className="p-4 pt-0 border-t border-gray-600">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-white">Response Streaming</h4>
                  <p className="text-sm text-gray-400">Show responses as they're being generated</p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-11 h-6 bg-yellow-400 rounded-full relative">
                    <div className="absolute top-[2px] right-[2px] bg-white border border-gray-300 rounded-full h-5 w-5"></div>
                  </div>
                  <span className="text-xs text-green-400">Enabled</span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-white">Response Caching</h4>
                  <p className="text-sm text-gray-400">Cache responses for faster repeated queries</p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-11 h-6 bg-yellow-400 rounded-full relative">
                    <div className="absolute top-[2px] right-[2px] bg-white border border-gray-300 rounded-full h-5 w-5"></div>
                  </div>
                  <span className="text-xs text-green-400">Enabled</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* System Information */}
      <div className="dashboard-card">
        <button
          onClick={() => toggleSection('system')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <Info className="w-5 h-5 text-purple-500" />
            <h3 className="font-medium text-white">System Information</h3>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSections.system ? 'rotate-180' : ''}`} />
        </button>
        
        {expandedSections.system && (
          <div className="p-4 pt-0 border-t border-gray-600">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                <h4 className="font-medium text-white mb-1">Memory Usage</h4>
                <p className="text-sm text-gray-400">Model memory consumption monitoring</p>
                <div className="mt-2 text-xs text-green-400">Active monitoring</div>
              </div>
              
              <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                <h4 className="font-medium text-white mb-1">GPU Acceleration</h4>
                <p className="text-sm text-gray-400">Hardware acceleration status</p>
                <div className="mt-2 text-xs text-blue-400">MPS enabled</div>
              </div>
              
              <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                <h4 className="font-medium text-white mb-1">Available Models</h4>
                <p className="text-sm text-gray-400">Models configured for this instance</p>
                <div className="mt-2 text-xs text-yellow-400">{models.length} models available</div>
              </div>
              
              <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                <h4 className="font-medium text-white mb-1">Service Health</h4>
                <p className="text-sm text-gray-400">Overall system health status</p>
                <div className={`mt-2 text-xs ${
                  serviceStatus.status === 'healthy' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {serviceStatus.status === 'healthy' ? 'Operational' : 'Service Issues'}
                </div>
              </div>
            </div>
            
            <div className="mt-4 p-4 bg-gray-900/50 border border-gray-700/50 rounded-lg">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-300 mb-1">Need Changes?</h4>
                  <p className="text-sm text-blue-400">
                    If you need different model settings or performance configurations, 
                    contact your system administrator. Model changes require admin privileges.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BeeSettingsReadOnly;