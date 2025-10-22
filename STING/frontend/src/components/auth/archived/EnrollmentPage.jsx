import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Smartphone, Key, CheckCircle, AlertCircle, Mail, Lock, ArrowRight, ArrowLeft } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useAALStatus } from '../../hooks/useAALStatus';
import TOTPManager from '../settings/TOTPManager';
import PasskeyManagerDirect from '../settings/PasskeyManagerDirect';
import axios from 'axios';

/**
 * EnrollmentPage - Standalone page for first-time AAL2 security setup
 * Accessible to users who have completed AAL1 (email verification) but need AAL2 setup
 */
const EnrollmentPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { identity, isAuthenticated } = useKratos();
  const {
    aalStatus,
    getMissingMethods,
    isAdmin,
    fetchAALStatus,
    canAccessDashboard
  } = useAALStatus();

  const [setupComplete, setSetupComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState(new Set());

  // 🚀 PRE-AUTH: Check if this is pre-auth enrollment from login page
  const preAuthData = location.state;
  const isPreAuth = preAuthData?.preAuth === true;
  
  console.log('🔍 EnrollmentPage mode:', isPreAuth ? 'PRE-AUTH' : 'AUTHENTICATED', preAuthData);

  // Helper function to check admin status that works in both modes
  const isUserAdmin = () => {
    return isPreAuth ? (userRole === 'admin') : isAdmin();
  };

  // Get missing methods and user info (use pre-auth data when available)
  let missingMethods, userRole, userEmail;
  
  if (isPreAuth) {
    // Pre-auth mode: Use data from login page navigation state
    missingMethods = preAuthData.missingMethods || [];
    userRole = preAuthData.isAdmin ? 'admin' : 'user';
    userEmail = preAuthData.email || 'Unknown';
    console.log('🔍 PRE-AUTH: Using navigation state data:', { missingMethods, userRole, userEmail });
  } else {
    // Authenticated mode: Use AAL status from hooks
    missingMethods = getMissingMethods();
    userRole = aalStatus?.role || 'user';
    userEmail = aalStatus?.email || identity?.traits?.email || 'Unknown';
    console.log('🔍 AUTHENTICATED: Using AAL status data:', { missingMethods, userRole, userEmail });
  }

  // Determine steps based on missing methods - TOTP FIRST, then Passkey
  const steps = [
    {
      id: 1,
      method: 'totp',
      title: 'Configure Authenticator App',
      subtitle: 'Time-based verification codes',
      icon: Smartphone,
      color: 'purple',
      required: missingMethods.includes('totp')
    },
    {
      id: 2,
      method: 'webauthn',
      title: 'Set up Passkey',
      subtitle: 'Secure device-based authentication',
      icon: Key,
      color: 'blue',
      required: missingMethods.includes('webauthn')
    }
  ].filter(step => step.required);

  // Initialize current step and completed steps based on missing methods
  useEffect(() => {
    if (aalStatus && missingMethods.length > 0) {
      // Mark already completed steps
      const completed = new Set();
      steps.forEach(step => {
        if (!missingMethods.includes(step.method)) {
          completed.add(step.id);
        }
      });
      setCompletedSteps(completed);
      
      // Set current step to first incomplete step
      const firstIncompleteStep = steps.find(step => missingMethods.includes(step.method));
      if (firstIncompleteStep) {
        setCurrentStep(firstIncompleteStep.id);
      }
    }
  }, [aalStatus, missingMethods.join(',')]); // Use join to detect array changes

  useEffect(() => {
    const checkStatus = async () => {
      if (isPreAuth) {
        // 🚀 PRE-AUTH: Skip authentication check, user hasn't logged in yet
        console.log('🔍 PRE-AUTH: Bypassing authentication requirement for pre-auth enrollment');
        
        if (!preAuthData?.email || !preAuthData?.missingMethods?.length) {
          console.error('🔍 PRE-AUTH: Invalid pre-auth data, redirecting to login');
          navigate('/login');
          return;
        }
        
        setIsLoading(false);
        return;
      }

      // Standard authenticated enrollment flow
      if (!isAuthenticated) {
        console.log('🔍 AUTHENTICATED: User not authenticated, redirecting to login');
        navigate('/login');
        return;
      }

      if (aalStatus) {
        const missing = getMissingMethods();
        console.log('🔍 AUTHENTICATED: Enrollment page status check:', {
          canAccessDashboard: canAccessDashboard(),
          missingMethods: missing,
          aalValidation: aalStatus?.validation,
          userRole: aalStatus?.role,
          email: aalStatus?.email
        });
        
        if (canAccessDashboard() || missing.length === 0) {
          console.log('✅ AUTHENTICATED: User is AAL compliant, redirecting to dashboard...');
          window.location.href = '/dashboard';
          return;
        }
      }

      setIsLoading(false);
    };

    // For authenticated mode, wait for aalStatus. For pre-auth mode, check immediately
    if (isPreAuth || aalStatus !== null) {
      checkStatus();
    }
  }, [isPreAuth, isAuthenticated, aalStatus, canAccessDashboard, navigate, preAuthData]);

  // Handle completion of individual setup steps
  const handleSetupComplete = async (method) => {
    console.log(`🔒 ${method} setup completed (${isPreAuth ? 'PRE-AUTH' : 'AUTHENTICATED'} mode)`);
    
    // Mark step as completed locally
    const stepId = steps.find(s => s.method === method)?.id;
    if (stepId) {
      setCompletedSteps(prev => new Set([...prev, stepId]));
    }
    
    // 🚀 PRE-AUTH: Handle completion differently for pre-auth users
    if (isPreAuth) {
      console.log('🔒 PRE-AUTH: Method setup completed, checking if all steps done');
      
      // Update local missing methods list
      const updatedMissing = missingMethods.filter(m => m !== method);
      
      // Check if all required steps are completed
      const allStepsCompleted = steps.every(step => 
        completedSteps.has(step.id) || step.method === method
      );
      
      if (allStepsCompleted || updatedMissing.length === 0) {
        console.log('🎉 PRE-AUTH: All security setup completed! Routing to login...');
        setSetupComplete(true);
        
        // Store success message for login page
        sessionStorage.setItem('enrollment_success', 'true');
        sessionStorage.setItem('enrollment_message', `Security setup complete! Please sign in with your email and new ${method === 'totp' ? 'authenticator app' : 'passkey'}.`);
        
        // Route back to login for authentication
        setTimeout(() => {
          window.location.href = '/login?setup_complete=true';
        }, 1500);
      } else {
        // Move to next step if there are more steps
        const nextStepMethod = updatedMissing[0];
        const nextStep = steps.find(s => s.method === nextStepMethod);
        if (nextStep) {
          setCurrentStep(nextStep.id);
        }
      }
      return; // Exit early for pre-auth mode
    }
    
    // AUTHENTICATED MODE: Force multiple refreshes to ensure status updates
    console.log('🔒 AUTHENTICATED: Refreshing AAL status...');
    await fetchAALStatus();
    
    // Wait and check again with longer delay for Kratos to update
    setTimeout(async () => {
      console.log('Second AAL status refresh...');
      await fetchAALStatus();
      
      // Force refresh the Kratos session to get updated credentials
      try {
        const response = await axios.post('/api/auth/refresh-session', {}, {
          withCredentials: true
        });
        console.log('Session refresh response:', response.data);
        
        // Check if we can now access dashboard
        if (response.data?.can_access_dashboard) {
          console.log('✅ Backend confirms dashboard access, navigating...');
          window.location.href = '/dashboard';
          return;
        }
      } catch (error) {
        console.error('Failed to refresh session:', error);
      }
      
      // Third refresh after session update
      await fetchAALStatus();
      
      // Get the latest missing methods
      const latestMissing = getMissingMethods();
      console.log('Latest missing methods:', latestMissing);
      console.log('Current AAL status:', aalStatus);
      
      // Check if all required steps are completed locally
      const allStepsCompleted = steps.every(step => 
        completedSteps.has(step.id) || step.method === method
      );
      
      // If no missing methods OR all steps completed locally, route to login
      if (latestMissing.length === 0 || allStepsCompleted) {
        console.log('🎉 Security setup completed! Routing to login for AAL2 authentication...');
        setSetupComplete(true);
        
        // Store success message for login page
        sessionStorage.setItem('enrollment_success', 'true');
        sessionStorage.setItem('enrollment_message', 'Security setup complete! Please sign in with your new authentication methods.');
        
        // Route to login instead of dashboard to force proper AAL2 authentication
        setTimeout(() => {
          window.location.href = '/login?setup_complete=true';
        }, 1500);
      } else {
        // Move to next step if there are more steps
        const remainingSteps = steps.filter(s => latestMissing.includes(s.method));
        if (remainingSteps.length > 0) {
          const nextStep = remainingSteps.find(s => s.id > currentStep);
          if (nextStep) {
            setCurrentStep(nextStep.id);
          }
        }
      }
    }, 2000); // Shorter delay since we're going to dashboard anyway
  };

  // Navigation handlers
  const handleNextStep = () => {
    const nextStep = steps.find(s => s.id > currentStep);
    if (nextStep) {
      setCurrentStep(nextStep.id);
    }
  };

  const handlePreviousStep = () => {
    const prevStep = steps.find(s => s.id < currentStep);
    if (prevStep) {
      setCurrentStep(prevStep.id);
    }
  };

  const handleSkipForNow = () => {
    if (!isUserAdmin()) {
      navigate('/dashboard');
    }
  };

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  // Check if all setup is truly complete
  const isAllSetupComplete = () => {
    return steps.length > 0 && steps.every(step => completedSteps.has(step.id)) && canAccessDashboard();
  };

  // Check navigation availability
  const canGoNext = () => {
    return steps.find(s => s.id > currentStep) !== undefined;
  };

  const canGoPrev = () => {
    return steps.find(s => s.id < currentStep) !== undefined;
  };

  const currentStepObj = steps.find(s => s.id === currentStep);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
      </div>
    );
  }

  if (setupComplete) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="max-w-lg w-full bg-gray-800 rounded-lg shadow-xl p-8 text-center">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">🎉 Security Setup Complete!</h2>
          <p className="text-gray-300 mb-4">
            Your {isUserAdmin() ? '3FA (Email + TOTP + Passkey)' : '2FA'} authentication has been configured successfully.
          </p>
          
          {/* Success message with next steps */}
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6">
            <h3 className="text-blue-300 font-semibold mb-2">🚀 Next: Sign In With Your New Methods</h3>
            <p className="text-blue-200 text-sm">
              You'll be redirected to the login page to authenticate with your newly configured methods.
              This ensures proper AAL2 security verification.
            </p>
          </div>
          
          {/* Countdown and automatic redirect notice */}
          <div className="text-gray-400 text-sm mb-6">
            <p>Redirecting to login page automatically...</p>
            <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
              <div className="bg-green-500 h-2 rounded-full animate-pulse" style={{width: '100%'}}></div>
            </div>
          </div>
          
          <button
            onClick={() => window.location.href = '/login?setup_complete=true'}
            className="w-full py-3 px-6 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            Continue to Login
          </button>
        </div>
      </div>
    );
  }

  // Add a completion check section right after the current step content
  const renderCompletionCheck = () => {
    const allLocalStepsComplete = steps.every(step => completedSteps.has(step.id));
    
    if (allLocalStepsComplete && !setupComplete) {
      return (
        <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-6 mt-6">
          <div className="text-center">
            <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Security Setup Complete!</h3>
            <p className="text-gray-300 mb-4">
              {isUserAdmin() 
                ? "All 3FA requirements have been configured successfully. You can now access the admin dashboard."
                : "Your 2FA setup is complete. You can now access the dashboard with enhanced security."
              }
            </p>
            
            <div className="flex justify-center space-x-4">
              <button
                onClick={async () => {
                  // Try to refresh status one more time
                  await fetchAALStatus();
                  
                  // Force navigate to dashboard since setup is complete
                  navigate('/dashboard');
                }}
                className="py-3 px-6 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center"
              >
                <CheckCircle className="w-5 h-5 mr-2" />
                Continue to Dashboard
              </button>
              
              <button
                onClick={async () => {
                  // Force refresh the session and reload
                  try {
                    await axios.post('/api/auth/refresh-session', {}, {
                      withCredentials: true
                    });
                    window.location.href = '/dashboard';
                  } catch (error) {
                    console.error('Session refresh failed:', error);
                    window.location.reload();
                  }
                }}
                className="py-3 px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Refresh & Continue
              </button>
            </div>
            
            <p className="text-gray-400 text-sm mt-4">
              If you encounter any issues, your security setup is saved and you can safely refresh the page.
            </p>
          </div>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-900 py-8">
      <div className="max-w-3xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <Shield className="w-16 h-16 text-yellow-400 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {isPreAuth 
              ? 'Account Security Setup'  
              : (userRole === 'admin' ? 'Admin Security Setup' : 'Multi-Factor Authentication Setup')
            }
          </h1>
          <p className="text-gray-300 mb-2">
            {isPreAuth ? 'Account: ' : 'Welcome, '}
            <span className="text-yellow-400">{userEmail}</span>
          </p>
          <p className="text-gray-400">
            {isPreAuth 
              ? (userRole === 'admin' 
                  ? 'Before you can sign in, please configure the required security methods for administrator accounts.'
                  : 'Before you can sign in, please configure the required security methods for your account.'
                )
              : (userRole === 'admin' 
                  ? 'Administrator accounts require enhanced security. Start with authenticator app setup, then add passkey protection.'
                  : 'Add additional security layers to your email-verified account. Set up authenticator app first, then optionally add passkey for convenience.'
                )
            }
          </p>
        </div>

        {/* Current Authentication Status */}
        {isPreAuth ? (
          <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-lg p-4 mb-8">
            <div className="flex items-center mb-2">
              <Mail className="w-5 h-5 text-blue-400 mr-2" />
              <span className="text-blue-300 font-medium">Account Setup Required</span>
            </div>
            <p className="text-blue-200 text-sm">
              🔒 Your account needs security setup before you can sign in. Complete the steps below, then return to login.
            </p>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-green-900/20 to-blue-900/20 border border-green-500/30 rounded-lg p-4 mb-8">
            <div className="flex items-center mb-2">
              <Mail className="w-5 h-5 text-green-400 mr-2" />
              <span className="text-green-300 font-medium">Email Verification Complete</span>
              <CheckCircle className="w-4 h-4 text-green-400 ml-2" />
            </div>
            <p className="text-green-200 text-sm">
              ✅ You've successfully verified your email address. Now let's add additional security layers.
            </p>
          </div>
        )}


        {/* Warning for admin users - FIXED LOGIC */}
        {isUserAdmin() && missingMethods.length > 0 && (
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 mb-8">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-red-300 font-medium">Admin Account Security Required</span>
            </div>
            <p className="text-red-200 text-sm mt-1">
              Administrator accounts must complete: {missingMethods.join(', ')} setup.
            </p>
          </div>
        )}

        {/* Success message for completed admin setup */}
        {isUserAdmin() && missingMethods.length === 0 && (
          <div className="bg-green-900/20 border border-green-500 rounded-lg p-4 mb-8">
            <div className="flex items-center">
              <CheckCircle className="w-5 h-5 text-green-400 mr-2" />
              <span className="text-green-300 font-medium">Admin Security Complete</span>
            </div>
            <p className="text-green-200 text-sm mt-1">
              All required administrator security methods have been configured successfully.
            </p>
          </div>
        )}

        {/* Progress Steps */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-white mb-4">Setup Progress</h3>
          <div className="flex items-center justify-between mb-6">
            {steps.map((step, index) => {
              const isCompleted = completedSteps.has(step.id);
              const isCurrent = currentStep === step.id;
              const isPast = step.id < currentStep;
              
              return (
                <React.Fragment key={step.id}>
                  <div className="flex flex-col items-center">
                    <div 
                      className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all cursor-pointer ${
                        isCompleted 
                          ? 'bg-green-600 border-green-600' 
                          : isCurrent 
                            ? `bg-${step.color}-600 border-${step.color}-600` 
                            : 'bg-gray-700 border-gray-600 hover:border-gray-500'
                      }`}
                      onClick={() => setCurrentStep(step.id)}
                    >
                      {isCompleted ? (
                        <CheckCircle className="w-6 h-6 text-white" />
                      ) : (
                        <step.icon className="w-6 h-6 text-white" />
                      )}
                    </div>
                    <span className={`text-sm mt-2 text-center ${
                      isCompleted ? 'text-green-400' : isCurrent ? 'text-white' : 'text-gray-400'
                    }`}>
                      {step.title}
                    </span>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`flex-1 h-1 mx-4 rounded ${
                      isPast || isCompleted ? 'bg-green-600' : 'bg-gray-600'
                    }`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Current Step Content */}
        {currentStepObj && (
          <div className={`bg-gray-800 rounded-xl shadow-xl border-l-4 transition-all ${
            currentStepObj.color === 'blue' ? 'border-blue-400' : 'border-purple-400'
          }`}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <currentStepObj.icon className={`w-8 h-8 mr-3 ${
                    currentStepObj.color === 'blue' ? 'text-blue-400' : 'text-purple-400'
                  }`} />
                  <div>
                    <h3 className="text-xl font-semibold text-white">{currentStepObj.title}</h3>
                    <p className="text-gray-400 text-sm">{currentStepObj.subtitle}</p>
                  </div>
                </div>
                {completedSteps.has(currentStepObj.id) && (
                  <CheckCircle className="w-8 h-8 text-green-400" />
                )}
              </div>
              
              {/* Info Box */}
              <div className={`rounded-lg p-4 mb-6 border ${
                currentStepObj.color === 'blue' 
                  ? 'bg-blue-900/20 border-blue-500/30' 
                  : 'bg-purple-900/20 border-purple-500/30'
              }`}>
                <p className={`text-sm ${
                  currentStepObj.color === 'blue' ? 'text-blue-200' : 'text-purple-200'
                }`}>
                  {currentStepObj.method === 'totp' ? (
                    <>
                      <strong>Authenticator App (Required First):</strong> Generates time-based codes using apps 
                      like Google Authenticator, Authy, or 1Password. This must be set up before adding passkeys.
                    </>
                  ) : (
                    <>
                      <strong>Passkey (After TOTP):</strong> Uses your device's built-in security 
                      (fingerprint, face recognition, or PIN) for convenient access after TOTP is configured.
                    </>
                  )}
                </p>
              </div>

              {/* Setup Component */}
              {!completedSteps.has(currentStepObj.id) && (
                <div className="bg-gray-900/50 rounded-lg p-4 mb-6">
                  {currentStepObj.method === 'webauthn' ? (
                    <PasskeyManagerDirect 
                      isEnrollmentMode={true}
                      onSetupComplete={() => handleSetupComplete('webauthn')}
                    />
                  ) : (
                    <TOTPManager 
                      isEnrollmentMode={true}
                      onSetupComplete={() => handleSetupComplete('totp')}
                    />
                  )}
                </div>
              )}

              {completedSteps.has(currentStepObj.id) && (
                <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6">
                  <div className="flex items-center text-green-300">
                    <CheckCircle className="w-5 h-5 mr-2" />
                    <span className="font-medium">Setup Complete</span>
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex justify-between items-center">
                <button
                  onClick={handlePreviousStep}
                  disabled={!canGoPrev()}
                  className={`flex items-center py-2 px-4 rounded-lg transition-colors ${
                    canGoPrev() 
                      ? 'bg-gray-600 hover:bg-gray-700 text-white' 
                      : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Previous
                </button>

                <div className="text-center">
                  <span className="text-gray-400 text-sm">
                    Step {currentStep} of {steps.length}
                  </span>
                </div>

                <button
                  onClick={handleNextStep}
                  disabled={!canGoNext()}
                  className={`flex items-center py-2 px-4 rounded-lg transition-colors ${
                    canGoNext() 
                      ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                      : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  Next
                  <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Completion Check - Show when all local steps are done */}
        {renderCompletionCheck()}

        {/* Show completion summary when all steps are marked complete */}
        {steps.length > 0 && steps.every(step => completedSteps.has(step.id)) && (
          <div className="bg-gray-800 rounded-lg p-6 mt-6">
            <h4 className="text-white font-medium mb-4 flex items-center">
              <CheckCircle className="w-5 h-5 mr-2 text-green-400" />
              Security Setup Summary
            </h4>
            <div className="space-y-3">
              {steps.map(step => (
                <div key={step.id} className="flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-400 mr-3" />
                  <span className="text-green-300">{step.title} - Complete</span>
                </div>
              ))}
            </div>
            
            <div className="mt-6 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
              <p className="text-green-200 text-sm">
                ✅ <strong>All required security methods configured!</strong> 
                {isUserAdmin() ? ' As an administrator, you now have full dashboard access.' : ' You can now access additional features.'}
              </p>
            </div>
          </div>
        )}

        {/* How It Works Section */}
        <div className="bg-gray-800 rounded-lg p-6 mt-8">
          <h4 className="text-white font-medium mb-4 flex items-center">
            <Lock className="w-5 h-5 mr-2" />
            How Login Works After Setup
          </h4>
          <div className="space-y-4">
            <div className="flex items-start">
              <span className="bg-green-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-4 mt-0.5 font-bold">1</span>
              <div>
                <p className="text-white font-medium">Email Verification</p>
                <p className="text-gray-400 text-sm">Click the secure link sent to your email to start login</p>
              </div>
            </div>
            
            {missingMethods.includes('totp') && (
              <div className="flex items-start">
                <span className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-4 mt-0.5 font-bold">2</span>
                <div>
                  <p className="text-white font-medium">Authenticator Code</p>
                  <p className="text-gray-400 text-sm">Enter the 6-digit code from your authenticator app</p>
                </div>
              </div>
            )}
            
            {missingMethods.includes('webauthn') && (
              <div className="flex items-start">
                <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm mr-4 mt-0.5 font-bold">
                  {missingMethods.includes('totp') ? '3' : '2'}
                </span>
                <div>
                  <p className="text-white font-medium">Passkey Verification</p>
                  <p className="text-gray-400 text-sm">Use your fingerprint, face, or device PIN for quick access</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4 mt-8">
          {/* Show dashboard access button when setup is complete */}
          {steps.length > 0 && steps.every(step => completedSteps.has(step.id)) && (
            <button
              onClick={() => {
                // Navigate directly to dashboard since setup is complete
                window.location.href = '/dashboard';
              }}
              className="py-3 px-6 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center"
            >
              <CheckCircle className="w-5 h-5 mr-2" />
              Access Dashboard
            </button>
          )}
          
          {!isUserAdmin() && missingMethods.length > 0 && !steps.every(step => completedSteps.has(step.id)) && (
            <button
              onClick={handleSkipForNow}
              className="py-3 px-6 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Skip Additional Security
            </button>
          )}
          
          {!steps.every(step => completedSteps.has(step.id)) && (
            <button
              onClick={async () => {
                await fetchAALStatus();
                window.location.reload();
              }}
              className="py-3 px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Refresh Status
            </button>
          )}
        </div>


        {/* Debug Information */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6 border border-gray-600">
          <h4 className="text-white font-medium mb-2">Debug Info:</h4>
          <div className="text-sm text-gray-300 space-y-1">
            <p>Missing Methods: {JSON.stringify(missingMethods)}</p>
            <p>Completed Steps: {JSON.stringify([...completedSteps])}</p>
            <p>Can Access Dashboard: {canAccessDashboard() ? 'Yes' : 'No'}</p>
            <p>Is Admin: {isUserAdmin() ? 'Yes' : 'No'}</p>
            <p>AAL Status: {JSON.stringify(aalStatus?.validation)}</p>
            <p>Configured Methods: {JSON.stringify(aalStatus?.configured_methods)}</p>
            <p>Current AAL: {aalStatus?.validation?.current_aal}</p>
          </div>
        </div>

        {/* Debug Status Check */}
        <div className="text-center mt-4 mb-4">
          <button
            onClick={async () => {
              console.log('🔍 Manual status check triggered...');
              try {
                // First try the refresh endpoint
                try {
                  const response = await axios.post('/api/auth/refresh-session', {}, {
                    withCredentials: true
                  });
                  console.log('Session refresh response:', response.data);
                  
                  // Force a page reload if backend says we can access dashboard
                  if (response.data?.can_access_dashboard) {
                    console.log('✅ Backend confirms dashboard access!');
                    window.location.href = '/dashboard';
                    return;
                  }
                } catch (refreshError) {
                  console.error('Refresh endpoint failed:', refreshError.response?.data || refreshError.message);
                  console.log('Trying direct AAL status check instead...');
                }
                
                // Fallback: Just refresh the AAL status
                await fetchAALStatus();
                console.log('Current AAL status after refresh:', aalStatus);
                
                // Check if we should redirect now
                const missing = getMissingMethods();
                console.log('Missing methods after manual check:', missing);
                
                if (missing.length === 0) {
                  console.log('✅ No missing methods found, redirecting to dashboard');
                  window.location.href = '/dashboard';
                }
                
              } catch (error) {
                console.error('Manual status check completely failed:', error);
                alert('Status check failed. Check console for details.');
              }
            }}
            className="py-2 px-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            🔍 Force Backend Check
          </button>
        </div>

        {/* Help Text */}
        <div className="text-center mt-8">
          <p className="text-gray-400 text-sm">
            Need help with setup? Contact your system administrator or check the{' '}
            <a href="#" className="text-blue-400 hover:underline">documentation</a>.
          </p>
        </div>
      </div>
    </div>
  );
};

export default EnrollmentPage;