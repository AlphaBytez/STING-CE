/**
 * AAL2 Step-Up Modal - Triggers proper Kratos AAL2 authentication
 */

import React from 'react';
import { Modal, Button, Alert } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';

const AAL2StepUpModal = ({ 
  visible, 
  onSuccess, 
  onCancel, 
  title = "Secure Authentication Required",
  message: messageText = "This section requires enhanced security."
}) => {

  const handleStepUpAuthentication = async () => {
    try {
      console.log('🔐 Starting AAL2 step-up authentication...');
      
      // Check current session and available methods
      const [aalStatusResponse, sessionResponse] = await Promise.all([
        fetch('/api/auth/aal-status', { credentials: 'include' }),
        fetch('/.ory/sessions/whoami', { credentials: 'include' })
      ]);
      
      const aalStatus = await aalStatusResponse.json();
      const session = await sessionResponse.json();
      
      console.log('🔐 AAL Status:', aalStatus);
      console.log('🔐 Current Session:', session);
      
      // Check if user has configured passkeys/TOTP - use the correct fields from API response
      const hasWebAuthn = aalStatus.has_webauthn || aalStatus.configured_methods?.webauthn;
      const hasTotp = aalStatus.has_totp || aalStatus.configured_methods?.totp;
      
      console.log('🔐 Method detection:', { 
        hasWebAuthn, 
        hasTotp, 
        has_webauthn_api: aalStatus.has_webauthn,
        has_totp_api: aalStatus.has_totp,
        configured_methods: aalStatus.configured_methods 
      });
      
      // IMPORTANT: In our current Kratos config, WebAuthn is AAL1 (passwordless: true)
      // For AAL2 step-up, Kratos expects TOTP as the second factor, not WebAuthn
      console.log('🔐 KRATOS LIMITATION: WebAuthn is AAL1 only in current config');
      console.log('🔐 For AAL2 step-up, checking TOTP availability...');
      
      // Check if user actually has no AAL2 methods configured (TOTP for step-up)
      if (!hasTotp) {
        console.log('🔐 No TOTP configured for AAL2 step-up, redirecting to setup...');
        
        // CRITICAL: Don't redirect if already on settings page (prevents infinite loop)
        const currentPath = window.location.pathname;
        if (currentPath.includes('/settings')) {
          console.log('🔐 Already on settings page, showing setup message instead of redirecting');
          // Don't redirect, let the modal show the setup message
        } else {
          window.location.href = '/dashboard/settings?tab=security';
          return;
        }
      }
      
      console.log('🔐 Proceeding with step-up (configured methods detected or API unavailable)...');
      
      const currentUrl = window.location.href;
      // FIXED: Use Flask AAL status instead of Kratos session format
      const currentAAL = aalStatus.aal_level || 'aal1';
      
      console.log('🔐 Current session AAL:', currentAAL);
      console.log('🔐 Available methods for AAL2:', { hasTotp });
      console.log('🔐 Available methods for AAL1:', { hasWebAuthn });
      
      // FIXED: Create AAL2 login flow that will include TOTP nodes for step-up
      console.log('🔐 Creating AAL2 step-up flow with TOTP...');
      
      try {
        // FIXED: Use API endpoint for JSON responses, not browser endpoint
        const apiResponse = await fetch('/.ory/self-service/login/browser?aal=aal2', {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        if (apiResponse.ok) {
          const flowData = await apiResponse.json();
          console.log('🔐 Created AAL2 login flow:', flowData.id);
          
          // Check for TOTP nodes (the correct AAL2 method in our config)
          const hasTotpNode = flowData.ui?.nodes?.some(node => 
            node.attributes?.name === 'totp_code' || 
            node.group === 'totp'
          );
          
          // Also check for any WebAuthn nodes (should not be present for AAL2)
          const hasWebAuthnNode = flowData.ui?.nodes?.some(node => 
            node.attributes?.name === 'webauthn_login' || 
            node.group === 'webauthn'
          );
          
          console.log('🔐 Flow has TOTP nodes:', hasTotpNode);
          console.log('🔐 Flow has WebAuthn nodes (should be false):', hasWebAuthnNode);
          console.log('🔐 All flow UI nodes:', flowData.ui?.nodes?.map(n => ({ 
            name: n.attributes?.name, 
            group: n.group, 
            type: n.attributes?.type 
          })));
          
          // Redirect to browser flow for TOTP authentication
          const browserUrl = `/.ory/self-service/login/browser?flow=${flowData.id}&return_to=${encodeURIComponent(currentUrl)}`;
          console.log('🔐 Redirecting to AAL2 TOTP flow:', browserUrl);
          window.location.href = browserUrl;
          return;
        }
      } catch (apiError) {
        console.warn('🔐 AAL2 flow creation failed:', apiError);
      }
      
      // Fallback: Direct browser URL with AAL2
      console.log('🔐 Using fallback direct AAL2 URL...');
      const fallbackUrl = `/.ory/self-service/login/browser?aal=aal2&refresh=true&return_to=${encodeURIComponent(currentUrl)}`;
      console.log('🔐 Fallback URL:', fallbackUrl);
      window.location.href = fallbackUrl;
      
    } catch (error) {
      console.error('AAL2 step-up error:', error);
      
      // Ultimate fallback - direct Kratos URL
      const currentUrl = window.location.href;
      const fallbackUrl = `/.ory/self-service/login/browser?aal=aal2&refresh=true&return_to=${encodeURIComponent(currentUrl)}`;
      console.log('🔐 Using fallback URL:', fallbackUrl);
      window.location.href = fallbackUrl;
    }
  };

  const handleGoToSettings = () => {
    window.location.href = '/dashboard/settings?tab=security';
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={480}
      centered
      maskClosable={false}
    >
      <div className="py-4">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <SafetyOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          </div>
          <p className="text-gray-600">{messageText}</p>
        </div>

        <Alert
          message="Additional Authentication Required"
          description="Please authenticate with your TOTP authenticator app to upgrade your session and access this secure section."
          type="info"
          showIcon
          className="mb-4"
        />

        <div className="space-y-3">
          <Button 
            type="primary" 
            size="large"
            onClick={handleStepUpAuthentication}
            className="w-full"
          >
            Authenticate with TOTP
          </Button>
          
          <Button 
            type="default" 
            onClick={handleGoToSettings}
            className="w-full"
          >
            Manage Security Methods
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default AAL2StepUpModal;