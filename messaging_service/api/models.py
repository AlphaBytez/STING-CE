from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class ContentType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    FILE = "file"
    IMAGE = "image"

class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    RECALLED = "recalled"

class SendMessageRequest(BaseModel):
    """Request to send a message"""
    sender_id: str = Field(..., description="ID of the sender")
    recipient_id: str = Field(..., description="ID of the recipient")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    content: str = Field(..., description="Message content")
    content_type: ContentType = Field(ContentType.TEXT, description="Type of content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    encryption_required: bool = Field(False, description="Whether to encrypt the message")
    notify: bool = Field(True, description="Whether to send notifications")
    notification_type: Optional[NotificationType] = Field(None, description="Preferred notification type")
    expires_at: Optional[datetime] = Field(None, description="Message expiration time")
    reply_to: Optional[str] = Field(None, description="ID of message being replied to")

class MessageResponse(BaseModel):
    """Response after sending a message"""
    message_id: str
    conversation_id: str
    status: MessageStatus
    timestamp: datetime
    encrypted: bool = False
    expires_at: Optional[datetime] = None

class Message(BaseModel):
    """Complete message object"""
    id: str
    sender_id: str
    recipient_id: str
    conversation_id: str
    content: str
    content_type: ContentType
    status: MessageStatus
    timestamp: datetime
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    encrypted: bool = False
    expires_at: Optional[datetime] = None
    reply_to: Optional[str] = None
    recalled_at: Optional[datetime] = None

class ConversationResponse(BaseModel):
    """Conversation with messages"""
    conversation_id: str
    messages: List[Message]
    total_messages: int
    unread_count: int
    participants: List[str]
    last_activity: datetime
    created_at: Optional[datetime] = None

class NotificationSettings(BaseModel):
    """User notification preferences"""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    quiet_hours: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "08:00"}
    notification_types: Dict[str, bool] = {
        "new_message": True,
        "message_recalled": True,
        "conversation_update": True,
        "mention": True
    }

class BulkMessageRequest(BaseModel):
    """Request to send multiple messages"""
    messages: List[SendMessageRequest]
    batch_id: Optional[str] = None
    priority: int = Field(5, ge=1, le=10, description="Priority level 1-10")

class MessageSearchRequest(BaseModel):
    """Search parameters for messages"""
    query: str
    conversation_ids: Optional[List[str]] = None
    sender_ids: Optional[List[str]] = None
    recipient_ids: Optional[List[str]] = None
    content_types: Optional[List[ContentType]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_recalled: bool = False
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)

class MessageAnalytics(BaseModel):
    """Messaging analytics data"""
    period: Dict[str, datetime]
    total_messages: int
    unique_conversations: int
    unique_users: int
    messages_by_status: Dict[MessageStatus, int]
    messages_by_type: Dict[ContentType, int]
    average_response_time: float
    peak_hours: List[int]
    encryption_rate: float
    recall_rate: float
    delivery_rate: float

# Chat History Models for Bee Conversations
class ChatMessage(BaseModel):
    """Chat message for Bee conversations"""
    id: str
    sender: str = Field(..., description="'user' or 'bee'")
    content: str = Field(..., description="Message content")
    timestamp: datetime
    message_type: str = Field(default="text", description="Type of message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ChatConversation(BaseModel):
    """Chat conversation metadata"""
    conversation_id: str
    user_id: str
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int
    is_archived: bool = False

class ChatHistoryResponse(BaseModel):
    """Response containing chat history"""
    conversations: List[ChatConversation]
    total_count: int

class ConversationMessagesResponse(BaseModel):
    """Response containing messages in a conversation"""
    conversation_id: str
    messages: List[ChatMessage]
    total_count: int

class SaveChatMessageRequest(BaseModel):
    """Request to save a chat message"""
    conversation_id: Optional[str] = None
    user_id: str
    sender: str = Field(..., description="'user' or 'bee'")
    content: str
    message_type: str = Field(default="text")
    metadata: Optional[Dict[str, Any]] = None