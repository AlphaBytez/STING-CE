import React from 'react';

/**
 * BeeProfileAvatar - A bee-themed profile avatar that matches notification design
 * Features honeycomb patterns, amber gradients, and optional profile image support
 */
const BeeProfileAvatar = ({ 
  size = 40, 
  initials = 'ST',
  profileImageUrl = null,
  isOnline = false,
  hasNotifications = false,
  className = '',
  variant = 'honeycomb', // 'honeycomb', 'circle', 'hexagon'
  ...props 
}) => {
  const id = `bee-avatar-${Date.now()}-${Math.random()}`; // Unique ID for gradients

  if (variant === 'honeycomb') {
    // Honeycomb hexagonal design
    return (
      <div 
        className={`inline-flex items-center justify-center relative ${className}`}
        style={{ width: size, height: size }}
        {...props}
      >
        <svg 
          width={size} 
          height={size} 
          viewBox={`0 0 ${size} ${size}`}
          className="absolute inset-0"
          style={{
            shapeRendering: 'geometricPrecision',
            imageRendering: 'crisp-edges',
          }}
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Gradient definitions */}
          <defs>
            <linearGradient id={`avatarGradient-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbbf24" /> {/* amber-400 */}
              <stop offset="50%" stopColor="#f59e0b" /> {/* amber-500 */}
              <stop offset="100%" stopColor="#d97706" /> {/* amber-600 */}
            </linearGradient>
            
            {/* Honeycomb pattern */}
            <pattern id={`honeycombPattern-${id}`} x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
              <path d="M4,1 L7,2.5 L7,5.5 L4,7 L1,5.5 L1,2.5 Z" 
                    fill="none" 
                    stroke="rgba(255,255,255,0.2)" 
                    strokeWidth="0.5"/>
            </pattern>
            
            {/* Clip path for hexagon */}
            <clipPath id={`hexClip-${id}`}>
              <path d={`
                M${size * 0.5},${size * 0.05}
                L${size * 0.85},${size * 0.275}
                L${size * 0.85},${size * 0.725}
                L${size * 0.5},${size * 0.95}
                L${size * 0.15},${size * 0.725}
                L${size * 0.15},${size * 0.275}
                Z
              `} />
            </clipPath>
          </defs>
          
          {/* Shadow */}
          <path 
            d={`
              M${size * 0.5},${size * 0.05}
              L${size * 0.85},${size * 0.275}
              L${size * 0.85},${size * 0.725}
              L${size * 0.5},${size * 0.95}
              L${size * 0.15},${size * 0.725}
              L${size * 0.15},${size * 0.275}
              Z
            `}
            fill="rgba(0,0,0,0.2)"
            transform="translate(1, 1)"
          />
          
          {/* Main hexagon */}
          <path 
            d={`
              M${size * 0.5},${size * 0.05}
              L${size * 0.85},${size * 0.275}
              L${size * 0.85},${size * 0.725}
              L${size * 0.5},${size * 0.95}
              L${size * 0.15},${size * 0.725}
              L${size * 0.15},${size * 0.275}
              Z
            `}
            fill={`url(#avatarGradient-${id})`}
            stroke="rgba(245, 158, 11, 0.5)"
            strokeWidth="1.5"
            className="filter drop-shadow-lg"
          />
          
          {/* Honeycomb pattern overlay */}
          <path 
            d={`
              M${size * 0.5},${size * 0.05}
              L${size * 0.85},${size * 0.275}
              L${size * 0.85},${size * 0.725}
              L${size * 0.5},${size * 0.95}
              L${size * 0.15},${size * 0.725}
              L${size * 0.15},${size * 0.275}
              Z
            `}
            fill={`url(#honeycombPattern-${id})`}
            opacity="0.4"
          />
          
          {/* Profile image */}
          {profileImageUrl && (
            <image
              href={profileImageUrl}
              x={size * 0.15}
              y={size * 0.05}
              width={size * 0.7}
              height={size * 0.9}
              clipPath={`url(#hexClip-${id})`}
              preserveAspectRatio="xMidYMid slice"
              style={{
                imageRendering: 'crisp-edges',
                filter: 'contrast(1.1) brightness(1.05) saturate(1.1)',
              }}
            />
          )}
          
          {/* Inner glow */}
          <path 
            d={`
              M${size * 0.5},${size * 0.15}
              L${size * 0.75},${size * 0.3}
              L${size * 0.75},${size * 0.4}
              L${size * 0.5},${size * 0.25}
              L${size * 0.25},${size * 0.4}
              L${size * 0.25},${size * 0.3}
              Z
            `}
            fill="rgba(255, 255, 255, 0.3)"
          />
        </svg>
        
        {/* Initials */}
        {!profileImageUrl && (
          <span 
            className="relative z-10 text-gray-900 font-bold select-none"
            style={{ 
              fontSize: `${size * 0.35}px`,
              textShadow: '0 1px 2px rgba(255,255,255,0.4)'
            }}
          >
            {initials}
          </span>
        )}
        
        {/* Online indicator */}
        {isOnline && (
          <div 
            className="absolute bottom-0 right-0 bg-green-500 rounded-full border-2 border-gray-900"
            style={{
              width: size * 0.25,
              height: size * 0.25,
            }}
          >
            <div className="w-full h-full bg-green-400 rounded-full animate-pulse" />
          </div>
        )}
        
        {/* Notification dot */}
        {hasNotifications && (
          <div 
            className="absolute -top-1 -right-1 bg-red-500 rounded-full border-2 border-gray-900 animate-bounce"
            style={{
              width: size * 0.2,
              height: size * 0.2,
            }}
          />
        )}
      </div>
    );
  }

  if (variant === 'circle') {
    // Circular design with honeycomb texture
    return (
      <div 
        className={`inline-flex items-center justify-center relative ${className}`}
        style={{ width: size, height: size }}
        {...props}
      >
        <div 
          className="absolute inset-0 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg"
          style={{
            boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)',
          }}
        >
          {/* Honeycomb texture overlay */}
          <svg 
            className="absolute inset-0 w-full h-full rounded-full overflow-hidden opacity-20"
            style={{
              shapeRendering: 'geometricPrecision',
              imageRendering: 'crisp-edges',
            }}
          >
            <pattern id={`circlePattern-${id}`} x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
              <polygon points="5,0 10,2.5 10,7.5 5,10 0,7.5 0,2.5" fill="white" />
            </pattern>
            <rect width="100%" height="100%" fill={`url(#circlePattern-${id})`} />
          </svg>
          
          {/* Profile image */}
          {profileImageUrl && (
            <img 
              src={profileImageUrl} 
              alt="Profile" 
              className="w-full h-full object-cover rounded-full"
              style={{
                imageRendering: 'crisp-edges',
                filter: 'contrast(1.1) brightness(1.05) saturate(1.1)',
                backfaceVisibility: 'hidden',
                transform: 'translateZ(0)',
              }}
              loading="eager"
              decoding="sync"
            />
          )}
        </div>
        
        {/* Initials */}
        {!profileImageUrl && (
          <span 
            className="relative z-10 text-gray-900 font-bold select-none"
            style={{ 
              fontSize: `${size * 0.4}px`,
              textShadow: '0 1px 2px rgba(255,255,255,0.3)'
            }}
          >
            {initials}
          </span>
        )}
        
        {/* Ring animation */}
        <div className="absolute inset-0 rounded-full ring-2 ring-amber-400 ring-opacity-30 animate-pulse" />
        
        {/* Online indicator */}
        {isOnline && (
          <div 
            className="absolute bottom-0 right-0 bg-green-500 rounded-full border-2 border-gray-900 shadow-md"
            style={{
              width: size * 0.3,
              height: size * 0.3,
            }}
          />
        )}
      </div>
    );
  }

  // Default hexagon variant
  return (
    <div 
      className={`inline-flex items-center justify-center relative ${className}`}
      style={{ width: size, height: size }}
      {...props}
    >
      <svg 
        width={size} 
        height={size} 
        viewBox={`0 0 ${size} ${size}`}
        style={{
          shapeRendering: 'geometricPrecision',
          imageRendering: 'crisp-edges',
        }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id={`hexGradient-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fcd34d" /> {/* yellow-300 */}
            <stop offset="100%" stopColor="#f59e0b" /> {/* amber-500 */}
          </linearGradient>
        </defs>
        
        {/* Simple hexagon */}
        <polygon
          points={`${size/2},${size*0.1} ${size*0.85},${size*0.3} ${size*0.85},${size*0.7} ${size/2},${size*0.9} ${size*0.15},${size*0.7} ${size*0.15},${size*0.3}`}
          fill={`url(#hexGradient-${id})`}
          stroke="#f59e0b"
          strokeWidth="2"
        />
      </svg>
      
      {/* Initials */}
      {!profileImageUrl && (
        <span 
          className="absolute text-gray-900 font-bold"
          style={{ fontSize: `${size * 0.4}px` }}
        >
          {initials}
        </span>
      )}
    </div>
  );
};

export default BeeProfileAvatar;