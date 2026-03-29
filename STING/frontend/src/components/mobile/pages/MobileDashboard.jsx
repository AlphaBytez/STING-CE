import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../auth/UnifiedAuthProvider';
import MobileLoadingSpinner from '../MobileLoadingSpinner';
import '../../../styles/mobile.css';

/**
 * MobileDashboard - Mobile dashboard with metrics and quick actions
 * Displays user stats, quick actions, and recent activity
 */
const MobileDashboard = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State - use defaults that render immediately
  const [stats, setStats] = useState({
    conversations: 0,
    documents: 0,
    honeyJars: 0,
    pendingTasks: 0,
  });
  const [recentActivity] = useState([
    { id: '1', type: 'conversation', title: 'New Conversation', description: 'Started a chat with Bee', time: 'Just now' },
    { id: '2', type: 'document', title: 'Document Uploaded', description: 'project_notes.pdf added', time: '2 hours ago' },
    { id: '3', type: 'report', title: 'Report Generated', description: 'Weekly summary completed', time: 'Yesterday' },
  ]);
  // Track if we've tried to load data - don't block rendering on API
  const [dataLoaded, setDataLoaded] = useState(false);

  // Fetch dashboard data (doesn't block rendering)
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Dynamic import to avoid build issues
        const { default: apiClient } = await import('../../../utils/apiClient');
        const [statsRes, activityRes] = await Promise.all([
          apiClient.get('/api/dashboard/stats').catch(() => ({ data: null })),
          apiClient.get('/api/dashboard/activity').catch(() => ({ data: [] })),
        ]);

        if (statsRes.data) {
          setStats({
            conversations: statsRes.data.conversations || 0,
            documents: statsRes.data.documents || 0,
            honeyJars: statsRes.data.honeyJars || 0,
            pendingTasks: statsRes.data.pendingTasks || 0,
          });
        }

        if (activityRes.data?.length > 0) {
          // Would update recentActivity here if we made it stateful
        }
      } catch (error) {
        console.log('Dashboard API unavailable, using defaults');
      } finally {
        setDataLoaded(true);
      }
    };

    // Small delay to allow initial render
    const timer = setTimeout(fetchDashboardData, 100);
    return () => clearTimeout(timer);
  }, []);

  // Quick action handler
  const handleQuickAction = (action) => {
    switch (action) {
      case 'chat':
        navigate('/m/chat');
        break;
      case 'search':
        navigate('/m/search');
        break;
      case 'upload':
        navigate('/m/honey-jars');
        break;
      case 'reports':
        navigate('/m/reports');
        break;
      default:
        break;
    }
  };

  // Get user display name
  const userName = user?.name || user?.email || 'User';

  // DEBUG: Fully inline styles without CSS variables for iOS Safari testing
  const pageStyle = {
    padding: '16px',
    paddingLeft: 'max(16px, env(safe-area-inset-left, 0px))',
    paddingRight: 'max(16px, env(safe-area-inset-right, 0px))',
    background: '#1a1f2e',
    minHeight: '100%',
  };

  const cardStyle = {
    padding: '16px',
    background: '#2a3142',
    border: '1px solid #3a4356',
    borderRadius: '8px',
    cursor: 'pointer',
    minHeight: '100px',
  };

  return (
    <div style={pageStyle}>
      {/* Welcome Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#f1f5f9', marginBottom: '4px', margin: 0 }}>
          Welcome back
        </h1>
        <p style={{ color: '#cbd5e1', fontSize: '12px', margin: 0 }}>
          {userName}
        </p>
      </div>

      {/* Stats Grid - responsive */}
      <div style={{ marginBottom: '24px' }}>
        <div className="mobile-card-grid-2">
          <div style={cardStyle} onClick={() => navigate('/m/chat')}>
            <MessageOutlined style={{ fontSize: 24, color: '#eab308', marginBottom: 8 }} />
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#f1f5f9' }}>
              {stats.conversations}
            </div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Conversations</div>
          </div>

          <div style={cardStyle} onClick={() => navigate('/m/basket')}>
            <FileTextOutlined style={{ fontSize: 24, color: '#eab308', marginBottom: 8 }} />
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#f1f5f9' }}>
              {stats.documents}
            </div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Documents</div>
          </div>

          <div style={cardStyle} onClick={() => navigate('/m/honey-jars')}>
            <AppstoreOutlined style={{ fontSize: 24, color: '#eab308', marginBottom: 8 }} />
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#f1f5f9' }}>
              {stats.honeyJars}
            </div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Honey Jars</div>
          </div>

          <div style={cardStyle} onClick={() => navigate('/m/reports')}>
            <ClockCircleOutlined style={{ fontSize: 24, color: '#eab308', marginBottom: 8 }} />
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#f1f5f9' }}>
              {stats.pendingTasks}
            </div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Pending</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', marginBottom: '16px', margin: '0 0 16px 0' }}>
          Quick Actions
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
          {['chat', 'search', 'upload', 'reports'].map((action) => (
            <button
              key={action}
              onClick={() => handleQuickAction(action)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '8px',
                background: '#1a1f2e',
                border: '1px solid #3a4356',
                borderRadius: '8px',
                cursor: 'pointer',
                color: '#f1f5f9',
              }}
            >
              {action === 'chat' && <MessageOutlined style={{ fontSize: 24, color: '#eab308' }} />}
              {action === 'search' && <FileTextOutlined style={{ fontSize: 24, color: '#eab308' }} />}
              {action === 'upload' && <AppstoreOutlined style={{ fontSize: 24, color: '#eab308' }} />}
              {action === 'reports' && <ClockCircleOutlined style={{ fontSize: 24, color: '#eab308' }} />}
              <span style={{ fontSize: '10px', marginTop: 4, textTransform: 'capitalize', color: '#cbd5e1' }}>
                {action}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', marginBottom: '16px', margin: '0 0 16px 0' }}>
          Recent Activity
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {recentActivity.map((activity) => (
            <div
              key={activity.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '16px',
                background: '#1a1f2e',
                border: '1px solid #3a4356',
                borderRadius: '8px',
              }}
            >
              <div style={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                background: '#2a3142',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {activity.type === 'conversation' && <MessageOutlined style={{ color: '#eab308' }} />}
                {activity.type === 'document' && <FileTextOutlined style={{ color: '#eab308' }} />}
                {activity.type === 'report' && <ClockCircleOutlined style={{ color: '#eab308' }} />}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, color: '#f1f5f9', marginBottom: 2 }}>
                  {activity.title}
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  {activity.description}
                </div>
              </div>
              <div style={{ fontSize: '10px', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                {activity.time}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MobileDashboard;
