import React from 'react';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import { KratosProviderRefactored } from './KratosProviderRefactored';
import { UnifiedAuthProvider } from './UnifiedAuthProvider';
import { ProfileProvider } from '../context/ProfileContext';
import BiometricChallenge from '../components/BiometricChallenge';
import SimpleProtectedRoute from './SimpleProtectedRoute';
// import DashboardEnrollmentGuard from './DashboardEnrollmentGuard'; // ARCHIVED - caused login loops

// Import your authentication-related pages
import EnhancedRegistration from '../components/auth/EnhancedRegistration'; // Enhanced passwordless registration
import VerificationPage from '../components/auth/VerificationPage';
import ErrorPage from './ErrorPage';
import DebugPage from './DebugPage';
import ModernEnrollment from '../components/auth/ModernEnrollment'; // Modern 3-factor enrollment
import SessionCheck from './SessionCheck';
import QuickLogout from '../components/auth/QuickLogout';
import EmailFirstLogin from '../components/auth/EmailFirstLogin';
import AuthFlowRouter from '../components/auth/refactored/components/AuthFlowRouter';
import SecurityUpgrade from '../components/auth/GracefulAAL2StepUp'; // TODO: Rename file to SecurityUpgrade.jsx
import TOTPVerify from '../components/auth/AAL2TOTPVerify'; // TODO: Rename file to TOTPVerify.jsx
import PasskeyVerify from '../components/auth/AAL2PasskeyVerify'; // TODO: Rename file to PasskeyVerify.jsx
import PostRegistration from './PostRegistration';
import LogoutPage from '../components/auth/LogoutPage';
import PasskeyDebugCheck from '../components/auth/PasskeyDebugCheck';
import ForcePasswordChange from '../components/auth/ForcePasswordChange';
// import TOTPSetup from '../components/auth/TOTPSetup'; // DEPRECATED: Using direct Kratos TOTP now
// Additional debug and auth components (archived components removed due to broken dependencies)
// import AAL2RedirectHandler from '../components/pages/AAL2RedirectHandler'; // Removed - using security-upgrade route
import ColonyLoadingScreen from '../components/common/ColonyLoadingScreen';

// Import your main application components
import MainInterface from '../components/MainInterface';
import KratosSettings from '../components/auth/KratosSettings';
import SecuritySettings from '../components/user/SecuritySettings';
import FeatureA from '../components/FeatureA';
import FeatureB from '../components/FeatureB';
import PremiumFeature from '../components/PremiumFeature';
import EnterpriseFeature from '../components/EnterpriseFeature';
import ChatDemoPage from '../components/chat/enhanced/ChatDemoPage';
// SimpleChatInterface removed - use BeeChat with simpleMode instead
import BeeChat from '../components/chat/BeeChat';
import PublicBotChat from '../components/pages/PublicBotChat';

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
    <KratosProviderRefactored>
      <UnifiedAuthProvider>
        <ProfileProvider>
          <BrowserRouter>
        <Routes>
          {/* Primary Authentication Routes (Kratos Native) */}
          <Route path="/login" element={<AuthFlowRouter mode="login" />} />
          <Route path="/login-simple" element={<EmailFirstLogin />} />
          <Route path="/register" element={<EnhancedRegistration />} />
          
          {/* Security upgrade route (replaces AAL2) */}
          <Route path="/security-upgrade" element={<SecurityUpgrade />} />
          
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
          
          {/* Debug and Testing Routes */}
          <Route path="/debug/auth" element={<DebugPage />} />
          {/* <Route path="/debug/passkey" element={<PasskeyTestPage />} /> */}
          <Route path="/debug/check-passkeys" element={<PasskeyDebugCheck />} />
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
          
          {/* Basic features available to all account types */}
          <Route 
            path="/feature-a" 
            element={
              <SimpleProtectedRoute>
                <FeatureA />
              </SimpleProtectedRoute>
            } 
          />
          
          <Route 
            path="/feature-b" 
            element={
              <SimpleProtectedRoute>
                <FeatureB />
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
          
          <Route 
            path="/enterprise-feature" 
            element={
              <SimpleProtectedRoute requiredAccountType="enterprise">
                <EnterpriseFeature />
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

          {/* Redirect root to dashboard (will redirect to login if not authenticated) */}
          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />
          
          {/* 404 route */}
          <Route 
            path="*" 
            element={<Navigate to="/dashboard" replace />} 
          />
        </Routes>
            </BrowserRouter>
            
            {/* Global Biometric Challenge Modal */}
            <BiometricChallenge />
          </ProfileProvider>
      </UnifiedAuthProvider>
    </KratosProviderRefactored>
  );
};

export default AuthenticationWrapper;