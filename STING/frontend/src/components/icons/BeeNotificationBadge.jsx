import React from 'react';

/**
 * BeeNotificationBadge - A bee-themed notification counter badge
 * Replaces the plain red circle with a more appealing honeycomb-inspired design
 */
const BeeNotificationBadge = ({ count = 0, size = 'medium' }) => {
  // Size configurations
  const sizes = {
    small: {
      container: 'w-7 h-7',
      text: 'text-xs',
      honeycomb: 'w-8 h-8',
      offset: '-top-1 -right-1'
    },
    medium: {
      container: 'w-9 h-9',
      text: 'text-sm',
      honeycomb: 'w-10 h-10',
      offset: '-top-1.5 -right-1.5'
    },
    large: {
      container: 'w-11 h-11',
      text: 'text-base',
      honeycomb: 'w-12 h-12',
      offset: '-top-2 -right-2'
    }
  };

  const currentSize = sizes[size] || sizes.medium;

  return (
    <div className="relative inline-block">
      {/* Honeycomb background shape */}
      <div className={`absolute ${currentSize.offset} ${currentSize.honeycomb}`}>
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="absolute inset-0 w-full h-full"
        >
          {/* Hexagon shape */}
          <path
            d="M20 4L32 11V29L20 36L8 29V11L20 4Z"
            fill="url(#honeyGradient)"
            stroke="url(#borderGradient)"
            strokeWidth="2"
            className="filter drop-shadow-lg"
          />
          
          {/* Gradient definitions */}
          <defs>
            <linearGradient id="honeyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f59e0b" /> {/* amber-500 */}
              <stop offset="100%" stopColor="#d97706" /> {/* amber-600 */}
            </linearGradient>
            <linearGradient id="borderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbbf24" /> {/* amber-400 */}
              <stop offset="100%" stopColor="#f59e0b" /> {/* amber-500 */}
            </linearGradient>
          </defs>
          
          {/* Inner honeycomb pattern */}
          <path
            d="M20 10L26 13.5V22.5L20 26L14 22.5V13.5L20 10Z"
            fill="none"
            stroke="#fef3c7"
            strokeWidth="0.5"
            opacity="0.5"
          />
        </svg>
      </div>
      
      {/* Count display */}
      <div 
        className={`
          relative z-10 
          ${currentSize.container} 
          flex items-center justify-center
          ${count > 0 ? 'animate-bounce-subtle' : ''}
        `}
      >
        <span 
          className={`
            ${currentSize.text} 
            font-bold 
            text-white 
            drop-shadow-md
            ${count > 99 ? 'text-xs' : ''}
          `}
        >
          {count > 99 ? '99+' : count}
        </span>
      </div>
      
      {/* Pulsing glow effect for new notifications */}
      {count > 0 && (
        <div className={`absolute ${currentSize.offset} ${currentSize.honeycomb} pointer-events-none`}>
          <div className="absolute inset-0 bg-amber-400 rounded-full blur-md opacity-50 animate-pulse" />
        </div>
      )}
      
      <style jsx>{`
        @keyframes bounce-subtle {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-2px);
          }
        }
        
        .animate-bounce-subtle {
          animation: bounce-subtle 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default BeeNotificationBadge;