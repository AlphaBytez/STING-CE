import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useKratos } from '../../auth/KratosProvider';
import StatsCard from '../dashboard/StatsCard';
import ActivityTimeline from '../dashboard/ActivityTimeline';

/**
 * Dashboard - Main application dashboard after login
 * Enhanced with statistics cards while maintaining original look
 */
const Dashboard = () => {
  const { identity, logout } = useKratos();
  const navigate = useNavigate();
  
  // Derive account type from identity data if available
  const accountType = identity?.traits?.accountType || 'Standard';
  
  const goToChat = () => navigate('/dashboard/chat');
  const goToSettings = () => navigate('/dashboard/settings');
  const goToReports = () => navigate('/dashboard/reports');
  
  // Sample activity data - in a real app, this would come from an API
  const recentActivities = [
    {
      title: 'New Conversation Started',
      description: 'You started a new chat conversation about project planning',
      time: '10 minutes ago',
      color: 'bg-blue-500'
    },
    {
      title: 'Account Settings Updated',
      description: 'You updated your notification preferences',
      time: '2 hours ago',
      color: 'bg-green-500'
    },
    {
      title: 'File Uploaded',
      description: 'You uploaded project_requirements.pdf',
      time: 'Yesterday at 3:45 PM',
      color: 'bg-yellow-500'
    },
    {
      title: 'Team Member Added',
      description: 'Jane Smith was added to your team',
      time: '2 days ago',
      color: 'bg-purple-500'
    }
  ];
  
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="dashboard-card p-8 text-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-white">Welcome to Your Dashboard</h1>
            <button
              onClick={logout}
              className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded"
            >
              Log Out
            </button>
          </div>
          
          {/* Statistics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatsCard title="Active Sessions" value="24" color="bg-blue-100" />
            <StatsCard title="Messages" value="142" color="bg-green-100" />
            <StatsCard title="Response Rate" value="98%" color="bg-yellow-100" />
            <StatsCard title="Avg. Response Time" value="1.4s" color="bg-purple-100" />
          </div>
          
          <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-4 mb-6">
            <h2 className="text-xl font-semibold text-yellow-400 mb-3">Your Profile</h2>
            {identity ? (
              <div>
                <p className="mb-2">
                  <span className="text-gray-400">Email:</span> {identity.traits.email}
                </p>
                {identity.traits.name && (
                  <p className="mb-2">
                    <span className="text-gray-400">Name:</span> 
                    {identity.traits.name.first} {identity.traits.name.last}
                  </p>
                )}
                <p className="mb-2">
                  <span className="text-gray-400">Account Type:</span> 
                  <span className="capitalize ml-2">{accountType}</span>
                </p>
                <p className="mb-2">
                  <span className="text-gray-400">Email Verified:</span> 
                  {identity.verifiable_addresses?.some(a => a.verified) ? 'Yes' : 'No'}
                </p>
              </div>
            ) : (
              <p className="text-gray-400">Loading profile data...</p>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-4">
              <h3 className="text-lg font-semibold text-yellow-400 mb-2">Quick Actions</h3>
              <div className="space-y-2">
                <button 
                  onClick={goToChat}
                  className="floating-button w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
                >
                  Start New Chat
                </button>
                <button 
                  onClick={goToReports}
                  className="floating-button w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
                >
                  View Reports
                </button>
                <button 
                  onClick={goToSettings}
                  className="floating-button w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
                >
                  Account Settings
                </button>
              </div>
            </div>
            
            <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-4">
              <h3 className="text-lg font-semibold text-yellow-400 mb-2">Account Status</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Account Type:</span>
                  <span className="capitalize">{accountType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Status:</span>
                  <span className="text-green-400">Active</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Next Billing:</span>
                  <span>N/A</span>
                </div>
                <div className="mt-4">
                  <button className="floating-button w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded">
                    Upgrade Plan
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Activity Timeline */}
          <div className="mt-6">
            <ActivityTimeline activities={recentActivities} />
          </div>
      </div>
    </div>
  );
};

export default Dashboard;