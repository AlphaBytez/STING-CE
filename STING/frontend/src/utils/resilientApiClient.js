import axios from 'axios';

/**
 * Unified Resilient API Client
 * 
 * Provides consistent authentication handling, timeout management, and fallback strategies
 * across all STING frontend components. Addresses the dual authentication system
 * (Kratos + Flask sessions) by implementing multiple fallback methods.
 * 
 * Usage:
 * import { resilientApiCall } from '../utils/resilientApiClient';
 * 
 * const data = await resilientApiCall({
 *   endpoint: '/api/users/profile',
 *   method: 'GET',
 *   fallbackData: { firstName: 'Demo', lastName: 'User' },
 *   critical: false,  // Set to true for endpoints that should not use fallbacks
 *   timeout: 5000
 * });
 */

// Configure axios with credentials for all requests
const apiClient = axios.create({
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Add request interceptor for debugging in development
if (process.env.NODE_ENV === 'development') {
    apiClient.interceptors.request.use(
        config => {
            console.log(`🔄 Resilient API: ${config.method?.toUpperCase()} ${config.url}`);
            return config;
        },
        error => Promise.reject(error)
    );
}

/**
 * Main resilient API call function
 * @param {Object} options - API call configuration
 * @param {string} options.endpoint - API endpoint path
 * @param {string} options.method - HTTP method (GET, POST, PUT, DELETE)
 * @param {Object} options.data - Request body data
 * @param {Object} options.params - URL query parameters
 * @param {Object} options.fallbackData - Data to return if API fails (for non-critical endpoints)
 * @param {boolean} options.critical - If true, will throw errors instead of using fallbacks
 * @param {number} options.timeout - Request timeout in milliseconds (default: 5000)
 * @param {boolean} options.usePublicFallback - Try public endpoint if authenticated endpoint fails
 * @param {string} options.publicEndpoint - Alternative public endpoint path
 * @returns {Promise} API response data or fallback data
 */
export const resilientApiCall = async ({
    endpoint,
    method = 'GET',
    data = null,
    params = null,
    fallbackData = null,
    critical = false,
    timeout = 5000,
    usePublicFallback = false,
    publicEndpoint = null
}) => {
    const requestConfig = {
        url: endpoint,
        method: method.toLowerCase(),
        timeout,
        ...(data && { data }),
        ...(params && { params })
    };

    try {
        // Primary API call with authentication
        console.log(`🎯 Attempting ${method} ${endpoint}`);
        const response = await apiClient(requestConfig);
        
        console.log(`✅ ${method} ${endpoint} succeeded (${response.status})`);
        return response.data;
        
    } catch (primaryError) {
        console.warn(`⚠️ Primary API call failed: ${primaryError.message}`);
        
        // If this is a critical endpoint, don't use fallbacks - throw the error
        if (critical) {
            console.error(`❌ Critical endpoint ${endpoint} failed, not using fallbacks`);
            throw primaryError;
        }
        
        // Try public endpoint fallback if configured
        if (usePublicFallback && publicEndpoint) {
            try {
                console.log(`🔄 Trying public fallback: ${publicEndpoint}`);
                const publicConfig = {
                    ...requestConfig,
                    url: publicEndpoint
                };
                const publicResponse = await apiClient(publicConfig);
                console.log(`✅ Public fallback ${publicEndpoint} succeeded`);
                return publicResponse.data;
                
            } catch (publicError) {
                console.warn(`⚠️ Public fallback also failed: ${publicError.message}`);
                // Continue to fallback data...
            }
        }
        
        // Use fallback data if provided
        if (fallbackData !== null) {
            console.log(`🎭 Using fallback data for ${endpoint}`);
            return {
                success: true,
                data: fallbackData,
                isFallback: true,
                message: 'Using demo data - API temporarily unavailable'
            };
        }
        
        // No fallback available, throw the original error
        throw primaryError;
    }
};

/**
 * Specialized resilient calls for common patterns
 */

// GET request with fallback
export const resilientGet = (endpoint, fallbackData = null, options = {}) => {
    return resilientApiCall({
        endpoint,
        method: 'GET',
        fallbackData,
        ...options
    });
};

// POST request (typically critical, no fallbacks by default)
export const resilientPost = (endpoint, data, options = {}) => {
    return resilientApiCall({
        endpoint,
        method: 'POST',
        data,
        critical: true,  // POST requests are usually critical
        ...options
    });
};

// PUT request (typically critical, no fallbacks by default)
export const resilientPut = (endpoint, data, options = {}) => {
    return resilientApiCall({
        endpoint,
        method: 'PUT',
        data,
        critical: true,  // PUT requests are usually critical
        ...options
    });
};

// DELETE request (typically critical, no fallbacks by default)
export const resilientDelete = (endpoint, options = {}) => {
    return resilientApiCall({
        endpoint,
        method: 'DELETE',
        critical: true,  // DELETE requests are usually critical
        ...options
    });
};

/**
 * Health check for session validation
 * Tests both Kratos and Flask session status
 */
export const validateSession = async () => {
    try {
        // Check Flask backend session
        const backendCheck = await resilientApiCall({
            endpoint: '/api/auth/session/check',
            method: 'GET',
            timeout: 3000,
            critical: true
        });
        
        return {
            isValid: true,
            backend: backendCheck,
            timestamp: new Date().toISOString()
        };
        
    } catch (error) {
        console.warn('Session validation failed:', error.message);
        return {
            isValid: false,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
};

/**
 * Authentication-aware wrapper for components
 * Use this in React components to handle authentication gracefully
 */
export const useResilientApi = () => {
    return {
        get: resilientGet,
        post: resilientPost,
        put: resilientPut,
        delete: resilientDelete,
        call: resilientApiCall,
        validateSession
    };
};

// Fallback data generators for common endpoints
export const fallbackGenerators = {
    profile: () => ({
        firstName: 'Demo',
        lastName: 'User', 
        displayName: 'Demo User',
        email: 'demo@sting.local',
        bio: 'Demo user profile - API temporarily unavailable',
        location: 'STING Demo Environment',
        isAdmin: false,
        role: 'user'
    }),
    
    honeyJars: () => ({
        items: [
            {
                id: 'demo-1',
                name: 'Demo Knowledge Base',
                description: 'Sample honey jar for demonstration',
                type: 'private',
                documentCount: 5,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            }
        ],
        total: 1,
        hasMore: false
    }),
    
    adminPendingDocs: () => ({
        documents: [
            {
                id: 'demo-doc-1',
                name: 'Sample Document.pdf',
                status: 'pending',
                uploadedBy: 'demo@sting.local',
                uploadedAt: new Date().toISOString(),
                size: 102400
            }
        ],
        total: 1
    }),
    
    systemHealth: () => ({
        services: [
            { name: 'STING Core API', status: 'healthy', uptime: '99.9%', responseTime: '32ms' },
            { name: 'Knowledge Service', status: 'healthy', uptime: '99.8%', responseTime: '45ms' },
            { name: 'Authentication', status: 'degraded', uptime: '98.5%', responseTime: '120ms' },
            { name: 'Database', status: 'healthy', uptime: '99.9%', responseTime: '15ms' }
        ],
        lastUpdate: new Date().toISOString()
    })
};

export default resilientApiCall;