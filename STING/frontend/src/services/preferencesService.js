/**
 * Preferences Service
 * Handles API calls for user and organization preferences
 */

const API_BASE = '/api/preferences';

class PreferencesService {
  
  // User Preference Methods
  
  /**
   * Get user's navigation preferences
   */
  async getNavigationPreferences() {
    try {
      const response = await fetch(`${API_BASE}/navigation`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get navigation preferences:', error);
      throw error;
    }
  }
  
  /**
   * Update user's navigation preferences
   */
  async updateNavigationPreferences(config, version = 4) {
    try {
      const response = await fetch(`${API_BASE}/navigation`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config, version }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to update navigation preferences:', error);
      throw error;
    }
  }
  
  /**
   * Get user's theme preferences
   */
  async getThemePreferences() {
    try {
      const response = await fetch(`${API_BASE}/theme`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get theme preferences:', error);
      throw error;
    }
  }
  
  /**
   * Update user's theme preferences
   */
  async updateThemePreferences(preferences) {
    try {
      const response = await fetch(`${API_BASE}/theme`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preferences }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to update theme preferences:', error);
      throw error;
    }
  }
  
  /**
   * Get user's UI preferences
   */
  async getUIPreferences() {
    try {
      const response = await fetch(`${API_BASE}/ui`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get UI preferences:', error);
      throw error;
    }
  }
  
  /**
   * Update user's UI preferences
   */
  async updateUIPreferences(preferences) {
    try {
      const response = await fetch(`${API_BASE}/ui`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preferences }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to update UI preferences:', error);
      throw error;
    }
  }
  
  /**
   * Get all user preferences in one call
   */
  async getAllPreferences() {
    try {
      const response = await fetch(`${API_BASE}/all`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get all preferences:', error);
      throw error;
    }
  }
  
  /**
   * Migrate preferences from localStorage to database
   */
  async migrateFromLocalStorage(localStorageData) {
    try {
      const response = await fetch(`${API_BASE}/migrate-from-localstorage`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(localStorageData),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to migrate preferences:', error);
      throw error;
    }
  }
  
  // Admin/Organization Methods
  
  /**
   * Get organization default preferences (admin only)
   */
  async getOrganizationPreferences() {
    try {
      const response = await fetch(`${API_BASE}/organization`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get organization preferences:', error);
      throw error;
    }
  }
  
  /**
   * Update organization preference (admin only)
   */
  async updateOrganizationPreference(preferenceType, config, version = 1) {
    try {
      const response = await fetch(`${API_BASE}/organization/${preferenceType}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config, version }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to update organization preference:', error);
      throw error;
    }
  }
  
  /**
   * Push organization preferences to users (admin only)
   */
  async pushPreferencesToUsers(preferenceTypes, userIds = null, forceUpdate = false) {
    try {
      const response = await fetch(`${API_BASE}/push-to-users`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          preference_types: preferenceTypes,
          user_ids: userIds,
          force_update: forceUpdate,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to push preferences to users:', error);
      throw error;
    }
  }
  
  /**
   * Get user preference history (admin only)
   */
  async getUserPreferenceHistory(userId, limit = 10) {
    try {
      const response = await fetch(`${API_BASE}/history/${userId}?limit=${limit}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get preference history:', error);
      throw error;
    }
  }
  
  // Utility Methods
  
  /**
   * Check if user has database preferences (vs localStorage)
   */
  async checkDatabaseMigrationStatus() {
    try {
      const allPrefs = await this.getAllPreferences();
      const hasDbPrefs = allPrefs && (
        allPrefs.navigation || 
        allPrefs.theme || 
        allPrefs.ui
      );
      
      // Check if we have localStorage data that could be migrated
      const hasLocalStorageData = this.hasLocalStoragePreferences();
      
      return {
        hasDatabasePreferences: !!hasDbPrefs,
        hasLocalStorageData,
        needsMigration: hasLocalStorageData && !hasDbPrefs
      };
    } catch (error) {
      console.error('Failed to check migration status:', error);
      return {
        hasDatabasePreferences: false,
        hasLocalStorageData: false,
        needsMigration: false
      };
    }
  }
  
  /**
   * Check if localStorage has preference data
   */
  hasLocalStoragePreferences() {
    const navConfig = localStorage.getItem('sting-nav-config');
    const theme = localStorage.getItem('sting-theme');
    const uiPrefs = localStorage.getItem('sting-ui-preferences');
    
    return !!(navConfig || theme || uiPrefs);
  }
  
  /**
   * Extract localStorage data for migration
   */
  extractLocalStorageData() {
    const data = {};
    
    try {
      const navConfig = localStorage.getItem('sting-nav-config');
      if (navConfig) {
        const parsed = JSON.parse(navConfig);
        data.navigation = parsed;
        data.navigation_version = parsed.version || 4;
      }
    } catch (e) {
      console.warn('Failed to parse navigation config from localStorage:', e);
    }
    
    try {
      const theme = localStorage.getItem('sting-theme');
      if (theme) {
        data.theme = JSON.parse(theme);
      }
    } catch (e) {
      console.warn('Failed to parse theme from localStorage:', e);
    }
    
    try {
      const uiPrefs = localStorage.getItem('sting-ui-preferences');
      if (uiPrefs) {
        data.ui = JSON.parse(uiPrefs);
      }
    } catch (e) {
      console.warn('Failed to parse UI preferences from localStorage:', e);
    }
    
    return data;
  }
  
  /**
   * Auto-migrate localStorage data to database if needed
   */
  async autoMigrate() {
    try {
      const status = await this.checkDatabaseMigrationStatus();
      
      if (status.needsMigration) {
        console.log('Auto-migrating preferences from localStorage to database...');
        const localData = this.extractLocalStorageData();
        
        if (Object.keys(localData).length > 0) {
          const result = await this.migrateFromLocalStorage(localData);
          console.log('Migration completed:', result);
          return true;
        }
      }
      
      return false;
    } catch (error) {
      console.error('Auto-migration failed:', error);
      return false;
    }
  }
}

// Create and export singleton instance
const preferencesService = new PreferencesService();
export default preferencesService;