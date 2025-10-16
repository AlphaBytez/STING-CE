/**
 * Legacy Theme Context - Migration Shim
 * 
 * This provides compatibility for components still using the old ThemeContext
 * while the new CSS-based theme system handles actual theming.
 * 
 * TODO: Migrate remaining components to use CSS variables directly
 * and remove this compatibility layer.
 */

import React, { createContext, useContext } from 'react';
import { useTheme as useNewTheme } from '../components/theme/ThemeManager';

const LegacyThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(LegacyThemeContext);
  const newTheme = useNewTheme();

  if (!context) {
    // Return dummy values for legacy compatibility
    return {
      currentTheme: newTheme?.currentTheme || 'modern-glass',
      darkMode: true,
      changeTheme: newTheme?.switchTheme || (() => {}),
      toggleDarkMode: () => {},
      themes: {
        dark: {
          id: 'dark',
          name: 'Modern Glass',
          colors: {
            primary: '#eab308',
            background: '#0f172a',
            text: '#f1f5f9'
          }
        }
      },
      themeColors: {
        primary: '#eab308',
        background: '#0f172a', 
        text: '#f1f5f9'
      }
    };
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const newTheme = useNewTheme();

  // Provide legacy compatibility values
  const value = {
    currentTheme: newTheme?.currentTheme || 'modern-glass',
    darkMode: true,
    changeTheme: newTheme?.switchTheme || (() => {}),
    toggleDarkMode: () => {},
    themes: {
      dark: {
        id: 'dark', 
        name: 'Modern Glass',
        colors: {
          primary: '#eab308',
          background: '#0f172a',
          text: '#f1f5f9'
        }
      }
    },
    themeColors: {
      primary: '#eab308',
      background: '#0f172a',
      text: '#f1f5f9'
    }
  };

  return (
    <LegacyThemeContext.Provider value={value}>
      {children}
    </LegacyThemeContext.Provider>
  );
};