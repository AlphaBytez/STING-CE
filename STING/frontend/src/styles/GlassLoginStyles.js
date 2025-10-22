/**
 * Unified Glass Login Styles
 * Shared styles for all login/auth components to ensure consistency
 */

export const glassLoginStyles = {
  // Main container with background
  container: "min-h-screen flex items-center justify-center relative overflow-hidden",
  
  // Background gradient - matches app design system colors
  backgroundGradient: "absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]",
  
  // Animated background shapes
  backgroundShapes: {
    container: "absolute inset-0 overflow-hidden",
    shape1: "absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse",
    shape2: "absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse"
  },
  
  // Glass card styles
  glassCard: "relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up",
  
  // Logo section
  logoSection: {
    container: "text-center mb-8",
    wrapper: "relative inline-block",
    glow: "absolute inset-0 bg-yellow-400/20 blur-xl rounded-full",
    logo: "relative w-24 h-24 mx-auto mb-4"
  },
  
  // Typography
  title: "text-3xl font-bold text-white",
  subtitle: "text-gray-400 mt-2",
  
  // Buttons
  primaryButton: "w-full py-3 px-4 sting-glass-button-primary mb-4",
  secondaryButton: "w-full py-3 px-4 sting-glass-button-secondary",
  ghostButton: "text-yellow-400 hover:text-yellow-300 font-medium transition-colors",
  
  // Form elements
  input: "w-full sting-glass-input",
  label: "block text-gray-300 mb-2 font-medium",
  
  // Dividers
  divider: {
    container: "relative mb-6",
    line: "absolute inset-0 flex items-center",
    border: "w-full border-t border-slate-600/30",
    text: {
      wrapper: "relative flex justify-center text-sm",
      content: "px-3 sting-glass-subtle text-gray-400 rounded-full"
    }
  },
  
  // Messages
  errorMessage: "p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded mb-6 text-red-300",
  successMessage: "p-3 bg-green-900 bg-opacity-30 border border-green-800 rounded mb-6 text-green-300",
  
  // Links
  link: "text-blue-400 hover:underline",
  
  // Loading spinner
  spinner: "animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"
};

// Component wrapper for consistent glass login layout
export const GlassLoginLayout = ({ children, title, subtitle }) => {
  return (
    <div className={glassLoginStyles.container}>
      {/* Background gradient */}
      <div className={glassLoginStyles.backgroundGradient}></div>
      
      {/* Animated background shapes */}
      <div className={glassLoginStyles.backgroundShapes.container}>
        <div className={glassLoginStyles.backgroundShapes.shape1}></div>
        <div 
          className={glassLoginStyles.backgroundShapes.shape2} 
          style={{animationDelay: '2s'}}
        ></div>
      </div>

      {/* Glass card container */}
      <div className={glassLoginStyles.glassCard}>
        {/* Logo section */}
        <div className={glassLoginStyles.logoSection.container}>
          <div className={glassLoginStyles.logoSection.wrapper}>
            <div className={glassLoginStyles.logoSection.glow}></div>
            <img 
              src="/sting-logo.png" 
              alt="STING Logo" 
              className={glassLoginStyles.logoSection.logo} 
            />
          </div>
          {title && <h2 className={glassLoginStyles.title}>{title}</h2>}
          {subtitle && <p className={glassLoginStyles.subtitle}>{subtitle}</p>}
        </div>
        
        {children}
      </div>
    </div>
  );
};