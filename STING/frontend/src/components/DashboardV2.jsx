import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Statistic, Row, Col, Button, Timeline, Space, Typography } from 'antd';
import GlassCard from './common/GlassCard';
import { 
  ThunderboltOutlined, 
  MessageOutlined, 
  BarChartOutlined, 
  ClockCircleOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  UploadOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { useKratos } from '../auth/KratosProvider';

const { Title, Text } = Typography;

const DashboardV2 = () => {
  const { identity, logout } = useKratos();
  const navigate = useNavigate();
  
  // Clean up any leftover registration flags
  useEffect(() => {
    // Remove any lingering registration flags that weren't cleaned up
    localStorage.removeItem('registration_email');
    localStorage.removeItem('justRegistered');
  }, []);
  
  const accountType = identity?.traits?.accountType || 'Standard';
  
  const goToChat = () => navigate('/dashboard/chat');
  const goToSettings = () => navigate('/dashboard/settings');
  
  // Sample activity data
  const recentActivities = [
    {
      children: (
        <div>
          <Text strong>New Conversation Started</Text>
          <br />
          <Text type="secondary">You started a new chat conversation about project planning</Text>
        </div>
      ),
      color: 'blue',
      dot: <MessageOutlined />,
    },
    {
      children: (
        <div>
          <Text strong>Account Settings Updated</Text>
          <br />
          <Text type="secondary">You updated your notification preferences</Text>
        </div>
      ),
      color: 'green',
      dot: <CheckCircleOutlined />,
    },
    {
      children: (
        <div>
          <Text strong>File Uploaded</Text>
          <br />
          <Text type="secondary">You uploaded project_requirements.pdf</Text>
        </div>
      ),
      color: 'yellow',
      dot: <UploadOutlined />,
    },
    {
      children: (
        <div>
          <Text strong>Team Member Added</Text>
          <br />
          <Text type="secondary">Jane Smith was added to your team</Text>
        </div>
      ),
      color: 'purple',
      dot: <TeamOutlined />,
    },
  ];
  
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ marginBottom: '8px' }}>
          <Title level={2} style={{ margin: 0, color: '#f59e0b' }}>The Buzz:</Title>
        </div>
        <div style={{ marginBottom: '4px' }}>
          <Text type="secondary" style={{ fontSize: '16px', fontWeight: '500' }}>
            Bee Smart. Bee Secure.
          </Text>
        </div>
        <Text type="secondary">
          Welcome to your Hive command center - monitor activity, manage your intelligent swarm, and stay ahead of threats
        </Text>
      </div>
      
      {/* Statistics Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: '32px' }}>
        <Col xs={24} sm={12} md={6}>
          <GlassCard elevation="high">
            <Statistic
              title="Active Sessions"
              value={24}
              prefix={<ThunderboltOutlined style={{ color: '#eab308' }} />}
              suffix={
                <span style={{ fontSize: '14px', color: '#5d9b63' }}>
                  <ArrowUpOutlined /> +3 today
                </span>
              }
            />
          </GlassCard>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <GlassCard elevation="high">
            <Statistic
              title="Messages"
              value={142}
              prefix={<MessageOutlined style={{ color: '#eab308' }} />}
              suffix={
                <span style={{ fontSize: '14px', color: '#5d9b63' }}>
                  <ArrowUpOutlined /> +18 today
                </span>
              }
            />
          </GlassCard>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <GlassCard elevation="high">
            <Statistic
              title="Response Rate"
              value={98}
              suffix="%"
              prefix={<BarChartOutlined style={{ color: '#eab308' }} />}
              valueStyle={{ color: '#5d9b63' }}
            />
          </GlassCard>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <GlassCard elevation="high">
            <Statistic
              title="Avg Response Time"
              value={1.2}
              suffix="s"
              prefix={<ClockCircleOutlined style={{ color: '#eab308' }} />}
              precision={1}
            />
          </GlassCard>
        </Col>
      </Row>
      
      {/* Main Content */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <GlassCard 
            title="Quick Actions" 
            elevation="medium"
            style={{ marginBottom: '24px' }}
          >
            <Space size="large">
              <Button 
                type="primary" 
                size="large"
                icon={<MessageOutlined />}
                onClick={goToChat}
              >
                Start New Chat
              </Button>
              <Button 
                size="large"
                icon={<BarChartOutlined />}
                onClick={() => navigate('/dashboard/analytics')}
              >
                View Analytics
              </Button>
              <Button 
                size="large"
                onClick={goToSettings}
              >
                Account Settings
              </Button>
            </Space>
          </GlassCard>
          
          <GlassCard 
            title="Recent Activity" 
            elevation="medium"
          >
            <Timeline items={recentActivities} />
          </GlassCard>
        </Col>
        
        <Col xs={24} lg={8}>
          <GlassCard 
            title="System Status" 
            variant="strong"
            elevation="medium"
            style={{ marginBottom: '24px' }}
          >
            <div style={{ textAlign: 'center' }}>
              <Title level={3} style={{ color: '#eab308' }}>{accountType}</Title>
              <Text>Your account is active and in good standing</Text>
              <div style={{ marginTop: '16px' }}>
                <Button type="primary" onClick={() => navigate('/dashboard/settings')}>
                  Manage Account
                </Button>
              </div>
            </div>
          </GlassCard>
          
          <GlassCard 
            title="Quick Tips" 
            variant="subtle"
            elevation="low"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button block onClick={() => navigate('/dashboard/chat')}>
                Chat with Support
              </Button>
              <Button block>
                View Documentation
              </Button>
              <Button block>
                Community Forum
              </Button>
            </Space>
          </GlassCard>
        </Col>
      </Row>
    </div>
  );
};

export default DashboardV2;