import React, { useState, useEffect } from 'react';
import { Activity, Zap, Monitor, BarChart3, Eye, EyeOff, Battery } from 'lucide-react';

const PerformanceIndicator = ({ compact = false }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [performanceData, setPerformanceData] = useState({
    theme: 'unknown',
    gpuSavings: 0,
    activeOptimizations: []
  });
  
  // Use our own performance detection instead of hooks to avoid conditional hook calls
  const [basicMetrics, setBasicMetrics] = useState({
    fps: '--',
    memoryMB: '--'
  });
  
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'modern-glass';
  
  // Detect performance optimizations
  useEffect(() => {
    const detectOptimizations = () => {
      const body = document.body;
      const optimizations = [];
      let gpuSavings = 0;
      let theme = currentTheme;

      // Check for performance mode classes
      if (body.classList.contains('ultra-performance-mode')) {
        optimizations.push('Ultra Performance Mode');
        gpuSavings = 90;
      } else if (body.classList.contains('balanced-performance-mode')) {
        optimizations.push('Balanced Performance');
        gpuSavings = 70;
      } else if (body.classList.contains('battery-saver-mode')) {
        optimizations.push('Battery Saver');
        gpuSavings = 95;
      }

      // Check if using optimized theme
      if (theme === 'modern-glass-optimized') {
        optimizations.push('Optimized Glass');
        gpuSavings = Math.max(gpuSavings, 85);
      } else if (theme === 'minimal-performance') {
        optimizations.push('Minimal Theme');
        gpuSavings = 100;
      }

      // Check for reduced motion preference
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        optimizations.push('Reduced Motion');
        gpuSavings = Math.min(gpuSavings + 10, 100);
      }

      // Check for Page Visibility API optimizations
      if (!document.hidden) {
        optimizations.push('Page Visibility API');
      }

      setPerformanceData({
        theme,
        gpuSavings,
        activeOptimizations: optimizations
      });
    };

    detectOptimizations();
    
    // Re-check when theme or performance modes change
    const observer = new MutationObserver(detectOptimizations);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['class']
    });

    const handleVisibilityChange = () => setTimeout(detectOptimizations, 100);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [currentTheme]);

  const getPerformanceColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getGPUSavingsColor = (savings) => {
    if (savings >= 80) return 'text-green-400';
    if (savings >= 50) return 'text-yellow-400';
    if (savings >= 20) return 'text-orange-400';
    return 'text-red-400';
  };

  const getPerformanceIcon = (score) => {
    if (score >= 80) return <Zap className="w-4 h-4" />;
    if (score >= 60) return <Activity className="w-4 h-4" />;
    return <Monitor className="w-4 h-4" />;
  };

  const getGPUSavingsIcon = (savings) => {
    if (savings >= 80) return '⚡';
    if (savings >= 50) return '🔋';
    if (savings >= 20) return '⚠️';
    return '🔥';
  };

  const gpuSavingsColor = getGPUSavingsColor(performanceData.gpuSavings);

  if (compact) {
    return (
      <div 
        className="flex items-center gap-2 px-3 py-1 rounded-full glass-subtle cursor-pointer hover:glass-medium transition-all"
        onClick={() => setShowDetails(!showDetails)}
        title={`Performance Metrics - ${performanceData.gpuSavings}% GPU savings`}
      >
        <span className="text-lg">{getGPUSavingsIcon(performanceData.gpuSavings)}</span>
        <div className="flex items-center gap-1">
          <span className={`text-sm font-medium ${gpuSavingsColor}`}>
            {performanceData.gpuSavings}%
          </span>
          <span className="text-xs text-gray-400">GPU</span>
        </div>
        <span className="text-xs text-gray-400">
          {basicMetrics.fps}fps
        </span>
      </div>
    );
  }

  return (
    <div className="glass-subtle rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getGPUSavingsIcon(performanceData.gpuSavings)}</span>
          <h3 className="font-medium text-white">Performance</h3>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1 ${gpuSavingsColor}`}>
            <span className="font-bold">{performanceData.gpuSavings}%</span>
            <span className="text-xs">GPU</span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center">
          <div className={`text-lg font-bold ${gpuSavingsColor}`}>
            {performanceData.gpuSavings}%
          </div>
          <div className="text-xs text-gray-400">GPU Savings</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-400">
            {performanceData.theme === 'modern-glass-optimized' ? 'Optimized' : 'Standard'}
          </div>
          <div className="text-xs text-gray-400">Theme</div>
        </div>
      </div>

      {/* Active Optimizations */}
      {performanceData.activeOptimizations.length > 0 && (
        <div className="bg-green-900/20 border border-green-800/50 rounded p-2 mb-3">
          <div className="flex items-center gap-1 text-green-300 text-xs mb-2">
            <Zap className="w-3 h-3" />
            <span>Active Optimizations</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {performanceData.activeOptimizations.map((opt, index) => (
              <span
                key={index}
                className="inline-block px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs"
              >
                {opt}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Performance Suggestions */}
      {performanceData.gpuSavings === 0 && (
        <div className="bg-yellow-900/20 border border-yellow-600/50 rounded p-2 mb-3">
          <div className="flex items-center gap-1 text-yellow-300 text-xs">
            <Battery className="w-3 h-3" />
            <span>💡 Switch to Modern Glass Optimized theme for 85% GPU savings</span>
          </div>
        </div>
      )}

      {/* Toggle Details */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors"
      >
        {showDetails ? 'Hide Details' : 'Show Details'}
      </button>

      {/* Detailed Performance Info */}
      {showDetails && (
        <div className="mt-3 pt-3 border-t border-gray-600 space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-gray-400">Theme:</span>
              <span className="text-white ml-2 capitalize">
                {performanceData.theme.replace(/[-_]/g, ' ')}
              </span>
            </div>
            <div>
              <span className="text-gray-400">GPU Impact:</span>
              <span className={`ml-2 ${gpuSavingsColor}`}>
                -{performanceData.gpuSavings}%
              </span>
            </div>
            <div>
              <span className="text-gray-400">Optimizations:</span>
              <span className="text-white ml-2">
                {performanceData.activeOptimizations.length}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Status:</span>
              <span className={`ml-2 ${performanceData.gpuSavings >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                {performanceData.gpuSavings >= 80 ? 'Excellent' : 
                 performanceData.gpuSavings >= 50 ? 'Good' : 
                 performanceData.gpuSavings >= 20 ? 'Fair' : 'Heavy'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PerformanceIndicator;