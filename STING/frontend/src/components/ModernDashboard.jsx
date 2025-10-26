import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';
import { useKratos } from '../auth/KratosProviderRefactored';
import { useAALStatus } from '../hooks/useAALStatus';
import { usePageVisibilityInterval } from '../hooks/usePageVisibilityInterval';
import { 
  Activity, Shield, Brain, MessageSquare, Database, 
  Settings, TrendingUp, Users, FileText,
  Zap, Globe, Lock, Sparkles
} from 'lucide-react';

// Import dashboard components
import MetricCard from './dashboard/MetricCard';
import SystemHealthWidget from './dashboard/SystemHealthWidget';
import PerformanceMetrics from './dashboard/PerformanceMetrics';
import ExperienceMetric from './dashboard/ExperienceMetric';
import FeatureCard from './dashboard/FeatureCard';
import ActivityTimeline from './dashboard/ActivityTimeline';
import StorageWidget from './dashboard/StorageWidget';
import PasskeyAuthModal from './auth/PasskeyAuthModal';
import PasskeyReminder from './auth/PasskeyReminder';

const ModernDashboard = () => {
  const { identity } = useUnifiedAuth();
  const navigate = useNavigate();
  
  // Re-enabled: Using tiered authentication status checking
  const {
    isAuthenticated: aalAuthenticated,
    aalStatus,
    isAdmin: aalIsAdmin,
    needsSetup,
    getMissingMethods,
    isAALCompliant,
    canAccessDashboard
  } = useAALStatus();

  // Use Kratos session as well for consistency
  const { session } = useKratos();
  const isAuthenticated = aalAuthenticated && !!session;
  const userAAL = session?.authenticator_assurance_level || 'aal1';
  const isAdmin = aalIsAdmin || identity?.traits?.role === 'admin';
  
  // User experience state
  const [userLevel, setUserLevel] = useState(1);
  const [userExp, setUserExp] = useState(0);
  const [unlockedFeatures, setUnlockedFeatures] = useState([]);
  
  // Metrics state
  const [metrics, setMetrics] = useState({
    activeHoneyJars: 0,
    messagesProcessed: 0,
    threatsBlocked: 0,
    systemUptime: 0,
    aiInteractions: 0,
    teamMembers: 0,
    reportsGenerated: 0,
    pendingReports: 0,
  });

  const [loading, setLoading] = useState(true);
  const [showPasskeyAuth, setShowPasskeyAuth] = useState(false);

  // Fetch real metrics from API with authentication - moved outside useEffect for page visibility hook
  const fetchMetrics = async () => {
    try {
      // Import axios for authenticated requests
      const axios = (await import('axios')).default;
      const response = await axios.get('/api/dashboard/metrics', { 
        timeout: 5000,
        withCredentials: true 
      });
      
      if (response.data && response.data.status === 'success') {
        setMetrics(response.data.data);
        setLoading(false);
      } else {
        console.log('Dashboard metrics API returned non-success status, using fallback data');
        setFallbackMetrics();
      }
    } catch (error) {
      console.log('Failed to fetch authenticated dashboard metrics, trying public endpoint:', error.message);
      // Try public endpoint as fallback
      try {
        const axios = (await import('axios')).default;
        const publicResponse = await axios.get('/api/dashboard/public/metrics', { timeout: 3000 });
        if (publicResponse.data && publicResponse.data.status === 'success') {
          setMetrics(publicResponse.data.data);
          setLoading(false);
          return;
        }
      } catch (publicError) {
        console.log('Public dashboard endpoint also failed:', publicError.message);
      }
      // Final fallback to static data
      setFallbackMetrics();
    }
  };

  const setFallbackMetrics = () => {
    setMetrics({
      activeHoneyJars: 5,
      messagesProcessed: 1234,
      threatsBlocked: 89,
      systemUptime: 99.9,
      aiInteractions: 456,
      teamMembers: 12,
      reportsGenerated: 47,
      pendingReports: 3,
    });
    setLoading(false);
  };

  useEffect(() => {
    // Load user experience data
    const savedLevel = parseInt(localStorage.getItem('userLevel') || '1');
    const savedExp = parseInt(localStorage.getItem('userExp') || '0');
    const savedFeatures = JSON.parse(localStorage.getItem('unlockedFeatures') || '[]');
    
    setUserLevel(savedLevel);
    setUserExp(savedExp);
    setUnlockedFeatures(savedFeatures);
    
    fetchMetrics(); // Initial load
  }, []);

  // Use page visibility aware interval for metrics refresh - major GPU savings
  usePageVisibilityInterval(fetchMetrics, 30000, []);

  // ✅ DASHBOARD GATE: Check AAL requirements and route to Security Settings if needed
  useEffect(() => {
    if (aalStatus && isAuthenticated) {
      console.log('🔒 DASHBOARD GATE: Checking AAL requirements', {
        isAuthenticated,
        needsSetup: needsSetup,
        missingMethods: getMissingMethods(),
        isAdmin: isAdmin,
        canAccessDashboard: canAccessDashboard,
        isAALCompliant: isAALCompliant
      });

      if (needsSetup && getMissingMethods().length > 0) {
        console.log('🔒 DASHBOARD GATE: User needs 2FA/3FA setup, routing to Security Settings');
        
        // Store the intended destination
        sessionStorage.setItem('redirectAfterSecuritySetup', '/dashboard');
        
        // Route to security settings with setup message
        navigate('/dashboard/settings?tab=security', {
          state: {
            setupRequired: true,
            missingMethods: getMissingMethods(),
            isAdmin: isAdmin,
            message: isAdmin 
              ? 'Admin accounts require both TOTP and Passkey authentication. Please complete your security setup.'
              : 'Your account requires Passkey authentication. Please complete your security setup.'
          }
        });
      }
    }
  }, [aalStatus, isAuthenticated, needsSetup, getMissingMethods, isAdmin, canAccessDashboard, isAALCompliant, navigate]);

  // Experience calculation
  const getNextLevelExp = () => userLevel * 100;
  
  // Check if user is admin - admins get all features unlocked  
  // Simplified: just check the role field from Kratos identity
  const isUserAdmin = identity?.traits?.role === 'admin';
  
  // Debug admin detection (remove in production)
  if (process.env.NODE_ENV === 'development') {
    console.log('Admin detection:', {
      role: identity?.traits?.role,
      email: identity?.traits?.email,
      isUserAdmin
    });
  }
  
  // Feature definitions with progressive unlocking (disabled for admins)
  const features = [
    {
      id: 'honey-jars',
      title: 'Honey Jars',
      description: 'Manage your deceptive honeypots and trap configurations',
      icon: Database,
      locked: !isUserAdmin && userLevel < 1,
      requirement: isUserAdmin ? 'Admin Access' : 'Available from start',
      path: '/dashboard/honey-jars',
      progress: 100,
    },
    {
      id: 'bee-chat',
      title: 'Bee Chat AI',
      description: 'Interact with your AI assistant for security insights',
      icon: MessageSquare,
      locked: !isUserAdmin && userLevel < 2,
      requirement: isUserAdmin ? 'Admin Access' : 'Reach Level 2',
      path: '/dashboard/chat',
      progress: isUserAdmin || userLevel >= 2 ? 100 : (userExp / 100) * 100,
    },
    {
      id: 'bee-reports',
      title: 'Bee Reports',
      description: 'Generate comprehensive security reports and analytics',
      icon: FileText,
      locked: false,
      requirement: 'Available from start',
      path: '/dashboard/reports',
      progress: 100,
    },
    {
      id: 'hive-manager',
      title: 'Hive Manager',
      description: 'Orchestrate your security hive and manage swarm intelligence',
      icon: Globe,
      locked: !isUserAdmin && userLevel < 3,
      requirement: isUserAdmin ? 'Admin Access' : 'Reach Level 3',
      path: '/dashboard/hive-manager',
      progress: isUserAdmin || userLevel >= 3 ? 100 : userLevel === 2 ? (userExp / 200) * 100 : 0,
    },
    {
      id: 'beeacon-monitoring',
      title: 'Beeacon Monitoring',
      description: 'Real-time visibility into your STING hive with intelligent observability',
      icon: TrendingUp,
      locked: !isUserAdmin && userLevel < 4,
      requirement: isUserAdmin ? 'Admin Access' : 'Reach Level 4',
      path: '/dashboard/beeacon',
      progress: isUserAdmin || userLevel >= 4 ? 100 : userLevel === 3 ? (userExp / 300) * 100 : 0,
    },
    {
      id: 'swarm-orchestration',
      title: 'Swarm Orchestration',
      description: 'Coordinate distributed security agents and responses',
      icon: Zap,
      locked: !isUserAdmin && userLevel < 5,
      requirement: isUserAdmin ? 'Admin Access' : 'Reach Level 5',
      path: '/dashboard/swarm',
      progress: isUserAdmin || userLevel >= 5 ? 100 : userLevel === 4 ? (userExp / 400) * 100 : 0,
    },
  ];

  const handleFeatureClick = (feature) => {
    if (!feature.locked && !feature.comingSoon && feature.path) {
      // Add experience for using features
      const newExp = userExp + 10;
      const nextLevel = getNextLevelExp();
      
      if (newExp >= nextLevel) {
        const newLevel = userLevel + 1;
        setUserLevel(newLevel);
        setUserExp(newExp - nextLevel);
        localStorage.setItem('userLevel', newLevel.toString());
        localStorage.setItem('userExp', (newExp - nextLevel).toString());
        
        // Unlock new features
        const newUnlocked = features
          .filter(f => f.requirement.includes(`Level ${newLevel}`))
          .map(f => f.title);
        if (newUnlocked.length > 0) {
          setUnlockedFeatures([...unlockedFeatures, ...newUnlocked]);
          localStorage.setItem('unlockedFeatures', JSON.stringify([...unlockedFeatures, ...newUnlocked]));
        }
      } else {
        setUserExp(newExp);
        localStorage.setItem('userExp', newExp.toString());
      }
      
      navigate(feature.path);
    }
  };

  // Get next feature to unlock
  const getNextFeature = () => {
    const locked = features.filter(f => f.locked && !f.comingSoon);
    return locked.length > 0 ? locked[0].title : null;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-yellow-400 mb-2">Welcome back, {identity?.traits?.profile?.displayName || identity?.traits?.name?.first || 'Beekeeper'}!</h1>
          <p className="text-gray-400">Monitor your hive's security posture and manage your swarm</p>
        </div>

        {/* Top Metrics Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Active Honey Jars"
            value={metrics.activeHoneyJars}
            icon={Database}
            color="yellow"
            trend={12}
            trendLabel="vs last week"
            loading={loading}
          />
          <MetricCard
            title="Messages Processed"
            value={metrics.messagesProcessed.toLocaleString()}
            icon={MessageSquare}
            color="blue"
            trend={23}
            trendLabel="vs last week"
            loading={loading}
          />
          <MetricCard
            title="Threats Blocked"
            value={metrics.threatsBlocked}
            icon={Shield}
            color="red"
            trend={-15}
            trendLabel="vs last week"
            loading={loading}
          />
          <MetricCard
            title="System Uptime"
            value={metrics.systemUptime >= 99.5 ? `${metrics.systemUptime.toFixed(2)}%` : `${metrics.systemUptime.toFixed(1)}%`}
            icon={Activity}
            color="green"
            trend={0.1}
            trendLabel="30 days"
            loading={loading}
          />
        </div>

        {/* Reports Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="lg:col-span-2">
            <div className="dashboard-card report-generation-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="report-title text-lg font-semibold text-blue-400 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Report Generation
                </h3>
                <button
                  onClick={() => navigate('/dashboard/reports')}
                  className="view-all-link text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  View All →
                </button>
              </div>
              <div className="report-metrics-grid grid grid-cols-2 gap-4">
                <div className="report-metric-card bg-gray-700/50 rounded-lg p-4">
                  <p className="text-2xl font-bold text-white">{metrics.reportsGenerated}</p>
                  <p className="text-sm text-gray-400">Reports Generated</p>
                  <p className="text-xs text-green-400 mt-1">+15% this week</p>
                </div>
                <div className="report-metric-card bg-gray-700/50 rounded-lg p-4">
                  <p className="text-2xl font-bold text-yellow-400">{metrics.pendingReports}</p>
                  <p className="text-sm text-gray-400">Pending Reports</p>
                  <p className="text-xs text-blue-400 mt-1">Processing...</p>
                </div>
              </div>
              <button
                onClick={() => setShowPasskeyAuth(true)}
                className="retro-report-button w-full mt-4 px-4 py-3 rounded-lg font-semibold text-white transition-all duration-300 transform hover:scale-105 hover:shadow-xl"
                style={{
                  background: 'rgba(251, 191, 36, 0.2)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(251, 191, 36, 0.3)',
                  boxShadow: '0 4px 20px rgba(251, 191, 36, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
                }}
                onMouseEnter={(e) => {
                  const isRetro = document.documentElement.getAttribute('data-theme') === 'retro-terminal';
                  if (!isRetro) {
                    e.currentTarget.style.background = 'rgba(251, 191, 36, 0.3)';
                    e.currentTarget.style.borderColor = 'rgba(251, 191, 36, 0.5)';
                    e.currentTarget.style.boxShadow = '0 8px 30px rgba(251, 191, 36, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2)';
                  }
                }}
                onMouseLeave={(e) => {
                  const isRetro = document.documentElement.getAttribute('data-theme') === 'retro-terminal';
                  if (!isRetro) {
                    e.currentTarget.style.background = 'rgba(251, 191, 36, 0.2)';
                    e.currentTarget.style.borderColor = 'rgba(251, 191, 36, 0.3)';
                    e.currentTarget.style.boxShadow = '0 4px 20px rgba(251, 191, 36, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)';
                  }
                }}
              >
                <span className="flex items-center justify-center gap-2">
                  <FileText className="w-5 h-5" />
                  Generate New Report
                </span>
              </button>
            </div>
          </div>
          <MetricCard
            title="Report Templates"
            value={6}
            icon={FileText}
            color="purple"
            trend={0}
            trendLabel="available"
            loading={loading}
          />
          <MetricCard
            title="Export Success"
            value={98.5}
            unit="%"
            icon={Shield}
            color="green"
            trend={2.5}
            trendLabel="vs last week"
            loading={loading}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* System Health - Takes 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            <SystemHealthWidget />
            <PerformanceMetrics />
          </div>
          
          {/* Experience & Activity - Takes 1 column */}
          <div className="space-y-6">
            <ExperienceMetric
              level={userLevel}
              experience={userExp}
              nextLevelExp={getNextLevelExp()}
              unlockedFeatures={unlockedFeatures}
              nextFeature={getNextFeature()}
            />
            <StorageWidget />
            <ActivityTimeline activities={[
              {
                title: 'Welcome to STING!',
                description: 'Your security hive is now active',
                time: 'Just now',
                color: 'bg-yellow-500'
              },
              {
                title: 'Report Templates Loaded',
                description: '6 report templates are now available',
                time: '5 minutes ago',
                color: 'bg-blue-500'
              },
              {
                title: 'System Initialized',
                description: 'All services are running smoothly',
                time: '10 minutes ago',
                color: 'bg-green-500'
              }
            ]} />
          </div>
        </div>

        {/* Features Grid */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-yellow-400" />
            Available Features
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <FeatureCard
              key={feature.id}
              title={feature.title}
              description={feature.description}
              icon={feature.icon}
              locked={feature.locked}
              progress={feature.progress}
              requirement={feature.requirement}
              comingSoon={feature.comingSoon}
              enterprise={feature.enterprise}
              onClick={() => handleFeatureClick(feature)}
            />
          ))}
        </div>

        {/* Quick Actions */}
        <div className="mt-8 dashboard-card quick-actions-card p-6">
          <h3 className="quick-actions-title text-lg font-semibold text-yellow-400 mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => navigate('/dashboard/settings')}
              className="quick-action-button floating-button flex items-center gap-2 text-white"
            >
              <Settings className="w-4 h-4 text-white" />
              <span className="text-white">Settings</span>
            </button>
            <button
              onClick={() => navigate('/dashboard/teams')}
              className="quick-action-button floating-button flex items-center gap-2 text-white"
            >
              <Users className="w-4 h-4 text-white" />
              <span className="text-white">Team Management</span>
            </button>
            <button
              onClick={() => navigate('/dashboard/reports')}
              className="quick-action-button floating-button flex items-center gap-2 text-white"
            >
              <FileText className="w-4 h-4 text-white" />
              <span className="text-white">View Reports</span>
            </button>
          </div>
        </div>

        {/* Passkey Authentication Modal */}
        <PasskeyAuthModal
          visible={showPasskeyAuth}
          title="Report Generation Requires Authentication"
          onSuccess={() => {
            setShowPasskeyAuth(false);
            navigate('/dashboard/reports');
          }}
          onCancel={() => setShowPasskeyAuth(false)}
        />

        {/* Enhanced 2FA Reminder - Banner for critical passkey setup, notification for TOTP */}
        <PasskeyReminder variant="auto" />
    </div>
  );
};

export default ModernDashboard;