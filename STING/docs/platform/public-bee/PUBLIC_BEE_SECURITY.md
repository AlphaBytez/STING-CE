# Public Bee Security Guide

**Security Best Practices for AI-as-a-Service Deployment**

## Overview

Public Bee services expose AI capabilities to external users, requiring robust security measures to protect both your organization and your users' data. This guide covers comprehensive security practices from development to production deployment.

## Security Architecture

### Defense in Depth Strategy

```
┌─────────────────┐
│   CDN/WAF       │  ← DDoS Protection, Rate Limiting
├─────────────────┤
│  Load Balancer  │  ← SSL Termination, Header Filtering  
├─────────────────┤
│  API Gateway    │  ← Authentication, Authorization
├─────────────────┤
│  Public Bee     │  ← Input Validation, PII Filtering
│  Service        │
├─────────────────┤
│  Knowledge      │  ← Access Control, Data Encryption
│  Service        │
├─────────────────┤
│  Database       │  ← Encryption at Rest, Network Isolation
└─────────────────┘
```

### Security Zones

#### DMZ (Demilitarized Zone)
- Public Bee API endpoints
- Rate limiting and basic validation
- SSL termination
- WAF protection

#### Application Zone
- Business logic processing
- Knowledge base access
- PII detection and filtering
- Audit logging

#### Data Zone
- Encrypted databases
- Honey Jar storage
- Conversation logs
- Analytics data

## Authentication & Authorization

### API Key Management

#### API Key Generation
```python
# Secure API key generation
import secrets
import hashlib
from datetime import datetime, timedelta

def generate_api_key(prefix="sk"):
    """Generate cryptographically secure API key"""
    random_bytes = secrets.token_bytes(32)
    key_id = secrets.token_hex(8)
    api_key = f"{prefix}_{key_id}_{secrets.token_urlsafe(32)}"
    
    # Store hash, not plaintext
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    return {
        'api_key': api_key,
        'key_hash': key_hash,
        'key_id': key_id,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + timedelta(days=365)
    }
```

#### Key Rotation Policy
```yaml
# API key security policy
api_key_policy:
  rotation:
    frequency: 90d  # Rotate every 90 days
    grace_period: 7d  # Allow old keys for 7 days
    notification: 14d  # Notify 14 days before expiration
    
  validation:
    max_age: 365d
    min_entropy: 256  # bits
    prefix_required: true
    
  permissions:
    scope_required: true
    rate_limits: true
    domain_restrictions: true
```

#### Multi-Factor API Authentication
```python
# Optional: HMAC signature validation for high-security scenarios
def validate_request_signature(request, api_secret):
    """Validate HMAC signature for request integrity"""
    timestamp = request.headers.get('X-Timestamp')
    signature = request.headers.get('X-Signature')
    
    # Check timestamp freshness (prevent replay attacks)
    if abs(int(timestamp) - int(time.time())) > 300:  # 5 minutes
        return False
        
    # Reconstruct expected signature
    payload = f"{request.method}{request.path}{request.body}{timestamp}"
    expected_sig = hmac.new(
        api_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_sig)
```

### Access Control Models

#### Role-Based Access Control (RBAC)
```yaml
# RBAC permissions matrix
roles:
  bot_user:
    permissions:
      - chat:send
      - chat:history:own
      - bot:info:public
      
  bot_admin:
    permissions:
      - chat:*
      - bot:create
      - bot:update:own
      - bot:delete:own
      - analytics:view:own
      
  tenant_admin:
    permissions:
      - bot:*
      - user:manage
      - analytics:*
      - billing:view
      
  super_admin:
    permissions:
      - "*"
```

#### Attribute-Based Access Control (ABAC)
```python
# Dynamic permissions based on context
class AccessPolicy:
    def can_access_bot(self, user, bot, action, context):
        rules = [
            # Tenant isolation
            user.tenant_id == bot.tenant_id,
            
            # Time-based access
            self.is_within_allowed_hours(context.timestamp),
            
            # Geographic restrictions
            self.is_allowed_location(context.ip_address, bot.geo_restrictions),
            
            # Rate limiting
            self.check_rate_limit(user.api_key, bot.rate_limits),
            
            # Bot status
            bot.status == 'active'
        ]
        
        return all(rules)
```

## Input Validation & Sanitization

### Message Validation

#### Comprehensive Input Sanitization
```python
# Multi-layer input validation
import re
import html
from typing import Optional

class MessageValidator:
    def __init__(self):
        self.max_length = 8000  # characters
        self.max_tokens = 2000  # estimated tokens
        self.forbidden_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS prevention
            r'javascript:',
            r'on\w+\s*=',  # Event handlers
            r'data:text/html',
            r'vbscript:',
        ]
        
    def validate_message(self, message: str) -> tuple[bool, Optional[str], str]:
        """Validate and sanitize user message"""
        
        # Length validation
        if len(message) > self.max_length:
            return False, "Message too long", ""
            
        # Empty message check
        if not message.strip():
            return False, "Empty message", ""
            
        # XSS pattern detection
        for pattern in self.forbidden_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False, "Potentially malicious content detected", ""
                
        # HTML escape
        sanitized = html.escape(message)
        
        # Unicode normalization
        sanitized = unicodedata.normalize('NFKC', sanitized)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized 
                           if ord(char) >= 32 or char in '\n\r\t')
        
        return True, None, sanitized
```

#### SQL Injection Prevention
```python
# Always use parameterized queries
def get_bot_conversations(bot_id: str, user_id: str, limit: int = 50):
    """Safe database query with parameters"""
    query = """
    SELECT session_id, message, response, timestamp 
    FROM conversations 
    WHERE bot_id = %s AND user_id = %s 
    ORDER BY timestamp DESC 
    LIMIT %s
    """
    return execute_query(query, (bot_id, user_id, limit))
```

### Content Security Policy (CSP)

#### Widget CSP Headers
```python
# CSP for embedded widgets
CSP_POLICY = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline' *.sting.com",
    'style-src': "'self' 'unsafe-inline'",
    'img-src': "'self' data: https:",
    'connect-src': "'self' wss: https:",
    'font-src': "'self' data:",
    'frame-src': "'none'",
    'object-src': "'none'",
    'base-uri': "'self'",
    'form-action': "'self'",
}

def add_csp_headers(response):
    csp_header = '; '.join([f"{key} {value}" for key, value in CSP_POLICY.items()])
    response.headers['Content-Security-Policy'] = csp_header
    return response
```

## Data Protection

### PII Detection & Filtering

#### Advanced PII Detection
```python
# Enhanced PII detection engine
class PIIDetector:
    def __init__(self):
        self.patterns = {
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[- ]?\d{3}[- ]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'api_key': r'\b[sS][kK]_[a-zA-Z0-9_-]{32,}\b',
            'password': r'(?i)(?:password|pwd|pass)[\'"\s:=]+[^\s\'"]+',
        }
        
        self.replacement_map = {
            'ssn': 'XXX-XX-XXXX',
            'credit_card': 'XXXX-XXXX-XXXX-XXXX',
            'email': '[EMAIL_REDACTED]',
            'phone': 'XXX-XXX-XXXX',
            'ip_address': 'XX.XX.XX.XX',
            'api_key': '[API_KEY_REDACTED]',
            'password': '[PASSWORD_REDACTED]',
        }
    
    def detect_and_redact(self, text: str, profile: str = 'moderate') -> tuple[str, list]:
        """Detect PII and return redacted text with detection log"""
        detections = []
        redacted_text = text
        
        # Profile-based filtering
        active_patterns = self.get_patterns_for_profile(profile)
        
        for pii_type, pattern in active_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                detections.append({
                    'type': pii_type,
                    'position': match.span(),
                    'confidence': self.calculate_confidence(match.group(), pii_type)
                })
                
                # Replace with redacted version
                replacement = self.replacement_map.get(pii_type, '[REDACTED]')
                redacted_text = re.sub(pattern, replacement, redacted_text)
        
        return redacted_text, detections
    
    def calculate_confidence(self, text: str, pii_type: str) -> float:
        """Calculate confidence score for PII detection"""
        # Implement ML-based confidence scoring
        # This is a simplified example
        confidence_map = {
            'ssn': 0.95 if len(text.replace('-', '')) == 9 else 0.8,
            'credit_card': 0.9,
            'email': 0.95 if '@' in text and '.' in text.split('@')[1] else 0.7,
            'phone': 0.85,
            'ip_address': 0.8,
            'api_key': 0.95 if text.startswith(('sk_', 'SK_')) else 0.7,
            'password': 0.6,  # Lower confidence due to false positives
        }
        return confidence_map.get(pii_type, 0.5)
```

#### GDPR Compliance Features
```python
# GDPR compliance utilities
class GDPRCompliance:
    def __init__(self):
        self.lawful_basis_map = {
            'consent': 'User provided explicit consent',
            'contract': 'Processing necessary for contract performance',
            'legal_obligation': 'Required by law',
            'vital_interests': 'Necessary to protect vital interests',
            'public_task': 'Necessary for public task',
            'legitimate_interest': 'Legitimate business interest'
        }
    
    def log_processing_activity(self, user_id: str, data_type: str, 
                               purpose: str, lawful_basis: str):
        """Log data processing for GDPR audit trail"""
        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'data_type': data_type,
            'purpose': purpose,
            'lawful_basis': lawful_basis,
            'retention_period': self.get_retention_period(data_type),
            'controller': 'Public Bee Service'
        }
        
        # Store in audit log
        self.store_processing_log(activity)
    
    def handle_right_to_erasure(self, user_id: str):
        """Handle GDPR Article 17 - Right to be forgotten"""
        # Anonymize conversation data
        self.anonymize_user_conversations(user_id)
        
        # Remove personal identifiers
        self.remove_user_profile(user_id)
        
        # Update analytics (anonymized)
        self.update_anonymized_analytics(user_id)
        
        # Log erasure activity
        self.log_erasure_activity(user_id)
        
        return {
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'data_removed': ['conversations', 'profile', 'session_data'],
            'data_retained': ['anonymized_analytics']  # Legitimate interest
        }
```

### Encryption

#### End-to-End Encryption
```python
# Encrypt sensitive data at rest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConversationEncryption:
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        
    def derive_session_key(self, session_id: str, salt: bytes = None) -> Fernet:
        """Derive encryption key for specific session"""
        if not salt:
            salt = session_id.encode()[:16].ljust(16, b'0')
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_conversation(self, session_id: str, content: str) -> str:
        """Encrypt conversation content"""
        fernet = self.derive_session_key(session_id)
        encrypted = fernet.encrypt(content.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_conversation(self, session_id: str, encrypted_content: str) -> str:
        """Decrypt conversation content"""
        fernet = self.derive_session_key(session_id)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_content.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
```

#### TLS Configuration
```nginx
# nginx SSL configuration for Public Bee
server {
    listen 443 ssl http2;
    server_name api.sting.com;
    
    # SSL Certificates
    ssl_certificate /etc/ssl/certs/sting.crt;
    ssl_certificate_key /etc/ssl/private/sting.key;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Security Headers
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location /api/public/ {
        proxy_pass http://public-bee-backend;
        proxy_ssl_verify off;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Hide server info
        proxy_hide_header X-Powered-By;
        proxy_hide_header Server;
    }
}
```

## Network Security

### Firewall Rules

#### Docker Network Isolation
```yaml
# docker-compose security configuration
networks:
  public_bee_dmz:
    driver: bridge
    internal: false  # Internet access
    ipam:
      config:
        - subnet: 172.20.0.0/24
          
  app_internal:
    driver: bridge
    internal: true  # No internet access
    ipam:
      config:
        - subnet: 172.21.0.0/24
          
  data_internal:
    driver: bridge
    internal: true  # Database network
    ipam:
      config:
        - subnet: 172.22.0.0/24

services:
  public-bee:
    networks:
      - public_bee_dmz
      - app_internal
      
  knowledge:
    networks:
      - app_internal
      - data_internal
      
  postgres:
    networks:
      - data_internal  # Only accessible from app layer
```

#### IPTables Rules
```bash
#!/bin/bash
# Firewall rules for Public Bee production deployment

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (restrict to admin IPs)
iptables -A INPUT -p tcp --dport 22 -s ADMIN_IP_RANGE -j ACCEPT

# Allow HTTPS for Public Bee
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8092 -j ACCEPT

# Rate limiting for API endpoints
iptables -A INPUT -p tcp --dport 8092 -m limit --limit 100/min --limit-burst 200 -j ACCEPT
iptables -A INPUT -p tcp --dport 8092 -j DROP

# Block common attack ports
iptables -A INPUT -p tcp --dport 23,135,139,445,1433,3389 -j DROP

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "STING-FIREWALL-DROP: "
iptables -A INPUT -j DROP
```

### VPN & Private Networks

#### Production Network Architecture
```yaml
# Production deployment with VPN
version: '3.8'
services:
  public-bee:
    image: sting/public-bee:production
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db-private:5432/sting
      - REDIS_URL=redis://redis-private:6379/0
    networks:
      - dmz
      - internal
    ports:
      - "8092:8092"
      
  wireguard:
    image: linuxserver/wireguard
    environment:
      - PEERS=admin,monitoring,backup
    volumes:
      - ./wireguard:/config
    ports:
      - "51820:51820/udp"
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
```

## Rate Limiting & DDoS Protection

### Advanced Rate Limiting

#### Multi-Tier Rate Limiting
```python
# Sophisticated rate limiting with Redis
import redis
from datetime import datetime, timedelta

class AdvancedRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def check_rate_limit(self, identifier: str, limits: dict) -> dict:
        """Check multiple rate limit tiers simultaneously"""
        now = datetime.utcnow()
        results = {}
        
        for window, limit in limits.items():
            key = f"rate_limit:{identifier}:{window}"
            window_start = self.get_window_start(now, window)
            
            # Sliding window log
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start.timestamp())
            pipe.zcard(key)
            pipe.zadd(key, {str(now.timestamp()): now.timestamp()})
            pipe.expire(key, self.get_window_seconds(window))
            
            _, current_count, _, _ = pipe.execute()
            
            results[window] = {
                'allowed': current_count < limit,
                'current': current_count,
                'limit': limit,
                'reset_time': window_start + timedelta(seconds=self.get_window_seconds(window))
            }
            
        return results
    
    def is_allowed(self, limits_result: dict) -> bool:
        """Check if request is allowed based on all limits"""
        return all(result['allowed'] for result in limits_result.values())
```

#### Adaptive Rate Limiting
```python
# Dynamic rate limiting based on system load
class AdaptiveRateLimiter:
    def __init__(self):
        self.base_limits = {'1m': 60, '1h': 1000, '1d': 10000}
        self.load_thresholds = {
            'low': 1.0,      # Normal limits
            'medium': 0.7,   # 70% of normal
            'high': 0.5,     # 50% of normal
            'critical': 0.1  # 10% of normal
        }
    
    def get_current_limits(self, api_key: str) -> dict:
        """Adjust limits based on system load"""
        system_load = self.get_system_load()
        load_level = self.get_load_level(system_load)
        multiplier = self.load_thresholds[load_level]
        
        adjusted_limits = {
            window: int(limit * multiplier) 
            for window, limit in self.base_limits.items()
        }
        
        return adjusted_limits
    
    def get_system_load(self) -> float:
        """Get current system load metrics"""
        # Combine CPU, memory, response time metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        avg_response_time = self.get_avg_response_time()
        
        # Weighted load score
        load_score = (cpu_usage * 0.4 + memory_usage * 0.3 + 
                     min(avg_response_time * 20, 100) * 0.3)
        
        return load_score / 100  # Normalize to 0-1
```

### DDoS Protection

#### Application-Layer Protection
```python
# Advanced DDoS detection
class DDoSProtection:
    def __init__(self):
        self.suspicious_patterns = [
            {'type': 'high_frequency', 'threshold': 100, 'window': 60},
            {'type': 'identical_messages', 'threshold': 10, 'window': 300},
            {'type': 'invalid_requests', 'threshold': 20, 'window': 60},
            {'type': 'empty_messages', 'threshold': 50, 'window': 300},
        ]
        
    def analyze_request_pattern(self, ip_address: str, request_data: dict) -> dict:
        """Analyze request for DDoS patterns"""
        analysis = {
            'risk_score': 0,
            'detected_patterns': [],
            'recommended_action': 'allow'
        }
        
        # Check each suspicious pattern
        for pattern in self.suspicious_patterns:
            if self.check_pattern(ip_address, request_data, pattern):
                analysis['risk_score'] += 25
                analysis['detected_patterns'].append(pattern['type'])
        
        # Determine action based on risk score
        if analysis['risk_score'] >= 75:
            analysis['recommended_action'] = 'block'
        elif analysis['risk_score'] >= 50:
            analysis['recommended_action'] = 'captcha'
        elif analysis['risk_score'] >= 25:
            analysis['recommended_action'] = 'rate_limit'
            
        return analysis
    
    def implement_protection(self, ip_address: str, action: str, duration: int = 300):
        """Implement protection action"""
        protection_key = f"ddos_protection:{ip_address}"
        
        if action == 'block':
            self.redis.setex(f"{protection_key}:blocked", duration, "1")
        elif action == 'rate_limit':
            # Reduce rate limits significantly
            self.redis.setex(f"{protection_key}:limited", duration, "1")
        elif action == 'captcha':
            self.redis.setex(f"{protection_key}:captcha", duration, "1")
```

## Audit Logging & Monitoring

### Comprehensive Audit Logging

#### Security Event Logging
```python
# Security-focused audit logging
class SecurityAuditor:
    def __init__(self):
        self.logger = self.setup_security_logger()
        
    def log_security_event(self, event_type: str, details: dict, 
                          severity: str = 'INFO'):
        """Log security-relevant events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'source': 'public_bee_service',
            'details': details,
            'correlation_id': self.generate_correlation_id()
        }
        
        # Add contextual information
        log_entry.update(self.get_context())
        
        # Log to appropriate destination based on severity
        if severity in ['CRITICAL', 'HIGH']:
            self.logger.critical(json.dumps(log_entry))
            self.send_alert(log_entry)
        elif severity == 'MEDIUM':
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
    
    def log_authentication_event(self, api_key_id: str, result: str, 
                                ip_address: str, user_agent: str):
        """Log authentication attempts"""
        self.log_security_event('authentication', {
            'api_key_id': api_key_id[:8] + '...',  # Partial key for identification
            'result': result,  # 'success', 'failure', 'expired', 'invalid'
            'ip_address': ip_address,
            'user_agent': user_agent,
            'geolocation': self.get_geolocation(ip_address)
        }, severity='MEDIUM' if result != 'success' else 'INFO')
    
    def log_data_access(self, bot_id: str, data_type: str, 
                       user_id: str, action: str):
        """Log data access for compliance"""
        self.log_security_event('data_access', {
            'bot_id': bot_id,
            'data_type': data_type,
            'user_id': user_id,
            'action': action,  # 'read', 'write', 'delete'
            'lawful_basis': self.determine_lawful_basis(action, data_type)
        })
```

#### Real-time Monitoring
```python
# Security monitoring with alerting
class SecurityMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'failed_authentications': {'count': 5, 'window': 300},
            'rate_limit_violations': {'count': 10, 'window': 600},
            'pii_detection_spikes': {'count': 20, 'window': 3600},
            'suspicious_ips': {'count': 3, 'window': 1800},
        }
    
    def check_security_metrics(self):
        """Continuously monitor security metrics"""
        for metric, threshold in self.alert_thresholds.items():
            current_count = self.get_metric_count(metric, threshold['window'])
            
            if current_count >= threshold['count']:
                self.trigger_alert(metric, current_count, threshold)
    
    def trigger_alert(self, metric: str, count: int, threshold: dict):
        """Trigger security alert"""
        alert = {
            'alert_type': 'security_threshold_exceeded',
            'metric': metric,
            'current_count': count,
            'threshold': threshold['count'],
            'window': threshold['window'],
            'timestamp': datetime.utcnow().isoformat(),
            'severity': self.get_alert_severity(metric)
        }
        
        # Send to monitoring system
        self.send_to_monitoring_system(alert)
        
        # Trigger automatic response if configured
        if self.should_auto_respond(metric):
            self.trigger_automatic_response(alert)
```

## Incident Response

### Automated Response System

#### Threat Response Automation
```python
# Automated incident response
class IncidentResponse:
    def __init__(self):
        self.response_playbooks = {
            'brute_force_attack': self.handle_brute_force,
            'ddos_attack': self.handle_ddos,
            'pii_leak_detection': self.handle_pii_leak,
            'api_abuse': self.handle_api_abuse,
        }
    
    def handle_security_incident(self, incident_type: str, details: dict):
        """Coordinate incident response"""
        playbook = self.response_playbooks.get(incident_type)
        if not playbook:
            return self.handle_unknown_incident(incident_type, details)
            
        # Execute response playbook
        response = playbook(details)
        
        # Log response actions
        self.log_incident_response(incident_type, details, response)
        
        # Notify security team
        self.notify_security_team(incident_type, details, response)
        
        return response
    
    def handle_brute_force(self, details: dict) -> dict:
        """Handle brute force attack"""
        ip_address = details.get('ip_address')
        api_key = details.get('api_key')
        
        actions = []
        
        # Block IP temporarily
        if ip_address:
            self.block_ip(ip_address, duration=3600)  # 1 hour
            actions.append(f"Blocked IP {ip_address} for 1 hour")
        
        # Suspend API key
        if api_key:
            self.suspend_api_key(api_key, reason="Suspected brute force")
            actions.append(f"Suspended API key {api_key[:8]}...")
        
        # Increase monitoring for related IPs
        self.increase_monitoring(ip_address)
        actions.append("Increased monitoring for IP range")
        
        return {'status': 'handled', 'actions': actions}
    
    def handle_pii_leak_detection(self, details: dict) -> dict:
        """Handle potential PII leak"""
        session_id = details.get('session_id')
        bot_id = details.get('bot_id')
        pii_types = details.get('detected_pii', [])
        
        actions = []
        
        # Immediately stop session
        self.terminate_session(session_id)
        actions.append(f"Terminated session {session_id}")
        
        # Review and potentially quarantine bot
        if len(pii_types) > 2:  # Multiple PII types detected
            self.quarantine_bot(bot_id, reason="Multiple PII types detected")
            actions.append(f"Quarantined bot {bot_id}")
        
        # Scrub logs
        self.scrub_session_logs(session_id, pii_types)
        actions.append(f"Scrubbed PII from logs")
        
        # Notify data protection officer
        self.notify_dpo(details)
        actions.append("Notified Data Protection Officer")
        
        return {'status': 'handled', 'actions': actions, 'severity': 'high'}
```

### Security Runbooks

#### Emergency Response Procedures

1. **Suspected Data Breach**
   ```bash
   # Immediate response steps
   ./manage_sting.sh stop public-bee  # Stop service
   ./manage_sting.sh logs public-bee > breach-logs-$(date +%Y%m%d).txt
   ./scripts/security/isolate-affected-data.sh
   ./scripts/security/notify-stakeholders.sh --severity=critical
   ```

2. **Compromise Detection**
   ```bash
   # Lock down and investigate
   ./scripts/security/emergency-lockdown.sh
   ./scripts/security/create-forensic-image.sh
   ./scripts/security/analyze-access-logs.sh --last-24h
   ```

3. **API Key Compromise**
   ```bash
   # Revoke and rotate
   ./scripts/security/revoke-api-key.sh $COMPROMISED_KEY
   ./scripts/security/force-key-rotation.sh --all-bots
   ./scripts/security/audit-key-usage.sh
   ```

## Security Testing

### Penetration Testing

#### Automated Security Testing
```python
# Security test automation
class SecurityTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.test_results = []
    
    def run_security_tests(self):
        """Run comprehensive security test suite"""
        tests = [
            self.test_sql_injection,
            self.test_xss_prevention,
            self.test_authentication_bypass,
            self.test_rate_limiting,
            self.test_input_validation,
            self.test_pii_filtering,
            self.test_csrf_protection,
        ]
        
        for test in tests:
            try:
                result = test()
                self.test_results.append(result)
            except Exception as e:
                self.test_results.append({
                    'test': test.__name__,
                    'status': 'error',
                    'error': str(e)
                })
        
        return self.generate_report()
    
    def test_sql_injection(self) -> dict:
        """Test for SQL injection vulnerabilities"""
        payloads = [
            "' OR 1=1 --",
            "'; DROP TABLE conversations; --",
            "1' UNION SELECT password FROM users --"
        ]
        
        vulnerabilities = []
        for payload in payloads:
            response = self.send_message(payload)
            if self.indicates_sql_error(response):
                vulnerabilities.append({
                    'payload': payload,
                    'response': response.text[:200]
                })
        
        return {
            'test': 'sql_injection',
            'status': 'fail' if vulnerabilities else 'pass',
            'vulnerabilities': vulnerabilities
        }
```

#### Manual Testing Checklist

- [ ] **Authentication & Authorization**
  - [ ] API key validation
  - [ ] Role-based access control
  - [ ] Session management
  - [ ] Token expiration handling

- [ ] **Input Validation**
  - [ ] XSS prevention
  - [ ] SQL injection prevention
  - [ ] Command injection prevention
  - [ ] Path traversal prevention

- [ ] **Data Protection**
  - [ ] PII detection accuracy
  - [ ] Encryption at rest
  - [ ] Encryption in transit
  - [ ] Data anonymization

- [ ] **Network Security**
  - [ ] SSL/TLS configuration
  - [ ] CORS policy
  - [ ] CSP headers
  - [ ] Security headers

- [ ] **Rate Limiting**
  - [ ] Per-IP rate limits
  - [ ] Per-API-key rate limits
  - [ ] DDoS protection
  - [ ] Graceful degradation

## Compliance Frameworks

### GDPR Compliance

#### Data Processing Inventory
```yaml
# GDPR data processing registry
data_processing:
  conversation_data:
    lawful_basis: "legitimate_interest"
    purpose: "Provide AI chat service"
    categories: ["conversation_content", "timestamps", "session_ids"]
    retention_period: "30_days"
    third_party_sharing: false
    
  analytics_data:
    lawful_basis: "legitimate_interest"
    purpose: "Service improvement and analytics"
    categories: ["usage_patterns", "response_times", "error_rates"]
    retention_period: "2_years"
    anonymized: true
    
  audit_logs:
    lawful_basis: "legal_obligation"
    purpose: "Security and compliance monitoring"
    categories: ["access_logs", "authentication_events", "security_events"]
    retention_period: "7_years"
    high_security: true
```

### SOC 2 Compliance

#### Security Controls Framework
```yaml
# SOC 2 Type II controls
security_controls:
  access_control:
    - multi_factor_authentication
    - role_based_access_control
    - regular_access_reviews
    - privileged_access_monitoring
    
  system_operations:
    - change_management_process
    - capacity_monitoring
    - performance_monitoring
    - incident_response_procedures
    
  logical_physical_access:
    - data_center_security
    - network_segmentation
    - endpoint_protection
    - secure_development_lifecycle
    
  system_availability:
    - backup_procedures
    - disaster_recovery_plan
    - high_availability_architecture
    - monitoring_alerting
    
  processing_integrity:
    - input_validation
    - error_handling
    - data_integrity_checks
    - audit_logging
    
  confidentiality:
    - data_classification
    - encryption_standards
    - secure_transmission
    - data_retention_policies
```

## Security Maintenance

### Regular Security Tasks

#### Daily Tasks
- Monitor security alerts and dashboards
- Review failed authentication logs
- Check rate limiting effectiveness
- Verify backup integrity

#### Weekly Tasks
- Analyze security metrics trends
- Review and rotate API keys if needed
- Update threat intelligence feeds
- Test incident response procedures

#### Monthly Tasks
- Security vulnerability scans
- Review and update security policies
- Analyze audit logs for anomalies
- Update security training materials

#### Quarterly Tasks
- Penetration testing
- Security architecture review
- Compliance audit preparation
- Disaster recovery testing

### Security Updates

#### Patch Management Process
```bash
#!/bin/bash
# Security update deployment process

# 1. Test in staging environment
./scripts/security/deploy-security-updates.sh --environment=staging
./scripts/security/run-security-tests.sh --environment=staging

# 2. Verify staging deployment
if ./scripts/security/verify-security-updates.sh --environment=staging; then
    echo "Security updates verified in staging"
else
    echo "Security updates failed verification"
    exit 1
fi

# 3. Deploy to production with blue-green deployment
./scripts/security/deploy-security-updates.sh --environment=production --blue-green
./scripts/security/verify-security-updates.sh --environment=production

# 4. Monitor for issues
./scripts/monitoring/enhanced-monitoring.sh --duration=24h --focus=security
```

---

**Remember**: Security is not a one-time setup but an ongoing process. Regularly review and update your security measures as threats evolve and your Public Bee deployment grows. 🛡️🐝