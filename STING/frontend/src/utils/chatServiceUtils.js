/**
 * Chat Service Utilities
 *
 * Provides intelligent timeout management and service initialization detection
 * for all chat services (internal STING chatbot, external LLM services, 3rd party APIs)
 */

import { resilientGet } from './resilientApiClient';

// Service initialization cache
const serviceInitCache = new Map();
const CACHE_DURATION = 60000; // 1 minute cache

/**
 * Check if a chat service is initialized
 * @param {string} serviceType - Type of service ('chatbot', 'external_ai', 'openai', etc.)
 * @param {string} healthEndpoint - Health check endpoint URL (optional, uses defaults)
 * @returns {Promise<Object>} - { initialized: boolean, responseTime: number }
 */
export const checkServiceInitialization = async (serviceType = 'chatbot', healthEndpoint = null) => {
    const cacheKey = `${serviceType}:${healthEndpoint || 'default'}`;

    // Check cache first
    const cached = serviceInitCache.get(cacheKey);
    if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
        console.log(`📦 Using cached init status for ${serviceType}: ${cached.initialized}`);
        return cached;
    }

    // Determine health endpoint
    const endpoint = healthEndpoint || getDefaultHealthEndpoint(serviceType);

    try {
        const startTime = Date.now();
        const response = await resilientGet(endpoint, null, {
            timeout: 5000,
            critical: true
        });
        const responseTime = Date.now() - startTime;

        // Check initialization status based on service type
        const initialized = checkInitStatus(response, serviceType);

        const result = {
            initialized,
            responseTime,
            timestamp: Date.now(),
            serviceType
        };

        // Cache the result
        serviceInitCache.set(cacheKey, result);

        console.log(`✅ Service ${serviceType} initialization check: ${initialized ? 'READY' : 'INITIALIZING'} (${responseTime}ms)`);
        return result;

    } catch (error) {
        console.warn(`⚠️ Could not check ${serviceType} initialization:`, error.message);

        // Return conservative result (assume not initialized)
        const result = {
            initialized: false,
            responseTime: 0,
            timestamp: Date.now(),
            serviceType,
            error: error.message
        };

        // Cache for shorter duration on errors
        serviceInitCache.set(cacheKey, { ...result, timestamp: Date.now() - (CACHE_DURATION * 0.9) });

        return result;
    }
};

/**
 * Get default health endpoint for known service types
 */
const getDefaultHealthEndpoint = (serviceType) => {
    const endpoints = {
        'chatbot': '/api/health/chatbot',
        'external_ai': '/api/health/external-ai',
        'openai': '/api/health/openai',
        'anthropic': '/api/health/anthropic',
        'ollama': '/api/health/ollama'
    };

    return endpoints[serviceType] || '/health';
};

/**
 * Check initialization status from health response based on service type
 */
const checkInitStatus = (response, serviceType) => {
    // STING chatbot service
    if (serviceType === 'chatbot') {
        return response?.service_initialized === true || response?.status === 'healthy';
    }

    // External AI service
    if (serviceType === 'external_ai') {
        return response?.status === 'ready' || response?.llm_loaded === true;
    }

    // Third-party services (OpenAI, Anthropic, etc.)
    if (['openai', 'anthropic', 'ollama'].includes(serviceType)) {
        return response?.status === 'available' || response?.models?.length > 0;
    }

    // Generic fallback
    return response?.status === 'healthy' || response?.ready === true;
};

/**
 * Get intelligent timeout for chat request based on service initialization
 * @param {string} serviceType - Type of service
 * @param {string} healthEndpoint - Optional health endpoint
 * @returns {Promise<number>} - Timeout in milliseconds
 */
export const getIntelligentTimeout = async (serviceType = 'chatbot', healthEndpoint = null) => {
    const TIMEOUT_UNINITIALIZED = 35000;  // 35s for first request (LLM loading)
    const TIMEOUT_INITIALIZED = 10000;     // 10s for normal requests
    const TIMEOUT_DEFAULT = 15000;         // 15s fallback if check fails

    try {
        const initStatus = await checkServiceInitialization(serviceType, healthEndpoint);

        if (initStatus.initialized) {
            console.log(`⚡ Service initialized - using fast timeout: ${TIMEOUT_INITIALIZED}ms`);
            return TIMEOUT_INITIALIZED;
        } else {
            console.log(`⏳ Service initializing - using extended timeout: ${TIMEOUT_UNINITIALIZED}ms`);
            return TIMEOUT_UNINITIALIZED;
        }
    } catch (error) {
        console.warn(`⚠️ Timeout check failed, using default: ${TIMEOUT_DEFAULT}ms`);
        return TIMEOUT_DEFAULT;
    }
};

/**
 * Clear initialization cache (useful after service restarts)
 */
export const clearInitCache = (serviceType = null) => {
    if (serviceType) {
        // Clear specific service
        for (const [key] of serviceInitCache) {
            if (key.startsWith(serviceType + ':')) {
                serviceInitCache.delete(key);
            }
        }
        console.log(`🧹 Cleared init cache for ${serviceType}`);
    } else {
        // Clear all
        serviceInitCache.clear();
        console.log('🧹 Cleared all init cache');
    }
};

/**
 * React hook for intelligent chat timeouts
 * Usage in components:
 *
 * const { getTimeout, checkInit } = useChatServiceTimeout('chatbot');
 * const timeout = await getTimeout(); // Returns intelligent timeout
 * const status = await checkInit();   // Returns init status
 */
export const useChatServiceTimeout = (serviceType = 'chatbot', healthEndpoint = null) => {
    return {
        getTimeout: () => getIntelligentTimeout(serviceType, healthEndpoint),
        checkInit: () => checkServiceInitialization(serviceType, healthEndpoint),
        clearCache: () => clearInitCache(serviceType)
    };
};

/**
 * Preload initialization status (call on app startup)
 * This warms up the cache so first chat requests don't need to wait
 */
export const preloadServiceStatus = async (services = ['chatbot', 'external_ai']) => {
    console.log('🔄 Preloading service initialization status...');

    const checks = services.map(service =>
        checkServiceInitialization(service).catch(err => {
            console.warn(`Failed to preload ${service}:`, err.message);
            return null;
        })
    );

    const results = await Promise.all(checks);
    const initialized = results.filter(r => r?.initialized).map(r => r.serviceType);

    console.log(`✅ Preloaded ${initialized.length}/${services.length} services:`, initialized);
    return results;
};

export default {
    checkServiceInitialization,
    getIntelligentTimeout,
    clearInitCache,
    useChatServiceTimeout,
    preloadServiceStatus
};
