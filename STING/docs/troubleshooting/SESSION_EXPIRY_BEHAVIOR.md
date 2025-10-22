# 🔐 Session Expiry Behavior in STING

## Session Lifetimes

### Kratos Sessions (AAL1)
- **Default lifetime**: 24 hours (configured in `kratos.yml` line 151)
- **Extension**: Can be extended after 1 hour of activity
- **Cookie name**: `ory_kratos_session`

### Flask Sessions
- **Default lifetime**: 30 minutes (configured in `app/config.py` line 38)
- **Cookie name**: `sting_session`
- **Type**: Redis-backed sessions

### AAL2 Sessions
- **Privileged session lifetime**: 1 hour (for AAL2 operations)
- **Configurable via**: `config.yml` → `security.authentication.aal2_session_timeout`

## What Happens When AAL1 Session Expires

### 1. Backend Response (Flask Middleware)
When a request is made with an expired session:

1. **Flask Session Check** (`auth_middleware.py`):
   - First checks Flask session for `user_id`
   - If invalid/expired, clears Flask session data

2. **Kratos Session Check**:
   - Calls Kratos `/sessions/whoami` endpoint
   - Kratos returns 401 if session expired
   - Middleware logs: "Kratos session invalid or expired (401)"

3. **API Response**:
   - Returns 401 status code
   - JSON response: `{"error": "Not authenticated"}`

### 2. Frontend Handling

#### Automatic Redirects
Multiple layers handle expired sessions:

1. **API Interceptor** (`knowledgeApi.js` line 62):
   ```javascript
   if (error.response?.status === 401) {
       localStorage.removeItem('user');
       sessionStorage.clear();
       window.location.href = '/login?message=Session expired. Please login again.';
   }
   ```

2. **Kratos SDK Provider** (`KratosSDKProvider.jsx` line 140):
   ```javascript
   if (error?.response?.status === 401 || error?.response?.status === 403) {
       // Session expired or invalid
       navigate('/login');
   }
   ```

3. **Component-Level Handling**:
   - Chat components show: "Session expired. Please refresh the page and try again."
   - Enrollment components show: "Session expired. Please log in again."
   - Then redirect to `/login` after 2 seconds

### 3. User Experience Flow

When AAL1 session expires:

1. **Any API call returns 401** → User is immediately redirected to login
2. **Login page shows message**: "Session expired. Please login again."
3. **User must re-authenticate**:
   - Enter email
   - Get new magic link/OTP code
   - Complete AAL1 authentication

4. **After successful re-authentication**:
   - New 24-hour Kratos session created
   - New 30-minute Flask session created
   - User returned to dashboard or original destination

### 4. Protected Routes Behavior

The `UnifiedProtectedRoute.jsx` component:
- Checks authentication status on mount
- If not authenticated → redirects to `/login`
- If AAL2 required but not met → redirects to `/login?aal=aal2`

## Session Extension Mechanism

### Kratos Session Extension
- Sessions can be extended after 1 hour of activity
- Each API call with valid session extends the expiry
- Maximum lifetime: 24 hours from initial creation

### Flask Session
- Updated on each request (session.modified = True)
- Extends by 30 minutes from last activity
- Stored in Redis with TTL

## Security Implications

### What's Protected
✅ All API endpoints require valid session (except public routes)
✅ WebAuthn/Passkey registration requires AAL1
✅ Admin functions require AAL2
✅ Expired sessions cannot be reused

### What Happens to Data
- **Session data**: Cleared from Redis/memory
- **User data**: Remains in database
- **Temporary auth states**: Cleared
- **Browser storage**: Cleared on 401 response

## Testing Session Expiry

### Manual Test
```bash
# 1. Login normally
# 2. Wait for session to expire (or manually delete cookie)
# 3. Try to access protected route
curl -k https://localhost:8443/api/auth/me
# Expected: 401 {"error": "Not authenticated"}

# 4. Browser will redirect to login with message
```

### Programmatic Test
```python
# Delete session from Redis to simulate expiry
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.delete('sting:session:*')  # Clears all Flask sessions
```

## Key Takeaways

1. **Two-layer session system**: Kratos (24hr) + Flask (30min)
2. **Graceful expiry**: Users redirected to login with clear message
3. **No data loss**: User just needs to re-authenticate
4. **Security maintained**: Expired sessions immediately rejected
5. **AAL2 separate**: Has its own 1-hour timeout for privileged operations

## Configuration Options

To adjust session timeouts:

1. **Kratos sessions**: Edit `/conf/kratos/kratos.yml`
   ```yaml
   session:
     lifespan: 24h  # Change this value
   ```

2. **Flask sessions**: Edit `/app/config.py`
   ```python
   'lifetime': timedelta(minutes=30)  # Change this value
   ```

3. **AAL2 timeout**: Edit `/conf/config.yml`
   ```yaml
   security:
     authentication:
       aal2_session_timeout: 1h  # Change this value
   ```

Remember to rebuild services after configuration changes!