import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthProvider';
import { useWebAuthn } from '../hooks/useWebAuthn';
import { useKratosFlow } from '../hooks/useKratosFlow';
import { useSessionCoordination } from '../hooks/useSessionCoordination';

const PasskeyAuth = ({ aalLevel = 'aal1', flowData, onSuccess, onCancel }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const {
    userEmail,
    isLoading,
    setLoading,
    biometricAvailable,
    hasRegisteredPasskey,
    error,
    setError,
    successMessage,
    setSuccessMessage,
    syncStatus,
    setSyncStatus,
    setFlowData
  } = useAuth();
  
  const { authenticateAAL1, authenticateAAL2 } = useWebAuthn();
  const { initializeFlow } = useKratosFlow();
  const { pollSyncStatus } = useSessionCoordination();
  
  const returnTo = searchParams.get('return_to') || '/dashboard';
  
  // Get appropriate button text and icon
  const getButtonContent = () => {
    if (biometricAvailable) {
      const isMac = navigator.platform.includes('Mac');
      return {
        icon: isMac ? '👆' : '🔐',
        title: isMac ? 'Touch ID' : 'Biometric Authentication',
        subtitle: 'Use your fingerprint or face recognition'
      };
    } else {
      return {
        icon: '🔑',
        title: 'Security Key',
        subtitle: 'Use your hardware security key'
      };
    }
  };
  
  const buttonContent = getButtonContent();
  
  // Handle passkey authentication
  const handleAuthenticate = async () => {
    if (!userEmail || !hasRegisteredPasskey) {
      setError('Email required and passkey must be configured for this authentication method.');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      console.log(`🔐 Starting ${aalLevel} passkey authentication for:`, userEmail);
      
      let success = false;
      
      if (aalLevel === 'aal2') {
        // For AAL2, we need a flow (should be provided from parent or initialize fresh AAL2 flow)
        let currentFlow = flowData;
        
        if (!currentFlow) {
          console.log('🔐 No flow data, initializing AAL2 flow...');
          currentFlow = await initializeFlow(true); // true for AAL2
          setFlowData(currentFlow);
        }
        
        success = await authenticateAAL2(currentFlow, userEmail, returnTo);
      } else {
        // AAL1 is no longer supported with new Kratos config
        success = await authenticateAAL1(userEmail, returnTo);
      }
      
      if (success) {
        setSuccessMessage('🔐 Authentication successful!');
        
        // Handle profile sync status for AAL2
        if (aalLevel === 'aal2') {
          setSyncStatus({ isActive: true, message: 'Finalizing authentication...' });
          await pollSyncStatus();
        }
        
        // Notify parent component
        if (onSuccess) {
          onSuccess();
        }
      }
    } catch (error) {
      console.error(`🔐 ${aalLevel} passkey authentication failed:`, error);
      
      // Enhanced error handling
      if (error.name === 'NotAllowedError') {
        setError('Authentication was cancelled or failed. Please try again.');
      } else if (error.message.includes('No credentials available')) {
        setError('No passkeys found for this account. Please use email authentication or register a passkey.');
      } else {
        setError(`Passkey authentication failed: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };
  
  // Auto-trigger authentication for seamless flow (optional)
  useEffect(() => {
    // Auto-trigger only if explicitly requested via URL parameter
    const autoTrigger = searchParams.get('auto_passkey') === 'true';
    if (autoTrigger && userEmail && hasRegisteredPasskey && !isLoading) {
      console.log('🔐 Auto-triggering passkey authentication');
      handleAuthenticate();
    }
  }, [userEmail, hasRegisteredPasskey, isLoading]);
  
  return (
    <div className="space-y-6">
      {/* Status display */}
      {userEmail && (
        <div className="text-center mb-4">
          <p className="text-gray-300 text-sm">
            Authenticating: <span className="text-blue-400">{userEmail}</span>
          </p>
          <p className="text-gray-500 text-xs mt-1">
            {aalLevel === 'aal2' ? 'High security verification required' : 'Passwordless authentication'}
          </p>
        </div>
      )}
      
      {/* Passkey authentication button */}
      {hasRegisteredPasskey ? (
        <button
          onClick={handleAuthenticate}
          disabled={isLoading || !userEmail}
          className={`w-full font-semibold py-4 px-4 rounded-lg transition duration-200 flex items-center justify-center text-lg ${
            aalLevel === 'aal2' 
              ? 'bg-amber-500 hover:bg-amber-600 disabled:bg-gray-600 text-black'
              : 'bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white'
          }`}
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current mr-3"></div>
              <div className="text-left">
                <div className="font-semibold">Authenticating...</div>
                <div className="text-sm opacity-80">Please complete on your device</div>
              </div>
            </>
          ) : (
            <>
              <span className="mr-3 text-2xl">{buttonContent.icon}</span>
              <div className="text-left">
                <div className="font-semibold">{buttonContent.title}</div>
                <div className="text-sm opacity-90">{buttonContent.subtitle}</div>
              </div>
            </>
          )}
        </button>
      ) : (
        <div className="sting-glass-subtle border border-amber-500/50 rounded-lg p-4">
          <p className="text-amber-300 text-sm text-center">
            ⚠️ No passkeys found for this account. Please set up passkey authentication first.
          </p>
          <button
            onClick={() => navigate('/enrollment')}
            className="w-full mt-3 bg-amber-600 hover:bg-amber-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Set Up Passkey
          </button>
        </div>
      )}
      
      {/* Alternative options */}
      {onCancel && (
        <div className="space-y-3">
          <div className="text-center text-gray-400 text-sm">
            <span>Having trouble with passkey?</span>
          </div>
          
          <button
            onClick={onCancel}
            className="w-full bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 px-4 rounded-lg transition-colors"
          >
            Use Different Method
          </button>
        </div>
      )}
      
      {/* Sync status display */}
      {syncStatus.isActive && (
        <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400 mr-3"></div>
            <span className="text-blue-200 text-sm">{syncStatus.message}</span>
          </div>
          {syncStatus.progress && (
            <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${syncStatus.progress}%` }}
              ></div>
            </div>
          )}
        </div>
      )}
      
      {/* Debug info in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="sting-glass-subtle border border-purple-500/50 rounded-lg p-3">
          <p className="text-purple-300 text-xs">
            Debug: AAL={aalLevel}, Email={userEmail}, HasPasskey={hasRegisteredPasskey}, BiometricAvailable={biometricAvailable}
          </p>
        </div>
      )}
    </div>
  );
};

export default PasskeyAuth;