import React from 'react';
import { Award, Lock, TrendingUp } from 'lucide-react';

const ExperienceMetric = ({ 
  level = 1, 
  experience = 0, 
  nextLevelExp = 100,
  unlockedFeatures = [],
  nextFeature = null 
}) => {
  const progress = (experience / nextLevelExp) * 100;
  
  const getLevelColor = () => {
    if (level >= 10) return 'from-purple-500 to-pink-500';
    if (level >= 5) return 'from-blue-500 to-purple-500';
    if (level >= 3) return 'from-green-500 to-blue-500';
    return 'from-yellow-500 to-green-500';
  };

  const getLevelTitle = () => {
    if (level >= 10) return 'Master Beekeeper';
    if (level >= 7) return 'Senior Beekeeper';
    if (level >= 5) return 'Experienced Keeper';
    if (level >= 3) return 'Apprentice Keeper';
    return 'Novice Beekeeper';
  };

  return (
    <div className="dashboard-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Award className="w-6 h-6 text-yellow-400" />
          <h3 className="text-lg font-semibold text-white">Experience Level</h3>
        </div>
        <span className={`text-sm px-3 py-1 rounded-full bg-gradient-to-r ${getLevelColor()} text-white font-medium`}>
          Level {level}
        </span>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-400 mb-2">{getLevelTitle()}</p>
        <div className="flex items-center justify-between text-sm text-gray-300 mb-2">
          <span>{experience} XP</span>
          <span>{nextLevelExp} XP</span>
        </div>
        <div className="w-full bg-gray-700/50 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${getLevelColor()} transition-all duration-500 ease-out`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {nextFeature && (
        <div className="bg-gray-700/30 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3">
            <Lock className="w-5 h-5 text-yellow-400" />
            <div>
              <p className="text-sm font-medium text-white">Next Unlock</p>
              <p className="text-xs text-gray-400">{nextFeature} at Level {level + 1}</p>
            </div>
          </div>
        </div>
      )}

      {unlockedFeatures.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-400 mb-2">Recently Unlocked</p>
          {unlockedFeatures.slice(-3).map((feature, index) => (
            <div key={index} className="flex items-center gap-2 text-sm text-green-400">
              <TrendingUp className="w-4 h-4" />
              <span>{feature}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ExperienceMetric;