import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class MessageStore:
    """Handles message storage and retrieval"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_backend = config.get('storage_backend', 'memory')
        
        # In-memory storage for development
        self.messages = {}
        self.conversations = {}
        
        # TODO: Implement PostgreSQL storage backend
        if self.storage_backend == 'postgresql':
            logger.warning("PostgreSQL backend not yet implemented, using in-memory storage")
    
    async def initialize(self):
        """Initialize storage backend"""
        logger.info(f"Initializing message store with backend: {self.storage_backend}")
        
        # TODO: Initialize database connections
        pass
    
    async def store_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Store a message"""
        message_id = message["id"]
        conversation_id = message["conversation_id"]
        
        # Store message
        self.messages[message_id] = message
        
        # Update conversation
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "id": conversation_id,
                "participants": [message["sender_id"], message["recipient_id"]],
                "created_at": message["timestamp"],
                "last_activity": message["timestamp"],
                "message_count": 0,
                "unread_count": 0
            }
        
        self.conversations[conversation_id]["message_count"] += 1
        self.conversations[conversation_id]["last_activity"] = message["timestamp"]
        self.conversations[conversation_id]["unread_count"] += 1
        
        # Update message status
        message["status"] = "stored"
        
        logger.info(f"Stored message {message_id}")
        return message
    
    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a message by ID"""
        return self.messages.get(message_id)
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages in a conversation"""
        # Get all messages for the conversation
        conv_messages = [
            msg for msg in self.messages.values()
            if msg["conversation_id"] == conversation_id
        ]
        
        # Sort by timestamp
        conv_messages.sort(key=lambda m: m["timestamp"])
        
        # Apply pagination
        return conv_messages[offset:offset + limit]
    
    async def get_conversation_metadata(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get conversation metadata"""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        
        return {
            "total_messages": 0,
            "unread_count": 0,
            "participants": [],
            "last_activity": None
        }
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        if message_id in self.messages:
            message = self.messages[message_id]
            
            if not message.get("read_at"):
                message["read_at"] = datetime.now().isoformat()
                message["status"] = "read"
                
                # Update conversation unread count
                conv_id = message["conversation_id"]
                if conv_id in self.conversations:
                    self.conversations[conv_id]["unread_count"] = max(
                        0, self.conversations[conv_id]["unread_count"] - 1
                    )
                
                logger.info(f"Marked message {message_id} as read")
            
            return True
        
        return False
    
    async def recall_message(self, message_id: str) -> bool:
        """Recall a message"""
        if message_id in self.messages:
            message = self.messages[message_id]
            message["recalled_at"] = datetime.now().isoformat()
            message["status"] = "recalled"
            message["content"] = "[Message recalled]"
            
            logger.info(f"Recalled message {message_id}")
            return True
        
        return False
    
    async def search_messages(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search messages"""
        results = []
        
        for message in self.messages.values():
            # Apply filters
            if conversation_id and message["conversation_id"] != conversation_id:
                continue
            
            if sender_id and message["sender_id"] != sender_id:
                continue
            
            if start_date and message["timestamp"] < start_date:
                continue
            
            if end_date and message["timestamp"] > end_date:
                continue
            
            # Search in content (case-insensitive)
            if query.lower() in message.get("content", "").lower():
                results.append(message)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def cleanup_expired_messages(self):
        """Clean up expired messages"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = datetime.now()
                expired_messages = []
                
                for message_id, message in self.messages.items():
                    if "expires_at" in message:
                        expires_at = datetime.fromisoformat(message["expires_at"])
                        if current_time > expires_at:
                            expired_messages.append(message_id)
                
                for message_id in expired_messages:
                    del self.messages[message_id]
                
                if expired_messages:
                    logger.info(f"Cleaned up {len(expired_messages)} expired messages")
                    
            except Exception as e:
                logger.error(f"Error in message cleanup: {str(e)}")
    
    async def close(self):
        """Close storage connections"""
        # TODO: Close database connections
        pass
    
    async def is_healthy(self) -> bool:
        """Health check"""
        try:
            # Basic health check
            _ = len(self.messages)
            return True
        except:
            return False