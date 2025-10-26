/**
 * System Configuration API
 * Handles system-level configuration like jar system setup
 */

import api from './knowledgeApi';

const BASE_URL = '/api/users';

export const systemApi = {
  /**
   * Get STING CE jar system configuration for default BeeChat context
   */
  getSystemJarConfig: async () => {
    try {
      const response = await fetch(`${BASE_URL}/system-jar-config`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 404) {
          // System jar not configured - this is expected on fresh installs before setup
          return { system_jar_id: null, configured: false };
        }
        if (response.status === 401) {
          // Authentication not ready - return default config to avoid blocking UI
          console.warn('System API: Authentication not ready, using default config');
          return { system_jar_id: null, configured: false };
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        ...data,
        configured: !!data.system_jar_id
      };
    } catch (error) {
      console.error('Error fetching system jar config:', error);
      // Return default config instead of throwing to prevent blocking UI
      return { system_jar_id: null, configured: false };
    }
  },

  /**
   * Get honey jar details by ID to populate default context
   */
  getHoneyJarDetails: async (jarId) => {
    try {
      const response = await fetch(`/api/honey-jars/${jarId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching honey jar details:', error);
      throw error;
    }
  },

  /**
   * Get user's BeeChat preferences
   */
  getBeeChatPreferences: async () => {
    try {
      const response = await fetch(`${BASE_URL}/beechat-preferences`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching BeeChat preferences:', error);
      throw error;
    }
  },

  /**
   * Update user's BeeChat preferences (limited in CE edition)
   */
  updateBeeChatPreferences: async (preferences) => {
    try {
      const response = await fetch(`${BASE_URL}/beechat-preferences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(preferences),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating BeeChat preferences:', error);
      throw error;
    }
  }
};

export default systemApi;