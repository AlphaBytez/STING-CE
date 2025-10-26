import React, { useState, useEffect } from 'react';
import {
  Settings,
  Plus,
  Edit,
  Trash2,
  Download,
  Upload,
  Shield,
  AlertTriangle,
  CheckCircle,
  Eye,
  Copy,
  Save,
  RefreshCw,
  Filter,
  Search,
  Sliders
} from 'lucide-react';
import PIISettingsFramework from './PIISettingsFramework';

const PIIConfigurationManager = () => {
  const [activeTab, setActiveTab] = useState('patterns');
  const [patterns, setPatterns] = useState([]);
  const [complianceProfiles, setComplianceProfiles] = useState([]);
  const [customRules, setCustomRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [testingPattern, setTestingPattern] = useState(null);
  const [testText, setTestText] = useState('');
  const [testResults, setTestResults] = useState(null);
  const [showAddPatternDialog, setShowAddPatternDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState(null);

  // Mock data - would come from backend
  const defaultPatterns = [
    {
      id: 1,
      name: 'Social Security Number',
      category: 'personal',
      pattern: '\\b\\d{3}-\\d{2}-\\d{4}\\b',
      description: 'US Social Security Number (XXX-XX-XXXX)',
      risk_level: 'high',
      compliance_frameworks: ['GDPR', 'CCPA'],
      enabled: true,
      custom: false,
      detection_count: 1247,
      last_detected: '2025-01-06T10:30:00Z'
    },
    {
      id: 2,
      name: 'Medical Record Number',
      category: 'medical',
      pattern: '\\b(?:MRN|Medical Record Number|Med Rec #?)[:\\s]*([A-Z0-9]{6,12})\\b',
      description: 'Medical Record Numbers in various formats',
      risk_level: 'medium',
      compliance_frameworks: ['HIPAA'],
      enabled: true,
      custom: false,
      detection_count: 892,
      last_detected: '2025-01-06T09:15:00Z'
    },
    {
      id: 3,
      name: 'Case Number',
      category: 'legal',
      pattern: '\\b(?:Case\\s*(?:No\\.?|Number)?[:\\s]*)?((?:\\d{2,4}[-/])?[A-Z]{2,4}[-/]\\d{3,8}(?:[-/]\\w+)?)\\b',
      description: 'Legal case numbers in court formats',
      risk_level: 'medium',
      compliance_frameworks: ['Attorney-Client'],
      enabled: true,
      custom: false,
      detection_count: 445,
      last_detected: '2025-01-06T08:22:00Z'
    }
  ];

  const complianceFrameworks = [
    {
      id: 1,
      name: 'HIPAA',
      description: 'Health Insurance Portability and Accountability Act',
      categories: ['medical', 'personal'],
      mandatory_patterns: ['medical_record', 'patient_id', 'ssn'],
      risk_threshold: 'medium',
      retention_days: 2555, // 7 years
      encryption_required: true,
      active: true
    },
    {
      id: 2,
      name: 'GDPR',
      description: 'General Data Protection Regulation',
      categories: ['personal', 'contact'],
      mandatory_patterns: ['email', 'phone', 'name', 'address'],
      risk_threshold: 'low',
      retention_days: 1095, // 3 years
      encryption_required: true,
      active: true
    },
    {
      id: 3,
      name: 'Attorney-Client',
      description: 'Attorney-Client Privilege Protection',
      categories: ['legal'],
      mandatory_patterns: ['case_number', 'settlement_amount', 'bar_number'],
      risk_threshold: 'medium',
      retention_days: 3650, // 10 years
      encryption_required: true,
      active: true
    }
  ];

  useEffect(() => {
    loadPIIConfiguration();
  }, []);

  const loadPIIConfiguration = async () => {
    try {
      setLoading(true);
      
      // Fetch patterns from backend
      const patternsResponse = await fetch('/api/pii/patterns', {
        credentials: 'include'
      });
      
      if (patternsResponse.ok) {
        const patternsData = await patternsResponse.json();
        setPatterns(patternsData.patterns || defaultPatterns);
      } else {
        console.warn('Failed to load patterns from backend, using defaults');
        setPatterns(defaultPatterns);
      }
      
      // Fetch compliance frameworks
      const frameworksResponse = await fetch('/api/pii/frameworks', {
        credentials: 'include'
      });
      
      if (frameworksResponse.ok) {
        const frameworksData = await frameworksResponse.json();
        setComplianceProfiles(frameworksData.frameworks || complianceFrameworks);
      } else {
        console.warn('Failed to load frameworks from backend, using defaults');
        setComplianceProfiles(complianceFrameworks);
      }
      
    } catch (error) {
      console.error('Error loading PII configuration:', error);
      // Fallback to mock data
      setPatterns(defaultPatterns);
      setComplianceProfiles(complianceFrameworks);
    } finally {
      setLoading(false);
    }
  };

  const handlePatternToggle = (id) => {
    setPatterns(patterns.map(p => 
      p.id === id ? { ...p, enabled: !p.enabled } : p
    ));
  };

  const handleExportConfig = async () => {
    try {
      const response = await fetch('/api/pii/export', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const config = await response.json();
        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sting-pii-config-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert('Failed to export configuration from server');
      }
    } catch (error) {
      console.error('Export error:', error);
      alert('Error exporting configuration');
    }
  };

  const handleImportConfig = async (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const config = JSON.parse(e.target.result);
          
          // Send to backend for validation and import
          const response = await fetch('/api/pii/import', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(config)
          });
          
          if (response.ok) {
            const result = await response.json();
            if (result.success) {
              alert(`Configuration imported successfully! ${result.imported_count}/${result.total_patterns} patterns imported.`);
              // Reload patterns from backend
              await loadPIIConfiguration();
            } else {
              let message = 'Import completed with issues:\n';
              if (result.errors && result.errors.length > 0) {
                message += result.errors.slice(0, 5).join('\n');
                if (result.errors.length > 5) {
                  message += `\n... and ${result.errors.length - 5} more errors`;
                }
              }
              alert(message);
            }
          } else {
            const error = await response.json();
            alert(`Import failed: ${error.error || 'Unknown error'}`);
          }
        } catch (error) {
          alert('Error importing configuration: Invalid JSON format or network error');
        }
      };
      reader.readAsText(file);
    }
    // Clear the file input
    if (event.target) {
      try {
        event.target.value = '';
      } catch (error) {
        console.error('❌ Error clearing file input value:', error);
      }
    }
  };

  const handleTestPattern = async (pattern) => {
    try {
      const response = await fetch('/api/pii/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          pattern: pattern.pattern,
          text: testText
        })
      });
      
      if (response.ok) {
        const results = await response.json();
        setTestResults(results);
      } else {
        const error = await response.json();
        alert(`Pattern test failed: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert('Error testing pattern: Network error');
    }
  };

  const openPatternTester = (pattern) => {
    setTestingPattern(pattern);
    setTestText('');
    setTestResults(null);
  };

  const openProfileSettings = (profileId) => {
    setSelectedProfileId(profileId);
    setShowSettingsDialog(true);
  };

  const handleSettingsSave = (settings) => {
    console.log('Saving profile settings:', settings);
    setShowSettingsDialog(false);
    // Refresh compliance profiles after settings save
    loadPIIConfiguration();
  };

  const filteredPatterns = patterns.filter(pattern => {
    const matchesSearch = pattern.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         pattern.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || pattern.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const PatternCard = ({ pattern }) => (
    <div className="dashboard-card p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3">
          <div className={`p-2 rounded-lg ${
            pattern.risk_level === 'high' ? 'bg-red-500/20 text-red-400' :
            pattern.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-green-500/20 text-green-400'
          }`}>
            <Shield className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-white">{pattern.name}</h3>
              {pattern.custom && (
                <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                  Custom
                </span>
              )}
              <span className={`px-2 py-1 text-xs rounded-full ${
                pattern.category === 'medical' ? 'bg-purple-500/20 text-purple-400' :
                pattern.category === 'legal' ? 'bg-amber-500/20 text-amber-400' :
                pattern.category === 'financial' ? 'bg-green-500/20 text-green-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {pattern.category}
              </span>
            </div>
            <p className="text-gray-400 text-sm mt-1">{pattern.description}</p>
            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
              <span>Detected: {pattern.detection_count.toLocaleString()}</span>
              <span>Last: {new Date(pattern.last_detected).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handlePatternToggle(pattern.id)}
            className={`p-2 rounded-lg transition-colors ${
              pattern.enabled 
                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' 
                : 'bg-gray-500/20 text-gray-400 hover:bg-gray-500/30'
            }`}
            title={pattern.enabled ? 'Disable pattern' : 'Enable pattern'}
          >
            <CheckCircle className="w-4 h-4" />
          </button>
          <button className="p-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
            <Edit className="w-4 h-4" />
          </button>
          <button 
            onClick={() => openPatternTester(pattern)}
            className="p-2 rounded-lg bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 transition-colors"
            title="Test pattern"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="bg-gray-800/50 rounded p-3 mb-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">Regular Expression Pattern:</span>
          <button 
            onClick={() => navigator.clipboard.writeText(pattern.pattern)}
            className="p-1 rounded text-gray-400 hover:text-white transition-colors"
            title="Copy pattern"
          >
            <Copy className="w-3 h-3" />
          </button>
        </div>
        <code className="text-xs text-green-400 font-mono break-all">
          {pattern.pattern}
        </code>
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">Compliance:</span>
          {pattern.compliance_frameworks.map(framework => (
            <span key={framework} className="px-2 py-1 bg-indigo-500/20 text-indigo-400 text-xs rounded">
              {framework}
            </span>
          ))}
        </div>
        <div className={`px-2 py-1 rounded text-xs ${
          pattern.risk_level === 'high' ? 'bg-red-500/20 text-red-400' :
          pattern.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-green-500/20 text-green-400'
        }`}>
          {pattern.risk_level} risk
        </div>
      </div>
    </div>
  );

  const ComplianceProfileCard = ({ profile }) => (
    <div className="dashboard-card p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
            <Shield className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-white">{profile.name}</h3>
              {profile.active && (
                <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                  Active
                </span>
              )}
            </div>
            <p className="text-gray-400 text-sm mt-1">{profile.description}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button 
            onClick={() => openProfileSettings(profile.id)}
            className="p-2 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
            title="Configure Profile Settings"
          >
            <Sliders className="w-4 h-4" />
          </button>
          <button className="p-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Categories:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {profile.categories.map(category => (
              <span key={category} className="px-2 py-1 bg-gray-700/50 text-gray-300 text-xs rounded">
                {category}
              </span>
            ))}
          </div>
        </div>
        <div>
          <span className="text-gray-400">Retention:</span>
          <div className="text-white mt-1">{Math.floor(profile.retention_days / 365)} years</div>
        </div>
        <div>
          <span className="text-gray-400">Risk Threshold:</span>
          <div className={`mt-1 ${
            profile.risk_threshold === 'high' ? 'text-red-400' :
            profile.risk_threshold === 'medium' ? 'text-yellow-400' :
            'text-green-400'
          }`}>{profile.risk_threshold}</div>
        </div>
        <div>
          <span className="text-gray-400">Encryption:</span>
          <div className="flex items-center space-x-1 mt-1">
            {profile.encryption_required ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
            )}
            <span className="text-white text-sm">
              {profile.encryption_required ? 'Required' : 'Optional'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">PII Configuration Manager</h1>
          <p className="text-gray-400">Configure PII detection patterns, compliance profiles, and custom rules</p>
        </div>
        <div className="flex items-center space-x-3">
          <input
            type="file"
            id="import-config"
            accept=".json"
            onChange={handleImportConfig}
            className="hidden"
          />
          <label
            htmlFor="import-config"
            className="px-4 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors cursor-pointer flex items-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>Import</span>
          </label>
          <button
            onClick={handleExportConfig}
            className="px-4 py-2 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded-lg transition-colors flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          <button 
            onClick={() => setShowAddPatternDialog(true)}
            className="px-4 py-2 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add Pattern</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-gray-800/50 p-1 rounded-lg">
        {[
          { id: 'patterns', label: 'PII Patterns', icon: Settings },
          { id: 'compliance', label: 'Compliance Profiles', icon: Shield },
          { id: 'custom', label: 'Custom Rules', icon: Edit },
          { id: 'analytics', label: 'Detection Analytics', icon: RefreshCw }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-amber-500/20 text-amber-400'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* PII Patterns Tab */}
      {activeTab === 'patterns' && (
        <div>
          {/* Search and Filter */}
          <div className="flex items-center space-x-4 mb-6">
            <div className="flex-1 relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search patterns..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-amber-500"
              />
            </div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
            >
              <option value="all">All Categories</option>
              <option value="personal">Personal</option>
              <option value="medical">Medical</option>
              <option value="legal">Legal</option>
              <option value="financial">Financial</option>
            </select>
            <button className="px-4 py-2 bg-gray-700/50 text-gray-400 hover:text-white rounded-lg transition-colors flex items-center space-x-2">
              <Filter className="w-4 h-4" />
              <span>Filter</span>
            </button>
          </div>

          {/* Pattern Statistics */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="dashboard-card p-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
                  <Settings className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">{patterns.length}</div>
                  <div className="text-gray-400 text-sm">Total Patterns</div>
                </div>
              </div>
            </div>
            <div className="dashboard-card p-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-green-500/20 text-green-400 rounded-lg">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">
                    {patterns.filter(p => p.enabled).length}
                  </div>
                  <div className="text-gray-400 text-sm">Active Patterns</div>
                </div>
              </div>
            </div>
            <div className="dashboard-card p-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-500/20 text-purple-400 rounded-lg">
                  <Edit className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">
                    {patterns.filter(p => p.custom).length}
                  </div>
                  <div className="text-gray-400 text-sm">Custom Patterns</div>
                </div>
              </div>
            </div>
            <div className="dashboard-card p-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-red-500/20 text-red-400 rounded-lg">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">
                    {patterns.filter(p => p.risk_level === 'high').length}
                  </div>
                  <div className="text-gray-400 text-sm">High Risk</div>
                </div>
              </div>
            </div>
          </div>

          {/* Pattern List */}
          <div>
            {filteredPatterns.map(pattern => (
              <PatternCard key={pattern.id} pattern={pattern} />
            ))}
          </div>
        </div>
      )}

      {/* Compliance Profiles Tab */}
      {activeTab === 'compliance' && (
        <div>
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Compliance Framework Profiles</h2>
            <p className="text-gray-400">Manage compliance frameworks and their associated PII requirements</p>
          </div>
          
          {complianceProfiles.map(profile => (
            <ComplianceProfileCard key={profile.id} profile={profile} />
          ))}
        </div>
      )}

      {/* Custom Rules Tab */}
      {activeTab === 'custom' && (
        <div className="text-center py-12">
          <div className="p-4 bg-gray-800/30 rounded-lg inline-block">
            <Edit className="w-8 h-8 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Custom Rules Editor</h3>
            <p className="text-gray-400 mb-4">Create organization-specific PII detection rules</p>
            <button className="px-6 py-2 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors">
              Create Custom Rule
            </button>
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="text-center py-12">
          <div className="p-4 bg-gray-800/30 rounded-lg inline-block">
            <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Detection Analytics</h3>
            <p className="text-gray-400 mb-4">View PII detection statistics and trends</p>
            <button className="px-6 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors">
              View Analytics
            </button>
          </div>
        </div>
      )}
      
      {/* Pattern Testing Modal */}
      {testingPattern && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Test Pattern: {testingPattern.name}</h2>
              <button 
                onClick={() => setTestingPattern(null)}
                className="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            
            <div className="mb-4">
              <label className="block text-gray-400 text-sm mb-2">Pattern:</label>
              <code className="block bg-gray-900 p-3 rounded text-green-400 font-mono text-sm">
                {testingPattern.pattern}
              </code>
            </div>
            
            <div className="mb-4">
              <label className="block text-gray-400 text-sm mb-2">Test Text:</label>
              <textarea
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400"
                rows={6}
                placeholder="Enter text to test the pattern against..."
              />
            </div>
            
            <div className="flex items-center space-x-3 mb-4">
              <button
                onClick={() => handleTestPattern(testingPattern)}
                className="px-4 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors"
              >
                Test Pattern
              </button>
              <button
                onClick={() => setTestText('This is a sample SSN: 123-45-6789 and email: user@example.com and phone: (555) 123-4567')}
                className="px-4 py-2 bg-gray-600/50 text-gray-300 hover:bg-gray-600 rounded-lg transition-colors text-sm"
              >
                Use Sample Text
              </button>
            </div>
            
            {testResults && (
              <div className="border-t border-gray-700 pt-4">
                <h3 className="text-lg font-semibold text-white mb-3">
                  Results: {testResults.count} matches found
                </h3>
                {testResults.matches.length > 0 ? (
                  <div className="space-y-2">
                    {testResults.matches.map((match, index) => (
                      <div key={index} className="bg-gray-700/50 p-3 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-white font-mono">"{match.match}"</span>
                          <span className="text-gray-400 text-sm">Position: {match.start}-{match.end}</span>
                        </div>
                        <div className="text-gray-400 text-sm">
                          Context: ...{match.context}...
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400">No matches found.</p>
                )}
                {!testResults.pattern_valid && (
                  <div className="mt-3 p-3 bg-red-500/20 border border-red-500/30 rounded">
                    <p className="text-red-400">Pattern Error: {testResults.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Add Pattern Dialog */}
      {showAddPatternDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Add Custom Pattern</h2>
              <button 
                onClick={() => setShowAddPatternDialog(false)}
                className="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            
            <div className="text-center py-8">
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg inline-block">
                <Plus className="w-8 h-8 text-amber-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-white mb-2">Feature Coming Soon</h3>
                <p className="text-gray-400 mb-4">Custom pattern creation is under development.</p>
                <p className="text-gray-400 text-sm">For now, use the Import feature to add patterns from JSON files.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Settings Framework Modal */}
      {showSettingsDialog && selectedProfileId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg w-full max-w-7xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h2 className="text-xl font-bold text-white">Advanced Profile Settings</h2>
              <button 
                onClick={() => setShowSettingsDialog(false)}
                className="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
              >
                ×
              </button>
            </div>
            <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
              <PIISettingsFramework 
                profileId={selectedProfileId}
                onSave={handleSettingsSave}
                onClose={() => setShowSettingsDialog(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PIIConfigurationManager;