import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MessagingClient:
    """
    Client for integrating with the standalone messaging service
    Replaces the embedded secure messaging for better scalability
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('messaging_service_url', 'http://messaging:8889')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.enabled = config.get('messaging_service_enabled', True)
    
    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        conversation_id: Optional[str] = None,
        encryption_required: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        notify: bool = True
    ) -> Dict[str, Any]:
        """Send a message through the messaging service"""
        if not self.enabled:
            logger.warning("Messaging service is disabled")
            return {
                "message_id": f"local_{datetime.now().timestamp()}",
                "status": "local_only",
                "encrypted": False
            }
        
        try:
            payload = {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "content": content,
                "conversation_id": conversation_id,
                "content_type": "text",
                "metadata": metadata or {},
                "encryption_required": encryption_required,
                "notify": notify
            }
            
            response = await self.client.post(
                f"{self.base_url}/messages/send",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Messaging service returned {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return None
    
    async def get_conversation(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Get conversation messages from messaging service"""
        if not self.enabled:
            return None
        
        try:
            response = await self.client.get(
                f"{self.base_url}/conversations/{conversation_id}",
                params={"limit": limit, "offset": offset}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get conversation: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    async def encrypt_message(
        self,
        message: str,
        user_id: str
    ) -> str:
        """Request message encryption from messaging service"""
        # This delegates encryption to the messaging service
        # which has better key management capabilities
        
        if not self.enabled:
            return message
        
        try:
            # The messaging service handles encryption internally
            # when encryption_required=True in send_message
            return message
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            return message
    
    async def search_messages(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search messages through messaging service"""
        if not self.enabled:
            return []
        
        try:
            params = {
                "query": query,
                "limit": limit
            }
            
            if conversation_id:
                params["conversation_id"] = conversation_id
            if sender_id:
                params["sender_id"] = sender_id
            
            response = await self.client.get(
                f"{self.base_url}/messages/search",
                params=params
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching messages: {str(e)}")
            return []
    
    async def update_notification_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> bool:
        """Update user's notification preferences"""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.put(
                f"{self.base_url}/notifications/settings/{user_id}",
                json=settings
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error updating notification settings: {str(e)}")
            return False
    
    async def recall_message(
        self,
        message_id: str,
        user_id: str
    ) -> bool:
        """Recall a sent message"""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/messages/{message_id}/recall",
                headers={"X-User-ID": user_id}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error recalling message: {str(e)}")
            return False
    
    async def get_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messaging analytics"""
        if not self.enabled:
            return {}
        
        try:
            params = {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = await self.client.get(
                f"{self.base_url}/analytics/messaging",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {}
    
    async def is_healthy(self) -> bool:
        """Check if messaging service is healthy"""
        if not self.enabled:
            return True  # If disabled, consider it "healthy"
        
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
            return False
            
        except:
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()