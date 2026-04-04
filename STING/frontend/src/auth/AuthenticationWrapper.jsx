import React, { Suspense, lazy } from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import { KratosProviderRefactored } from './KratosProviderRefactored';
import { UnifiedAuthProvider } from './UnifiedAuthProvider';
import { ProfileProvider } from '../context/ProfileContext';
import BiometricChallenge from '../components/BiometricChallenge';
import SimpleProtectedRoute from './SimpleProtectedRoute';
// Import mobile route helpers
import { 
  MobileLayoutWrapper, 
  MobileLoadingFallback,
  MobileAdminGuard,
  MobileDashboard,
  MobileChat,
  MobileBasket,
  MobileSearch,
  MobileReports,
  MobileReportDetail,
  MobileTemplates,
  MobileTemplateDetail,
  MobileHoneyJars,
  MobileHoneyJarDetail,
  MobileSettings,
  MobileProfile,
  MobileSecurity,
  MobileAdmin,
  MobileAdminPending,
  MobileAdminUsers,
} from '../routes/MobileRouteHelpers';
import MobileTest from '../components/mobile/MobileTest';
import EmergencyReset from '../components/auth/EmergencyReset';

// Import your authentication-related pages
import EnhancedRegistration from '../components/auth/EnhancedRegistration'; // Enhanced passwordless registration
import VerificationPage from '../components/auth/VerificationPage';
import ErrorPage from './ErrorPage';
import ModernEnrollment from '../components/auth/ModernEnrollment'; // Modern 3-factor enrollment
import SessionCheck from './SessionCheck';
import QuickLogout from '../components/auth/QuickLogout';
import EmailFirstLogin from '../components/auth/EmailFirstLogin';
import AuthFlowRouter from '../components/auth/refactored/components/AuthFlowRouter';
import SecurityUpgrade from '../components/auth/GracefulAAL2StepUp'; // TODO: Rename file to SecurityUpgrade.jsx
import TOTPVerify from '../components/auth/AAL2TOTPVerify'; // TODO: Rename file to TOTPVerify.jsx
import PasskeyVerify from '../components/auth/AAL2PasskeyVerify'; // TODO: Rename file to PasskeyVerify.jsx
import CredentialSetup from '../components/auth/CredentialSetup';
import PostRegistration from './PostRegistration';
import LogoutPage from '../components/auth/LogoutPage';
import ForcePasswordChange from '../components/auth/ForcePasswordChange';
// import TOTPSetup from '../components/auth/TOTPSetup'; // DEPRECATED: Using direct Kratos TOTP now
// Additional debug and auth components (archived components removed due to broken dependencies)
// import AAL2RedirectHandler from '../components/pages/AAL2RedirectHandler'; // Removed - using security-upgrade route

// Import your main application components
import MainInterface from '../components/MainInterface';
import KratosSettings from '../components/auth/KratosSettings';
import SecuritySettings from '../components/user/SecuritySettings';
import PremiumFeature from '../components/PremiumFeature';
import ChatDemoPage from '../components/chat/enhanced/ChatDemoPage';
// SimpleChatInterface removed - use BeeChat with simpleMode instead
import BeeChat from '../components/chat/BeeChat';
import PublicBotChat from '../components/pages/PublicBotChat';
import DemoLanding from '../pages/DemoLanding';
import DemoDashboard from '../pages/DemoDashboard';
import FirstRun from '../pages/FirstRun';
import MaintenancePage from '../pages/MaintenancePage';

/**
 * FirstRunRootRedirect - Checks if admin exists and redirects appropriately
 * If no admin exists, shows first-run setup page
 * If admin exists, redirects to dashboard (which will redirect to login if needed)
 */
import { useState, useEffect } from 'react';

/**
 * MaintenanceGate - Checks maintenance status and shows maintenance page if active
 * This runs before any routes are rendered to ensure maintenance mode is respected
 */
const MaintenanceGate = ({ children }) => {
  const [status, setStatus] = useState('checking');
  const [maintenanceData, setMaintenanceData] = useState(null);

  useEffect(() => {
    const checkMaintenance = async () => {
      try {
        const response = await fetch('/api/system/maintenance/status');
        const data = await response.json();

        if (data.maintenance_mode) {
          setMaintenanceData(data);
          setStatus('maintenance');
        } else {
          setStatus('operational');
        }
      } catch (err) {
        // If check fails, allow access (fail open for usability)
        console.debug('Maintenance check failed:', err);
        setStatus('operational');
      }
    };

    checkMaintenance();
    // Re-check periodically in case maintenance starts/ends
    const interval = setInterval(checkMaintenance, 30000);
    return () => clearInterval(interval);
  }, []);

  if (status === 'checking') {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
        color: '#94a3b8',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid #334155',
            borderTopColor: '#f59e0b',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px',
          }}></div>
          <p>Loading...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (status === 'maintenance') {
    return <MaintenancePage initialData={maintenanceData} />;
  }

  return children;
};

const FirstRunRootRedirect = () => {
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await fetch('/api/auth/admin-setup-status');
        const data = await response.json();

        if (data.setup_required) {
          // No admin exists, redirect to first-run setup
          setStatus('needs-setup');
        } else {
          // Admin exists, redirect to dashboard
          setStatus('ready');
        }
      } catch (err) {
        // If endpoint fails, assume setup is needed (fresh install)
        setStatus('needs-setup');
      }
    };

    checkSetup();
  }, []);

  if (status === 'checking') {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
        color: '#94a3b8',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid #334155',
            borderTopColor: '#f59e0b',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px',
          }}></div>
          <p>Checking setup status...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (status === 'needs-setup') {
    return <Navigate to="/first-run" replace />;
  }

  return <Navigate to="/dashboard" replace />;
};

// Mobile routes are now handled by MobileRoutesComponent

/**
 * AuthenticationWrapper - The main authentication wrapper component
 *
 * This component:
 * 1. Provides the KratosProvider context to the entire app
 * 2. Sets up routing with authentication protection
 * 3. Handles different account types and permissions
 */
const AuthenticationWrapper = () => {
  return (
    <MaintenanceGate>
      <KratosProviderRefactored>
        <UnifiedAuthProvider>
          <ProfileProvider>
        <Routes>
          {/* Primary Authentication Routes (Kratos Native) */}
          <Route path="/login" element={<AuthFlowRouter mode="login" />} />
          <Route path="/login-simple" element={<EmailFirstLogin />} />
          <Route path="/register" element={<EnhancedRegistration />} />
          
          {/* Security upgrade route (replaces AAL2) */}
          <Route path="/security-upgrade" element={<SecurityUpgrade />} />

          {/* Forced credential setup for new users */}
          <Route path="/credential-setup" element={<CredentialSetup />} />

          {/* Auth Flow Routes */}
          <Route path="/verification" element={<VerificationPage />} />
          <Route path="/error" element={<ErrorPage />} />
          <Route path="/change-password" element={<ForcePasswordChange />} />
          {/* DEPRECATED: /setup-totp route removed - using direct Kratos TOTP now */}
          {/* <Route path="/setup-passkey" element={<PasskeySetup />} /> - Deprecated: Use Settings > Security instead */}
          {/* <Route path="/passkey-info" element={<PasskeySetupPage />} /> - Archived: Using Kratos native WebAuthn */}
          <Route path="/post-registration" element={<PostRegistration />} />
          <Route path="/logout" element={<LogoutPage />} />
          <Route path="/session-check" element={<SessionCheck />} />
          <Route path="/quick-logout" element={<QuickLogout />} />
          <Route path="/reset-state" element={<EmergencyReset />} />
          
          {/* Debug and Testing Routes */}
          <Route path="/debug/chat" element={<ChatDemoPage />} />
          
          {/* Modern 3-Factor Enrollment for authenticated users */}
          <Route path="/enrollment" element={<ModernEnrollment />} />
          
          {/* Legacy AAL2 redirect - redirects to security-upgrade */}
          <Route path="/aal2-step-up" element={<Navigate to="/security-upgrade" replace />} />
          
          {/* Verification Routes - Standalone authentication pages */}
          <Route path="/verify-totp" element={<TOTPVerify />} />
          <Route path="/verify-passkey" element={<PasskeyVerify />} />
          {/* Legacy AAL2 verification redirects */}
          <Route path="/aal2-verify-totp" element={<Navigate to="/verify-totp" replace />} />
          <Route path="/aal2-verify-passkey" element={<Navigate to="/verify-passkey" replace />} />

          {/* Public Bot Routes - NO authentication required */}
          <Route path="/bot/:slug" element={<PublicBotChat />} />
          <Route path="/bot/:slug/embed" element={<PublicBotChat />} />

          {/* Demo Routes - Email capture authentication */}
          <Route path="/demo" element={<DemoLanding />} />
          <Route path="/demo/*" element={<DemoDashboard />} />
          
          {/* Maintenance Page - Public route for when system is in maintenance */}
          <Route path="/maintenance" element={<MaintenancePage />} />

          {/* Protected routes requiring authentication */}
          <Route 
            path="/dashboard/*" 
            element={
              <SimpleProtectedRoute>
                {/* DashboardEnrollmentGuard removed - trust Kratos AAL levels directly */}
                <MainInterface />
              </SimpleProtectedRoute>
            } 
          />
          
          <Route 
            path="/settings" 
            element={
              <SimpleProtectedRoute>
                <KratosSettings />
              </SimpleProtectedRoute>
            } 
          />
          
          {/* Direct SecuritySettings route - bypasses dashboard enrollment guard */}
          <Route 
            path="/settings/security" 
            element={
              <SimpleProtectedRoute>
                <SecuritySettings />
              </SimpleProtectedRoute>
            } 
          />
          
          {/* Premium features with account type restrictions */}
          <Route 
            path="/premium-feature" 
            element={
              <SimpleProtectedRoute requiredAccountType="premium">
                <PremiumFeature />
              </SimpleProtectedRoute>
            } 
          />
          
          {/* Example of permission-based protection */}
          <Route 
            path="/admin" 
            element={
              <SimpleProtectedRoute requiredPermissions={['admin.access']}>
                <div>Admin Panel</div>
              </SimpleProtectedRoute>
            } 
          />
          

          {/* Chat demo route - redirects to the dashboard chat */}
          <Route 
            path="/chat-demo" 
            element={<Navigate to="/dashboard/chat" replace />} 
          />

          {/* Simple Chat Interface - BeeChat with built-in simple/advanced toggle */}
          <Route
            path="/chat"
            element={
              <SimpleProtectedRoute>
                <BeeChat />
              </SimpleProtectedRoute>
            }
          />

          {/* Legacy AAL2 route - redirect to security upgrade */}
          <Route path="/auth/aal2-complete" element={<Navigate to="/security-upgrade" replace />} />

          {/* First Run - Check if admin exists, redirect to setup if not */}
          <Route path="/first-run" element={<FirstRun />} />

          {/* Root route - Check setup status and redirect appropriately */}
          <Route
            path="/"
            element={<FirstRunRootRedirect />}
          />
          
          {/* Mobile Routes - defined inline to avoid nested Routes issue */}
          <Route path="/m/test" element={<MobileTest />} />
          <Route path="/m" element={<MobileLayoutWrapper />}>
            <Route index element={<Suspense fallback={<MobileLoadingFallback />}><MobileDashboard /></Suspense>} />
            <Route path="chat" element={<Suspense fallback={<MobileLoadingFallback />}><MobileChat /></Suspense>} />
            <Route path="chat/:conversationId" element={<Suspense fallback={<MobileLoadingFallback />}><MobileChat /></Suspense>} />
            <Route path="basket" element={<Suspense fallback={<MobileLoadingFallback />}><MobileBasket /></Suspense>} />
            <Route path="search" element={<Suspense fallback={<MobileLoadingFallback />}><MobileSearch /></Suspense>} />
            <Route path="reports" element={<Suspense fallback={<MobileLoadingFallback />}><MobileReports /></Suspense>} />
            <Route path="reports/:id" element={<Suspense fallback={<MobileLoadingFallback />}><MobileReportDetail /></Suspense>} />
            <Route path="templates" element={<Suspense fallback={<MobileLoadingFallback />}><MobileTemplates /></Suspense>} />
            <Route path="templates/:id" element={<Suspense fallback={<MobileLoadingFallback />}><MobileTemplateDetail /></Suspense>} />
            <Route path="honey-jars" element={<Suspense fallback={<MobileLoadingFallback />}><MobileHoneyJars /></Suspense>} />
            <Route path="honey-jars/:id" element={<Suspense fallback={<MobileLoadingFallback />}><MobileHoneyJarDetail /></Suspense>} />
            <Route path="settings" element={<Suspense fallback={<MobileLoadingFallback />}><MobileSettings /></Suspense>} />
            <Route path="settings/profile" element={<Suspense fallback={<MobileLoadingFallback />}><MobileProfile /></Suspense>} />
            <Route path="settings/security" element={<Suspense fallback={<MobileLoadingFallback />}><MobileSecurity /></Suspense>} />
            <Route path="admin" element={<MobileAdminGuard><Suspense fallback={<MobileLoadingFallback />}><MobileAdmin /></Suspense></MobileAdminGuard>} />
            <Route path="admin/pending" element={<MobileAdminGuard><Suspense fallback={<MobileLoadingFallback />}><MobileAdminPending /></Suspense></MobileAdminGuard>} />
            <Route path="admin/users" element={<MobileAdminGuard><Suspense fallback={<MobileLoadingFallback />}><MobileAdminUsers /></Suspense></MobileAdminGuard>} />
            <Route path="*" element={<Navigate to="/m" replace />} />
          </Route>

          {/* 404 route */}
          <Route
            path="*"
            element={<Navigate to="/dashboard" replace />}
          />
        </Routes>
            
            {/* Global Biometric Challenge Modal */}
            <BiometricChallenge />
          </ProfileProvider>
        </UnifiedAuthProvider>
      </KratosProviderRefactored>
    </MaintenanceGate>
  );
};

export default AuthenticationWrapper;