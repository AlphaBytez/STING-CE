import { useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthProvider';

export function useKratosFlow() {
  const { setFlowData, setError } = useAuth();
  
  // Initialize Kratos flow for authentication (regular flows only)
  const initializeFlow = useCallback(async (isAAL2 = false) => {
    try {
      // FIXED: Don't create AAL2 flows directly as they interfere with natural Kratos step-up
      // AAL2 flows should only be created by Kratos itself via proper redirects
      if (isAAL2) {
        console.warn('🔐 AAL2 flow creation blocked - let Kratos handle AAL2 step-up naturally');
        throw new Error('Direct AAL2 flow creation not supported - use natural Kratos step-up flow');
      }
      
      console.log('🔐 Initializing regular Kratos flow (AAL1)');
      
      // Only support regular login flows - let Kratos handle AAL2 step-up via redirects
      const flowUrl = `/self-service/login/browser?refresh=true`;
        
      const response = await axios.get(flowUrl, {
        headers: { 
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        withCredentials: true
      });
      
      setFlowData(response.data);
      console.log('🔐 Regular Kratos flow initialized:', response.data.id);
      return response.data;
    } catch (error) {
      console.error('🔐 Failed to initialize Kratos flow:', error);
      setError('Failed to initialize authentication. Please refresh and try again.');
      throw error;
    }
  }, [setFlowData, setError]);
  
  // Submit form data to Kratos flow
  const submitToFlow = useCallback(async (flowData, formData, actionUrl = null) => {
    try {
      // 🔍 DEBUG: Log every submission attempt in detail
      console.log('🔍 useKratosFlow submitToFlow called:', {
        hasFlowData: !!flowData,
        flowId: flowData?.id,
        flowState: flowData?.state,
        formDataType: typeof formData,
        formDataLength: formData?.length || formData?.toString()?.length,
        actionUrl,
        timestamp: new Date().toISOString(),
        stackTrace: new Error().stack
      });
      
      if (!flowData) {
        console.error('❌ No flow data available for submission');
        throw new Error('No flow data available');
      }
      
      // Validate that we have actual form data
      if (!formData || (typeof formData === 'string' && formData.trim() === '')) {
        console.error('❌ Empty or invalid form data:', formData);
        throw new Error('No form data provided');
      }
      
      // Use provided action URL or extract from flow
      const submitUrl = actionUrl || flowData.ui.action.replace(/https?:\/\/[^\/]+/, '');
      
      console.log('🔐 Submitting to Kratos flow:', submitUrl);
      
      const response = await axios.post(
        submitUrl,
        formData,
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true,
          validateStatus: () => true
        }
      );
      
      // Log response with context about whether it's expected
      const isExpectedFlowState = response.status === 400 && 
                                 (response.data?.state === 'choose_method' || 
                                  response.data?.state === 'sent_email');
      
      console.log(isExpectedFlowState ? '✅' : '🔐', 
                 'Flow submission response:', 
                 response.status, 
                 response.data?.state,
                 isExpectedFlowState ? '(Expected flow state)' : '');
      
      // Handle 422 responses (AAL2 required) gracefully
      if (response.status === 422) {
        console.log('🔐 422 response - checking for AAL2 requirement:', response.data);
        console.log('🔐 Full 422 response details:', JSON.stringify(response.data, null, 2));
        
        // Check if this is an AAL2 requirement
        const isAAL2Required = response.data?.error?.id === 'session_aal2_required' ||
                              response.data?.redirect_browser_to?.includes('aal=aal2') ||
                              response.data?.redirect_browser_to?.includes('aal2');
        
        if (isAAL2Required) {
          console.log('🔐 AAL2 requirement detected in 422 response');
          return {
            ...response,
            isAAL2Required: true
          };
        }
      }
      
      return response;
    } catch (error) {
      console.error('🔐 Flow submission failed:', error);
      throw error;
    }
  }, []);
  
  // Process continue_with actions from Kratos response
  const processContinueWith = useCallback(async (continueWith) => {
    if (!continueWith || !Array.isArray(continueWith) || continueWith.length === 0) {
      console.log('ℹ️ No continue_with actions to process');
      return false;
    }
    
    console.log('🔄 Processing continue_with actions:', continueWith);
    console.log('🔍 Action details:', JSON.stringify(continueWith, null, 2));
    
    for (const action of continueWith) {
      if (action.action === 'redirect_browser_to') {
        console.log('🔐 Found redirect_browser_to action, navigating to:', action.redirect_browser_to);
        // Mark that we just successfully authenticated to prevent redirect loops
        sessionStorage.setItem('sting_recent_auth', Date.now().toString());
        window.location.href = action.redirect_browser_to;
        return true;
      } else if (action.action === 'set_ory_session_token') {
        console.log('🔐 Found set_ory_session_token action, completing session...');
        
        try {
          // Use only Kratos-provided redirect URL, no STING fallbacks
          if (!action.redirect_browser_to) {
            console.log('⚠️ No redirect URL provided in continue_with action, skipping');
            continue;
          }
          
          const sessionUrl = action.redirect_browser_to;
          const sessionResponse = await fetch(sessionUrl, {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            }
          });
          
          console.log('🔐 Session completion response:', sessionResponse.status);
          
          if (sessionResponse.ok) {
            const sessionData = await sessionResponse.json();
            console.log('✅ Kratos session established:', {
              identity: sessionData.identity?.id,
              active: sessionData.active,
              aal: sessionData.authenticator_assurance_level
            });
            return true;
          } else {
            console.warn('⚠️ Session completion failed:', sessionResponse.status);
          }
        } catch (sessionError) {
          console.error('❌ Error completing session:', sessionError);
        }
      }
    }
    
    return false;
  }, []);
  
  // Extract CSRF token from flow
  const extractCSRFToken = useCallback((flowData) => {
    if (!flowData?.ui?.nodes) return null;
    
    const csrfNode = flowData.ui.nodes.find(
      n => n.attributes?.name === 'csrf_token'
    );
    
    return csrfNode?.attributes?.value || null;
  }, []);
  
  // Check if flow has specific method available
  const hasMethod = useCallback((flowData, method) => {
    if (!flowData?.ui?.nodes) return false;
    
    return flowData.ui.nodes.some(
      n => n.attributes?.name === 'method' && n.attributes?.value === method
    );
  }, []);
  
  return {
    initializeFlow,
    submitToFlow,
    processContinueWith,
    extractCSRFToken,
    hasMethod
  };
}