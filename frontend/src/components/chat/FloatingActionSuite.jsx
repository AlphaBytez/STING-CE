import React, { useState, useRef } from 'react';
import {
  Upload,
  Plus,
  Settings,
  Search,
  Download,
  Clock,
  FileText,
  Database,
  X,
  ChevronUp,
  Activity,
  Users,
  MessageCircle
} from 'lucide-react';
import { useRole } from '../user/RoleContext';
import BeeSettings from '../settings/BeeSettings';
import BeeSettingsReadOnly from '../settings/BeeSettingsReadOnly';
import HoneyJarStats from './HoneyJarStats';
import BasketIcon from '../icons/BasketIcon';
import HoneyIcon from '../icons/HoneyIcon';
import FlowerIcon from '../icons/FlowerIcon';
import CrownIcon from '../icons/CrownIcon';
import FeaturePopup from '../common/FeaturePopup';
import './FloatingActionSuite.css';

/**
 * Grains - Floating Action Suite for Bee Chat
 * 
 * A customizable collection of quick-access tools that users can arrange
 * to optimize their workflow. Like individual grains of knowledge,
 * each action provides focused functionality for productive bee interactions.
 * 
 * Features:
 * - Customizable grain arrangement
 * - Role-based grain availability
 * - Live hive status monitoring
 * - Seamless integration with STING ecosystem
 * - Glass morphism design with stackable transparency
 */
const Grains = ({ isSidebar = false, isMobile = false, onFileUpload, onCreateHoneyJar, onSearchKnowledge, onExportChat, onBeeNetworking, honeyJarContext, onHoneyJarChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showBeeSettings, setShowBeeSettings] = useState(false);
  const [showQueueStatus, setShowQueueStatus] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [showFeaturePopup, setShowFeaturePopup] = useState(false);
  const { userRole } = useRole();
  const fileInputRef = useRef(null);

  const isAdmin = userRole === 'admin' || userRole === 'super_admin';
  const isSuperAdmin = userRole === 'super_admin';

  // Removed mock nectar flow status - replaced with honey jar context

  // Feature information for non-working grains
  const featureInfo = {
    'bulk-upload': {
      title: 'Bulk Upload',
      subtitle: 'Upload multiple documents at once',
      description: 'Upload and process multiple files simultaneously with batch processing capabilities. Perfect for importing large document collections into your honey jars.',
      status: 'coming-soon',
      timeline: 'Q2 2024',
      keyFeatures: [
        'Drag-and-drop multiple files',
        'Batch processing with progress tracking',
        'Auto-categorization by file type',
        'Bulk metadata assignment'
      ]
    },
    'sync-all': {
      title: 'Sync All',
      subtitle: 'Synchronize all honey jars',
      description: 'Refresh and synchronize all your honey jars with the latest data, ensuring consistency across your knowledge bases.',
      status: 'development',
      timeline: 'Next release',
      keyFeatures: [
        'Real-time synchronization',
        'Conflict resolution',
        'Background processing',
        'Sync status indicators'
      ]
    },
    'advanced-settings': {
      title: 'Advanced Settings',
      subtitle: 'Fine-tune your hive configuration',
      description: 'Access advanced configuration options for power users, including performance tuning, integration settings, and custom workflows.',
      status: 'beta',
      timeline: 'Available in beta',
      keyFeatures: [
        'Performance optimization',
        'Custom integrations',
        'Workflow automation',
        'Advanced security controls'
      ]
    }
  };

  // Grains (quick actions) - customizable by user preferences
  const grains = [
    {
      id: 'nectar-upload',
      icon: Upload,
      label: 'Gather Nectar',
      color: 'bg-blue-500/20 border-blue-400/30 hover:bg-blue-500/30',
      action: () => fileInputRef.current?.click(),
      tooltip: 'Upload documents to extract knowledge nectar - Supports PDF, Word, text files',
      grainType: 'document',
      working: true
    },
    {
      id: 'comb-builder',
      icon: Database,
      label: 'Build Comb',
      color: 'bg-amber-500/20 border-amber-400/30 hover:bg-amber-500/30',
      action: onCreateHoneyJar,
      tooltip: 'Create a new honey jar to organize and store knowledge collections',
      grainType: 'creation',
      working: true
    },
    {
      id: 'forager',
      icon: Search,
      label: 'Forage Knowledge',
      color: 'bg-purple-500/20 border-purple-400/30 hover:bg-purple-500/30',
      action: onSearchKnowledge,
      tooltip: 'Search across all honey jars to find relevant knowledge and documents',
      grainType: 'search',
      working: true
    },
    {
      id: 'honey-jar-context',
      icon: Database,
      label: 'Honey Jar Context',
      color: 'bg-yellow-500/20 border-yellow-400/30 hover:bg-yellow-500/30',
      action: () => setShowQueueStatus(!showQueueStatus),
      tooltip: 'Select honey jar context for focused knowledge queries',
      badge: honeyJarContext ? '🍯' : null,
      grainType: 'context',
      working: true
    },
    {
      id: 'queen-chamber',
      icon: Settings,
      label: 'Queen\'s Chamber',
      color: 'bg-yellow-500/20 border-yellow-400/30 hover:bg-yellow-500/30',
      action: () => setShowBeeSettings(true),
      tooltip: isAdmin ? 'Access royal settings' : 'View hive configuration',
      badge: isSuperAdmin ? '👑' : isAdmin ? '🔍' : null,
      grainType: 'admin',
      working: true
    },
    {
      id: 'honey-harvest',
      icon: Download,
      label: 'Harvest Honey',
      color: 'bg-gray-500/20 border-gray-400/30 hover:bg-gray-500/30',
      action: onExportChat,
      tooltip: 'Export chat conversation as JSON file for backup or sharing',
      grainType: 'export',
      working: true
    },
    {
      id: 'bulk-upload',
      icon: Plus,
      label: 'Bulk Upload',
      color: 'bg-cyan-500/20 border-cyan-400/30 hover:bg-cyan-500/30',
      action: () => showFeatureDetails('bulk-upload'),
      tooltip: 'Upload multiple files at once (Coming Soon)',
      grainType: 'upload',
      working: false
    },
    {
      id: 'sync-all',
      icon: Activity,
      label: 'Sync All',
      color: 'bg-emerald-500/20 border-emerald-400/30 hover:bg-emerald-500/30',
      action: () => showFeatureDetails('sync-all'),
      tooltip: 'Synchronize all honey jars (In Development)',
      grainType: 'sync',
      working: false
    },
    {
      id: 'advanced-settings',
      icon: Settings,
      label: 'Advanced Settings',
      color: 'bg-rose-500/20 border-rose-400/30 hover:bg-rose-500/30',
      action: () => showFeatureDetails('advanced-settings'),
      tooltip: 'Fine-tune hive configuration (Beta)',
      grainType: 'config',
      working: false
    },
    {
      id: 'swarm-network',
      icon: MessageCircle,
      label: 'Swarm Network',
      color: 'bg-purple-500/20 border-purple-400/30 hover:bg-purple-500/30',
      action: onBeeNetworking || (() => console.log('Swarm Network - Enterprise+ Feature')),
      tooltip: 'Connect with team members for collaborative AI workflows (Enterprise)',
      badge: 'Enterprise+',
      grainType: 'collaboration',
      enterpriseOnly: true,
      working: true
    }
  ];

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && onFileUpload) {
      onFileUpload(file);
    }
    setIsExpanded(false);
  };

  const showFeatureDetails = (featureId) => {
    setSelectedFeature(featureInfo[featureId]);
    setShowFeaturePopup(true);
    setIsExpanded(false);
  };

  const handleActionClick = (grain) => {
    if (!grain.working) {
      showFeatureDetails(grain.id);
      return;
    }
    
    grain.action();
    if (grain.id !== 'hive-monitor') {
      setIsExpanded(false);
    }
  };

  // Sidebar Layout
  if (isSidebar) {
    return (
      <>
        {/* Grains Sidebar */}
        <div className="grains-glass h-full flex flex-col p-4 overflow-hidden">
          {/* Sidebar Header - Fixed */}
          <div className="mb-4 flex-shrink-0">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-2">
              <BasketIcon size={20} color="rgb(251 191 36)" />
              Grains
            </h3>
            <p className="text-sm text-gray-400">Your personalized collection of quick actions</p>
          </div>

          {/* Honey Jar Activity Stats - Collapsible */}
          <div className="mb-4 flex-shrink-0">
            <HoneyJarStats 
              currentHoneyJar={honeyJarContext}
              defaultCollapsed={false}
            />
          </div>

          {/* Grains Grid - Scrollable */}
          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2 flex-shrink-0">
              <FlowerIcon size={16} color="rgb(251 191 36)" variant="simple" />
              Action Grains
            </h4>
            <div className="flex-1 overflow-y-auto overflow-x-visible pr-1 grains-scrollbar">
              <div className="grid grid-cols-2 gap-3 pb-2 px-1 pt-1">
              {grains.map((grain) => (
                <button
                  key={grain.id}
                  onClick={() => handleActionClick(grain)}
                  className={`${grain.color} border backdrop-blur-md p-3 rounded-xl transition-all duration-300 hover:scale-105 hover:backdrop-blur-lg relative group ${!grain.working ? 'opacity-75' : ''}`}
                  title={grain.tooltip}
                  data-tooltip={grain.tooltip}
                  data-grain-type={grain.grainType}
                >
                  <div className="flex flex-col items-center gap-2 text-white">
                    <grain.icon className={`w-5 h-5 ${!grain.working ? 'opacity-60' : ''}`} />
                    <span className="text-xs font-medium text-center leading-tight">{grain.label}</span>
                  </div>
                  {grain.badge && (
                    <span className="absolute -top-1 -right-1 bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/50 text-white text-xs rounded-full min-w-5 h-4 flex items-center justify-center font-bold text-[10px] px-2 border border-red-400/30">
                      {grain.badge}
                    </span>
                  )}
                  {!grain.working && (
                    <div className="absolute inset-0 bg-gray-900/20 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
                      <span className="text-[8px] text-gray-300 font-medium px-1 py-0.5 bg-gray-800/60 rounded">
                        Coming Soon
                      </span>
                    </div>
                  )}
                </button>
              ))}
              </div>
            </div>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md,.json,.csv,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
        />

        {/* Queen's Chamber Modal */}
        {showBeeSettings && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="dashboard-card max-w-4xl max-h-[90vh] overflow-auto relative">
              <div className="absolute top-4 left-4 text-yellow-400 text-sm font-medium flex items-center gap-2">
                👑 Queen's Chamber
              </div>
              <button
                onClick={() => setShowBeeSettings(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white z-10"
              >
                <X className="w-6 h-6" />
              </button>
              <div className="p-6 pt-12">
                {isSuperAdmin ? <BeeSettings /> : <BeeSettingsReadOnly />}
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  // Mobile Layout (Horizontal bar)
  if (isMobile) {
    return (
      <>
        <div className="flex items-center gap-2 overflow-x-auto px-2 py-1">
          {/* Priority grains for mobile - showing only the most important */}
          {grains.filter(g => ['upload-file', 'create-honey-jar', 'search-knowledge', 'export-chat', 'hive-monitor'].includes(g.id)).map((grain) => (
            <button
              key={grain.id}
              onClick={() => handleActionClick(grain)}
              className={`${grain.color} border backdrop-blur-md p-2 rounded-lg transition-all duration-300 flex-shrink-0 relative group ${!grain.working ? 'opacity-75' : ''}`}
              title={grain.tooltip}
            >
              <grain.icon className={`w-4 h-4 ${!grain.working ? 'opacity-60' : ''}`} />
              {grain.badge && (
                <span className="absolute -top-1 -right-1 bg-gradient-to-br from-red-500 to-red-600 text-white text-[10px] rounded-full min-w-4 h-3 flex items-center justify-center font-bold px-1">
                  {grain.badge}
                </span>
              )}
            </button>
          ))}
          
          {/* More button for accessing all grains */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="bg-amber-500/30 hover:bg-amber-500/50 border border-amber-400/30 backdrop-blur-md p-2 rounded-lg transition-all duration-300 flex-shrink-0"
          >
            <ChevronUp className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </button>
        </div>
        
        {/* Expanded view for mobile */}
        {isExpanded && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-end">
            <div className="bg-gray-800/95 backdrop-blur-lg w-full max-h-[60vh] rounded-t-2xl border-t border-gray-600 p-4 animate-slide-up">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <BasketIcon size={20} color="rgb(251 191 36)" />
                  All Grains
                </h3>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="text-gray-400 hover:text-white p-2"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              {/* Honey Jar Stats for mobile */}
              <div className="mb-4">
                <HoneyJarStats 
                  currentHoneyJar={honeyJarContext}
                  defaultCollapsed={true}
                />
              </div>
              
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 overflow-y-auto max-h-[40vh]">
                {grains.map((grain) => (
                  <button
                    key={grain.id}
                    onClick={() => handleActionClick(grain)}
                    className={`${grain.color} border backdrop-blur-md p-3 rounded-xl transition-all duration-300 relative group ${!grain.working ? 'opacity-75' : ''}`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      <grain.icon className={`w-5 h-5 ${!grain.working ? 'opacity-60' : ''}`} />
                      <span className="text-[10px] font-medium text-center leading-tight">{grain.label}</span>
                    </div>
                    {grain.badge && (
                      <span className="absolute -top-1 -right-1 bg-gradient-to-br from-red-500 to-red-600 text-white text-[8px] rounded-full min-w-4 h-3 flex items-center justify-center font-bold px-1">
                        {grain.badge}
                      </span>
                    )}
                    {!grain.working && (
                      <div className="absolute inset-0 bg-gray-900/20 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
                        <span className="text-[8px] text-gray-300 font-medium">
                          Soon
                        </span>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md,.json,.csv,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
        />
        
        {/* Queen's Chamber (Bee Settings Modal) */}
        {showBeeSettings && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-50 p-4">
            <div className="dashboard-card max-w-full sm:max-w-lg md:max-w-2xl lg:max-w-4xl w-full max-h-[90vh] overflow-auto relative mx-4">
              <button
                onClick={() => setShowBeeSettings(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white z-10 p-2"
              >
                <X className="w-6 h-6" />
              </button>
              <div className="p-4 sm:p-6">
                {isSuperAdmin ? <BeeSettings /> : <BeeSettingsReadOnly />}
              </div>
            </div>
          </div>
        )}
        
        {/* Feature Popup */}
        <FeaturePopup 
          isOpen={showFeaturePopup}
          onClose={() => setShowFeaturePopup(false)}
          feature={selectedFeature}
        />
      </>
    );
  }

  // Floating Layout (Original)
  return (
    <>
      {/* Grains Container */}
      <div className="fab-container" style={{ zIndex: showQueueStatus ? 2000 : 1000 }}>
        {/* Honey Jar Context */}
        {showQueueStatus && (
          <div className="floating-nav mb-4 p-4 w-80 animate-fade-in-scale" style={{ zIndex: 1500 }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Honey Jar Context</h3>
              <button
                onClick={() => setShowQueueStatus(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <HoneyJarStats 
              currentHoneyJar={honeyJarContext}
            />
          </div>
        )}

        {/* Action Grains (Floating Buttons) */}
        {isExpanded && (
          <div className="flex flex-col gap-3 mb-4">
            {grains.map((grain, index) => (
              <div
                key={grain.id}
                className="flex items-center gap-3 animate-fade-in-up"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <span className="text-sm text-white bg-gray-800/60 backdrop-blur-md border border-gray-700/50 px-3 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                  {grain.tooltip}
                </span>
                <button
                  onClick={() => handleActionClick(grain)}
                  className={`fab-secondary ${grain.color} border backdrop-blur-md relative group transition-all duration-300 hover:scale-110 hover:backdrop-blur-lg ${!grain.working ? 'opacity-75' : ''}`}
                  title={grain.tooltip}
                  data-grain-type={grain.grainType}
                >
                  <grain.icon className={`w-5 h-5 ${!grain.working ? 'opacity-60' : ''}`} />
                  {grain.badge && (
                    <span className='absolute -top-3 -right-3 bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/50 text-white text-xs rounded-full min-w-6 h-5 flex items-center justify-center font-bold px-2 border border-red-400/30 z-20'>
                      {grain.badge}
                    </span>
                  )}
                  {!grain.working && (
                    <div className="absolute inset-0 bg-gray-900/20 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
                      <span className="text-[6px] text-gray-300 font-medium">
                        Soon
                      </span>
                    </div>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Grains FAB */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`fab-primary backdrop-blur-lg border border-amber-400/30 transition-all duration-300 ${
            isExpanded ? 'rotate-45 bg-red-500/30 hover:bg-red-500/50 border-red-400/40' : 'bg-amber-500/30 hover:bg-amber-500/50'
          }`}
          title={isExpanded ? 'Close Grains' : 'Open Grains - Your personalized collection of quick actions'}
        >
          {isExpanded ? (
            <X className="w-6 h-6" />
          ) : (
            <div className="flex items-center justify-center">
              <BasketIcon size={24} color="rgb(251 191 36)" />
            </div>
          )}
        </button>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,.txt,.md,.json,.csv,.png,.jpg,.jpeg"
        onChange={handleFileSelect}
      />

      {/* Queen's Chamber (Bee Settings Modal) */}
      {showBeeSettings && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="dashboard-card max-w-4xl max-h-[90vh] overflow-auto relative">
            <div className="absolute top-4 left-4 text-yellow-400 text-sm font-medium flex items-center gap-2">
              <CrownIcon size={16} color="rgb(251 191 36)" />
              Queen's Chamber
            </div>
            <button
              onClick={() => setShowBeeSettings(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white z-10"
            >
              <X className="w-6 h-6" />
            </button>
            <div className="p-6 pt-12">
              {isSuperAdmin ? <BeeSettings /> : <BeeSettingsReadOnly />}
            </div>
          </div>
        </div>
      )}

      {/* Feature Popup */}
      <FeaturePopup 
        isOpen={showFeaturePopup}
        onClose={() => setShowFeaturePopup(false)}
        feature={selectedFeature}
      />
    </>
  );
};

export default Grains;