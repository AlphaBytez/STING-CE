import { externalAiApi, mockExternalAi, KNOWLEDGE_SYNC_CONFIG } from './externalAiApi';

// Knowledge Base Synchronization Service
export class KnowledgeSyncService {
    constructor() {
        this.syncHistory = [];
        this.activeSyncs = new Map();
        this.knowledgeBaseVersion = '1.0.0';
    }

    // Get all honey jar data for sync
    async getHoneyJarData() {
        try {
            // This would integrate with your existing honey jar API
            const response = await fetch('/api/honey-jars', {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch honey jar data:', error);
            return [];
        }
    }

    // Get report data for sync
    async getReportData() {
        try {
            const response = await fetch('/api/reports', {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch report data:', error);
            return [];
        }
    }

    // Get system configuration for sync
    async getSystemConfig() {
        try {
            const response = await fetch('/api/system/config', {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch system config:', error);
            return {};
        }
    }

    // Prepare knowledge data for sync
    async prepareKnowledgeData(syncType = 'full', dataTypes = null) {
        const knowledgeData = {
            version: this.knowledgeBaseVersion,
            timestamp: new Date().toISOString(),
            syncType: syncType,
            data: {}
        };

        const defaultDataTypes = KNOWLEDGE_SYNC_CONFIG[syncType.toUpperCase()]?.dataTypes || ['honey_jars'];
        const targetDataTypes = dataTypes || defaultDataTypes;

        // Collect data based on requested types
        for (const dataType of targetDataTypes) {
            switch (dataType) {
                case 'honey_jars':
                case 'recent_honey_jars':
                    knowledgeData.data.honeyJars = await this.getHoneyJarData();
                    if (dataType === 'recent_honey_jars') {
                        // Filter to last 30 days
                        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
                        knowledgeData.data.honeyJars = knowledgeData.data.honeyJars.filter(
                            jar => new Date(jar.created_at) > thirtyDaysAgo
                        );
                    }
                    break;

                case 'reports':
                case 'new_reports':
                    knowledgeData.data.reports = await this.getReportData();
                    if (dataType === 'new_reports') {
                        // Filter to last 7 days
                        const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                        knowledgeData.data.reports = knowledgeData.data.reports.filter(
                            report => new Date(report.created_at) > sevenDaysAgo
                        );
                    }
                    break;

                case 'configurations':
                    knowledgeData.data.configurations = await this.getSystemConfig();
                    break;

                case 'user_data':
                    // Only include non-sensitive user preferences
                    knowledgeData.data.userPreferences = {
                        theme: localStorage.getItem('theme') || 'dark',
                        language: localStorage.getItem('language') || 'en',
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    };
                    break;

                default:
                    console.warn(`Unknown data type: ${dataType}`);
            }
        }

        return knowledgeData;
    }

    // Start knowledge base sync
    async startSync(syncType = 'incremental', targetProvider = 'ollama', dataTypes = null) {
        const syncId = `sync_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
        
        try {
            // Prepare knowledge data
            const knowledgeData = await this.prepareKnowledgeData(syncType, dataTypes);
            
            // Start sync process
            this.activeSyncs.set(syncId, {
                id: syncId,
                status: 'preparing',
                startTime: new Date(),
                syncType: syncType,
                targetProvider: targetProvider,
                dataTypes: dataTypes,
                progress: 0
            });

            // Update progress
            this.updateSyncProgress(syncId, 25, 'uploading');

            // Call external AI API for sync
            const syncResult = await externalAiApi.knowledgeBase.syncToLocal(knowledgeData, targetProvider);
            
            // Update progress
            this.updateSyncProgress(syncId, 75, 'processing');

            // Create embeddings for searchable content
            const documents = this.extractDocumentsFromKnowledge(knowledgeData);
            const embeddingResult = await externalAiApi.knowledgeBase.createEmbeddings(documents, targetProvider);

            // Complete sync
            this.updateSyncProgress(syncId, 100, 'completed');

            const finalResult = {
                syncId: syncId,
                status: 'completed',
                syncType: syncType,
                targetProvider: targetProvider,
                dataSize: syncResult.dataSize,
                documentsProcessed: syncResult.documentsProcessed,
                embeddingsCreated: embeddingResult.embeddings.length,
                processingTime: syncResult.processingTime,
                completedAt: new Date().toISOString()
            };

            // Add to history
            this.syncHistory.unshift(finalResult);
            this.activeSyncs.delete(syncId);

            return finalResult;

        } catch (error) {
            console.error('Sync failed:', error);
            this.updateSyncProgress(syncId, -1, 'failed', error.message);
            throw error;
        }
    }

    // Update sync progress
    updateSyncProgress(syncId, progress, status, error = null) {
        const sync = this.activeSyncs.get(syncId);
        if (sync) {
            sync.progress = progress;
            sync.status = status;
            sync.lastUpdate = new Date();
            if (error) {
                sync.error = error;
            }
        }
    }

    // Get sync status
    getSyncStatus(syncId) {
        return this.activeSyncs.get(syncId) || 
               this.syncHistory.find(sync => sync.syncId === syncId) ||
               { status: 'not_found' };
    }

    // Extract documents from knowledge data for embedding
    extractDocumentsFromKnowledge(knowledgeData) {
        const documents = [];

        // Extract from honey jars
        if (knowledgeData.data.honeyJars) {
            knowledgeData.data.honeyJars.forEach(jar => {
                documents.push(`Honey Jar: ${jar.name} - ${jar.description || 'No description'}`);
                if (jar.logs) {
                    jar.logs.forEach(log => {
                        documents.push(`Log entry: ${log.message || log.data}`);
                    });
                }
            });
        }

        // Extract from reports
        if (knowledgeData.data.reports) {
            knowledgeData.data.reports.forEach(report => {
                documents.push(`Report: ${report.title} - ${report.summary || report.content}`);
            });
        }

        // Extract from configurations
        if (knowledgeData.data.configurations) {
            Object.entries(knowledgeData.data.configurations).forEach(([key, value]) => {
                documents.push(`Configuration: ${key} = ${JSON.stringify(value)}`);
            });
        }

        return documents;
    }

    // Search knowledge base
    async searchKnowledge(query, provider = 'ollama', limit = 10) {
        try {
            return await externalAiApi.knowledgeBase.search(query, provider, limit);
        } catch (error) {
            console.error('Knowledge search failed:', error);
            // Fallback to mock for demo
            return await mockExternalAi.knowledgeBase.search(query, provider, limit);
        }
    }

    // Get sync history
    getSyncHistory() {
        return this.syncHistory;
    }

    // Get active syncs
    getActiveSyncs() {
        return Array.from(this.activeSyncs.values());
    }

    // Cancel active sync
    async cancelSync(syncId) {
        const sync = this.activeSyncs.get(syncId);
        if (sync) {
            sync.status = 'cancelled';
            sync.progress = -1;
            this.activeSyncs.delete(syncId);
            return { success: true, message: 'Sync cancelled' };
        }
        return { success: false, message: 'Sync not found or already completed' };
    }

    // Check if Ollama is available
    async checkOllamaStatus() {
        try {
            return await externalAiApi.ollama.checkStatus();
        } catch (error) {
            console.error('Failed to check Ollama status:', error);
            // Fallback to mock for demo
            return await mockExternalAi.ollama.checkStatus();
        }
    }

    // Get available Ollama models
    async getOllamaModels() {
        try {
            return await externalAiApi.ollama.getModels();
        } catch (error) {
            console.error('Failed to get Ollama models:', error);
            // Fallback to mock for demo
            return await mockExternalAi.ollama.getModels();
        }
    }
}

// Create singleton instance
export const knowledgeSyncService = new KnowledgeSyncService();

// Export utility functions
export const knowledgeUtils = {
    // Format sync status for display
    formatSyncStatus: (sync) => {
        const statusMap = {
            'preparing': 'Preparing data...',
            'uploading': 'Uploading to local AI...',
            'processing': 'Processing embeddings...',
            'completed': 'Completed successfully',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        return statusMap[sync.status] || sync.status;
    },

    // Calculate sync progress percentage
    getSyncProgressPercentage: (sync) => {
        if (sync.progress < 0) return 0;
        return Math.min(100, Math.max(0, sync.progress));
    },

    // Estimate sync time based on data size
    estimateSyncTime: (dataSize, syncType) => {
        const baseTime = syncType === 'full' ? 600 : syncType === 'incremental' ? 120 : 300; // seconds
        const sizeMultiplier = Math.max(1, dataSize / 1024); // KB
        return Math.round(baseTime * Math.log(sizeMultiplier + 1));
    },

    // Format data size
    formatDataSize: (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }
};

export default knowledgeSyncService;