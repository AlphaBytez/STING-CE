// Kratos helper utilities for authentication flows

/**
 * Extract CSRF token from Kratos flow
 * @param {Object} flowData - Kratos flow response data
 * @returns {string|null} - CSRF token or null if not found
 */
export function extractCSRFToken(flowData) {
  if (!flowData?.ui?.nodes) return null;
  
  const csrfNode = flowData.ui.nodes.find(
    n => n.attributes?.name === 'csrf_token'
  );
  
  return csrfNode?.attributes?.value || null;
}

/**
 * Check if Kratos flow has specific authentication method
 * @param {Object} flowData - Kratos flow response data
 * @param {string} method - Method to check for ('code', 'webauthn', 'totp', etc.)
 * @returns {boolean} - Whether method is available
 */
export function hasMethod(flowData, method) {
  if (!flowData?.ui?.nodes) return false;
  
  return flowData.ui.nodes.some(
    n => n.attributes?.name === 'method' && n.attributes?.value === method
  );
}

/**
 * Get available authentication methods from Kratos flow
 * @param {Object} flowData - Kratos flow response data
 * @returns {string[]} - Array of available method names
 */
export function getAvailableMethods(flowData) {
  if (!flowData?.ui?.nodes) return [];
  
  return flowData.ui.nodes
    .filter(n => n.attributes?.name === 'method')
    .map(n => n.attributes?.value)
    .filter(Boolean);
}

/**
 * Extract error messages from Kratos flow response
 * @param {Object} flowData - Kratos flow response data
 * @returns {string[]} - Array of error messages
 */
export function extractErrorMessages(flowData) {
  if (!flowData?.ui?.messages) return [];
  
  return flowData.ui.messages
    .filter(m => m.type === 'error')
    .map(m => m.text);
}

/**
 * Extract info messages from Kratos flow response
 * @param {Object} flowData - Kratos flow response data
 * @returns {string[]} - Array of info messages
 */
export function extractInfoMessages(flowData) {
  if (!flowData?.ui?.messages) return [];
  
  return flowData.ui.messages
    .filter(m => m.type === 'info')
    .map(m => m.text);
}

/**
 * Clean action URL by removing localhost references
 * @param {string} actionUrl - Original action URL from Kratos
 * @returns {string} - Cleaned URL for proxy compatibility
 */
export function cleanActionUrl(actionUrl) {
  if (typeof actionUrl !== 'string') return actionUrl;
  
  // Replace hardcoded localhost URLs with proxy-friendly URLs
  return actionUrl.replace(/https?:\/\/[^\/]+/, '');
}

/**
 * Create form data for Kratos submission
 * @param {Object} fields - Key-value pairs of form fields
 * @param {Object} flowData - Kratos flow data (for CSRF token)
 * @returns {URLSearchParams} - Form data ready for submission
 */
export function createFormData(fields, flowData = null) {
  const formData = new URLSearchParams();
  
  // Add provided fields
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  });
  
  // Add CSRF token if available
  if (flowData) {
    const csrfToken = extractCSRFToken(flowData);
    if (csrfToken) {
      formData.append('csrf_token', csrfToken);
    }
  }
  
  return formData;
}

/**
 * Check if Kratos response indicates successful authentication
 * @param {Object} response - Axios response from Kratos
 * @returns {boolean} - Whether authentication was successful
 */
export function isAuthenticationSuccess(response) {
  return response.status === 200 || 
         response.data?.state === 'passed_challenge' ||
         response.data?.session?.active === true;
}

/**
 * Check if Kratos response requires AAL2 step-up
 * @param {Object} response - Axios response from Kratos
 * @returns {boolean} - Whether AAL2 step-up is required
 */
export function requiresAAL2StepUp(response) {
  return response.status === 422 && 
         response.data?.redirect_browser_to &&
         response.data.redirect_browser_to.includes('aal=aal2');
}

/**
 * Extract redirect URL from Kratos response
 * @param {Object} response - Axios response from Kratos
 * @returns {string|null} - Redirect URL or null if not found
 */
export function extractRedirectUrl(response) {
  return response.data?.redirect_browser_to || null;
}

/**
 * Process continue_with actions from Kratos response
 * @param {Array} continueWith - continue_with array from Kratos response
 * @returns {Promise<boolean>} - Whether session completion was successful
 */
export async function processContinueWithActions(continueWith) {
  if (!continueWith || !Array.isArray(continueWith) || continueWith.length === 0) {
    console.log('ℹ️ No continue_with actions to process');
    return false;
  }
  
  console.log('🔄 Processing continue_with actions:', continueWith);
  
  for (const action of continueWith) {
    if (action.action === 'set_ory_session_token') {
      console.log('🔐 Found set_ory_session_token action, completing session...');
      
      try {
        const sessionUrl = action.redirect_browser_to || '/api/auth/me';
        const sessionResponse = await fetch(sessionUrl, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });
        
        console.log('🔐 Session completion response:', sessionResponse.status);
        
        if (sessionResponse.ok) {
          const sessionData = await sessionResponse.json();
          console.log('✅ Kratos session established:', {
            identity: sessionData.identity?.id,
            active: sessionData.active,
            aal: sessionData.authenticator_assurance_level
          });
          return true;
        } else {
          console.warn('⚠️ Session completion failed:', sessionResponse.status);
        }
      } catch (sessionError) {
        console.error('❌ Error completing session:', sessionError);
      }
    } else if (action.action === 'redirect_browser_to') {
      console.warn('⚠️ Unexpected redirect_browser_to in continue_with - this may indicate a flow configuration issue');
    }
  }
  
  return false;
}

/**
 * Check if current session exists and is active
 * @returns {Promise<Object|null>} - Session data or null if no session
 */
export async function checkCurrentSession() {
  try {
    const sessionResponse = await fetch('/api/auth/me', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });
    
    if (sessionResponse.ok) {
      const sessionData = await sessionResponse.json();
      if (sessionData?.active) {
        return sessionData;
      }
    }
  } catch (error) {
    console.log('🔐 No active session found:', error.message);
  }
  
  return null;
}