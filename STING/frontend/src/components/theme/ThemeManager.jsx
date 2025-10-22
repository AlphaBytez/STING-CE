import React, { createContext, useContext, useState, useEffect } from 'react';

// Available themes
export const THEMES = {
  MODERN: 'modern-glass',
  MODERN_OPTIMIZED: 'modern-glass-optimized',
  MODERN_LITE: 'modern-lite',
  MINIMAL: 'minimal-performance',
  RETRO: 'retro',
  RETRO_PERFORMANCE: 'retro-performance',
  GARDEN_GALAXY: 'garden-galaxy'
};

export const THEME_CONFIG = {
  [THEMES.MODERN]: {
    name: 'Modern Glass',
    description: 'Modern glassmorphism design with rich visual effects',
    category: 'Premium',
    performance: 'Standard',
    features: ['Glassmorphism', 'Blur effects', 'Gradients', 'Animations'],
    preview: '/theme-previews/modern-glass.png'
  },
  [THEMES.MODERN_OPTIMIZED]: {
    name: 'Modern Glass Optimized',
    description: 'GPU-optimized glassmorphism with 85% performance savings',
    category: 'Performance',
    performance: 'High Performance',
    features: ['Smart blur reduction', 'Optimized shadows', 'GPU-friendly effects', '85% GPU savings'],
    preview: '/theme-previews/modern-glass-optimized.png'
  },
  [THEMES.MODERN_LITE]: {
    name: 'Modern Lite',
    description: 'Clean modern design optimized for performance',
    category: 'Balanced',
    performance: 'Good Performance',
    features: ['Clean design', 'Lightweight', 'Smooth transitions', 'Optimized rendering'],
    preview: '/theme-previews/modern-lite.png'
  },
  [THEMES.MINIMAL]: {
    name: 'Minimal Performance',
    description: 'Ultra-minimal design for maximum performance',
    category: 'Performance',
    performance: 'Maximum Performance',
    features: ['Zero animations', 'Minimal colors', 'System fonts', 'Ultra-fast'],
    preview: '/theme-previews/minimal-performance.png'
  },
  [THEMES.RETRO]: {
    name: 'Retro Terminal',
    description: 'Full terminal experience with scanlines and effects',
    category: 'Experience',
    performance: 'Good Performance',
    features: ['Scanline effects', 'Terminal glow', 'Retro animations', 'Authentic feel'],
    preview: '/theme-previews/retro.png'
  },
  [THEMES.RETRO_PERFORMANCE]: {
    name: 'Retro Terminal - Performance',
    description: 'Terminal aesthetics optimized for maximum speed',
    category: 'Performance',
    performance: 'Maximum Performance',
    features: ['Zero animations', 'Terminal colors', 'Monospace fonts', 'Ultra-fast'],
    preview: '/theme-previews/retro-performance.png'
  },
  [THEMES.GARDEN_GALAXY]: {
    name: 'Garden Galaxy',
    description: 'Earthy cosmic theme with enhanced readability and green galaxy aesthetics',
    category: 'Experience',
    performance: 'Good Performance',
    features: ['Cosmic glass effects', 'Earthy green palette', 'Enhanced readability', 'Wide components'],
    preview: '/theme-previews/garden-galaxy.png'
  }
};

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState(() => {
    // Load theme from localStorage or default to modern glass optimized for better performance
    const savedTheme = localStorage.getItem('sting-theme');
    return savedTheme && Object.values(THEMES).includes(savedTheme) 
      ? savedTheme 
      : THEMES.MODERN_OPTIMIZED;
  });

  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    // Apply theme to document root
    const applyTheme = (theme) => {
      const root = document.documentElement;
      
      // Remove all theme classes
      Object.values(THEMES).forEach(t => {
        root.classList.remove(`theme-${t}`);
      });
      
      // Set data-theme attribute
      root.setAttribute('data-theme', theme);
      
      // Add theme class for any CSS that needs it
      root.classList.add(`theme-${theme}`);
      
      // Load theme-specific CSS if needed
      loadThemeCSS(theme);
    };

    const loadThemeCSS = (theme) => {
      // Remove existing theme stylesheets
      const existingLinks = document.querySelectorAll('link[data-theme-css]');
      existingLinks.forEach(link => link.remove());

      // Theme CSS mapping
      const themeCSS = {
        [THEMES.MODERN_OPTIMIZED]: '/theme/modern-glass-optimized.css',
        [THEMES.RETRO]: '/theme/retro-theme.css',
        [THEMES.RETRO_PERFORMANCE]: '/theme/retro-performance-theme.css',
        [THEMES.MODERN_LITE]: '/theme/modern-lite-theme.css',
        [THEMES.MINIMAL]: '/theme/minimal-performance-theme.css',
        [THEMES.GARDEN_GALAXY]: '/theme/garden-galaxy-theme.css'
        // MODERN theme uses the built-in floating-design CSS, no external CSS needed
      };

      // Load theme-specific CSS if it exists
      if (themeCSS[theme]) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = themeCSS[theme];
        link.setAttribute('data-theme-css', theme);
        document.head.appendChild(link);
      }
      // Modern theme uses the default CSS, no additional loading needed
    };

    applyTheme(currentTheme);
  }, [currentTheme]);

  const switchTheme = async (newTheme) => {
    if (newTheme === currentTheme || isTransitioning) return;

    setIsTransitioning(true);

    // Add a brief transition effect
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Small delay to show transition
    await new Promise(resolve => setTimeout(resolve, 100));

    setCurrentTheme(newTheme);
    localStorage.setItem('sting-theme', newTheme);

    // Remove transition after theme is applied
    setTimeout(() => {
      document.body.style.transition = '';
      setIsTransitioning(false);
    }, 300);
  };

  const getThemeConfig = (theme = currentTheme) => {
    return THEME_CONFIG[theme] || THEME_CONFIG[THEMES.MODERN];
  };

  const isHighPerformanceTheme = (theme = currentTheme) => {
    return theme === THEMES.MINIMAL || 
           theme === THEMES.RETRO_PERFORMANCE || 
           theme === THEMES.MODERN_OPTIMIZED;
  };

  const value = {
    currentTheme,
    availableThemes: THEMES,
    themeConfig: THEME_CONFIG,
    switchTheme,
    getThemeConfig,
    isHighPerformanceTheme,
    isTransitioning
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeProvider;