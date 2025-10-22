import React from 'react';

/**
 * BeeIcon - Custom flat bee icon that matches Lucide/Material-UI style
 * 
 * A minimalist, geometric bee icon with clean lines and consistent
 * stroke weight to match the rest of the interface icons.
 */
const BeeIcon = ({ 
  size = 20, 
  color = 'currentColor', 
  strokeWidth = 2,
  className = '',
  ...props 
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`bee-icon ${className}`}
      {...props}
    >
      {/* Bee Body - Oval shape */}
      <ellipse cx="12" cy="13" rx="4" ry="6" />
      
      {/* Bee Stripes */}
      <path d="M8.5 10h7" />
      <path d="M8.5 13h7" />
      <path d="M8.5 16h7" />
      
      {/* Left Wing */}
      <ellipse cx="7.5" cy="9" rx="2.5" ry="1.5" transform="rotate(-25 7.5 9)" />
      
      {/* Right Wing */}
      <ellipse cx="16.5" cy="9" rx="2.5" ry="1.5" transform="rotate(25 16.5 9)" />
      
      {/* Antennae */}
      <path d="M10.5 6.5l-1-1.5" />
      <path d="M13.5 6.5l1-1.5" />
      
      {/* Antennae tips */}
      <circle cx="9.5" cy="5" r="0.5" fill={color} />
      <circle cx="14.5" cy="5" r="0.5" fill={color} />
    </svg>
  );
};

export default BeeIcon;