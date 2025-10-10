import React from 'react';

/**
 * ActivityTimeline component
 * Displays a vertical timeline of recent user activities
 */
const ActivityTimeline = ({ activities }) => {
  return (
    <div className="activity-card p-3 md:p-4">
      <h3 className="text-base md:text-lg font-semibold text-yellow-400 mb-2 md:mb-3">Recent Activity</h3>
      
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute top-0 left-3 md:left-4 h-full w-0.5 bg-gray-600"></div>
        
        {/* Timeline items */}
        <div className="space-y-4 md:space-y-6 ml-6 md:ml-8">
          {activities.map((activity, index) => (
            <div key={index} className="relative">
              {/* Dot marker */}
              <div className="absolute -left-7 md:-left-10 mt-1">
                <div className={`w-3 h-3 md:w-4 md:h-4 rounded-full ${activity.color || 'bg-blue-500'}`}></div>
              </div>
              
              {/* Content */}
              <div>
                <h4 className="text-sm md:text-md font-semibold text-white mb-1">{activity.title}</h4>
                <p className="text-xs md:text-sm text-gray-300 mb-1">{activity.description}</p>
                <span className="text-xs text-gray-400">{activity.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ActivityTimeline;