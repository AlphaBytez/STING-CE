import React, { useState, useEffect, useRef } from 'react';
import { Key, Shield, Loader, AlertCircle, Check, Trash2, Plus, Info, RefreshCw } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import { useTheme } from '../../context/ThemeContext';
import { useNavigate } from 'react-router-dom';
import securityGateService from '../../services/securityGateService';
import { setupGlobalNavigationPrevention } from '../../utils/settingsNavigation';
import axios from 'axios';

const PasskeyManagerDirect = ({ isEnrollmentMode = false, onSetupComplete = null }) => {
  const { themeColors } = useTheme();
  const { identity, checkSession } = useKratos();
  const navigate = useNavigate();
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [passkeyName, setPasskeyName] = useState('');
  const [registrationStatus, setRegistrationStatus] = useState('');
  const [settingsFlow, setSettingsFlow] = useState(null);
  const [has2FA, setHas2FA] = useState(false);
  const [checkingAAL, setCheckingAAL] = useState(true);
  const formRef = useRef(null);
  const checkIntervalRef = useRef(null);
  const isRegisteringRef = useRef(false); // Ref for beforeunload check to avoid stale closure

  // Check if user has 2FA enabled and current AAL
  const check2FAStatus = async () => {
    try {
      setCheckingAAL(true);
      
      // Check current session for AAL and available authentication methods
      const sessionResponse = await axios.get('/.ory/sessions/whoami', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });
      
      const session = sessionResponse.data;
      console.log('🔒 Session AAL info:', {
        aal: session.authenticator_assurance_level,
        methods: session.authentication_methods
      });
      
      // Check if user has TOTP or other 2FA methods configured
      // Check both credentials and current session authentication methods
      const credentialTOTP = session.identity?.credentials?.totp && 
                            Object.keys(session.identity.credentials.totp).length > 0;
      
      const sessionTOTP = session.authentication_methods?.some(method => 
                         method.method === 'totp' && method.aal === 'aal2');
      
      // Check if user is admin and has completed TOTP setup flow
      const isAdmin = session.identity?.traits?.role?.toLowerCase() === 'admin';
      const completedTOTPSetup = localStorage.getItem('totp_setup_complete') === 'true';
      
      // Also check if TOTP setup was recently completed (within 5 minutes)
      const recentTOTPSetup = sessionStorage.getItem('totp_recently_setup') === 'true';
      
      const hasTOTP = credentialTOTP || sessionTOTP || completedTOTPSetup || recentTOTPSetup;
      
      const hasWebAuthnSetup = session.identity?.credentials?.webauthn && 
                              Object.keys(session.identity.credentials.webauthn).length > 0;
      
      // UPDATED: Allow admin users to set up passkey regardless of TOTP order
      // Admins need both methods but can set them up in any order
      // For regular users: require TOTP OR allow passkey as their 2FA method
      const allows2FA = isAdmin ? true : (hasTOTP || session.authenticator_assurance_level >= 'aal1');
      setHas2FA(allows2FA);
      
      console.log('🔒 2FA Detection Details:', { 
        credentialTOTP, 
        sessionTOTP, 
        isAdmin,
        completedTOTPSetup,
        recentTOTPSetup,
        hasTOTP, 
        hasWebAuthnSetup, 
        allows2FA,
        finalHas2FA: allows2FA 
      });
      
      console.log('🔒 2FA Status:', { hasTOTP, hasWebAuthnSetup, has2FA: allows2FA });
      
    } catch (error) {
      console.error('Error checking 2FA status:', error);
      // For admin users, be permissive if there's an error checking
      try {
        const fallbackResponse = await axios.get('/api/auth/me', { withCredentials: true });
        const isAdmin = fallbackResponse.data?.is_admin;
        setHas2FA(isAdmin || false);
        console.log('🔒 Fallback 2FA check for admin:', isAdmin);
      } catch (fallbackError) {
        setHas2FA(false);
      }
    } finally {
      setCheckingAAL(false);
    }
  };

  // Load passkeys from settings flow
  const loadPasskeys = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Create or refresh settings flow to get latest data
      console.log('🔐 Loading settings flow for passkeys...');
      const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      const flow = flowResponse.data;
      setSettingsFlow(flow);
      
      // Find WebAuthn remove nodes - these indicate existing passkeys
      const webauthnNodes = flow.ui.nodes.filter(n => n.group === 'webauthn');
      const removeNodes = webauthnNodes.filter(n => 
        n.attributes?.name === 'webauthn_remove' && 
        n.attributes?.type === 'submit'
      );
      
      console.log(`🔐 Found ${removeNodes.length} passkeys from remove buttons`);
      
      // Extract passkey info from nodes
      const extractedPasskeys = removeNodes.map((node, index) => {
        // The value is the credential ID
        const credentialId = node.attributes.value;
        
        // Try to find display name from node title or meta
        let displayName = `Passkey ${index + 1}`;
        
        // Look for a related text node that might have the display name
        const relatedTextNode = webauthnNodes.find(n => 
          n.type === 'text' && 
          n.meta?.label?.text?.includes('display_name')
        );
        
        if (node.meta?.label?.context?.display_name) {
          displayName = node.meta.label.context.display_name;
        }
        
        return {
          id: credentialId,
          display_name: displayName,
          created_at: null, // Not available in this view
          last_used: null,
          identifier: identity?.traits?.email
        };
      });
      
      setPasskeys(extractedPasskeys);
      
      // Double-check by looking at messages
      const messages = flow.ui.messages || [];
      const passkeyMessage = messages.find(m => 
        m.text?.includes('passkey') || m.text?.includes('WebAuthn')
      );
      
      if (passkeyMessage) {
        console.log('📝 Passkey message:', passkeyMessage.text);
      }
      
    } catch (err) {
      console.error('Error loading passkeys:', err);
      setError('Failed to load passkeys. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  // Load on mount and when identity changes
  useEffect(() => {
    if (identity) {
      check2FAStatus();
      loadPasskeys();
    }
  }, [identity]);

  // Setup global navigation prevention to avoid Kratos redirects
  useEffect(() => {
    if (!isEnrollmentMode) {
      const cleanup = setupGlobalNavigationPrevention(navigate, 'security');
      return cleanup;
    }
  }, [navigate, isEnrollmentMode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      if (formRef.current && document.body.contains(formRef.current)) {
        document.body.removeChild(formRef.current);
      }
    };
  }, []);

  // Intercept form submission to prevent redirect
  useEffect(() => {
    const interceptFormSubmission = (e) => {
      const form = e.target;
      if (form.id === 'webauthn-settings-form') {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        console.log('🔐 Intercepted form submission');
        
        // Submit via AJAX instead
        const formData = new FormData(form);
        const data = new URLSearchParams();
        for (const [key, value] of formData.entries()) {
          data.append(key, value.toString());
        }
        
        // Submit the form via fetch
        fetch(form.action, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          body: data
        }).then(response => {
          console.log('🔐 Form submission response:', response.status);
          if (response.ok || response.status === 422) {
            // 422 might mean the flow needs to be refreshed
            console.log('🔐 Registration may have completed, checking...');
          }
        }).catch(err => {
          console.error('Form submission error:', err);
        });
        
        return false;
      }
    };

    // Global Kratos redirect prevention
    const originalPushState = window.history.pushState;
    const originalReplaceState = window.history.replaceState;
    
    const preventKratosRedirects = () => {
      // Override history methods globally during passkey operations
      window.history.pushState = function(state, title, url) {
        if (url && (url.includes('/.ory/') || url.includes('kratos') || url.includes('self-service/settings/browser'))) {
          console.log('🔐 [GLOBAL] Blocked pushState to Kratos:', url);
          return;
        }
        return originalPushState.call(this, state, title, url);
      };
      
      window.history.replaceState = function(state, title, url) {
        if (url && (url.includes('/.ory/') || url.includes('kratos') || url.includes('self-service/settings/browser'))) {
          console.log('🔐 [GLOBAL] Blocked replaceState to Kratos:', url);
          return;
        }
        return originalReplaceState.call(this, state, title, url);
      };
    };

    // Add global form submit listener with capture phase
    document.addEventListener('submit', interceptFormSubmission, true);
    
    // Start global redirect prevention
    preventKratosRedirects();
    
    // Also intercept beforeunload to prevent navigation
    // BUT: Skip this in enrollment mode to avoid interfering with the enrollment flow
    // Use ref instead of state to avoid stale closure issue
    const preventNavigation = (e) => {
      if (isRegisteringRef.current && !isEnrollmentMode) {
        console.log('🔐 Preventing navigation during registration');
        e.preventDefault();
        e.returnValue = '';
      }
    };
    
    // Only add the beforeunload listener if not in enrollment mode
    if (!isEnrollmentMode) {
      window.addEventListener('beforeunload', preventNavigation);
    }
    
    return () => {
      document.removeEventListener('submit', interceptFormSubmission, true);
      if (!isEnrollmentMode) {
        window.removeEventListener('beforeunload', preventNavigation);
      }
      
      // Restore original history methods
      window.history.pushState = originalPushState;
      window.history.replaceState = originalReplaceState;
      console.log('🔐 [CLEANUP] Restored original history methods');
    };
  }, [isRegistering, isEnrollmentMode]);

  // Start passkey registration
  const startRegistration = async () => {
    if (!passkeyName.trim()) {
      setError('Please enter a name for your passkey');
      return;
    }

    // Check 2FA requirement before allowing passkey registration
    if (!has2FA) {
      const userRole = identity?.traits?.role?.toLowerCase();
      if (userRole === 'admin') {
        setError('✅ Admin Setup: You can create passkeys and TOTP in any order. Both methods provide secure access to admin features.');
      } else {
        setError('🔐 2FA Required: Please set up TOTP (authenticator app) first, then you can add passkeys as an additional secure login method.');
      }
      return;
    }

    setError('');
    setSuccess('');
    setIsRegistering(true);
    isRegisteringRef.current = true; // Update ref immediately
    setRegistrationStatus('Initializing...');

    try {
      // Use existing flow or create new one
      let flow = settingsFlow;
      if (!flow) {
        console.log('🔐 Creating new settings flow...');
        const flowResponse = await axios.get('/.ory/self-service/settings/browser', {
          headers: { 'Accept': 'application/json' },
          withCredentials: true
        });
        flow = flowResponse.data;
        setSettingsFlow(flow);
      }

      console.log('🔐 Settings flow ready:', flow.id);

      // Find the WebAuthn trigger
      const triggerNode = flow.ui.nodes.find(
        n => n.group === 'webauthn' && 
             n.attributes?.name === 'webauthn_register_trigger' && 
             n.attributes?.type === 'button'
      );

      if (!triggerNode) {
        throw new Error('WebAuthn registration not available. Please ensure your email is verified.');
      }

      // Build and submit the form
      setRegistrationStatus('Preparing security session...');
      
      const form = document.createElement('form');
      form.id = 'webauthn-settings-form';
      // In enrollment mode, ensure the action URL uses the correct base path
      let actionUrl = flow.ui.action;
      if (isEnrollmentMode && !actionUrl.startsWith('http')) {
        // Ensure we use the full URL to prevent relative path issues
        actionUrl = `${window.location.origin}${actionUrl.startsWith('/') ? '' : '/'}${actionUrl}`;
      }
      form.action = actionUrl;
      form.method = 'POST';
      form.style.cssText = 'position: absolute; left: -9999px; visibility: hidden;';
      
      // Add all input nodes from the flow
      flow.ui.nodes.forEach(node => {
        if (node.type === 'input') {
          const input = document.createElement('input');

          // Null check for input element creation
          if (!input) {
            console.error('❌ Failed to create input element for passkey registration');
            return;
          }

          try {
            input.type = node.attributes?.type || 'hidden';
            input.name = node.attributes?.name || '';
            input.id = node.attributes?.name || '';

            // Set the value
            if (node.attributes?.name === 'webauthn_register_displayname') {
              input.value = passkeyName || '';
            } else {
              input.value = node.attributes?.value || '';
            }

            form.appendChild(input);
          } catch (error) {
            console.error('❌ Error setting input properties for passkey registration:', error);
          }
        }
      });

      // Add submit button
      const button = document.createElement('button');

      // Null check for button element creation
      if (!button) {
        console.error('❌ Failed to create button element for passkey registration');
        throw new Error('Failed to create registration button');
      }

      try {
        button.type = 'submit';
        button.name = triggerNode.attributes?.name || '';
        button.value = triggerNode.attributes?.value || '';
        form.appendChild(button);
      } catch (error) {
        console.error('❌ Error setting button properties for passkey registration:', error);
        throw new Error('Failed to configure registration button');
      }

      // Override form submission to prevent redirect
      form.onsubmit = (e) => {
        e.preventDefault();
        console.log('🔐 Form submission blocked - handling via AJAX');
        return false;
      };

      document.body.appendChild(form);
      formRef.current = form;

      // Load WebAuthn script if needed
      if (!window.oryWebAuthnRegistration) {
        console.log('⏳ Loading WebAuthn script...');
        setRegistrationStatus('Loading security components...');
        
        const scriptNode = flow.ui.nodes.find(n => n.type === 'script' && n.group === 'webauthn');
        if (scriptNode?.attributes?.src) {
          await loadScript(scriptNode.attributes.src);
        }
      }

      setRegistrationStatus('Please complete the security prompt in your browser...');
      
      // Monitor for completion
      let attempts = 0;
      const initialCount = passkeys.length;
      
      checkIntervalRef.current = setInterval(async () => {
        attempts++;
        
        try {
          // Check for new passkeys by fetching fresh data
          const checkResponse = await axios.get('/.ory/self-service/settings/browser', {
            headers: { 'Accept': 'application/json' },
            withCredentials: true
          });
          
          const checkFlow = checkResponse.data;
          const checkNodes = checkFlow.ui.nodes.filter(n => n.group === 'webauthn');
          const removeNodes = checkNodes.filter(n => 
            n.attributes?.name === 'webauthn_remove' && 
            n.attributes?.type === 'submit'
          );
          
          // Check if count increased
          if (removeNodes.length > initialCount) {
            console.log('✅ New passkey detected!');
            clearInterval(checkIntervalRef.current);
            checkIntervalRef.current = null;
            setSuccess('Passkey registered successfully!');
            setPasskeyName('');
            setIsRegistering(false);
            isRegisteringRef.current = false; // Clear ref immediately to prevent leave warning
            setRegistrationStatus('');
            
            if (formRef.current && document.body.contains(formRef.current)) {
              document.body.removeChild(formRef.current);
              formRef.current = null;
            }
            
            // Reload the passkeys list
            await loadPasskeys();
            
            // CRITICAL: Refresh session data after successful passkey registration
            // This prevents logout issues due to AAL level changes
            try {
              console.log('🔐 Refreshing session data after passkey registration...');
              await checkSession(); // Refresh Kratos session
              await check2FAStatus(); // Refresh AAL status
              
              // CRITICAL: Clear SecurityGateService cache to prevent redirect loops
              console.log('🔐 Clearing SecurityGateService cache after passkey setup...');
              securityGateService.clearCache(identity?.traits?.email);
              
              // Call enrollment completion callback if provided
              if (isEnrollmentMode && onSetupComplete) {
                console.log('🔐 Calling enrollment completion callback...');
                // Call immediately, don't delay
                onSetupComplete('webauthn');
                
                // Don't prevent navigation - the enrollment page will handle it
                console.log('🔐 Enrollment mode - completion callback triggered, enrollment page will handle navigation');
              }
              
              // Emit event to trigger AAL status refresh across the app
              window.dispatchEvent(new CustomEvent('aal-status-refresh'));

              console.log('✅ Session and AAL status refreshed successfully');

              // Auto-reload after brief delay for non-enrollment mode to show success message
              // This prevents the "Leave site?" dialog and ensures clean UI state
              if (!isEnrollmentMode) {
                console.log('🔄 Auto-reloading page to refresh UI state...');
                setTimeout(() => {
                  window.location.reload();
                }, 1500); // 1.5 second delay to show success message
              }
            } catch (refreshError) {
              console.error('⚠️ Error refreshing session after passkey registration:', refreshError);
              // Don't fail the registration, just log the error
            }

            // Note: In enrollment mode, the callback handles navigation
            // In settings mode, we auto-reload to prevent "Leave site?" dialog
            console.log(`🔐 Passkey registration completed, ${isEnrollmentMode ? 'enrollment callback triggered' : 'page will auto-reload'}`);
          }
        } catch (err) {
          console.error('Error checking for new passkey:', err);
        }
        
        if (attempts >= 120) { // 2 minutes
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
          setError('Passkey registration timed out. Please try again.');
          setIsRegistering(false);
          isRegisteringRef.current = false; // Clear ref on timeout
          setRegistrationStatus('');
          
          if (formRef.current && document.body.contains(formRef.current)) {
            document.body.removeChild(formRef.current);
            formRef.current = null;
          }
        }
      }, 1000);

      // Add onclick handler to trigger WebAuthn
      button.onclick = async (e) => {
        e.preventDefault();
        console.log('🔐 Button clicked, triggering WebAuthn...');
        
        // Store current location to restore later
        const currentLocation = window.location.href;
        
        try {
          const webauthnOptions = JSON.parse(triggerNode.attributes.value);
          console.log('🔐 WebAuthn options:', webauthnOptions);
          
          // Enhanced navigation prevention - block all Kratos/Ory redirects
          const originalPushState = window.history.pushState;
          const originalReplaceState = window.history.replaceState;
          const originalAssign = window.location.assign;
          const originalReplace = window.location.replace;
          let restoreTimer = null;
          
          // Override navigation methods to prevent Kratos redirects
          const preventKratosNavigation = () => {
            // Helper to check if we should block the redirect
            const shouldBlockRedirect = (url) => {
              if (!url) return false;
              
              // Block Kratos/Ory redirects
              if (url.includes('ory') || url.includes('kratos') || url.includes('self-service')) {
                return true;
              }
              
              // In enrollment mode, also block redirects to settings pages
              if (isEnrollmentMode && (url.includes('/settings') || url.includes('/dashboard/settings'))) {
                return true;
              }
              
              return false;
            };
            
            window.history.pushState = (state, title, url) => {
              if (shouldBlockRedirect(url)) {
                console.log('🔐 Blocked pushState redirect to:', url);
                return;
              }
              return originalPushState.call(window.history, state, title, url);
            };
            
            window.history.replaceState = (state, title, url) => {
              if (shouldBlockRedirect(url)) {
                console.log('🔐 Blocked replaceState redirect to:', url);
                return;
              }
              return originalReplaceState.call(window.history, state, title, url);
            };
            
            // Try to override location methods safely
            try {
              if (originalAssign && typeof originalAssign === 'function') {
                window.location.assign = (url) => {
                  if (shouldBlockRedirect(url)) {
                    console.log('🔐 Blocked location.assign redirect to:', url);
                    return;
                  }
                  return originalAssign.call(window.location, url);
                };
              }
              
              if (originalReplace && typeof originalReplace === 'function') {
                window.location.replace = (url) => {
                  if (shouldBlockRedirect(url)) {
                    console.log('🔐 Blocked location.replace redirect to:', url);
                    return;
                  }
                  return originalReplace.call(window.location, url);
                };
              }
            } catch (e) {
              console.log('🔐 Note: Could not override location methods (browser restriction)');
            }
            
            // Also monitor for direct href changes
            let currentHref = window.location.href;
            const hrefMonitor = setInterval(() => {
              const newHref = window.location.href;
              if (newHref !== currentHref) {
                if (shouldBlockRedirect(newHref)) {
                  console.log('🔐 Detected unwanted redirect, restoring location');
                  window.history.replaceState(null, '', currentHref);
                } else {
                  currentHref = newHref;
                }
              }
            }, 100);
            
            return hrefMonitor;
          };
          
          // Start prevention
          const hrefMonitor = preventKratosNavigation();
          
          // Restore methods after 15 seconds
          restoreTimer = setTimeout(() => {
            clearInterval(hrefMonitor);
            window.history.pushState = originalPushState;
            window.history.replaceState = originalReplaceState;
            
            // Safely restore location methods
            try {
              if (originalAssign) window.location.assign = originalAssign;
              if (originalReplace) window.location.replace = originalReplace;
            } catch (e) {
              console.log('🔐 Note: Could not restore location methods');
            }
            
            console.log('🔐 Navigation monitoring stopped');
          }, 15000);
          
          // Call WebAuthn registration
          if (window.oryWebAuthnRegistration) {
            console.log('🔐 Calling oryWebAuthnRegistration...');
            window.oryWebAuthnRegistration(webauthnOptions);
          } else if (triggerNode.attributes.onclick) {
            console.log('🔐 Parsing onclick to avoid redirect...');
            const onclickCode = triggerNode.attributes.onclick;
            
            // Try to safely extract WebAuthn call without executing redirect code
            if (onclickCode.includes('oryWebAuthnRegistration')) {
              console.log('🔐 Attempting safe WebAuthn execution');
              // Use a modified eval that blocks window navigation
              const originalWindowOpen = window.open;
              window.open = () => { console.log('🔐 Blocked window.open'); };
              
              try {
                eval(onclickCode);
              } finally {
                window.open = originalWindowOpen;
              }
            } else {
              throw new Error('WebAuthn function not found in onclick');
            }
          } else {
            throw new Error('WebAuthn registration method not available');
          }
        } catch (err) {
          console.error('Error triggering WebAuthn:', err);
          setError('Failed to start passkey registration. Please try again.');
        }
      };
      
      // Trigger click after a small delay to ensure form is ready
      setTimeout(() => {
        console.log('🔐 Clicking button to start registration...');
        button.click();
      }, 100);

    } catch (err) {
      console.error('Registration error:', err);
      setError(err.message || 'Failed to register passkey');
      setIsRegistering(false);
      isRegisteringRef.current = false; // Clear ref on error
      setRegistrationStatus('');
      
      if (formRef.current && document.body.contains(formRef.current)) {
        document.body.removeChild(formRef.current);
        formRef.current = null;
      }
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
    }
  };

  // Helper to load a script
  const loadScript = (src) => {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }
      
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  };

  // Remove passkey
  const removePasskey = async (passkeyId) => {
    // Check 2FA requirement before allowing passkey removal
    if (!has2FA) {
      setError('🔐 2FA Required: Please set up TOTP (authenticator app) first before managing passkeys.');
      return;
    }

    if (!window.confirm('Are you sure you want to remove this passkey?')) {
      return;
    }

    setError('');
    setSuccess('');

    try {
      if (!settingsFlow) {
        await loadPasskeys(); // This will set settingsFlow
      }

      const flow = settingsFlow;
      const csrfToken = flow.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;

      const formData = new URLSearchParams();
      formData.append('csrf_token', csrfToken);
      formData.append('webauthn_remove', passkeyId);

      await axios.post(flow.ui.action, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true
      });

      setSuccess('Passkey removed successfully');
      // Reload passkeys
      await loadPasskeys();
    } catch (err) {
      console.error('Remove error:', err);
      setError('Failed to remove passkey');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading || checkingAAL) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="w-8 h-8 animate-spin text-yellow-400" />
        <span className="ml-3 text-gray-400">
          {checkingAAL ? 'Checking security requirements...' : 'Loading passkeys...'}
        </span>
      </div>
    );
  }

  return (
    <div className={`max-w-4xl mx-auto p-6 ${themeColors.mainBg || 'bg-slate-800'}`}>
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Key className="w-8 h-8 text-yellow-400" />
              <div>
                <h1 className="text-2xl font-bold text-white">Passkey Management</h1>
                <p className="text-gray-400 text-sm mt-1">
                  Manage your passwordless authentication methods
                </p>
              </div>
            </div>
            <button
              onClick={loadPasskeys}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              title="Refresh passkeys"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Messages */}
          {error && (
            <div className="mb-6 p-4 glass-subtle border border-red-500/30 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="text-red-300">{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 glass-subtle border border-green-500/30 rounded-lg flex items-center gap-3">
              <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
              <span className="text-green-300">{success}</span>
            </div>
          )}

          {/* Positive status when passkeys are configured and working */}
          {has2FA && passkeys.length > 0 && !error && !isRegistering && (
            <div className="mb-6 p-4 bg-green-900/20 border border-green-700/50 rounded-lg flex items-center gap-3">
              <Shield className="w-5 h-5 text-green-400 flex-shrink-0" />
              <div className="text-green-300 text-sm">
                <span className="font-medium">✅ Passkey Security Active:</span> You have {passkeys.length} passkey{passkeys.length > 1 ? 's' : ''} configured for secure, passwordless authentication.
              </div>
            </div>
          )}

          {/* Registration Status */}
          {registrationStatus && (
            <div className="mb-6 p-4 glass-subtle border border-blue-500/30 rounded-lg flex items-center gap-3">
              <Loader className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
              <span className="text-blue-300">{registrationStatus}</span>
            </div>
          )}

          {/* 2FA Requirement Warning */}
          {!has2FA && (
            <div className="mb-6 p-4 bg-amber-900/20 border border-amber-700/50 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-300">
                  {identity?.traits?.role?.toLowerCase() === 'admin' ? (
                    <>
                      <p className="font-semibold mb-1">🛡️ Admin Enhanced Security Setup</p>
                      <p>
                        Admin accounts use enhanced security with multiple authentication methods. 
                        You can set up <strong>passkey OR TOTP</strong> in any order - both provide secure admin access.
                      </p>
                      <p className="mt-2 text-amber-400/80 text-xs">
                        💡 Tip: Passkeys (biometric/hardware) are often more convenient, while TOTP provides reliable backup access.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-semibold mb-1">🔐 Secure Authentication Setup</p>
                      <p>
                        Set up TOTP (authenticator app) first for your security foundation. 
                        Then you can add passkeys for faster, more convenient login.
                      </p>
                      <p className="mt-2 text-amber-400/80 text-xs">
                        💡 This two-step approach ensures you always have secure backup access via your authenticator app.
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Existing Passkeys */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Your Passkeys</h2>
            
            {passkeys.length === 0 ? (
              <div className="p-6 bg-slate-700/30 border border-slate-600/50 rounded-lg text-center">
                <Shield className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                <p className="text-gray-400">No passkeys registered yet</p>
                <p className="text-gray-500 text-sm mt-1">
                  Add a passkey to enable passwordless sign-in
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {passkeys.map((passkey, index) => (
                  <div
                    key={passkey.id}
                    className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg hover:bg-slate-700/70 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Key className="w-5 h-5 text-yellow-400" />
                        <div>
                          <p className="text-white font-medium">{passkey.display_name}</p>
                          <p className="text-xs text-gray-400">
                            Credential ID: {passkey.id.substring(0, 20)}...
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => removePasskey(passkey.id)}
                        className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Remove passkey"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add New Passkey */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Add New Passkey</h2>
            
            <div className="p-6 bg-blue-900/20 border border-blue-700/50 rounded-lg">
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-2 text-sm font-medium">
                    Passkey Name
                  </label>
                  <input
                    type="text"
                    value={passkeyName}
                    onChange={(e) => setPasskeyName(e.target.value)}
                    placeholder="e.g., MacBook Pro, iPhone, YubiKey"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400"
                    disabled={isRegistering}
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Give your passkey a name to identify it later
                  </p>
                </div>

                <button
                  onClick={startRegistration}
                  disabled={isRegistering || !window.PublicKeyCredential || !has2FA}
                  className="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRegistering ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      <span>Registering...</span>
                    </>
                  ) : !has2FA ? (
                    <>
                      <Plus className="w-5 h-5" />
                      <span>{identity?.traits?.role?.toLowerCase() === 'admin' ? 'Setup Available - Choose Method' : 'Setup TOTP First'}</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-5 h-5" />
                      <span>Register New Passkey</span>
                    </>
                  )}
                </button>

                {isRegistering && (
                  <p className="text-xs text-gray-400 text-center">
                    Complete the security prompt in your browser. This may take up to 2 minutes.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Info Note */}
          <div className="mt-6 p-4 bg-amber-900/20 border border-amber-700/50 rounded-lg">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-300">
                <p className="font-semibold mb-1">Note:</p>
                <p>
                  Passkeys are being fetched directly from your security settings. 
                  If you don't see your passkeys immediately after registration, 
                  click the refresh button above.
                </p>
              </div>
            </div>
          </div>

          {/* Info Section */}
          <div className="mt-8 p-4 bg-slate-700/30 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">About Passkeys</h3>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>• Passkeys are a secure, passwordless way to sign in</li>
              <li>• They use your device's biometrics or security key</li>
              <li>• Each passkey is unique to this website</li>
              <li>• You can have multiple passkeys on different devices</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PasskeyManagerDirect;