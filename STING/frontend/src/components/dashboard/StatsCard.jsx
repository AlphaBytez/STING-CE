import React from 'react';

const StatsCard = ({ title, value, color }) => (
  <div className="stats-card p-4 text-center">
    <h3 className="text-lg font-semibold text-gray-300">{title}</h3>
    <p className="text-2xl font-bold text-gray-100">{value}</p>
  </div>
);

export default StatsCard;