/**
 * Theme Service
 * Handles theme preferences with database backend integration
 */

import preferencesService from './preferencesService';

class ThemeService {
  
  /**
   * Get user's theme preferences from database or localStorage fallback
   */
  async getThemePreferences() {
    try {
      // Try database first
      const response = await preferencesService.getThemePreferences();
      
      if (response && response.preferences) {
        console.log('Theme: Loaded from database');
        return response.preferences;
      }
      
      // Fallback to localStorage
      console.log('Theme: No database preferences, using localStorage fallback');
      return this.getThemeFromLocalStorage();
    } catch (error) {
      console.warn('Theme: Database load failed, using localStorage:', error);
      return this.getThemeFromLocalStorage();
    }
  }
  
  /**
   * Save theme preferences to database with localStorage fallback
   */
  async saveThemePreferences(themePreferences, fallbackToLocalStorage = true) {
    try {
      await preferencesService.updateThemePreferences(themePreferences);
      console.log('Theme: Saved to database successfully');
      return true;
    } catch (error) {
      console.warn('Theme: Database save failed:', error);
      
      if (fallbackToLocalStorage) {
        try {
          localStorage.setItem('sting-theme', JSON.stringify(themePreferences));
          console.log('Theme: Saved to localStorage as fallback');
          return true;
        } catch (localError) {
          console.error('Theme: LocalStorage save also failed:', localError);
        }
      }
      
      return false;
    }
  }
  
  /**
   * Get theme from localStorage (fallback method)
   */
  getThemeFromLocalStorage() {
    try {
      const saved = localStorage.getItem('sting-theme');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      console.error('Failed to parse theme from localStorage:', error);
    }
    
    // Return default theme preferences
    return {
      theme: 'modern-glass',
      darkMode: true,
      compactMode: false,
      animations: true
    };
  }
  
  /**
   * Auto-migrate theme preferences from localStorage to database if needed
   */
  async autoMigrateTheme() {
    try {
      const status = await preferencesService.checkDatabaseMigrationStatus();
      
      if (status.needsMigration) {
        const localTheme = this.getThemeFromLocalStorage();
        const localData = preferencesService.extractLocalStorageData();
        
        if (localTheme && Object.keys(localTheme).length > 0) {
          localData.theme = localTheme;
          
          const result = await preferencesService.migrateFromLocalStorage(localData);
          console.log('Theme: Auto-migration completed:', result);
          return true;
        }
      }
      
      return false;
    } catch (error) {
      console.error('Theme: Auto-migration failed:', error);
      return false;
    }
  }
  
  /**
   * Get organization theme defaults (admin only)
   */
  async getOrganizationThemeDefaults() {
    try {
      const response = await preferencesService.getOrganizationPreferences();
      
      if (response && response.preferences) {
        const themeDefault = response.preferences.find(pref => pref.preference_type === 'theme');
        return themeDefault ? themeDefault.config : null;
      }
      
      return null;
    } catch (error) {
      console.error('Failed to get organization theme defaults:', error);
      return null;
    }
  }
  
  /**
   * Set organization theme defaults (admin only)
   */
  async setOrganizationThemeDefaults(themeConfig) {
    try {
      await preferencesService.updateOrganizationPreference('theme', themeConfig, 1);
      return true;
    } catch (error) {
      console.error('Failed to set organization theme defaults:', error);
      return false;
    }
  }
  
  /**
   * Push theme preferences to all users (admin only)
   */
  async pushThemeToAllUsers(themeConfig, forceUpdate = false) {
    try {
      // First set organization default
      await this.setOrganizationThemeDefaults(themeConfig);
      
      // Then push to all users
      const result = await preferencesService.pushPreferencesToUsers(['theme'], null, forceUpdate);
      return result;
    } catch (error) {
      console.error('Failed to push theme to users:', error);
      return false;
    }
  }
  
  /**
   * Get available themes
   */
  getAvailableThemes() {
    return [
      {
        id: 'modern-glass',
        name: 'Modern Glass',
        description: 'Glassmorphism with modern aesthetics',
        preview: '/theme-previews/modern-glass.png'
      },
      {
        id: 'modern-lite',
        name: 'Modern Lite',
        description: 'Clean and lightweight modern design',
        preview: '/theme-previews/modern-lite.png'
      },
      {
        id: 'minimal-performance',
        name: 'Minimal Performance',
        description: 'Ultra-lightweight for maximum performance',
        preview: '/theme-previews/minimal-performance.png'
      },
      {
        id: 'retro-terminal',
        name: 'Retro Terminal',
        description: 'Classic terminal-inspired theme',
        preview: '/theme-previews/retro-terminal.png'
      }
    ];
  }
  
  /**
   * Validate theme configuration
   */
  validateThemeConfig(config) {
    const validThemes = this.getAvailableThemes().map(t => t.id);
    
    if (!config || typeof config !== 'object') {
      return false;
    }
    
    if (!validThemes.includes(config.theme)) {
      return false;
    }
    
    const booleanFields = ['darkMode', 'compactMode', 'animations'];
    for (const field of booleanFields) {
      if (config[field] !== undefined && typeof config[field] !== 'boolean') {
        return false;
      }
    }
    
    return true;
  }
  
  /**
   * Apply theme configuration to document
   */
  applyThemeToDocument(themeConfig) {
    try {
      const root = document.documentElement;
      
      // Set theme class
      document.body.className = document.body.className.replace(/theme-\w+/g, '');
      document.body.classList.add(`theme-${themeConfig.theme}`);
      
      // Set dark mode
      if (themeConfig.darkMode) {
        root.classList.add('dark');
        root.classList.remove('light');
      } else {
        root.classList.add('light');
        root.classList.remove('dark');
      }
      
      // Set compact mode
      if (themeConfig.compactMode) {
        root.classList.add('compact');
      } else {
        root.classList.remove('compact');
      }
      
      // Set animations
      if (!themeConfig.animations) {
        root.classList.add('no-animations');
      } else {
        root.classList.remove('no-animations');
      }
      
      // Store in CSS custom properties for theme components
      root.style.setProperty('--theme-name', themeConfig.theme);
      root.style.setProperty('--dark-mode', themeConfig.darkMode ? '1' : '0');
      root.style.setProperty('--compact-mode', themeConfig.compactMode ? '1' : '0');
      root.style.setProperty('--animations-enabled', themeConfig.animations ? '1' : '0');
      
      console.log('Theme: Applied configuration to document:', themeConfig);
    } catch (error) {
      console.error('Theme: Failed to apply configuration:', error);
    }
  }
}

// Create and export singleton instance
const themeService = new ThemeService();
export default themeService;