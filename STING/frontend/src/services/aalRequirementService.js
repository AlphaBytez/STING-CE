/**
 * Service to check AAL requirements from backend
 * This ensures frontend and backend are always in sync
 */

import axios from 'axios';

class AALRequirementService {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 2 * 60 * 1000; // 2 minutes (shorter than security cache)
  }

  /**
   * Check if a specific route/operation requires AAL2
   * @param {string} route - The route path (e.g., '/dashboard/reports')
   * @returns {Promise<Object>} - AAL requirements
   */
  async checkAALRequirement(route) {
    const cacheKey = `aal_req_${route}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }

    try {
      // Check with backend what AAL level this route requires
      const response = await axios.get('/api/auth/aal-requirements', {
        params: { route },
        withCredentials: true
      });

      const requirement = {
        requiresAAL2: response.data.requires_aal2 || false,
        minAAL: response.data.min_aal || 'aal1',
        reason: response.data.reason || 'general_access',
        message: response.data.message || 'Additional authentication required',
        gracePeriodMinutes: response.data.grace_period_minutes || 15
      };

      // Cache the result
      this.cache.set(cacheKey, {
        data: requirement,
        timestamp: Date.now()
      });

      return requirement;

    } catch (error) {
      console.error('Error checking AAL requirements:', error);
      
      // Fallback: Use frontend-defined sensitive routes
      const sensitiveRoutes = ['/dashboard/reports', '/dashboard/admin'];
      const isSensitive = sensitiveRoutes.some(r => route.startsWith(r));
      
      return {
        requiresAAL2: isSensitive,
        minAAL: isSensitive ? 'aal2' : 'aal1',
        reason: 'fallback_detection',
        message: 'This operation requires additional verification',
        gracePeriodMinutes: 15
      };
    }
  }

  /**
   * Check current user's AAL status against requirements
   * @param {string} route - The route to check
   * @returns {Promise<Object>} - Current status vs requirements
   */
  async checkCurrentAALStatus(route) {
    try {
      const [requirement, session] = await Promise.all([
        this.checkAALRequirement(route),
        axios.get('/api/auth/me', { withCredentials: true })
      ]);

      const sessionData = session.data;
      // UPDATED: Handle Flask backend response format
      const currentAAL = sessionData.auth_method === 'enhanced_webauthn' ? 'aal2' : 'aal1';
      
      // Check if user has recent second factor authentication
      const gracePeriod = requirement.gracePeriodMinutes * 60 * 1000;
      const cutoffTime = new Date(Date.now() - gracePeriod);
      
      // For Flask backend, check if session has WebAuthn authentication
      const recentSecondFactor = sessionData.auth_method === 'enhanced_webauthn' && 
        sessionData.session?.authenticated_at &&
        new Date(sessionData.session.authenticated_at) > cutoffTime;

      const meetsRequirement = requirement.requiresAAL2 
        ? (currentAAL === 'aal2' && recentSecondFactor)
        : true;

      return {
        meetsRequirement,
        requirement,
        currentAAL,
        recentSecondFactor,
        needsStepUp: requirement.requiresAAL2 && !meetsRequirement
      };

    } catch (error) {
      console.error('Error checking current AAL status:', error);
      return {
        meetsRequirement: false,
        needsStepUp: true,
        error: error.message
      };
    }
  }

  clearCache() {
    this.cache.clear();
  }
}

export default new AALRequirementService();