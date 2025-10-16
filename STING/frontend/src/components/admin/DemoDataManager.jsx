import React, { useState, useEffect } from 'react';
import { Play, Database, FileText, Users, Shield, AlertCircle, CheckCircle, Loader, Heart, Bot } from 'lucide-react';
import { Button, Card, message, Progress } from 'antd';
import reportApi from '../../services/reportApi';
import TierBadge, { TierIndicator, OPERATION_TIERS } from '../common/TierBadge';
import {
  handleReturnFromAuth,
  checkOperationAuth,
  clearAuthMarker,
  storeOperationContext,
  getStoredOperationContext,
  shouldRetryOperation,
  OPERATIONS
} from '../../utils/tieredAuth';

// Define operations for demo data management
const DEMO_OPERATIONS = {
  GENERATE_DEMO_DATA: {
    name: 'GENERATE_DEMO_DATA',
    tier: 3,
    description: 'Generate demo data scenarios'
  },
  CLEAR_DEMO_DATA: {
    name: 'CLEAR_DEMO_DATA',
    tier: 4,
    description: 'Clear all demo data'
  },
  VIEW_DEMO_STATS: {
    name: 'VIEW_DEMO_STATS',
    tier: 2,
    description: 'View demo data statistics'
  }
};

const DemoDataManager = () => {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState('');
  const [generatedData, setGeneratedData] = useState({
    reports: 0,
    honeyJars: 0,
    documents: 0,
    users: 0
  });
  const [loading, setLoading] = useState(true);

  // Handle return from authentication flow and auto-retry operations
  useEffect(() => {
    // Check for each operation if user just returned from authentication
    Object.values(DEMO_OPERATIONS).forEach(operation => {
      if (shouldRetryOperation(operation.name)) {
        console.log(`🔄 Auto-retrying demo operation after authentication: ${operation.name}`);

        // Get stored context
        const context = getStoredOperationContext(operation.name);

        // Set auth marker
        handleReturnFromAuth(operation.name);

        // Auto-retry the operation based on its type
        setTimeout(() => {
          switch (operation.name) {
            case DEMO_OPERATIONS.GENERATE_DEMO_DATA.name:
              if (context?.scenarioId) {
                generateDemoData(context.scenarioId);
              }
              break;
            case DEMO_OPERATIONS.CLEAR_DEMO_DATA.name:
              clearDemoData();
              break;
            default:
              console.log(`⚠️ Unknown demo operation for auto-retry: ${operation.name}`);
          }
        }, 100); // Small delay to ensure page is fully loaded
      }
    });
  }, []);

  // Tiered authentication for demo operations
  const protectDemoOperation = async (operationKey, additionalData = {}) => {
    const operation = DEMO_OPERATIONS[operationKey];
    if (!operation) {
      console.error('Unknown demo operation:', operationKey);
      return false;
    }

    console.log(`🔐 Demo: Checking ${operation.tier} authentication for: ${operation.description}`);

    const canProceed = await checkOperationAuth(operation.name, operation.tier, additionalData);

    if (canProceed) {
      console.log(`✅ Demo: Authentication verified for ${operation.description}`);
      return true;
    } else {
      console.log(`❌ Demo: Authentication failed for ${operation.description}`);
      return false;
    }
  };

  const demoScenarios = [
    {
      id: 'basic',
      name: 'Basic Demo Data',
      description: 'Generate basic honey jars, documents, and sample reports',
      icon: Database,
      estimatedTime: '2-3 minutes',
      includes: [
        '5 sample honey jars with documents',
        '10 sample reports (various types)',
        'Sample PII data for scrubbing demos',
        'Basic user activity data'
      ]
    },
    {
      id: 'comprehensive',
      name: 'Comprehensive Demo',
      description: 'Full demo environment with all features populated',
      icon: Shield,
      estimatedTime: '5-8 minutes',
      includes: [
        '20 honey jars across different categories',
        '50 sample reports with realistic data',
        'Compliance templates with test data',
        'Advanced PII patterns and scenarios',
        'Sample team collaboration data',
        'Security audit trails'
      ]
    },
    {
      id: 'security-focused',
      name: 'Security & Compliance Demo',
      description: 'Focus on security features and compliance reporting',
      icon: Shield,
      estimatedTime: '3-4 minutes',
      includes: [
        'Security-focused honey jars',
        'Compliance reports (HIPAA, GDPR, etc.)',
        'PII detection and scrubbing samples',
        'Security audit reports',
        'Vulnerability assessments'
      ]
    },
    {
      id: 'healthcare',
      name: 'Healthcare & Medical Demo',
      description: 'Generate realistic healthcare data with HIPAA compliance focus',
      icon: Heart,
      estimatedTime: '2-3 minutes',
      includes: [
        'Patient intake forms with PHI',
        'Lab results and medical reports',
        'Prescription and medication data',
        'HIPAA compliance templates',
        'Medical record number patterns',
        'Healthcare provider information'
      ]
    },
    {
      id: 'pii-scrubbing',
      name: 'PII Scrubbing Demo',
      description: 'Generate diverse PII patterns for testing scrubbing capabilities',
      icon: FileText,
      estimatedTime: '1-2 minutes',
      includes: [
        'Sample documents with various PII types',
        'Email addresses, phone numbers, SSNs',
        'Medical records samples',
        'Financial data patterns',
        'Custom PII detection rules'
      ]
    },
    {
      id: 'nectar-bot',
      name: 'Nectar Bot Demo',
      description: 'Generate AI-powered chatbots with conversation data and handoff scenarios',
      icon: Bot,
      estimatedTime: '2-3 minutes',
      includes: [
        'Customer Support Bot with conversation history',
        'FAQ Assistant with automated responses',
        'Documentation Helper Bot',
        'Enterprise Support Bot with escalation data',
        'Security Incident Bot with handoff scenarios',
        'Realistic conversation usage statistics',
        'Bot handoff and escalation examples'
      ]
    }
  ];

  // Load existing demo data counts on component mount
  useEffect(() => {
    loadDemoDataCounts();
  }, []);

  const loadDemoDataCounts = async () => {
    try {
      setLoading(true);

      // Get demo reports count using proper reportApi service
      console.log('🔍 DemoDataManager: Loading demo data counts...');

      try {
        const reportsData = await reportApi.listReports({
          search: 'Demo',
          limit: 1
        });

        console.log('🔍 DemoDataManager: Found demo reports:', reportsData.data?.pagination?.total || 0);
        setGeneratedData(prev => ({
          ...prev,
          reports: reportsData.data?.pagination?.total || 0
        }));
      } catch (error) {
        console.warn('🔍 DemoDataManager: Reports API failed:', error);
      }

      // TODO: Add honey jars count when honey jar service is integrated
      // TODO: Add document count from honey jars

    } catch (error) {
      console.warn('Could not load demo data counts:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateDemoData = async (scenarioId) => {
    // Check authentication BEFORE attempting generation (Tier 3 - sensitive operation)
    const canProceed = await protectDemoOperation('GENERATE_DEMO_DATA', { scenarioId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    setGenerating(true);
    setProgress(0);
    setCurrentTask('Initializing demo data generation...');
    console.log('🔄 Generating demo data (authentication pre-verified)');

    try {
      const scenario = demoScenarios.find(s => s.id === scenarioId);

      // Call the backend demo generation API step by step
      console.log('🔍 DemoDataManager: Starting backend demo generation for scenario:', scenarioId);

      const tasks = [
        'Creating report templates...',    // Step 1
        'Generating sample documents...',  // Step 2
        'Creating honey jars...',          // Step 3
        'Uploading documents to honey jars...', // Step 4
        'Building reports...'              // Step 5
      ];

      // Execute each step sequentially
      for (let step = 1; step <= 5; step++) {
        setCurrentTask(tasks[step - 1]);
        setProgress((step / 5) * 100);

        const response = await fetch('/api/admin/generate-demo-data', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            scenario: scenarioId,
            step: step,
            totalSteps: 5
          })
        });

        if (!response.ok) {
          throw new Error(`Demo generation step ${step} failed: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();
        console.log(`🔍 DemoDataManager: Step ${step} result:`, result);

        // Add delay for UI feedback
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      message.success(`${scenario.name} generated successfully!`);
      setCurrentTask('Demo data generation completed!');

      // Clear auth markers since operation succeeded
      clearAuthMarker(DEMO_OPERATIONS.GENERATE_DEMO_DATA.name);

      // Refresh data counts
      setTimeout(() => {
        loadDemoDataCounts();
      }, 1000);

    } catch (error) {
      console.error('❌ Demo data generation failed:', error);
      message.error('Failed to generate demo data. Please try again.');
      setCurrentTask('Generation failed');
    } finally {
      setGenerating(false);
      setTimeout(() => {
        setProgress(0);
        setCurrentTask('');
      }, 3000);
    }
  };

  const clearDemoData = async () => {
    // Check authentication BEFORE attempting clear (Tier 4 - critical operation)
    const canProceed = await protectDemoOperation('CLEAR_DEMO_DATA');
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      setGenerating(true);
      setCurrentTask('Clearing demo data...');
      console.log('🔄 Clearing demo data (authentication pre-verified)');

      const response = await fetch('/api/admin/clear-demo-data', {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        setGeneratedData({ reports: 0, honeyJars: 0, documents: 0, users: 0 });
        message.success('Demo data cleared successfully!');

        // Clear auth markers since operation succeeded
        clearAuthMarker(DEMO_OPERATIONS.CLEAR_DEMO_DATA.name);
      } else {
        throw new Error('Failed to clear demo data');
      }
    } catch (error) {
      console.error('❌ Clear demo data failed:', error);
      message.error('Failed to clear demo data. Please try again.');
    } finally {
      setGenerating(false);
      setCurrentTask('');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Demo Data Manager</h2>
          <p className="text-slate-400 mt-1">
            Generate realistic demo data for testing and demonstrations
          </p>
        </div>
        <div className="flex items-center gap-3">
          <TierBadge tier={4} size="sm" showDescription operation="Clear Demo Data" />
          <Button
            danger
            onClick={clearDemoData}
            disabled={generating}
            className="bg-red-600 border-red-600 text-white hover:bg-red-700"
          >
            Clear All Demo Data
          </Button>
        </div>
      </div>

      {/* Security Notice */}
      <div className="sting-glass-subtle border border-red-500/50 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Shield className="text-red-400 text-lg mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-red-300 font-medium mb-2">Admin Security Notice</h3>
            <p className="text-red-200/80 text-sm leading-relaxed mb-3">
              Demo data operations require enhanced authentication due to their system-wide impact:
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TierBadge tier={3} size="xs" />
                <span className="text-red-200 text-sm">Generate demo scenarios</span>
              </div>
              <div className="flex items-center gap-2">
                <TierBadge tier={4} size="xs" />
                <span className="text-red-200 text-sm">Clear all demo data (irreversible)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Display */}
      {generating && (
        <Card className="bg-slate-800 border-slate-700">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-white">
              <Loader className="w-4 h-4 animate-spin" />
              <span className="font-medium">{currentTask}</span>
            </div>
            <Progress 
              percent={progress} 
              strokeColor="#facc15"
              trailColor="#374151"
              showInfo={false}
            />
            <p className="text-slate-400 text-sm">
              Please wait while we generate your demo data...
            </p>
          </div>
        </Card>
      )}

      {/* Current Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Honey Jars</p>
              <p className="text-2xl font-bold text-white">{generatedData.honeyJars}</p>
            </div>
            <Database className="w-8 h-8 text-yellow-400" />
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Reports</p>
              <p className="text-2xl font-bold text-white">{generatedData.reports}</p>
            </div>
            <FileText className="w-8 h-8 text-blue-400" />
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Documents</p>
              <p className="text-2xl font-bold text-white">{generatedData.documents}</p>
            </div>
            <FileText className="w-8 h-8 text-green-400" />
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Test Users</p>
              <p className="text-2xl font-bold text-white">{generatedData.users}</p>
            </div>
            <Users className="w-8 h-8 text-purple-400" />
          </div>
        </div>
      </div>

      {/* Demo Scenarios */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {demoScenarios.map((scenario) => {
          const IconComponent = scenario.icon;
          return (
            <Card
              key={scenario.id}
              className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors"
            >
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-lg">
                    <IconComponent className="w-6 h-6 text-yellow-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-white">{scenario.name}</h3>
                    <p className="text-slate-400 text-sm">{scenario.description}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <AlertCircle className="w-4 h-4" />
                    <span>Estimated time: {scenario.estimatedTime}</span>
                  </div>
                  <div className="text-sm text-slate-300">
                    <p className="font-medium mb-1">Includes:</p>
                    <ul className="space-y-1">
                      {scenario.includes.map((item, index) => (
                        <li key={index} className="flex items-center gap-2">
                          <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <Button
                  type="primary"
                  onClick={() => generateDemoData(scenario.id)}
                  disabled={generating}
                  className="w-full bg-yellow-500 border-yellow-500 text-black hover:bg-yellow-400"
                  icon={<Play className="w-4 h-4" />}
                >
                  Generate {scenario.name}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Warning Notice */}
      <Card className="bg-amber-900/20 border-amber-600/50">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-2">
            <h4 className="text-amber-400 font-medium">Important Notes</h4>
            <div className="text-amber-200 text-sm space-y-1">
              <p>• Demo data is for testing purposes only and contains fictional information</p>
              <p>• Generated PII patterns are synthetic and safe for demonstration</p>
              <p>• Large datasets may take several minutes to generate</p>
              <p>• Demo data can be cleared at any time without affecting real user data</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default DemoDataManager;