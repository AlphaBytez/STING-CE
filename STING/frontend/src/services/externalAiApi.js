import axios from 'axios';

// External AI Service API client
const EXTERNAL_AI_API_URL = window.env?.REACT_APP_EXTERNAL_AI_API_URL || 
                           process.env.REACT_APP_EXTERNAL_AI_API_URL || 
                           '/api/external-ai';  // Use proxy route instead of direct port

const externalAiClient = axios.create({
    baseURL: EXTERNAL_AI_API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Add logging for debug purposes
if (process.env.NODE_ENV === 'development' || window.env?.NODE_ENV === 'development') {
    console.log('External AI API URL:', EXTERNAL_AI_API_URL);
    
    externalAiClient.interceptors.response.use(
        response => {
            console.log('External AI API response:', response.status, response.config.url);
            return response;
        },
        error => {
            console.error('External AI API error:', error.message, error.config?.url);
            if (error.response) {
                console.error('Response data:', error.response.data);
                console.error('Response status:', error.response.status);
            }
            return Promise.reject(error);
        }
    );
}

// External AI Provider configurations
export const AI_PROVIDERS = {
    OPENAI: {
        id: 'openai',
        name: 'OpenAI GPT-4',
        description: 'Advanced language model for comprehensive analysis',
        capabilities: ['text-analysis', 'summarization', 'insights', 'recommendations'],
        privacyLevel: 'medium',
        estimatedCost: 0.03, // per 1K tokens
        maxTokens: 128000,
        type: 'cloud'
    },
    CLAUDE: {
        id: 'claude',
        name: 'Anthropic Claude',
        description: 'Constitutional AI for safe and helpful analysis',
        capabilities: ['text-analysis', 'summarization', 'code-review', 'research'],
        privacyLevel: 'medium',
        estimatedCost: 0.025,
        maxTokens: 200000,
        type: 'cloud'
    },
    OLLAMA: {
        id: 'ollama',
        name: 'Ollama Local',
        description: 'Local Ollama deployment for maximum privacy and control',
        capabilities: ['text-analysis', 'summarization', 'insights', 'code-review', 'agent-tasks'],
        privacyLevel: 'high',
        estimatedCost: 0.0,
        maxTokens: 32000,
        type: 'local',
        defaultModel: 'phi3:mini',
        supportedModels: [
            'phi3:mini',
            'phi3:medium',
            'llama3.1:8b',
            'llama3.1:70b',
            'codellama:13b',
            'mistral:7b',
            'qwen2:7b',
            'deepseek-r1:latest',
            'deepseek-r1:32b'
        ],
        endpoint: 'http://localhost:11434',
        features: {
            knowledgeSync: true,
            agentTasks: true,
            codeAnalysis: true,
            multiModal: false
        }
    },
    LOCAL_LLM: {
        id: 'local',
        name: 'Generic Local LLM',
        description: 'Generic on-premises model for basic tasks',
        capabilities: ['text-analysis', 'summarization', 'basic-insights'],
        privacyLevel: 'high',
        estimatedCost: 0.0,
        maxTokens: 32000,
        type: 'local'
    }
};

// Privacy levels and their data handling policies
export const PRIVACY_LEVELS = {
    LOW: {
        level: 'low',
        name: 'Low Privacy',
        description: 'Data sent directly to external AI service',
        dataHandling: 'direct',
        piiScrambling: false,
        encryption: false,
        auditLog: true
    },
    MEDIUM: {
        level: 'medium',
        name: 'Medium Privacy',
        description: 'Basic PII detection and replacement',
        dataHandling: 'scrambled',
        piiScrambling: true,
        encryption: false,
        auditLog: true
    },
    HIGH: {
        level: 'high',
        name: 'High Privacy',
        description: 'Full PII scrambling with encrypted transmission',
        dataHandling: 'encrypted_scrambled',
        piiScrambling: true,
        encryption: true,
        auditLog: true
    }
};

// External AI API functions
export const externalAiApi = {
    // Get available AI providers
    getProviders: async () => {
        try {
            const response = await externalAiClient.get('/providers');
            return response.data;
        } catch (error) {
            console.warn('Failed to fetch providers from API, using defaults');
            return Object.values(AI_PROVIDERS);
        }
    },

    // Generate report using external AI
    generateReport: async (reportRequest) => {
        const response = await externalAiClient.post('/reports/generate', reportRequest);
        return response.data;
    },

    // Get report generation status
    getReportStatus: async (reportId) => {
        const response = await externalAiClient.get(`/reports/${reportId}/status`);
        return response.data;
    },

    // Get completed report
    getReport: async (reportId) => {
        const response = await externalAiClient.get(`/reports/${reportId}`);
        return response.data;
    },

    // Cancel report generation
    cancelReport: async (reportId) => {
        const response = await externalAiClient.delete(`/reports/${reportId}`);
        return response.data;
    },

    // Test AI provider connection
    testProvider: async (providerId, testData = null) => {
        const response = await externalAiClient.post(`/providers/${providerId}/test`, {
            testData: testData || 'This is a test message to verify the AI provider connection.'
        });
        return response.data;
    },

    // Get PII scrambling preview
    previewScrambling: async (data, privacyLevel = 'medium') => {
        const response = await externalAiClient.post('/privacy/preview-scrambling', {
            data,
            privacyLevel
        });
        return response.data;
    },

    // Estimate report cost and time
    estimateReport: async (reportRequest) => {
        const response = await externalAiClient.post('/reports/estimate', reportRequest);
        return response.data;
    },

    // Ollama-specific functions
    ollama: {
        // Get available Ollama models
        getModels: async () => {
            try {
                const response = await externalAiClient.get('/ollama/models');
                return response.data;
            } catch (error) {
                console.warn('Failed to fetch Ollama models, using defaults');
                return AI_PROVIDERS.OLLAMA.supportedModels.map(model => ({
                    name: model,
                    size: 'Unknown',
                    modified_at: new Date().toISOString()
                }));
            }
        },

        // Pull/download a model
        pullModel: async (modelName) => {
            const response = await externalAiClient.post('/ollama/pull', { model: modelName });
            return response.data;
        },

        // Check if Ollama is running
        checkStatus: async () => {
            try {
                const response = await externalAiClient.get('/ollama/status');
                return response.data;
            } catch (error) {
                return { running: false, error: error.message };
            }
        },

        // Generate with specific Ollama model
        generate: async (prompt, model = 'phi3:mini', options = {}) => {
            const response = await externalAiClient.post('/ollama/generate', {
                model,
                prompt,
                options: {
                    temperature: 0.7,
                    top_p: 0.9,
                    ...options
                }
            });
            return response.data;
        }
    },

    // Unified Bee chat endpoint (handles both conversation and reports)
    beeChatUnified: async (chatRequest) => {
        const response = await externalAiClient.post('/bee/chat', chatRequest);
        return response.data;
    },

    // Knowledge base sync functions
    knowledgeBase: {
        // Sync knowledge base with local AI
        syncToLocal: async (knowledgeData, targetProvider = 'ollama') => {
            const response = await externalAiClient.post('/knowledge/sync', {
                data: knowledgeData,
                targetProvider,
                syncType: 'full'
            });
            return response.data;
        },

        // Get sync status
        getSyncStatus: async (syncId) => {
            const response = await externalAiClient.get(`/knowledge/sync/${syncId}/status`);
            return response.data;
        },

        // Create knowledge embeddings
        createEmbeddings: async (documents, provider = 'ollama') => {
            const response = await externalAiClient.post('/knowledge/embeddings', {
                documents,
                provider,
                model: provider === 'ollama' ? 'nomic-embed-text' : 'text-embedding-ada-002'
            });
            return response.data;
        },

        // Search knowledge base
        search: async (query, provider = 'ollama', limit = 10) => {
            const response = await externalAiClient.post('/knowledge/search', {
                query,
                provider,
                limit
            });
            return response.data;
        },

        // Update knowledge base incrementally
        updateIncremental: async (newData, provider = 'ollama') => {
            const response = await externalAiClient.post('/knowledge/update', {
                data: newData,
                provider,
                updateType: 'incremental'
            });
            return response.data;
        }
    },

    // Agent task functions for local processing
    agentTasks: {
        // Create an agent task
        createTask: async (taskDefinition) => {
            const response = await externalAiClient.post('/agent/tasks', taskDefinition);
            return response.data;
        },

        // Get task status
        getTaskStatus: async (taskId) => {
            const response = await externalAiClient.get(`/agent/tasks/${taskId}/status`);
            return response.data;
        },

        // Get task results
        getTaskResults: async (taskId) => {
            const response = await externalAiClient.get(`/agent/tasks/${taskId}/results`);
            return response.data;
        },

        // Cancel a task
        cancelTask: async (taskId) => {
            const response = await externalAiClient.delete(`/agent/tasks/${taskId}`);
            return response.data;
        },

        // List all tasks
        listTasks: async (status = null) => {
            const params = status ? { status } : {};
            const response = await externalAiClient.get('/agent/tasks', { params });
            return response.data;
        }
    }
};

// Knowledge base sync configurations
export const KNOWLEDGE_SYNC_CONFIG = {
    FULL_SYNC: {
        type: 'full',
        description: 'Complete knowledge base synchronization',
        estimatedTime: '10-30 minutes',
        dataTypes: ['honey_jars', 'reports', 'configurations', 'user_data'],
        privacyLevel: 'high',
        compression: true,
        encryption: true
    },
    INCREMENTAL_SYNC: {
        type: 'incremental',
        description: 'Sync only new or modified data',
        estimatedTime: '1-5 minutes',
        dataTypes: ['recent_honey_jars', 'new_reports'],
        privacyLevel: 'high',
        compression: true,
        encryption: true
    },
    SELECTIVE_SYNC: {
        type: 'selective',
        description: 'Sync specific data categories',
        estimatedTime: '2-10 minutes',
        dataTypes: 'user_defined',
        privacyLevel: 'configurable',
        compression: true,
        encryption: true
    }
};

// Agent task templates for local processing
export const AGENT_TASK_TEMPLATES = {
    DATA_ANALYSIS: {
        id: 'data-analysis',
        name: 'Data Analysis Task',
        description: 'Analyze data patterns and generate insights',
        category: 'analysis',
        provider: 'ollama',
        model: 'phi3:mini',
        estimatedTime: '5-15 minutes',
        requiredCapabilities: ['text-analysis', 'pattern-recognition'],
        template: {
            system: 'You are a data analyst AI. Analyze the provided data and identify patterns, trends, and insights.',
            userPrompt: 'Analyze this data: {{DATA}}. Focus on: {{ANALYSIS_FOCUS}}',
            outputFormat: 'structured_json'
        }
    },
    SECURITY_SCAN: {
        id: 'security-scan',
        name: 'Security Analysis Task',
        description: 'Perform security analysis on logs and data',
        category: 'security',
        provider: 'ollama',
        model: 'codellama:13b',
        estimatedTime: '10-20 minutes',
        requiredCapabilities: ['security-analysis', 'log-analysis'],
        template: {
            system: 'You are a cybersecurity analyst AI. Analyze logs and data for security threats and vulnerabilities.',
            userPrompt: 'Analyze these logs for security issues: {{LOG_DATA}}. Focus on: {{SECURITY_SCOPE}}',
            outputFormat: 'security_report'
        }
    },
    CODE_REVIEW: {
        id: 'code-review',
        name: 'Code Review Task',
        description: 'Review code for quality and security issues',
        category: 'development',
        provider: 'ollama',
        model: 'codellama:13b',
        estimatedTime: '5-10 minutes',
        requiredCapabilities: ['code-analysis', 'security-review'],
        template: {
            system: 'You are a senior software engineer AI. Review code for quality, security, and best practices.',
            userPrompt: 'Review this code: {{CODE}}. Focus on: {{REVIEW_CRITERIA}}',
            outputFormat: 'code_review_report'
        }
    },
    KNOWLEDGE_EXTRACTION: {
        id: 'knowledge-extraction',
        name: 'Knowledge Extraction Task',
        description: 'Extract and structure knowledge from unstructured data',
        category: 'knowledge',
        provider: 'ollama',
        model: 'phi3:mini',
        estimatedTime: '3-8 minutes',
        requiredCapabilities: ['text-processing', 'knowledge-extraction'],
        template: {
            system: 'You are a knowledge extraction AI. Extract structured information from unstructured text.',
            userPrompt: 'Extract key information from: {{TEXT_DATA}}. Structure as: {{OUTPUT_STRUCTURE}}',
            outputFormat: 'structured_knowledge'
        }
    }
};

// Report templates with external AI integration
export const REPORT_TEMPLATES = {
    CUSTOMER_INSIGHTS: {
        id: 'customer-insights',
        title: 'Customer Insights Report',
        description: 'AI-powered analysis of customer behavior and trends',
        category: 'analytics',
        dataSources: ['honey_jars', 'csv_upload'],
        recommendedProvider: 'openai',
        privacyLevel: 'medium',
        estimatedTime: '2-5 minutes',
        requiredFields: ['data_source', 'analysis_period'],
        template: `
Analyze the provided customer data and generate insights on:
1. Customer behavior patterns
2. Trends and anomalies
3. Segmentation opportunities
4. Recommendations for improvement

Data provided: {{DATA_SUMMARY}}
Analysis period: {{ANALYSIS_PERIOD}}
        `
    },
    SECURITY_AUDIT: {
        id: 'security-audit',
        title: 'Security Audit Report',
        description: 'Automated security assessment and recommendations',
        category: 'security',
        dataSources: ['logs', 'honey_jars'],
        recommendedProvider: 'local',
        privacyLevel: 'high',
        estimatedTime: '5-10 minutes',
        requiredFields: ['data_source', 'audit_scope'],
        template: `
Perform a security analysis on the provided data focusing on:
1. Access patterns and anomalies
2. Potential security threats
3. Compliance issues
4. Recommended security improvements

Data provided: {{DATA_SUMMARY}}
Audit scope: {{AUDIT_SCOPE}}
        `
    },
    SALES_PERFORMANCE: {
        id: 'sales-performance',
        title: 'Sales Performance Report',
        description: 'Quarterly sales analysis with predictive insights',
        category: 'business',
        dataSources: ['honey_jars', 'database'],
        recommendedProvider: 'claude',
        privacyLevel: 'medium',
        estimatedTime: '3-7 minutes',
        requiredFields: ['data_source', 'time_period'],
        template: `
Analyze sales performance data and provide:
1. Performance metrics and KPIs
2. Trend analysis and forecasting
3. Regional and product performance
4. Strategic recommendations

Data provided: {{DATA_SUMMARY}}
Time period: {{TIME_PERIOD}}
        `
    }
};

// Mock external AI service for demo purposes
export const mockExternalAi = {
    generateInsights: async (scrambledData, provider = 'openai') => {
        // Simulate processing time based on provider
        const processingTime = provider === 'ollama' ? 
            1000 + Math.random() * 2000 : // Ollama is faster locally
            2000 + Math.random() * 3000;  // Cloud providers take longer
        
        await new Promise(resolve => setTimeout(resolve, processingTime));
        
        // Log what the "external" service receives (for demo)
        console.log(`${provider.toUpperCase()} received:`, scrambledData);
        
        // Provider-specific responses
        const providerResponses = {
            ollama: {
                insights: [
                    "Local analysis shows {{NAME_1}} represents 15% of total customer value with consistent engagement",
                    "Regional data indicates {{REGION_1}} customers show 23% higher engagement rates",
                    "Product analysis reveals {{PRODUCT_1}} maintains 4.8/5 satisfaction with strong retention",
                    "Temporal patterns show peak activity during {{TIME_PERIOD_1}} with 40% increase",
                    "Trend analysis identifies {{CATEGORY_1}} with 35% growth trajectory"
                ],
                recommendations: [
                    "Prioritize {{REGION_1}} market expansion based on engagement metrics",
                    "Scale {{PRODUCT_1}} production to meet demand indicators",
                    "Investigate {{CATEGORY_1}} growth potential for strategic planning"
                ],
                confidence: 0.92, // Higher confidence for local analysis
                processingTime: `${(processingTime / 1000).toFixed(1)} seconds`,
                tokensUsed: 1100,
                estimatedCost: 0.0, // Free for local
                provider: provider,
                privacyCompliant: true,
                localProcessing: true,
                knowledgeBaseUsed: true
            },
            openai: {
                insights: [
                    "Advanced analysis indicates {{NAME_1}} represents 15% of total customer value",
                    "Geographic segmentation shows {{REGION_1}} with 23% higher engagement rates",
                    "Product performance data reveals {{PRODUCT_1}} leading with 4.8/5 satisfaction",
                    "Temporal analysis identifies {{TIME_PERIOD_1}} as peak activity period",
                    "Market trend analysis shows {{CATEGORY_1}} with significant 35% growth"
                ],
                recommendations: [
                    "Implement targeted marketing strategy for {{REGION_1}} demographic",
                    "Expand {{PRODUCT_1}} portfolio based on performance metrics",
                    "Develop {{CATEGORY_1}} market strategy to capitalize on growth trend"
                ],
                confidence: 0.87,
                processingTime: `${(processingTime / 1000).toFixed(1)} seconds`,
                tokensUsed: 1250,
                estimatedCost: 0.0375,
                provider: provider,
                privacyCompliant: true,
                localProcessing: false
            }
        };
        
        return providerResponses[provider] || providerResponses.openai;
    },

    // Mock Ollama-specific functions
    ollama: {
        checkStatus: async () => {
            await new Promise(resolve => setTimeout(resolve, 500));
            return {
                running: true,
                version: "0.1.32",
                models: AI_PROVIDERS.OLLAMA.supportedModels.length,
                endpoint: AI_PROVIDERS.OLLAMA.endpoint
            };
        },

        getModels: async () => {
            await new Promise(resolve => setTimeout(resolve, 800));
            return AI_PROVIDERS.OLLAMA.supportedModels.map(model => ({
                name: model,
                size: model.includes('70b') ? '40GB' : model.includes('13b') ? '7.3GB' : '4.7GB',
                modified_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
                digest: `sha256:${Math.random().toString(36).substring(2, 15)}`,
                details: {
                    format: 'gguf',
                    family: model.split(':')[0],
                    families: [model.split(':')[0]],
                    parameter_size: model.includes('70b') ? '70B' : model.includes('13b') ? '13B' : '8B'
                }
            }));
        },

        generate: async (prompt, model = 'phi3:mini', options = {}) => {
            const processingTime = 1000 + Math.random() * 2000;
            await new Promise(resolve => setTimeout(resolve, processingTime));
            
            return {
                model: model,
                created_at: new Date().toISOString(),
                response: `Local AI response to: "${prompt.substring(0, 50)}..." using ${model}`,
                done: true,
                context: [1, 2, 3, 4, 5], // Mock context tokens
                total_duration: processingTime * 1000000, // nanoseconds
                load_duration: 100000000,
                prompt_eval_count: prompt.length / 4,
                prompt_eval_duration: 200000000,
                eval_count: 150,
                eval_duration: 800000000
            };
        }
    },

    // Mock knowledge base sync functions
    knowledgeBase: {
        syncToLocal: async (knowledgeData, targetProvider = 'ollama') => {
            const syncTime = 5000 + Math.random() * 10000; // 5-15 seconds for demo
            await new Promise(resolve => setTimeout(resolve, syncTime));
            
            return {
                syncId: `sync_${Date.now()}`,
                status: 'completed',
                provider: targetProvider,
                dataSize: `${(JSON.stringify(knowledgeData).length / 1024).toFixed(2)} KB`,
                documentsProcessed: Array.isArray(knowledgeData) ? knowledgeData.length : 1,
                embeddingsCreated: Array.isArray(knowledgeData) ? knowledgeData.length * 10 : 10,
                processingTime: `${(syncTime / 1000).toFixed(1)} seconds`,
                knowledgeBaseSize: '2.3 MB',
                lastSync: new Date().toISOString()
            };
        },

        search: async (query, provider = 'ollama', limit = 10) => {
            await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
            
            // Mock search results
            const mockResults = [
                { content: `Knowledge about ${query} from honey jar data`, score: 0.95, source: 'honey_jar_1' },
                { content: `Related information on ${query} patterns`, score: 0.87, source: 'report_analysis' },
                { content: `Historical data regarding ${query} trends`, score: 0.82, source: 'historical_logs' },
                { content: `Configuration details for ${query}`, score: 0.78, source: 'system_config' }
            ];
            
            return {
                query: query,
                results: mockResults.slice(0, limit),
                totalResults: mockResults.length,
                searchTime: `${(Math.random() * 0.5 + 0.1).toFixed(3)} seconds`,
                provider: provider,
                knowledgeBaseVersion: '1.2.3'
            };
        },

        createEmbeddings: async (documents, provider = 'ollama') => {
            const processingTime = documents.length * 200 + Math.random() * 1000;
            await new Promise(resolve => setTimeout(resolve, processingTime));
            
            return {
                embeddings: documents.map((doc, index) => ({
                    document: doc.substring(0, 100) + '...',
                    embedding: Array.from({length: 384}, () => Math.random() - 0.5), // Mock embedding vector
                    index: index
                })),
                model: provider === 'ollama' ? 'nomic-embed-text' : 'text-embedding-ada-002',
                dimensions: 384,
                processingTime: `${(processingTime / 1000).toFixed(1)} seconds`,
                provider: provider
            };
        }
    },

    // Mock agent task functions
    agentTasks: {
        createTask: async (taskDefinition) => {
            await new Promise(resolve => setTimeout(resolve, 500));
            
            const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
            
            return {
                taskId: taskId,
                status: 'created',
                taskType: taskDefinition.type || 'analysis',
                provider: taskDefinition.provider || 'ollama',
                model: taskDefinition.model || 'phi3:mini',
                estimatedTime: taskDefinition.estimatedTime || '5-10 minutes',
                createdAt: new Date().toISOString(),
                priority: taskDefinition.priority || 'medium'
            };
        },

        getTaskStatus: async (taskId) => {
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Simulate task progression
            const statuses = ['created', 'queued', 'running', 'completed'];
            const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
            
            return {
                taskId: taskId,
                status: randomStatus,
                progress: randomStatus === 'completed' ? 100 : Math.floor(Math.random() * 90) + 10,
                startedAt: new Date(Date.now() - Math.random() * 300000).toISOString(),
                estimatedCompletion: randomStatus === 'completed' ? null : new Date(Date.now() + Math.random() * 600000).toISOString(),
                currentStep: randomStatus === 'running' ? 'Processing data with local AI model' : null
            };
        },

        getTaskResults: async (taskId) => {
            await new Promise(resolve => setTimeout(resolve, 800));
            
            return {
                taskId: taskId,
                status: 'completed',
                results: {
                    summary: 'Task completed successfully using local AI processing',
                    insights: [
                        'Local processing maintained complete data privacy',
                        'Analysis completed without external API calls',
                        'Knowledge base integration provided contextual insights'
                    ],
                    data: {
                        processedItems: Math.floor(Math.random() * 1000) + 100,
                        patterns: Math.floor(Math.random() * 50) + 10,
                        anomalies: Math.floor(Math.random() * 5),
                        confidence: (Math.random() * 0.3 + 0.7).toFixed(2)
                    }
                },
                completedAt: new Date().toISOString(),
                processingTime: `${(Math.random() * 300 + 60).toFixed(1)} seconds`,
                resourceUsage: {
                    cpu: `${(Math.random() * 50 + 20).toFixed(1)}%`,
                    memory: `${(Math.random() * 2 + 1).toFixed(1)} GB`,
                    tokens: Math.floor(Math.random() * 5000) + 1000
                }
            };
        }
    },

    // Demo PII detection and scrambling
    scrambleData: (text, privacyLevel = 'medium') => {
        const patterns = {
            email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
            phone: /\b\d{3}-\d{3}-\d{4}\b/g,
            ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
            name: /\b[A-Z][a-z]+ [A-Z][a-z]+\b/g,
            address: /\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b/g,
            creditCard: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g
        };
        
        const replacements = {};
        let scrambled = text;
        let detectedPii = [];
        
        if (privacyLevel === 'low') {
            return { scrambled: text, replacements: {}, detectedPii: [] };
        }
        
        Object.entries(patterns).forEach(([type, pattern]) => {
            const matches = text.match(pattern) || [];
            matches.forEach((match, index) => {
                const variable = `{{${type.toUpperCase()}_${index + 1}}}`;
                replacements[variable] = match;
                detectedPii.push({ type, value: match, variable });
                scrambled = scrambled.replace(match, variable);
            });
        });
        
        return { 
            scrambled, 
            replacements, 
            detectedPii,
            privacyLevel,
            scramblingApplied: privacyLevel !== 'low'
        };
    }
};

export default externalAiApi;