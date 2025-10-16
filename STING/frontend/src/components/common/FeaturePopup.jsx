import React from 'react';
import { X, Calendar, Users, Zap, Shield, Info } from 'lucide-react';

/**
 * FeaturePopup - Information modal for upcoming/premium features
 * Displays feature details, availability, and requirements
 */
const FeaturePopup = ({ isOpen, onClose, feature }) => {
  if (!isOpen || !feature) return null;

  const getStatusIcon = (status) => {
    switch (status) {
      case 'coming-soon': return <Calendar className="w-5 h-5 text-blue-400" />;
      case 'enterprise': return <Shield className="w-5 h-5 text-purple-400" />;
      case 'premium': return <Zap className="w-5 h-5 text-yellow-400" />;
      case 'beta': return <Users className="w-5 h-5 text-green-400" />;
      default: return <Info className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      'coming-soon': { text: 'Coming Soon', bg: 'bg-blue-500/20 border-blue-500/30 text-blue-300' },
      'enterprise': { text: 'Enterprise+', bg: 'bg-purple-500/20 border-purple-500/30 text-purple-300' },
      'premium': { text: 'Premium', bg: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300' },
      'beta': { text: 'Beta', bg: 'bg-green-500/20 border-green-500/30 text-green-300' },
      'development': { text: 'In Development', bg: 'bg-orange-500/20 border-orange-500/30 text-orange-300' }
    };
    
    const badge = badges[status] || badges['coming-soon'];
    return (
      <span className={`px-3 py-1 rounded-full border text-xs font-medium ${badge.bg}`}>
        {badge.text}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-lg flex items-center justify-center z-50 p-4">
      {/* Glass Modal */}
      <div className="glass-card max-w-md w-full max-h-[80vh] overflow-auto relative animate-fade-in-scale">
        {/* Header */}
        <div className="flex items-start gap-3 p-6 pb-4">
          <div className="flex-shrink-0 p-2 rounded-lg bg-gray-700/30">
            {getStatusIcon(feature.status)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-semibold text-white truncate">{feature.title}</h3>
              {getStatusBadge(feature.status)}
            </div>
            <p className="text-sm text-gray-400">{feature.subtitle}</p>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 p-1 text-gray-400 hover:text-white transition-colors duration-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 pb-6">
          <div className="space-y-4">
            {/* Description */}
            <div>
              <p className="text-gray-300 text-sm leading-relaxed">{feature.description}</p>
            </div>

            {/* Key Features */}
            {feature.keyFeatures && (
              <div>
                <h4 className="text-sm font-medium text-white mb-2">Key Features</h4>
                <ul className="space-y-1.5">
                  {feature.keyFeatures.map((item, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 mt-2 flex-shrink-0"></span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Requirements */}
            {feature.requirements && (
              <div>
                <h4 className="text-sm font-medium text-white mb-2">Requirements</h4>
                <div className="bg-gray-800/40 rounded-lg p-3">
                  <p className="text-xs text-gray-400">{feature.requirements}</p>
                </div>
              </div>
            )}

            {/* Timeline */}
            {feature.timeline && (
              <div>
                <h4 className="text-sm font-medium text-white mb-2">Availability</h4>
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-400">{feature.timeline}</span>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex gap-2">
            {feature.status === 'enterprise' && (
              <button className="flex-1 py-2 px-4 bg-purple-600/20 border border-purple-500/30 text-purple-300 rounded-lg hover:bg-purple-600/30 transition-colors duration-200 text-sm font-medium">
                Contact Sales
              </button>
            )}
            {feature.learnMore && (
              <button className="flex-1 py-2 px-4 bg-gray-700/40 border border-gray-600/50 text-gray-300 rounded-lg hover:bg-gray-700/60 transition-colors duration-200 text-sm font-medium">
                Learn More
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-200 text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeaturePopup;