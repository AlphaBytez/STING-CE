import React from 'react';

/**
 * BeeAlertIcon - A playful bee-themed notification icon
 * Features a bee with vibrating wings to indicate notifications
 */
const BeeAlertIcon = ({ className = "w-5 h-5", isActive = false, hasNotifications = false }) => {
  const primaryColor = isActive ? "#facc15" : "#9ca3af"; // yellow-400 : gray-400
  const accentColor = isActive ? "#f59e0b" : "#6b7280"; // amber-500 : gray-500
  
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ transition: 'all 0.2s' }}
    >
      {/* Bee body */}
      <ellipse
        cx="12"
        cy="14"
        rx="3.5"
        ry="4.5"
        fill={primaryColor}
        className="hover:fill-yellow-400 transition-colors"
      />
      
      {/* Bee stripes */}
      <rect x="8.5" y="11.5" width="7" height="1.5" fill={accentColor} opacity="0.7" />
      <rect x="8.5" y="14" width="7" height="1.5" fill={accentColor} opacity="0.7" />
      <rect x="8.5" y="16.5" width="7" height="1.5" fill={accentColor} opacity="0.7" />
      
      {/* Bee head */}
      <circle
        cx="12"
        cy="8"
        r="2.5"
        fill={primaryColor}
        className="hover:fill-yellow-400 transition-colors"
      />
      
      {/* Eyes */}
      <circle cx="11" cy="8" r="0.7" fill="#1f2937" />
      <circle cx="13" cy="8" r="0.7" fill="#1f2937" />
      
      {/* Wings - animated when hasNotifications */}
      <g className={hasNotifications ? "animate-pulse" : ""}>
        {/* Left wing */}
        <ellipse
          cx="7"
          cy="12"
          rx="3"
          ry="5"
          fill={primaryColor}
          fillOpacity="0.3"
          stroke={primaryColor}
          strokeWidth="0.5"
          transform="rotate(-20 7 12)"
          className={hasNotifications ? "animate-wiggle-left" : ""}
        />
        {/* Right wing */}
        <ellipse
          cx="17"
          cy="12"
          rx="3"
          ry="5"
          fill={primaryColor}
          fillOpacity="0.3"
          stroke={primaryColor}
          strokeWidth="0.5"
          transform="rotate(20 17 12)"
          className={hasNotifications ? "animate-wiggle-right" : ""}
        />
      </g>
      
      {/* Notification indicator - small bell on top */}
      {hasNotifications && (
        <g transform="translate(15, 2)">
          <path
            d="M0 3C0 1.5 1 0.5 2.5 0.5C4 0.5 5 1.5 5 3V5L6 6V6.5H-1V6L0 5V3Z"
            fill="#ef4444"
            stroke="#dc2626"
            strokeWidth="0.5"
          />
          <circle cx="2.5" cy="7" r="1" fill="#ef4444" />
          {/* Notification pulse */}
          <circle cx="2.5" cy="3.5" r="3" fill="#ef4444" opacity="0.3">
            <animate
              attributeName="r"
              from="3"
              to="5"
              dur="1s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              from="0.3"
              to="0"
              dur="1s"
              repeatCount="indefinite"
            />
          </circle>
        </g>
      )}
      
      {/* Antennae */}
      <line x1="11" y1="6" x2="9" y2="3" stroke={accentColor} strokeWidth="0.5" strokeLinecap="round" />
      <line x1="13" y1="6" x2="15" y2="3" stroke={accentColor} strokeWidth="0.5" strokeLinecap="round" />
      <circle cx="9" cy="3" r="0.5" fill={accentColor} />
      <circle cx="15" cy="3" r="0.5" fill={accentColor} />
      
      <style jsx>{`
        @keyframes wiggle-left {
          0%, 100% { transform: rotate(-20deg); }
          50% { transform: rotate(-30deg); }
        }
        
        @keyframes wiggle-right {
          0%, 100% { transform: rotate(20deg); }
          50% { transform: rotate(30deg); }
        }
      `}</style>
    </svg>
  );
};

export default BeeAlertIcon;