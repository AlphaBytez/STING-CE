import React from 'react';
import { Terminal, Layers, Code, Activity, Zap } from 'lucide-react';

const ThemeDemo = ({ theme }) => {
  const isRetro = theme === 'retro-terminal';

  return (
    <div className="p-4 border border-slate-600 rounded-lg bg-slate-800/30 min-h-[200px]">
      <div className="flex items-center gap-2 mb-3">
        {isRetro ? (
          <Terminal className="w-5 h-5 text-green-400" />
        ) : (
          <Layers className="w-5 h-5 text-purple-400" />
        )}
        <h3 className="font-mono text-white font-bold">
          {isRetro ? 'RETRO_TERMINAL_THEME' : 'Modern Glass Theme'}
        </h3>
      </div>

      {/* Sample UI Elements */}
      <div className="space-y-3">
        {/* Buttons */}
        <div className="flex gap-2">
          <button className={`px-3 py-1 text-sm font-medium transition-colors ${
            isRetro 
              ? 'bg-green-500 text-black border border-green-500 hover:bg-green-400'
              : 'bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:shadow-lg'
          }`}>
            Primary
          </button>
          <button className={`px-3 py-1 text-sm border transition-colors ${
            isRetro
              ? 'border-gray-500 text-green-400 hover:bg-gray-800'
              : 'border-gray-400 text-gray-300 rounded-lg hover:bg-white/10 backdrop-blur'
          }`}>
            Secondary
          </button>
        </div>

        {/* Input */}
        <div>
          <input
            type="text"
            placeholder={isRetro ? "> Enter command..." : "Enter text..."}
            className={`w-full px-3 py-2 text-sm transition-all ${
              isRetro
                ? 'bg-black border border-gray-600 text-green-400 font-mono focus:border-green-400'
                : 'bg-white/10 backdrop-blur border border-white/20 text-white rounded-lg focus:ring-2 focus:ring-purple-500'
            }`}
          />
        </div>

        {/* Card */}
        <div className={`p-3 transition-all ${
          isRetro
            ? 'bg-gray-900 border border-gray-700 text-green-300'
            : 'bg-white/5 backdrop-blur-md border border-white/10 rounded-xl text-white shadow-lg'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {isRetro ? (
              <Code className="w-4 h-4" />
            ) : (
              <Activity className="w-4 h-4" />
            )}
            <span className="text-xs font-medium">
              {isRetro ? 'SYSTEM_STATUS' : 'Dashboard Card'}
            </span>
          </div>
          <div className="text-xs">
            {isRetro ? (
              <div className="font-mono">
                <div>CPU: 45% MEM: 67% DISK: 23%</div>
                <div className="text-yellow-400">WARNING: High memory usage</div>
              </div>
            ) : (
              <div>
                <div>Beautiful glassmorphism effects with</div>
                <div>smooth animations and gradients</div>
              </div>
            )}
          </div>
        </div>

        {/* Progress/Loading */}
        <div className="space-y-2">
          <div className="text-xs text-gray-400">
            {isRetro ? 'PROCESSING...' : 'Loading...'}
          </div>
          <div className={`w-full h-2 overflow-hidden ${
            isRetro ? 'bg-gray-800 border border-gray-600' : 'bg-white/10 rounded-full'
          }`}>
            <div className={`h-full transition-all ${
              isRetro
                ? 'bg-green-400 bg-opacity-80'
                : 'bg-gradient-to-r from-purple-500 to-blue-500'
            }`} style={{ width: '65%' }}>
            </div>
          </div>
        </div>

        {/* Performance indicator */}
        <div className="flex items-center justify-between text-xs mt-3 pt-2 border-t border-gray-600">
          <div className="flex items-center gap-1">
            <Zap className="w-3 h-3 text-green-400" />
            <span className="text-gray-400">Performance:</span>
          </div>
          <div className={isRetro ? 'text-green-400 font-mono' : 'text-purple-400'}>
            {isRetro ? '60FPS | LOW-RESOURCE' : '45FPS | RICH-EFFECTS'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThemeDemo;