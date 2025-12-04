import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from '../contexts/AuthProvider';
import EmailCodeAuth from './EmailCodeAuth';
import PasskeyAuth from './PasskeyAuth';
import TOTPAuth from './TOTPAuth';
import AAL2StepUp from './AAL2StepUp';

// Inner component that uses the auth context
const AuthFlowRouterInner = ({ mode = 'login' }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  
  const [currentFlow, setCurrentFlow] = useState('email'); // email, passkey, totp, aal2_stepup
  
  const {
    userEmail,
    setUserEmail,
    error,
    successMessage,
    setSuccessMessage,
    clearMessages,
    checkEmailPasskeys,
    initializeAuthCapabilities,
    flowData,
    setFlowData
  } = useAuth();
  
  const isAAL2 = searchParams.get('aal') === 'aal2';
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // Initialize auth capabilities and check for registration success
  useEffect(() => {
    const initialize = async () => {
      try {
        // Check for registration success message
        const locationState = location.state;
        if (locationState?.registrationSuccess) {
          setSuccessMessage(locationState.message || 'Registration successful! Sign in with your passkey.');
          if (locationState.email) {
            setUserEmail(locationState.email);
          }
          // Clear the state to prevent showing message on refresh
          navigate(location.pathname, { replace: true, state: null });
        }
        
        await initializeAuthCapabilities();
        
        // Determine initial flow
        if (isAAL2) {
          // FIXED: Don't create AAL2 flows - let Kratos handle step-up naturally
          console.log('🔐 AAL2 detected in URL - showing AAL2 step-up component instead of creating new flow');
          setCurrentFlow('aal2_stepup');
          return;
        }
        
        // Default to email flow
        setCurrentFlow('email');
      } catch (error) {
        console.error('🔐 Initialization error:', error);
      }
    };
    
    initialize();
  }, [isAAL2, location.state, navigate, setUserEmail, initializeAuthCapabilities]);
  
  // Handle flow transitions
  const handleFlowChange = (newFlow, data = {}) => {
    console.log('🔐 Flow changing from', currentFlow, 'to', newFlow, data);
    
    clearMessages();
    setCurrentFlow(newFlow);
    
    // Handle flow-specific data
    if (data.email) {
      setUserEmail(data.email);
    }
  };
  
  // Handle switching to passkey authentication
  const handleSwitchToPasskey = () => {
    if (!userEmail) {
      console.warn('🔐 Cannot switch to passkey without email');
      return;
    }
    
    // Check passkeys first
    checkEmailPasskeys(userEmail).then(hasPasskeys => {
      if (hasPasskeys) {
        handleFlowChange('passkey');
      } else {
        console.log('🔐 No passkeys found for email:', userEmail);
      }
    });
  };
  
  // Handle method selection from AAL2 step-up
  const handleAAL2MethodSelection = (method) => {
    console.log('🔐 AAL2 method selected:', method);
    
    if (method === 'passkey') {
      handleFlowChange('passkey');
    } else if (method === 'totp') {
      handleFlowChange('totp');
    }
  };
  
  // Handle successful authentication
  const handleAuthSuccess = (result) => {
    console.log('🔐 Auth success:', result);
    
    if (result === 'aal2_required') {
      // Email auth succeeded but AAL2 is required
      handleFlowChange('aal2_stepup');
    } else {
      // Authentication fully completed
      setTimeout(() => {
        navigate(returnTo, { replace: true });
      }, 1000);
    }
  };
  
  // Handle cancellation/back navigation
  const handleCancel = () => {
    if (currentFlow === 'aal2_stepup' && !isAAL2) {
      // From AAL2 step-up back to main options
      setCurrentFlow('email');
    } else if (currentFlow === 'passkey' || currentFlow === 'totp') {
      // Back to step-up selection or email
      setCurrentFlow(isAAL2 ? 'aal2_stepup' : 'email');
    } else {
      // Default cancel behavior
      navigate('/dashboard');
    }
  };
  
  // Render current flow component
  const renderCurrentFlow = () => {
    switch (currentFlow) {
      case 'email':
        return (
          <EmailCodeAuth
            onSwitchToPasskey={handleSwitchToPasskey}
            onSuccess={handleAuthSuccess}
          />
        );
      
      case 'passkey':
        return (
          <PasskeyAuth
            aalLevel={isAAL2 ? 'aal2' : 'aal1'}
            flowData={flowData}
            onSuccess={handleAuthSuccess}
            onCancel={handleCancel}
          />
        );
      
      case 'totp':
        return (
          <TOTPAuth
            onSuccess={handleAuthSuccess}
            onCancel={handleCancel}
          />
        );
      
      case 'aal2_stepup':
        return (
          <AAL2StepUp
            onMethodSelected={handleAAL2MethodSelection}
            onCancel={handleCancel}
          />
        );
      
      default:
        return (
          <div className="text-center text-gray-400">
            <p>Unknown authentication flow: {currentFlow}</p>
            <button
              onClick={() => setCurrentFlow('email')}
              className="mt-2 text-blue-400 hover:text-blue-300 underline"
            >
              Return to email login
            </button>
          </div>
        );
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="Hive" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isAAL2 ? 'Secure Access Required' : 'Welcome to Hive'}
          </h1>
          <p className="text-gray-300">
            {isAAL2 
              ? 'Additional verification needed for sensitive data'
              : 'Sign in to continue'
            }
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="sting-glass-subtle border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6">
            {successMessage}
          </div>
        )}

        {/* Current Flow Component */}
        {renderCurrentFlow()}

        {/* Registration Link - only show for non-AAL2 flows */}
        {!isAAL2 && currentFlow === 'email' && (
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Don't have an account?{' '}
              <button
                onClick={() => navigate('/register')}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign up here
              </button>
            </p>
          </div>
        )}

        {/* Flow indicator in development */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs text-center">
              🔧 Dev: Current flow = {currentFlow} | AAL2 = {isAAL2 ? 'true' : 'false'}
              <br />
              📧 Check{' '}
              <a href="http://localhost:8025" target="_blank" rel="noopener noreferrer" className="underline">
                Mailpit
              </a>{' '}
              for emails
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// Main component with AuthProvider wrapper
const AuthFlowRouter = ({ mode = 'login' }) => {
  return (
    <AuthProvider>
      <AuthFlowRouterInner mode={mode} />
    </AuthProvider>
  );
};

export default AuthFlowRouter;