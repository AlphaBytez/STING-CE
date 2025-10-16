# Redis Session Analytics

## Overview

STING-CE uses Redis as a high-performance session store to provide persistent sessions across service restarts, real-time session analytics, and comprehensive user activity monitoring. This system seamlessly integrates with Kratos authentication while providing enhanced session management capabilities.

## Architecture

### Session Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Client      │───▶│     Kratos      │───▶│  Flask Session  │
│   (Browser)     │    │ (Authentication)│    │   (App Logic)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────────────────────────────┐
                       │              Redis                      │
                       │        (Session Store)                  │
                       │  ┌─────────────┐ ┌─────────────────────┐│
                       │  │   Kratos    │ │  Flask Sessions     ││
                       │  │  Sessions   │ │  (sting:session:*)  ││
                       │  └─────────────┘ └─────────────────────┘│
                       └─────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │    Analytics    │
                              │   Dashboard     │
                              └─────────────────┘
```

### Key Components

1. **Redis Server**: High-performance session storage
2. **Flask Session Manager**: Application-level session handling  
3. **Kratos Integration**: Authentication session coordination
4. **Analytics Engine**: Real-time session monitoring
5. **Dashboard Interface**: Visual session analytics

## Configuration

### Redis Configuration

Redis is configured in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  container_name: sting-ce-redis
  ports:
    - 6379:6379
  volumes:
    - redis_data:/data
  networks:
    - sting_local
  environment:
    - REDIS_MAXMEMORY=512mb
    - REDIS_MAXMEMORY_POLICY=allkeys-lru
    - REDIS_SAVE="900 1 300 10 60 10000"  # Persistence settings
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
      reservations:
        memory: 128M
```

### Flask Session Configuration  

In the STING application (`app/__init__.py`):

```python
import redis
from flask_session import Session

# Redis connection
redis_client = redis.from_url('redis://redis:6379/0', decode_responses=True)

# Flask session configuration
app.config.update({
    'SESSION_TYPE': 'redis',
    'SESSION_REDIS': redis_client,
    'SESSION_KEY_PREFIX': 'sting:',
    'SESSION_PERMANENT': True,
    'SESSION_USE_SIGNER': True,
    'SESSION_COOKIE_SECURE': True,  # HTTPS only
    'SESSION_COOKIE_HTTPONLY': True,  # Prevent XSS
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=24)
})

# Initialize session manager
Session(app)
```

### Environment Variables

Session configuration is managed through environment files:

```bash
# Redis connection
REDIS_URL=redis://redis:6379/0
SESSION_REDIS_HOST=redis
SESSION_REDIS_PORT=6379
SESSION_REDIS_DB=0

# Session security
SESSION_SECRET_KEY=secure_session_secret_change_me
SESSION_COOKIE_SECURE=true
SESSION_LIFETIME_HOURS=24

# Analytics settings
ANALYTICS_ENABLED=true
ANALYTICS_RETENTION_DAYS=30
```

## Session Data Structure

### Redis Key Patterns

```redis
# Flask sessions (application state)
sting:session:{session_id}

# Session analytics (tracking data)  
sting:analytics:session:{session_id}
sting:analytics:user:{user_id}:sessions
sting:analytics:daily:{date}

# Active session tracking
sting:active:sessions
sting:active:users:{user_id}

# Session metrics
sting:metrics:hourly:{hour}
sting:metrics:daily:{date}
```

### Session Data Example

```json
// sting:session:abc123def456
{
  "user_id": "kratos-user-uuid",
  "email": "user@example.com", 
  "role": "user",
  "created_at": "2024-08-22T10:30:45Z",
  "last_activity": "2024-08-22T11:45:20Z",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "kratos_session_id": "kratos-session-uuid",
  "permissions": ["honey_jar:read", "reports:create"],
  "preferences": {
    "theme": "dark",
    "language": "en"
  }
}
```

### Analytics Data Example

```json
// sting:analytics:session:abc123def456
{
  "session_id": "abc123def456",
  "user_id": "kratos-user-uuid", 
  "start_time": "2024-08-22T10:30:45Z",
  "end_time": null,
  "duration": 4575,  // seconds
  "page_views": 23,
  "actions": [
    {"timestamp": "2024-08-22T10:31:00Z", "action": "login"},
    {"timestamp": "2024-08-22T10:32:15Z", "action": "view_dashboard"},
    {"timestamp": "2024-08-22T10:35:30Z", "action": "upload_document"}
  ],
  "ip_address": "192.168.1.100",
  "location": {"country": "US", "city": "San Francisco"},
  "device": {
    "os": "macOS",
    "browser": "Chrome",
    "mobile": false
  }
}
```

## Analytics Features

### Real-time Session Monitoring

The analytics system provides real-time insights:

```python
class SessionAnalytics:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def track_session_start(self, session_id, user_id, metadata):
        """Track when a session begins"""
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'start_time': datetime.utcnow().isoformat(),
            'ip_address': metadata.get('ip'),
            'user_agent': metadata.get('user_agent'),
            'page_views': 0,
            'actions': []
        }
        
        # Store session analytics
        self.redis.setex(
            f"sting:analytics:session:{session_id}",
            86400 * 30,  # 30 days
            json.dumps(session_data)
        )
        
        # Add to active sessions
        self.redis.sadd("sting:active:sessions", session_id)
        self.redis.sadd(f"sting:active:users:{user_id}", session_id)
        
        # Update metrics
        self.increment_metric("sessions_started")
    
    def track_page_view(self, session_id, page, timestamp=None):
        """Track page views within a session"""
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()
            
        # Update session data
        session_key = f"sting:analytics:session:{session_id}"
        session_data = self.get_session_data(session_id)
        
        if session_data:
            session_data['page_views'] += 1
            session_data['last_activity'] = timestamp
            session_data['actions'].append({
                'timestamp': timestamp,
                'action': 'page_view',
                'page': page
            })
            
            self.redis.setex(session_key, 86400 * 30, json.dumps(session_data))
    
    def get_active_sessions(self):
        """Get count of currently active sessions"""
        return self.redis.scard("sting:active:sessions")
    
    def get_user_session_history(self, user_id, limit=50):
        """Get session history for a specific user"""
        user_sessions = self.redis.smembers(f"sting:active:users:{user_id}")
        
        sessions = []
        for session_id in user_sessions:
            session_data = self.get_session_data(session_id)
            if session_data:
                sessions.append(session_data)
        
        return sorted(sessions, key=lambda x: x['start_time'], reverse=True)[:limit]
```

### Dashboard Metrics

Key metrics available in the analytics dashboard:

1. **Active Sessions**: Real-time count of active user sessions
2. **Session Duration**: Average and distribution of session lengths
3. **Page Views**: Most visited pages and user navigation patterns  
4. **User Activity**: Login frequency, peak usage times
5. **Geographic Data**: User locations and access patterns
6. **Device Analytics**: Browser, OS, and device type statistics

### API Endpoints

Session analytics are accessible via REST API:

```python
@app.route('/api/analytics/sessions/active')
@require_auth
def get_active_sessions():
    """Get current active session count"""
    analytics = SessionAnalytics(redis_client)
    return jsonify({
        'active_sessions': analytics.get_active_sessions(),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/analytics/sessions/stats')
@require_auth  
def get_session_stats():
    """Get session statistics"""
    analytics = SessionAnalytics(redis_client)
    
    # Calculate metrics
    total_sessions_today = analytics.get_metric('sessions_started', 'daily')
    avg_session_duration = analytics.get_average_duration()
    unique_users_today = analytics.get_unique_users('daily')
    
    return jsonify({
        'total_sessions_today': total_sessions_today,
        'average_duration_minutes': avg_session_duration / 60,
        'unique_users_today': unique_users_today,
        'active_sessions': analytics.get_active_sessions()
    })

@app.route('/api/analytics/users/<user_id>/sessions')
@require_auth
def get_user_sessions(user_id):
    """Get session history for a specific user"""
    analytics = SessionAnalytics(redis_client)
    sessions = analytics.get_user_session_history(user_id)
    
    return jsonify({
        'user_id': user_id,
        'sessions': sessions,
        'total_count': len(sessions)
    })
```

## Session Management

### Session Cleanup

Automatic cleanup of expired sessions:

```python
class SessionCleanup:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions and update analytics"""
        active_sessions = self.redis.smembers("sting:active:sessions")
        expired_count = 0
        
        for session_id in active_sessions:
            session_key = f"sting:session:{session_id}"
            
            # Check if Flask session still exists
            if not self.redis.exists(session_key):
                self.mark_session_ended(session_id)
                expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        return expired_count
    
    def mark_session_ended(self, session_id):
        """Mark a session as ended in analytics"""
        analytics_key = f"sting:analytics:session:{session_id}"
        session_data = self.get_session_data(session_id)
        
        if session_data:
            session_data['end_time'] = datetime.utcnow().isoformat()
            # Calculate total duration
            start = datetime.fromisoformat(session_data['start_time'])
            end = datetime.utcnow()
            session_data['total_duration'] = int((end - start).total_seconds())
            
            # Move to historical storage
            self.redis.setex(analytics_key, 86400 * 30, json.dumps(session_data))
        
        # Remove from active tracking
        self.redis.srem("sting:active:sessions", session_id)
        
        # Remove from user active sessions
        if session_data and 'user_id' in session_data:
            self.redis.srem(f"sting:active:users:{session_data['user_id']}", session_id)
```

### Session Monitoring Commands

```bash
# Connect to Redis and examine sessions
redis-cli -h localhost -p 6379

# Check active sessions
redis-cli SCARD sting:active:sessions

# List all session keys  
redis-cli KEYS "sting:session:*" | head -10

# Get session data
redis-cli GET "sting:session:abc123def456"

# Check analytics data
redis-cli KEYS "sting:analytics:*" | head -10

# Monitor real-time activity
redis-cli MONITOR
```

## Integration with Authentication

### Kratos Session Synchronization

The system maintains synchronization between Kratos and Flask sessions:

```python
def sync_kratos_session(kratos_session_id, flask_session_id):
    """Synchronize Kratos and Flask sessions"""
    
    # Get Kratos session details
    kratos_session = get_kratos_session(kratos_session_id)
    if not kratos_session:
        return False
    
    # Update Flask session with Kratos data
    session_data = {
        'kratos_session_id': kratos_session_id,
        'user_id': kratos_session['identity']['id'],
        'email': kratos_session['identity']['traits']['email'],
        'verified': kratos_session['identity']['verified_addresses'],
        'aal': kratos_session.get('authenticator_assurance_level', 'aal1'),
        'synced_at': datetime.utcnow().isoformat()
    }
    
    # Store in Redis with expiration matching Kratos session
    session_key = f"sting:session:{flask_session_id}"
    redis_client.setex(session_key, 86400, json.dumps(session_data))
    
    return True
```

### AAL2 Session Tracking

Track AAL2 (multi-factor authentication) sessions separately:

```python
def track_aal2_session(session_id, user_id, method):
    """Track AAL2 authentication events"""
    aal2_data = {
        'session_id': session_id,
        'user_id': user_id,
        'method': method,  # 'webauthn', 'totp', etc.
        'timestamp': datetime.utcnow().isoformat(),
        'ip_address': request.remote_addr
    }
    
    # Store AAL2 event
    aal2_key = f"sting:aal2:{session_id}:{int(time.time())}"
    redis_client.setex(aal2_key, 86400 * 7, json.dumps(aal2_data))
    
    # Update session analytics
    analytics = SessionAnalytics(redis_client)
    analytics.track_action(session_id, 'aal2_authentication', {
        'method': method,
        'success': True
    })
```

## Performance Optimization

### Redis Memory Management

Configure Redis for optimal session storage:

```redis
# redis.conf optimizations for session storage
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence for session durability  
save 900 1    # Save if at least 1 key changed in 900 seconds
save 300 10   # Save if at least 10 keys changed in 300 seconds
save 60 10000 # Save if at least 10000 keys changed in 60 seconds

# Network optimizations
tcp-keepalive 300
timeout 300
```

### Connection Pooling

Use connection pooling for better performance:

```python
import redis.connection

# Configure connection pool
redis_pool = redis.ConnectionPool(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=20,
    retry_on_timeout=True,
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

## Troubleshooting

### Session Data Issues

**Symptoms:**
- Users getting logged out frequently
- Session data not persisting across requests

**Diagnosis:**
```bash
# Check Redis connectivity
redis-cli -h localhost -p 6379 ping

# Examine session keys
redis-cli KEYS "sting:session:*" | wc -l

# Check memory usage
redis-cli INFO memory
```

**Solutions:**
```bash
# Restart Redis if connectivity issues
docker compose restart redis

# Check session configuration in Flask app
docker exec sting-ce-app python -c "
from app import app
print(f'Session type: {app.config.get(\"SESSION_TYPE\")}')
print(f'Redis URL: {app.config.get(\"SESSION_REDIS\")}')
"

# Verify Redis persistence settings
docker exec sting-ce-redis redis-cli CONFIG GET save
```

### Analytics Data Gaps

**Symptoms:**
- Missing analytics data
- Inconsistent session tracking

**Solutions:**
```python
# Run analytics cleanup and validation
from app.services.session_analytics import SessionAnalytics

analytics = SessionAnalytics(redis_client)
analytics.validate_data_integrity()
analytics.cleanup_orphaned_data()
```

### Memory Usage Issues

**Symptoms:**
- Redis consuming excessive memory
- Out of memory errors

**Solutions:**
```bash
# Check memory usage by key pattern
redis-cli --bigkeys

# Clean up old analytics data
redis-cli EVAL "
for i, key in ipairs(redis.call('keys', 'sting:analytics:*')) do
    local ttl = redis.call('ttl', key)
    if ttl == -1 then  -- No expiration set
        redis.call('expire', key, 2592000)  -- 30 days
    end
end
" 0

# Adjust memory policy if needed
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Security Considerations

### Session Security

- **Secure Cookies**: All session cookies use Secure and HttpOnly flags
- **SameSite Protection**: Cookies configured with SameSite=Lax
- **Session Signing**: Flask sessions are cryptographically signed
- **IP Validation**: Track and validate session IP addresses
- **Timeout Management**: Automatic session expiration

### Data Protection

```python
# Example of session data encryption for sensitive fields
from cryptography.fernet import Fernet

class EncryptedSessionStore:
    def __init__(self, redis_client, encryption_key):
        self.redis = redis_client
        self.fernet = Fernet(encryption_key)
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive session data"""
        sensitive_fields = ['email', 'ip_address', 'user_agent']
        
        for field in sensitive_fields:
            if field in data:
                encrypted = self.fernet.encrypt(data[field].encode())
                data[field] = encrypted.decode()
        
        return data
    
    def decrypt_sensitive_data(self, data):
        """Decrypt sensitive session data"""
        sensitive_fields = ['email', 'ip_address', 'user_agent']
        
        for field in sensitive_fields:
            if field in data:
                try:
                    decrypted = self.fernet.decrypt(data[field].encode())
                    data[field] = decrypted.decode()
                except Exception:
                    pass  # Field may not be encrypted
        
        return data
```

## Future Enhancements

### Planned Features

1. **Machine Learning Analytics**: Anomaly detection for suspicious session patterns
2. **Advanced Geolocation**: Enhanced geographic tracking and analysis
3. **Session Replay**: Capture and replay user session interactions
4. **Cross-Device Tracking**: Link sessions across multiple devices
5. **Real-time Alerts**: Instant notifications for security events

### API Expansion

Future API endpoints will include:

```python
# Planned endpoints
GET /api/analytics/sessions/anomalies
GET /api/analytics/sessions/replay/{session_id}
POST /api/analytics/sessions/alerts/configure
GET /api/analytics/users/behavior-patterns
```

---

**Note**: The Redis Session Analytics system provides comprehensive session management and monitoring for STING-CE deployments. It ensures session persistence, security, and provides valuable insights into user behavior while maintaining privacy and performance standards.