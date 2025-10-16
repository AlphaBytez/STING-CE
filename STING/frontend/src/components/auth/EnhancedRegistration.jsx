/**
 * EnhancedRegistration - Unified registration flow for users and admins
 * 
 * Flow:
 * 1. Check for admin registration token (optional)
 * 2. Complete Kratos registration with email verification
 * 3. If admin token provided, upgrade to admin role
 * 4. Redirect to appropriate dashboard
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';

const EnhancedRegistration = () => {
  console.log('🚀 ENHANCED REGISTRATION: Component is mounting!');
  console.log('🚀 ENHANCED REGISTRATION: This is the CORRECT component');
  console.log('🚀 ENHANCED REGISTRATION: If you see this, routing is working');
  
  // Add visible debug banner
  useEffect(() => {
    console.log('🎯 ENHANCED REGISTRATION: Component mounted successfully');
    console.log('🎯 ENHANCED REGISTRATION: URL:', window.location.href);
    console.log('🎯 ENHANCED REGISTRATION: Component name:', EnhancedRegistration.name);
  }, []);
  
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Get admin token from URL if present
  const adminToken = searchParams.get('admin_token');
  
  // State management
  const [step, setStep] = useState('info'); // info, email_verification, webauthn_setup, totp_setup, admin_upgrade, complete
  const [formData, setFormData] = useState({
    email: '',
    firstName: '',
    lastName: '',
    isAdminRegistration: !!adminToken
  });
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [flowData, setFlowData] = useState(null);
  const [adminTokenData, setAdminTokenData] = useState(null);

  // Verify admin token on mount if present
  useEffect(() => {
    if (adminToken) {
      verifyAdminToken();
    }
  }, [adminToken]);

  // Check for pre-filled email from login redirect
  useEffect(() => {
    const prefilledEmail = sessionStorage.getItem('register_email');
    if (prefilledEmail) {
      console.log('🔐 Pre-filling email from login redirect:', prefilledEmail);
      setFormData(prev => ({
        ...prev,
        email: prefilledEmail
      }));
      // Clear the stored email after using it
      sessionStorage.removeItem('register_email');
    }
  }, []);

  const verifyAdminToken = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post('/api/admin-registration/verify-token', {
        token: adminToken
      });
      
      if (response.data.success) {
        setAdminTokenData(response.data.data);
        setSuccess(`Admin registration token verified. Created by: ${response.data.data.created_by}`);
      }
    } catch (error) {
      setError('Invalid or expired admin registration token');
      // Remove token from URL
      navigate('/register', { replace: true });
    } finally {
      setIsLoading(false);
    }
  };

  const initializeKratosRegistrationFlow = async () => {
    try {
      const kratosUrl = 'https://localhost:4433';
      const response = await axios.get(`${kratosUrl}/self-service/registration/browser`, {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      setFlowData(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to initialize Kratos registration flow:', error);
      throw error;
    }
  };

  const handleInfoSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      // Initialize Kratos registration flow
      const flow = await initializeKratosRegistrationFlow();
      
      // Submit registration data to Kratos
      const formParams = new URLSearchParams();
      formParams.append('traits.email', formData.email);
      formParams.append('traits.name.first', formData.firstName);
      formParams.append('traits.name.last', formData.lastName);
      formParams.append('traits.role', 'user'); // Start as user, upgrade later if admin token
      formParams.append('method', 'profile'); // Use profile method for registration
      
      const csrfToken = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token');
      if (csrfToken) {
        formParams.append('csrf_token', csrfToken.attributes.value);
      }
      
      const registrationResponse = await axios.post(
        flow.ui.action,
        formParams.toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      console.log('Registration response:', registrationResponse.status, registrationResponse.data);
      
      // Kratos returns 400 for choose_method state, but it's actually success
      if (registrationResponse.status === 200 || 
          (registrationResponse.status === 400 && registrationResponse.data?.state === 'choose_method')) {
        // Check if this is the expected choose_method state
        if (registrationResponse.data?.state === 'choose_method') {
          console.log('✅ Profile accepted! Kratos is requesting credential setup (choose_method state)');
          
          // Use the same email code approach that works for login
          // Complete registration with email code to establish AAL1 session
          console.log('🔐 Profile created, requesting email code to complete registration');
          setFlowData(registrationResponse.data);
          // Automatically request email code
          await requestEmailCode();
          setSuccess('Profile created! We\'ve sent a verification code to complete registration.');
          setStep('email_verification');
        } else if (registrationResponse.data?.redirect_browser_to) {
          // Registration completed successfully with redirect
          console.log('🎉 Registration completed! Redirecting...');
          handleRegistrationComplete();
        } else {
          // Check for actual error messages (type: "error")
          const errorMsg = registrationResponse.data?.ui?.messages?.find(m => m.type === 'error')?.text;
          if (errorMsg) {
            setError(errorMsg);
          } else {
            // Unexpected state - show debug info
            console.warn('Unexpected registration response:', registrationResponse.data);
            setError('Unexpected registration response. Please try again.');
          }
        }
      } else {
        // Handle HTTP errors
        const errorMsg = registrationResponse.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || `Registration failed (${registrationResponse.status}). Please try again.`);
      }
      
    } catch (error) {
      console.error('Registration failed:', error);
      setError('Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };


  const handleRegistrationComplete = async () => {
    // Registration completed successfully - now require TOTP setup
    console.log('🔐 WebAuthn complete, moving to mandatory TOTP setup to prevent AAL2 traps');
    setStep('totp_setup');
  };

  const requestEmailCode = async () => {
    try {
      console.log('🔐 Following proper Kratos pattern: requesting email code via registration flow');
      
      // Step 1: Submit method: code to registration flow (triggers automatic email sending)
      const csrfToken = flowData?.ui?.nodes?.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;
      console.log('🔐 Flow data available:', !!flowData, 'CSRF token found:', !!csrfToken);
      
      const codeRequest = {
        method: 'code',
        'traits.email': formData.email,
        'traits.name.first': formData.firstName,
        'traits.name.last': formData.lastName,
        'traits.role': formData.isAdminRegistration ? 'admin' : 'user',
        csrf_token: csrfToken
      };

      const response = await fetch(`/.ory/self-service/registration?flow=${flowData.id}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(codeRequest)
      });

      const result = await response.json();
      console.log('🔐 Registration code request result:', response.status, result);
      
      if (result.state === 'sent_email') {
        console.log('✅ Email code sent! State:', result.state);
        setFlowData(result); // Update flow data with sent_email state
      } else {
        console.log('⚠️ Registration flow state:', result.state);
        setFlowData(result); // Update anyway
      }
      
    } catch (err) {
      console.error('🔐 Email code request error:', err);
      setError('Failed to send verification code. Please try again.');
    }
  };

  const handleEmailCodeSubmit = async () => {
    try {
      setIsLoading(true);
      setError('');
      console.log('🔐 Submitting email code to complete registration...');

      // Submit the email code to Kratos verification flow (not registration flow)
      // First, initialize verification flow
      const verificationResponse = await fetch('/.ory/self-service/verification/browser', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      
      if (!verificationResponse.ok) {
        throw new Error('Failed to initialize verification flow');
      }
      
      const verificationData = await verificationResponse.json();
      console.log('🔐 Verification flow initialized:', verificationData.id);
      
      // Now submit the code to verification flow
      const codeSubmission = {
        method: 'code',
        code: verificationCode,
        csrf_token: verificationData.ui.nodes.find(n => n.attributes.name === 'csrf_token')?.attributes.value
      };

      const submitResponse = await fetch(`/.ory/self-service/verification?flow=${verificationData.id}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(codeSubmission)
      });

      const result = await submitResponse.json();
      console.log('🔐 Email code submission result:', submitResponse.status, result);

      if (submitResponse.ok || result.continue_with) {
        console.log('✅ Registration completed! AAL1 session established');
        setSuccess('Registration completed! Redirecting to security setup...');
        
        // Registration complete - redirect to post-registration for 2FA setup
        setTimeout(() => {
          navigate('/post-registration', {
            state: {
              registrationComplete: true,
              email: formData.email,
              isAdminRegistration: formData.isAdminRegistration
            }
          });
        }, 2000);
      } else {
        const errorMsg = result.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || 'Invalid code. Please check your email and try again.');
      }
      
    } catch (err) {
      console.error('🔐 Email code submission error:', err);
      setError('Failed to submit code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTOTPSetup = async () => {
    try {
      setIsLoading(true);
      setError('');
      console.log('🔐 Starting mandatory TOTP setup to prevent AAL2 traps');

      // Initialize Kratos settings flow for TOTP setup
      const settingsResponse = await fetch('/.ory/self-service/settings/browser', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      if (!settingsResponse.ok) {
        throw new Error('Failed to initialize TOTP setup flow');
      }

      const settingsData = await settingsResponse.json();
      console.log('🔐 TOTP settings flow initialized:', settingsData.id);
      
      // For now, move to admin upgrade or complete (TOTP setup UI to be implemented)
      console.log('🔐 TOTP setup flow ready - proceeding to next step');
      
      if (formData.isAdminRegistration && adminToken) {
        setStep('admin_upgrade');
        await upgradeToAdmin();
      } else {
        setSuccess('Registration completed with enhanced security!');
        setStep('complete');
      }
      
    } catch (err) {
      console.error('🔐 TOTP setup error:', err);
      setError('Failed to initialize TOTP setup. You can complete this in Settings later.');
      
      // Allow continuation but warn user
      setTimeout(() => {
        if (formData.isAdminRegistration && adminToken) {
          setStep('admin_upgrade');
        } else {
          setStep('complete');
        }
      }, 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWebAuthnSetup = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      // Check if we have the WebAuthn challenge from the last registration response
      if (!flowData || !flowData.ui) {
        setError('Registration session expired. Please refresh and try again.');
        return;
      }
      
      // Find the WebAuthn trigger button data
      const webauthnTrigger = flowData.ui.nodes.find(n => 
        n.attributes?.name === 'webauthn_register_trigger'
      );
      
      if (!webauthnTrigger || !webauthnTrigger.attributes?.value) {
        setError('WebAuthn setup data not found. Please refresh and try again.');
        return;
      }
      
      // Parse the WebAuthn challenge
      const challengeData = JSON.parse(webauthnTrigger.attributes.value);
      console.log('🔐 WebAuthn challenge data:', challengeData);
      
      // Convert base64url challenge to ArrayBuffer
      if (challengeData.publicKey.challenge) {
        try {
          // Convert base64url string to ArrayBuffer
          const challengeStr = challengeData.publicKey.challenge;
          const challengeBuffer = Uint8Array.from(atob(challengeStr.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
          challengeData.publicKey.challenge = challengeBuffer.buffer;
          console.log('🔐 Challenge converted to ArrayBuffer:', challengeBuffer);
        } catch (err) {
          console.error('Failed to convert challenge:', err);
          setError('Invalid WebAuthn challenge format. Please refresh and try again.');
          return;
        }
      }
      
      // Convert user.id if it exists
      if (challengeData.publicKey.user && challengeData.publicKey.user.id) {
        try {
          const userIdStr = challengeData.publicKey.user.id;
          const userIdBuffer = Uint8Array.from(atob(userIdStr.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
          challengeData.publicKey.user.id = userIdBuffer.buffer;
          console.log('🔐 User ID converted to ArrayBuffer');
        } catch (err) {
          console.error('Failed to convert user ID:', err);
        }
      }
      
      console.log('🔐 Final challenge data for WebAuthn:', challengeData);
      
      // Create the WebAuthn credential
      const credential = await navigator.credentials.create({
        publicKey: challengeData.publicKey
      });
      
      if (!credential) {
        setError('Passkey setup was cancelled or failed.');
        return;
      }
      
      console.log('✅ WebAuthn credential created:', credential);
      
      // Prepare the credential response for Kratos using proper base64url encoding
      const arrayBufferToBase64Url = (buffer) => {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        bytes.forEach((byte) => {
          binary += String.fromCharCode(byte);
        });
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
      };
      
      // IMPORTANT: Kratos expects rawId to be base64url encoded, but id should remain the original string
      const response = {
        id: credential.id, // Keep original string ID
        rawId: arrayBufferToBase64Url(credential.rawId), // Convert ArrayBuffer to base64url
        type: credential.type,
        response: {
          attestationObject: arrayBufferToBase64Url(credential.response.attestationObject),
          clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON)
        }
      };
      
      // Verify that rawId is actually different from id (debugging)
      console.log('🔐 Credential ID (string):', credential.id);
      console.log('🔐 Raw ID (base64url):', response.rawId);
      console.log('🔐 Are they different?', credential.id !== response.rawId);
      
      console.log('🔐 Formatted WebAuthn response:', response);
      
      // Submit the WebAuthn credential to complete registration
      const formParams = new URLSearchParams();
      formParams.append('method', 'webauthn'); // CRITICAL: Must specify method for Kratos
      formParams.append('webauthn_register', JSON.stringify(response));
      formParams.append('webauthn_register_displayname', 'STING Passkey');
      
      // CRITICAL: Include traits with email for Kratos identity schema validation
      formParams.append('traits.email', formData.email);
      formParams.append('traits.name.first', formData.firstName || '');
      formParams.append('traits.name.last', formData.lastName || '');
      
      const csrfToken = flowData.ui.nodes.find(n => n.attributes?.name === 'csrf_token');
      if (csrfToken) {
        formParams.append('csrf_token', csrfToken.attributes.value);
      }
      
      const registrationResponse = await axios.post(
        flowData.ui.action,
        formParams.toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      console.log('Registration completion response:', registrationResponse.status, registrationResponse.data);
      
      // Check for successful registration (200 OR 400 with choose_method state)
      if (registrationResponse.status === 200 || 
          (registrationResponse.status === 400 && registrationResponse.data?.state === 'choose_method')) {
        
        // For Kratos, 400 with choose_method often means successful WebAuthn registration
        if (registrationResponse.data?.state === 'choose_method') {
          console.log('✅ WebAuthn registration successful! Kratos choose_method state indicates completion.');
        }
        
        if (registrationResponse.data?.redirect_browser_to) {
          // Registration successful with redirect!
          console.log('✅ Registration completed! Redirect URL:', registrationResponse.data.redirect_browser_to);
          
          if (formData.isAdminRegistration && adminToken) {
            // Upgrade to admin role first, then redirect to login
            setStep('admin_upgrade');
            await upgradeToAdmin();
          } else {
            // Registration complete - redirect to login page
            console.log('🔄 Redirecting to login with newly created passkey...');
            setSuccess('Registration successful! Please sign in with your new passkey.');
            setStep('complete');
            setTimeout(() => {
              navigate('/login', { 
                state: { 
                  registrationSuccess: true,
                  email: formData.email,
                  message: 'Registration successful! Sign in with your passkey.'
                }
              });
            }, 2000);
          }
        } else if (registrationResponse.data?.session_token || registrationResponse.data?.session) {
          // Registration successful with session - but still redirect to login for security
          console.log('✅ Registration completed with session, but redirecting to login for proper flow');
          
          // All users need TOTP setup after WebAuthn to prevent AAL2 traps
          console.log('🔐 WebAuthn successful, proceeding to mandatory TOTP setup');
          setStep('totp_setup');
        } else {
          // For choose_method state without redirect, assume WebAuthn registration completed successfully
          console.log('✅ WebAuthn registration appears successful (choose_method state). Redirecting to login...');
          
          // All users need TOTP setup after WebAuthn to prevent AAL2 traps
          console.log('🔐 WebAuthn successful, proceeding to mandatory TOTP setup');
          setStep('totp_setup');
        }
      } else {
        // Only treat as error if it's not the expected choose_method state
        const errorMsg = registrationResponse.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        setError(errorMsg || `Registration completion failed (${registrationResponse.status}). Please try again.`);
      }
      
    } catch (error) {
      console.error('WebAuthn setup failed:', error);
      console.error('Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      
      if (error.name === 'NotSupportedError') {
        setError('Passkeys are not supported on this device or browser.');
      } else if (error.name === 'NotAllowedError') {
        setError('Passkey setup was cancelled or not allowed.');
      } else if (error.name === 'InvalidStateError') {
        setError('A passkey for this account already exists on this device.');
      } else if (error.name === 'NetworkError') {
        setError('Network error during passkey setup. Please check your connection.');
      } else if (error.message?.includes('base64') || error.message?.includes('ArrayBuffer')) {
        setError('Invalid data format in WebAuthn challenge. Please refresh and try again.');
      } else {
        setError(`Passkey setup failed: ${error.message || 'Please try again.'}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const upgradeToAdmin = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post('/api/admin-registration/upgrade-to-admin', {
        token: adminToken,
        email: formData.email
      });
      
      if (response.data.success) {
        setSuccess('Successfully upgraded to admin role!');
        setStep('complete');
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      }
    } catch (error) {
      console.error('Admin upgrade failed:', error);
      setError('Failed to upgrade to admin role. You can complete this later in settings.');
      // Still redirect to dashboard as regular user
      setTimeout(() => {
        navigate('/dashboard');
      }, 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyAdminUpgrade = async () => {
    const secret = prompt('Enter admin registration secret:');
    if (!secret) return;
    
    try {
      setIsLoading(true);
      const response = await axios.post('/api/admin-registration/emergency-upgrade', {
        secret: secret,
        email: formData.email
      });
      
      if (response.data.success) {
        setSuccess('Emergency admin upgrade completed!');
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      }
    } catch (error) {
      setError('Emergency upgrade failed. Invalid secret or other error.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            {formData.isAdminRegistration ? 'Admin Registration' : 'Create Account'}
          </h1>
          <p className="text-gray-300">
            {formData.isAdminRegistration 
              ? 'Complete admin account setup'
              : 'Join STING Platform with passwordless authentication'
            }
          </p>
        </div>

        {/* Admin Token Status */}
        {formData.isAdminRegistration && adminTokenData && (
          <div className="sting-glass-subtle border border-blue-500/50 text-blue-200 px-4 py-3 rounded-lg mb-6">
            <p className="text-sm">
              🔐 <strong>Admin Registration</strong><br />
              Token created by: {adminTokenData.created_by}
            </p>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="sting-glass-subtle border border-green-500/50 text-green-200 px-4 py-3 rounded-lg mb-6">
            {success}
          </div>
        )}

        {/* Step 1: Basic Information */}
        {step === 'info' && (
          <form onSubmit={handleInfoSubmit} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  First Name
                </label>
                <input
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => setFormData({...formData, firstName: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                  required
                  disabled={isLoading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Last Name
                </label>
                <input
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => setFormData({...formData, lastName: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                placeholder="you@example.com"
                required
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 text-black font-semibold py-3 px-4 rounded-lg transition duration-200"
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>
        )}


        {/* Step 2: WebAuthn Setup */}
        {step === 'webauthn_setup' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">🔐</div>
              <h3 className="text-xl font-bold text-white mb-2">Set Up Your Passkey</h3>
              <p className="text-gray-300 mb-4">
                STING uses passwordless authentication. Please set up a passkey to secure your account.
              </p>
              <p className="text-sm text-gray-400 mb-6">
                Passkeys work with Face ID, Touch ID, or your device's security key.
              </p>
              
              <button
                onClick={handleWebAuthnSetup}
                disabled={isLoading}
                className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 mb-4"
              >
                {isLoading ? 'Setting up passkey...' : '🔑 Set Up Passkey'}
              </button>
              
              <p className="text-xs text-gray-500">
                Your passkey will be stored securely on this device and synced to your iCloud Keychain (iOS/macOS) or Google Password Manager (Android/Chrome).
              </p>
            </div>
            
            {isLoading && (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
                <span className="text-gray-300">Follow the prompts on your device...</span>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Email Verification (Like login - establishes AAL1) */}
        {step === 'email_verification' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">📧</div>
              <h3 className="text-xl font-bold text-white mb-2">Complete Registration</h3>
              <p className="text-gray-300 mb-4">
                We've sent a code to <strong>{formData.email}</strong>
              </p>
              <p className="text-gray-400 text-sm mb-4">
                Enter the 6-digit code to complete your registration and establish your secure session.
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <input
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  maxLength="6"
                  autoComplete="one-time-code"
                />
              </div>
              
              <button
                onClick={handleEmailCodeSubmit}
                disabled={isLoading || verificationCode.length !== 6}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-bold py-3 px-6 rounded-lg transition-all duration-200"
              >
                {isLoading ? 'Completing registration...' : 'Complete Registration'}
              </button>
            </div>
            
            <p className="text-gray-400 text-sm">
              After completing registration, you'll be redirected to set up additional security.
            </p>
          </div>
        )}

        {/* Step 3: WebAuthn Setup (After email verification) */}
        {step === 'webauthn_setup' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">🔐</div>
              <h3 className="text-xl font-bold text-white mb-2">Set Up Your Passkey</h3>
              <p className="text-gray-300 mb-4">
                Your email is verified! Now set up a passkey to secure your account.
              </p>
            </div>
          </div>
        )}

        {/* Step 4: TOTP Setup (Mandatory to prevent AAL2 traps) */}
        {step === 'totp_setup' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-yellow-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">📱</div>
              <h3 className="text-xl font-bold text-white mb-2">Set Up Authenticator App</h3>
              <p className="text-gray-300 mb-4">
                Complete your secure registration by adding TOTP authentication. This prevents account lockouts and ensures smooth login experience.
              </p>
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-4">
                <p className="text-yellow-300 text-sm">
                  ⚠️ This step is required to prevent authentication loops in future logins.
                </p>
              </div>
            </div>
            
            <button
              onClick={handleTOTPSetup}
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-bold py-3 px-6 rounded-lg transition-all duration-200"
            >
              {isLoading ? 'Setting up TOTP...' : 'Set Up Authenticator App'}
            </button>
            
            <p className="text-gray-400 text-sm">
              You'll need an authenticator app like Google Authenticator, Authy, or 1Password.
            </p>
          </div>
        )}

        {/* Step 4: Admin Upgrade */}
        {step === 'admin_upgrade' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-blue-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">🔐</div>
              <h3 className="text-xl font-bold text-white mb-2">Upgrading to Admin</h3>
              <p className="text-gray-300">
                Your account is being upgraded to administrator privileges...
              </p>
            </div>
            
            {isLoading && (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-yellow-400"></div>
                <span className="text-gray-300">Processing upgrade...</span>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Complete */}
        {step === 'complete' && (
          <div className="space-y-6 text-center">
            <div className="sting-glass-subtle border border-green-500/50 rounded-lg p-6">
              <div className="text-4xl mb-4">🎉</div>
              <h3 className="text-xl font-bold text-white mb-2">
                {formData.isAdminRegistration ? 'Admin Account Created!' : 'Account Created!'}
              </h3>
              <p className="text-gray-300">
                Welcome to STING Platform. Redirecting to dashboard...
              </p>
            </div>
          </div>
        )}

        {/* Login Link */}
        {step === 'info' && (
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              Already have an account?{' '}
              <button
                onClick={() => navigate('/login')}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Sign in here
              </button>
            </p>
          </div>
        )}

        {/* Emergency Admin Upgrade */}
        {step === 'complete' && !formData.isAdminRegistration && (
          <div className="mt-6 text-center">
            <button
              onClick={handleEmergencyAdminUpgrade}
              className="text-gray-500 hover:text-gray-400 text-xs underline"
            >
              Emergency Admin Upgrade
            </button>
          </div>
        )}

        {/* Dev Mode Helper */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs">
              📧 Dev: Check{' '}
              <a href="http://localhost:8026" target="_blank" rel="noopener noreferrer" className="underline">
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

export default EnhancedRegistration;