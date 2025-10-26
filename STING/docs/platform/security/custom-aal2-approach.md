# Custom AAL2 Approach for Passwordless WebAuthn

## Problem
Kratos doesn't support passwordless WebAuthn at AAL2 level, but biometric authenticators should qualify for AAL2.

## Custom Solution Architecture

### Backend Enhancement
```python
# app/utils/enhanced_aal2_check.py

def check_webauthn_aal2_eligibility(session_data):
    """
    Custom logic to determine if WebAuthn authentication qualifies for AAL2
    based on authenticator characteristics
    """
    
    # Check if user used WebAuthn with user verification
    webauthn_methods = [m for m in session_data.get('authentication_methods', []) 
                       if m.get('method') == 'webauthn']
    
    for method in webauthn_methods:
        # Check for UV flag or biometric indicators
        if method.get('user_verified') or method.get('biometric_used'):
            return True
    
    # Check device characteristics
    credentials = session_data.get('identity', {}).get('credentials', {})
    if 'webauthn' in credentials:
        for cred in credentials['webauthn']['credentials']:
            # Platform authenticators (built-in) often support biometrics
            if cred.get('authenticator_attachment') == 'platform':
                return True
            
            # Check for specific biometric authenticator types
            if cred.get('authenticator_metadata', {}).get('biometric_capable'):
                return True
    
    return False

def get_effective_aal(kratos_session):
    """
    Determine effective AAL level considering custom WebAuthn AAL2 logic
    """
    base_aal = kratos_session.get('authenticator_assurance_level', 'aal1')
    
    # If already AAL2, return as-is
    if base_aal == 'aal2':
        return 'aal2'
    
    # Check if WebAuthn qualifies for AAL2
    if check_webauthn_aal2_eligibility(kratos_session):
        return 'aal2'
    
    return base_aal
```

### Frontend Integration
```javascript
// Enhanced auth provider with custom AAL2 logic
const checkEffectiveAAL = async () => {
  const response = await axios.get('/api/auth/effective-aal');
  return response.data.aal; // 'aal1' or 'aal2'
};
```

### Implementation Steps
1. Add WebAuthn credential analysis to session endpoints
2. Implement UV flag detection in WebAuthn responses  
3. Update AAL2 protected routes to use custom logic
4. Maintain Kratos compatibility for other flows