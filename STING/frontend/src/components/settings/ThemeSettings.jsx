import React, { useState } from 'react';
import { 
  Palette, 
  Monitor, 
  Zap, 
  Eye, 
  Smartphone, 
  Settings,
  Check,
  Star,
  Gauge,
  Sparkles,
  Terminal,
  Layers
} from 'lucide-react';
import { useTheme, THEMES } from '../theme/ThemeManager';

const ThemeSettings = () => {
  const { currentTheme, themeConfig, switchTheme, isTransitioning } = useTheme();
  const [previewTheme, setPreviewTheme] = useState(null);

  const getThemeIcon = (theme) => {
    switch (theme) {
      case THEMES.MODERN:
        return <Layers className="w-6 h-6" />;
      case THEMES.RETRO_TERMINAL:
        return <Terminal className="w-6 h-6" />;
      default:
        return <Palette className="w-6 h-6" />;
    }
  };

  const getPerformanceColor = (performance) => {
    switch (performance) {
      case 'High Performance':
        return 'text-green-400';
      case 'Standard':
        return 'text-yellow-400';
      case 'Resource Intensive':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'Performance':
        return 'bg-green-900/20 text-green-300 border-green-800/50';
      case 'Premium':
        return 'bg-blue-900/20 text-blue-300 border-blue-800/50';
      case 'Experimental':
        return 'bg-purple-900/20 text-purple-300 border-purple-800/50';
      default:
        return 'bg-gray-900/20 text-gray-300 border-gray-800/50';
    }
  };

  const handleThemePreview = (theme) => {
    if (theme === currentTheme) return;
    
    // For now, just switch immediately. In the future, we could implement
    // a temporary preview that reverts after a few seconds
    setPreviewTheme(theme);
    setTimeout(() => setPreviewTheme(null), 100);
    switchTheme(theme);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Palette className="w-5 h-5 text-purple-400" />
            Theme Settings
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Choose your preferred visual theme and performance level
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Monitor className="w-4 h-4" />
          <span>Auto-saves to browser</span>
        </div>
      </div>

      {/* Current Theme Info */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              {getThemeIcon(currentTheme)}
            </div>
            <div>
              <h3 className="font-medium text-white">
                Currently Using: {themeConfig[currentTheme]?.name}
              </h3>
              <p className="text-sm text-gray-400">
                {themeConfig[currentTheme]?.description}
              </p>
            </div>
          </div>
          <div className={`px-2 py-1 rounded text-xs font-medium ${
            getPerformanceColor(themeConfig[currentTheme]?.performance)
          }`}>
            <div className="flex items-center gap-1">
              <Gauge className="w-3 h-3" />
              {themeConfig[currentTheme]?.performance}
            </div>
          </div>
        </div>
      </div>

      {/* Theme Selection */}
      <div>
        <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-400" />
          Available Themes
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(THEMES).map(([key, themeId]) => {
            const config = themeConfig[themeId];
            const isActive = currentTheme === themeId;
            const isPreviewing = previewTheme === themeId;
            
            return (
              <div
                key={themeId}
                className={`relative border rounded-lg p-4 transition-all cursor-pointer ${
                  isActive 
                    ? 'border-purple-500 bg-purple-900/10' 
                    : 'border-slate-600 bg-slate-800/30 hover:border-slate-500 hover:bg-slate-700/30'
                } ${isTransitioning && isActive ? 'opacity-75' : ''}`}
                onClick={() => handleThemePreview(themeId)}
              >
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute top-2 right-2">
                    <div className="flex items-center justify-center w-6 h-6 bg-purple-500 rounded-full">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  </div>
                )}

                {/* Theme preview/icon */}
                <div className="flex items-start gap-3 mb-3">
                  <div className={`p-3 rounded-lg ${
                    themeId === THEMES.MODERN 
                      ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-400/30' 
                      : 'bg-green-900/20 border border-green-400/30'
                  }`}>
                    {getThemeIcon(themeId)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-white">{config.name}</h4>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                        getCategoryColor(config.category)
                      }`}>
                        {config.category}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mb-2">{config.description}</p>
                  </div>
                </div>

                {/* Performance indicator */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1">
                    <Zap className={`w-3 h-3 ${getPerformanceColor(config.performance)}`} />
                    <span className={getPerformanceColor(config.performance)}>
                      {config.performance}
                    </span>
                  </div>
                  <div className="text-gray-500">
                    {config.features.length} features
                  </div>
                </div>

                {/* Features list */}
                <div className="mt-3 pt-3 border-t border-slate-700">
                  <div className="flex flex-wrap gap-1">
                    {config.features.map((feature, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-slate-700/50 text-xs text-gray-300 rounded"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Loading state */}
                {isTransitioning && isActive && (
                  <div className="absolute inset-0 flex items-center justify-center sting-glass-strong rounded-lg">
                    <div className="flex items-center gap-2 text-purple-400">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400"></div>
                      <span className="text-sm">Applying...</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Theme Recommendations */}
      <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
        <div className="flex items-center gap-2 text-blue-300 mb-3">
          <Star className="w-4 h-4" />
          <span className="font-medium">Recommendations</span>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex items-start gap-2">
            <Zap className="w-4 h-4 text-green-400 mt-0.5" />
            <div>
              <span className="text-white font-medium">For better performance:</span>
              <span className="text-blue-200 ml-1">
                Use Retro Terminal theme on older devices or when running resource-intensive tasks
              </span>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Eye className="w-4 h-4 text-purple-400 mt-0.5" />
            <div>
              <span className="text-white font-medium">For visual appeal:</span>
              <span className="text-blue-200 ml-1">
                Modern Glass theme provides rich visual effects and smooth animations
              </span>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Smartphone className="w-4 h-4 text-yellow-400 mt-0.5" />
            <div>
              <span className="text-white font-medium">On mobile devices:</span>
              <span className="text-blue-200 ml-1">
                Retro Terminal automatically disables effects for better battery life
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="border-t border-slate-700 pt-6">
        <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
          <Settings className="w-4 h-4 text-gray-400" />
          Advanced Options
        </h3>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
            <div>
              <span className="text-white font-medium">Auto Performance Mode</span>
              <p className="text-sm text-gray-400">
                Automatically switch to high-performance theme on low-end devices
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked={false} />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
            </label>
          </div>
          
          <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
            <div>
              <span className="text-white font-medium">Reduce Motion</span>
              <p className="text-sm text-gray-400">
                Disable animations and transitions for accessibility
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked={false} />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThemeSettings;