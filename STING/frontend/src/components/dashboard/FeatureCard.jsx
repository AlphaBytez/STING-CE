import React from 'react';
import { Lock, CheckCircle, TrendingUp } from 'lucide-react';

const FeatureCard = ({ 
  title, 
  description, 
  icon: Icon,
  locked = false,
  progress = 0,
  requirement = '',
  onClick,
  comingSoon = false,
  enterprise = false
}) => {
  const handleClick = () => {
    if (!locked && !comingSoon && onClick) {
      onClick();
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`
        dashboard-card relative overflow-hidden p-6 transition-all duration-300
        ${locked 
          ? 'cursor-not-allowed opacity-60' 
          : comingSoon
          ? 'cursor-not-allowed'
          : 'hover:border-yellow-500/50 hover:shadow-lg hover:scale-105 cursor-pointer'
        }
      `}
    >
      {comingSoon && (
        <div className="absolute top-2 right-2 px-2 py-1 bg-purple-500/20 rounded-full">
          <span className="text-xs text-purple-300 font-medium">Coming Soon</span>
        </div>
      )}
      
      {enterprise && !comingSoon && (
        <div className="absolute top-2 right-2 px-2 py-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-400/30 rounded-full">
          <span className="text-xs text-indigo-300 font-medium">ENTERPRISE</span>
        </div>
      )}
      
      {enterprise && comingSoon && (
        <div className="absolute top-2 right-2 flex flex-col gap-1">
          <div className="px-2 py-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-400/30 rounded-full">
            <span className="text-xs text-indigo-300 font-medium">ENTERPRISE</span>
          </div>
          <div className="px-2 py-1 bg-purple-500/20 rounded-full">
            <span className="text-xs text-purple-300 font-medium">Coming Soon</span>
          </div>
        </div>
      )}

      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-gray-700/50 rounded-lg">
          {Icon && <Icon className={`w-6 h-6 ${locked ? 'text-gray-500' : 'text-yellow-400'}`} />}
        </div>
        {locked && <Lock className="w-5 h-5 text-gray-500" />}
        {!locked && !comingSoon && progress > 0 && progress < 100 && (
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400">{progress}%</span>
          </div>
        )}
        {!locked && !comingSoon && progress === 100 && (
          <CheckCircle className="w-5 h-5 text-green-400" />
        )}
      </div>

      <h3 className={`text-lg font-semibold mb-2 ${locked ? 'text-gray-400' : 'text-white'}`}>
        {title}
      </h3>
      
      <p className={`text-sm mb-4 ${locked ? 'text-gray-500' : 'text-gray-300'}`}>
        {description}
      </p>

      {locked && requirement && (
        <div className="mt-4 pt-4 border-t border-gray-700/50">
          <p className="text-xs text-gray-500">
            <Lock className="w-3 h-3 inline mr-1" />
            {requirement}
          </p>
        </div>
      )}

      {!locked && !comingSoon && progress > 0 && progress < 100 && (
        <div className="mt-4">
          <div className="w-full bg-gray-700/50 rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-yellow-500 to-amber-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FeatureCard;