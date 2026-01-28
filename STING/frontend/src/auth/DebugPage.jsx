import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Activity, 
  Server, 
  Wrench, 
  RefreshCw, 
  Trash2, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader,
  Navigation,
  Terminal,
  Database,
  Code
} from 'lucide-react';
import PasskeyDebugPanel from '../components/debug/PasskeyDebugPanel';
import PasskeyDebugCheck from '../components/auth/PasskeyDebugCheck';
import '../theme/floating-design.css'; // Import dashboard styles

/**
 * DebugPage - A component for diagnosing authentication and routing issues
 * Updated to match STING UI theme
 */
const DebugPage = () => {
  const [testResults, setTestResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  const [scriptOutput, setScriptOutput] = useState('');
  const [scriptLoading, setScriptLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('tests');
  
  const kratosUrl = window.env?.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
  const appUrl = window.location.origin;
  const apiUrl = window.env?.REACT_APP_API_URL || 'https://localhost:5050';

  // Function to test direct Kratos API connection
  const testKratosConnection = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const response = await fetch(`${kratosUrl}/health/ready`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        // Important for cross-domain cookies
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setTestResults(prev => ({
          ...prev,
          kratosHealth: { success: true, data }
        }));
      } else {
        setTestResults(prev => ({
          ...prev,
          kratosHealth: { 
            success: false, 
            status: response.status,
            statusText: response.statusText
          }
        }));
      }
    } catch (err) {
      console.error('Kratos health check failed:', err);
      setTestResults(prev => ({
        ...prev,
        kratosHealth: { 
          success: false, 
          error: err.message 
        }
      }));
    } finally {
      setLoading(false);
    }
  };
  
  // Function to test login flow creation
  const testLoginFlow = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const response = await fetch(`${kratosUrl}/self-service/login/api`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setTestResults(prev => ({
          ...prev,
          loginFlow: { 
            success: true, 
            flowId: data.id,
            expiresAt: data.expires_at
          }
        }));
        
        // Store flow ID for potential use
        window.sessionStorage.setItem('debug_flow_id', data.id);
      } else {
        setTestResults(prev => ({
          ...prev,
          loginFlow: { 
            success: false, 
            status: response.status,
            statusText: response.statusText
          }
        }));
      }
    } catch (err) {
      console.error('Login flow creation failed:', err);
      setTestResults(prev => ({
        ...prev,
        loginFlow: { 
          success: false, 
          error: err.message 
        }
      }));
    } finally {
      setLoading(false);
    }
  };
  
  // Helper for direct navigation to URL
  const navigateTo = (url) => {
    try {
      window.location.href = url;
    } catch (err) {
      setErrorMessage(`Navigation error: ${err.message}`);
    }
  };
  
  // Test direct dashboard navigation
  const testDashboard = () => navigateTo('/dashboard');
  
  // Test manual login with flow
  const testManualLogin = () => {
    const returnTo = encodeURIComponent(`${appUrl}/dashboard`);
    navigateTo(`${kratosUrl}/self-service/login/browser?return_to=${returnTo}`);
  };
  
  // Test login with a flow ID if we have one
  const testFlowLogin = () => {
    const flowId = window.sessionStorage.getItem('debug_flow_id');
    if (flowId) {
      navigateTo(`/login?flow=${flowId}`);
    } else {
      setErrorMessage('No flow ID available. Run the Login Flow Test first.');
    }
  };
  
  // Function to fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/debug/system-status`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data);
      } else {
        console.error('Failed to fetch system status');
      }
    } catch (err) {
      console.error('Error fetching system status:', err);
    }
  };

  // Function to clear user data
  const clearUserData = async () => {
    if (!window.confirm('⚠️ This will permanently delete ALL user accounts and data!\n\nThis action cannot be undone. Are you sure you want to continue?')) {
      return;
    }
    
    setScriptLoading(true);
    setScriptOutput('');
    setErrorMessage('');
    
    try {
      const response = await fetch(`${apiUrl}/api/debug/clear-users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      
      const data = await response.json();
      
      if (data.success) {
        setScriptOutput(`✅ ${data.message}\n\n${data.output || ''}`);
        // Refresh system status
        setTimeout(fetchSystemStatus, 2000);
      } else {
        setErrorMessage(`❌ ${data.error}\n\nOutput: ${data.output || ''}\nError: ${data.stderr || ''}`);
      }
    } catch (err) {
      setErrorMessage(`❌ Failed to clear user data: ${err.message}`);
    } finally {
      setScriptLoading(false);
    }
  };

  // Function to fix msting command
  const fixMstingCommand = async () => {
    setScriptLoading(true);
    setScriptOutput('');
    setErrorMessage('');
    
    try {
      const response = await fetch(`${apiUrl}/api/debug/fix-msting`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      
      const data = await response.json();
      
      if (data.success) {
        setScriptOutput(`✅ ${data.message}\n\n${data.output || ''}`);
        // Refresh system status
        setTimeout(fetchSystemStatus, 2000);
      } else {
        setErrorMessage(`❌ ${data.error}\n\nOutput: ${data.output || ''}\nError: ${data.stderr || ''}`);
      }
    } catch (err) {
      setErrorMessage(`❌ Failed to fix msting command: ${err.message}`);
    } finally {
      setScriptLoading(false);
    }
  };
  
  // Run basic tests on mount
  useEffect(() => {
    testKratosConnection();
    fetchSystemStatus();
  }, []);
  
  return (
    <div className="min-h-screen bg-gray-900 px-6 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          <div className="p-3 bg-yellow-500/20 rounded-lg">
            <Code className="w-8 h-8 text-yellow-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Debug Console</h1>
            <p className="text-gray-400">System diagnostics and testing tools</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="mb-6 flex gap-4 border-b border-gray-700">
          <button
            onClick={() => setActiveTab('tests')}
            className={`py-3 px-6 font-medium transition-colors ${
              activeTab === 'tests'
                ? 'text-yellow-400 border-b-2 border-yellow-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Connection Tests
            </div>
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`py-3 px-6 font-medium transition-colors ${
              activeTab === 'tools'
                ? 'text-yellow-400 border-b-2 border-yellow-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4" />
              Dev Tools
            </div>
          </button>
          <button
            onClick={() => setActiveTab('passkeys')}
            className={`py-3 px-6 font-medium transition-colors ${
              activeTab === 'passkeys'
                ? 'text-yellow-400 border-b-2 border-yellow-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Passkey Testing
            </div>
          </button>
        </div>

        {/* Loading States */}
        {(loading || scriptLoading) && (
          <div className="mb-6 dashboard-card p-4">
            <div className="flex items-center gap-3">
              <Loader className="w-5 h-5 animate-spin text-yellow-400" />
              <span className="text-gray-300">
                {loading ? 'Running tests...' : 'Running development script...'}
              </span>
            </div>
          </div>
        )}

        {/* Error Display */}
        {errorMessage && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-700/50 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
              <pre className="text-red-300 whitespace-pre-wrap flex-1">{errorMessage}</pre>
            </div>
          </div>
        )}

        {/* Success Output */}
        {scriptOutput && (
          <div className="mb-6 p-4 bg-green-900/30 border border-green-700/50 rounded-lg">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-400 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-green-300 font-semibold mb-2">Script Output</h3>
                <pre className="text-green-200 text-sm whitespace-pre-wrap">{scriptOutput}</pre>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'tests' && (
          <>
            {/* Environment Info */}
            <div className="mb-6 dashboard-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Server className="w-5 h-5 text-blue-400" />
                <h2 className="text-xl font-semibold text-white">Environment Information</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Kratos URL:</span>
                  <span className="text-gray-300 ml-2">{kratosUrl}</span>
                </div>
                <div>
                  <span className="text-gray-500">App URL:</span>
                  <span className="text-gray-300 ml-2">{appUrl}</span>
                </div>
                <div>
                  <span className="text-gray-500">API URL:</span>
                  <span className="text-gray-300 ml-2">{apiUrl}</span>
                </div>
                <div>
                  <span className="text-gray-500">Environment:</span>
                  <span className="text-gray-300 ml-2">{process.env.NODE_ENV}</span>
                </div>
              </div>
            </div>

            {/* Test Results */}
            <div className="mb-6 dashboard-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Activity className="w-5 h-5 text-green-400" />
                <h2 className="text-xl font-semibold text-white">Test Results</h2>
              </div>
              
              {/* Kratos Health */}
              <div className="mb-4 p-4 bg-gray-800/50 rounded-lg">
                <h3 className="font-medium text-white mb-2">Kratos Health Check</h3>
                {testResults.kratosHealth ? (
                  <div className="flex items-center gap-2">
                    {testResults.kratosHealth.success ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-400" />
                        <span className="text-green-300">Kratos is healthy</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4 text-red-400" />
                        <span className="text-red-300">
                          {testResults.kratosHealth.error || `Status: ${testResults.kratosHealth.status}`}
                        </span>
                      </>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-500 italic">No results yet</span>
                )}
              </div>

              {/* Login Flow */}
              <div className="mb-4 p-4 bg-gray-800/50 rounded-lg">
                <h3 className="font-medium text-white mb-2">Login Flow Creation</h3>
                {testResults.loginFlow ? (
                  <div className="space-y-1">
                    {testResults.loginFlow.success ? (
                      <>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          <span className="text-green-300">Login flow created successfully</span>
                        </div>
                        <p className="text-sm text-gray-400 ml-6">Flow ID: {testResults.loginFlow.flowId}</p>
                        <p className="text-sm text-gray-400 ml-6">Expires: {testResults.loginFlow.expiresAt}</p>
                      </>
                    ) : (
                      <div className="flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-red-400" />
                        <span className="text-red-300">
                          {testResults.loginFlow.error || `Status: ${testResults.loginFlow.status}`}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-500 italic">No results yet</span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                <button 
                  onClick={testKratosConnection}
                  className="floating-button bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2"
                  disabled={loading}
                >
                  <Server className="w-4 h-4" />
                  Test Kratos Connection
                </button>
                
                <button 
                  onClick={testLoginFlow}
                  className="floating-button bg-green-600 hover:bg-green-700 flex items-center justify-center gap-2"
                  disabled={loading}
                >
                  <Activity className="w-4 h-4" />
                  Create Login Flow
                </button>
              </div>
            </div>

            {/* Navigation Tests */}
            <div className="dashboard-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Navigation className="w-5 h-5 text-purple-400" />
                <h2 className="text-xl font-semibold text-white">Navigation Tests</h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <button 
                  onClick={testDashboard}
                  className="floating-button bg-purple-600 hover:bg-purple-700"
                >
                  Go to Dashboard
                </button>
                
                <button 
                  onClick={testManualLogin}
                  className="floating-button bg-yellow-600 hover:bg-yellow-700"
                >
                  Kratos Login (Browser Flow)
                </button>
                
                <button 
                  onClick={testFlowLogin}
                  className="floating-button bg-gray-600 hover:bg-gray-700"
                  disabled={!window.sessionStorage.getItem('debug_flow_id')}
                >
                  Use Existing Flow
                </button>

                <a 
                  href={`${kratosUrl}/.well-known/jwks.json`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="floating-button bg-gray-600 hover:bg-gray-700 text-center"
                >
                  Test Kratos JWKS
                </a>
              </div>
            </div>
          </>
        )}

        {activeTab === 'tools' && (
          <>
            {/* System Status */}
            {systemStatus && (
              <div className="mb-6 dashboard-card p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Database className="w-5 h-5 text-cyan-400" />
                  <h2 className="text-xl font-semibold text-white">System Status</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-400 block mb-1">Clear Users Script</span>
                    <span className={systemStatus.scripts?.clear_users_available ? 'text-green-300' : 'text-red-300'}>
                      {systemStatus.scripts?.clear_users_available ? '✅ Available' : '❌ Missing'}
                    </span>
                  </div>
                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-400 block mb-1">Fix msting Script</span>
                    <span className={systemStatus.scripts?.fix_msting_available ? 'text-green-300' : 'text-red-300'}>
                      {systemStatus.scripts?.fix_msting_available ? '✅ Available' : '❌ Missing'}
                    </span>
                  </div>
                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-400 block mb-1">msting Command</span>
                    <span className={systemStatus.msting_command?.available ? 'text-green-300' : 'text-yellow-300'}>
                      {systemStatus.msting_command?.available ? '✅ Installed' : '⚠️ Not Found'}
                    </span>
                  </div>
                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-400 block mb-1">Docker Services</span>
                    <span className="text-blue-300">
                      {systemStatus.docker_services?.length || 0} running
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Development Tools */}
            <div className="dashboard-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <Wrench className="w-5 h-5 text-red-400" />
                <h2 className="text-xl font-semibold text-white">Development Tools</h2>
              </div>
              
              <div className="mb-4 p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <span className="text-red-300 font-medium">⚠️ Danger Zone</span>
                </div>
                <p className="text-red-300/80 text-sm">
                  These tools will modify or delete data. Use with caution!
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button 
                  onClick={clearUserData}
                  className="floating-button bg-red-600 hover:bg-red-700 flex items-center justify-center gap-2"
                  disabled={scriptLoading}
                >
                  <Trash2 className="w-4 h-4" />
                  Clear All User Data
                </button>
                
                <button 
                  onClick={fixMstingCommand}
                  className="floating-button bg-orange-600 hover:bg-orange-700 flex items-center justify-center gap-2"
                  disabled={scriptLoading}
                >
                  <Terminal className="w-4 h-4" />
                  Fix msting Command
                </button>
                
                <button 
                  onClick={fetchSystemStatus}
                  className="floating-button bg-gray-600 hover:bg-gray-700 flex items-center justify-center gap-2"
                  disabled={scriptLoading}
                >
                  <RefreshCw className="w-4 h-4" />
                  Refresh Status
                </button>
              </div>
              
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-gray-400">
                <div className="p-2">
                  <strong>Clear User Data:</strong> Removes all accounts and sessions
                </div>
                <div className="p-2">
                  <strong>Fix msting:</strong> Installs the msting CLI tool
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'passkeys' && (
          <>
            <PasskeyDebugPanel />
            <div className="mt-6">
              <PasskeyDebugCheck />
            </div>
          </>
        )}
        
        {/* Footer Note */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>404 errors may indicate networking, CORS, or SSL certificate issues</p>
        </div>
      </div>
    </div>
  );
};

export default DebugPage;