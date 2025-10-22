import React from 'react';
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const ProgressBar = ({ 
  progress = 0, 
  status = 'running', 
  message = '', 
  showPercentage = true,
  className = "" 
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'downloading':
        return 'bg-blue-500';
      case 'loading':
        return 'bg-purple-500';
      default:
        return 'bg-yellow-500';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'initializing':
        return 'Initializing...';
      case 'starting':
        return 'Starting...';
      case 'downloading':
        return 'Downloading...';
      case 'loading':
        return 'Loading into memory...';
      case 'finalizing':
        return 'Finalizing...';
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return 'Processing...';
    }
  };

  return (
    <div className={`progress-container ${className}`}>
      {/* Status Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium text-gray-900">
            {getStatusText()}
          </span>
        </div>
        {showPercentage && (
          <span className="text-sm font-medium text-gray-600">
            {Math.round(progress)}%
          </span>
        )}
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ease-out ${getStatusColor()}`}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        >
          {/* Animated stripe effect for active progress */}
          {status !== 'completed' && status !== 'error' && progress > 0 && (
            <div 
              className="h-full bg-white bg-opacity-30 animate-pulse"
              style={{
                backgroundImage: 'linear-gradient(45deg, transparent 25%, rgba(255,255,255,0.2) 25%, rgba(255,255,255,0.2) 50%, transparent 50%, transparent 75%, rgba(255,255,255,0.2) 75%)',
                backgroundSize: '1rem 1rem',
                animation: 'progress-stripe 1s linear infinite'
              }}
            />
          )}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className="mt-2 text-sm text-gray-600">
          {message}
        </div>
      )}

      {/* Add CSS animation */}
      <style jsx>{`
        @keyframes progress-stripe {
          0% {
            background-position: 0 0;
          }
          100% {
            background-position: 1rem 0;
          }
        }
      `}</style>
    </div>
  );
};

export default ProgressBar;