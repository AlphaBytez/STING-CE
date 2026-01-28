// Main exports for the refactored authentication system

// Main router component
export { default as AuthFlowRouter } from './components/AuthFlowRouter';

// Individual auth components
export { default as EmailCodeAuth } from './components/EmailCodeAuth';
export { default as PasskeyAuth } from './components/PasskeyAuth';
export { default as TOTPAuth } from './components/TOTPAuth';
export { default as AAL2StepUp } from './components/AAL2StepUp';

// Context and hooks
export { AuthProvider, useAuth } from './contexts/AuthProvider';
export { useKratosFlow } from './hooks/useKratosFlow';
export { useWebAuthn } from './hooks/useWebAuthn';
export { useSessionCoordination } from './hooks/useSessionCoordination';

// Utilities
export * from './utils/webauthn';
export * from './utils/kratosHelpers';