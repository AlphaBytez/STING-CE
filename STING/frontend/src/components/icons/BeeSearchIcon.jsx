import React from 'react';

/**
 * BeeSearchIcon - Bee-themed search icon combining magnifying glass with bee elements
 * Represents semantic search through honey jars and documents
 */
const BeeSearchIcon = ({ 
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
      className={`bee-search-icon ${className}`}
      {...props}
    >
      {/* Main magnifying glass circle */}
      <circle cx="10" cy="10" r="7" />
      
      {/* Magnifying glass handle */}
      <path d="M21 21l-4.35-4.35" />
      
      {/* Bee body inside the magnifying glass */}
      <ellipse cx="10" cy="10" rx="3" ry="2" fill={color} fillOpacity="0.1" />
      
      {/* Bee stripes */}
      <path d="M8 9h4" strokeWidth="1" />
      <path d="M8 10h4" strokeWidth="1" />
      <path d="M8 11h4" strokeWidth="1" />
      
      {/* Bee wings */}
      <path d="M7 8c-1-1 0-2 1-1" strokeWidth="1" />
      <path d="M13 8c1-1 0-2-1-1" strokeWidth="1" />
      
      {/* Search particles/honey drops */}
      <circle cx="15" cy="6" r="0.5" fill={color} fillOpacity="0.6" />
      <circle cx="17" cy="4" r="0.5" fill={color} fillOpacity="0.4" />
      <circle cx="18" cy="6" r="0.5" fill={color} fillOpacity="0.3" />
    </svg>
  );
};

export default BeeSearchIcon;