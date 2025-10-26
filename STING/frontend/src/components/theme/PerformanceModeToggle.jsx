import React, { useState, useEffect } from 'react';
import { Zap, Battery, Settings, Monitor } from 'lucide-react';

/**
 * Performance Mode Toggle Component
 * Allows users to dynamically adjust GPU performance vs visual quality
 * Integrates with Modern Glass Optimized theme performance tiers
 */
const PerformanceModeToggle = ({ className = "" }) => {
  const [performanceMode, setPerformanceMode] = useState('standard');
  const [batteryLevel, setBatteryLevel] = useState(null);
  const [isPluggedIn, setIsPluggedIn] = useState(true);

  // Performance modes configuration
  const performanceModes = {
    ultra: {
      name: 'Ultra Performance',
      icon: Zap,
      description: 'Maximum performance, minimal effects',
      className: 'ultra-performance-mode',
      gpuSavings: '90%'
    },
    balanced: {
      name: 'Balanced',
      icon: Settings,
      description: 'Optimal performance with good visuals',
      className: 'balanced-performance-mode',
      gpuSavings: '70%'
    },
    standard: {
      name: 'Standard Glass',
      icon: Monitor,
      description: 'Full Modern Glass experience',
      className: '',
      gpuSavings: '0%'
    },
    battery: {
      name: 'Battery Saver',
      icon: Battery,
      description: 'Minimal effects for battery life',
      className: 'battery-saver-mode',
      gpuSavings: '95%'
    }
  };

  // Battery API integration for smart performance suggestions
  useEffect(() => {
    if ('getBattery' in navigator) {
      navigator.getBattery().then(battery => {
        setBatteryLevel(Math.round(battery.level * 100));
        setIsPluggedIn(battery.charging);
        
        // Auto-suggest battery mode when battery is low
        if (battery.level < 0.2 && !battery.charging && performanceMode === 'standard') {
          console.log('🔋 Low battery detected - consider enabling Battery Saver mode');
        }
      });
    }
  }, [performanceMode]);

  // Apply performance mode to document
  useEffect(() => {
    const body = document.body;
    
    // Remove all performance mode classes
    Object.values(performanceModes).forEach(mode => {
      if (mode.className) {
        body.classList.remove(mode.className);
      }
    });
    
    // Add current performance mode class
    const currentMode = performanceModes[performanceMode];
    if (currentMode.className) {
      body.classList.add(currentMode.className);
    }
    
    // Store preference
    localStorage.setItem('sting-performance-mode', performanceMode);
    
    // Log performance mode change for debugging
    console.log(`🎨 Performance mode: ${currentMode.name} (${currentMode.gpuSavings} GPU savings)`);
    
  }, [performanceMode]);

  // Load saved preference on mount
  useEffect(() => {
    const savedMode = localStorage.getItem('sting-performance-mode');
    if (savedMode && performanceModes[savedMode]) {
      setPerformanceMode(savedMode);
    }
  }, []);

  const handleModeChange = (mode) => {
    setPerformanceMode(mode);
  };

  const currentMode = performanceModes[performanceMode];
  const CurrentIcon = currentMode.icon;

  return (
    <div className={`performance-toggle ${className}`}>
      {/* Current mode indicator */}
      <div className="flex items-center gap-2 mb-3">
        <CurrentIcon className="w-4 h-4 text-yellow-400" />
        <span className="text-sm font-medium text-white">{currentMode.name}</span>
        <span className="text-xs text-green-400">-{currentMode.gpuSavings}</span>
      </div>
      
      {/* Battery indicator (if available) */}
      {batteryLevel !== null && (
        <div className="flex items-center gap-2 mb-3 text-xs text-gray-400">
          <Battery className="w-3 h-3" />
          <span>{batteryLevel}%</span>
          {!isPluggedIn && batteryLevel < 20 && (
            <span className="text-yellow-400">⚠ Low</span>
          )}
        </div>
      )}
      
      {/* Mode selection */}
      <div className="space-y-1">
        {Object.entries(performanceModes).map(([key, mode]) => {
          const Icon = mode.icon;
          const isActive = performanceMode === key;
          
          return (
            <button
              key={key}
              onClick={() => handleModeChange(key)}
              className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-colors ${
                isActive 
                  ? 'bg-yellow-500/20 border border-yellow-500/30 text-white' 
                  : 'bg-gray-700/30 hover:bg-gray-600/40 text-gray-300 hover:text-white border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-yellow-400' : 'text-gray-400'}`} />
              <div className="flex-1">
                <div className="font-medium text-sm">{mode.name}</div>
                <div className="text-xs opacity-75">{mode.description}</div>
              </div>
              <span className={`text-xs ${isActive ? 'text-green-400' : 'text-gray-500'}`}>
                -{mode.gpuSavings}
              </span>
            </button>
          );
        })}
      </div>
      
      {/* Performance tip */}
      <div className="mt-3 p-2 bg-blue-500/10 border border-blue-500/20 rounded text-xs text-blue-300">
        💡 Performance modes affect backdrop-filters, shadows, and animations. 
        Changes apply immediately without page refresh.
      </div>
      
      {/* Auto-suggestions */}
      {batteryLevel !== null && batteryLevel < 20 && !isPluggedIn && performanceMode !== 'battery' && (
        <div className="mt-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-xs text-yellow-300">
          🔋 Low battery detected. Consider switching to Battery Saver mode.
        </div>
      )}
    </div>
  );
};

export default PerformanceModeToggle;