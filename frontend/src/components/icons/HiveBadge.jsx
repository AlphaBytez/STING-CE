import React from 'react';

/**
 * HiveBadge - A circular notification badge with bee-themed styling
 * More subtle than the hexagon version but still themed
 */
const HiveBadge = ({ count = 0, size = 'medium', variant = 'amber' }) => {
  // Size configurations
  const sizes = {
    small: {
      container: 'w-6 h-6',
      text: 'text-xs',
      ring: 'ring-2'
    },
    medium: {
      container: 'w-8 h-8',
      text: 'text-sm',
      ring: 'ring-2'
    },
    large: {
      container: 'w-10 h-10',
      text: 'text-base',
      ring: 'ring-3'
    }
  };

  // Color variants
  const variants = {
    amber: {
      gradient: 'from-amber-500 to-yellow-600',
      shadow: 'shadow-amber-500/50',
      ring: 'ring-amber-400/30',
      glow: 'bg-amber-400'
    },
    honey: {
      gradient: 'from-yellow-500 to-amber-600',
      shadow: 'shadow-yellow-500/50',
      ring: 'ring-yellow-400/30',
      glow: 'bg-yellow-400'
    },
    gold: {
      gradient: 'from-yellow-600 to-amber-700',
      shadow: 'shadow-yellow-600/50',
      ring: 'ring-yellow-500/30',
      glow: 'bg-yellow-500'
    }
  };

  const currentSize = sizes[size] || sizes.medium;
  const currentVariant = variants[variant] || variants.amber;

  return (
    <div className="relative inline-flex items-center justify-center">
      {/* Main badge */}
      <div 
        className={`
          ${currentSize.container}
          bg-gradient-to-br ${currentVariant.gradient}
          rounded-full
          shadow-lg ${currentVariant.shadow}
          ${currentSize.ring} ${currentVariant.ring}
          flex items-center justify-center
          transform transition-all duration-200
          hover:scale-110
          ${count > 0 ? 'animate-pulse-subtle' : ''}
        `}
      >
        {/* Inner honeycomb texture */}
        <div className="absolute inset-0 rounded-full overflow-hidden opacity-20">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <defs>
              <pattern id="honeycomb" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                <polygon points="10,0 20,5 20,15 10,20 0,15 0,5" fill="white" />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#honeycomb)" />
          </svg>
        </div>
        
        {/* Count */}
        <span 
          className={`
            relative z-10
            ${currentSize.text} 
            font-bold 
            text-white 
            drop-shadow-md
            ${count > 99 ? 'text-xs' : ''}
          `}
        >
          {count > 99 ? '99+' : count}
        </span>
        
        {/* Shine effect */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-white/30 to-transparent" />
      </div>
      
      {/* Animated rings for emphasis */}
      {count > 0 && (
        <>
          <div 
            className={`
              absolute inset-0 
              rounded-full 
              ${currentVariant.glow}
              opacity-30
              animate-ping
            `} 
          />
          <div 
            className={`
              absolute inset-0 
              rounded-full 
              ring-2 ring-white/20
              animate-pulse
            `} 
          />
        </>
      )}
      
      {/* Floating bee dots (decorative) */}
      <div className="absolute -top-1 -right-1 w-2 h-2 bg-white rounded-full opacity-80 animate-float" />
      <div className="absolute -bottom-1 -left-1 w-1.5 h-1.5 bg-white rounded-full opacity-60 animate-float-delayed" />
      
    </div>
  );
};

export default HiveBadge;