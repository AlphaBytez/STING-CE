import axios from 'axios';

// Create a centralized API client with consistent authentication handling
const apiClient = axios.create({
  withCredentials: true, // Always include cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to log outgoing requests
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API Client] ${config.method?.toUpperCase()} ${config.url}`);
    // Log cookies being sent
    console.log('[API Client] Cookies:', document.cookie);
    return config;
  },
  (error) => {
    console.error('[API Client] Request error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle authentication errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      console.error('[API Client] Authentication error - user not authenticated');
      // Log the error details
      console.error('[API Client] Error details:', error.response?.data);
      
      // Only redirect for certain paths that definitely require auth
      // Don't redirect for honey jar endpoints as they might have public access
      const currentPath = window.location.pathname;
      const requestUrl = error.config?.url || '';
      
      // Don't redirect if:
      // 1. Already on login/register page
      // 2. Accessing knowledge/honey-jar endpoints (might have public jars)
      // 3. Accessing public endpoints
      const shouldRedirect = !currentPath.includes('/login') && 
                           !currentPath.includes('/register') &&
                           !requestUrl.includes('/knowledge/') &&
                           !requestUrl.includes('/public');
      
      if (shouldRedirect) {
        console.log('[API Client] Authentication required - redirecting to login...');
        // Store the current location to redirect back after login
        sessionStorage.setItem('redirectAfterLogin', window.location.href);
        window.location.href = '/login';
      }
    }

    // Handle 403 2FA setup required
    if (error.response?.status === 403) {
      const errorData = error.response?.data;

      // Handle METHOD_REQUIRED (AAL2 authentication required)
      if (errorData?.code === 'METHOD_REQUIRED' || errorData?.error === 'SPECIFIC_METHOD_REQUIRED') {
        console.log('[API Client] 🔐 Level 2 authentication required - redirecting to security upgrade');
        console.log('[API Client] Required methods:', errorData.required_methods);

        const currentPath = window.location.pathname;
        // Don't redirect if already on security-upgrade
        if (!currentPath.includes('/security-upgrade')) {
          // Store operation context
          const operation = errorData.operation || 'ACCESS_PROTECTED_RESOURCE';
          const tier = 2; // AAL2

          // Redirect to security-upgrade with return URL
          const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.href = `/security-upgrade?reason=${encodeURIComponent(operation)}&tier=${tier}&return_to=${returnUrl}`;
        }
        return Promise.reject(error);
      }

      if (errorData?.error === '2FA_SETUP_REQUIRED') {
        console.log('[API Client] 2FA setup required - redirecting to security settings');
        console.log('[API Client] Missing 2FA methods:', errorData.missing);

        const currentPath = window.location.pathname;
        // Don't redirect if already on security settings OR during AAL2 flow
        const isAAL2Flow = sessionStorage.getItem('aal2_passkey_setup');
        if (!currentPath.includes('/dashboard/settings') && !isAAL2Flow) {
          // Navigate to clean settings URL without query parameters to avoid stale flows
          window.location.href = '/dashboard/settings/security';
        } else if (isAAL2Flow) {
          console.log('🔐 apiClient: Skipping redirect during AAL2 passkey setup flow');
        }
        return Promise.reject(error);
      }

      // Handle passkey requirement for sensitive operations
      if (errorData?.error === 'PASSKEY_REQUIRED') {
        console.log('[API Client] Passkey required for sensitive operation - redirecting to security settings');

        const currentPath = window.location.pathname;
        // Don't redirect if already on security settings
        if (!currentPath.includes('/dashboard/settings')) {
          // Show a brief message before redirecting
          if (window.confirm('This operation requires passkey authentication. Set up passkey now?')) {
            // Navigate to clean settings URL without query parameters
            window.location.href = '/dashboard/settings/security';
          }
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// Convenience methods for common operations
export const api = {
  // WebAuthn endpoints
  webauthn: {
    registrationBegin: (data) => apiClient.post('/api/webauthn/registration/begin', data),
    registrationComplete: (data) => apiClient.post('/api/webauthn/registration/complete', data),
    authenticationBegin: (data) => apiClient.post('/api/webauthn/authentication/begin', data),
    authenticationComplete: (data) => apiClient.post('/api/webauthn/authentication/complete', data),
  },
  
  // Session endpoints (using backend proxy for proper cookie handling)
  session: {
    whoami: () => apiClient.get('/api/session/whoami'),
    logout: () => apiClient.post('/api/session/logout'),
  },
  
  // Auth endpoints
  auth: {
    checkUser: (email) => apiClient.post('/api/auth/check-user', { email }),
    getSession: () => apiClient.get('/api/auth/me'),
    clearSession: () => apiClient.post('/api/auth/clear-session'),
    testSession: () => apiClient.get('/api/auth/test-session'),
    me: () => apiClient.get('/api/auth/me'),
    passkeyStatus: () => apiClient.get('/api/auth/passkey-status'),
  },
  
  // Knowledge/Honey Jar endpoints
  knowledge: {
    listHoneyJars: () => apiClient.get('/api/knowledge/honey-jars'),
    getHoneyJar: (id) => apiClient.get(`/api/knowledge/honey-jars/${id}`),
    createHoneyJar: (data) => apiClient.post('/api/knowledge/honey-jars', data),
    updateHoneyJar: (id, data) => apiClient.put(`/api/knowledge/honey-jars/${id}`, data),
    deleteHoneyJar: (id) => apiClient.delete(`/api/knowledge/honey-jars/${id}`),
    uploadDocuments: (honeyJarId, formData) => apiClient.post(`/api/knowledge/honey-jars/${honeyJarId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    search: (data) => apiClient.post('/api/knowledge/search', data),
  }
};