import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  Zap, 
  Settings, 
  Users, 
  FileText,
  Database,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';

const ChatModeSelector = ({ currentMode, onModeChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const chatModes = {
    simple: {
      id: 'simple',
      name: 'Simple Chat',
      description: 'Clean, focused chat experience',
      icon: MessageSquare,
      features: ['Easy to use', 'Quick responses', 'File attachments', 'Basic settings'],
      color: 'blue',
      recommended: 'New Users'
    },
    advanced: {
      id: 'advanced',
      name: 'Advanced Chat',
      description: 'Full-featured chat with tools',
      icon: Zap,
      features: ['Honey jar context', 'Tool integration', 'Chat history', 'Advanced settings'],
      color: 'amber',
      recommended: 'Power Users'
    }
  };

  const currentModeData = chatModes[currentMode] || chatModes.simple;
  const otherMode = currentMode === 'simple' ? 'advanced' : 'simple';
  const otherModeData = chatModes[otherMode];

  // Load saved preference
  useEffect(() => {
    const saved = localStorage.getItem('sting-chat-mode');
    if (saved && saved !== currentMode) {
      onModeChange(saved);
    }
  }, [currentMode, onModeChange]);

  const handleModeSwitch = (newMode) => {
    localStorage.setItem('sting-chat-mode', newMode);
    onModeChange(newMode);
    setIsExpanded(false);
  };

  const ModeIcon = currentModeData.icon;
  const OtherIcon = otherModeData.icon;

  if (!isExpanded) {
    return (
      <div className="relative">
        {/* Compact Toggle */}
        <button
          onClick={() => setIsExpanded(true)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
            currentMode === 'simple'
              ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
              : 'bg-amber-500/20 border-amber-500/50 text-amber-400'
          }`}
          title="Switch chat mode"
        >
          <ModeIcon className="w-4 h-4" />
          <span className="text-sm font-medium">{currentModeData.name}</span>
          <Settings className="w-3 h-3 opacity-60" />
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Floating Popup Overlay */}
      {isExpanded && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setIsExpanded(false)}>
          <div className="sting-glass-card sting-elevation-floating border border-slate-700 rounded-lg shadow-xl min-w-80 max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Chat Mode</h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1 hover:bg-slate-700 rounded text-slate-400"
            >
              ×
            </button>
          </div>

          {/* Current Mode */}
          <div className={`p-4 rounded-lg border mb-4 ${
            currentMode === 'simple'
              ? 'bg-blue-500/10 border-blue-500/30'
              : 'bg-amber-500/10 border-amber-500/30'
          }`}>
            <div className="flex items-center gap-3 mb-2">
              <ModeIcon className={`w-5 h-5 ${
                currentMode === 'simple' ? 'text-blue-400' : 'text-amber-400'
              }`} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">{currentModeData.name}</span>
                  <span className="text-xs px-2 py-1 bg-green-600 text-green-100 rounded">
                    Current
                  </span>
                </div>
                <p className="text-sm text-slate-400">{currentModeData.description}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-3">
              {currentModeData.features.map((feature, index) => (
                <div key={index} className="flex items-center gap-2 text-xs text-slate-300">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    currentMode === 'simple' ? 'bg-blue-400' : 'bg-amber-400'
                  }`} />
                  {feature}
                </div>
              ))}
            </div>
          </div>

          {/* Switch Option */}
          <div className="p-4 border border-slate-600 rounded-lg hover:bg-slate-800/50 transition-colors">
            <button
              onClick={() => handleModeSwitch(otherMode)}
              className="w-full text-left"
            >
              <div className="flex items-center gap-3 mb-2">
                <OtherIcon className={`w-5 h-5 ${
                  otherMode === 'simple' ? 'text-blue-400' : 'text-amber-400'
                }`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{otherModeData.name}</span>
                    <span className="text-xs px-2 py-1 bg-slate-700 text-slate-300 rounded">
                      {otherModeData.recommended}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">{otherModeData.description}</p>
                </div>
                <div className="text-slate-500">
                  {currentMode === 'simple' ? <ToggleRight /> : <ToggleLeft />}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-3">
                {otherModeData.features.map((feature, index) => (
                  <div key={index} className="flex items-center gap-2 text-xs text-slate-400">
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      otherMode === 'simple' ? 'bg-blue-400' : 'bg-amber-400'
                    }`} />
                    {feature}
                  </div>
                ))}
              </div>
            </button>
          </div>

          {/* Quick Comparison */}
          <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
            <h4 className="text-sm font-medium text-white mb-2">Quick Comparison</h4>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-blue-400 font-medium mb-1">Simple Mode</div>
                <ul className="space-y-1 text-slate-400">
                  <li>• ChatGPT-like interface</li>
                  <li>• Essential features only</li>
                  <li>• Perfect for quick tasks</li>
                </ul>
              </div>
              <div>
                <div className="text-amber-400 font-medium mb-1">Advanced Mode</div>
                <ul className="space-y-1 text-slate-400">
                  <li>• Full STING integration</li>
                  <li>• Honey jar context</li>
                  <li>• Advanced tools & history</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Switch Button */}
          <button
            onClick={() => handleModeSwitch(otherMode)}
            className={`w-full mt-4 px-4 py-2 rounded-lg font-medium transition-colors ${
              otherMode === 'simple'
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-amber-600 hover:bg-amber-700 text-white'
            }`}
          >
            Switch to {otherModeData.name}
          </button>
          </div>
        </div>
        </div>
      )}
      
      {/* Compact Trigger Button */}
      <div className="relative">
        <button
          onClick={() => setIsExpanded(true)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
            currentMode === 'simple'
              ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
              : 'bg-amber-500/20 border-amber-500/50 text-amber-400'
          }`}
          title="Switch chat mode"
        >
          <ModeIcon className="w-4 h-4" />
          <span className="text-sm font-medium">{currentModeData.name}</span>
          <Settings className="w-3 h-3 opacity-60" />
        </button>
      </div>
    </>
  );
};

export default ChatModeSelector;