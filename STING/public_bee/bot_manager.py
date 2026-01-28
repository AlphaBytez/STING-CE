"""
Public Bot management and configuration
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import PublicBot, PublicBotAPIKey
from auth import APIKeyAuth
import requests

logger = logging.getLogger(__name__)

class PublicBotManager:
    """Manages public bot configurations and operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_service_url = "http://knowledge:8090"
    
    def create_bot(self, 
                   name: str, 
                   display_name: str,
                   description: str,
                   honey_jar_ids: List[str],
                   system_prompt: str = None,
                   created_by: str = "admin") -> PublicBot:
        """Create a new public bot"""
        
        # Validate honey jars exist
        self._validate_honey_jars(honey_jar_ids)
        
        bot = PublicBot(
            name=name,
            display_name=display_name,
            description=description,
            honey_jar_ids=honey_jar_ids,
            system_prompt=system_prompt or self._get_default_system_prompt(),
            created_by=created_by
        )
        
        self.db.add(bot)
        self.db.commit()
        self.db.refresh(bot)
        
        logger.info(f"Created public bot: {bot.name} (ID: {bot.id})")
        return bot
    
    def create_api_key(self, 
                       bot_id: str, 
                       name: str,
                       created_by: str = "admin",
                       rate_limit: int = None,
                       max_concurrent: int = None,
                       allowed_ips: List[str] = None) -> tuple[str, PublicBotAPIKey]:
        """Create an API key for a bot"""
        
        # Verify bot exists
        bot = self.db.query(PublicBot).filter(PublicBot.id == bot_id).first()
        if not bot:
            raise ValueError(f"Bot with ID {bot_id} not found")
        
        # Generate API key
        api_key, key_hash = APIKeyAuth.generate_api_key()
        key_prefix = APIKeyAuth.get_key_prefix(api_key)
        
        api_key_record = PublicBotAPIKey(
            bot_id=bot_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            rate_limit=rate_limit,
            max_concurrent=max_concurrent,
            allowed_ips=allowed_ips or [],
            created_by=created_by
        )
        
        self.db.add(api_key_record)
        self.db.commit()
        self.db.refresh(api_key_record)
        
        logger.info(f"Created API key '{name}' for bot {bot.name}")
        return api_key, api_key_record
    
    def get_bot(self, bot_id: str) -> Optional[PublicBot]:
        """Get a bot by ID"""
        return self.db.query(PublicBot).filter(PublicBot.id == bot_id).first()
    
    def list_bots(self, created_by: str = None, enabled_only: bool = True) -> List[PublicBot]:
        """List all bots, optionally filtered by creator"""
        query = self.db.query(PublicBot)
        
        if enabled_only:
            query = query.filter(PublicBot.enabled == True)
        
        if created_by:
            query = query.filter(PublicBot.created_by == created_by)
        
        return query.order_by(PublicBot.created_at.desc()).all()
    
    def update_bot(self, bot_id: str, updates: Dict[str, Any]) -> Optional[PublicBot]:
        """Update a bot's configuration"""
        bot = self.get_bot(bot_id)
        if not bot:
            return None
        
        # Validate honey jars if being updated
        if 'honey_jar_ids' in updates:
            self._validate_honey_jars(updates['honey_jar_ids'])
        
        # Update allowed fields
        allowed_fields = [
            'display_name', 'description', 'honey_jar_ids', 'system_prompt', 
            'response_guidelines', 'allowed_domains', 'rate_limit', 
            'max_concurrent', 'enabled', 'public'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(bot, field, value)
        
        bot.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(bot)
        
        logger.info(f"Updated bot {bot.name}")
        return bot
    
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot and all its API keys"""
        bot = self.get_bot(bot_id)
        if not bot:
            return False
        
        # Delete all API keys for this bot
        self.db.query(PublicBotAPIKey).filter(PublicBotAPIKey.bot_id == bot_id).delete()
        
        # Delete the bot
        self.db.delete(bot)
        self.db.commit()
        
        logger.info(f"Deleted bot {bot.name} and all its API keys")
        return True
    
    def get_bot_api_keys(self, bot_id: str) -> List[PublicBotAPIKey]:
        """Get all API keys for a bot"""
        return self.db.query(PublicBotAPIKey).filter(
            PublicBotAPIKey.bot_id == bot_id
        ).order_by(PublicBotAPIKey.created_at.desc()).all()
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        api_key_record = self.db.query(PublicBotAPIKey).filter(
            PublicBotAPIKey.id == key_id
        ).first()
        
        if not api_key_record:
            return False
        
        api_key_record.enabled = False
        self.db.commit()
        
        logger.info(f"Revoked API key {api_key_record.name}")
        return True
    
    def query_honey_jars(self, bot: PublicBot, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Query the knowledge service for relevant content"""
        if not bot.honey_jar_ids:
            return []
        
        try:
            # Query each honey jar
            all_results = []
            
            for jar_id in bot.honey_jar_ids:
                response = requests.post(
                    f"{self.knowledge_service_url}/honey-jars/{jar_id}/search",
                    json={
                        "query": query,
                        "top_k": max_results
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    all_results.extend(results)
            
            # Sort by relevance score and return top results
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error querying honey jars: {e}")
            return []
    
    def create_demo_bot(self) -> PublicBot:
        """Create a demo bot with STING documentation"""
        
        # Check if demo bot already exists
        existing = self.db.query(PublicBot).filter(PublicBot.name == "sting-assistant").first()
        if existing:
            return existing
        
        # Create demo bot
        demo_bot = self.create_bot(
            name="sting-assistant",
            display_name="STING Assistant",
            description="AI assistant trained on STING platform documentation. Ask me anything about STING setup, features, and troubleshooting!",
            honey_jar_ids=["sting-platform-docs"],  # Will be created separately
            system_prompt=self._get_sting_demo_prompt(),
            created_by="system"
        )
        
        # Make it public and enable by default
        demo_bot.public = True
        demo_bot.enabled = True
        demo_bot.rate_limit = 50  # Lower rate limit for demo
        
        self.db.commit()
        
        # Create a demo API key
        demo_key, _ = self.create_api_key(
            bot_id=str(demo_bot.id),
            name="Demo API Key",
            created_by="system",
            rate_limit=50
        )
        
        logger.info(f"Created demo bot with API key: {demo_key[:16]}...")
        return demo_bot
    
    def _validate_honey_jars(self, honey_jar_ids: List[str]):
        """Validate that honey jars exist"""
        try:
            for jar_id in honey_jar_ids:
                response = requests.get(
                    f"{self.knowledge_service_url}/honey-jars/{jar_id}",
                    timeout=5
                )
                if response.status_code != 200:
                    raise ValueError(f"Honey jar {jar_id} not found or inaccessible")
        except requests.RequestException as e:
            logger.warning(f"Could not validate honey jars (knowledge service unavailable): {e}")
            # Allow creation even if validation fails (service might be starting up)
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for public bots"""
        return """You are a helpful AI assistant. You have access to a knowledge base and can answer questions based on the information provided. 

Guidelines:
- Be helpful, accurate, and concise
- If you don't know something based on the available knowledge, say so
- Do not share sensitive or personal information
- Stay professional and friendly
- Focus on being useful to the user

Please answer the user's question based on the available knowledge."""
    
    def _get_sting_demo_prompt(self) -> str:
        """Get system prompt for STING demo bot"""
        return """You are the STING Assistant, an AI helper trained on STING platform documentation. 

STING (Secure Trusted Intelligence and Networking Guardian) is a secure, private AI/LLM platform with features like:
- Passwordless authentication with WebAuthn/passkeys
- Honey Jar knowledge management system
- Bee Chat AI assistant
- Enterprise security and privacy
- Docker-based microservices architecture

Your role:
- Help users understand STING features and capabilities
- Provide setup and configuration guidance
- Troubleshoot common issues
- Explain concepts in user-friendly terms
- Direct users to relevant documentation when appropriate

Be helpful, accurate, and enthusiastic about STING's capabilities while staying professional."""