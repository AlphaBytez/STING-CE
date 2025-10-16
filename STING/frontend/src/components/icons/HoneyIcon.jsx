import React from 'react';

/**
 * HoneyIcon - Flat honey drop icon to replace 🍯 emoji
 * Geometric honey drop with clean lines
 */
const HoneyIcon = ({ 
  size = 20, 
  color = 'currentColor', 
  strokeWidth = 2,
  className = '',
  filled = false,
  ...props 
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? color : "none"}
      stroke={filled ? "none" : color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`honey-icon ${className}`}
      {...props}
    >
      {/* Honey drop shape */}
      <path d="M12 3c-3 3-8 8-8 12a8 8 0 0016 0c0-4-5-9-8-12z" />
      
      {/* Honey texture lines */}
      {!filled && (
        <>
          <path d="M8 14c2-1 4-1 6 0" strokeWidth={strokeWidth * 0.7} />
          <path d="M9 17c1.5-0.5 3-0.5 4.5 0" strokeWidth={strokeWidth * 0.7} />
        </>
      )}
    </svg>
  );
};

export default HoneyIcon;