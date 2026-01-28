/**
 * Kratos Settings Flow Hook
 * 
 * Handles WebAuthn and TOTP registration through Kratos native settings flows
 * Replaces custom WebAuthn APIs for enrollment
 */

import { useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthProvider';

export const useKratosSettings = () => {
  const { setError, setSuccessMessage, clearMessages } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  // Initialize Kratos settings flow
  const initializeSettingsFlow = useCallback(async () => {
    try {
      console.log('🔧 Initializing Kratos settings flow...');
      
      const response = await fetch('/.ory/self-service/settings/browser', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Settings flow failed: ${response.status}`);
      }
      
      const flowData = await response.json();
      console.log('🔧 Settings flow initialized:', flowData.id);
      
      return flowData;
    } catch (error) {
      console.error('🔧 Error initializing settings flow:', error);
      throw error;
    }
  }, []);

  // Submit to settings flow
  const submitSettingsFlow = useCallback(async (flowData, formData) => {
    try {
      console.log('🔧 Submitting to settings flow:', flowData.id);
      
      const response = await fetch(flowData.ui.action, {
        method: flowData.ui.method || 'POST',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });
      
      const responseData = await response.json();
      
      return {
        status: response.status,
        data: responseData
      };
    } catch (error) {
      console.error('🔧 Error submitting settings flow:', error);
      throw error;
    }
  }, []);

  // Extract CSRF token from settings flow
  const extractCSRFToken = useCallback((flowData) => {
    const csrfNode = flowData?.ui?.nodes?.find(
      node => node.attributes?.name === 'csrf_token'
    );
    return csrfNode?.attributes?.value || '';
  }, []);

  // Register WebAuthn credentials through Kratos
  const registerWebAuthn = useCallback(async () => {
    setIsLoading(true);
    clearMessages();
    
    try {
      console.log('🔧 Starting Kratos WebAuthn registration...');
      
      // Step 1: Initialize settings flow
      const flow = await initializeSettingsFlow();
      
      // Step 2: Check for WebAuthn method
      const webauthnNodes = flow.ui.nodes.filter(n => n.group === 'webauthn');
      console.log('🔧 WebAuthn nodes found:', webauthnNodes.length);
      
      if (webauthnNodes.length === 0) {
        throw new Error('WebAuthn not available in settings flow');
      }
      
      // Step 3: Find the WebAuthn register button/trigger
      const registerTrigger = webauthnNodes.find(n => 
        n.attributes?.name === 'webauthn_register_trigger' ||
        n.attributes?.name === 'webauthn_register' ||
        n.type === 'input' && n.attributes?.type === 'submit'
      );
      
      if (!registerTrigger) {
        throw new Error('WebAuthn register trigger not found');
      }
      
      // Step 4: Submit form to trigger WebAuthn registration
      const formData = new URLSearchParams();
      formData.append('method', 'webauthn');
      
      const csrfToken = extractCSRFToken(flow);
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      // Add the trigger field
      formData.append(registerTrigger.attributes.name, registerTrigger.attributes.value || '');
      
      console.log('🔧 Submitting WebAuthn registration trigger...');
      const response = await submitSettingsFlow(flow, formData.toString());
      
      // Step 5: Handle WebAuthn challenge
      if (response.data?.ui) {
        const updatedFlow = response.data;
        
        // Look for WebAuthn script and options
        const scriptNode = updatedFlow.ui.nodes.find(n => 
          n.type === 'script' && n.group === 'webauthn'
        );
        
        const optionsNode = updatedFlow.ui.nodes.find(n =>
          n.attributes?.name === 'webauthn_register' && 
          n.attributes?.type === 'hidden'
        );
        
        if (scriptNode && optionsNode) {
          console.log('🔧 WebAuthn challenge received, loading script...');
          
          // Load WebAuthn script if needed
          await loadWebAuthnScript(scriptNode.attributes.src);
          
          // Parse WebAuthn options
          const webauthnOptions = JSON.parse(optionsNode.attributes.value);
          console.log('🔧 WebAuthn options:', webauthnOptions);
          
          // Trigger WebAuthn registration
          if (window.oryWebAuthnRegistration) {
            console.log('🔧 Triggering Kratos WebAuthn registration...');
            const result = await window.oryWebAuthnRegistration(webauthnOptions);
            console.log('🔧 WebAuthn registration result:', result);
            
            setSuccessMessage('WebAuthn credential registered successfully!');
            return { success: true, result };
          } else {
            throw new Error('WebAuthn registration script not loaded');
          }
        } else {
          console.log('🔧 Response data:', response.data);
          throw new Error('WebAuthn challenge not found in response');
        }
      } else if (response.status === 200) {
        // Success without additional challenge
        setSuccessMessage('WebAuthn credential registered successfully!');
        return { success: true };
      } else {
        throw new Error(`Settings flow failed: ${response.status}`);
      }
    } catch (error) {
      console.error('🔧 WebAuthn registration failed:', error);
      setError(`WebAuthn registration failed: ${error.message}`);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [initializeSettingsFlow, submitSettingsFlow, extractCSRFToken, setError, setSuccessMessage, clearMessages]);

  // Register TOTP through Kratos
  const registerTOTP = useCallback(async () => {
    setIsLoading(true);
    clearMessages();
    
    try {
      console.log('🔧 Starting Kratos TOTP registration...');
      
      // Step 1: Initialize settings flow
      const flow = await initializeSettingsFlow();
      
      // Step 2: Submit TOTP method
      const formData = new URLSearchParams();
      formData.append('method', 'totp');
      
      const csrfToken = extractCSRFToken(flow);
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      console.log('🔧 Requesting TOTP setup...');
      const response = await submitSettingsFlow(flow, formData.toString());
      
      if (response.data?.ui) {
        const updatedFlow = response.data;
        
        // Look for TOTP QR code and secret
        const qrNode = updatedFlow.ui.nodes.find(n =>
          n.attributes?.name === 'totp_qr' || n.group === 'totp'
        );
        
        const secretNode = updatedFlow.ui.nodes.find(n =>
          n.attributes?.name === 'totp_secret_key'
        );
        
        if (qrNode || secretNode) {
          console.log('🔧 TOTP setup data received');
          
          const totpData = {
            qr_code: qrNode?.attributes?.src,
            secret: secretNode?.attributes?.value,
            flow: updatedFlow
          };
          
          return { success: true, totpData };
        } else {
          throw new Error('TOTP setup data not found in response');
        }
      } else if (response.status === 200) {
        // Already configured
        setSuccessMessage('TOTP is already configured!');
        return { success: true, alreadyConfigured: true };
      } else {
        throw new Error(`TOTP registration failed: ${response.status}`);
      }
    } catch (error) {
      console.error('🔧 TOTP registration failed:', error);
      setError(`TOTP registration failed: ${error.message}`);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [initializeSettingsFlow, submitSettingsFlow, extractCSRFToken, setError, setSuccessMessage, clearMessages]);

  // Verify TOTP code during registration
  const verifyTOTPCode = useCallback(async (flowData, totpCode) => {
    setIsLoading(true);
    
    try {
      console.log('🔧 Verifying TOTP code...');
      
      const formData = new URLSearchParams();
      formData.append('method', 'totp');
      formData.append('totp_code', totpCode);
      
      const csrfToken = extractCSRFToken(flowData);
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      const response = await submitSettingsFlow(flowData, formData.toString());
      
      if (response.status === 200 || response.data?.state === 'success') {
        setSuccessMessage('TOTP configured successfully!');
        return { success: true };
      } else {
        const errorMsg = response.data?.ui?.messages?.find(m => m.type === 'error')?.text;
        throw new Error(errorMsg || 'Invalid TOTP code');
      }
    } catch (error) {
      console.error('🔧 TOTP verification failed:', error);
      setError(`TOTP verification failed: ${error.message}`);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [submitSettingsFlow, extractCSRFToken, setError, setSuccessMessage]);

  // Get current settings (check what's already configured)
  const getCurrentSettings = useCallback(async () => {
    try {
      console.log('🔧 Getting current settings...');
      
      const flow = await initializeSettingsFlow();
      
      // Parse existing credentials from flow
      const webauthnNodes = flow.ui.nodes.filter(n => n.group === 'webauthn');
      const totpNodes = flow.ui.nodes.filter(n => n.group === 'totp');
      
      const hasWebAuthn = webauthnNodes.some(n => 
        n.attributes?.name === 'webauthn_remove' && n.attributes?.type === 'submit'
      );
      
      const hasTotp = totpNodes.some(n => 
        n.attributes?.name === 'totp_unlink' && n.attributes?.type === 'submit'
      );
      
      return {
        success: true,
        credentials: {
          webauthn: hasWebAuthn,
          totp: hasTotp
        },
        flow
      };
    } catch (error) {
      console.error('🔧 Error getting current settings:', error);
      return { success: false, error: error.message };
    }
  }, [initializeSettingsFlow]);

  return {
    isLoading,
    initializeSettingsFlow,
    submitSettingsFlow,
    extractCSRFToken,
    registerWebAuthn,
    registerTOTP,
    verifyTOTPCode,
    getCurrentSettings
  };
};

// Helper function to load WebAuthn script
const loadWebAuthnScript = async (scriptSrc) => {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${scriptSrc}"]`);
    if (existing) {
      resolve();
      return;
    }
    
    const script = document.createElement('script');
    script.src = scriptSrc;
    script.async = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

export default useKratosSettings;