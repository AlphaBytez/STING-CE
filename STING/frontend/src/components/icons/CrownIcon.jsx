import React from 'react';

/**
 * CrownIcon - Flat crown icon to replace 👑 emoji
 * Simple geometric crown for admin/queen references
 */
const CrownIcon = ({ 
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
      className={`crown-icon ${className}`}
      {...props}
    >
      {/* Crown base */}
      <path d="M5 18h14l-1-8H6l-1 8z" />
      
      {/* Crown points */}
      <path d="M6 10l3-3 3 2 3-2 3 3" />
      
      {/* Crown jewels */}
      {!filled && (
        <>
          <circle cx="9" cy="13" r="0.5" />
          <circle cx="12" cy="14" r="0.5" />
          <circle cx="15" cy="13" r="0.5" />
        </>
      )}
      
      {/* Crown band */}
      <path d="M5 18h14" strokeWidth={strokeWidth * 1.5} />
    </svg>
  );
};

export default CrownIcon;