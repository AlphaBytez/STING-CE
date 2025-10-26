import axios from 'axios';
import { resilientGet, resilientPost, fallbackGenerators } from '../utils/resilientApiClient';

// Knowledge Service API client
const KNOWLEDGE_API_URL = window.env?.REACT_APP_KNOWLEDGE_API_URL || 
                         process.env.REACT_APP_KNOWLEDGE_API_URL || 
                         '/api/knowledge';

const knowledgeClient = axios.create({
    baseURL: KNOWLEDGE_API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Add request interceptor for consistent header handling
knowledgeClient.interceptors.request.use(
    async (config) => {
        // Rely on Flask session cookies for authentication
        // The axios client is already configured with withCredentials: true
        // so session cookies will be included automatically
        
        // Add any additional headers needed for the knowledge service
        config.headers['X-Requested-With'] = 'XMLHttpRequest';
        
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor for error handling
knowledgeClient.interceptors.response.use(
    response => {
        if (process.env.NODE_ENV === 'development' || window.env?.NODE_ENV === 'development') {
            console.log('Knowledge API response:', response.status, response.config.url);
        }
        return response;
    },
    error => {
        if (process.env.NODE_ENV === 'development' || window.env?.NODE_ENV === 'development') {
            console.error('Knowledge API error:', error.message, error.config?.url);
            if (error.response) {
                console.error('Response data:', error.response.data);
                console.error('Response status:', error.response.status);
            }
        }
        
        // Handle authentication errors
        if (error.response && error.response.status === 401) {
            // Don't immediately redirect - let components handle auth gracefully
            console.warn('Knowledge API: 401 authentication error - component should handle gracefully');
            
            // Only redirect if this is a critical auth failure after retries
            const shouldRedirect = error.config?._isRetry || false;
            if (shouldRedirect) {
                localStorage.removeItem('user');
                sessionStorage.clear();
                window.location.href = '/login?message=Session expired. Please login again.';
            }
        } else if (error.response && error.response.status === 403) {
            // 403 (forbidden) - user is authenticated but lacks permission
            // Don't logout, just show the error message
            console.error('Permission denied:', error.response.data?.detail || 'You do not have permission to perform this action');
        } else if (error.response && error.response.status === 503) {
            // 503 (service unavailable) - knowledge service is down
            // Don't logout, just show error
            console.error('Knowledge service unavailable:', error.response.data?.error || 'Service temporarily unavailable');
        }
        
        return Promise.reject(error);
    }
);

// Honey Jar API functions
export const honeyJarApi = {
    // Get all honey jars
    getHoneyJars: async (page = 1, pageSize = 20, filters = {}) => {
        try {
            // Convert page-based pagination to offset-based for knowledge service
            const offset = (page - 1) * pageSize;
            const params = new URLSearchParams({
                limit: pageSize.toString(),
                offset: offset.toString(),
                ...filters
            });
            const response = await knowledgeClient.get(`/honey-jars?${params.toString()}`);
            return response.data;
        } catch (error) {
            console.warn('HoneyJars API failed, using fallback data:', error.message);
            return fallbackGenerators.honeyJars();
        }
    },

    // Get a specific honey jar by ID
    getHoneyJar: async (id) => {
        const response = await knowledgeClient.get(`/honey-jars/${id}`);
        return response.data;
    },

    // Create a new honey jar
    createHoneyJar: async (data) => {
        const response = await knowledgeClient.post('/honey-jars', data);
        return response.data;
    },

    // Update a honey jar
    updateHoneyJar: async (id, data) => {
        const response = await knowledgeClient.put(`/honey-jars/${id}`, data);
        return response.data;
    },

    // Delete a honey jar
    deleteHoneyJar: async (id) => {
        await knowledgeClient.delete(`/honey-jars/${id}`);
    },

    // Upload documents to a honey jar
    uploadDocuments: async (honeyJarId, files, metadata = {}) => {
        console.log(`📁 Starting upload for ${files.length} files to honey jar ${honeyJarId}`);
        
        const results = [];
        let successCount = 0;
        let requiresApproval = false;
        
        // Upload files one at a time since backend expects single file
        for (const file of files) {
            console.log(`📄 Uploading file: ${file.name} (${file.size} bytes, ${file.type})`);
            
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                // Add tags if provided in metadata
                if (metadata.tags && Array.isArray(metadata.tags)) {
                    metadata.tags.forEach(tag => {
                        formData.append('tags', tag);
                    });
                }

                console.log(`🚀 Making POST request to /honey-jars/${honeyJarId}/documents/upload`);
                
                const response = await knowledgeClient.post(
                    `/honey-jars/${honeyJarId}/documents/upload`, 
                    formData,
                    {
                        headers: {
                            'Content-Type': 'multipart/form-data'
                        }
                    }
                );
                
                console.log(`✅ Upload successful for ${file.name}:`, response.data);
                
                results.push(response.data);
                successCount++;
                
                // Check if any document requires approval
                if (response.data.status === 'pending_approval') {
                    requiresApproval = true;
                }
                
            } catch (error) {
                console.error(`❌ Failed to upload ${file.name}:`, error);
                console.error(`Error details:`, {
                    status: error.response?.status,
                    statusText: error.response?.statusText,
                    data: error.response?.data,
                    message: error.message
                });
                
                results.push({
                    filename: file.name,
                    error: error.response?.data?.detail || error.message,
                    status: 'failed'
                });
            }
        }

        console.log(`📊 Upload summary: ${successCount}/${files.length} successful, requires_approval: ${requiresApproval}`);
        
        // Return summary result
        return {
            documents_uploaded: successCount,
            total_files: files.length,
            requires_approval: requiresApproval,
            results: results
        };
    },

    // Bulk upload directory to honey jar
    uploadDirectory: async (honeyJarId, file, options = {}) => {
        console.log(`📦 Starting bulk upload to honey jar ${honeyJarId}: ${file.name}`);
        
        const formData = new FormData();
        formData.append('directory', file);
        formData.append('options', JSON.stringify({
            recursive: true,
            include_patterns: options.include_patterns || ['*.md', '*.txt', '*.pdf', '*.doc', '*.docx', '*.json', '*.html'],
            exclude_patterns: options.exclude_patterns || ['.git', 'node_modules', '*.tmp', '.DS_Store'],
            retention_policy: options.retention_policy || 'permanent',
            metadata: options.metadata || {}
        }));

        const response = await knowledgeClient.post(
            `/honey-jars/${honeyJarId}/upload-directory`, 
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }
        );
        
        console.log('✅ Bulk upload started:', response.data);
        return response.data;
    },

    // Get bulk upload status
    getBulkUploadStatus: async (uploadId) => {
        const response = await knowledgeClient.get(`/uploads/${uploadId}/status`);
        return response.data;
    },

    // Get documents in a honey jar
    getDocuments: async (honeyJarId) => {
        const response = await knowledgeClient.get(`/honey-jars/${honeyJarId}/documents`);
        return response.data;
    },

    // Delete a document
    deleteDocument: async (honeyJarId, documentId) => {
        await knowledgeClient.delete(`/honey-jars/${honeyJarId}/documents/${documentId}`);
    },

    // Ripen a honey jar (reprocess all documents)
    ripenHoneyJar: async (honeyJarId) => {
        const response = await knowledgeClient.post(`/honey-jars/${honeyJarId}/ripen`);
        return response.data;
    }
};

// Search API functions
export const searchApi = {
    // Search across honey jars
    search: async (query, options = {}) => {
        const searchData = {
            query,
            honey_jar_ids: options.honeyJarIds,
            top_k: options.topK || 5,
            filters: options.filters || {},
            include_metadata: options.includeMetadata !== false
        };
        
        const response = await knowledgeClient.post('/search', searchData);
        return response.data;
    },

    // Get context for Bee chatbot
    getBeeContext: async (query, conversationHistory = [], maxItems = 3) => {
        const contextData = {
            query,
            conversation_history: conversationHistory,
            max_context_items: maxItems
        };
        
        const response = await knowledgeClient.post('/bee/context', contextData);
        return response.data;
    }
};

// Marketplace API functions
export const marketplaceApi = {
    // Search marketplace listings
    searchMarketplace: async (options = {}) => {
        const searchData = {
            query: options.query,
            tags: options.tags,
            price_min: options.priceMin,
            price_max: options.priceMax,
            license_type: options.licenseType,
            sort_by: options.sortBy || 'relevance',
            page: options.page || 1,
            page_size: options.pageSize || 20
        };
        
        const response = await knowledgeClient.post('/marketplace/search', searchData);
        return response.data;
    },

    // Get marketplace listing details
    getListing: async (listingId) => {
        const response = await knowledgeClient.get(`/marketplace/listings/${listingId}`);
        return response.data;
    },

    // Create marketplace listing
    createListing: async (data) => {
        const response = await knowledgeClient.post('/marketplace/listings', data);
        return response.data;
    },

    // Purchase/download from marketplace
    purchaseListing: async (listingId, paymentData = {}) => {
        const response = await knowledgeClient.post(`/marketplace/listings/${listingId}/purchase`, paymentData);
        return response.data;
    }
};

// Health check
export const healthApi = {
    checkHealth: async () => {
        const response = await knowledgeClient.get('/health');
        return response.data;
    }
};

// Backward compatibility - keep old names as aliases
export const HoneyJarApi = honeyJarApi;

export default knowledgeClient;