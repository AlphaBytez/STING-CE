"""
Authentication and security for Public Bee service
"""

import hashlib
import secrets
import time
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import PublicBot, PublicBotAPIKey, PublicBotUsage

logger = logging.getLogger(__name__)

# Redis client for rate limiting
redis_client = None
try:
    redis_client = redis.from_url('redis://redis:6379/3')  # Use DB 3 for public bee
    redis_client.ping()
    logger.info("✅ Connected to Redis for rate limiting")
except Exception as e:
    logger.warning(f"⚠️ Redis not available for rate limiting: {e}")

security = HTTPBearer()

class APIKeyAuth:
    """API Key authentication for public bots"""
    
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Generate a new API key and its hash"""
        # Format: pb_<16-char-random>_<16-char-random>
        key = f"pb_{secrets.token_urlsafe(12)}_{secrets.token_urlsafe(12)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the display prefix of an API key"""
        return api_key[:8] + "..."

class RateLimiter:
    """Rate limiting for public bot API endpoints"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.default_window = 3600  # 1 hour in seconds
    
    def is_rate_limited(self, key: str, limit: int, window: int = None) -> tuple[bool, Dict[str, Any]]:
        """
        Check if a key is rate limited
        
        Args:
            key: Unique identifier (API key, IP, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds (default: 1 hour)
        
        Returns:
            Tuple of (is_limited, rate_info)
        """
        if not self.redis_client:
            # If Redis is not available, allow all requests
            return False, {'current': 0, 'limit': limit, 'reset_at': None}
        
        window = window or self.default_window
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        redis_key = f"rate_limit:{key}:{window_start}"
        
        try:
            # Get current count
            current = self.redis_client.get(redis_key)
            current = int(current) if current else 0
            
            if current >= limit:
                return True, {
                    'current': current,
                    'limit': limit,
                    'reset_at': window_start + window,
                    'retry_after': (window_start + window) - current_time
                }
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window)
            pipe.execute()
            
            return False, {
                'current': current + 1,
                'limit': limit,
                'reset_at': window_start + window,
                'retry_after': None
            }
        
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # If Redis fails, allow the request
            return False, {'current': 0, 'limit': limit, 'reset_at': None}

rate_limiter = RateLimiter()

class PublicBeeAuth:
    """Authentication and authorization for Public Bee endpoints"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_api_key(self, api_key: str) -> Optional[PublicBotAPIKey]:
        """Authenticate an API key"""
        if not api_key or not api_key.startswith('pb_'):
            return None
        
        key_hash = APIKeyAuth.hash_api_key(api_key)
        
        api_key_record = self.db.query(PublicBotAPIKey).filter(
            PublicBotAPIKey.key_hash == key_hash,
            PublicBotAPIKey.enabled == True
        ).first()
        
        if not api_key_record:
            return None
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
            return None
        
        return api_key_record
    
    def authorize_bot_access(self, api_key_record: PublicBotAPIKey, bot_id: str) -> Optional[PublicBot]:
        """Check if API key can access a specific bot"""
        bot = self.db.query(PublicBot).filter(
            PublicBot.id == bot_id,
            PublicBot.enabled == True
        ).first()
        
        if not bot:
            return None
        
        # Check if API key is authorized for this bot
        if api_key_record.bot_id != bot.id:
            return None
        
        return bot
    
    def check_ip_whitelist(self, api_key_record: PublicBotAPIKey, client_ip: str) -> bool:
        """Check if client IP is allowed"""
        if not api_key_record.allowed_ips:
            return True  # No restrictions
        
        return client_ip in api_key_record.allowed_ips
    
    def check_rate_limit(self, api_key_record: PublicBotAPIKey, bot: PublicBot, client_ip: str) -> tuple[bool, Dict[str, Any]]:
        """Check rate limits for the request"""
        # Use API key specific limit or bot's default
        limit = api_key_record.rate_limit or bot.rate_limit
        
        # Create a composite key for rate limiting
        rate_key = f"{api_key_record.id}:{client_ip}"
        
        return rate_limiter.is_rate_limited(rate_key, limit)
    
    def log_usage(self, bot: PublicBot, api_key_record: PublicBotAPIKey, request: Request, 
                  conversation_id: str, tokens_used: int, response_time_ms: int, 
                  success: bool = True, error_message: str = None):
        """Log usage statistics"""
        usage = PublicBotUsage(
            bot_id=bot.id,
            api_key=api_key_record.key_prefix,  # Store only prefix for privacy
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent'),
            referer=request.headers.get('referer'),
            conversation_id=conversation_id,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message
        )
        
        self.db.add(usage)
        
        # Update API key usage
        api_key_record.last_used_at = datetime.now(timezone.utc)
        api_key_record.usage_count += 1
        
        # Update bot stats
        bot.total_messages += 1
        bot.total_tokens += tokens_used
        
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            self.db.rollback()

def get_public_bee_auth(request: Request, db, credentials: HTTPAuthorizationCredentials = Depends(security)) -> tuple[PublicBot, PublicBotAPIKey]:
    """
    Dependency to authenticate and authorize public bee requests
    
    Returns:
        Tuple of (bot, api_key_record)
    """
    auth = PublicBeeAuth(db)
    
    # Extract bot ID from URL path
    bot_id = None
    path_parts = request.url.path.split('/')
    try:
        # URL format: /api/public/chat/{bot-id}/...
        if 'chat' in path_parts:
            bot_id_index = path_parts.index('chat') + 1
            if bot_id_index < len(path_parts):
                bot_id = path_parts[bot_id_index]
    except (ValueError, IndexError):
        pass
    
    if not bot_id:
        raise HTTPException(status_code=400, detail="Bot ID is required in URL path")
    
    # Authenticate API key
    api_key_record = auth.authenticate_api_key(credentials.credentials)
    if not api_key_record:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    # Authorize bot access
    bot = auth.authorize_bot_access(api_key_record, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found or access denied")
    
    # Check IP whitelist
    client_ip = request.client.host
    if not auth.check_ip_whitelist(api_key_record, client_ip):
        raise HTTPException(status_code=403, detail="IP address not allowed")
    
    # Check rate limits
    is_limited, rate_info = auth.check_rate_limit(api_key_record, bot, client_ip)
    if is_limited:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(rate_info.get('retry_after', 3600)),
                "X-RateLimit-Limit": str(rate_info.get('limit')),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info.get('reset_at'))
            }
        )
    
    return bot, api_key_record