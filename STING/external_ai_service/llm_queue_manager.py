#!/usr/bin/env python3
"""
LLM Queue Manager for STING External AI Service
Handles request queuing, priority management, and load balancing
"""

import os
import json
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
import aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_LLM_DB", "1"))  # Use separate DB for LLM queue

# Queue configuration
MAX_QUEUE_SIZE = int(os.getenv("LLM_MAX_QUEUE_SIZE", "1000"))
REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "300"))  # 5 minutes
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
QUEUE_POLL_INTERVAL = float(os.getenv("LLM_QUEUE_POLL_INTERVAL", "0.1"))  # 100ms

class UserRole(str, Enum):
    """User roles with associated priority levels"""
    ADMIN = "admin"
    QUEEN = "queen"
    WORKER = "worker"
    DRONE = "drone"
    ANONYMOUS = "anonymous"

# Priority mapping (higher number = higher priority)
ROLE_PRIORITY = {
    UserRole.ADMIN: 10,
    UserRole.QUEEN: 8,
    UserRole.WORKER: 5,
    UserRole.DRONE: 3,
    UserRole.ANONYMOUS: 1
}

class RequestStatus(str, Enum):
    """Request status in the queue"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class QueuedRequest(BaseModel):
    """Model for queued LLM requests"""
    request_id: str
    user_id: str
    user_role: UserRole
    priority: int
    request_type: str  # "chat", "report", "embedding", etc.
    payload: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: RequestStatus = RequestStatus.QUEUED
    retry_count: int = 0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class LLMQueueManager:
    """Manages LLM request queue with Redis backend"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.is_processing = False
        
        # Redis keys
        self.QUEUE_KEY = "llm:queue"
        self.PROCESSING_KEY = "llm:processing"
        self.COMPLETED_KEY = "llm:completed"
        self.STATUS_KEY = "llm:status"
        self.USER_QUOTA_KEY = "llm:quota"
        self.METRICS_KEY = "llm:metrics"
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            
            # Clear any stale processing tasks on startup
            await self.cleanup_stale_tasks()
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def cleanup_stale_tasks(self):
        """Clean up any tasks that were processing when service restarted"""
        try:
            # Get all processing tasks
            processing = await self.redis.hgetall(self.PROCESSING_KEY)
            
            for request_id, request_data in processing.items():
                request = QueuedRequest(**json.loads(request_data))
                
                # If task has been processing for more than timeout, mark as failed
                if request.started_at:
                    processing_time = datetime.now() - request.started_at
                    if processing_time.total_seconds() > REQUEST_TIMEOUT:
                        request.status = RequestStatus.TIMEOUT
                        request.error_message = "Request timed out during service restart"
                        await self.mark_request_complete(request)
                        await self.redis.hdel(self.PROCESSING_KEY, request_id)
                        logger.warning(f"Marked stale request {request_id} as timeout")
                else:
                    # Re-queue the request
                    await self.enqueue_request(request)
                    await self.redis.hdel(self.PROCESSING_KEY, request_id)
                    logger.info(f"Re-queued stale request {request_id}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up stale tasks: {e}")
    
    async def enqueue_request(
        self,
        user_id: str,
        user_role: str,
        request_type: str,
        payload: Dict[str, Any],
        priority_boost: int = 0
    ) -> str:
        """Add a request to the queue"""
        try:
            # Check queue size
            queue_size = await self.redis.zcard(self.QUEUE_KEY)
            if queue_size >= MAX_QUEUE_SIZE:
                raise Exception(f"Queue is full ({queue_size}/{MAX_QUEUE_SIZE})")
            
            # Check user quota (optional, can be implemented later)
            if not await self.check_user_quota(user_id, user_role):
                raise Exception("User quota exceeded")
            
            # Create request
            request_id = str(uuid.uuid4())
            role = UserRole(user_role.lower())
            priority = ROLE_PRIORITY.get(role, 1) + priority_boost
            
            request = QueuedRequest(
                request_id=request_id,
                user_id=user_id,
                user_role=role,
                priority=priority,
                request_type=request_type,
                payload=payload,
                created_at=datetime.now()
            )
            
            # Add to sorted set with priority as score (negative for reverse order)
            score = -priority * 1000000 + time.time()  # Priority first, then FIFO
            await self.redis.zadd(
                self.QUEUE_KEY,
                score,
                json.dumps(request.dict(), default=str)
            )
            
            # Update queue metrics
            await self.update_metrics("requests_queued")
            
            # Get queue position
            position = await self.get_queue_position(request_id)
            
            logger.info(f"Enqueued request {request_id} for user {user_id} with priority {priority}")
            
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue request: {e}")
            raise
    
    async def get_next_request(self) -> Optional[QueuedRequest]:
        """Get the highest priority request from queue"""
        try:
            # Pop highest priority item (lowest score)
            items = await self.redis.zrange(self.QUEUE_KEY, 0, 0)
            if not items:
                return None
            
            # Remove from queue and parse
            request_data = items[0]
            await self.redis.zrem(self.QUEUE_KEY, request_data)
            
            request = QueuedRequest(**json.loads(request_data))
            
            # Mark as processing
            request.started_at = datetime.now()
            request.status = RequestStatus.PROCESSING
            
            await self.redis.hset(
                self.PROCESSING_KEY,
                request.request_id,
                json.dumps(request.dict(), default=str)
            )
            
            # Update metrics
            await self.update_metrics("requests_processing")
            
            return request
            
        except Exception as e:
            logger.error(f"Failed to get next request: {e}")
            return None
    
    async def mark_request_complete(
        self,
        request: QueuedRequest,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Mark a request as complete"""
        try:
            request.completed_at = datetime.now()
            
            if error:
                request.status = RequestStatus.FAILED
                request.error_message = error
            else:
                request.status = RequestStatus.COMPLETED
                request.result = result
            
            # Store in completed set with TTL
            await self.redis.setex(
                f"{self.COMPLETED_KEY}:{request.request_id}",
                3600,  # Keep for 1 hour
                json.dumps(request.dict(), default=str)
            )
            
            # Remove from processing
            await self.redis.hdel(self.PROCESSING_KEY, request.request_id)
            
            # Update metrics
            if request.status == RequestStatus.COMPLETED:
                await self.update_metrics("requests_completed")
                processing_time = (request.completed_at - request.started_at).total_seconds()
                await self.update_metrics("total_processing_time", processing_time)
            else:
                await self.update_metrics("requests_failed")
            
            logger.info(f"Marked request {request.request_id} as {request.status}")
            
        except Exception as e:
            logger.error(f"Failed to mark request complete: {e}")
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a request"""
        try:
            # Check if completed
            completed_data = await self.redis.get(f"{self.COMPLETED_KEY}:{request_id}")
            if completed_data:
                request = QueuedRequest(**json.loads(completed_data))
                return {
                    "request_id": request_id,
                    "status": request.status,
                    "created_at": request.created_at,
                    "completed_at": request.completed_at,
                    "result": request.result,
                    "error": request.error_message
                }
            
            # Check if processing
            processing_data = await self.redis.hget(self.PROCESSING_KEY, request_id)
            if processing_data:
                request = QueuedRequest(**json.loads(processing_data))
                processing_time = (datetime.now() - request.started_at).total_seconds()
                return {
                    "request_id": request_id,
                    "status": request.status,
                    "created_at": request.created_at,
                    "started_at": request.started_at,
                    "processing_time": processing_time
                }
            
            # Check if in queue
            position = await self.get_queue_position(request_id)
            if position is not None:
                return {
                    "request_id": request_id,
                    "status": RequestStatus.QUEUED,
                    "queue_position": position
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get request status: {e}")
            return None
    
    async def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get position of request in queue"""
        try:
            # Get all queued items
            all_items = await self.redis.zrange(self.QUEUE_KEY, 0, -1)
            
            for i, item in enumerate(all_items):
                request_data = json.loads(item)
                if request_data.get("request_id") == request_id:
                    return i + 1
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get queue position: {e}")
            return None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        try:
            queue_size = await self.redis.zcard(self.QUEUE_KEY)
            processing_count = await self.redis.hlen(self.PROCESSING_KEY)
            
            # Get metrics
            metrics = await self.redis.hgetall(self.METRICS_KEY)
            
            # Calculate average processing time
            total_time = float(metrics.get("total_processing_time", 0))
            completed = int(metrics.get("requests_completed", 0))
            avg_time = total_time / completed if completed > 0 else 0
            
            return {
                "queue_size": queue_size,
                "processing_count": processing_count,
                "total_queued": int(metrics.get("requests_queued", 0)),
                "total_completed": completed,
                "total_failed": int(metrics.get("requests_failed", 0)),
                "average_processing_time": f"{avg_time:.2f} seconds",
                "queue_health": "healthy" if queue_size < MAX_QUEUE_SIZE * 0.8 else "busy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    async def check_user_quota(self, user_id: str, user_role: str) -> bool:
        """Check if user has available quota"""
        # TODO: Implement user quota logic
        # For now, always return True
        return True
    
    async def update_metrics(self, metric: str, value: float = 1):
        """Update queue metrics"""
        try:
            await self.redis.hincrbyfloat(self.METRICS_KEY, metric, value)
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a queued request"""
        try:
            # Check if in queue
            all_items = await self.redis.zrange(self.QUEUE_KEY, 0, -1)
            
            for item in all_items:
                request_data = json.loads(item)
                if request_data.get("request_id") == request_id:
                    # Remove from queue
                    await self.redis.zrem(self.QUEUE_KEY, item)
                    
                    # Mark as cancelled
                    request = QueuedRequest(**request_data)
                    request.status = RequestStatus.CANCELLED
                    request.completed_at = datetime.now()
                    
                    await self.redis.setex(
                        f"{self.COMPLETED_KEY}:{request_id}",
                        3600,
                        json.dumps(request.dict(), default=str)
                    )
                    
                    logger.info(f"Cancelled request {request_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel request: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Closed Redis connection")