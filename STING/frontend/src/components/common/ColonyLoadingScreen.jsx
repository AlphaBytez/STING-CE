import React, { useState, useEffect } from 'react';

const ColonyLoadingScreen = ({
  isVisible = true,
  message = "Connecting to your Colony",
  subMessage = "Securing access to your workspace...",
  showProgress = false,
  progress = 0
}) => {
  const [dots, setDots] = useState('');
  const [messageIndex, setMessageIndex] = useState(0);

  // Animated dots effect
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Rotating messages for variety
  const messages = [
    "Connecting to your Colony",
    "Securing Colony access",
    "Verifying Colony permissions",
    "Loading Colony resources"
  ];

  useEffect(() => {
    if (message === "Connecting to your Colony") {
      const interval = setInterval(() => {
        setMessageIndex(prev => (prev + 1) % messages.length);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [message]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/95 backdrop-blur-sm">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-10 left-10 w-8 h-8 bg-yellow-400 rounded-full animate-pulse"></div>
        <div className="absolute top-32 right-20 w-4 h-4 bg-yellow-300 rounded-full animate-pulse" style={{animationDelay: '0.5s'}}></div>
        <div className="absolute bottom-32 left-32 w-6 h-6 bg-yellow-500 rounded-full animate-pulse" style={{animationDelay: '1s'}}></div>
        <div className="absolute bottom-20 right-16 w-5 h-5 bg-yellow-400 rounded-full animate-pulse" style={{animationDelay: '1.5s'}}></div>
      </div>

      <div className="text-center space-y-8 max-w-md mx-auto px-6">
        {/* Main bee logo/spinner */}
        <div className="relative">
          {/* Hexagon background */}
          <div className="w-24 h-24 mx-auto relative">
            <div className="absolute inset-0 bg-gradient-to-br from-yellow-400 to-amber-500 transform rotate-12 hexagon animate-spin-slow opacity-20"></div>
            <div className="absolute inset-2 bg-gradient-to-br from-yellow-500 to-amber-600 hexagon animate-spin-reverse opacity-30"></div>
          </div>

          {/* Bee icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-12 h-12 relative animate-bounce">
              {/* Simple bee representation */}
              <div className="w-8 h-6 bg-gradient-to-r from-yellow-400 to-amber-500 rounded-full mx-auto relative">
                {/* Bee stripes */}
                <div className="absolute inset-0 bg-gradient-to-r from-slate-800 via-transparent via-transparent to-slate-800 rounded-full opacity-60"></div>
                <div className="absolute top-1 left-1 w-1.5 h-1.5 bg-slate-800 rounded-full"></div>
                <div className="absolute top-1 right-1 w-1.5 h-1.5 bg-slate-800 rounded-full"></div>
              </div>
              {/* Wings */}
              <div className="absolute -top-1 left-1 w-3 h-4 bg-white/40 rounded-full transform -rotate-12 animate-pulse"></div>
              <div className="absolute -top-1 right-1 w-3 h-4 bg-white/40 rounded-full transform rotate-12 animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Main message */}
        <div className="space-y-3">
          <h2 className="text-2xl font-semibold text-white">
            {message === "Connecting to your Colony" ? messages[messageIndex] : message}
            <span className="text-yellow-400 inline-block w-6 text-left">{dots}</span>
          </h2>

          {subMessage && (
            <p className="text-slate-300 text-lg">
              {subMessage}
            </p>
          )}
        </div>

        {/* Progress bar (optional) */}
        {showProgress && (
          <div className="w-full max-w-xs mx-auto">
            <div className="bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-yellow-400 to-amber-500 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              ></div>
            </div>
            <p className="text-slate-400 text-sm mt-2">{progress}% complete</p>
          </div>
        )}

        {/* Subtle animation hints */}
        <div className="flex justify-center space-x-2">
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" style={{animationDelay: '0.3s'}}></div>
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" style={{animationDelay: '0.6s'}}></div>
        </div>

        {/* Additional context for longer loads */}
        <div className="text-slate-500 text-sm">
          <p>Ensuring secure access to your data</p>
        </div>
      </div>

      <style jsx>{`
        .hexagon {
          clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
        }

        .animate-spin-slow {
          animation: spin 3s linear infinite;
        }

        .animate-spin-reverse {
          animation: spin 4s linear infinite reverse;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ColonyLoadingScreen;