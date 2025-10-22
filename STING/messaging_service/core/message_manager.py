import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MessageManager:
    """Core message management functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_message_size = config.get('max_message_size', 1048576)
        self.message_retention_days = config.get('message_retention_days', 30)
    
    async def create_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        conversation_id: Optional[str] = None,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        encryption_required: bool = False
    ) -> Dict[str, Any]:
        """Create a new message"""
        
        # Generate IDs
        message_id = f"msg_{uuid.uuid4().hex}"
        if not conversation_id:
            conversation_id = f"conv_{sender_id}_{recipient_id}_{uuid.uuid4().hex[:8]}"
        
        # Create message structure
        message = {
            "id": message_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "conversation_id": conversation_id,
            "content": content,
            "content_type": content_type,
            "status": "created",
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "encrypted": False,
            "encryption_required": encryption_required,
            "read_at": None,
            "expires_at": (datetime.now() + timedelta(days=self.message_retention_days)).isoformat()
        }
        
        logger.info(f"Created message {message_id} from {sender_id} to {recipient_id}")
        return message
    
    async def can_recall_message(self, message: Dict[str, Any]) -> bool:
        """Check if a message can be recalled"""
        
        # Check if already recalled
        if message.get("recalled_at"):
            return False
        
        # Check if already read
        if message.get("read_at"):
            return False
        
        # Check time limit (5 minutes)
        created_at = datetime.fromisoformat(message["timestamp"])
        if datetime.now() - created_at > timedelta(minutes=5):
            return False
        
        return True
    
    async def get_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messaging analytics"""
        
        # This is a placeholder - implement with actual data
        return {
            "period": {
                "start": start_date or (datetime.now() - timedelta(days=7)).isoformat(),
                "end": end_date or datetime.now().isoformat()
            },
            "total_messages": 0,
            "unique_conversations": 0,
            "unique_users": 0,
            "messages_by_status": {
                "sent": 0,
                "delivered": 0,
                "read": 0,
                "failed": 0
            },
            "encryption_rate": 0.0,
            "average_response_time": 0.0
        }