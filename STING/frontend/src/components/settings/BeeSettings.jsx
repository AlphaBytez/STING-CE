import React, { useState, useEffect } from 'react';
import { Settings, ChevronDown, Cpu, HardDrive, RefreshCw, AlertCircle, CheckCircle, Info, Terminal } from 'lucide-react';
import ProgressBar from '../common/ProgressBar';
import TerminalOutput from '../common/TerminalOutput';
const BeeSettings = () => {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [serviceStatus, setServiceStatus] = useState({
    status: 'unknown',
    message: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    model: true,
    performance: false,
    advanced: false
  });
  
  // Progress tracking state
  const [loadingOperation, setLoadingOperation] = useState(null);
  const [progressData, setProgressData] = useState({
    status: 'idle',
    progress: 0,
    message: '',
    logs: []
  });
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);

  // Fetch available models and current configuration
  useEffect(() => {
    fetchModels();
    fetchServiceStatus();
  }, []);

  // Poll progress when operation is active
  useEffect(() => {
    let pollInterval;
    
    if (loadingOperation) {
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`/api/llm/progress/${loadingOperation}`);
          if (response.ok) {
            const data = await response.json();
            setProgressData(data);
            
            // If operation is complete or failed, stop polling
            if (data.status === 'completed' || data.status === 'error') {
              setLoadingOperation(null);
              setTimeout(() => {
                setShowProgressModal(false);
                fetchServiceStatus(); // Refresh service status
                fetchModels(); // Refresh models
              }, 2000); // Show completion for 2 seconds
            }
          }
        } catch (error) {
          console.error('Error polling progress:', error);
        }
      }, 1000); // Poll every second
    }
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [loadingOperation]);

  const fetchModels = async () => {
    try {
      // Fetch from Ollama API
      const response = await fetch('/api/external-ai/models');
      if (response.ok) {
        const data = await response.json();
        setModels(data.models || []);
        // Get current model from Bee settings
        const beeResponse = await fetch('/api/bee/settings');
        if (beeResponse.ok) {
          const beeData = await beeResponse.json();
          setSelectedModel(beeData.active_model || 'phi3:mini');
        }
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const fetchServiceStatus = async () => {
    try {
      // Check External AI service (OpenAI-compatible API standard)
      const externalAiResponse = await fetch('/api/external-ai/health');

      if (externalAiResponse.ok) {
        const data = await externalAiResponse.json();
        setServiceStatus({
          status: 'healthy',
          message: `External AI service running (${models.length} models available)`
        });
      } else {
        setServiceStatus({
          status: 'unhealthy',
          message: 'AI services are not responding'
        });
      }
    } catch (error) {
      setServiceStatus({
        status: 'error',
        message: 'Unable to connect to AI services'
      });
    }
  };

  const handleModelChange = async (model) => {
    setIsLoading(true);
    try {
      // Update Bee's active model preference
      const response = await fetch('/api/bee/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active_model: model }),
      });

      if (response.ok) {
        setSelectedModel(model);
        // Check if model needs to be pulled
        const pullResponse = await fetch('/api/external-ai/pull', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ model }),
        });
        
        if (pullResponse.ok) {
          const data = await pullResponse.json();
          if (data.status === 'pulling') {
            setProgressData({
              status: 'starting',
              progress: 0,
              message: `Downloading ${model}...`,
              logs: []
            });
            setShowProgressModal(true);
          }
        }
      } else {
        const errorData = await response.json();
        console.error('Failed to update model:', errorData);
        alert(`Failed to update model: ${errorData.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating model:', error);
      alert(`Error updating model: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const restartService = async () => {
    setIsLoading(true);
    try {
      // Restart External AI service (Ollama managed separately)
      const response = await fetch('/api/external-ai/restart', {
        method: 'POST',
      });

      if (response.ok) {
        setServiceStatus({
          status: 'restarting',
          message: 'Restarting External AI service...'
        });
        setTimeout(() => {
          fetchServiceStatus();
          fetchModels();
        }, 3000); // Wait for service to restart
      }
    } catch (error) {
      console.error('Error restarting service:', error);
    } finally {
      setIsLoading(false);
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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-8 h-8 text-yellow-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">🐝 AI Model Settings</h1>
          <p className="text-gray-400">Configure Ollama models and External AI service</p>
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
          <button
            onClick={restartService}
            disabled={isLoading}
            className="floating-button bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Restart Bridge
          </button>
        </div>
      </div>

      {/* Model Selection */}
      <div className="dashboard-card">
        <button
          onClick={() => toggleSection('model')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-yellow-400" />
            <h3 className="font-medium text-white">Model Selection</h3>
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
                <select
                  value={selectedModel}
                  onChange={(e) => handleModelChange(e.target.value)}
                  disabled={isLoading}
                  className="w-full p-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 disabled:opacity-50"
                >
                  <option value="">Select a model...</option>
                  {models.map((model) => (
                    <option key={model} value={model}>
                      {model} {model === 'phi3' ? '(Recommended)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 bg-blue-900/30 border border-blue-700/50 rounded-lg">
                  <h4 className="font-medium text-blue-300 mb-1">phi3:mini (Default)</h4>
                  <p className="text-sm text-blue-400">3.8B model, best balance of quality and speed. Great for Bee.</p>
                </div>
                <div className="p-3 bg-green-900/30 border border-green-700/50 rounded-lg">
                  <h4 className="font-medium text-green-300 mb-1">deepseek-r1:latest</h4>
                  <p className="text-sm text-green-400">Advanced reasoning model with chain-of-thought capabilities.</p>
                </div>
                <div className="p-3 bg-purple-900/30 border border-purple-700/50 rounded-lg">
                  <h4 className="font-medium text-purple-300 mb-1">deepseek-r1:32b</h4>
                  <p className="text-sm text-purple-400">Larger DeepSeek model for complex reasoning tasks.</p>
                </div>
                <div className="p-3 bg-orange-900/30 border border-orange-700/50 rounded-lg">
                  <h4 className="font-medium text-orange-300 mb-1">Custom Models</h4>
                  <p className="text-sm text-orange-400">Pull any Ollama model using command line: ollama pull model:tag</p>
                </div>
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
            <h3 className="font-medium text-white">Performance Settings</h3>
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
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-yellow-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-yellow-400"></div>
                </label>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-white">Response Caching</h4>
                  <p className="text-sm text-gray-400">Cache responses for faster repeated queries</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-yellow-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-yellow-400"></div>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Advanced Settings */}
      <div className="dashboard-card">
        <button
          onClick={() => toggleSection('advanced')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            <Info className="w-5 h-5 text-purple-500" />
            <h3 className="font-medium text-white">Advanced Configuration</h3>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSections.advanced ? 'rotate-180' : ''}`} />
        </button>
        
        {expandedSections.advanced && (
          <div className="p-4 pt-0 border-t border-gray-600">
            <div className="space-y-4">
              <div className="p-4 bg-yellow-900/30 border border-yellow-700/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-yellow-300 mb-1">Advanced Configuration</h4>
                    <p className="text-sm text-yellow-400">
                      Advanced settings are available through the configuration file. 
                      Modify these settings only if you understand their impact on performance.
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                  <h4 className="font-medium text-white mb-1">Ollama Service</h4>
                  <p className="text-sm text-gray-400">Local LLM server status</p>
                  <div className="mt-2 text-xs text-green-400">Running on localhost:11434</div>
                </div>
                
                <div className="p-3 bg-gray-800 border border-gray-600 rounded-lg">
                  <h4 className="font-medium text-white mb-1">External AI Bridge</h4>
                  <p className="text-sm text-gray-400">STING to Ollama connector</p>
                  <div className="mt-2 text-xs text-blue-400">Connected via port 8091</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Progress Modal */}
      {showProgressModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Loading Model</h3>
              <button
                onClick={() => setShowTerminal(!showTerminal)}
                className="floating-button bg-gray-600 hover:bg-gray-500"
              >
                <Terminal className="w-4 h-4" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm text-gray-300 mb-1">
                  <span>{progressData.message}</span>
                  <span>{Math.round(progressData.progress)}%</span>
                </div>
                <ProgressBar 
                  progress={progressData.progress} 
                  variant={progressData.status === 'error' ? 'error' : 'default'}
                />
              </div>
              
              {showTerminal && progressData.logs && progressData.logs.length > 0 && (
                <TerminalOutput logs={progressData.logs} maxHeight="200px" />
              )}
              
              {progressData.status === 'completed' && (
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  <span>Model loaded successfully!</span>
                </div>
              )}
              
              {progressData.status === 'error' && (
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle className="w-4 h-4" />
                  <span>Failed to load model</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BeeSettings;