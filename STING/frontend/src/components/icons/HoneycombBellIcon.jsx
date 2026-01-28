import React from 'react';

/**
 * HoneycombBellIcon - A bee-themed notification icon for STING
 * Combines a honeycomb pattern with a bell shape for a unique look
 */
const HoneycombBellIcon = ({ className = "w-5 h-5", isActive = false }) => {
  const fillColor = isActive ? "#facc15" : "#9ca3af"; // yellow-400 : gray-400
  const hoverColor = isActive ? "#fbbf24" : "#fbbf24"; // yellow-400 : yellow-400
  
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ transition: 'all 0.2s' }}
    >
      {/* Honeycomb pattern inside bell */}
      <g className="honeycomb-pattern">
        {/* Top hexagon */}
        <path
          d="M12 4L10.5 5.5L10.5 7.5L12 9L13.5 7.5L13.5 5.5L12 4Z"
          fill={fillColor}
          fillOpacity="0.3"
          stroke={fillColor}
          strokeWidth="0.5"
        />
        {/* Left hexagon */}
        <path
          d="M9 8L7.5 9.5L7.5 11.5L9 13L10.5 11.5L10.5 9.5L9 8Z"
          fill={fillColor}
          fillOpacity="0.3"
          stroke={fillColor}
          strokeWidth="0.5"
        />
        {/* Right hexagon */}
        <path
          d="M15 8L13.5 9.5L13.5 11.5L15 13L16.5 11.5L16.5 9.5L15 8Z"
          fill={fillColor}
          fillOpacity="0.3"
          stroke={fillColor}
          strokeWidth="0.5"
        />
      </g>
      
      {/* Bell outline with honeycomb-inspired curves */}
      <path
        d="M12 2C10.5 2 9 3 9 5C9 5.5 9 6 9 6.5C7 7.5 5.5 9.5 5.5 12V16L4 17.5V18.5H20V17.5L18.5 16V12C18.5 9.5 17 7.5 15 6.5C15 6 15 5.5 15 5C15 3 13.5 2 12 2Z"
        stroke={fillColor}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        className="hover:stroke-yellow-400 transition-colors"
      />
      
      {/* Clapper with bee stripe pattern */}
      <path
        d="M10 19C10 20.1 10.9 21 12 21C13.1 21 14 20.1 14 19"
        stroke={fillColor}
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        className="hover:stroke-yellow-400 transition-colors"
      />
      
      {/* Animated pulse effect when active */}
      {isActive && (
        <circle cx="12" cy="12" r="10" fill="none" stroke={fillColor} strokeWidth="0.5" opacity="0.4">
          <animate
            attributeName="r"
            from="10"
            to="14"
            dur="1.5s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from="0.4"
            to="0"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </circle>
      )}
    </svg>
  );
};

export default HoneycombBellIcon;