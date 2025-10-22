# Kratos WebAuthn Implementation Guide

## Understanding Kratos WebAuthn Flow

### How Kratos WebAuthn Works
1. User must first have a password-based identity
2. WebAuthn is added as a second factor/method
3. During login, Kratos checks available methods for the identifier
4. If WebAuthn credentials exist, it offers WebAuthn authentication

### Key Concepts

#### 1. Login Flow
```javascript
// Step 1: Initialize login flow
const { data: flow } = await kratosApi.get('/self-service/login/browser');

// Step 2: Submit identifier
const response = await kratosApi.post(`/self-service/login?flow=${flow.id}`, {
  method: 'password',
  identifier: 'user@example.com'
});

// Step 3: If WebAuthn available, flow.ui will contain WebAuthn nodes
// Look for nodes with group='webauthn' or type='script'
```

#### 2. WebAuthn Script Integration
Kratos provides a JavaScript file that handles WebAuthn browser APIs:
```javascript
// Find the script node
const webauthnScript = flow.ui.nodes.find(node => 
  node.type === 'script' && node.group === 'webauthn'
);

// Load and execute it
if (webauthnScript?.attributes?.src) {
  const script = document.createElement('script');
  script.src = webauthnScript.attributes.src;
  document.body.appendChild(script);
}
```

#### 3. Settings Flow (Adding WebAuthn)
```javascript
// Initialize settings flow
const { data: flow } = await kratosApi.get('/self-service/settings/browser');

// Submit to add WebAuthn
await kratosApi.post(`/self-service/settings?flow=${flow.id}`, {
  method: 'webauthn',
  webauthn_register: true,
  webauthn_register_displayname: 'My Device'
});
```

## Implementation Patterns

### Pattern 1: Identifier-First Login
```javascript
const IdentifierFirstLogin = () => {
  const [stage, setStage] = useState('identifier'); // identifier | webauthn | password
  
  const handleIdentifierSubmit = async (email) => {
    // Check what methods are available for this user
    const methods = await checkAvailableMethods(email);
    
    if (methods.includes('webauthn')) {
      setStage('webauthn');
      // Show passkey button
    } else {
      setStage('password');
      // Show password form
    }
  };
};
```

### Pattern 2: Progressive Enhancement
```javascript
const LoginForm = () => {
  // Always show email field
  // After email entered:
  // 1. Check if user has WebAuthn
  // 2. If yes, show big "Sign in with Passkey" button
  // 3. Always show small "Use password instead" link
};
```

### Pattern 3: Registration with Immediate WebAuthn
```javascript
const handleRegistrationSuccess = async (session) => {
  // After successful password registration
  if (window.PublicKeyCredential) {
    // Immediately redirect to settings with WebAuthn setup
    navigate('/settings/security?setup=webauthn&first=true');
  } else {
    navigate('/dashboard');
  }
};
```

## UI/UX Recommendations

### Login Page Design
```
┌─────────────────────────────────┐
│          STING Logo             │
│                                 │
│  ┌─────────────────────────┐   │
│  │  email@example.com      │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │   🔐 Sign in with       │   │
│  │      Passkey            │   │
│  └─────────────────────────┘   │
│                                 │
│  Use password instead ▼         │
└─────────────────────────────────┘
```

### Registration Flow
```
1. Email + Password → 
2. "Secure your account with a passkey" (immediate prompt) →
3. WebAuthn setup →
4. Dashboard
```

### Settings Page
```
Security Settings
├── Password
│   └── Change Password
├── Passkeys
│   ├── MacBook Pro (Added: Jan 1, 2024)
│   ├── iPhone (Added: Jan 15, 2024)
│   └── [+ Add New Passkey]
└── Sessions
    └── Active Sessions
```

## Code Examples

### 1. Check Available Methods
```javascript
const checkUserMethods = async (email) => {
  try {
    // Initialize flow and submit identifier
    const { data: flow } = await kratosApi.get('/self-service/login/browser');
    const response = await kratosApi.post(`/self-service/login?flow=${flow.id}`, {
      method: 'password',
      identifier: email,
      password: '' // Empty to just check methods
    });
    
    // Check UI nodes for available methods
    const hasWebAuthn = response.data.ui.nodes.some(node => 
      node.group === 'webauthn'
    );
    
    return { hasWebAuthn, flow: response.data };
  } catch (error) {
    // User needs password
    return { hasWebAuthn: false };
  }
};
```

### 2. Execute WebAuthn Authentication
```javascript
const executeWebAuthn = async (flow) => {
  // Option 1: Use Kratos script
  const scriptNode = flow.ui.nodes.find(n => 
    n.type === 'script' && n.group === 'webauthn'
  );
  
  if (scriptNode) {
    // This will handle everything including redirect
    window.__ory_kratos_login_flow = flow;
    loadScript(scriptNode.attributes.src);
  }
  
  // Option 2: Manual submission
  const response = await kratosApi.post(`/self-service/login?flow=${flow.id}`, {
    method: 'webauthn'
  });
};
```

### 3. Add WebAuthn in Settings
```javascript
const addPasskey = async () => {
  const { data: flow } = await kratosApi.get('/self-service/settings/browser');
  
  // Find CSRF token
  const csrfToken = flow.ui.nodes.find(n => 
    n.attributes.name === 'csrf_token'
  )?.attributes?.value;
  
  // Submit WebAuthn registration
  const response = await kratosApi.post(`/self-service/settings?flow=${flow.id}`, {
    method: 'webauthn',
    csrf_token: csrfToken,
    webauthn_register: true,
    webauthn_register_displayname: getDeviceName()
  });
};
```

## Testing Checklist

- [ ] New user can register with email/password
- [ ] After registration, user is prompted to add passkey
- [ ] Returning user with passkey sees passkey option first
- [ ] Returning user without passkey sees password form
- [ ] Passkey authentication works correctly
- [ ] Password fallback works when passkey fails
- [ ] Users can add multiple passkeys
- [ ] Users can remove passkeys (if they have password)
- [ ] Session management works correctly
- [ ] Logout clears Kratos session properly

## Common Issues & Solutions

### Issue: WebAuthn script not loading
**Solution**: Ensure CORS is properly configured in kratos.yml

### Issue: WebAuthn not offered after identifier
**Solution**: User might not have WebAuthn credentials yet

### Issue: "Method not allowed" errors
**Solution**: Ensure WebAuthn is enabled in kratos.yml

### Issue: Domain mismatch errors
**Solution**: Check RP ID and origins in kratos.yml match your domain