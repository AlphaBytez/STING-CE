#!/usr/bin/env python3
"""
Demo Authentication System for STING-CE
Provides guest access without requiring user registration
"""

import uuid
import time
import json
import hashlib
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class DemoSession:
    """Demo session data structure"""
    session_id: str
    user_id: str
    display_name: str
    ip_address: str
    created_at: datetime
    expires_at: datetime
    message_count: int = 0
    conversation_count: int = 0
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DemoSession':
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if data.get('last_activity'):
            data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.now() > self.expires_at
    
    def is_rate_limited(self, max_messages_per_minute: int = 10) -> bool:
        """Check if session is rate limited"""
        if not self.last_activity:
            return False
        
        time_since_last = datetime.now() - self.last_activity
        if time_since_last < timedelta(minutes=1):
            # Check message rate in last minute
            return self.message_count > max_messages_per_minute
        return False

class DemoAuthManager:
    """Manages demo authentication and sessions"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.sessions: Dict[str, DemoSession] = {}
        self.ip_sessions: Dict[str, List[str]] = {}  # Track sessions per IP
        
        # Configuration
        self.session_timeout = config.get('session_timeout', 1800)  # 30 minutes
        self.max_sessions_per_ip = config.get('max_sessions_per_ip', 3)
        self.max_messages_per_session = config.get('max_messages_per_session', 50)
        self.max_conversation_length = config.get('max_conversation_length', 20)
        self.rate_limit_per_minute = config.get('requests_per_minute', 10)
        
        # Demo user names
        self.demo_names = [
            "Demo Explorer", "Guest User", "Curious Visitor", "Test User",
            "Anonymous User", "Platform Tester", "Demo Participant", "Trial User"
        ]
        
    def create_guest_session(self, ip_address: str, user_agent: str = "") -> Optional[DemoSession]:
        """Create a new guest session"""
        
        # Check IP session limits
        if self._check_ip_session_limit(ip_address):
            logger.warning(f"IP {ip_address} exceeded session limit")
            return None
        
        # Generate unique session ID and user ID
        session_id = self._generate_session_id(ip_address, user_agent)
        user_id = f"demo_user_{uuid.uuid4().hex[:8]}"
        display_name = self._generate_display_name()
        
        # Create session
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        session = DemoSession(
            session_id=session_id,
            user_id=user_id,
            display_name=display_name,
            ip_address=ip_address,
            created_at=now,
            expires_at=expires_at,
            last_activity=now
        )
        
        # Store session
        self.sessions[session_id] = session
        
        # Track IP sessions
        if ip_address not in self.ip_sessions:
            self.ip_sessions[ip_address] = []
        self.ip_sessions[ip_address].append(session_id)
        
        logger.info(f"Created demo session {session_id} for IP {ip_address}")
        return session
    
    def get_session(self, session_id: str) -> Optional[DemoSession]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if session.is_expired():
            self._cleanup_session(session_id)
            return None
        
        return session
    
    def validate_session(self, session_id: str, ip_address: str) -> bool:
        """Validate session and IP match"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Check IP match (basic security)
        if session.ip_address != ip_address:
            logger.warning(f"IP mismatch for session {session_id}: {session.ip_address} vs {ip_address}")
            return False
        
        return True
    
    def update_activity(self, session_id: str) -> bool:
        """Update session activity timestamp"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.last_activity = datetime.now()
        return True
    
    def increment_message_count(self, session_id: str) -> bool:
        """Increment message count for rate limiting"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.message_count += 1
        session.last_activity = datetime.now()
        
        # Check limits
        if session.message_count > self.max_messages_per_session:
            logger.warning(f"Session {session_id} exceeded message limit")
            return False
        
        return True
    
    def increment_conversation_count(self, session_id: str) -> bool:
        """Increment conversation count"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.conversation_count += 1
        
        # Check limits
        if session.conversation_count > self.max_conversation_length:
            logger.warning(f"Session {session_id} exceeded conversation limit")
            return False
        
        return True
    
    def check_rate_limit(self, session_id: str) -> bool:
        """Check if session is rate limited"""
        session = self.get_session(session_id)
        if not session:
            return True  # Rate limited if no session
        
        return session.is_rate_limited(self.rate_limit_per_minute)
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._cleanup_session(session_id)
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        active_sessions = len(self.sessions)
        total_ips = len(self.ip_sessions)
        
        # Calculate average session duration
        now = datetime.now()
        total_duration = 0
        for session in self.sessions.values():
            duration = (now - session.created_at).total_seconds()
            total_duration += duration
        
        avg_duration = total_duration / active_sessions if active_sessions > 0 else 0
        
        return {
            'active_sessions': active_sessions,
            'unique_ips': total_ips,
            'average_session_duration': avg_duration,
            'session_timeout': self.session_timeout,
            'max_sessions_per_ip': self.max_sessions_per_ip
        }
    
    def _generate_session_id(self, ip_address: str, user_agent: str) -> str:
        """Generate unique session ID"""
        timestamp = str(time.time())
        random_uuid = str(uuid.uuid4())
        
        # Create hash from IP, user agent, timestamp, and random UUID
        hash_input = f"{ip_address}:{user_agent}:{timestamp}:{random_uuid}"
        session_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return f"demo_{session_hash[:16]}"
    
    def _generate_display_name(self) -> str:
        """Generate a friendly display name"""
        import random
        return random.choice(self.demo_names)
    
    def _check_ip_session_limit(self, ip_address: str) -> bool:
        """Check if IP has exceeded session limit"""
        if ip_address not in self.ip_sessions:
            return False
        
        # Clean up expired sessions for this IP first
        active_sessions = []
        for session_id in self.ip_sessions[ip_address]:
            if session_id in self.sessions and not self.sessions[session_id].is_expired():
                active_sessions.append(session_id)
        
        self.ip_sessions[ip_address] = active_sessions
        
        return len(active_sessions) >= self.max_sessions_per_ip
    
    def _cleanup_session(self, session_id: str):
        """Clean up a specific session"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        ip_address = session.ip_address
        
        # Remove from sessions
        del self.sessions[session_id]
        
        # Remove from IP tracking
        if ip_address in self.ip_sessions:
            if session_id in self.ip_sessions[ip_address]:
                self.ip_sessions[ip_address].remove(session_id)
            
            # Clean up empty IP entries
            if not self.ip_sessions[ip_address]:
                del self.ip_sessions[ip_address]
        
        logger.debug(f"Cleaned up session {session_id}")

# Flask integration helpers
def create_demo_auth_middleware(app, config):
    """Create Flask middleware for demo authentication"""
    
    auth_manager = DemoAuthManager(config)
    
    @app.before_request
    def before_request():
        from flask import request, session, g
        
        # Skip auth for static files and health checks
        if request.endpoint in ['static', 'health']:
            return
        
        # Get or create demo session
        demo_session_id = session.get('demo_session_id')
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        if not demo_session_id or not auth_manager.validate_session(demo_session_id, client_ip):
            # Create new demo session
            demo_session = auth_manager.create_guest_session(client_ip, user_agent)
            if demo_session:
                session['demo_session_id'] = demo_session.session_id
                g.demo_session = demo_session
            else:
                # Rate limited or error
                from flask import jsonify
                return jsonify({'error': 'Demo session limit exceeded'}), 429
        else:
            # Update existing session
            demo_session = auth_manager.get_session(demo_session_id)
            auth_manager.update_activity(demo_session_id)
            g.demo_session = demo_session
    
    # Cleanup task (run periodically)
    def cleanup_sessions():
        auth_manager.cleanup_expired_sessions()
    
    return auth_manager, cleanup_sessions

if __name__ == "__main__":
    # Test the demo auth system
    config = {
        'session_timeout': 1800,
        'max_sessions_per_ip': 3,
        'max_messages_per_session': 50,
        'max_conversation_length': 20,
        'requests_per_minute': 10
    }
    
    auth_manager = DemoAuthManager(config)
    
    # Create test session
    session = auth_manager.create_guest_session("192.168.1.1", "Test Browser")
    print(f"Created session: {session.session_id}")
    print(f"User: {session.display_name}")
    print(f"Stats: {auth_manager.get_session_stats()}")