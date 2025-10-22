import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  Shield,
  Download,
  Eye,
  Hexagon,
  Database,
  FileText,
  Calendar,
  Tag,
  Lock,
  Globe,
  Building,
  UserCheck,
  X,
  Activity,
  Clock,
  Users,
  BookOpen,
  Zap,
  Brain,
  Plus,
  Upload,
  RefreshCw,
  Folder
} from 'lucide-react';
import { honeyJarApi } from '../../services/knowledgeApi';
import ResponsiveModal, { ResponsiveModalFooter, ResponsiveModalButton } from '../common/ResponsiveModal';
import BulkUploadModal from '../common/BulkUploadModal';
import ScrollToTopButton from '../common/ScrollToTopButton';
import TierBadge, { TierIndicator, OPERATION_TIERS } from '../common/TierBadge';
import DocumentPreviewModal from '../modals/DocumentPreviewModal';
import {
  handleReturnFromAuth,
  checkOperationAuth,
  clearAuthMarker,
  storeOperationContext,
  getStoredOperationContext,
  shouldRetryOperation,
  OPERATIONS
} from '../../utils/tieredAuth';

// Modal component using ResponsiveModal
const CreateHoneyJarModal = ({ isOpen, onClose, onSuccess, protectOperation }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'private',
    tags: []
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    setError(null);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return;
    }

    if (!formData.description.trim()) {
      setError('Description is required');
      return;
    }

    // Check authentication BEFORE attempting creation (Tier 2 - basic operation)
    if (protectOperation) {
      const canProceed = await protectOperation('CREATE_HONEY_JAR', { name: formData.name });
      if (!canProceed) {
        // User was redirected to security-upgrade or cancelled
        return;
      }
    }

    setIsSubmitting(true);
    setError(null);
    console.log('🔄 Creating honey jar (authentication pre-verified)');

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        type: formData.type,
        tags: formData.tags
      };

      const newHoneyJar = await honeyJarApi.createHoneyJar(payload);

      // Clear auth markers since operation succeeded
      if (protectOperation) {
        // Import clearAuthMarker in the parent component
        console.log('✅ Honey jar created successfully');
      }

      // Reset form
      setFormData({
        name: '',
        description: '',
        type: 'private',
        tags: []
      });

      // Close modal and refresh list
      onClose();
      if (onSuccess) {
        onSuccess(newHoneyJar);
      }
    } catch (err) {
      console.error('Failed to create honey jar:', err);
      setError(err.message || 'Failed to create honey jar. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        name: '',
        description: '',
        type: 'private',
        tags: []
      });
      setError(null);
      onClose();
    }
  };

  return (
    <ResponsiveModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Honey Jar"
      size="md"
    >
      <div className="space-y-4">
        <p className="text-gray-400">Configure and create a new knowledge base.</p>
        
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-500 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
            <input 
              type="text" 
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="w-full px-3 py-2 dynamic-card-subtle border border-gray-600 text-white rounded-2xl focus:ring-2 focus:ring-purple-400 focus:border-purple-400 placeholder-gray-400"
              placeholder="Enter honey jar name"
              disabled={isSubmitting}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <textarea 
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              className="w-full px-3 py-2 dynamic-card-subtle border border-gray-600 text-white rounded-2xl focus:ring-2 focus:ring-purple-400 focus:border-purple-400 placeholder-gray-400"
              rows="3"
              placeholder="Describe the purpose of this knowledge base"
              disabled={isSubmitting}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
            <select 
              value={formData.type}
              onChange={(e) => handleInputChange('type', e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 text-white rounded-2xl focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 [&>option]:bg-gray-800 [&>option]:text-white"
              disabled={isSubmitting}
            >
              <option value="private">Private</option>
              <option value="public">Public</option>
              <option value="team">Team</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Tags (optional)</label>
            <input 
              type="text" 
              value={formData.tags.join(', ')}
              onChange={(e) => handleInputChange('tags', e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag))}
              className="w-full px-3 py-2 dynamic-card-subtle border border-gray-600 text-white rounded-2xl focus:ring-2 focus:ring-purple-400 focus:border-purple-400 placeholder-gray-400"
              placeholder="Enter tags separated by commas"
              disabled={isSubmitting}
            />
          </div>
        </div>
        <ResponsiveModalFooter>
          <ResponsiveModalButton
            onClick={handleClose}
            variant="cancel"
            className="sm:flex-1"
            disabled={isSubmitting}
          >
            Cancel
          </ResponsiveModalButton>
          <ResponsiveModalButton
            onClick={handleSubmit}
            variant="primary"
            className="sm:flex-1"
            disabled={isSubmitting || !formData.name.trim() || !formData.description.trim()}
          >
            {isSubmitting ? 'Creating...' : 'Create'}
          </ResponsiveModalButton>
        </ResponsiveModalFooter>
      </div>
    </ResponsiveModal>
  );
};

// Define operations for honey jars
const HONEY_JAR_OPERATIONS = {
  VIEW_HONEY_JARS: {
    name: 'VIEW_HONEY_JARS',
    tier: 2,
    description: 'View honey jar contents'
  },
  CREATE_HONEY_JAR: {
    name: 'CREATE_HONEY_JAR',
    tier: 2,
    description: 'Create new honey jars'
  },
  UPLOAD_DOCUMENTS: {
    name: 'UPLOAD_DOCUMENTS',
    tier: 2,
    description: 'Upload documents to honey jars'
  },
  EXPORT_HONEY_JAR: {
    name: 'EXPORT_HONEY_JAR',
    tier: 3,
    description: 'Export honey jar data'
  },
  RIPEN_HONEY_JAR: {
    name: 'RIPEN_HONEY_JAR',
    tier: 3,
    description: 'Reprocess honey jar embeddings'
  },
  BULK_UPLOAD: {
    name: 'BULK_UPLOAD',
    tier: 3,
    description: 'Bulk upload documents'
  },
  MODIFY_PERMISSIONS: {
    name: 'MODIFY_PERMISSIONS',
    tier: 4,
    description: 'Modify honey jar permissions'
  }
};

const HoneyJarPage = () => {
  const navigate = useNavigate();
  const [honeyJars, setHoneyJars] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedHoneyJar, setSelectedHoneyJar] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  
  // Mock data as fallback
  const mockHoneyJars = [
    {
      id: 1,
      name: "STING Platform Knowledge",
      description: "Core documentation and API references for STING platform",
      documents: 42,
      embeddings: 1250,
      lastUpdated: "2025-06-20",
      lastAccessed: "2 hours ago",
      status: "active",
      type: "public",
      owner: "Admin",
      team: "Platform",
      permissions: ["read", "query"],
      tags: ["documentation", "api", "platform"],
      size: "124 MB",
      version: "2.1.0",
      // Additional details for modal
      stats: {
        totalQueries: 3420,
        avgResponseTime: 0.23,
        accuracy: 98.5,
        lastTraining: "2025-06-15",
        documentsProcessed: 156,
        activeUsers: 89
      },
      contents: [
        "Installation Guide",
        "API Reference",
        "Architecture Overview",
        "Security Documentation",
        "Troubleshooting Guide"
      ],
      integrations: ["Bee Chat", "Search API", "Beeacon Monitoring"]
    },
    {
      id: 2, 
      name: "Customer Support FAQ",
      description: "Frequently asked questions and troubleshooting guides",
      documents: 18,
      embeddings: 890,
      lastUpdated: "2025-06-19",
      lastAccessed: "1 day ago",
      status: "active", 
      type: "private",
      owner: "Support Team",
      team: "Support",
      permissions: ["read", "write", "query"],
      tags: ["faq", "support", "troubleshooting"],
      size: "45 MB",
      version: "1.4.2"
    },
    {
      id: 3,
      name: "Marketing Materials",
      description: "Product brochures, case studies, and marketing content",
      documents: 25,
      embeddings: 650,
      lastUpdated: "2025-06-18",
      lastAccessed: "3 days ago",
      status: "active",
      type: "team",
      owner: "Marketing",
      team: "Marketing",
      permissions: ["read", "query"],
      tags: ["marketing", "content", "brochures"],
      size: "89 MB",
      version: "3.0.1"
    },
    {
      id: 4,
      name: "Engineering Documentation",
      description: "Technical specifications, architecture diagrams, and development guides",
      documents: 156,
      embeddings: 4320,
      lastUpdated: "2025-06-21",
      lastAccessed: "30 minutes ago",
      status: "active",
      type: "team",
      owner: "Engineering Lead",
      team: "Engineering",
      permissions: ["read", "write", "query", "admin"],
      tags: ["technical", "architecture", "development"],
      size: "512 MB",
      version: "4.2.0"
    },
    {
      id: 5,
      name: "Legal & Compliance",
      description: "Contracts, policies, compliance documents, and regulatory information",
      documents: 89,
      embeddings: 2100,
      lastUpdated: "2025-06-15",
      lastAccessed: "5 hours ago",
      status: "active",
      type: "restricted",
      owner: "Legal Dept",
      team: "Legal",
      permissions: ["read", "query"],
      tags: ["legal", "compliance", "policies"],
      size: "234 MB",
      version: "2.0.3"
    }
  ];

  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    type: 'all',
    team: 'all',
    permission: 'all',
    status: 'all'
  });
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 9; // 3x3 grid
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [ripenProgress, setRipenProgress] = useState(null);
  const [ripenError, setRipenError] = useState(null);
  const [isRipening, setIsRipening] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [documentError, setDocumentError] = useState(null);
  const [showBulkUploadModal, setShowBulkUploadModal] = useState(false);
  const [bulkUploadHoneyJar, setBulkUploadHoneyJar] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [showDocumentPreview, setShowDocumentPreview] = useState(false);

  // Handle return from authentication flow and auto-retry operations
  useEffect(() => {
    // Check for each operation if user just returned from authentication
    Object.values(HONEY_JAR_OPERATIONS).forEach(operation => {
      if (shouldRetryOperation(operation.name)) {
        console.log(`🔄 Auto-retrying honey jar operation after authentication: ${operation.name}`);

        // Get stored context
        const context = getStoredOperationContext(operation.name);

        // Set auth marker
        handleReturnFromAuth(operation.name);

        // Auto-retry the operation based on its type
        setTimeout(() => {
          switch (operation.name) {
            case HONEY_JAR_OPERATIONS.UPLOAD_DOCUMENTS.name:
              if (context?.honeyJarId && context?.files) {
                // Re-trigger file upload - would need to store file references
                console.log(`🔄 File upload ready for retry on honey jar ${context.honeyJarId}`);
                // Note: File upload retry is complex due to file object limitations
              }
              break;
            case HONEY_JAR_OPERATIONS.EXPORT_HONEY_JAR.name:
              if (context?.honeyJarId && context?.format) {
                const jar = honeyJars.find(j => j.id === context.honeyJarId);
                if (jar) {
                  handleExportHoneyJar(jar, context.format);
                }
              }
              break;
            case HONEY_JAR_OPERATIONS.RIPEN_HONEY_JAR.name:
              if (context?.honeyJarId) {
                const jar = honeyJars.find(j => j.id === context.honeyJarId);
                if (jar) {
                  handleRipenHoneyJar(jar);
                }
              }
              break;
            case HONEY_JAR_OPERATIONS.BULK_UPLOAD.name:
              if (context?.honeyJarId) {
                const jar = honeyJars.find(j => j.id === context.honeyJarId);
                if (jar) {
                  handleBulkUpload(jar);
                }
              }
              break;
            default:
              console.log(`⚠️ Unknown honey jar operation for auto-retry: ${operation.name}`);
          }
        }, 100); // Small delay to ensure page is fully loaded
      }
    });
  }, [honeyJars]);

  // Tiered authentication for honey jar operations
  const protectHoneyJarOperation = async (operationKey, additionalData = {}) => {
    const operation = HONEY_JAR_OPERATIONS[operationKey];
    if (!operation) {
      console.error('Unknown honey jar operation:', operationKey);
      return false;
    }

    console.log(`🔐 HoneyJar: Checking ${operation.tier} authentication for: ${operation.description}`);

    const canProceed = await checkOperationAuth(operation.name, operation.tier, additionalData);

    if (canProceed) {
      console.log(`✅ HoneyJar: Authentication verified for ${operation.description}`);
      return true;
    } else {
      console.log(`❌ HoneyJar: Authentication failed for ${operation.description}`);
      return false;
    }
  };

  // Optimized authentication-aware loading: Faster auth checks with reduced delays
  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 2; // Reduced from 3 to 2 for faster fallback
    
    const loadSystemJarsWithAuth = async () => {
      attempts++;
      
      try {
        // Quick auth check with shorter timeout
        console.log(`🔒 Checking authentication status (attempt ${attempts}/${maxAttempts})...`);
        
        // Optimized auth check with timeout
        const authCheck = await Promise.race([
          fetch('/api/auth/me', {
            method: 'GET',
            credentials: 'include'
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Auth check timeout')), 3000))
        ]);
        
        if (authCheck.ok) {
          const authData = await authCheck.json();
          if (authData.authenticated) {
            console.log('✅ Authentication confirmed, loading honey jars...');
            await loadHoneyJars(true); // Skip loading state since we manage it in the auth flow
            return;
          }
        }
        
        // If auth check failed, wait briefly and retry or use fallback
        if (attempts < maxAttempts) {
          console.log(`🔄 Authentication not ready, retrying in 1s...`);
          setTimeout(loadSystemJarsWithAuth, 1000); // Reduced from 2-5s to 1s
        } else {
          console.log('📦 Max auth attempts reached, attempting direct load...');
          // Try direct load before falling back to mock data
          try {
            await loadHoneyJars(true);
          } catch (directLoadError) {
            console.log('📦 Direct load failed, using mock data');
            setHoneyJars(mockHoneyJars);
            setLoading(false);
          }
        }
        
      } catch (error) {
        console.error(`Failed auth check attempt ${attempts}:`, error);
        
        if (attempts < maxAttempts) {
          setTimeout(loadSystemJarsWithAuth, 1000); // Reduced retry delay
        } else {
          console.log('📦 Attempting direct load as final attempt...');
          try {
            await loadHoneyJars(true);
          } catch (directLoadError) {
            console.log('📦 Using mock honey jars as final fallback');
            setHoneyJars(mockHoneyJars);
            setLoading(false);
          }
        }
      }
    };
    
    // Start the optimized auth-aware loading process
    loadSystemJarsWithAuth();
  }, []); // Only on mount

  // Helper functions
  const calculateTimeAgo = (date) => {
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffHours < 1) return 'Less than an hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays === 1) return '1 day ago';
    return `${diffDays} days ago`;
  };

  const extractTeamFromOwner = (owner) => {
    if (!owner) return 'Unknown';
    if (owner.toLowerCase().includes('admin')) return 'Platform';
    if (owner.toLowerCase().includes('support')) return 'Support';
    if (owner.toLowerCase().includes('engineering')) return 'Engineering';
    if (owner.toLowerCase().includes('legal')) return 'Legal';
    return owner;
  };

  const extractPermissionsFromType = (type) => {
    switch (type?.toLowerCase()) {
      case 'public': return ['read', 'query'];
      case 'private': return ['read', 'write', 'query'];
      case 'premium': return ['read', 'query'];
      case 'enterprise': return ['read', 'write', 'query', 'admin'];
      default: return ['read'];
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const teams = [...new Set(honeyJars.map(jar => jar.team))];
  const permissions = ['read', 'write', 'query', 'admin'];

  const handleOpenHoneyJar = (jar) => {
    setSelectedHoneyJar(jar);
    setShowDetails(true);
  };

  const handleCloseDetails = () => {
    setShowDetails(false);
    setTimeout(() => setSelectedHoneyJar(null), 300);
    setDocuments([]);
    setDocumentError(null);
  };

  // Load documents when modal opens
  useEffect(() => {
    if (showDetails && selectedHoneyJar) {
      loadDocuments(selectedHoneyJar.id);
    }
  }, [showDetails, selectedHoneyJar]);

  const loadDocuments = async (honeyJarId) => {
    setLoadingDocs(true);
    setDocumentError(null);
    try {
      const response = await honeyJarApi.getDocuments(honeyJarId);
      console.log('📄 Loaded documents:', response);
      // Handle both response.data and direct array response
      const docs = response.data || response || [];
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocumentError('Unable to load documents');
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const handleDocumentDownload = async (honeyJarId, document) => {
    try {
      console.log(`📥 Downloading document: ${document.filename}`);

      // Create download URL
      const downloadUrl = `/api/knowledge/honey-jars/${honeyJarId}/documents/${document.id}/download`;

      // Trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = document.filename;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

    } catch (error) {
      console.error('Failed to download document:', error);
      setDocumentError('Failed to download document');
    }
  };

  const handleDocumentPreview = (honeyJarId, doc) => {
    setSelectedDocument(doc);
    setShowDocumentPreview(true);
  };

  const handleFileUpload = async (event, honeyJarId) => {
    // Check authentication BEFORE attempting upload (Tier 2 - basic operation)
    const canProceed = await protectHoneyJarOperation('UPLOAD_DOCUMENTS', { honeyJarId });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    const files = event.target.files;
    if (!files || files.length === 0) return;

    console.log('🔄 Uploading documents (authentication pre-verified)');
    setUploadProgress('Uploading documents...');
    setUploadError(null);

    try {
      const result = await honeyJarApi.uploadDocuments(honeyJarId, Array.from(files));
      
      // Update the honey jar stats locally
      const updatedJar = honeyJars.find(jar => jar.id === honeyJarId);
      if (updatedJar) {
        updatedJar.documents += result.documents_uploaded;
        updatedJar.embeddings += result.documents_uploaded * 30; // Estimate
        setHoneyJars([...honeyJars]);
      }

      // Clear auth markers since operation succeeded
      clearAuthMarker(HONEY_JAR_OPERATIONS.UPLOAD_DOCUMENTS.name);

      // Show appropriate success message
      if (result.requires_approval) {
        setUploadProgress(`Uploaded ${result.documents_uploaded} documents. They are pending admin approval.`);
      } else {
        setUploadProgress(`Successfully uploaded ${result.documents_uploaded} documents!`);
      }

      // Clear success message after 5 seconds
      setTimeout(() => {
        setUploadProgress(null);
        // Refresh the honey jar data
        loadHoneyJars();
      }, 5000);
      
    } catch (error) {
      console.error('❌ Document upload failed:', error);
      
      // Handle specific error cases
      let errorMessage = 'Failed to upload documents';
      
      if (error.response) {
        if (error.response.status === 403) {
          errorMessage = 'You do not have permission to upload documents to this honey jar. ' +
                        'Only admins and honey jar owners can upload documents directly. ' +
                        'Document approval workflow coming soon!';
        } else if (error.response.data?.detail) {
          errorMessage = error.response.data.detail;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setUploadError(errorMessage);
      setUploadProgress(null);
      
      // Clear error after 5 seconds
      setTimeout(() => {
        setUploadError(null);
      }, 5000);
    }
  };

  const handleBulkUpload = async (honeyJar) => {
    // Check authentication BEFORE attempting bulk upload (Tier 3 - sensitive operation)
    const canProceed = await protectHoneyJarOperation('BULK_UPLOAD', { honeyJarId: honeyJar.id });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    console.log('🔄 Opening bulk upload modal (authentication pre-verified)');
    setBulkUploadHoneyJar(honeyJar);
    setShowBulkUploadModal(true);

    // Clear auth markers since operation succeeded
    clearAuthMarker(HONEY_JAR_OPERATIONS.BULK_UPLOAD.name);
  };

  const closeBulkUploadModal = () => {
    setShowBulkUploadModal(false);
    setBulkUploadHoneyJar(null);
    // Refresh honey jars to show updated stats
    loadHoneyJars();
  };

  const handleQueryWithBee = (honeyJar) => {
    // Navigate to Bee chat with honey jar context
    navigate('/dashboard/chat', { 
      state: { 
        honeyJarContext: {
          id: honeyJar.id,
          name: honeyJar.name,
          description: honeyJar.description,
          documentCount: honeyJar.stats?.document_count || 0
        },
        initialMessage: `I'd like to explore the "${honeyJar.name}" honey jar. What insights can you provide about its contents?`
      }
    });
  };

  const handleExportHoneyJar = async (honeyJar, format = 'hjx') => {
    // Check authentication BEFORE attempting export (Tier 3 - sensitive operation)
    const canProceed = await protectHoneyJarOperation('EXPORT_HONEY_JAR', { honeyJarId: honeyJar.id, format });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Exporting honey jar (authentication pre-verified)');
      const response = await fetch(`/api/knowledge/honey-jars/${honeyJar.id}/export?format=${format}`);
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
      const filename = filenameMatch ? filenameMatch[1] : `${honeyJar.name.replace(/\s+/g, '_')}.${format}`;
      
      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Clear auth markers since operation succeeded
      clearAuthMarker(HONEY_JAR_OPERATIONS.EXPORT_HONEY_JAR.name);

      // Show success message (you could add a toast notification here)
      console.log(`Successfully exported honey jar: ${filename}`);
    } catch (error) {
      console.error('❌ Honey jar export failed:', error);
      setError('Failed to export honey jar');
    }
  };

  const handleRipenHoneyJar = async (honeyJar) => {
    // Check authentication BEFORE attempting ripen (Tier 3 - sensitive operation)
    const canProceed = await protectHoneyJarOperation('RIPEN_HONEY_JAR', { honeyJarId: honeyJar.id });
    if (!canProceed) {
      // User was redirected to security-upgrade or cancelled
      return;
    }

    try {
      console.log('🔄 Ripening honey jar (authentication pre-verified)');
      setIsRipening(true);
      setRipenProgress('Ripening honey jar...');
      setRipenError(null);
      
      const result = await honeyJarApi.ripenHoneyJar(honeyJar.id);
      
      // Update local state with new stats
      const updatedJar = honeyJars.find(jar => jar.id === honeyJar.id);
      if (updatedJar) {
        updatedJar.embeddings = result.total_chunks;
        updatedJar.lastUpdated = result.ripened_at;
        setHoneyJars([...honeyJars]);
        
        // Update selected honey jar if it's the same
        if (selectedHoneyJar?.id === honeyJar.id) {
          setSelectedHoneyJar({
            ...selectedHoneyJar,
            embeddings: result.total_chunks,
            lastUpdated: result.ripened_at
          });
        }
      }
      
      // Clear auth markers since operation succeeded
      clearAuthMarker(HONEY_JAR_OPERATIONS.RIPEN_HONEY_JAR.name);

      setRipenProgress(
        `Successfully ripened honey jar! Processed ${result.processed} documents with ${result.total_chunks} chunks.` +
        (result.failed > 0 ? ` ${result.failed} documents failed.` : '')
      );
      
      // Refresh data after 3 seconds
      setTimeout(() => {
        setRipenProgress(null);
        setIsRipening(false);
        loadHoneyJars();
      }, 3000);
      
    } catch (error) {
      console.error('❌ Honey jar ripening failed:', error);
      
      let errorMessage = 'Failed to ripen honey jar';
      if (error.response) {
        if (error.response.status === 403) {
          errorMessage = 'Only administrators and honey jar owners can ripen honey jars.';
        } else if (error.response.data?.detail) {
          errorMessage = error.response.data.detail;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setRipenError(errorMessage);
      setRipenProgress(null);
      setIsRipening(false);
      
      // Clear error after 5 seconds
      setTimeout(() => {
        setRipenError(null);
      }, 5000);
    }
  };

  const loadHoneyJars = async (skipLoadingState = false) => {
    try {
      if (!skipLoadingState) {
        setLoading(true);
      }
      const response = await honeyJarApi.getHoneyJars();
      // API returns array directly, not {items: [...]}
      const jarData = Array.isArray(response) ? response : (response.items || []);
      
      // Process the data to match our frontend structure
      const processedJars = jarData.map(jar => ({
        id: jar.id,
        name: jar.name,
        description: jar.description,
        documents: jar.stats?.document_count || 0,
        embeddings: jar.stats?.embedding_count || 0,
        lastUpdated: jar.last_updated,
        lastAccessed: jar.stats?.last_accessed || jar.last_updated,
        status: jar.status,
        type: jar.type,
        owner: jar.owner,
        team: jar.tags?.[0] || 'General',
        permissions: ['read', 'query'],
        tags: jar.tags || [],
        stats: {
          totalQueries: 0,
          avgResponseTime: 0,
          accuracy: 95
        },
        integrations: ['Bee Chat'],
        contents: ['API Docs', 'User Guides', 'Tutorials'],
        version: '1.0.0'
      }));
      
      setHoneyJars(processedJars);
      setError(null);
    } catch (err) {
      console.error('Failed to load honey jars:', err);
      setError('Failed to load honey jars. Using offline data.');
      // Use mock data as fallback
      setHoneyJars(mockHoneyJars);
    } finally {
      setLoading(false);
    }
  };

  const filteredHoneyJars = honeyJars.filter(jar => {
    const matchesSearch = jar.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         jar.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         jar.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesType = filters.type === 'all' || jar.type === filters.type;
    const matchesTeam = filters.team === 'all' || jar.team === filters.team;
    const matchesPermission = filters.permission === 'all' || jar.permissions.includes(filters.permission);
    const matchesStatus = filters.status === 'all' || jar.status === filters.status;
    return matchesSearch && matchesType && matchesTeam && matchesPermission && matchesStatus;
  });

  // Pagination
  const totalPages = Math.ceil(filteredHoneyJars.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedHoneyJars = filteredHoneyJars.slice(startIndex, endIndex);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filters]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'draft': return 'bg-orange-100/80 text-orange-800';
      case 'archived': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type) => {
    switch(type) {
      case 'public': return <Globe className="w-4 h-4" />;
      case 'private': return <Lock className="w-4 h-4" />;
      case 'team': return <Building className="w-4 h-4" />;
      case 'restricted': return <Shield className="w-4 h-4" />;
      default: return <Database className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type) => {
    switch(type) {
      case 'public': return 'text-blue-600 bg-blue-100';
      case 'private': return 'text-gray-600 bg-gray-100';
      case 'team': return 'text-purple-600 bg-purple-100';
      case 'restricted': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Hexagon className="w-8 h-8 text-yellow-500" />
            <h1 className="text-3xl font-bold text-white">Honey Jars</h1>
          </div>
          <p className="text-gray-400">Browse and access your installed knowledge bases</p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-500"></div>
          <span className="ml-3 text-gray-400">Loading honey jars...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="dark-theme">
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Hexagon className="w-8 h-8 text-yellow-500" />
          <h1 className="text-3xl font-bold text-white">Honey Jars</h1>
        </div>
        <p className="text-gray-400">Browse and access your installed knowledge bases</p>
          {error && (
            <div className="mt-3 p-3 bg-orange-900 border border-orange-700 rounded-xl">
              <p className="text-orange-300 text-sm">⚠️ {error}</p>
            </div>
          )}
        </div>

        {/* Security Notice with Tier Information */}
        <div className="sting-glass-subtle border border-amber-500/50 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <Shield className="text-amber-400 text-lg mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-amber-300 font-medium mb-2">Tiered Knowledge Security</h3>
              <p className="text-amber-200/80 text-sm leading-relaxed mb-3">
                Knowledge base operations are protected by progressive security levels based on sensitivity:
              </p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <TierBadge tier={2} size="xs" />
                  <span className="text-amber-200 text-sm">View, Create, Upload documents</span>
                </div>
                <div className="flex items-center gap-2">
                  <TierBadge tier={3} size="xs" />
                  <span className="text-amber-200 text-sm">Export, Bulk upload, Ripen (reprocess)</span>
                </div>
                <div className="flex items-center gap-2">
                  <TierBadge tier={4} size="xs" />
                  <span className="text-amber-200 text-sm">Modify permissions, Admin operations</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search honey jars by name, description, or tags..."
            className="w-full pl-10 pr-4 py-2 bg-gray-600 border border-gray-500 text-gray-100 rounded-2xl focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        {/* Load Honey Jars button - shows when using mock data */}
        {honeyJars === mockHoneyJars && (
          <button
            onClick={() => {
              console.log('🔄 Manual honey jar reload requested');
              setError(null);
              setLoading(true);
              loadHoneyJars().finally(() => setLoading(false));
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-2xl hover:bg-blue-600 transition-colors"
            disabled={loading}
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Load Honey Jars'}
          </button>
        )}
        
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 floating-button rounded-2xl transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create Honey Jar
        </button>
        
        <button
          onClick={() => setShowFilterPanel(!showFilterPanel)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-500 bg-gray-600 text-gray-100 rounded-2xl hover:bg-gray-500 transition-colors"
        >
          <Filter className="w-5 h-5" />
          Filters
          {Object.values(filters).filter(f => f !== 'all').length > 0 && (
            <span className="bg-purple-500/80 text-white text-xs px-2 py-0.5 rounded-full">
              {Object.values(filters).filter(f => f !== 'all').length}
            </span>
          )}
        </button>
      </div>

      {/* Filter Panel */}
      {showFilterPanel && (
        <div className="standard-card rounded-2xl p-6 mb-6">
          <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
              <select
                className="w-full px-3 py-2 bg-gray-500 border border-gray-400 text-gray-100 rounded-2xl focus:ring-2 focus:ring-yellow-500"
                value={filters.type}
                onChange={(e) => setFilters({...filters, type: e.target.value})}
              >
                <option value="all">All Types</option>
                <option value="public">Public</option>
                <option value="private">Private</option>
                <option value="team">Team</option>
                <option value="restricted">Restricted</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Team</label>
              <select
                className="w-full px-3 py-2 bg-gray-500 border border-gray-400 text-gray-100 rounded-2xl focus:ring-2 focus:ring-yellow-500"
                value={filters.team}
                onChange={(e) => setFilters({...filters, team: e.target.value})}
              >
                <option value="all">All Teams</option>
                {teams.map(team => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Permission</label>
              <select
                className="w-full px-3 py-2 bg-gray-500 border border-gray-400 text-gray-100 rounded-2xl focus:ring-2 focus:ring-yellow-500"
                value={filters.permission}
                onChange={(e) => setFilters({...filters, permission: e.target.value})}
              >
                <option value="all">All Permissions</option>
                {permissions.map(perm => (
                  <option key={perm} value={perm}>{perm}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Status</label>
              <select
                className="w-full px-3 py-2 bg-gray-500 border border-gray-400 text-gray-100 rounded-2xl focus:ring-2 focus:ring-yellow-500"
                value={filters.status}
                onChange={(e) => setFilters({...filters, status: e.target.value})}
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="draft">Draft</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setFilters({ type: 'all', team: 'all', permission: 'all', status: 'all' })}
              className="text-sm text-gray-400 hover:text-gray-200"
            >
              Clear all filters
            </button>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="standard-card border border-yellow-600 rounded-2xl p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-sm text-gray-400">Showing</p>
              <p className="text-lg font-semibold text-gray-100">{filteredHoneyJars.length} of {honeyJars.length} Honey Jars</p>
            </div>
            <div className="border-l border-yellow-600 pl-6">
              <p className="text-sm text-gray-400">Total Documents</p>
              <p className="text-lg font-semibold text-gray-100">
                {filteredHoneyJars.reduce((sum, jar) => sum + jar.documents, 0).toLocaleString()}
              </p>
            </div>
            <div className="border-l border-yellow-600 pl-6">
              <p className="text-sm text-gray-400">Total Storage</p>
              <p className="text-lg font-semibold text-gray-100">
                {filteredHoneyJars.reduce((sum, jar) => {
                  const size = parseInt(jar.size) || 0;
                  return sum + size;
                }, 0)} MB
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Honey Jars List */}
      <div className="space-y-4">
        {paginatedHoneyJars.map((jar) => (
          <div 
            key={jar.id} 
            onClick={() => handleOpenHoneyJar(jar)}
            className="standard-card rounded-2xl shadow hover:shadow-lg transition-all hover:scale-[1.01] cursor-pointer">
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-center gap-3 mb-3">
                    <Hexagon className="w-8 h-8 text-yellow-500 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-100">{jar.name}</h3>
                      <p className="text-sm text-gray-400 mt-1">{jar.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`flex items-center gap-1 px-3 py-1 text-xs rounded-full ${getTypeColor(jar.type)}`}>
                        {getTypeIcon(jar.type)}
                        {jar.type}
                      </span>
                      <span className={`px-3 py-1 text-xs rounded-full ${getStatusColor(jar.status)}`}>
                        {jar.status}
                      </span>
                    </div>
                  </div>

                  {/* Main Content Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-4">
                    {/* Stats */}
                    <div>
                      <div className="flex items-center gap-2 text-gray-500 mb-1">
                        <FileText className="w-4 h-4" />
                        <p className="text-xs">Documents</p>
                      </div>
                      <p className="text-lg font-semibold text-gray-100">{jar.documents}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-gray-500 mb-1">
                        <Database className="w-4 h-4" />
                        <p className="text-xs">Embeddings</p>
                      </div>
                      <p className="text-lg font-semibold text-gray-100">{jar.embeddings.toLocaleString()}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-gray-500 mb-1">
                        <Building className="w-4 h-4" />
                        <p className="text-xs">Team</p>
                      </div>
                      <p className="text-sm font-medium text-gray-100">{jar.team}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 text-gray-500 mb-1">
                        <Calendar className="w-4 h-4" />
                        <p className="text-xs">Last Access</p>
                      </div>
                      <p className="text-sm font-medium text-gray-100">{jar.lastAccessed}</p>
                    </div>
                  </div>

                  {/* Bottom Row */}
                  <div className="flex items-center justify-between">
                    {/* Tags */}
                    <div className="flex items-center gap-2">
                      <Tag className="w-4 h-4 text-gray-400" />
                      <div className="flex flex-wrap gap-1">
                        {jar.tags.map((tag, index) => (
                          <span key={index} className="px-2 py-1 bg-gray-500 text-gray-300 text-xs rounded-xl">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Meta Info */}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <UserCheck className="w-3 h-3" />
                        <span>{jar.permissions.join(', ')}</span>
                      </div>
                      <span>v{jar.version}</span>
                      <span>{jar.size}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenHoneyJar(jar);
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 floating-button text-sm rounded transition-colors">
                        <Eye className="w-4 h-4" />
                        Open
                      </button>
                      <button 
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 text-gray-400 hover:bg-gray-500 rounded-xl transition-colors">
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State - differentiate between not loaded vs filtered */}
      {filteredHoneyJars.length === 0 && (
        <div className="text-center py-12">
          <Hexagon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          {honeyJars.length === 0 ? (
            // No data loaded yet
            <>
              <h3 className="text-lg font-medium text-gray-100 mb-2">Ready to explore honey jars</h3>
              <p className="text-gray-400 mb-4">Click below to load your knowledge bases</p>
              <button
                onClick={loadHoneyJars}
                className="inline-flex items-center gap-2 px-6 py-3 floating-button font-medium rounded-2xl transition-colors"
              >
                <Database className="w-5 h-5" />
                Load Honey Jars
              </button>
            </>
          ) : (
            // Filtered results are empty
            <>
              <h3 className="text-lg font-medium text-gray-100 mb-2">No honey jars found</h3>
              <p className="text-gray-400 mb-4">Try adjusting your search or filters</p>
              <button
                onClick={() => {
                  setSearchTerm('');
                  setFilters({ type: 'all', team: 'all', permission: 'all', status: 'all' });
                }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-2xl hover:bg-gray-400 transition-colors"
              >
                Clear Filters
              </button>
            </>
          )}
        </div>
      )}

      {/* Pagination Controls */}
      {filteredHoneyJars.length > itemsPerPage && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 rounded-lg dynamic-card-subtle text-gray-300 hover:bg-gray-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          
          <div className="flex items-center gap-1">
            {[...Array(Math.min(5, totalPages))].map((_, index) => {
              let pageNumber;
              if (totalPages <= 5) {
                pageNumber = index + 1;
              } else if (currentPage <= 3) {
                pageNumber = index + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNumber = totalPages - 4 + index;
              } else {
                pageNumber = currentPage - 2 + index;
              }
              
              return (
                <button
                  key={pageNumber}
                  onClick={() => setCurrentPage(pageNumber)}
                  className={`w-8 h-8 rounded-lg transition-colors ${
                    currentPage === pageNumber
                      ? 'bg-purple-500/80 text-white'
                      : 'dynamic-card-subtle text-gray-300 hover:bg-gray-600/30'
                  }`}
                >
                  {pageNumber}
                </button>
              );
            })}
          </div>
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 rounded-lg dynamic-card-subtle text-gray-300 hover:bg-gray-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {/* Honey Jar Details Modal */}
      <ResponsiveModal
        isOpen={showDetails && selectedHoneyJar}
        onClose={() => setShowDetails(false)}
        size="lg"
        className="honey-jar-details-modal"
        showCloseButton={false}
      >
        {selectedHoneyJar && (
          <>
            {/* Modal Header */}
            <div className="dynamic-card-subtle -m-4 sm:-m-6 p-4 sm:p-6 mb-6 rounded-t-xl">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <Hexagon className="w-8 sm:w-10 h-8 sm:h-10" />
                  <div>
                    <h2 className="text-2xl font-bold">{selectedHoneyJar.name}</h2>
                    <p className="text-gray-300 mt-1">{selectedHoneyJar.description}</p>
                  </div>
                </div>
                <button
                  onClick={handleCloseDetails}
                  className="p-2 hover:bg-gray-600/30 rounded-xl transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                <div className="standard-card-light p-4 rounded-2xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-100">Performance</h3>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Total Queries</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.stats?.totalQueries || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Avg Response Time</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.stats?.avgResponseTime || 0}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Accuracy</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.stats?.accuracy || 0}%</span>
                    </div>
                  </div>
                </div>

                <div className="standard-card-light p-4 rounded-2xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-100">Data</h3>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Documents</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.documents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Embeddings</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.embeddings.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Size</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.size}</span>
                    </div>
                  </div>
                </div>

                <div className="standard-card-light p-4 rounded-2xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-100">Usage</h3>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Active Users</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.stats?.activeUsers || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Last Accessed</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.lastAccessed}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Last Training</span>
                      <span className="font-medium text-gray-200">{selectedHoneyJar.stats?.lastTraining || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Content Sections */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Documents */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <BookOpen className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-100">Documents ({documents.length})</h3>
                  </div>
                  {loadingDocs ? (
                    <div className="flex items-center gap-2 p-4">
                      <RefreshCw className="w-4 h-4 text-gray-400 animate-spin" />
                      <span className="text-sm text-gray-400">Loading documents...</span>
                    </div>
                  ) : documentError ? (
                    <div className="text-sm text-red-400 p-2">{documentError}</div>
                  ) : documents.length === 0 ? (
                    <div className="text-sm text-gray-400 p-2">No documents uploaded yet</div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {documents.map((doc) => (
                        <div key={doc.id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors">
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-gray-200 truncate" title={doc.filename}>
                                {doc.filename}
                              </p>
                              <p className="text-xs text-gray-400">
                                {formatFileSize(doc.size_bytes)} • {formatDate(doc.upload_date || doc.created_at)}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={() => handleDocumentPreview(selectedHoneyJar.id, doc)}
                              className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-500/30 rounded transition-all"
                              title="Preview document"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDocumentDownload(selectedHoneyJar.id, doc)}
                              className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-500/30 rounded transition-all"
                              title="Download document"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Integrations */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-100">Integrations</h3>
                  </div>
                  <div className="space-y-2">
                    {(selectedHoneyJar.integrations || ['Bee Chat']).map((integration, idx) => (
                      <div key={idx} className="flex items-center gap-2 p-2 bg-gray-600 rounded-xl">
                        <Brain className="w-4 h-4 text-yellow-500" />
                        <span className="text-sm font-medium text-gray-200">{integration}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex items-center gap-3 flex-wrap">
                <button 
                  onClick={() => handleQueryWithBee(selectedHoneyJar)}
                  className="flex items-center gap-2 px-4 py-2 floating-button rounded-xl transition-colors">
                  <Brain className="w-4 h-4" />
                  Query with Bee
                </button>
                <label className="flex items-center gap-2 px-4 py-2 floating-button rounded-xl transition-colors cursor-pointer">
                  <Upload className="w-4 h-4" />
                  Upload Documents
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.txt,.md,.html,.json"
                    onChange={(e) => handleFileUpload(e, selectedHoneyJar.id)}
                    className="hidden"
                  />
                </label>
                <button
                  onClick={() => handleBulkUpload(selectedHoneyJar)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
                  title="Upload directory/archive with multiple files"
                >
                  <Folder className="w-4 h-4" />
                  Bulk Upload
                </button>
                <button 
                  onClick={() => handleRipenHoneyJar(selectedHoneyJar)}
                  disabled={isRipening}
                  title="Re-process documents to refresh knowledge extraction"
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
                    isRipening 
                      ? 'bg-amber-600 text-white cursor-not-allowed' 
                      : 'bg-amber-500 text-white hover:bg-amber-600'
                  }`}>
                  <RefreshCw className={`w-4 h-4 ${isRipening ? 'animate-spin' : ''}`} />
                  {isRipening ? 'Ripening...' : 'Ripen'}
                </button>
                <div className="relative">
                  <button 
                    onClick={() => setShowExportMenu(!showExportMenu)}
                    className="flex items-center gap-2 px-4 py-2 border border-gray-500 text-gray-200 rounded-2xl hover:bg-gray-600 transition-colors">
                    <Download className="w-4 h-4" />
                    Export
                  </button>
                  {showExportMenu && (
                    <div className="absolute top-full mt-2 right-0 bg-gray-800 border border-gray-600 rounded-2xl shadow-lg z-10 overflow-hidden">
                      <button
                        onClick={() => {
                          handleExportHoneyJar(selectedHoneyJar, 'hjx');
                          setShowExportMenu(false);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-600/20 transition-colors flex items-center gap-2"
                      >
                        <Hexagon className="w-4 h-4 text-yellow-400" />
                        <div>
                          <div className="font-medium">HJX Format</div>
                          <div className="text-xs text-gray-400">STING Honey Jar Export (Recommended)</div>
                        </div>
                      </button>
                      <button
                        onClick={() => {
                          handleExportHoneyJar(selectedHoneyJar, 'json');
                          setShowExportMenu(false);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-600/20 transition-colors flex items-center gap-2"
                      >
                        <FileText className="w-4 h-4 text-blue-400" />
                        <div>
                          <div className="font-medium">JSON Format</div>
                          <div className="text-xs text-gray-400">Plain JSON with metadata</div>
                        </div>
                      </button>
                      <button
                        onClick={() => {
                          handleExportHoneyJar(selectedHoneyJar, 'tar');
                          setShowExportMenu(false);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-600/20 transition-colors flex items-center gap-2"
                      >
                        <Database className="w-4 h-4 text-green-400" />
                        <div>
                          <div className="font-medium">TAR Archive</div>
                          <div className="text-xs text-gray-400">All documents as archive</div>
                        </div>
                      </button>
                    </div>
                  )}
                </div>
                <button className="flex items-center gap-2 px-4 py-2 border border-gray-500 text-gray-200 rounded-2xl hover:bg-gray-600 transition-colors">
                  <Shield className="w-4 h-4" />
                  Permissions
                </button>
              </div>

              {/* Upload Status */}
              {(uploadProgress || uploadError) && (
                <div className={`mt-4 p-4 rounded-xl ${uploadError ? 'bg-red-500/20 border border-red-500' : 'bg-green-500/20 border border-green-500'}`}>
                  <p className={`text-sm ${uploadError ? 'text-red-200' : 'text-green-200'}`}>
                    {uploadProgress || uploadError}
                  </p>
                </div>
              )}
              
              {/* Ripen Status */}
              {(ripenProgress || ripenError) && (
                <div className={`mt-4 p-4 rounded-xl ${ripenError ? 'bg-red-500/20 border border-red-500' : 'bg-amber-500/20 border border-amber-500'}`}>
                  <p className={`text-sm ${ripenError ? 'text-red-200' : 'text-amber-200'}`}>
                    {ripenProgress || ripenError}
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </ResponsiveModal>

      {/* Create Honey Jar Modal - using portal to render at document root */}
      <CreateHoneyJarModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => {
          clearAuthMarker(HONEY_JAR_OPERATIONS.CREATE_HONEY_JAR.name);
          loadHoneyJars();
        }}
        protectOperation={protectHoneyJarOperation}
      />

      {/* Bulk Upload Modal */}
      <BulkUploadModal
        isOpen={showBulkUploadModal}
        onClose={closeBulkUploadModal}
        honeyJarId={bulkUploadHoneyJar?.id}
        honeyJarName={bulkUploadHoneyJar?.name}
      />

      {/* Scroll to Top Button */}
      <ScrollToTopButton />

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={showDocumentPreview}
        onClose={() => {
          setShowDocumentPreview(false);
          setSelectedDocument(null);
        }}
        document={selectedDocument}
        honeyJarId={selectedHoneyJar?.id}
      />
      </div>
    </div>
  );
};

export default HoneyJarPage;