import React from 'react';

/**
 * UserAvatarIcon - Profile picture placeholder icon
 * Clean geometric user avatar that matches the icon system
 */
const UserAvatarIcon = ({ 
  size = 32, 
  color = 'currentColor', 
  strokeWidth = 2,
  className = '',
  initials = 'ST',
  profileImageUrl = null,
  ...props 
}) => {
  // Always show hexagonal honeycomb version if initials provided
  if (initials && initials.trim().length > 0) {
    // Show initials version with rounded hexagonal honeycomb shape
    const roundedHexagonPath = `
      M${size * 0.5},${size * 0.08}
      C${size * 0.52},${size * 0.08} ${size * 0.55},${size * 0.09} ${size * 0.58},${size * 0.11}
      L${size * 0.85},${size * 0.27}
      C${size * 0.88},${size * 0.29} ${size * 0.9},${size * 0.32} ${size * 0.9},${size * 0.35}
      L${size * 0.9},${size * 0.65}
      C${size * 0.9},${size * 0.68} ${size * 0.88},${size * 0.71} ${size * 0.85},${size * 0.73}
      L${size * 0.58},${size * 0.89}
      C${size * 0.55},${size * 0.91} ${size * 0.52},${size * 0.92} ${size * 0.5},${size * 0.92}
      C${size * 0.48},${size * 0.92} ${size * 0.45},${size * 0.91} ${size * 0.42},${size * 0.89}
      L${size * 0.15},${size * 0.73}
      C${size * 0.12},${size * 0.71} ${size * 0.1},${size * 0.68} ${size * 0.1},${size * 0.65}
      L${size * 0.1},${size * 0.35}
      C${size * 0.1},${size * 0.32} ${size * 0.12},${size * 0.29} ${size * 0.15},${size * 0.27}
      L${size * 0.42},${size * 0.11}
      C${size * 0.45},${size * 0.09} ${size * 0.48},${size * 0.08} ${size * 0.5},${size * 0.08}
      Z
    `;

    return (
      <div 
        className={`inline-flex items-center justify-center relative ${className}`}
        style={{ width: size, height: size }}
        {...props}
      >
        {/* Hexagonal honeycomb background */}
        <svg 
          width={size} 
          height={size} 
          viewBox={`0 0 ${size} ${size}`}
          className="absolute inset-0"
        >
          {/* Honeycomb gradient definitions */}
          <defs>
            <linearGradient id={`honeycombGradient-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbbf24" />
              <stop offset="30%" stopColor="#f59e0b" />
              <stop offset="70%" stopColor="#d97706" />
              <stop offset="100%" stopColor="#92400e" />
            </linearGradient>
            {/* Subtle hexagon pattern overlay */}
            <pattern id={`honeycombPattern-${size}`} x="0" y="0" width="6" height="6" patternUnits="userSpaceOnUse">
              <path d="M3,0.5 L5.5,2 L5.5,4 L3,5.5 L0.5,4 L0.5,2 Z" 
                    fill="none" 
                    stroke="rgba(255,255,255,0.15)" 
                    strokeWidth="0.3"/>
            </pattern>
          </defs>
          
          {/* Main rounded hexagon shape */}
          <path 
            d={roundedHexagonPath}
            fill={`url(#honeycombGradient-${size})`}
            stroke="rgba(251, 191, 36, 0.6)"
            strokeWidth="1"
            className="drop-shadow-md"
          />
          
          {/* Honeycomb pattern overlay */}
          <path 
            d={roundedHexagonPath}
            fill={`url(#honeycombPattern-${size})`}
            opacity="0.4"
          />
          
          {/* Profile image clipped to hexagon shape */}
          {profileImageUrl && (
            <defs>
              <clipPath id={`hexClip-${size}`}>
                <path d={roundedHexagonPath} />
              </clipPath>
            </defs>
          )}
          {profileImageUrl && (
            <image
              href={profileImageUrl}
              x={size * 0.1}
              y={size * 0.08}
              width={size * 0.8}
              height={size * 0.84}
              clipPath={`url(#hexClip-${size})`}
              preserveAspectRatio="xMidYMid slice"
              opacity="0.9"
            />
          )}
          
          {/* Inner highlight for 3D depth effect */}
          <path 
            d={`
              M${size * 0.5},${size * 0.16}
              L${size * 0.82},${size * 0.34}
              L${size * 0.82},${size * 0.42}
              L${size * 0.5},${size * 0.26}
              L${size * 0.18},${size * 0.42}
              L${size * 0.18},${size * 0.34}
              Z
            `}
            fill="rgba(255, 255, 255, 0.35)"
            opacity="0.8"
          />
        </svg>
        
        {/* Initials text - only show if no profile image */}
        {!profileImageUrl && (
          <span 
            className="relative z-10 text-white font-bold select-none tracking-tight"
            style={{ 
              fontSize: `${size * 0.32}px`,
              textShadow: '0 1px 3px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.4)'
            }}
          >
            {initials}
          </span>
        )}
      </div>
    );
  }

  // Show icon version
  return (
    <div
      className={`flex items-center justify-center rounded-full bg-gray-600 ${className}`}
      style={{ width: size, height: size }}
      {...props}
    >
      <svg
        width={size * 0.6}
        height={size * 0.6}
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* User head */}
        <circle cx="12" cy="8" r="4" />
        
        {/* User body */}
        <path d="M6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" />
      </svg>
    </div>
  );
};

export default UserAvatarIcon;