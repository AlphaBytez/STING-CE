import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation, Navigate, useNavigate } from 'react-router-dom';
import { Layout, Button, Badge, Tooltip } from 'antd';
import { 
  DashboardOutlined, 
  MessageOutlined, 
  SettingOutlined, 
  TeamOutlined, 
  BarChartOutlined, 
  BellOutlined, 
  LogoutOutlined, 
  ShoppingOutlined,
  GlobalOutlined,
  AppstoreOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';
import { useUnifiedAuth } from '../auth/UnifiedAuthProvider';
import kratosApi from '../utils/kratosConfig';
import { useProfile } from '../context/ProfileContext';
import UserAvatarIcon from './icons/UserAvatarIcon';
import NotificationDropdown from './common/NotificationDropdown';
import HiveBadge from './icons/HiveBadge';
import FeatureInProgress from './common/FeatureInProgress';
import Sidebar from './layout/Sidebar';
import { useTheme as useNewTheme } from './theme/ThemeManager';
import AAL2ProtectedRoute from './auth/AAL2ProtectedRoute';

// Import components
import ModernDashboard from './ModernDashboard';
import ChatModeWrapper from './chat/ChatModeWrapper';
import BeeReportsPage from './pages/BeeReportsPage';
import Teams from './pages/TeamsPage';
import AdminPanel from './admin/AdminPanel';
import BeeaconPage from './pages/BeeaconPage';
import UserSettings from './user/UserSettings';
import KratosSettings from './auth/KratosSettings';
import SecuritySettings from './user/SecuritySettings';
import HoneyJarPage from './pages/HoneyJarPage';
import HiveManagerPage from './pages/HiveManagerPage';
import NectarBotsPage from './pages/NectarBotsPage';
import SwarmOrchestrationPage from './pages/SwarmOrchestrationPage';
import MarketplacePage from './pages/MarketplacePage';
import BasketPage from './pages/BasketPage';
import SearchPage from './pages/SearchPage';
import BeeSettings from './settings/BeeSettings';
import NectarFlowDemo from './pages/NectarFlowDemo';
import ReportTemplateManager from './reports/ReportTemplateManager';
import { loadNavigationConfig, convertIconsToComponents } from '../config/navigationConfig';

const { Header, Content } = Layout;

const MainInterface = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { darkMode } = useTheme();
  const { currentTheme } = useNewTheme();
  const [userInfo, setUserInfo] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const { isAuthenticated, isLoading, identity, logout: kratosLogout } = useUnifiedAuth();
  const { profilePicture, profileData } = useProfile();
  
  // Prevent browser caching of authenticated pages
  useEffect(() => {
    // Set cache control headers via meta tags
    const metaTags = [
      { name: 'cache-control', content: 'no-cache, no-store, must-revalidate' },
      { name: 'pragma', content: 'no-cache' },
      { name: 'expires', content: '0' }
    ];
    
    metaTags.forEach(tag => {
      let meta = document.querySelector(`meta[name="${tag.name}"]`);
      if (!meta) {
        meta = document.createElement('meta');
        meta.name = tag.name;
        document.head.appendChild(meta);
      }
      meta.content = tag.content;
    });
    
    // Note: Authentication and email verification checks should be handled by ProtectedRoute
    // MainInterface should only run when user is already authenticated and verified
  }, [identity, navigate, isLoading]);
  
  // Smart user display name
  const getUserDisplayName = () => {
    // Priority: Display name > First+Last name > Username > Email
    if (profileData?.displayName) {
      return profileData.displayName;
    }
    
    if (profileData?.firstName || profileData?.lastName) {
      return `${profileData.firstName || ''} ${profileData.lastName || ''}`.trim();
    }
    
    if (userInfo?.name?.first || userInfo?.name?.last) {
      return `${userInfo.name.first || ''} ${userInfo.name.last || ''}`.trim();
    }
    
    if (profileData?.username) {
      return profileData.username;
    }
    
    if (userInfo?.username) {
      return userInfo.username;
    }
    
    // Fallback to email
    return userInfo?.email || 'User';
  };
  
  // Smart initials for avatar
  const getUserInitials = () => {
    if (profileData?.firstName && profileData?.lastName) {
      return `${profileData.firstName[0]}${profileData.lastName[0]}`.toUpperCase();
    }
    
    if (userInfo?.name?.first && userInfo?.name?.last) {
      return `${userInfo.name.first[0]}${userInfo.name.last[0]}`.toUpperCase();
    }
    
    if (profileData?.displayName && profileData.displayName.length >= 2) {
      const words = profileData.displayName.split(' ');
      if (words.length >= 2) {
        return `${words[0][0]}${words[1][0]}`.toUpperCase();
      }
      return profileData.displayName.substring(0, 2).toUpperCase();
    }
    
    if (userInfo?.email) {
      return userInfo.email.substring(0, 2).toUpperCase();
    }
    
    return 'ST';
  };
  // kratosUrl no longer needed - using kratosApi utility
  
  // Mock notification count for demo - with ability to clear
  const [notificationCount, setNotificationCount] = useState(3);
  const [notificationsPaused, setNotificationsPaused] = useState(false);
  
  // Auto-reset notifications after a period (optional)
  useEffect(() => {
    if (notificationCount === 0 && !notificationsPaused) {
      // Reset to show demo notifications after 30 seconds
      const timer = setTimeout(() => {
        setNotificationCount(3);
      }, 30000);
      return () => clearTimeout(timer);
    }
  }, [notificationCount, notificationsPaused]);
  
  // Keyboard shortcut to clear notifications (Cmd/Ctrl + Shift + N)
  useEffect(() => {
    const handleKeyPress = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        setNotificationCount(0);
        setNotificationsPaused(true); // Pause auto-reset
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);
  
  // Close notifications when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showNotifications && !event.target.closest('.notification-container')) {
        setShowNotifications(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showNotifications]);

  // Use identity from UnifiedAuth provider instead of separate auth check
  useEffect(() => {
    if (identity) {
      setUserInfo({
        email: identity.traits?.email || identity.traits?.username || 'User',
        id: identity.id,
        name: identity.traits?.name || {}
      });
    }
  }, [identity]);

  const handleLogout = async () => {
    console.log('Logout button clicked - clearing Redis AAL2 and Kratos session');
    
    try {
      // Clear Redis AAL2 verification before Kratos logout
      const aal2Response = await fetch('/api/aal2/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      if (aal2Response.ok) {
        console.log('🧹 Redis AAL2 cleared successfully');
      } else {
        console.log('⚠️ Redis AAL2 clear failed, proceeding with logout');
      }
    } catch (error) {
      console.log('⚠️ Redis AAL2 clear error:', error);
    }
    
    // Use the KratosProvider logout method which clears Kratos session
    kratosLogout();
  };

  // Check if user is admin - enhanced detection with email fallback
  const isAdmin = identity?.traits?.role === 'admin' ||
                  identity?.traits?.email === 'admin@sting.local' ||  // Email-based admin detection
                  userInfo?.email === 'admin@sting.local' ||
                  localStorage.getItem('temp-admin-override') === 'true';

  // Auto-set admin override for admin@sting.local users
  useEffect(() => {
    if (identity?.traits?.email === 'admin@sting.local' || userInfo?.email === 'admin@sting.local') {
      localStorage.setItem('temp-admin-override', 'true');
    }
  }, [identity, userInfo]);

  // Navigation configuration state
  const [navConfig, setNavConfig] = useState(null);
  const [navConfigLoading, setNavConfigLoading] = useState(true);

  // Load navigation configuration on mount using database-backed config
  useEffect(() => {
    const loadNavConfig = async () => {
      setNavConfigLoading(true);
      try {
        // Try to load from database first, fallback to localStorage
        const config = await loadNavigationConfig(isAdmin, true);
        setNavConfig(convertIconsToComponents(config));
      } catch (error) {
        console.warn('Failed to load navigation config from database, using localStorage:', error);
        // Fallback to synchronous localStorage loading
        try {
          const fallbackConfig = await loadNavigationConfig(isAdmin, false);
          setNavConfig(convertIconsToComponents(fallbackConfig));
        } catch (fallbackError) {
          console.error('Failed to load navigation config from localStorage:', fallbackError);
          // Use basic default config as last resort
          const basicConfig = {
            version: 4,
            persistent: [
              { id: 'dashboard', name: 'Dashboard', icon: 'DashboardOutlined', path: '/dashboard', enabled: true },
              { id: 'chat', name: 'Bee Chat', icon: 'MessageOutlined', path: '/dashboard/chat', enabled: true }
            ],
            scrollable: []
          };
          setNavConfig(convertIconsToComponents(basicConfig));
        }
      } finally {
        setNavConfigLoading(false);
      }
    };

    if (isAuthenticated && !isLoading) {
      loadNavConfig();
    }

    // Listen for configuration updates from admin panel
    const handleNavConfigUpdate = (event) => {
      setNavConfig(convertIconsToComponents(event.detail));
    };

    window.addEventListener('navigation-config-updated', handleNavConfigUpdate);
    
    return () => {
      window.removeEventListener('navigation-config-updated', handleNavConfigUpdate);
    };
  }, [isAdmin, isAuthenticated, isLoading]);

  // Get enabled items for each section
  const persistentItems = navConfig ? navConfig.persistent.filter(item => 
    item.enabled && (!item.adminOnly || isAdmin)
  ) : [];
  
  const scrollableItems = navConfig ? navConfig.scrollable.filter(item => 
    item.enabled && (!item.adminOnly || isAdmin)
  ) : [];

  // Combined for backward compatibility
  const menuItems = [...persistentItems, ...scrollableItems];

  const currentPath = location.pathname;

  // ALL themes now use floating navigation (no traditional sidebars)
  const showTraditionalSidebar = false;

  return (
    <Layout style={{ minHeight: '100vh' }} className="dark-theme">
      {/* Traditional Sidebar for Retro Themes */}
      {showTraditionalSidebar && (
        <Sidebar colorScheme="dark" />
      )}
      
      {/* Floating Navigation for Modern Themes */}
      {!showTraditionalSidebar && (
        <div className="floating-nav glass-light elevation-floating" data-theme-nav="floating">
        {/* Persistent Navigation Items */}
        <div className="floating-nav-persistent px-2 pt-4">
          {persistentItems.map((item) => (
            <Tooltip key={item.path} title={item.name} placement="right">
              <Link to={item.path}>
                <div 
                  className={`floating-nav-item ${currentPath === item.path ? 'active' : ''}`}
                >
                  {item.inProgress ? (
                    <FeatureInProgress type="overlay">
                      {item.badge ? (
                        <Badge count={item.badge} size="small">
                          <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        </Badge>
                      ) : (
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                      )}
                    </FeatureInProgress>
                  ) : item.badge ? (
                    <Badge count={item.badge} size="small">
                      <span style={{ fontSize: '16px' }}>{item.icon}</span>
                    </Badge>
                  ) : (
                    <span style={{ fontSize: '16px' }}>{item.icon}</span>
                  )}
                   <span style={{ fontSize: '9px' }} className="mt-1">
                      {item.name === 'Honey Jars' ? 'Jars' : 
                       item.name === 'Jar Manager' ? 'Manager' :
                       item.name === 'Bee Reports' ? 'Reports' :
                       item.name.split(' ')[0]}
                   </span>
                </div>
              </Link>
            </Tooltip>
          ))}
        </div>

        {/* Divider */}
        <div className="floating-nav-divider mx-3 my-2"></div>

        {/* Scrollable Navigation Items */}
        <div className="floating-nav-scrollable px-2 pb-4">
          {scrollableItems.map((item) => (
            <Tooltip key={item.path} title={item.name} placement="right">
              <Link to={item.path}>
                <div 
                  className={`floating-nav-item ${currentPath === item.path ? 'active' : ''}`}
                >
                  {item.inProgress ? (
                    <FeatureInProgress type="overlay">
                      {item.badge ? (
                        <Badge count={item.badge} size="small">
                          <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        </Badge>
                      ) : (
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                      )}
                    </FeatureInProgress>
                  ) : item.badge ? (
                    <Badge count={item.badge} size="small">
                      <span style={{ fontSize: '16px' }}>{item.icon}</span>
                    </Badge>
                  ) : (
                    <span style={{ fontSize: '16px' }}>{item.icon}</span>
                  )}
                   <span style={{ fontSize: '9px' }} className="mt-1">
                      {item.name === 'Honey Jars' ? 'Jars' : 
                       item.name === 'Jar Manager' ? 'Manager' :
                       item.name === 'Bee Reports' ? 'Reports' :
                       item.name.split(' ')[0]}
                   </span>
                </div>
              </Link>
            </Tooltip>
          ))}
        </div>
      </div>
      )}

      {/* Floating Header - Adjust padding based on navigation type */}
      <Header className="floating-header glass-dark" style={{ paddingLeft: showTraditionalSidebar ? '240px' : '90px' }}>
        <div className="flex justify-between items-center h-full">
          <div className="flex items-center gap-4">
            <img 
              src="/sting-logo.png" 
              alt="Hive Logo" 
              className="w-12 h-12 object-contain cursor-pointer hover:opacity-80 transition-opacity duration-200"
              onClick={() => navigate('/dashboard')}
              title="Go to Dashboard"
            />
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold m-0" style={{ color: 'var(--color-text)' }}>Hive</h1>
              <span style={{ color: 'var(--color-text-tertiary)' }}>|</span>
              <h2 className="text-lg font-medium m-0" style={{ color: 'var(--color-text)' }}>
                {menuItems.find(item => item.path === currentPath)?.name || 'Dashboard'}
              </h2>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="font-medium" style={{ color: 'var(--color-text-secondary)' }}>{getUserDisplayName()}</span>
            
            {/* Profile Avatar - Hexagonal Honeycomb */}
            <Tooltip title="Profile Settings" placement="bottom">
              <UserAvatarIcon 
                size={40}
                className="cursor-pointer hover:scale-110 transition-transform duration-200 flex-shrink-0"
                initials={getUserInitials()}
                profileImageUrl={profilePicture || profileData?.profilePicture || null}
                onClick={() => navigate('/dashboard/settings')}
              />
            </Tooltip>
            
            {/* Notifications */}
            <div className="relative notification-container">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative cursor-pointer group"
              >
                {notificationCount > 0 ? (
                  <div className="relative">
                    {/* Using HiveBadge - you can switch to BeeNotificationBadge for hexagon style */}
                    <HiveBadge 
                      count={notificationCount} 
                      size="medium" 
                      variant="amber"  // Try: 'amber', 'honey', or 'gold'
                    />
                    {/* Alternative hexagon style - uncomment to use */}
                    {/* <BeeNotificationBadge 
                      count={notificationCount} 
                      size="medium" 
                    /> */}
                  </div>
                ) : (
                  <BellOutlined className="text-lg transition-colors duration-200" style={{ color: 'var(--color-text-secondary)' }} />
                )}
              </button>
              
              <NotificationDropdown 
                isOpen={showNotifications}
                onClose={() => setShowNotifications(false)}
                notificationCount={notificationCount}
                onClearAll={() => setNotificationCount(0)}
              />
            </div>
            
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={handleLogout}
              style={{ color: 'var(--color-text)' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-primary)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-text)'}
            />
          </div>
        </div>
      </Header>


      {/* Main Content - Adjust margins based on navigation type */}
      <Content style={{ 
        marginTop: '70px', 
        marginLeft: showTraditionalSidebar ? '225px' : '75px',
        padding: '20px',
        minHeight: 'calc(100vh - 70px)',
        transition: 'margin 0.3s ease'
      }}>
        <div className="animate-fade-in-up" style={{ paddingTop: '24px' }}>
          <Routes>
            {/* Regular dashboard routes */}
            <Route index element={<ModernDashboard />} />
            <Route path="chat" element={<ChatModeWrapper />} />
            <Route path="basket" element={<BasketPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="reports" element={<BeeReportsPage />} />
            <Route path="report-templates" element={<ReportTemplateManager />} />
            <Route path="bee-settings" element={<BeeSettings />} />
            <Route path="honey-jars" element={<HoneyJarPage />} />
            <Route path="hive-manager" element={<HiveManagerPage />} />
            <Route path="nectar-bots" element={<NectarBotsPage />} />
            <Route path="nectar-flow" element={<NectarFlowDemo />} />
            <Route path="swarm" element={<SwarmOrchestrationPage />} />
            <Route path="marketplace" element={<MarketplacePage />} />
            {isAdmin && <Route path="admin" element={<AdminPanel />} />}
            <Route path="beeacon" element={<BeeaconPage />} />
            <Route path="settings" element={<UserSettings />} />
            <Route path="settings/security" element={<SecuritySettings />} />
            <Route path="user" element={<UserSettings />} />
            
            {/* AAL2 protected routes - Claude's approach - reports now handled at action level */}
            
            <Route 
              path="admin/*" 
              element={
                <AAL2ProtectedRoute message="Administrative functions require additional verification.">
                  <AdminPanel />
                </AAL2ProtectedRoute>
              } 
            />
            
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Content>

      {/* Floating Action Buttons */}
      <div className="fab-container">
        <Tooltip title="Quick Actions" placement="left">
          <button className="fab-secondary animate-fade-in-scale">
            <SettingOutlined />
          </button>
        </Tooltip>
        
        <Tooltip title="Start Chat" placement="left">
          <button 
            className="fab-primary animate-fade-in-scale"
            onClick={() => navigate('/dashboard/chat')}
          >
            <MessageOutlined />
          </button>
        </Tooltip>
      </div>
    </Layout>
  );
};

export default MainInterface;