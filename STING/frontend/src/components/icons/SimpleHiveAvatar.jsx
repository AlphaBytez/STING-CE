import React from 'react';

/**
 * SimpleHiveAvatar - A simpler circular avatar with bee-themed styling
 * Matches the notification badge aesthetic with amber gradients
 */
const SimpleHiveAvatar = ({ 
  size = 32, 
  initials = 'ST',
  profileImageUrl = null,
  isOnline = false,
  className = '',
  ...props 
}) => {
  return (
    <div 
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      {...props}
    >
      {/* Main avatar circle */}
      <div 
        className={`
          w-full h-full
          rounded-full
          bg-gradient-to-br from-amber-400 via-amber-500 to-yellow-600
          shadow-lg shadow-amber-500/30
          ring-2 ring-amber-400/30
          flex items-center justify-center
          overflow-hidden
          transition-all duration-200
          hover:shadow-xl hover:shadow-amber-500/40
          hover:ring-amber-400/50
          group
        `}
      >
        {/* Honeycomb texture overlay */}
        <div className="absolute inset-0 opacity-20">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <pattern id="simpleHoneycomb" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
              <polygon points="10,0 20,5 20,15 10,20 0,15 0,5" fill="white" stroke="white" strokeWidth="0.5" />
            </pattern>
            <rect width="100" height="100" fill="url(#simpleHoneycomb)" />
          </svg>
        </div>
        
        {/* Profile image or initials */}
        {profileImageUrl ? (
          <img 
            src={profileImageUrl} 
            alt="Profile" 
            className="w-full h-full object-cover z-10 relative"
          />
        ) : (
          <span 
            className="relative z-10 text-gray-900 font-bold select-none tracking-tight"
            style={{ 
              fontSize: `${size * 0.4}px`,
              textShadow: '0 1px 2px rgba(255,255,255,0.3)'
            }}
          >
            {initials}
          </span>
        )}
        
        {/* Shine effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-white/20 to-transparent rounded-full" />
        
        {/* Hover glow */}
        <div className="absolute inset-0 rounded-full bg-amber-300 opacity-0 group-hover:opacity-20 transition-opacity duration-200" />
      </div>
      
      {/* Online indicator */}
      {isOnline && (
        <div 
          className="absolute bottom-0 right-0"
          style={{
            width: size * 0.3,
            height: size * 0.3,
          }}
        >
          <div className="w-full h-full bg-green-500 rounded-full border-2 border-gray-900 shadow-md">
            <div className="w-full h-full bg-green-400 rounded-full animate-pulse" />
          </div>
        </div>
      )}
      
      {/* Floating bee dots (decorative) */}
      <div 
        className="absolute -top-0.5 -right-0.5 bg-white rounded-full opacity-70 animate-float"
        style={{
          width: size * 0.08,
          height: size * 0.08,
        }}
      />
      <div 
        className="absolute -bottom-0.5 -left-0.5 bg-white rounded-full opacity-50 animate-float-delayed"
        style={{
          width: size * 0.06,
          height: size * 0.06,
        }}
      />
      
      <style jsx>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-2px);
          }
        }
        
        @keyframes float-delayed {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-1px);
          }
        }
        
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
        
        .animate-float-delayed {
          animation: float-delayed 3s ease-in-out infinite;
          animation-delay: 1.5s;
        }
      `}</style>
    </div>
  );
};

export default SimpleHiveAvatar;