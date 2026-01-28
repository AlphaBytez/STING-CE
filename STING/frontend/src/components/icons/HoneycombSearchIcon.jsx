import React from 'react';

/**
 * HoneycombSearchIcon - Honeycomb-themed search icon
 * Represents searching through structured honey jar data
 */
const HoneycombSearchIcon = ({ 
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
      className={`honeycomb-search-icon ${className}`}
      {...props}
    >
      {/* Main magnifying glass circle */}
      <circle cx="10" cy="10" r="7" />
      
      {/* Magnifying glass handle */}
      <path d="M21 21l-4.35-4.35" />
      
      {/* Honeycomb pattern inside magnifying glass */}
      <g strokeWidth="1">
        {/* Central hexagon */}
        <path d="M10 7l2 1v2l-2 1-2-1V8z" fill={color} fillOpacity="0.1" />
        
        {/* Surrounding partial hexagons */}
        <path d="M6 9l2 1v1l-1 0.5" />
        <path d="M14 9l-2 1v1l1 0.5" />
        <path d="M8 6l1 0.5v1" />
        <path d="M12 6l-1 0.5v1" />
        <path d="M8 12l1-0.5v-1" />
        <path d="M12 12l-1-0.5v-1" />
      </g>
    </svg>
  );
};

export default HoneycombSearchIcon;