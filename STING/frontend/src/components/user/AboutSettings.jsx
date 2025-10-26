import React from 'react';
import { ExternalLink, Heart, Code, Shield, Globe } from 'lucide-react';

const AboutSettings = () => {
  return (
    <div className="space-y-6">
      {/* STING Information */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-lg">
            <Shield className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">STING Platform</h3>
            <p className="text-slate-400 text-sm">Secure, Transparent, Intelligent, Natural Gateway</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-400">Version:</span>
            <span className="text-white ml-2">Community Edition v1.0</span>
          </div>
          <div>
            <span className="text-slate-400">Release:</span>
            <span className="text-white ml-2">Open Source</span>
          </div>
          <div>
            <span className="text-slate-400">Build:</span>
            <span className="text-white ml-2">{process.env.REACT_APP_BUILD_VERSION || 'Development'}</span>
          </div>
          <div>
            <span className="text-slate-400">Environment:</span>
            <span className="text-white ml-2">{process.env.NODE_ENV || 'Production'}</span>
          </div>
        </div>
      </div>

      {/* Company Information */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg">
            <Code className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">AlphaBytez</h3>
            <p className="text-slate-400 text-sm">Innovative AI & Security Solutions</p>
          </div>
        </div>
        
        <p className="text-slate-300 text-sm mb-4">
          AlphaBytez is a forward-thinking development company specializing in AI-powered security platforms, 
          intelligent document management, and privacy-preserving technologies. We believe in building tools 
          that empower organizations while maintaining the highest standards of security and transparency.
        </p>
        
        <div className="flex items-center gap-4 text-sm">
          <a 
            href="https://alphabytez.com" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
          >
            <Globe className="w-4 h-4" />
            Website
            <ExternalLink className="w-3 h-3" />
          </a>
          <a 
            href="https://github.com/alphabytez" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
          >
            <Code className="w-4 h-4" />
            GitHub
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Open Source Information */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-lg">
            <Heart className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">Open Source</h3>
            <p className="text-slate-400 text-sm">Community-Driven Development</p>
          </div>
        </div>
        
        <p className="text-slate-300 text-sm mb-4">
          STING is proudly open source and community-driven. We believe in transparency, collaboration, 
          and building tools that serve the greater good. Contributions, feedback, and community involvement 
          are always welcome and appreciated.
        </p>
        
        <div className="flex items-center gap-4 text-sm">
          <a 
            href="https://github.com/captain-wolf/STING-CE" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-green-400 hover:text-green-300 transition-colors"
          >
            <Code className="w-4 h-4" />
            Source Code
            <ExternalLink className="w-3 h-3" />
          </a>
          <a 
            href="https://github.com/captain-wolf/STING-CE/issues" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-green-400 hover:text-green-300 transition-colors"
          >
            <Shield className="w-4 h-4" />
            Report Issues
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Copyright and Legal */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="text-center">
          <p className="text-slate-400 text-sm mb-2">
            © {new Date().getFullYear()} AlphaBytez. All rights reserved.
          </p>
          <p className="text-slate-500 text-xs">
            STING Community Edition is released under the MIT License.
            See the LICENSE file in the source repository for full terms.
          </p>
        </div>
      </div>

      {/* Technical Details */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h4 className="text-white font-medium mb-3">Technical Stack</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="text-center p-2 bg-slate-700/30 rounded-lg">
            <div className="text-blue-400 font-medium">React 18</div>
            <div className="text-slate-400 text-xs">Frontend</div>
          </div>
          <div className="text-center p-2 bg-slate-700/30 rounded-lg">
            <div className="text-green-400 font-medium">Flask</div>
            <div className="text-slate-400 text-xs">Backend</div>
          </div>
          <div className="text-center p-2 bg-slate-700/30 rounded-lg">
            <div className="text-purple-400 font-medium">PostgreSQL</div>
            <div className="text-slate-400 text-xs">Database</div>
          </div>
          <div className="text-center p-2 bg-slate-700/30 rounded-lg">
            <div className="text-red-400 font-medium">Redis</div>
            <div className="text-slate-400 text-xs">Cache</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutSettings;