# STING Authentication Architecture Alignment with Kratos Best Practices

## Current Issues

1. **Cookie Domain Mismatch**: Frontend cookies set for `localhost` can't be validated by backend accessing Kratos via `kratos:4433`
2. **Dual State Management**: `force_password_change` stored in both Kratos traits AND separate database
3. **Complex Middleware**: Backend trying to enforce password changes but can't validate sessions properly
4. **Frontend Bypass**: Frontend checks Kratos directly, bypassing backend enforcement

## Industry Best Practices Solution

### 1. Use Kratos Native Flows (Recommended)

Instead of custom middleware, use Kratos's native "Settings Flow" with required fields:

```yaml
# kratos.yml
selfservice:
  flows:
    settings:
      required_aal: aal1
      after:
        password:
          hooks:
            - hook: web_hook
              config:
                url: http://app:5050/api/kratos/hooks/password-changed
                method: POST
```

### 2. Implement Kratos Hooks

Create a webhook that Kratos calls after password change:

```python
@kratos_hooks_bp.route('/password-changed', methods=['POST'])
def kratos_password_changed():
    """Called by Kratos after successful password change"""
    data = request.json
    identity_id = data['identity']['id']
    
    # Clear force_password_change in our database
    settings = UserSettings.query.filter_by(user_id=identity_id).first()
    if settings:
        settings.force_password_change = False
        settings.password_changed_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({"success": True})
```

### 3. Use Kratos Admin API for Enforcement

Instead of traits, use Kratos's native session management:

```python
def require_password_change(identity_id):
    """Force user to change password on next login"""
    # Use Kratos Admin API to require settings update
    requests.post(
        f"{KRATOS_ADMIN_URL}/admin/identities/{identity_id}/sessions",
        json={
            "active": False  # Invalidate all sessions
        }
    )
```

### 4. Simplify Frontend Flow

Use Kratos's UI nodes directly:

```javascript
// Check if Kratos requires settings update
const checkRequiredActions = async () => {
  try {
    const { data } = await kratos.toSession();
    
    // Kratos will redirect to settings if required
    if (data.active && !window.location.pathname.includes('/settings')) {
      // User is good to go
      navigate('/dashboard');
    }
  } catch (error) {
    if (error.response?.status === 403) {
      // Kratos requires action
      window.location.href = `${KRATOS_BROWSER_URL}/self-service/settings/browser`;
    }
  }
};
```

## Immediate Fix for Your Situation

Since we need a quick solution, here's a workaround:

### Option 1: Direct Password Change URL

Navigate directly to Kratos settings:
```
https://localhost:4433/self-service/settings/browser?flow=password
```

### Option 2: Manual API Call to Change Password

I'll create a script that changes your password via API:

```python
#!/usr/bin/env python3
import requests
import json

def change_password_via_api():
    # Initialize settings flow
    resp = requests.get("https://localhost:4433/self-service/settings/api", verify=False)
    flow = resp.json()
    
    # Submit password change
    payload = {
        "method": "password",
        "password": "your-new-secure-password",
        "csrf_token": flow['ui']['nodes'][0]['attributes']['value']
    }
    
    resp = requests.post(
        f"https://localhost:4433/self-service/settings?flow={flow['id']}",
        json=payload,
        verify=False
    )
    
    if resp.status_code == 200:
        print("✓ Password changed successfully!")
    else:
        print(f"✗ Failed: {resp.text}")

if __name__ == "__main__":
    change_password_via_api()
```

## Recommended Architecture Changes

### 1. Single Source of Truth
- Use Kratos as the ONLY source for authentication state
- Remove `force_password_change` from UserSettings table
- Use Kratos hooks for any custom logic

### 2. Proper Cookie Configuration
```yaml
# kratos.yml
serve:
  public:
    cors:
      enabled: true
      allowed_origins:
        - https://localhost:8443
        - https://localhost:3000
session:
  cookie:
    domain: ""  # Empty = no domain restriction
    same_site: "Lax"
    secure: true
    http_only: true
```

### 3. API Gateway Pattern
Instead of each service talking to Kratos, use the frontend as a gateway:
- Frontend → Kratos (for auth)
- Frontend → Backend API (with session token)
- Backend trusts Frontend's authentication

### 4. Use Kratos SDK
```javascript
import { FrontendApi, Configuration } from '@ory/kratos-client'

const kratos = new FrontendApi(
  new Configuration({
    basePath: process.env.REACT_APP_KRATOS_PUBLIC_URL,
    baseOptions: {
      withCredentials: true
    }
  })
)
```

## Quick Actions You Can Take Now

1. **Change password manually via Kratos UI**:
   ```
   https://localhost:4433/self-service/settings/browser
   ```

2. **Clear the force_password_change flag**:
   ```sql
   UPDATE user_settings 
   SET force_password_change = false 
   WHERE email = 'admin@sting.local';
   ```

3. **Disable the middleware temporarily**:
   Comment out the middleware in `app/__init__.py`

Would you like me to implement any of these solutions?