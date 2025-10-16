import React, { useEffect, useRef } from 'react';
import { Terminal, Copy, Download } from 'lucide-react';

const TerminalOutput = ({ logs = [], title = "Terminal Output", isVisible = true, className = "" }) => {
  const terminalRef = useRef(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const copyToClipboard = () => {
    const logText = logs.join('\n');
    navigator.clipboard.writeText(logText).then(() => {
      // Could add a toast notification here
      console.log('Logs copied to clipboard');
    });
  };

  const downloadLogs = () => {
    const logText = logs.join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sting-llm-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isVisible) return null;

  return (
    <div className={`terminal-container ${className}`}>
      {/* Terminal Header */}
      <div className="bg-gray-800 text-white px-4 py-2 rounded-t-lg flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4" />
          <span className="font-mono text-sm">{title}</span>
          <div className="flex gap-1 ml-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
        </div>
        
        {/* Terminal Controls */}
        <div className="flex gap-2">
          <button
            onClick={copyToClipboard}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title="Copy logs to clipboard"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={downloadLogs}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title="Download logs as file"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div 
        ref={terminalRef}
        className="bg-black text-green-400 font-mono text-sm p-4 rounded-b-lg overflow-y-auto"
        style={{ height: '300px', maxHeight: '400px' }}
      >
        {logs.length === 0 ? (
          <div className="text-gray-500 italic">Waiting for output...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="whitespace-pre-wrap break-words">
              <span className="text-gray-500 mr-2">
                {String(index + 1).padStart(3, '0')}
              </span>
              <span className="text-green-400">{log}</span>
            </div>
          ))
        )}
        
        {/* Blinking cursor */}
        <div className="inline-block w-2 h-4 bg-green-400 animate-pulse mt-1"></div>
      </div>
    </div>
  );
};

export default TerminalOutput;