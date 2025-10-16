import React, { useState } from 'react';
import { ExternalLink, Maximize2, Minimize2, RefreshCw } from 'lucide-react';

const EmbeddedGrafanaDashboard = ({ 
  title, 
  dashboardId, 
  description,
  height = 400,
  grafanaBaseUrl = 'http://localhost:3001'  // Grafana is on port 3001 (mapped from container port 3000)
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Construct the embed URL for Grafana
  const embedUrl = `${grafanaBaseUrl}/d-solo/${dashboardId}?orgId=1&refresh=5s&theme=dark&panelId=1`;
  
  const handleLoad = () => {
    setIsLoading(false);
  };
  
  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Force iframe reload
    const iframe = document.getElementById(`grafana-${dashboardId}`);
    if (iframe) {
      iframe.src = iframe.src;
    }
  };

  const handleExpandToggle = () => {
    setIsExpanded(!isExpanded);
  };

  const openInNewTab = () => {
    window.open(`${grafanaBaseUrl}/d/${dashboardId}`, '_blank');
  };

  return (
    <div className={`grafana-dashboard-container bg-slate-800 rounded-xl border border-slate-700 transition-all duration-300 ${
      isExpanded ? 'fixed inset-4 z-50' : 'relative'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {description && (
            <p className="text-sm text-gray-400 mt-1">{description}</p>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white transition-colors"
            title="Refresh Dashboard"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          <button
            onClick={handleExpandToggle}
            className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white transition-colors"
            title={isExpanded ? "Minimize" : "Expand"}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          
          <button
            onClick={openInNewTab}
            className="p-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-black transition-colors"
            title="Open in Grafana"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="grafana-content relative" style={{ height: isExpanded ? 'calc(100vh - 120px)' : height }}>
        {isLoading && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-800 z-10">
            <div className="flex flex-col items-center gap-3 text-gray-400">
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span className="text-center">
                Connecting to Grafana...<br/>
                <span className="text-xs">Dashboard: {dashboardId}</span>
              </span>
            </div>
          </div>
        )}
        
        {(hasError || true) && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-800 z-10">
            <div className="flex flex-col items-center gap-4 text-gray-400 p-8">
              <div className="text-amber-400 text-4xl">📊</div>
              <div className="text-center">
                <p className="text-white font-semibold mb-2">Interactive Dashboard Available</p>
                <p className="text-sm mb-4">Click below to view the "{title}" dashboard in Grafana</p>
                <p className="text-xs text-gray-500 mb-4">
                  For security reasons, dashboards open in a separate tab<br/>
                  Dashboard ID: {dashboardId}
                </p>
                <button
                  onClick={() => window.open(`${grafanaBaseUrl}/d/${dashboardId}`, '_blank')}
                  className="px-6 py-3 bg-amber-500 hover:bg-amber-600 text-black rounded-lg font-semibold text-sm transition-colors"
                >
                  Open {title} Dashboard
                </button>
              </div>
            </div>
          </div>
        )}
        
        <iframe
          id={`grafana-${dashboardId}`}
          src={embedUrl}
          className="w-full h-full border-0 rounded-b-xl"
          title={title}
          onLoad={handleLoad}
          onError={handleError}
          style={{ 
            background: 'transparent',
            minHeight: height,
            display: hasError ? 'none' : 'block'
          }}
        />
      </div>

      {/* Expanded overlay */}
      {isExpanded && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  );
};

export default EmbeddedGrafanaDashboard;