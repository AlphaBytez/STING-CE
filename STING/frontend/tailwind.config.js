module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        'primary': 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',
        'primary-active': 'var(--color-primary-active)',
        'primary-light': 'var(--color-primary-light)',
        'primary-pale': 'var(--color-primary-pale)',
        'primary-ghost': 'var(--color-primary-ghost)',
        
        // Background colors
        'bg-layout': 'var(--color-bg-layout)',
        'bg-container': 'var(--color-bg-container)',
        'bg-elevated': 'var(--color-bg-elevated)',
        'bg-input': 'var(--color-bg-input)',
        'bg-header': 'var(--color-bg-header)',
        'bg-spotlight': 'var(--color-bg-spotlight)',
        'bg-light-hover': 'var(--color-bg-light-hover)',
        
        // Text colors
        'text-default': 'var(--color-text)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-tertiary': 'var(--color-text-tertiary)',
        'text-quaternary': 'var(--color-text-quaternary)',
        'text-prose': 'var(--color-text-prose)',
        'text-inverse': 'var(--color-text-inverse)',
        
        // Border colors
        'border-default': 'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',
        'border-glass': 'var(--color-border-glass)',
        'border-dark': 'var(--color-border-dark)',
        
        // Semantic colors - replacing emerald with lime
        'success': 'var(--color-success)',
        'success-hover': 'var(--color-success-hover)',
        'success-light': 'var(--color-success-light)',
        'success-dark': 'var(--color-success-dark)',
        'success-bg': 'var(--color-success-bg)',
        
        'error': 'var(--color-error)',
        'error-hover': 'var(--color-error-hover)',
        'error-light': 'var(--color-error-light)',
        'error-dark': 'var(--color-error-dark)',
        'error-bg': 'var(--color-error-bg)',
        
        'warning': 'var(--color-warning)',
        'warning-hover': 'var(--color-warning-hover)',
        'warning-light': 'var(--color-warning-light)',
        'warning-dark': 'var(--color-warning-dark)',
        'warning-bg': 'var(--color-warning-bg)',
        
        'info': 'var(--color-info)',
        'info-hover': 'var(--color-info-hover)',
        'info-light': 'var(--color-info-light)',
        'info-dark': 'var(--color-info-dark)',
        'info-bg': 'var(--color-info-bg)',
        
        // Glass effect colors
        'glass-subtle': 'var(--color-glass-subtle)',
        'glass-medium': 'var(--color-glass-medium)',
        'glass-strong': 'var(--color-glass-strong)',
        'glass-ultra': 'var(--color-glass-ultra)',
        'glass-heavy': 'var(--color-glass-heavy)',
        'glass-light-subtle': 'var(--color-glass-light-subtle)',
        'glass-light-medium': 'var(--color-glass-light-medium)',
        
        // Override default green with warm jade
        green: {
          50: '#f0f7f1',
          100: '#daeedd',
          200: '#b6ddb9',
          300: '#8fc693',
          400: '#7ab57f',
          500: '#5d9b63',  // Our primary success color - warm jade
          600: '#4a7a4f',
          700: '#3d6640',
          800: '#2f4f31',
          900: '#253d26',
        },
        
        // Ensure emerald is not used by mapping to warm jade
        emerald: {
          50: '#f0f7f1',
          100: '#daeedd',
          200: '#b6ddb9',
          300: '#8fc693',
          400: '#7ab57f',
          500: '#5d9b63',  // Map emerald-500 to warm jade
          600: '#4a7a4f',
          700: '#3d6640',
          800: '#2f4f31',
          900: '#253d26',
        }
      },
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        'mono': ['Fira Code', 'Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
      fontSize: {
        'xs': 'var(--text-xs)',
        'sm': 'var(--text-sm)',
        'base': 'var(--text-base)',
        'lg': 'var(--text-lg)',
        'xl': 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
        '4xl': 'var(--text-4xl)',
      },
      spacing: {
        'xs': 'var(--space-xs)',
        'sm': 'var(--space-sm)',
        'md': 'var(--space-md)',
        'lg': 'var(--space-lg)',
        'xl': 'var(--space-xl)',
        '2xl': 'var(--space-2xl)',
        '3xl': 'var(--space-3xl)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
        'dashboard': 'var(--shadow-dashboard)',
      },
      zIndex: {
        'base': 'var(--z-base)',
        'dropdown': 'var(--z-dropdown)',
        'sticky': 'var(--z-sticky)',
        'fixed': 'var(--z-fixed)',
        'modal-backdrop': 'var(--z-modal-backdrop)',
        'modal': 'var(--z-modal)',
        'popover': 'var(--z-popover)',
        'tooltip': 'var(--z-tooltip)',
      },
      transitionDuration: {
        'fast': 'var(--transition-fast)',
        'base': 'var(--transition-base)',
        'slow': 'var(--transition-slow)',
      },
      backdropBlur: {
        'sm': 'var(--glass-blur-sm)',
        'md': 'var(--glass-blur-md)',
        'lg': 'var(--glass-blur-lg)',
        'xl': 'var(--glass-blur-xl)',
        '2xl': 'var(--glass-blur-2xl)',
      },
    },
  },
  plugins: [],
}