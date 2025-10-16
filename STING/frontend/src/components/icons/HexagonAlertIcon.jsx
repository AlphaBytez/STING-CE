import React from 'react';

/**
 * HexagonAlertIcon - A honeycomb-inspired hexagonal notification icon
 * Clean, modern design that fits with STING's bee theme
 */
const HexagonAlertIcon = ({ className = "w-5 h-5", isActive = false, hasNotifications = false }) => {
  const fillColor = isActive ? "#facc15" : "#9ca3af"; // yellow-400 : gray-400
  
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ transition: 'all 0.2s' }}
    >
      {/* Main hexagon */}
      <path
        d="M12 2L20 7V17L12 22L4 17V7L12 2Z"
        stroke={fillColor}
        strokeWidth="2"
        strokeLinejoin="round"
        fill="none"
        className="hover:stroke-yellow-400 transition-colors"
      />
      
      {/* Inner hexagon pattern */}
      <path
        d="M12 6L16 8.5V13.5L12 16L8 13.5V8.5L12 6Z"
        fill={fillColor}
        fillOpacity="0.2"
        stroke={fillColor}
        strokeWidth="1"
        strokeLinejoin="round"
        className="hover:fill-yellow-400 hover:fill-opacity-30 transition-all"
      />
      
      {/* Notification bell inside */}
      <g transform="translate(12, 12)">
        <path
          d="M-3 -2C-3 -4 -2 -5 0 -5C2 -5 3 -4 3 -2V0L4 1V2H-4V1L-3 0V-2Z"
          fill={fillColor}
          fillOpacity="0.8"
          className="hover:fill-yellow-400 transition-colors"
        />
        <circle 
          cx="0" 
          cy="3" 
          r="1" 
          fill={fillColor}
          className="hover:fill-yellow-400 transition-colors"
        />
      </g>
      
      {/* Notification dot */}
      {hasNotifications && (
        <>
          <circle
            cx="18"
            cy="6"
            r="3"
            fill="#ef4444"
            stroke="#ffffff"
            strokeWidth="1"
            className="animate-pulse"
          />
          {/* Ripple effect */}
          <circle cx="18" cy="6" r="3" fill="#ef4444" opacity="0.3">
            <animate
              attributeName="r"
              from="3"
              to="6"
              dur="1.5s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              from="0.3"
              to="0"
              dur="1.5s"
              repeatCount="indefinite"
            />
          </circle>
        </>
      )}
      
      {/* Hover glow effect */}
      {isActive && (
        <path
          d="M12 2L20 7V17L12 22L4 17V7L12 2Z"
          stroke={fillColor}
          strokeWidth="4"
          strokeLinejoin="round"
          fill="none"
          opacity="0.3"
          className="animate-pulse"
        />
      )}
    </svg>
  );
};

export default HexagonAlertIcon;