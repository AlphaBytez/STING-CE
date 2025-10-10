import axios from 'axios';

// Get API base URLs from window.env or environment variables
const API_URL = window.env?.REACT_APP_API_URL || process.env.REACT_APP_API_URL || 'https://localhost:5050';
const KRATOS_URL = window.env?.REACT_APP_KRATOS_PUBLIC_URL || process.env.REACT_APP_KRATOS_PUBLIC_URL || '';

// Main API client for backend services
// Use empty baseURL to work through proxy (like kratosClient)
const apiClient = axios.create({
    baseURL: '', // Empty base URL to use relative paths through the proxy
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Kratos API client for authentication
// For browser use, we don't need to set a base URL since we're using the proxy
// The setupProxy.js will handle forwarding requests to Kratos
const kratosClient = axios.create({
    baseURL: '', // Empty base URL to use relative paths through the proxy
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Request/Response interceptors for error handling only
apiClient.interceptors.response.use(
    response => response,
    error => {
        // Only log actual errors, not every request
        if (error.response?.status >= 500) {
            console.error('Server error:', error.response.status, error.config?.url);
        }
        return Promise.reject(error);
    }
);

kratosClient.interceptors.response.use(
    response => response,
    error => {
        // Only log actual errors
        if (error.response?.status >= 500) {
            console.error('Kratos error:', error.response.status, error.config?.url);
        }
        return Promise.reject(error);
    }
);

export { kratosClient };
export default apiClient;