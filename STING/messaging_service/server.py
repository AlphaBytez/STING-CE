#!/usr/bin/env python3
"""
STING Messaging Service
Handles secure message delivery, encryption, and notifications
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import os
import logging
import asyncio
import uuid
from datetime import datetime
import uvicorn

from core.message_manager import MessageManager
from core.encryption_service import EncryptionService
from storage.message_store import MessageStore
from queue.message_queue import MessageQueue
from notifications.notification_service import NotificationService
from api.models import (
    SendMessageRequest, 
    MessageResponse, 
    ConversationResponse,
    NotificationSettings,
    ChatMessage,
    ChatConversation,
    ChatHistoryResponse,
    ConversationMessagesResponse,
    SaveChatMessageRequest
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get CORS origins from environment or use defaults
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else [
    "https://localhost:8443",
    "http://localhost:8443",
    "https://127.0.0.1:8443",
    "http://127.0.0.1:8443",
    "http://localhost",
    "https://localhost",
    "http://host.docker.internal:8443",
    "https://host.docker.internal:8443"
]

# Create FastAPI app
app = FastAPI(
    title="STING Messaging Service",
    description="Secure messaging service for STING platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
config = {
    "encryption_enabled": os.getenv('MESSAGING_ENCRYPTION_ENABLED', 'true').lower() == 'true',
    "queue_enabled": os.getenv('MESSAGING_QUEUE_ENABLED', 'true').lower() == 'true',
    "notifications_enabled": os.getenv('MESSAGING_NOTIFICATIONS_ENABLED', 'true').lower() == 'true',
    "storage_backend": os.getenv('MESSAGING_STORAGE_BACKEND', 'postgresql'),
    "redis_url": os.getenv('REDIS_URL', 'redis://redis:6379'),
    "database_url": os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/sting_messaging'),
    "max_message_size": int(os.getenv('MAX_MESSAGE_SIZE', '1048576')),  # 1MB
    "message_retention_days": int(os.getenv('MESSAGE_RETENTION_DAYS', '30')),
}

# Initialize services
message_manager = MessageManager(config)
encryption_service = EncryptionService(config)
message_store = MessageStore(config)
message_queue = MessageQueue(config)
notification_service = NotificationService(config)

# Security
security = HTTPBearer(auto_error=False)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting STING Messaging Service")
    
    # Initialize all services
    await message_store.initialize()
    await message_queue.initialize()
    await notification_service.initialize()
    
    # Start background tasks
    asyncio.create_task(message_queue.process_messages())
    asyncio.create_task(message_store.cleanup_expired_messages())
    
    logger.info("✅ Messaging Service ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Messaging Service")
    
    await message_queue.close()
    await message_store.close()
    await notification_service.close()

@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "STING Messaging Service",
        "version": "1.0.0",
        "status": "operational",
        "features": {
            "encryption": config["encryption_enabled"],
            "queue": config["queue_enabled"],
            "notifications": config["notifications_enabled"]
        },
        "endpoints": [
            {"path": "/messages/send", "method": "POST", "description": "Send a message"},
            {"path": "/messages/{message_id}", "method": "GET", "description": "Get a message"},
            {"path": "/conversations/{conversation_id}", "method": "GET", "description": "Get conversation"},
            {"path": "/messages/{message_id}/recall", "method": "DELETE", "description": "Recall a message"},
            {"path": "/notifications/settings", "method": "GET/PUT", "description": "Notification settings"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "messaging",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "message_store": await message_store.is_healthy(),
            "message_queue": await message_queue.is_healthy(),
            "encryption": encryption_service.is_healthy(),
            "notifications": await notification_service.is_healthy()
        }
    }
    
    # Check if all components are healthy
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status

@app.post("/messages/send", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Send a secure message"""
    try:
        # Validate authentication if required
        sender_id = request.sender_id
        if auth:
            # Verify sender identity matches auth token
            # TODO: Implement token verification
            pass
        
        # Check message size
        if len(request.content) > config["max_message_size"]:
            raise HTTPException(
                status_code=413,
                detail=f"Message too large. Maximum size: {config['max_message_size']} bytes"
            )
        
        # Create message
        message = await message_manager.create_message(
            sender_id=sender_id,
            recipient_id=request.recipient_id,
            conversation_id=request.conversation_id,
            content=request.content,
            content_type=request.content_type,
            metadata=request.metadata,
            encryption_required=request.encryption_required
        )
        
        # Encrypt if required
        if request.encryption_required and config["encryption_enabled"]:
            encrypted_content = await encryption_service.encrypt_message(
                content=message["content"],
                sender_id=message["sender_id"],
                recipient_id=message["recipient_id"]
            )
            message["content"] = encrypted_content
            message["encrypted"] = True
        
        # Store message
        stored_message = await message_store.store_message(message)
        
        # Queue for delivery
        if config["queue_enabled"]:
            await message_queue.enqueue_message(stored_message)
        
        # Send notifications
        if config["notifications_enabled"] and request.notify:
            background_tasks.add_task(
                notification_service.send_notification,
                recipient_id=request.recipient_id,
                message=stored_message,
                notification_type=request.notification_type
            )
        
        return MessageResponse(
            message_id=stored_message["id"],
            conversation_id=stored_message["conversation_id"],
            status="sent",
            timestamp=stored_message["timestamp"],
            encrypted=stored_message.get("encrypted", False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@app.get("/messages/{message_id}")
async def get_message(
    message_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Retrieve a message"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get message from store
        message = await message_store.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # TODO: Verify user has access to this message
        
        # Decrypt if needed
        if message.get("encrypted") and config["encryption_enabled"]:
            decrypted_content = await encryption_service.decrypt_message(
                encrypted_content=message["content"],
                recipient_id=message["recipient_id"]
            )
            message["content"] = decrypted_content
        
        # Mark as read
        await message_store.mark_as_read(message_id)
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve message")

@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all messages in a conversation"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # TODO: Verify user has access to this conversation
        
        # Get messages
        messages = await message_store.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        # Decrypt messages if needed
        for message in messages:
            if message.get("encrypted") and config["encryption_enabled"]:
                try:
                    decrypted_content = await encryption_service.decrypt_message(
                        encrypted_content=message["content"],
                        recipient_id=message["recipient_id"]
                    )
                    message["content"] = decrypted_content
                except:
                    message["content"] = "[Decryption failed]"
        
        # Get conversation metadata
        metadata = await message_store.get_conversation_metadata(conversation_id)
        
        return ConversationResponse(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=metadata.get("total_messages", len(messages)),
            unread_count=metadata.get("unread_count", 0),
            participants=metadata.get("participants", []),
            last_activity=metadata.get("last_activity")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")

@app.delete("/messages/{message_id}/recall")
async def recall_message(
    message_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Recall a sent message"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get message to verify ownership
        message = await message_store.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # TODO: Verify user is the sender
        
        # Check if message can be recalled (time limit, read status, etc.)
        if await message_manager.can_recall_message(message):
            # Recall the message
            success = await message_store.recall_message(message_id)
            
            if success:
                # Remove from queue if not yet delivered
                if config["queue_enabled"]:
                    await message_queue.remove_message(message_id)
                
                # Send recall notification
                if config["notifications_enabled"]:
                    await notification_service.send_recall_notification(
                        message=message
                    )
                
                return {"success": True, "message": "Message recalled"}
            else:
                raise HTTPException(status_code=400, detail="Failed to recall message")
        else:
            raise HTTPException(status_code=400, detail="Message cannot be recalled")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalling message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to recall message")

@app.get("/notifications/settings/{user_id}")
async def get_notification_settings(
    user_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's notification settings"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # TODO: Verify user access
    
    settings = await notification_service.get_user_settings(user_id)
    return settings

@app.put("/notifications/settings/{user_id}")
async def update_notification_settings(
    user_id: str,
    settings: NotificationSettings,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Update user's notification settings"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # TODO: Verify user access
    
    updated = await notification_service.update_user_settings(user_id, settings.dict())
    return {"success": updated, "settings": settings}

@app.post("/messages/bulk/send")
async def send_bulk_messages(
    messages: List[SendMessageRequest],
    background_tasks: BackgroundTasks,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Send multiple messages at once"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # TODO: Verify admin/support role
    
    results = []
    for msg_request in messages:
        try:
            result = await send_message(msg_request, background_tasks, auth)
            results.append({"success": True, "message_id": result.message_id})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total": len(messages),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }

@app.get("/messages/search")
async def search_messages(
    query: str,
    conversation_id: Optional[str] = None,
    sender_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Search messages"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # TODO: Implement message search with proper access control
    
    results = await message_store.search_messages(
        query=query,
        conversation_id=conversation_id,
        sender_id=sender_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }

@app.get("/analytics/messaging")
async def get_messaging_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get messaging analytics (admin only)"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # TODO: Verify admin role
    
    analytics = await message_manager.get_analytics(
        start_date=start_date,
        end_date=end_date
    )
    
    return analytics

# Chat History Endpoints for Bee Conversations
@app.get("/chat/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: str, limit: int = 50, offset: int = 0):
    """Get chat conversation history for a user"""
    try:
        # Get conversations where user is either sender or recipient
        conversations = await message_store.get_user_conversations(
            user_id=user_id,
            conversation_type="bee_chat",
            limit=limit,
            offset=offset
        )
        
        chat_conversations = []
        for conv in conversations:
            chat_conv = ChatConversation(
                conversation_id=conv["conversation_id"],
                user_id=user_id,
                title=conv.get("title", f"Chat {conv['conversation_id'][:8]}"),
                created_at=conv["created_at"],
                last_message_at=conv["last_message_at"],
                message_count=conv["message_count"],
                is_archived=conv.get("is_archived", False)
            )
            chat_conversations.append(chat_conv)
        
        return ChatHistoryResponse(
            conversations=chat_conversations,
            total_count=len(chat_conversations)
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")

@app.get("/chat/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(conversation_id: str, limit: int = 100, offset: int = 0):
    """Get all messages in a chat conversation"""
    try:
        messages = await message_store.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        chat_messages = []
        for msg in messages:
            chat_msg = ChatMessage(
                id=msg["id"],
                sender=msg["metadata"].get("sender", "user"),
                content=msg["content"],
                timestamp=msg["timestamp"],
                message_type=msg.get("content_type", "text"),
                metadata=msg.get("metadata", {})
            )
            chat_messages.append(chat_msg)
        
        return ConversationMessagesResponse(
            conversation_id=conversation_id,
            messages=chat_messages,
            total_count=len(chat_messages)
        )
        
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation messages")

@app.post("/chat/conversations/{conversation_id}/messages")
async def save_chat_message(conversation_id: str, request: SaveChatMessageRequest):
    """Save a chat message to conversation history"""
    try:
        # Create message using existing message manager
        message = await message_manager.create_message(
            sender_id=request.user_id if request.sender == "user" else "bee",
            recipient_id="bee" if request.sender == "user" else request.user_id,
            content=request.content,
            conversation_id=conversation_id,
            content_type=request.message_type,
            metadata={
                "sender": request.sender,
                "conversation_type": "bee_chat",
                "title": request.metadata.get("title") if request.metadata else None,
                **(request.metadata if request.metadata else {})
            }
        )
        
        # Store the message
        await message_store.store_message(message)
        
        return {"message_id": message["id"], "status": "saved"}
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to save chat message")

@app.post("/chat/conversations")
async def create_chat_conversation(user_id: str, title: str = None):
    """Create a new chat conversation"""
    try:
        conversation_id = f"chat_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Create initial conversation metadata
        metadata = {
            "conversation_type": "bee_chat",
            "title": title or f"Chat {conversation_id[:8]}",
            "created_by": user_id,
            "participants": [user_id, "bee"]
        }
        
        # Store conversation metadata
        await message_store.create_conversation(conversation_id, metadata)
        
        return {
            "conversation_id": conversation_id,
            "title": metadata["title"],
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating chat conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8889,
        log_level="info"
    )