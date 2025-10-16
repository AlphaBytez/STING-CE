import React from 'react';

/**
 * FlowerIcon - Flat flower icon to replace 🌺🌼🌻 emojis
 * Simple geometric flower design
 */
const FlowerIcon = ({ 
  size = 20, 
  color = 'currentColor', 
  strokeWidth = 2,
  className = '',
  variant = 'simple', // 'simple', 'detailed'
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
      className={`flower-icon ${className}`}
      {...props}
    >
      {variant === 'simple' ? (
        <>
          {/* Simple flower - 5 petals */}
          <circle cx="12" cy="12" r="2" />
          <path d="M12 6c-1 0-2 1-2 2s1 2 2 2 2-1 2-2-1-2-2-2z" />
          <path d="M18 12c0-1-1-2-2-2s-2 1-2 2 1 2 2 2 2-1 2-2z" />
          <path d="M12 18c1 0 2-1 2-2s-1-2-2-2-2 1-2 2 1 2 2 2z" />
          <path d="M6 12c0 1 1 2 2 2s2-1 2-2-1-2-2-2-2 1-2 2z" />
          <path d="M15.5 8.5c-0.7-0.7-1.8-0.7-2.5 0s-0.7 1.8 0 2.5 1.8 0.7 2.5 0 0.7-1.8 0-2.5z" />
          
          {/* Stem */}
          <path d="M12 14v6" />
          <path d="M10 18l2-1 2 1" />
        </>
      ) : (
        <>
          {/* Detailed flower */}
          <circle cx="12" cy="10" r="1.5" />
          <path d="M12 6c-1.5 0-3 1.5-3 3s1.5 3 3 3 3-1.5 3-3-1.5-3-3-3z" />
          <path d="M17 10c0-1.5-1.5-3-3-3s-3 1.5-3 3 1.5 3 3 3 3-1.5 3-3z" />
          <path d="M12 14c1.5 0 3-1.5 3-3s-1.5-3-3-3-3 1.5-3 3 1.5 3 3 3z" />
          <path d="M7 10c0 1.5 1.5 3 3 3s3-1.5 3-3-1.5-3-3-3-3 1.5-3 3z" />
          
          {/* Stem and leaves */}
          <path d="M12 12v8" />
          <path d="M10 16c-2-1-3-2-2-4" />
          <path d="M14 16c2-1 3-2 2-4" />
        </>
      )}
    </svg>
  );
};

export default FlowerIcon;