import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const MetricCard = ({ 
  title, 
  value, 
  unit = '', 
  trend = 0, 
  trendLabel = '', 
  icon: Icon,
  color = 'yellow',
  loading = false 
}) => {
  const getTrendIcon = () => {
    if (trend > 0) return <TrendingUp className="w-4 h-4" />;
    if (trend < 0) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (trend > 0) return 'text-green-400';
    if (trend < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const getColorClasses = () => {
    const colors = {
      yellow: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30',
      green: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
      blue: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
      purple: 'from-purple-500/20 to-pink-500/20 border-purple-500/30',
      red: 'from-red-500/20 to-rose-500/20 border-red-500/30',
    };
    return colors[color] || colors.yellow;
  };

  const getIconColor = () => {
    const colors = {
      yellow: 'text-yellow-400',
      green: 'text-green-400',
      blue: 'text-blue-400',
      purple: 'text-purple-400',
      red: 'text-red-400',
    };
    return colors[color] || colors.yellow;
  };

  if (loading) {
    return (
      <div className="dashboard-card p-6 animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 bg-gray-700 rounded w-24"></div>
          <div className="h-8 w-8 bg-gray-700 rounded"></div>
        </div>
        <div className="h-8 bg-gray-700 rounded w-32 mb-2"></div>
        <div className="h-4 bg-gray-700 rounded w-20"></div>
      </div>
    );
  }

  return (
    <div className="dashboard-card p-6 transform transition-all duration-300 hover:scale-105 hover:shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300">{title}</h3>
        {Icon && <Icon className={`w-8 h-8 ${getIconColor()} opacity-80`} />}
      </div>
      
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-3xl font-bold text-white">{value}</span>
        {unit && <span className="text-lg text-gray-400">{unit}</span>}
      </div>
      
      {(trend !== 0 || trendLabel) && (
        <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
          {getTrendIcon()}
          <span>{Math.abs(trend)}%</span>
          {trendLabel && <span className="text-gray-400">{trendLabel}</span>}
        </div>
      )}
    </div>
  );
};

export default MetricCard;