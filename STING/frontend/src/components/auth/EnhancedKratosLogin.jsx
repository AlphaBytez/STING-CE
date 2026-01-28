import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useKratos } from '../../auth/KratosProviderRefactored';
import kratosApi, { getKratosUrl } from '../../utils/kratosConfig';
import { useAALStatus } from '../../hooks/useAALStatus';
import { detectWebAuthnCapabilities, getAuthenticationButtonConfig } from '../../utils/webAuthnDetection';
import AdminNotice from './AdminNotice';
import PasskeyMigrationWarning from './PasskeyMigrationWarning';
import '../../theme/sting-glass-theme.css';
import '../../theme/glass-login-override.css';

/**
 * EnhancedKratosLogin - A component that uses Kratos native WebAuthn
 * with an identifier-first authentication flow.
 */
const EnhancedKratosLogin = () => {
  // State
  const [flowData, setFlowData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [flowInitialized, setFlowInitialized] = useState(false);
  const [error, setError] = useState('');
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [webAuthnCapabilities, setWebAuthnCapabilities] = useState(null);
  const [authButtonConfig, setAuthButtonConfig] = useState(null);
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPasswordField, setShowPasswordField] = useState(false);
  const [identifierSubmitted, setIdentifierSubmitted] = useState(false);
  const [hasCustomPasskeys, setHasCustomPasskeys] = useState(false);
  const [showPasskeyWarning, setShowPasskeyWarning] = useState(false);
  const [emailConfig, setEmailConfig] = useState(null);
  
  // Check if this is an AAL2 flow
  const needsAAL2 = searchParams.get('aal') === 'aal2';
  
  const navigate = useNavigate();
  const { isAuthenticated, checkSession } = useKratos();
  
  // AAL status management
  const {
    aalStatus,
    isAALCompliant,
    needsSetup,
    getMissingMethods,
    getCurrentAAL,
    getRequiredAAL,
    isAdmin,
    canAccessDashboard,
    fetchAALStatus
  } = useAALStatus();
  
  // Get Kratos URL using configuration utility
  const kratosUrl = getKratosUrl(true); // true for browser navigation
  
  // Get flow ID from URL if present
  const flowId = searchParams.get('flow');
  
  // Handle authentication state and AAL requirements
  useEffect(() => {
    // Check if we're already authenticated at the required level
    const checkAuthLevel = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const requestedAAL = urlParams.get('aal');
      
      if (isAuthenticated && aalStatus) {
        console.log('🔐 Checking authentication level:', {
          isAuthenticated,
          currentAAL: getCurrentAAL(),
          requiredAAL: getRequiredAAL(),
          requestedAAL,
          isAALCompliant: isAALCompliant(),
          canAccessDashboard: canAccessDashboard(),
          needsSetup: needsSetup()
        });
        
        // Check if user meets AAL requirements
        if (isAALCompliant() && canAccessDashboard()) {
          // User is properly authenticated - redirect to intended destination
          const redirectUrl = sessionStorage.getItem('redirectAfterLogin') || '/dashboard';
          sessionStorage.removeItem('redirectAfterLogin');
          console.log('🔐 User is AAL compliant, redirecting to:', redirectUrl);
          navigate(redirectUrl);
        } else if (requestedAAL && getCurrentAAL() >= requestedAAL) {
          // User has reached the requested AAL level
          const redirectUrl = sessionStorage.getItem('redirectAfterLogin') || '/dashboard';
          sessionStorage.removeItem('redirectAfterLogin');
          console.log('🔐 User reached requested AAL level, redirecting to:', redirectUrl);
          navigate(redirectUrl);
        } else {
          // User needs additional authentication
          console.log('🔐 User needs additional authentication:', {
            missingMethods: getMissingMethods(),
            isAdmin: isAdmin()
          });
          // Let the login flow handle step-up authentication
        }
      } else if (requestedAAL) {
        // Specific AAL level requested - let the flow handle this
        console.log('🔐 Specific AAL authentication required:', requestedAAL);
      }
    };
    
    // Only check if we have AAL status (avoid premature redirects)
    if (aalStatus !== null) {
      checkAuthLevel();
    }
  }, [isAuthenticated, aalStatus, getCurrentAAL, getRequiredAAL, isAALCompliant, canAccessDashboard, needsSetup, getMissingMethods, isAdmin, navigate]);
  
  // Enhanced WebAuthn capability detection
  useEffect(() => {
    let mounted = true;
    
    const detectCapabilities = async () => {
      console.log('🔐 Detecting WebAuthn capabilities...');
      try {
        const capabilities = await detectWebAuthnCapabilities();
        const buttonConfig = await getAuthenticationButtonConfig();
        
        if (mounted) {
          setWebAuthnCapabilities(capabilities);
          setAuthButtonConfig(buttonConfig);
          setWebAuthnSupported(capabilities.supported);
          
          console.log('🔐 WebAuthn capabilities detected:', {
            supported: capabilities.supported,
            hasPlatformAuth: capabilities.hasplatformAuthenticator,
            hasExternalAuth: capabilities.hasExternalAuthenticator,
            userMessage: capabilities.userMessage,
            buttonConfig: buttonConfig
          });
        }
      } catch (err) {
        console.error('🔐 Error detecting WebAuthn capabilities:', err);
        if (mounted) {
          setWebAuthnSupported(false);
          setWebAuthnCapabilities({ supported: false, userMessage: 'WebAuthn detection failed' });
        }
      }
    };
    
    detectCapabilities();
    
    return () => {
      mounted = false;
    };
  }, []);
  
  // Log WebAuthn support state when it changes
  useEffect(() => {
    console.log('🔐 WebAuthn supported state updated:', webAuthnSupported);
  }, [webAuthnSupported]);
  
  // Load Kratos WebAuthn script on component mount
  useEffect(() => {
    // Check if the Kratos WebAuthn script is already loaded
    if (!window.oryPasskeyLogin) {
      console.log('🔐 Loading Kratos WebAuthn script...');
      const script = document.createElement('script');
      script.src = `/.ory/.well-known/ory/webauthn.js`;
      script.async = true;
      script.onload = () => {
        console.log('🔐 Kratos WebAuthn script loaded successfully');
        console.log('🔐 WebAuthn functions available:', {
          oryPasskeyLogin: typeof window.oryPasskeyLogin,
          oryPasskeyLoginAutocompleteInit: typeof window.oryPasskeyLoginAutocompleteInit
        });
      };
      script.onerror = () => {
        console.error('🔐 Failed to load Kratos WebAuthn script');
      };
      document.head.appendChild(script);
      
      // Cleanup function to remove script on unmount
      return () => {
        if (document.head.contains(script)) {
          document.head.removeChild(script);
        }
      };
    }
  }, []);
  
  // Fetch flow data on mount or when flowId changes
  useEffect(() => {
    const fetchFlowData = async () => {
      // Prevent multiple initializations
      if (!flowId && !flowData && !flowInitialized) {
        // Check if we need AAL2 by examining URL params
        const urlParams = new URLSearchParams(window.location.search);
        const needsAAL2 = urlParams.get('aal') === 'aal2';
        
        // If no flow ID, initialize a new login flow via API
        try {
          console.log('No flow ID found, initializing new login flow...');
          if (needsAAL2) {
            console.log('🔐 AAL2 required - initializing flow with aal=aal2');
          }
          setFlowInitialized(true); // Set immediately to prevent duplicate calls
          
          // Construct the URL with AAL2 parameter if needed
          const loginUrl = needsAAL2 
            ? `/.ory/self-service/login/browser?refresh=true&aal=aal2`
            : `/.ory/self-service/login/browser?refresh=true`;
            
          const response = await axios.get(loginUrl, {
            headers: {
              'Accept': 'application/json',
            },
            withCredentials: true
          });
          
          if (response.data && response.data.id) {
            console.log('New login flow created:', response.data.id);
            setFlowData(response.data);
            
            // For AAL2 flows, check if we already have TOTP fields available
            if (needsAAL2) {
              console.log('🔐 AAL2 flow detected, checking for available auth methods...');
              const hasTOTPField = response.data.ui.nodes.some(node => 
                node.attributes?.name === 'totp_code' || node.group === 'totp'
              );
              const hasLookupField = response.data.ui.nodes.some(node => 
                node.attributes?.name === 'lookup_secret' || node.group === 'lookup_secret'
              );
              
              if (hasTOTPField || hasLookupField) {
                console.log('🔐 Second factor fields available, showing auth form');
                setIdentifierSubmitted(true);
                setShowPasswordField(true);
              }
            }
            // Don't update URL - this was causing loops
          }
        } catch (error) {
          console.error('Failed to initialize login flow:', error);
          setError('Failed to initialize login. Please try again.');
          // flowInitialized already set above
        } finally {
          setIsLoading(false);
        }
        return;
      } else if (flowId && !flowData) {
        // We have a flow ID, fetch the flow data
        try {
          setIsLoading(true);
          
          // Log the URL we're about to fetch
          console.log(`Fetching flow data from: ${kratosUrl}/self-service/login/flows?id=${flowId}`);
        
          const response = await axios.get(
            kratosApi.loginFlow(flowId),
            {
              withCredentials: true,
            }
          );
          
          // Log the response status
          console.log(`Flow fetch response status: ${response.status}`);
          console.log('🔐 Flow data received:', response.data);
          setFlowData(response.data);
          setFlowInitialized(true);
          
          // Check for script nodes that need to be executed
          if (response.data && response.data.ui && response.data.ui.nodes) {
            const scriptNodes = response.data.ui.nodes.filter(node => node.type === 'script');
            console.log('🔐 Found script nodes:', scriptNodes.length);
            
            scriptNodes.forEach(node => {
              if (node.attributes?.src) {
                console.log('🔐 Loading script from:', node.attributes.src);
                const script = document.createElement('script');
                script.src = node.attributes.src;
                script.async = node.attributes.async || true;
                script.crossOrigin = node.attributes.crossorigin || 'anonymous';
                if (node.attributes.referrerpolicy) {
                  script.referrerPolicy = node.attributes.referrerpolicy;
                }
                if (node.attributes.type) {
                  script.type = node.attributes.type;
                }
                script.onload = () => {
                  console.log('🔐 Script loaded successfully');
                  // Check for onload handlers
                  if (node.attributes.onload) {
                    console.log('🔐 Executing onload handler');
                    try {
                      eval(node.attributes.onload);
                    } catch (e) {
                      console.error('🔐 Error executing onload:', e);
                    }
                  }
                };
                document.body.appendChild(script);
              }
            });
          }
        } catch (err) {
          console.error('Error fetching flow data:', err);
          setError('Failed to connect to authentication service. Please try again later.');
          setFlowInitialized(true); // Set even on error so UI shows
        } finally {
          setIsLoading(false);
        }
      }
    };
    
    fetchFlowData();
    checkEmailConfig();
  }, [flowId, kratosUrl]); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Check email configuration for showing hints
  const checkEmailConfig = async () => {
    try {
      const response = await axios.get('/api/config/smtp/status');
      setEmailConfig(response.data);
      console.log('📧 Email config:', response.data);
    } catch (error) {
      console.log('Could not fetch email config:', error);
    }
  };
  
  // Monitor for passkey authentication attempts
  useEffect(() => {
    // Check if there's an error message about authentication failure
    if (flowData?.ui?.messages) {
      const hasAuthError = flowData.ui.messages.some(msg => 
        msg.type === 'error' && 
        (msg.text?.toLowerCase().includes('authentication') || 
         msg.text?.toLowerCase().includes('credentials'))
      );
      
      if (hasAuthError && webAuthnSupported && !sessionStorage.getItem('passkey_warning_shown')) {
        setShowPasskeyWarning(true);
      }
    }
  }, [flowData, webAuthnSupported]);
  
  // Start login flow
  const startLogin = async () => {
    // Temporarily disabled flow restart prevention for debugging
    // if (identifierSubmitted && showPasswordField && flowData?.ui?.nodes?.some(node => 
    //   node.attributes?.name === 'code' || node.group === 'code'
    // )) {
    //   console.log('🔐 Preventing restart - passwordless flow already active');
    //   return;
    // }
    
    // Clear error state first
    setError('');
    setIsLoading(true);
    
    try {
      // Check if we need AAL2
      const urlParams = new URLSearchParams(window.location.search);
      const needsAAL2 = urlParams.get('aal') === 'aal2';
      
      const loginUrl = needsAAL2 
        ? `/.ory/self-service/login/browser?refresh=true&aal=aal2`
        : `/.ory/self-service/login/browser?refresh=true`;
        
      console.log('🔐 Starting login flow:', loginUrl);
        
      const response = await axios.get(loginUrl, {
        headers: {
          'Accept': 'application/json',
        },
        withCredentials: true
      });
      
      if (response.data && response.data.id) {
        console.log('New login flow created:', response.data.id);
        setFlowData(response.data);
        // Reset form state
        setEmail('');
        setPassword('');
        setIdentifierSubmitted(false);
        setShowPasswordField(false);
        // Update URL with flow ID
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('flow', response.data.id);
        if (needsAAL2) {
          newUrl.searchParams.set('aal', 'aal2');
        }
        window.history.pushState({}, '', newUrl);
      }
    } catch (error) {
      console.error('Failed to initialize login flow:', error);
      setError('Failed to initialize login. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Start registration flow
  const startRegistration = () => {
    // Build dynamic return URL to handle Codespaces/VMs/port forwarding
    const returnUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
    window.location.href = `${kratosUrl}/self-service/registration/browser?return_to=${returnUrl}`;
  };
  
  // Extract WebAuthn-related nodes from flow
  const getWebAuthnButton = () => {
    if (!flowData || !flowData.ui || !flowData.ui.nodes) return null;
    
    console.log('🔐 Searching for WebAuthn button in flow nodes...');
    
    // Log all nodes for debugging
    flowData.ui.nodes.forEach((node, index) => {
      if (node.attributes?.type === 'button' || node.attributes?.name?.includes('webauthn') || node.attributes?.name?.includes('passkey')) {
        console.log(`🔐 Node ${index}:`, {
          name: node.attributes.name,
          type: node.attributes.type,
          value: node.attributes.value,
          onclick: node.attributes.onclick ? 'has onclick' : 'no onclick'
        });
      }
    });
    
    // Find the WebAuthn button node - try multiple possible names
    const webAuthnNode = flowData.ui.nodes.find(node => 
      node.attributes &&
      node.attributes.type === 'button' &&
      (
        node.attributes.name === 'webauthn_login_trigger' ||
        node.attributes.name === 'webauthn_login' ||
        node.attributes.name === 'passkey_login_trigger' ||
        node.attributes.name?.includes('webauthn') ||
        node.attributes.name?.includes('passkey')
      ) &&
      node.attributes.onclick
    );
    
    if (webAuthnNode) {
      console.log('🔐 Found WebAuthn button:', webAuthnNode.attributes.name);
    } else {
      console.log('🔐 No WebAuthn button found in flow');
    }
    
    return webAuthnNode ? webAuthnNode.attributes.onclick : null;
  };
  
  
  // Trigger WebAuthn login
  const handleWebAuthnLogin = async (e) => {
    e.preventDefault();
    
    // Check if we have Kratos WebAuthn support in the flow
    const clickHandler = getWebAuthnButton();
    if (clickHandler && flowData) {
      // Use Kratos WebAuthn
      console.log('🔐 Using Kratos WebAuthn');
      // eslint-disable-next-line no-eval
      eval(clickHandler);
    } else {
      // No WebAuthn available in this flow
      console.log('🔐 WebAuthn not available in current flow');
      setError('Please enter your email and password to continue');
    }
  };
  
  // Handle custom passkey login (with optional email)
  const handleCustomPasskeyLogin = async (e, useDiscoverable = true) => {
    console.log('🔐 handleCustomPasskeyLogin called!');
    e.preventDefault();
    
    try {
      console.log('🔐 Setting loading state...');
      setIsLoading(true);
      setError('');
      
      console.log('🔐 Starting custom passkey authentication, discoverable:', useDiscoverable);
      
      // Start custom passkey authentication
      // If useDiscoverable is true, don't send username to get all available passkeys
      const beginResponse = await axios.post('/api/webauthn/authentication/begin', 
        useDiscoverable ? {} : { username: email }, 
        {
          withCredentials: true
        }
      );
      
      console.log('🔐 Custom passkey auth options:', beginResponse.data);
      
      // Convert the options for the browser API
      const publicKeyOptions = beginResponse.data;
      
      // The challenge might already be base64url encoded, we need to handle it properly
      const challengeStr = publicKeyOptions.publicKey ? publicKeyOptions.publicKey.challenge : publicKeyOptions.challenge;
      if (challengeStr) {
        // Convert base64url to base64 if needed
        const base64 = challengeStr.replace(/-/g, '+').replace(/_/g, '/');
        // Pad if necessary
        const padded = base64 + '=='.substring(0, (4 - base64.length % 4) % 4);
        publicKeyOptions.challenge = Uint8Array.from(atob(padded), c => c.charCodeAt(0));
        if (publicKeyOptions.publicKey) {
          publicKeyOptions.publicKey.challenge = publicKeyOptions.challenge;
        }
      }
      
      if (publicKeyOptions.publicKey.allowCredentials && publicKeyOptions.publicKey.allowCredentials.length > 0) {
        publicKeyOptions.publicKey.allowCredentials = publicKeyOptions.publicKey.allowCredentials.map(cred => {
          // Validate credential object before accessing properties
          if (!cred || !cred.id) {
            throw new Error('Invalid credential in allowCredentials: missing credential or credential ID');
          }
          // Handle base64url encoding for credential IDs
          const credIdStr = cred.id.replace(/-/g, '+').replace(/_/g, '/');
          const paddedCredId = credIdStr + '=='.substring(0, (4 - credIdStr.length % 4) % 4);
          return {
            ...cred,
            id: Uint8Array.from(atob(paddedCredId), c => c.charCodeAt(0))
          };
        });
      } else if (useDiscoverable) {
        // For discoverable credentials, we don't specify allowCredentials
        delete publicKeyOptions.publicKey.allowCredentials;
      }
      
      // Get credential from browser
      console.log('🔐 Requesting credential from browser...');
      console.log('🔐 PublicKey options:', publicKeyOptions.publicKey);
      
      let credential;
      try {
        credential = await navigator.credentials.get({
          publicKey: publicKeyOptions.publicKey
        });
      } catch (credErr) {
        console.error('🔐 Error getting credential:', credErr);
        throw credErr;
      }
      
      console.log('🔐 Got credential from browser:', credential);

      // Validate credential before using it
      if (!credential) {
        throw new Error('Authentication was cancelled or failed');
      }

      if (!credential.id || !credential.rawId || !credential.response) {
        console.error('🔐 Invalid credential object received:', credential);
        throw new Error('Invalid credential received from authenticator');
      }
      
      console.log('🔐 Credential ID:', credential.id);
      console.log('🔐 Credential type:', credential.type);
      
      // Prepare credential data for backend
      const credentialData = {
        id: credential.id,
        rawId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
        response: {
          clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(credential.response.clientDataJSON))),
          authenticatorData: btoa(String.fromCharCode(...new Uint8Array(credential.response.authenticatorData))),
          signature: btoa(String.fromCharCode(...new Uint8Array(credential.response.signature))),
          userHandle: credential.response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(credential.response.userHandle))) : null
        },
        type: credential.type
      };
      
      console.log('🔐 Sending credential to backend:', credentialData);
      
      // Complete authentication
      const completeResponse = await axios.post('/api/webauthn/authentication/complete', 
        { credential: credentialData }, 
        {
          withCredentials: true,
          timeout: 30000 // 30 second timeout
        }
      );
      
      console.log('🔐 Backend response:', completeResponse.data);
      
      if (completeResponse.data.verified) {
        console.log('🔐 Custom passkey authentication successful');
        console.log('🔐 Authentication response:', completeResponse.data);
        
        // Sync Kratos session to ensure identity traits are populated
        try {
          console.log('🔐 Syncing Kratos session...');
          const syncResponse = await axios.post('/api/auth/sync-kratos-session', {}, {
            withCredentials: true
          });
          console.log('🔐 Kratos session sync response:', syncResponse.data);
        } catch (syncErr) {
          console.error('🔐 Failed to sync Kratos session:', syncErr);
          // Don't fail login if sync fails
        }
        
        console.log('🔐 Redirecting to dashboard in 1 second...');
        
        // Add a small delay to ensure session is set
        setTimeout(() => {
          // Check if we have a redirect URL stored
          const redirectUrl = sessionStorage.getItem('redirectAfterLogin');
          if (redirectUrl) {
            console.log('🔐 Redirecting to stored URL:', redirectUrl);
            sessionStorage.removeItem('redirectAfterLogin');
            window.location.href = redirectUrl;
          } else {
            console.log('🔐 Now redirecting to /dashboard');
            window.location.href = '/dashboard';
          }
        }, 1000);
      } else {
        setError('Passkey authentication failed');
      }
      
    } catch (err) {
      console.error('🔐 Custom passkey authentication error:', err);
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.name === 'NotAllowedError') {
        setError('Authentication was cancelled or timed out');
      } else {
        setError('Failed to authenticate with passkey');
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle identifier-first flow
  const handleIdentifierSubmit = async (e) => {
    e.preventDefault();
    
    // Race condition protection: prevent multiple submissions
    if (isLoading) {
      console.log('🔐 Identifier submission already in progress, ignoring duplicate');
      return;
    }
    
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    
    if (!flowData) {
      setError('No login flow available. Please refresh the page.');
      return;
    }
    
    try {
      setIsLoading(true);
      setError('');
      
      // Small delay to prevent race conditions and improve UX
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Skip custom passkey check - we're using Kratos WebAuthn now
      const hasCustomPasskeys = false;
      
      // For identifier-first flow, submit the identifier with method
      const params = new URLSearchParams();
      params.append('identifier', email);
      params.append('method', 'identifier_first');
      
      // Add CSRF token if present
      const csrfNode = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token');
      if (csrfNode) {
        params.append('csrf_token', csrfNode.attributes.value);
        console.log('🔐 Found CSRF token:', csrfNode.attributes.value);
      } else {
        console.log('🔐 WARNING: No CSRF token found in flow');
      }
      
      // Use the action URL as-is from the flow (it should already point to the proxy)
      let actionUrl = flowData.ui.action;
      
      // If it's a relative URL, make it absolute with the .ory prefix
      if (!actionUrl.startsWith('http')) {
        actionUrl = `/.ory${actionUrl}`;
      } else if (actionUrl.includes('/self-service/')) {
        // If it's an absolute URL pointing to Kratos, convert to proxy URL
        const url = new URL(actionUrl);
        actionUrl = `/.ory${url.pathname}${url.search}`;
      }
      
      console.log('🔐 Submitting identifier to:', actionUrl);
      
      // NOTE: Kratos returns 400 status for identifier-first flow - this is expected!
      // The 400 response contains the updated flow with available auth methods.
      const response = await axios.post(actionUrl, params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        withCredentials: true,
        validateStatus: () => true, // Don't throw on 4xx/5xx - we handle these
      });
      
      console.log('Identifier submission response:', response.status, response.data);
      console.log('Response has ui?:', !!response.data?.ui);
      console.log('Response ui nodes count:', response.data?.ui?.nodes?.length);
      
      if (response.status === 200 || response.status === 303) {
        // Success - redirect happened
        const redirectUrl = sessionStorage.getItem('redirectAfterLogin');
        if (redirectUrl) {
          sessionStorage.removeItem('redirectAfterLogin');
          window.location.href = redirectUrl;
        } else {
          window.location.href = response.headers.location || '/dashboard';
        }
      } else if (response.status === 400 && response.data && response.data.ui) {
        // This is expected - Kratos returns 400 with updated flow
        console.log('🔐 Setting identifierSubmitted=true after 400 response');
        setFlowData(response.data);
        setIdentifierSubmitted(true);
        
        // Log all nodes to see what's available after identifier submission
        console.log('🔐 Nodes after identifier submission:');
        response.data.ui.nodes.forEach((node, index) => {
          console.log(`🔐 Node ${index}:`, {
            type: node.type,
            name: node.attributes?.name,
            nodeType: node.attributes?.type,
            value: node.attributes?.value,
            meta: node.meta
          });
        });
        
        // Check if WebAuthn nodes are available
        const hasWebAuthnButton = response.data.ui.nodes.some(node => 
          (node.attributes?.type === 'button' || node.attributes?.type === 'submit') && 
          (node.attributes?.name === 'method' && node.attributes?.value === 'webauthn' ||
           node.attributes?.name?.includes('webauthn') || 
           node.attributes?.name?.includes('passkey') ||
           node.attributes?.onclick?.includes('webauthn') ||
           node.group === 'webauthn')
        );
        
        // Check if TOTP nodes are available
        const hasTOTPField = response.data.ui.nodes.some(node => 
          node.attributes?.name === 'totp_code' ||
          node.group === 'totp'
        );
        
        // Check if lookup secret (recovery code) field is available
        const hasLookupSecretField = response.data.ui.nodes.some(node => 
          node.attributes?.name === 'lookup_secret' ||
          node.group === 'lookup_secret'
        );
        
        // Check if code field is available (for passwordless)
        const hasCodeField = response.data.ui.nodes.some(node => 
          node.attributes?.name === 'code' ||
          node.group === 'code'
        );
        
        // Check if we're in link sent state (for passwordless link)
        const hasLinkSent = response.data.ui.nodes.some(node => 
          node.group === 'link' ||
          (node.meta?.label?.text && node.meta.label.text.includes('email'))
        );
        
        // Check if password field exists (don't require 'required' attribute)
        const passwordNode = response.data.ui.nodes.find(node => 
          node.attributes?.name === 'password'
        );
        
        // Log available authentication methods
        console.log('🔐 === AVAILABLE AUTHENTICATION METHODS ===');
        console.log('🔐 Has WebAuthn button:', hasWebAuthnButton);
        console.log('🔐 Has TOTP field:', hasTOTPField);
        console.log('🔐 Has lookup secret field:', hasLookupSecretField);
        console.log('🔐 Has password field:', !!passwordNode);
        console.log('🔐 Has code field:', hasCodeField);
        console.log('🔐 Has link sent:', hasLinkSent);
        console.log('🔐 Has custom passkeys:', hasCustomPasskeys);
        
        // Log groups present in the flow
        const groups = [...new Set(response.data.ui.nodes.map(n => n.group))];
        console.log('🔐 Node groups present:', groups);
        
        // Check if we're stuck in identifier_first loop (no auth methods available)
        const isStuckInLoop = !passwordNode && !hasTOTPField && !hasLookupSecretField && !hasCodeField && !hasLinkSent;
        
        if (isStuckInLoop) {
          console.log('🔐 Detected stuck identifier_first loop - showing manual options instead of auto-trigger');
          setError('Choose your authentication method below');
          // AUTO-TRIGGER COMPLETELY DISABLED: Let users choose manually
          // Users will see manual buttons: passkey (if available) + email code
          setIdentifierSubmitted(true); // Show the manual options UI
          return;
        } else {
          // Show authentication fields after identifier submission
          // This includes password, TOTP, lookup secret, or code fields
          setIdentifierSubmitted(true);  // FIX: Must set this to show the form!
          setShowPasswordField(true);
          console.log('🔐 Setting identifierSubmitted=true and showPasswordField=true for auth fields:', {
            passwordNode: !!passwordNode,
            hasTOTPField,
            hasLookupSecretField,
            hasCodeField,
            hasLinkSent
          });
          
          // If we only have a code submit button but no actual code input field, auto-submit it
          const codeSubmitButton = response.data.ui.nodes.find(n => 
            n.attributes?.name === 'method' && n.attributes?.value === 'code'
          );
          const hasCodeInputField = response.data.ui.nodes.some(n => 
            n.attributes?.name === 'code' && n.attributes?.type === 'text'
          );
          
          // DISABLED: Auto-submit to prevent premature submissions
          if (false && hasCodeField && codeSubmitButton && !hasCodeInputField) {
            console.log('🔐 Auto-submitting code method to get code input field...');
            setTimeout(async () => {
              try {
                const params = new URLSearchParams();
                params.append('identifier', email);
                params.append('method', 'code');
                const csrf = response.data.ui.nodes.find(n => n.attributes.name === 'csrf_token');
                if (csrf) {
                  params.append('csrf_token', csrf.attributes.value);
                }
                
                const submitResponse = await axios.post(actionUrl, params.toString(), {
                  headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                  },
                  withCredentials: true,
                  validateStatus: () => true
                });
                
                if (submitResponse.data?.ui) {
                  console.log('🔐 Code method submitted, updating flow with code input field');
                  setFlowData(submitResponse.data);
                  setIsLoading(false);  // FIX: Clear loading state after flow update!
                  // Keep the identifier and password field states as they are
                }
              } catch (err) {
                console.error('🔐 Error auto-submitting code method:', err);
                setIsLoading(false);  // Also clear loading on error
              }
            }, 100);
          }
        }
        
        // Check for script nodes that need to be executed for WebAuthn
        const scriptNodes = response.data.ui.nodes.filter(node => node.type === 'script');
        scriptNodes.forEach(node => {
          if (node.attributes?.src) {
            console.log('🔐 Loading script from:', node.attributes.src);
            const script = document.createElement('script');
            script.src = node.attributes.src;
            script.async = node.attributes.async || true;
            script.crossOrigin = node.attributes.crossorigin || 'anonymous';
            if (node.attributes.referrerpolicy) {
              script.referrerPolicy = node.attributes.referrerpolicy;
            }
            if (node.attributes.type) {
              script.type = node.attributes.type;
            }
            script.onload = () => {
              console.log('🔐 Script loaded successfully');
              if (node.attributes.onload) {
                try {
                  eval(node.attributes.onload);
                } catch (e) {
                  console.error('🔐 Error executing onload:', e);
                }
              }
            };
            document.body.appendChild(script);
          }
        });
      } else if (response.data && response.data.error) {
        // Handle specific error cases
        console.error('🔐 Error response:', response.data.error);
        if (response.data.error.id === 'missing_credentials' || 
            response.data.error.message?.includes('strategy') ||
            response.data.error.message?.includes('password is missing')) {
          // This might be the "could not find a strategy" error or password required
          console.log('🔐 No strategy found - trying to request passwordless code...');
          setError('Requesting login link via email...');
          
          // Try to request a passwordless code directly
          try {
            const codeParams = new URLSearchParams();
            codeParams.append('identifier', email);
            codeParams.append('method', 'link'); // Request link method
            
            // Get CSRF token again
            const csrf = flowData.ui.nodes.find(n => n.attributes.name === 'csrf_token');
            if (csrf) {
              codeParams.append('csrf_token', csrf.attributes.value);
            }
            
            // Use the same action URL logic
            let linkActionUrl = flowData.ui.action;
            if (!linkActionUrl.startsWith('http')) {
              linkActionUrl = `/.ory${linkActionUrl}`;
            } else if (linkActionUrl.includes('/self-service/')) {
              const url = new URL(linkActionUrl);
              linkActionUrl = `/.ory${url.pathname}${url.search}`;
            }
            
            console.log('🔐 Requesting passwordless link for:', email);
            const codeResponse = await axios.post(linkActionUrl, codeParams.toString(), {
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
              },
              withCredentials: true,
              validateStatus: () => true,
            });
            
            console.log('🔐 Passwordless link response:', codeResponse.status, codeResponse.data);
            
            // Check if we have valid flow data (status 400 is expected for flow updates)
            if (codeResponse.data?.ui) {
              console.log('🔐 Passwordless link requested successfully - flow updated');
              setFlowData(codeResponse.data);
              setIdentifierSubmitted(true);
              setShowPasswordField(true);
              
              // Check if link was sent or code field is available
              const hasLinkSent = codeResponse.data.ui.nodes.some(node => 
                node.group === 'link' || 
                (node.meta?.label?.text && node.meta.label.text.toLowerCase().includes('email'))
              );
              const hasCodeField = codeResponse.data.ui.nodes.some(node => 
                node.attributes?.name === 'code' || node.group === 'code'
              );
              
              if (hasLinkSent) {
                setError('Check your email for the login link');
              } else if (hasCodeField) {
                setError('Check your email for the verification code');
              } else {
                setError('Email sent - check your inbox');
              }
            } else {
              // Fallback to password if available
              console.log('🔐 Passwordless failed, falling back to password field');
              setIdentifierSubmitted(true);
              setShowPasswordField(true);
              if (response.data.ui) {
                setFlowData(response.data);
              }
            }
          } catch (err) {
            console.error('🔐 Error requesting passwordless code:', err);
            // Fallback to password field
            setIdentifierSubmitted(true);
            setShowPasswordField(true);
            if (response.data.ui) {
              setFlowData(response.data);
            }
          }
        } else {
          setError(response.data.error.message || 'An error occurred');
        }
      } else {
        // Unknown response structure
        console.error('🔐 Unexpected response structure:', {
          status: response.status,
          hasData: !!response.data,
          dataKeys: response.data ? Object.keys(response.data) : [],
          data: response.data
        });
        setError('Unexpected response from server. Please try again.');
      }
    } catch (err) {
      console.error('Error submitting identifier:', err);
      setError('Failed to check authentication methods. Please try again.');
    } finally {
      // Keep loading if we're about to make another request for passwordless
      const shouldKeepLoading = flowData && !flowData.ui.nodes.some(n => 
        n.attributes?.name === 'password' || 
        n.attributes?.name === 'totp_code' || 
        n.attributes?.name === 'lookup_secret' || 
        n.attributes?.name === 'code' ||
        n.group === 'code' ||
        n.group === 'link'
      );
      
      if (!shouldKeepLoading) {
        setIsLoading(false);
      }
    }
  };
  
  // Render the login form based on flow data
  const renderLoginForm = () => {
    if (!flowData || !flowData.ui) {
      return (
        <div className="text-center py-6">
          <p>No login data available. Please try again.</p>
          <button
            onClick={startLogin}
            className="mt-4 py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Restart Login
          </button>
        </div>
      );
    }
    
    // Extract form action and method
    const { action, method } = flowData.ui;
    
    // Check if identifier has been submitted
    if (!identifierSubmitted) {
      // Show identifier-first form
      return (
        <form onSubmit={handleIdentifierSubmit} autoComplete="off">
          <div className="mb-4">
            <label className="block text-gray-300 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
              placeholder="you@example.com"
              required
              autoFocus
              autoComplete="username webauthn"
            />
          </div>
          
          <button 
            type="submit" 
            className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
            disabled={isLoading}
          >
            {isLoading ? 'Checking...' : 'Continue'}
          </button>
        </form>
      );
    }
    
    // Handle form submission with validation
    const handlePasswordFormSubmit = async (e) => {
      e.preventDefault(); // Always prevent default form submission
      
      // Race condition protection: prevent multiple submissions
      if (isLoading) {
        console.log('🔐 Submission already in progress, ignoring duplicate');
        return;
      }
      
      setIsLoading(true);
      setError('');
      
      // Check if this is a WebAuthn submission (has webauthn_login field)
      const webauthnInput = e.target.querySelector('input[name="webauthn_login"]');
      const passkeyInput = e.target.querySelector('input[name="passkey_login"]');
      
      if (webauthnInput || passkeyInput) {
        console.log('🔐 WebAuthn form submission detected');
        setIsLoading(false);
        // For WebAuthn, we might need special handling
        return;
      }
      
      // For password submission, check if password field is filled
      const passwordInput = e.target.querySelector('input[name="password"]');
      if (passwordInput && !passwordInput.value) {
        setError('Please enter your password');
        setIsLoading(false);
        return;
      }
      
      // Get all form data
      const formData = new FormData(e.target);
      
      // Convert FormData to URLSearchParams for proper encoding
      const params = new URLSearchParams();
      for (let [key, value] of formData.entries()) {
        params.append(key, value);
      }
      
      // Add method if not present - determine the correct method based on form content
      if (!params.has('method')) {
        // Check if this is a TOTP or lookup secret submission
        if (params.has('totp_code')) {
          params.append('method', 'totp');
          console.log('🔐 Setting method to "totp" for TOTP code submission');
        } else if (params.has('lookup_secret')) {
          params.append('method', 'lookup_secret');
          console.log('🔐 Setting method to "lookup_secret" for recovery code submission');
        } else if (params.has('code')) {
          params.append('method', 'code');
          console.log('🔐 Setting method to "code" for passwordless code submission');
        } else {
          params.append('method', 'password');
          console.log('🔐 Setting method to "password" for password submission');
        }
      }
      
      // CRITICAL FIX: Ensure identifier (email) is included
      // This fixes the issue where email disappears during identifier-first flow
      if (!params.has('identifier') && email) {
        console.log('🔐 Adding missing identifier to form data:', email);
        params.append('identifier', email);
      }
      
      try {
        setIsLoading(true);
        setError('');
        
        // Small delay to prevent race conditions and improve UX
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Use the action URL as-is from the flow (it should already point to the proxy)
        let actionUrl = action;
        
        // If it's a relative URL, make it absolute with the .ory prefix
        if (!actionUrl.startsWith('http')) {
          actionUrl = `/.ory${actionUrl}`;
        } else if (actionUrl.includes('/self-service/')) {
          // If it's an absolute URL pointing to Kratos, convert to proxy URL
          const url = new URL(actionUrl);
          actionUrl = `/.ory${url.pathname}${url.search}`;
        }
        
        console.log('Submitting login form:', { 
          action: actionUrl, 
          method: method.toUpperCase(),
          formData: Object.fromEntries(params),
          emailFromState: email
        });
        
        const response = await axios({
          method: method.toUpperCase(),
          url: actionUrl,
          data: params.toString(),
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
            // REMOVED: 'Accept': 'application/json' - Let Kratos return redirects naturally
          },
          withCredentials: true,
          maxRedirects: 0, // Don't follow redirects automatically
          validateStatus: (status) => status < 500
        });
        
        console.log('Login response:', response.status, response.data);
        
        // Debug: Log all nodes in the response
        if (response.data?.ui?.nodes) {
          console.log('🔐 RESPONSE NODES:', response.data.ui.nodes.map(node => ({
            name: node.attributes?.name,
            type: node.attributes?.type,
            group: node.group,
            required: node.attributes?.required
          })));
        }
        
        console.log('🔐 CRITICAL: Response status:', response.status);
        console.log('🔐 CRITICAL: Response has redirect_browser_to:', !!response.data?.redirect_browser_to);
        console.log('🔐 CRITICAL: Response has continue_with:', !!response.data?.continue_with);
        console.log('🔐 CRITICAL: Response has ui:', !!response.data?.ui);
        
        // Check for successful login
        if (response.status === 200 || response.status === 303) {
          // Check for redirect URL in the correct location
          let redirectUrl = response.data?.redirect_browser_to;
          
          // In newer Kratos versions, redirect info is in continue_with array
          if (!redirectUrl && response.data?.continue_with) {
            const redirectAction = response.data.continue_with.find(
              action => action.action === 'redirect_browser_to'
            );
            redirectUrl = redirectAction?.redirect_browser_to;
          }
          
          if (redirectUrl) {
            console.log('🔐 CRITICAL: About to redirect to:', redirectUrl);
            console.log('🔐 CRITICAL: This may be causing the TOTP login loop!');
            
            // CHECK: If this is a login flow redirect, it might be for TOTP
            if (redirectUrl.includes('/self-service/login')) {
              console.log('🔐 WARNING: Redirecting to new login flow - this breaks TOTP!');
            }
            
            window.location.href = redirectUrl;
          } else {
            // Check session and verify 2FA requirements before navigating
            console.log('🔐 Login successful, checking session and 2FA requirements...');
            await checkSession();
            
            // Check if user needs 2FA setup before allowing dashboard access
            try {
              const response = await axios.get('/api/auth/me', {
                headers: { 'Accept': 'application/json' },
                withCredentials: true
              });
              
              const authMethods = response.data?.user?.auth_methods || {};
              const needsSetup = !(authMethods.totp || authMethods.webauthn);
              
              if (needsSetup) {
                console.log('🔒 User needs 2FA setup, redirecting to security settings');
                navigate('/dashboard/settings/security');
              } else {
                console.log('🔓 2FA requirements met, proceeding to dashboard');
                navigate('/dashboard');
              }
            } catch (error) {
              console.error('Failed to check 2FA status, proceeding to dashboard:', error);
              navigate('/dashboard');
            }
          }
        } else if (response.data?.ui) {
          // Update flow data with new UI - this handles AAL2 transitions (TOTP, etc.)
          console.log('🔐 UI flow updated - checking for AAL2/TOTP requirement...');
          
          // Check if this is an AAL2 step (TOTP, recovery codes, etc.)
          const hasTOTPField = response.data.ui.nodes.some(node => 
            node.attributes?.name === 'totp_code' ||
            node.group === 'totp'
          );
          const hasLookupSecretField = response.data.ui.nodes.some(node => 
            node.attributes?.name === 'lookup_secret' ||
            node.group === 'lookup_secret'
          );
          
          console.log('🔐 DETAILED AAL2 CHECK:', {
            hasTOTPField,
            hasLookupSecretField,
            totpNodes: response.data.ui.nodes.filter(n => n.attributes?.name === 'totp_code' || n.group === 'totp'),
            lookupNodes: response.data.ui.nodes.filter(n => n.attributes?.name === 'lookup_secret' || n.group === 'lookup_secret')
          });
          
          if (hasTOTPField || hasLookupSecretField) {
            console.log('🔐 AAL2 step required:', { hasTOTPField, hasLookupSecretField });
            // Clear any existing error - this is expected behavior for AAL2
            setError('');
            // Ensure password field remains visible for AAL2 step
            setShowPasswordField(true);
            // Show helpful message about second factor
            if (hasTOTPField) {
              console.log('🔐 TOTP code required for second factor authentication');
            }
            if (hasLookupSecretField) {
              console.log('🔐 Recovery code available as alternative');
            }
          } else {
            // Check if there are field-level errors
            const hasFieldErrors = response.data.ui.nodes.some(node => 
              node.messages && node.messages.some(msg => msg.type === 'error')
            );
            
            if (hasFieldErrors) {
              // Field-level errors will be shown in the form
              console.log('🔐 Field-level validation errors present');
            } else if (response.data.ui.messages?.length > 0) {
              // Show form-level messages
              const errorMessage = response.data.ui.messages
                .filter(msg => msg.type === 'error')
                .map(msg => msg.text)
                .join(', ');
              if (errorMessage) {
                setError(errorMessage);
              }
            }
          }
          
          console.log('🔐 Updating flow data. Current state:', {
            identifierSubmitted,
            showPasswordField,
            hasTOTPField,
            hasLookupSecretField
          });
          setFlowData(response.data);
          // Keep user authenticated state - don't reset identifier submission during AAL2
          // This ensures TOTP form remains visible after password submission
          console.log('🔐 Flow data updated. Preserving authentication state.');
        } else if (response.status === 422 && response.data?.error?.id === 'browser_location_change_required') {
          // Handle browser redirect requirement for WebAuthn/TOTP
          console.log('🔐 422 Browser redirect required:', response.data);
          
          let redirectUrl = response.data.redirect_browser_to || 
                           response.data.error?.redirect_browser_to ||
                           (response.data.continue_with && response.data.continue_with.find(action => 
                             action.action === 'redirect_browser_to'
                           )?.redirect_browser_to);
          
          if (redirectUrl) {
            console.log('🔐 Redirecting to:', redirectUrl);
            window.location.href = redirectUrl;
            return;
          }
        } else if (response.status === 422 && response.data?.error?.id === 'browser_location_change_required') {
          // Handle browser redirect requirement for WebAuthn/TOTP
          console.log('🔐 422 Browser redirect required:', response.data);
          
          let redirectUrl = response.data.redirect_browser_to || 
                           response.data.error?.redirect_browser_to ||
                           (response.data.continue_with && response.data.continue_with.find(action => 
                             action.action === 'redirect_browser_to'
                           )?.redirect_browser_to);
          
          if (redirectUrl) {
            console.log('🔐 Redirecting to:', redirectUrl);
            window.location.href = redirectUrl;
            return;
          }
        } else if (response.data?.error) {
          console.log('🔐 Login error:', response.data.error);
          setError(response.data.error.message || 'Login failed');
        }
      } catch (error) {
        console.error('Login submission error:', error);
        
        // Check if this is a 422 browser redirect requirement
        if (error.response && error.response.status === 422) {
          const errorData = error.response.data;
          console.log('🔐 422 Error received:', errorData);
          
          // Check multiple possible locations for redirect URL
          let redirectUrl = errorData.redirect_browser_to || 
                           errorData.error?.redirect_browser_to ||
                           (errorData.continue_with && errorData.continue_with.find(action => 
                             action.action === 'redirect_browser_to'
                           )?.redirect_browser_to);
          
          if (errorData.error && errorData.error.id === 'browser_location_change_required' && redirectUrl) {
            console.log('🔐 Browser redirect required:', redirectUrl);
            // Redirect to the browser flow for authentication ceremony
            window.location.href = redirectUrl;
            return;
          }
        }
        
        setError('An error occurred during login. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <form action={action} method={method.toLowerCase()} autoComplete="off" onSubmit={handlePasswordFormSubmit}>
        {/* Add manual password field if we detected password is required but no password node exists */}
        {/* BUT don't add it if we have a code field (passwordless flow) */}
        {identifierSubmitted && showPasswordField && !flowData.ui.nodes.find(n => n.attributes?.name === 'password') && 
         !flowData.ui.nodes.find(n => n.attributes?.name === 'code' || n.group === 'code') && (
          <div className="mb-4">
            <label className="block text-gray-300 mb-2 font-medium">Password</label>
            <input
              name="password"
              type="password"
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded text-white transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Enter your password"
              required
              autoComplete="current-password"
              autoFocus
            />
          </div>
        )}
        
        {/* Hidden CSRF field */}
        {flowData.ui.nodes.map((node, index) => {
          if (node.attributes.name === 'csrf_token') {
            return (
              <input
                key={index}
                type="hidden"
                name={node.attributes.name}
                value={node.attributes.value}
              />
            );
          }
          
          // Handle passkey/webauthn nodes specially
          if (node.attributes.name?.includes('passkey') || 
              node.attributes.name?.includes('webauthn') || 
              node.attributes.name === 'webauthn_login_trigger' ||
              (node.attributes.name === 'method' && node.attributes.value === 'webauthn') ||
              node.group === 'webauthn') {
            console.log('🔐 Processing passkey node:', node.attributes.name, node.attributes.type, node.meta?.label?.text);
            
            // Only show passkey options after identifier has been submitted
            if (!identifierSubmitted) {
              console.log('🔐 Skipping passkey button - identifier not yet submitted');
              return null;
            }
            
            // Check if this is a passkey login button
            if (node.attributes.type === 'button' || (node.attributes.type === 'submit' && node.attributes.name === 'method' && node.attributes.value === 'webauthn')) {
              // Use improved authentication button text based on capabilities
              let label = node.meta?.label?.text || node.attributes.value;
              
              // Override with user-friendly text based on detected capabilities
              if (authButtonConfig && authButtonConfig.showPasskeyOption) {
                label = authButtonConfig.primary;
              } else if (webAuthnCapabilities) {
                if (webAuthnCapabilities.hasplatformAuthenticator) {
                  label = webAuthnCapabilities.userMessage.includes('Touch ID') ? 'Sign in with Touch ID or Face ID' :
                         webAuthnCapabilities.userMessage.includes('Windows Hello') ? 'Sign in with Windows Hello' :
                         'Sign in with Biometric Authentication';
                } else if (webAuthnCapabilities.hasExternalAuthenticator) {
                  label = 'Sign in with Passkey';
                } else {
                  label = 'Sign in with Passkey';
                }
              } else {
                label = label || 'Sign in with Passkey';
              }
              const onClickHandler = node.attributes.onclick;
              const isSubmitButton = node.attributes.type === 'submit';
              
              console.log('🔐 Rendering passkey button:', {
                name: node.attributes.name,
                label: label,
                onclick: onClickHandler
              });
              
              // Handle both button and submit types
              if (isSubmitButton) {
                // For submit buttons, create a proper form submit button
                return (
                  <button
                    key={index}
                    type="submit"
                    name={node.attributes.name}
                    value={node.attributes.value}
                    onClick={(e) => {
                      e.preventDefault();
                      console.log('🔐 User clicked WebAuthn submit button');
                      sessionStorage.setItem('passkey_attempt', 'true');
                      
                      // Submit the form with the WebAuthn method
                      const form = e.target.closest('form');
                      const formData = new FormData(form);
                      formData.set('method', 'webauthn');
                      // Ensure identifier is included
                      if (email) {
                        formData.set('identifier', email);
                      }
                      
                      // Submit via axios
                      axios.post(form.action, formData, {
                        headers: {
                          'Content-Type': 'application/x-www-form-urlencoded',
                          'Accept': 'application/json'
                        },
                        withCredentials: true,
                        transformRequest: [function (data) {
                          const params = new URLSearchParams();
                          for (const [key, value] of data.entries()) {
                            params.append(key, value);
                          }
                          return params.toString();
                        }]
                      }).then(response => {
                        console.log('🔐 WebAuthn submit response:', response.status, response.data);
                        if (response.status === 200 || response.status === 303) {
                          window.location.href = response.headers.location || '/dashboard';
                        } else if (response.data && response.data.ui) {
                          setFlowData(response.data);
                        }
                      }).catch(error => {
                        console.error('🔐 WebAuthn submit error:', error);
                        
                        // Check if this is a 422 browser redirect requirement
                        if (error.response && error.response.status === 422) {
                          const errorData = error.response.data;
                          if (errorData.error && errorData.error.id === 'browser_location_change_required') {
                            console.log('🔐 Browser redirect required for WebAuthn:', errorData.redirect_browser_to);
                            // Redirect to the browser flow for WebAuthn ceremony
                            window.location.href = errorData.redirect_browser_to;
                            return;
                          }
                        }
                        
                        setError('WebAuthn authentication failed');
                      });
                    }}
                    className="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 flex items-center justify-center mb-4 font-semibold"
                  >
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                      <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
                    </svg>
                    {label}
                  </button>
                );
              } else {
                // For legacy button type with onclick attribute
                return (
                  <div 
                    key={index} 
                    onClick={() => {
                      // Track that user tried to use passkey
                      console.log('🔐 User clicked passkey button');
                      sessionStorage.setItem('passkey_attempt', 'true');
                      // Set a timeout to check if auth succeeded
                      setTimeout(() => {
                        // If we're still on the login page after 5 seconds, something went wrong
                        if (window.location.pathname.includes('login') && 
                            sessionStorage.getItem('passkey_attempt') === 'true') {
                          setShowPasskeyWarning(true);
                          sessionStorage.removeItem('passkey_attempt');
                        }
                      }, 5000);
                    }}
                    dangerouslySetInnerHTML={{
                      __html: `
                        <button
                          type="button"
                          name="${node.attributes.name}"
                          value="${node.attributes.value || ''}"
                          onclick="${onClickHandler || ''}"
                          class="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 flex items-center justify-center mb-4 font-semibold"
                        >
                          <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                            <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
                          </svg>
                          ${label}
                        </button>
                      `
                    }} 
                  />
                );
              }
            } else if (node.attributes.type === 'hidden') {
              // Hidden passkey fields
              console.log('🔐 Rendering hidden passkey field:', node.attributes.name);
              return (
                <input
                  key={index}
                  type="hidden"
                  name={node.attributes.name}
                  value={node.attributes.value}
                />
              );
            }
            return null;
          }
          
          // For identifier field, pre-fill with submitted email
          if (node.attributes.name === 'identifier') {
            return (
              <div key={index} className="mb-4">
                <label className="block text-gray-300 mb-2">Email</label>
                <input
                  name={node.attributes.name}
                  type={node.attributes.type}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                  required={node.attributes.required}
                  value={email}
                  readOnly
                  autoComplete="username webauthn"
                />
              </div>
            );
          }
          
          // Handle hidden inputs for WebAuthn
          if (node.type === 'input' && node.attributes.type === 'hidden') {
            return (
              <input
                key={index}
                type="hidden"
                name={node.attributes.name}
                value={node.attributes.value || ''}
              />
            );
          }
          
          // Skip submit buttons (we'll add our own) but allow other node types
          if (node.attributes?.type === 'submit') {
            return null;
          }
          
          // Skip non-input nodes except scripts
          if (node.type !== 'input' && node.type !== 'script') {
            return null;
          }
          
          // Only show authentication fields after identifier is submitted
          // Exception: Always show TOTP, lookup secret, and code fields when they exist (AAL2 flow or passwordless)
          if (node.attributes.name === 'password' && !identifierSubmitted) {
            return null;
          }
          if ((node.attributes.name === 'totp_code' || node.attributes.name === 'lookup_secret' || node.attributes.name === 'code')) {
            // TOTP, lookup secret, and code fields should always be visible when present
            console.log('🔐 Rendering authentication field:', node.attributes.name);
          }
          
          // Extract label if available and enhance for TOTP
          let label = node.meta?.label?.text || node.attributes.name;
          let helpText = '';
          
          // Enhance TOTP and recovery field labels
          if (node.attributes.name === 'totp_code') {
            label = 'Two-Factor Authentication Code';
            helpText = 'Enter the 6-digit code from your authenticator app';
          } else if (node.attributes.name === 'lookup_secret') {
            label = 'Recovery Code';  
            helpText = 'Enter one of your backup recovery codes';
          }
          
          // Render appropriate input based on type
          return (
            <div key={index} className="mb-4">
              <label className="block text-gray-300 mb-2 font-medium">{label}</label>
              {helpText && (
                <p className="text-sm text-gray-400 mb-2">{helpText}</p>
              )}
              <input
                name={node.attributes.name}
                type={node.attributes.type}
                className={`w-full p-3 bg-gray-700 border border-gray-600 rounded text-white transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 ${
                  node.attributes.name === 'totp_code' 
                    ? 'text-center text-xl tracking-widest font-mono' 
                    : ''
                }`}
                required={node.attributes.required}
                defaultValue={node.attributes.value || ''}
                placeholder={
                  node.attributes.name === 'totp_code' ? '000000' :
                  node.attributes.name === 'lookup_secret' ? 'Enter recovery code' :
                  node.attributes.name === 'code' ? 'Enter verification code' :
                  undefined
                }
                maxLength={node.attributes.name === 'totp_code' ? 6 : node.attributes.name === 'code' ? 6 : undefined}
                minLength={node.attributes.name === 'totp_code' ? 6 : node.attributes.name === 'code' ? 6 : undefined}
                autoComplete={
                  node.attributes.name === 'password' ? 'current-password' : 
                  node.attributes.name === 'totp_code' ? 'one-time-code' :
                  node.attributes.name === 'code' ? 'one-time-code' :
                  'username webauthn'
                }
                autoFocus={node.attributes.name !== 'identifier'}
                // Auto-submit TOTP when 6 digits are entered
                onChange={node.attributes.name === 'totp_code' ? (e) => {
                  if (e.target.value.length === 6 && /^\d{6}$/.test(e.target.value)) {
                    // Auto-submit after a short delay to allow user to see the complete code
                    setTimeout(() => {
                      const form = e.target.closest('form');
                      if (form) {
                        console.log('🔐 Auto-submitting TOTP form');
                        form.dispatchEvent(new Event('submit', { bubbles: true }));
                      }
                    }, 300);
                  }
                } : undefined}
              />
              {/* Show any messages for this field */}
              {node.messages?.map((msg, i) => (
                <p key={i} className={`mt-1 text-sm ${msg.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {msg.text}
                </p>
              ))}
            </div>
          );
        })}
        
        {/* Manual authentication options for all users */}
        {identifierSubmitted && !getWebAuthnButton() && (
          <>
            <div className="space-y-3 mb-4">
              {/* Passkey option - only if user has passkeys */}
              {hasCustomPasskeys && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    console.error('🔐 Custom passkey login is disabled - use Kratos WebAuthn instead');
                    setError('Passkey login temporarily unavailable. Please use password login.');
                  }}
                  className="w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 flex items-center justify-center font-semibold"
                  disabled={isLoading}
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 1.5C8.96243 1.5 6.5 3.96243 6.5 7C6.5 8.30622 7.04822 9.47584 7.91015 10.3378C7.91015 10.3378 12 16.5 12 16.5C12 16.5 16.0899 10.3378 16.0899 10.3378C16.9518 9.47584 17.5 8.30622 17.5 7C17.5 3.96243 15.0376 1.5 12 1.5ZM12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7C14 8.10457 13.1046 9 12 9Z" fill="currentColor"/>
                    <path d="M8 18.5L8.5 20H15.5L16 18.5H8Z" fill="currentColor"/>
                  </svg>
                  {isLoading ? 'Authenticating...' : 'Sign in with Passkey'}
                </button>
              )}
              
              {/* Email code fallback option */}
              <button
                type="button"
                onClick={async (e) => {
                  e.preventDefault();
                  console.log('🔐 User manually requested email code');
                  setError('Requesting verification code...');
                  
                  // Manually trigger email code request
                  try {
                    const codeParams = new URLSearchParams();
                    codeParams.append('identifier', email);
                    codeParams.append('method', 'code');
                    
                    const csrf = flowData?.ui?.nodes?.find(n => n.attributes.name === 'csrf_token');
                    if (csrf) {
                      codeParams.append('csrf_token', csrf.attributes.value);
                    }
                    
                    let codeActionUrl = flowData.ui.action;
                    if (!codeActionUrl.startsWith('http')) {
                      codeActionUrl = `/.ory${codeActionUrl}`;
                    } else if (codeActionUrl.includes('/self-service/')) {
                      const url = new URL(codeActionUrl);
                      codeActionUrl = `/.ory${url.pathname}${url.search}`;
                    }
                    
                    const codeResponse = await axios.post(codeActionUrl, codeParams.toString(), {
                      headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'application/json'
                      },
                      withCredentials: true,
                      validateStatus: () => true,
                    });
                    
                    if (codeResponse.data?.ui) {
                      setFlowData(codeResponse.data);
                      setError('Check your email for the verification code');
                    }
                  } catch (error) {
                    console.error('Manual email code request failed:', error);
                    setError('Failed to send email code. Please try again.');
                  }
                }}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center font-medium"
                disabled={isLoading}
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Send Email Code Instead
              </button>
            </div>
            
            {/* Add escape hatch for stuck state */}
            {isLoading && (
              <button
                type="button"
                onClick={() => {
                  setIsLoading(false);
                  setError('Authentication cancelled');
                }}
                className="mt-2 text-sm text-gray-400 hover:text-gray-300"
              >
                Cancel
              </button>
            )}
            
            {/* Only show separator if we have multiple auth methods - FIXED: Support AAL2 flows */}
            {(() => {
              const hasAnyOtherAuth = showPasswordField || 
                (flowData && flowData.ui.nodes.some(n => 
                  n.attributes?.name === 'totp_code' || 
                  n.attributes?.name === 'lookup_secret' || 
                  n.attributes?.name === 'code'
                ));
              
              return identifierSubmitted && hasAnyOtherAuth && getWebAuthnButton() && (
                <div className="relative mb-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-600"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-gray-800 text-gray-400">Or use alternative method</span>
                  </div>
                </div>
              );
            })()}
            
          </>
        )}
        
        {/* Show AAL2 step indicator when TOTP is required - FIXED: Remove showPasswordField dependency */}
        {identifierSubmitted && flowData && (() => {
          const hasTOTPField = flowData.ui.nodes.some(node => 
            node.attributes?.name === 'totp_code' || node.group === 'totp'
          );
          const hasLookupField = flowData.ui.nodes.some(node => 
            node.attributes?.name === 'lookup_secret' || node.group === 'lookup_secret'
          );
          
          // Show AAL2 indicator for any second factor requirement
          if (hasTOTPField || hasLookupField) {
            console.log('🔐 Showing AAL2 step indicator:', { hasTOTPField, hasLookupField, needsAAL2 });
            return (
              <div className="mb-4 p-3 bg-blue-900/20 border border-blue-600/30 rounded-lg">
                <div className="flex items-center gap-2 text-blue-300">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 8a6 6 0 01-7.743 5.743L10 14l-1 1-1 1H6v2H2v-4l4.257-4.257A6 6 0 1118 8zm-6-4a1 1 0 100 2 2 2 0 012 2 1 1 0 102 0 4 4 0 00-4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium">
                    {needsAAL2 ? 'Additional Authentication Required' : 'Second Factor Required'}
                  </span>
                </div>
                <p className="text-xs text-blue-200 mt-1">
                  {hasTOTPField && hasLookupField 
                    ? 'Use your authenticator app or enter a recovery code below'
                    : hasTOTPField 
                    ? 'Complete sign-in with your authenticator app'
                    : 'Enter one of your backup recovery codes'}
                </p>
              </div>
            );
          }
          return null;
        })()}

        {/* Dynamic submit button based on available authentication methods - FIXED: Support AAL2 without showPasswordField */}
        {identifierSubmitted && flowData && (
          (() => {
            // Check what authentication methods are available in current flow
            const passwordNode = flowData.ui.nodes.find(n => n.attributes?.name === 'password');
            const totpNode = flowData.ui.nodes.find(n => n.attributes?.name === 'totp_code');
            const lookupNode = flowData.ui.nodes.find(n => n.attributes?.name === 'lookup_secret');
            const codeNode = flowData.ui.nodes.find(n => n.attributes?.name === 'code');
            
            // Show submit button if we have any authentication method available OR if showPasswordField is true
            const hasAnyAuthMethod = passwordNode || totpNode || lookupNode || codeNode;
            const shouldShowSubmitButton = showPasswordField || hasAnyAuthMethod;
            
            console.log('🔐 Submit button check:', { 
              showPasswordField, 
              hasAnyAuthMethod,
              shouldShowSubmitButton,
              passwordNode: !!passwordNode,
              totpNode: !!totpNode,
              lookupNode: !!lookupNode,
              codeNode: !!codeNode
            });
            
            if (!shouldShowSubmitButton) {
              return null;
            }
            
            // Determine the primary method and button text
            // PRIORITY ORDER: 1. Code (passwordless), 2. TOTP, 3. Lookup, 4. Password (fallback)
            let method = 'password';
            let buttonText = 'Sign In with Password';
            let buttonClass = 'w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors';
            
            // PRIORITY 1: Passwordless email verification code (highest priority)
            if (codeNode) {
              method = 'code';
              buttonText = 'Verify Email Code';
              buttonClass = 'w-full py-3 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors';
            } 
            // PRIORITY 2: TOTP backup authentication
            else if (totpNode) {
              method = 'totp';
              buttonText = 'Use TOTP Backup';
              buttonClass = 'w-full py-3 px-4 bg-yellow-600 text-black rounded-lg hover:bg-yellow-500 font-medium transition-colors';
            } 
            // PRIORITY 3: Recovery codes
            else if (lookupNode) {
              method = 'lookup_secret';
              buttonText = 'Use Recovery Code';
              buttonClass = 'w-full py-3 px-4 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium transition-colors';
            }
            // PRIORITY 4: Password fallback (legacy accounts only)
            else if (!passwordNode && !codeNode && !totpNode && !lookupNode && showPasswordField) {
              method = 'password';
              buttonText = 'Sign In (Legacy)';
              buttonClass = 'w-full py-3 px-4 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium transition-colors';
            }
            
            return (
              <div>
                <button 
                  type="submit" 
                  name="method" 
                  value={method}
                  className={buttonClass + " mt-4"}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      {method === 'totp' ? 'Verifying...' : method === 'lookup_secret' ? 'Checking...' : method === 'code' ? 'Verifying...' : 'Signing in...'}
                    </div>
                  ) : (
                    buttonText
                  )}
                </button>
                
                {/* Show authentication method priority info */}
                {(codeNode || totpNode || lookupNode) && (
                  <div className="mt-3 text-xs text-gray-400 text-center">
                    {codeNode && "🛡️ Primary: Passwordless email verification"}
                    {!codeNode && totpNode && "🔄 Backup: TOTP authenticator code"}
                    {!codeNode && !totpNode && lookupNode && "🆘 Recovery: Backup codes"}
                  </div>
                )}
              </div>
            );
          })()
        )}
        
        {/* Show form-level messages */}
        {flowData.ui.messages?.map((msg, index) => (
          <div 
            key={index} 
            className={`mt-4 p-3 rounded ${
              msg.type === 'error' ? 'bg-red-900 bg-opacity-30 border border-red-800 text-red-300' : 'bg-green-900 bg-opacity-30 border border-green-800 text-green-300'
            }`}
          >
            {msg.text}
          </div>
        ))}
        
        {/* Show email configuration hints for passwordless */}
        {emailConfig && identifierSubmitted && (
          (() => {
            const hasCodeOrLink = flowData?.ui?.nodes?.some(n => 
              n.attributes?.name === 'code' || n.group === 'code' ||
              n.group === 'link'
            );
            
            if (hasCodeOrLink && emailConfig.mode === 'development') {
              return (
                <div className="mt-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-600 rounded">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div>
                      <p className="text-blue-300 font-medium">Development Mode - Email Sent to Mailpit</p>
                      <p className="text-blue-200 text-sm mt-1">
                        Check your verification code at{' '}
                        <a 
                          href={emailConfig.mailpit_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="underline hover:text-blue-100"
                        >
                          {emailConfig.mailpit_url}
                        </a>
                      </p>
                    </div>
                  </div>
                </div>
              );
            }
            
            return null;
          })()
        )}
      </form>
    );
  };
  
  // If flow hasn't been initialized yet, show loading
  if (!flowInitialized && isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        <div className="relative z-10 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <p className="text-gray-300">Initializing login...</p>
        </div>
      </div>
    );
  }
  
  // If no flow data after initialization, show the simple UI
  if (!flowData && flowInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
        
        {/* Animated background shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        </div>

        {/* Glass card container */}
        <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
          <div className="text-center mb-6">
            <img src="/sting-logo.png" alt="Hive Logo" className="w-24 h-24 mx-auto mb-2" />
            <h2 className="text-2xl font-bold">
              {needsAAL2 ? 'Complete Two-Factor Authentication' : 'Sign in to Hive'}
            </h2>
            {needsAAL2 && (
              <p className="text-sm text-blue-300 mt-2">
                Additional authentication required for secure access
              </p>
            )}
          </div>

          {/* Admin Notice */}
          <AdminNotice />
          
          {error && (
            <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded text-red-300">
              {error}
            </div>
          )}
          
          {/* Removed custom passkey button - using Kratos identifier-first flow */}
          
          <button
            onClick={startLogin}
            className="mb-4 w-full py-3 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Sign In with Email
          </button>
          
          <div className="mt-6 text-center">
            <p className="text-gray-400">
              Don't have an account?{" "}
              <button 
                onClick={startRegistration}
                className="text-blue-400 hover:underline"
              >
                Sign up
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // Render full login screen with flow data
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <PasskeyMigrationWarning 
        show={showPasskeyWarning} 
        onClose={() => setShowPasskeyWarning(false)} 
      />
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#161922] via-[#1a1f2e] to-[#161922]"></div>
      
      {/* Animated background shapes */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-yellow-500/10 blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-500/10 blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      {/* Glass card container */}
      <div className="relative z-10 w-full max-w-md p-8 sting-glass-card sting-glass-strong sting-elevation-floating animate-fade-in-up">
        <div className="text-center mb-6">
          <img src="/sting-logo.png" alt="STING Logo" className="w-24 h-24 mx-auto mb-2" />
          <h2 className="text-2xl font-bold">
            {needsAAL2 ? 'Complete Two-Factor Authentication' : 'Sign in to STING'}
          </h2>
          {needsAAL2 && (
            <p className="text-sm text-blue-300 mt-2">
              Additional authentication required for secure access
            </p>
          )}
        </div>

        {/* Admin Notice */}
        <AdminNotice />
        
        {isLoading ? (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
            <p>Loading login form...</p>
          </div>
        ) : error ? (
          <div className="p-3 bg-red-900 bg-opacity-30 border border-red-800 rounded mb-6">
            <p className="text-red-300">{error}</p>
            <div className="mt-4">
              <button
                onClick={startLogin}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Passkey button removed - Kratos requires email first for WebAuthn */}
            
            {/* Only show separator after identifier is submitted and there are multiple auth methods - FIXED: Support AAL2 flows */}
            {(() => {
              const hasAnyOtherAuth = showPasswordField || 
                (flowData && flowData.ui.nodes.some(n => 
                  n.attributes?.name === 'totp_code' || 
                  n.attributes?.name === 'lookup_secret' || 
                  n.attributes?.name === 'code'
                ));
              
              return identifierSubmitted && hasAnyOtherAuth && getWebAuthnButton() && (
                <div className="relative mb-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-600"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-gray-800 text-gray-400">Or use alternative method</span>
                  </div>
                </div>
              );
            })()}
            
            {renderLoginForm()}
          </>
        )}
        
        <div className="mt-6 text-center text-sm text-gray-400">
          <div className="mb-2">
            <a href={`${kratosUrl}/self-service/recovery/browser`} className="text-blue-400 hover:underline">
              Forgot your password?
            </a>
          </div>
          <p>
            Don't have an account?{' '}
            <button 
              onClick={startRegistration}
              className="text-yellow-400 hover:underline"
            >
              Register
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default EnhancedKratosLogin;