import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Users,
  FileText,
  Shield,
  Check,
  X,
  Eye,
  RefreshCw,
  UserPlus,
  Clock,
  AlertCircle,
  Search,
  Navigation,
  Settings,
  Database,
  Bot,
  Crown,
  Activity,
  TrendingUp,
  Server,
  Zap,
  Sparkles
} from 'lucide-react';
import { honeyJarApi } from '../../services/knowledgeApi';
import ResponsiveModal, { ResponsiveModalFooter, ResponsiveModalButton } from '../common/ResponsiveModal';
import NavigationSettings from './NavigationSettings';
import PIIConfigurationManager from './PIIConfigurationManager';
import AdminRecovery from './AdminRecovery';
import DemoDataManager from './DemoDataManager';
import NectarBotManager from './NectarBotManager';
import { resilientGet, resilientPost, fallbackGenerators } from '../../utils/resilientApiClient';
import ScrollToTopButton from '../common/ScrollToTopButton';

const AdminPanel = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get tab from URL params, default to 'pending-docs'
  const tabFromUrl = searchParams.get('tab') || 'pending-docs';
  const [activeTab, setActiveTab] = useState(tabFromUrl);
  const [pendingDocuments, setPendingDocuments] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedHoneyJar, setSelectedHoneyJar] = useState(null);
  const [honeyJars, setHoneyJars] = useState([]);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingDoc, setRejectingDoc] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  // Sync tab state when URL changes
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') || 'pending-docs';
    setActiveTab(tabFromUrl);
  }, [searchParams]);

  useEffect(() => {
    loadHoneyJars();
  }, []);

  useEffect(() => {
    if (selectedHoneyJar) {
      loadPendingDocuments(selectedHoneyJar);
    }
  }, [selectedHoneyJar]);

  const loadHoneyJars = async () => {
    try {
      setLoading(true);
      const response = await honeyJarApi.getHoneyJars();
      setHoneyJars(response.items || []);
      // Select first honey jar by default
      if (response.items?.length > 0) {
        setSelectedHoneyJar(response.items[0].id);
      }
    } catch (err) {
      console.error('Failed to load honey jars:', err);
      setError('Failed to load honey jars');
    } finally {
      setLoading(false);
    }
  };

  const loadPendingDocuments = async (honeyJarId) => {
    try {
      setLoading(true);
      const data = await resilientGet(
        `/api/knowledge/honey-jars/${honeyJarId}/pending-documents`,
        fallbackGenerators.adminPendingDocs(),
        { timeout: 5000 }
      );
      
      setPendingDocuments(data.documents || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load pending documents:', err);
      setError('Failed to load pending documents');
      setPendingDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveDocument = async (honeyJarId, documentId, documentName) => {
    try {
      await resilientPost(
        `/api/knowledge/honey-jars/${honeyJarId}/documents/${documentId}/approve`,
        null,
        { timeout: 8000 } // Longer timeout for approval operations
      );
      
      // Refresh pending documents
      loadPendingDocuments(honeyJarId);
      
      // Show success message
      alert(`Document "${documentName}" approved successfully!`);
    } catch (err) {
      console.error('Failed to approve document:', err);
      alert('Failed to approve document. Please check your connection and try again.');
    }
  };

  const handleRejectDocument = async () => {
    if (!rejectingDoc) return;
    
    try {
      const formData = new FormData();
      formData.append('reason', rejectReason);
      
      const response = await fetch(
        `/api/knowledge/honey-jars/${rejectingDoc.honeyJarId}/documents/${rejectingDoc.documentId}/reject`, 
        {
          method: 'POST',
          credentials: 'include',
          body: formData
        }
      );
      
      if (!response.ok) {
        throw new Error('Failed to reject document');
      }
      
      // Refresh pending documents
      loadPendingDocuments(rejectingDoc.honeyJarId);
      
      // Close modal and reset
      setShowRejectModal(false);
      setRejectingDoc(null);
      setRejectReason('');
      
      // Show success message
      alert(`Document "${rejectingDoc.documentName}" rejected`);
    } catch (err) {
      console.error('Failed to reject document:', err);
      alert('Failed to reject document');
    }
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleString();
  };

  const formatFileSize = (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Helper function to change tabs and update URL
  const changeTab = (tabName) => {
    setSearchParams({ tab: tabName });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
        {/* Modern Header with Stats */}
        <div className="mb-8">
          <div className="bg-gradient-to-r from-amber-500/20 to-yellow-500/20 rounded-3xl p-8 border border-amber-500/30 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Crown className="w-10 h-10 text-amber-400" />
                  <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-1 -right-1 animate-pulse" />
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-white mb-1">Admin Control Center</h1>
                  <p className="text-amber-200/80">Complete platform management and oversight</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="bg-green-500/20 border border-green-400/30 rounded-full px-3 py-1 flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-green-300 text-sm font-medium">System Online</span>
                </div>
              </div>
            </div>
            
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                <div className="flex items-center gap-3">
                  <div className="bg-purple-500/20 p-2 rounded-xl">
                    <Users className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{users.length}</p>
                    <p className="text-xs text-gray-300">Active Users</p>
                  </div>
                </div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                <div className="flex items-center gap-3">
                  <div className="bg-amber-500/20 p-2 rounded-xl">
                    <FileText className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{pendingDocuments.length}</p>
                    <p className="text-xs text-gray-300">Pending Reviews</p>
                  </div>
                </div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                <div className="flex items-center gap-3">
                  <div className="bg-purple-500/20 p-2 rounded-xl">
                    <Database className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{honeyJars.length}</p>
                    <p className="text-xs text-gray-300">Honey Jars</p>
                  </div>
                </div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                <div className="flex items-center gap-3">
                  <div className="bg-green-500/20 p-2 rounded-xl">
                    <Activity className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">98%</p>
                    <p className="text-xs text-gray-300">System Health</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modern Tab Navigation */}
        <div className="mb-8">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-2 border border-slate-700/50">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => changeTab('pending-docs')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'pending-docs'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-lg shadow-amber-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <FileText className="w-4 h-4" />
                Pending Documents
                {pendingDocuments.length > 0 && (
                  <span className="bg-amber-500 text-black text-xs font-bold px-2 py-0.5 rounded-full ml-1">
                    {pendingDocuments.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => changeTab('users')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'users'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30 shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Users className="w-4 h-4" />
                User Management
              </button>
              <button
                onClick={() => changeTab('navigation')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'navigation'
                    ? 'bg-green-500/20 text-green-300 border border-green-500/30 shadow-lg shadow-green-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Navigation className="w-4 h-4" />
                Navigation
              </button>
              <button
                onClick={() => changeTab('pii-config')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'pii-config'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30 shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Settings className="w-4 h-4" />
                PII Configuration
              </button>

              <button
                onClick={() => changeTab('recovery')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'recovery'
                    ? 'bg-red-500/20 text-red-300 border border-red-500/30 shadow-lg shadow-red-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Shield className="w-4 h-4" />
                Admin Recovery
              </button>
              <button
                onClick={() => changeTab('demo-data')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'demo-data'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-lg shadow-indigo-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Database className="w-4 h-4" />
                Demo Data
              </button>
              <button
                onClick={() => changeTab('nectar-bots')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  activeTab === 'nectar-bots'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-lg shadow-cyan-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Bot className="w-4 h-4" />
                Nectar Bots
              </button>
            </div>
          </div>
        </div>

        {/* Enhanced Content Area */}
        <div className="bg-slate-800/30 backdrop-blur-sm rounded-3xl p-8 border border-slate-700/50">
          {activeTab === 'pending-docs' && (
            <div>
              {/* Modern Honey Jar Selector */}
              <div className="mb-8">
                <div className="bg-gradient-to-r from-amber-500/10 to-yellow-500/10 rounded-2xl p-6 border border-amber-500/20">
                  <label className="flex items-center gap-2 text-lg font-semibold text-amber-300 mb-4">
                    <Database className="w-5 h-5" />
                    Select Honey Jar for Review
                  </label>
                  <select
                    className="w-full px-4 py-3 bg-slate-700/80 border border-slate-600/50 text-white rounded-xl focus:ring-2 focus:ring-amber-400 focus:border-transparent backdrop-blur-sm"
                    value={selectedHoneyJar || ''}
                    onChange={(e) => setSelectedHoneyJar(e.target.value)}
                  >
                    <option value="">Choose a honey jar to review pending documents...</option>
                    {honeyJars.map(jar => (
                      <option key={jar.id} value={jar.id}>
                        🍯 {jar.name} ({jar.type})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Enhanced Pending Documents List */}
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="text-center">
                    <div className="relative">
                      <RefreshCw className="w-8 h-8 animate-spin text-amber-400 mx-auto mb-4" />
                      <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-1 -right-1 animate-pulse" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">Loading Documents</h3>
                    <p className="text-gray-400">Fetching pending documents for review...</p>
                  </div>
                </div>
              ) : pendingDocuments.length === 0 ? (
                <div className="text-center py-16 bg-slate-700/30 rounded-2xl border border-slate-600/30">
                  <div className="relative inline-block">
                    <Clock className="w-20 h-20 text-slate-500 mx-auto mb-4" />
                    <div className="absolute -top-2 -right-2 bg-green-500/20 border border-green-400/30 rounded-full p-1">
                      <Check className="w-4 h-4 text-green-400" />
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">All Clear!</h3>
                  <p className="text-gray-400 max-w-md mx-auto">
                    {selectedHoneyJar ? 'No documents are waiting for approval in this honey jar. Great job staying on top of reviews!' : 'Select a honey jar above to view and manage pending document approvals.'}
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {pendingDocuments.map(doc => (
                    <div key={doc.id} className="group bg-gradient-to-r from-slate-700/50 to-slate-600/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-600/50 hover:border-amber-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-amber-500/10">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="bg-amber-500/20 p-2 rounded-xl">
                              <FileText className="w-5 h-5 text-amber-400" />
                            </div>
                            <div>
                              <h3 className="text-xl font-semibold text-white group-hover:text-amber-200 transition-colors">{doc.filename}</h3>
                              <p className="text-sm text-amber-400/70">Awaiting review and approval</p>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-slate-800/40 rounded-xl p-3">
                              <span className="text-gray-400 text-xs font-medium block mb-1">Uploaded by</span>
                              <p className="text-white font-medium">{doc.uploaded_by}</p>
                            </div>
                            <div className="bg-slate-800/40 rounded-xl p-3">
                              <span className="text-gray-400 text-xs font-medium block mb-1">Upload date</span>
                              <p className="text-white font-medium">{formatDate(doc.upload_date)}</p>
                            </div>
                            <div className="bg-slate-800/40 rounded-xl p-3">
                              <span className="text-gray-400 text-xs font-medium block mb-1">File size</span>
                              <p className="text-white font-medium">{formatFileSize(doc.size_bytes)}</p>
                            </div>
                            <div className="bg-slate-800/40 rounded-xl p-3">
                              <span className="text-gray-400 text-xs font-medium block mb-1">Type</span>
                              <p className="text-white font-medium">{doc.content_type || 'Unknown'}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col gap-3 ml-6">
                          <button
                            onClick={() => handleApproveDocument(selectedHoneyJar, doc.id, doc.filename)}
                            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-green-500 text-white font-semibold rounded-xl hover:from-green-500 hover:to-green-400 transition-all duration-200 shadow-lg shadow-green-500/20 hover:shadow-green-500/40"
                          >
                            <Check className="w-4 h-4" />
                            Approve
                          </button>
                          <button
                            onClick={() => {
                              setRejectingDoc({
                                honeyJarId: selectedHoneyJar,
                                documentId: doc.id,
                                documentName: doc.filename
                              });
                              setShowRejectModal(true);
                            }}
                            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-600 to-red-500 text-white font-semibold rounded-xl hover:from-red-500 hover:to-red-400 transition-all duration-200 shadow-lg shadow-red-500/20 hover:shadow-red-500/40"
                          >
                            <X className="w-4 h-4" />
                            Reject
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
            )}
          </div>
        )}

          {activeTab === 'users' && (
            <div className="text-center py-20">
              <div className="dynamic-card-subtle rounded-3xl p-12">
                <div className="relative inline-block mb-6">
                  <Users className="w-24 h-24 text-purple-400 mx-auto" />
                  <div className="absolute -top-2 -right-2 bg-yellow-500/20 border border-yellow-400/30 rounded-full p-2">
                    <Sparkles className="w-6 h-6 text-yellow-400 animate-pulse" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Advanced User Management</h3>
                <p className="text-gray-400 max-w-2xl mx-auto mb-6">
                  Comprehensive user management features including role assignment, permissions, bulk operations, and detailed user analytics are being finalized for the next major update.
                </p>
                <div className="dynamic-card-subtle rounded-2xl p-4">
                  <p className="text-purple-300 text-sm font-medium">🚀 Coming Soon: Role-based access control, user analytics, and advanced permissions</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'navigation' && (
            <div className="bg-gradient-to-br from-green-500/5 to-emerald-500/5 rounded-2xl p-1 border border-green-500/20">
              <NavigationSettings />
            </div>
          )}

          {activeTab === 'pii-config' && (
            <div className="bg-gradient-to-br from-purple-500/5 to-violet-500/5 rounded-2xl p-1 border border-purple-500/20">
              <PIIConfigurationManager />
            </div>
          )}
          
          {activeTab === 'recovery' && (
            <div className="bg-gradient-to-br from-red-500/5 to-rose-500/5 rounded-2xl p-1 border border-red-500/20">
              <AdminRecovery />
            </div>
          )}

          {activeTab === 'demo-data' && (
            <div className="dynamic-card-subtle rounded-2xl p-1">
              <DemoDataManager />
            </div>
          )}

          {activeTab === 'nectar-bots' && (
            <div className="bg-gradient-to-br from-cyan-500/5 to-teal-500/5 rounded-2xl p-1 border border-cyan-500/20">
              <NectarBotManager />
            </div>
          )}
        </div>

        {/* Enhanced Reject Document Modal */}
        <ResponsiveModal
          isOpen={showRejectModal}
          onClose={() => {
            setShowRejectModal(false);
            setRejectingDoc(null);
            setRejectReason('');
          }}
          title="Document Rejection"
          size="md"
        >
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-red-900/30 to-rose-900/30 border border-red-500/30 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-start gap-4">
                <div className="bg-red-500/20 p-3 rounded-xl">
                  <AlertCircle className="w-6 h-6 text-red-400" />
                </div>
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-red-300 mb-2">Confirm Document Rejection</h4>
                  <p className="text-red-200/80 mb-3">
                    You are about to reject <strong>"{rejectingDoc?.documentName}"</strong>
                  </p>
                  <div className="bg-red-500/10 rounded-xl p-3 border border-red-500/20">
                    <p className="text-red-300/80 text-sm">
                      ⚠️ This action will permanently delete the document and send a notification to the uploader.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                <FileText className="w-4 h-4" />
                Rejection Reason (optional)
              </label>
              <textarea
                className="w-full px-4 py-3 bg-slate-700/80 border border-slate-600/50 text-white rounded-xl focus:ring-2 focus:ring-red-400 focus:border-transparent backdrop-blur-sm"
                rows="4"
                placeholder="Provide feedback to help the uploader understand why this document was rejected..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
            
            <ResponsiveModalFooter>
              <ResponsiveModalButton
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectingDoc(null);
                  setRejectReason('');
                }}
                variant="cancel"
              >
                Cancel
              </ResponsiveModalButton>
              <ResponsiveModalButton
                onClick={handleRejectDocument}
                variant="danger"
              >
                Reject Document
              </ResponsiveModalButton>
            </ResponsiveModalFooter>
          </div>
        </ResponsiveModal>

        {/* Scroll to Top Button */}
        <ScrollToTopButton />
    </div>
  );
};

export default AdminPanel;