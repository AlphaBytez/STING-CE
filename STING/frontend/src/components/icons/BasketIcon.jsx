import React from 'react';

/**
 * BasketIcon - Flat basket icon to replace 🧺 emoji
 * Represents the Pollen Basket concept with clean geometric lines
 */
const BasketIcon = ({ 
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
      className={`basket-icon ${className}`}
      {...props}
    >
      {/* Basket rim */}
      <ellipse cx="12" cy="7" rx="8" ry="2" />
      
      {/* Basket body */}
      <path d="M4 7v8c0 2 2 4 8 4s8-2 8-4V7" />
      
      {/* Basket weave pattern */}
      <path d="M6 9h2" />
      <path d="M10 9h4" />
      <path d="M16 9h2" />
      
      <path d="M6 12h3" />
      <path d="M11 12h2" />
      <path d="M15 12h3" />
      
      <path d="M7 15h2" />
      <path d="M11 15h2" />
      <path d="M15 15h2" />
      
      {/* Handle */}
      <path d="M8 7V5a1 1 0 011-1h6a1 1 0 011 1v2" />
    </svg>
  );
};

export default BasketIcon;