import React, { useState, useEffect } from 'react';
import {
  Bot,
  Plus,
  Edit3,
  Trash2,
  Key,
  Eye,
  EyeOff,
  MessageCircle,
  Users,
  TrendingUp,
  Settings,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  RefreshCw,
  Copy,
  ExternalLink,
  Activity,
  Globe,
  TestTube,
  Shield
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ResponsiveModal, { ResponsiveModalFooter, ResponsiveModalButton } from '../common/ResponsiveModal';
import { resilientGet, resilientPost, resilientPut, resilientDelete } from '../../utils/resilientApiClient';

const NectarBotManager = () => {
  const navigate = useNavigate();
  const [bots, setBots] = useState([]);
  const [handoffs, setHandoffs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('bots');
  const [selectedBot, setSelectedBot] = useState(null);
  const [showBotModal, setShowBotModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [showHandoffModal, setShowHandoffModal] = useState(false);
  const [editingBot, setEditingBot] = useState(null);
  const [selectedHandoff, setSelectedHandoff] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [apiKeyVisible, setApiKeyVisible] = useState({});

  useEffect(() => {
    loadBots();
    loadHandoffs();
    loadAnalytics();
  }, []);

  const loadBots = async () => {
    try {
      setLoading(true);
      const data = await resilientGet('/api/nectar-bots');
      setBots(data.bots || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load bots:', err);
      setError('Failed to load Nectar Bots');
    } finally {
      setLoading(false);
    }
  };

  const loadHandoffs = async () => {
    try {
      const data = await resilientGet('/api/nectar-bots/handoffs');
      setHandoffs(data.handoffs || []);
    } catch (err) {
      console.error('Failed to load handoffs:', err);
    }
  };

  const loadAnalytics = async () => {
    try {
      const data = await resilientGet('/api/nectar-bots/analytics/overview');
      setAnalytics(data.overview || {});
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  };

  const handleCreateBot = () => {
    setEditingBot({
      name: '',
      description: '',
      honey_jar_ids: [],
      system_prompt: 'You are a helpful AI assistant.',
      max_conversation_length: 20,
      confidence_threshold: 0.7,
      rate_limit_per_hour: 100,
      rate_limit_per_day: 1000,
      is_public: false,
      handoff_enabled: true,
      handoff_keywords: ['help', 'human', 'support', 'escalate'],
      handoff_confidence_threshold: 0.6
    });
    setShowBotModal(true);
  };

  const handleEditBot = (bot) => {
    setEditingBot({ ...bot });
    setShowBotModal(true);
  };

  const handleSaveBot = async () => {
    try {
      setLoading(true);
      
      const botData = {
        name: editingBot.name,
        description: editingBot.description,
        honey_jar_ids: editingBot.honey_jar_ids,
        system_prompt: editingBot.system_prompt,
        max_conversation_length: parseInt(editingBot.max_conversation_length),
        confidence_threshold: parseFloat(editingBot.confidence_threshold),
        rate_limit_per_hour: parseInt(editingBot.rate_limit_per_hour),
        rate_limit_per_day: parseInt(editingBot.rate_limit_per_day),
        is_public: editingBot.is_public,
        handoff_enabled: editingBot.handoff_enabled,
        handoff_keywords: Array.isArray(editingBot.handoff_keywords) 
          ? editingBot.handoff_keywords 
          : editingBot.handoff_keywords.split(',').map(k => k.trim()),
        handoff_confidence_threshold: parseFloat(editingBot.handoff_confidence_threshold)
      };

      if (editingBot.id) {
        await resilientPut(`/api/nectar-bots/${editingBot.id}`, botData);
      } else {
        await resilientPost('/api/nectar-bots', botData);
      }

      setShowBotModal(false);
      setEditingBot(null);
      await loadBots();
      
    } catch (err) {
      console.error('Failed to save bot:', err);
      setError('Failed to save bot');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBot = async () => {
    try {
      setLoading(true);
      await resilientDelete(`/api/nectar-bots/${selectedBot.id}`);
      setShowDeleteModal(false);
      setSelectedBot(null);
      await loadBots();
    } catch (err) {
      console.error('Failed to delete bot:', err);
      setError('Failed to delete bot');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateApiKey = async (bot) => {
    try {
      setLoading(true);
      const response = await resilientPost(`/api/nectar-bots/${bot.id}/regenerate-api-key`);
      
      // Update the bot in the list with new API key
      setBots(bots.map(b => 
        b.id === bot.id 
          ? { ...b, api_key: response.api_key }
          : b
      ));
      
      alert('API key regenerated successfully!');
      
    } catch (err) {
      console.error('Failed to regenerate API key:', err);
      setError('Failed to regenerate API key');
    } finally {
      setLoading(false);
    }
  };

  const handleAssignHandoff = async (handoffId) => {
    try {
      await resilientPost(`/api/nectar-bots/handoffs/${handoffId}/assign`);
      await loadHandoffs();
    } catch (err) {
      console.error('Failed to assign handoff:', err);
      setError('Failed to assign handoff');
    }
  };

  const handleResolveHandoff = async (handoffId, notes = '') => {
    try {
      await resilientPost(`/api/nectar-bots/handoffs/${handoffId}/resolve`, {
        resolution_notes: notes
      });
      setShowHandoffModal(false);
      setSelectedHandoff(null);
      await loadHandoffs();
    } catch (err) {
      console.error('Failed to resolve handoff:', err);
      setError('Failed to resolve handoff');
    }
  };

  const copyApiKey = (apiKey) => {
    navigator.clipboard.writeText(apiKey);
    alert('API key copied to clipboard!');
  };

  const copyPublicUrl = (bot) => {
    const fullUrl = `${window.location.origin}${bot.public_url}`;
    navigator.clipboard.writeText(fullUrl);
    alert('Public URL copied to clipboard!');
  };

  const openPublicBot = (bot) => {
    window.open(bot.public_url, '_blank');
  };

  const handleTestBot = (bot) => {
    if (bot.is_public) {
      // Open public bot in new tab
      window.open(bot.public_url, '_blank');
    } else {
      // Navigate to BeeChat with bot pre-selected via URL parameter
      navigate(`/dashboard/bee-chat?botId=${bot.id}&botName=${encodeURIComponent(bot.name)}`);
    }
  };

  const toggleApiKeyVisibility = (botId) => {
    setApiKeyVisible(prev => ({
      ...prev,
      [botId]: !prev[botId]
    }));
  };

  const getBotStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-green-400';
      case 'inactive': return 'text-gray-400';
      case 'maintenance': return 'text-yellow-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getHandoffUrgencyColor = (urgency) => {
    switch (urgency) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateApiKey = (apiKey) => {
    if (!apiKey) return '';
    return `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 8)}`;
  };

  return (
    <div className="space-y-6">
      {/* Header - Create Bot Button */}
      <div className="flex items-center justify-end">
        <button
          onClick={handleCreateBot}
          className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-black rounded-xl hover:bg-yellow-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create New Bot
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded-xl text-red-300">
          {error}
        </div>
      )}

      {/* Analytics Overview */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Bots</p>
                <p className="text-2xl font-bold text-white">{analytics.total_bots || 0}</p>
              </div>
              <Bot className="w-8 h-8 text-yellow-400" />
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Active Conversations</p>
                <p className="text-2xl font-bold text-white">{analytics.unique_conversations || 0}</p>
              </div>
              <MessageCircle className="w-8 h-8 text-blue-400" />
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Handoffs</p>
                <p className="text-2xl font-bold text-white">{analytics.total_handoffs || 0}</p>
              </div>
              <Users className="w-8 h-8 text-purple-400" />
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Resolution Rate</p>
                <p className="text-2xl font-bold text-white">
                  {Math.round(analytics.handoff_resolution_rate || 0)}%
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-400" />
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-4 border-b border-gray-600">
        <button
          onClick={() => setActiveTab('bots')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'bots'
              ? 'text-yellow-400 border-yellow-400'
              : 'text-gray-400 border-transparent hover:text-gray-200'
          }`}
        >
          <Bot className="w-4 h-4" />
          Bots ({bots.length})
        </button>
        <button
          onClick={() => setActiveTab('handoffs')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'handoffs'
              ? 'text-yellow-400 border-yellow-400'
              : 'text-gray-400 border-transparent hover:text-gray-200'
          }`}
        >
          <Users className="w-4 h-4" />
          Handoffs ({handoffs.filter(h => h.status === 'pending').length} pending)
        </button>
      </div>

      {/* Content */}
      {activeTab === 'bots' && (
        <div className="space-y-4">
          {loading && bots.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-yellow-500 mr-2" />
              <span className="text-gray-400">Loading bots...</span>
            </div>
          ) : bots.length === 0 ? (
            <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-xl">
              <Bot className="w-16 h-16 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">No Nectar Bots Yet</h3>
              <p className="text-gray-500 mb-4">
                Create your first Nectar Bot to start serving AI-powered conversations.
              </p>
              <button
                onClick={handleCreateBot}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-black rounded-xl hover:bg-yellow-400 transition-colors mx-auto"
              >
                <Plus className="w-4 h-4" />
                Create Your First Bot
              </button>
            </div>
          ) : (
            bots.map((bot) => (
              <div key={bot.id} className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-lg">
                        <Bot className="w-6 h-6 text-yellow-400" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">{bot.name}</h3>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm ${getBotStatusColor(bot.status)}`}>
                            {bot.status.charAt(0).toUpperCase() + bot.status.slice(1)}
                          </span>
                          {bot.is_public && (
                            <span className="px-2 py-1 text-xs bg-blue-600 text-white rounded">
                              Public
                            </span>
                          )}
                          {bot.handoff_enabled && (
                            <span className="px-2 py-1 text-xs bg-green-600 text-white rounded">
                              Handoff Enabled
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {bot.description && (
                      <p className="text-slate-300 text-sm mb-3">{bot.description}</p>
                    )}

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500">Conversations:</span>
                        <p className="text-slate-300">{bot.total_conversations || 0}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Messages:</span>
                        <p className="text-slate-300">{bot.total_messages || 0}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Handoffs:</span>
                        <p className="text-slate-300">{bot.total_handoffs || 0}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Avg Confidence:</span>
                        <p className="text-slate-300">{Math.round((bot.average_confidence || 0) * 100)}%</p>
                      </div>
                    </div>

                    {/* API Key Display */}
                    <div className="mt-4 p-3 sting-glass-subtle border border-slate-600 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <span className="text-slate-500 text-xs">API Key:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <code className="text-sm text-slate-300 font-mono">
                              {apiKeyVisible[bot.id] ? bot.api_key : truncateApiKey(bot.api_key)}
                            </code>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <button
                            onClick={() => toggleApiKeyVisibility(bot.id)}
                            className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
                            title={apiKeyVisible[bot.id] ? "Hide API key" : "Show API key"}
                          >
                            {apiKeyVisible[bot.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                          <button
                            onClick={() => copyApiKey(bot.api_key)}
                            className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
                            title="Copy API key"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Public URL Section - Show for public bots */}
                    {bot.is_public && bot.public_url && (
                      <div className="mt-4 p-4 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-700/30 rounded-lg">
                        <div className="flex items-center gap-2 mb-3">
                          <Globe className="w-4 h-4 text-blue-400" />
                          <span className="text-slate-300 text-sm font-semibold">Public URL</span>
                          <span className="px-2 py-0.5 bg-green-600/20 text-green-400 text-xs rounded-full border border-green-600/30">
                            Public
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mb-3">
                          <code className="flex-1 text-sm text-blue-300 font-mono bg-black/20 px-3 py-1.5 rounded truncate">
                            {window.location.origin}{bot.public_url}
                          </code>
                          <button
                            onClick={() => copyPublicUrl(bot)}
                            className="p-1.5 text-slate-400 hover:text-blue-400 transition-colors"
                            title="Copy public URL"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openPublicBot(bot)}
                            className="p-1.5 text-slate-400 hover:text-blue-400 transition-colors"
                            title="Open in new tab"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        </div>
                        {/* Prominent Test Button for Public Bots */}
                        <button
                          onClick={() => handleTestBot(bot)}
                          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white rounded-lg transition-all shadow-lg"
                        >
                          <TestTube className="w-4 h-4" />
                          <span className="font-medium">Test Public Bot</span>
                        </button>
                        <p className="text-xs text-slate-500 mt-2">
                          💡 This bot is publicly accessible. Anyone with this URL can chat with it!
                        </p>
                      </div>
                    )}

                    {/* Private Bot Test Section */}
                    {!bot.is_public && (
                      <div className="mt-4 p-4 bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-700/30 rounded-lg">
                        <div className="flex items-center gap-2 mb-3">
                          <Shield className="w-4 h-4 text-purple-400" />
                          <span className="text-slate-300 text-sm font-semibold">Private Bot</span>
                          <span className="px-2 py-0.5 bg-purple-600/20 text-purple-400 text-xs rounded-full border border-purple-600/30">
                            Private
                          </span>
                        </div>
                        <button
                          onClick={() => handleTestBot(bot)}
                          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg transition-all shadow-lg"
                        >
                          <TestTube className="w-4 h-4" />
                          <span className="font-medium">Test in Bee Chat Sandbox</span>
                        </button>
                        <p className="text-xs text-slate-500 mt-2">
                          🔒 Test this bot in a private sandbox environment within Bee Chat
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleEditBot(bot)}
                      className="p-2 text-slate-400 hover:text-yellow-400 transition-colors"
                      title="Edit bot"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleRegenerateApiKey(bot)}
                      className="p-2 text-slate-400 hover:text-blue-400 transition-colors"
                      title="Regenerate API key"
                    >
                      <Key className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedBot(bot);
                        setShowDeleteModal(true);
                      }}
                      className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete bot"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'handoffs' && (
        <div className="space-y-4">
          {handoffs.length === 0 ? (
            <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-xl">
              <Users className="w-16 h-16 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">No Handoffs</h3>
              <p className="text-gray-500">
                Handoff requests from your Nectar Bots will appear here.
              </p>
            </div>
          ) : (
            handoffs.map((handoff) => (
              <div key={handoff.id} className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`w-3 h-3 rounded-full ${getHandoffUrgencyColor(handoff.urgency)}`}></div>
                      <h3 className="text-lg font-semibold text-white">
                        {handoff.bot_name} - Handoff Request
                      </h3>
                      <span className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">
                        {handoff.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                      <div>
                        <span className="text-slate-500">Reason:</span>
                        <p className="text-slate-300">{handoff.reason.replace('_', ' ')}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Urgency:</span>
                        <p className="text-slate-300">{handoff.urgency}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Created:</span>
                        <p className="text-slate-300">{formatDate(handoff.created_at)}</p>
                      </div>
                      <div>
                        <span className="text-slate-500">Assigned To:</span>
                        <p className="text-slate-300">{handoff.assigned_to || 'Unassigned'}</p>
                      </div>
                    </div>

                    {handoff.trigger_message && (
                      <div className="p-3 sting-glass-subtle border border-slate-600 rounded-lg">
                        <span className="text-slate-500 text-xs">Trigger Message:</span>
                        <p className="text-slate-300 text-sm mt-1">{handoff.trigger_message}</p>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 ml-4">
                    {handoff.status === 'pending' && (
                      <button
                        onClick={() => handleAssignHandoff(handoff.id)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                      >
                        <Users className="w-4 h-4" />
                        Assign to Me
                      </button>
                    )}
                    {(handoff.status === 'pending' || handoff.status === 'in_progress') && (
                      <button
                        onClick={() => {
                          setSelectedHandoff(handoff);
                          setShowHandoffModal(true);
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Bot Edit/Create Modal */}
      <ResponsiveModal
        isOpen={showBotModal}
        onClose={() => {
          setShowBotModal(false);
          setEditingBot(null);
        }}
        title={editingBot?.id ? 'Edit Nectar Bot' : 'Create New Nectar Bot'}
        size="lg"
      >
        {editingBot && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Bot Name *
                </label>
                <input
                  type="text"
                  value={editingBot.name}
                  onChange={(e) => setEditingBot({ ...editingBot, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                  placeholder="My Awesome Bot"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Status
                </label>
                <select
                  value={editingBot.status || 'active'}
                  onChange={(e) => setEditingBot({ ...editingBot, status: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="maintenance">Maintenance</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={editingBot.description}
                onChange={(e) => setEditingBot({ ...editingBot, description: e.target.value })}
                rows="3"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                placeholder="Describe what this bot does..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                System Prompt
              </label>
              <textarea
                value={editingBot.system_prompt}
                onChange={(e) => setEditingBot({ ...editingBot, system_prompt: e.target.value })}
                rows="4"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                placeholder="You are a helpful AI assistant..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Max Conversation Length
                </label>
                <input
                  type="number"
                  value={editingBot.max_conversation_length}
                  onChange={(e) => setEditingBot({ ...editingBot, max_conversation_length: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                  min="1"
                  max="100"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Confidence Threshold
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={editingBot.confidence_threshold}
                  onChange={(e) => setEditingBot({ ...editingBot, confidence_threshold: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                  min="0"
                  max="1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Rate Limit (per hour)
                </label>
                <input
                  type="number"
                  value={editingBot.rate_limit_per_hour}
                  onChange={(e) => setEditingBot({ ...editingBot, rate_limit_per_hour: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                  min="1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Rate Limit (per day)
                </label>
                <input
                  type="number"
                  value={editingBot.rate_limit_per_day}
                  onChange={(e) => setEditingBot({ ...editingBot, rate_limit_per_day: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                  min="1"
                />
              </div>
            </div>

            <div className="border-t border-gray-600 pt-4">
              <h4 className="text-lg font-medium text-white mb-4">Handoff Configuration</h4>
              
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="handoff_enabled"
                    checked={editingBot.handoff_enabled}
                    onChange={(e) => setEditingBot({ ...editingBot, handoff_enabled: e.target.checked })}
                    className="mr-2"
                  />
                  <label htmlFor="handoff_enabled" className="text-sm text-gray-300">
                    Enable handoff to human agents
                  </label>
                </div>

                {editingBot.handoff_enabled && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Handoff Keywords (comma-separated)
                      </label>
                      <input
                        type="text"
                        value={Array.isArray(editingBot.handoff_keywords) 
                          ? editingBot.handoff_keywords.join(', ') 
                          : editingBot.handoff_keywords}
                        onChange={(e) => setEditingBot({ ...editingBot, handoff_keywords: e.target.value })}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                        placeholder="help, human, support, escalate"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Handoff Confidence Threshold
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={editingBot.handoff_confidence_threshold}
                        onChange={(e) => setEditingBot({ ...editingBot, handoff_confidence_threshold: parseFloat(e.target.value) })}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                        min="0"
                        max="1"
                      />
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_public"
                checked={editingBot.is_public}
                onChange={(e) => setEditingBot({ ...editingBot, is_public: e.target.checked })}
                className="mr-2"
              />
              <label htmlFor="is_public" className="text-sm text-gray-300">
                Make this bot publicly accessible
              </label>
            </div>
          </div>
        )}

        <ResponsiveModalFooter>
          <ResponsiveModalButton
            onClick={() => {
              setShowBotModal(false);
              setEditingBot(null);
            }}
            variant="cancel"
          >
            Cancel
          </ResponsiveModalButton>
          <ResponsiveModalButton
            onClick={handleSaveBot}
            variant="primary"
            disabled={!editingBot?.name?.trim() || loading}
          >
            {editingBot?.id ? 'Update Bot' : 'Create Bot'}
          </ResponsiveModalButton>
        </ResponsiveModalFooter>
      </ResponsiveModal>

      {/* Delete Confirmation Modal */}
      <ResponsiveModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedBot(null);
        }}
        title="Delete Nectar Bot"
        size="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-red-900/20 border border-red-700 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <p className="text-sm text-red-300">
                Are you sure you want to delete "{selectedBot?.name}"?
              </p>
              <p className="text-xs text-red-400 mt-1">
                This action cannot be undone. All conversation history and analytics will be permanently lost.
              </p>
            </div>
          </div>
        </div>

        <ResponsiveModalFooter>
          <ResponsiveModalButton
            onClick={() => {
              setShowDeleteModal(false);
              setSelectedBot(null);
            }}
            variant="cancel"
          >
            Cancel
          </ResponsiveModalButton>
          <ResponsiveModalButton
            onClick={handleDeleteBot}
            variant="danger"
            disabled={loading}
          >
            Delete Bot
          </ResponsiveModalButton>
        </ResponsiveModalFooter>
      </ResponsiveModal>

      {/* Handoff Resolution Modal */}
      <ResponsiveModal
        isOpen={showHandoffModal}
        onClose={() => {
          setShowHandoffModal(false);
          setSelectedHandoff(null);
        }}
        title="Resolve Handoff"
        size="lg"
      >
        {selectedHandoff && (
          <div className="space-y-4">
            <div className="p-4 sting-glass-subtle border border-slate-600 rounded-xl">
              <h4 className="text-white font-medium mb-2">Handoff Details</h4>
              <div className="space-y-2 text-sm">
                <p><span className="text-slate-400">Bot:</span> <span className="text-white">{selectedHandoff.bot_name}</span></p>
                <p><span className="text-slate-400">Reason:</span> <span className="text-white">{selectedHandoff.reason.replace('_', ' ')}</span></p>
                <p><span className="text-slate-400">Created:</span> <span className="text-white">{formatDate(selectedHandoff.created_at)}</span></p>
              </div>
            </div>

            {selectedHandoff.trigger_message && (
              <div className="p-4 sting-glass-subtle border border-slate-600 rounded-xl">
                <h4 className="text-white font-medium mb-2">User Message</h4>
                <p className="text-slate-300 text-sm">{selectedHandoff.trigger_message}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Resolution Notes (optional)
              </label>
              <textarea
                rows="4"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-xl focus:ring-2 focus:ring-yellow-400"
                placeholder="Add notes about how this handoff was resolved..."
                onChange={(e) => setSelectedHandoff({ ...selectedHandoff, resolution_notes: e.target.value })}
              />
            </div>
          </div>
        )}

        <ResponsiveModalFooter>
          <ResponsiveModalButton
            onClick={() => {
              setShowHandoffModal(false);
              setSelectedHandoff(null);
            }}
            variant="cancel"
          >
            Cancel
          </ResponsiveModalButton>
          <ResponsiveModalButton
            onClick={() => handleResolveHandoff(selectedHandoff?.id, selectedHandoff?.resolution_notes)}
            variant="primary"
          >
            Mark as Resolved
          </ResponsiveModalButton>
        </ResponsiveModalFooter>
      </ResponsiveModal>
    </div>
  );
};

export default NectarBotManager;