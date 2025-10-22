#!/usr/bin/env python3
"""
Pydantic models for STING Knowledge Service
Defines the data structures for Honey Jar management, search, and marketplace functionality
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

# Enums for validation
class HoneyJarType(str, Enum):
    public = "public"
    private = "private"
    team = "team"
    premium = "premium"
    enterprise = "enterprise"
    restricted = "restricted"

class HoneyJarStatus(str, Enum):
    active = "active"
    draft = "draft"
    archived = "archived"
    processing = "processing"
    error = "error"

class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

# Request Models
class HoneyJarCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the Honey Jar")
    description: str = Field(..., description="Description of the knowledge base")
    tags: List[str] = Field(default=[], description="Tags for categorization")
    type: HoneyJarType = Field(default=HoneyJarType.private, description="Access type")
    permissions: Optional[Dict[str, Any]] = Field(default=None, description="Permission settings")

class HoneyJarUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    type: Optional[HoneyJarType] = Field(None, description="Updated access type")
    permissions: Optional[Dict[str, Any]] = Field(None, description="Updated permissions")

class DocumentUploadRequest(BaseModel):
    honey_jar_id: str = Field(..., description="Target Honey Jar ID")
    metadata: Dict[str, Any] = Field(default={}, description="Document metadata")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    honey_jar_ids: Optional[List[str]] = Field(None, description="Specific Honey Jars to search")
    top_k: int = Field(default=5, description="Number of results to return")
    filters: Dict[str, Any] = Field(default={}, description="Additional filters")

class BeeContextRequest(BaseModel):
    query: str = Field(..., description="User query for context")
    conversation_history: List[Dict[str, Any]] = Field(default=[], description="Previous conversation")
    max_context_items: int = Field(default=3, description="Maximum context items to return")

class MarketplaceListingRequest(BaseModel):
    honey_jar_id: str = Field(..., description="Honey Jar to list")
    price: float = Field(default=0.0, description="Price (0 for free)")
    license_type: str = Field(default="Creative Commons", description="License type")
    description: str = Field(..., description="Marketplace description")

class MarketplaceSearchRequest(BaseModel):
    query: Optional[str] = Field(None, description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    license_type: Optional[str] = Field(None, description="License type filter")
    sort_by: str = Field(default="relevance", description="Sort criteria")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Items per page")

class BatchDocumentUpload(BaseModel):
    honey_jar_id: str = Field(..., description="Target Honey Jar ID")
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to upload")
    batch_metadata: Dict[str, Any] = Field(default={}, description="Batch processing metadata")

# Response Models
class DocumentInfo(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    upload_date: datetime
    status: DocumentStatus
    metadata: Dict[str, Any]

class HoneyJarResponse(BaseModel):
    id: str
    name: str
    description: str
    type: HoneyJarType
    status: HoneyJarStatus
    owner: str
    created_date: datetime
    last_updated: datetime
    tags: List[str]
    stats: Dict[str, Any]
    permissions: Optional[Dict[str, Any]] = None
    documents: Optional[List[DocumentInfo]] = None

class HoneyJarListResponse(BaseModel):
    honey_jars: List[HoneyJarResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class SearchResult(BaseModel):
    content: str
    score: float
    honey_jar_id: str
    honey_jar_name: str
    document_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default={})

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time: float
    suggested_queries: Optional[List[str]] = None

class BeeContextResponse(BaseModel):
    context_items: List[SearchResult]
    suggested_actions: List[str]
    relevant_honey_jars: List[str]
    confidence_score: float

class MarketplaceListing(BaseModel):
    id: str
    honey_jar_name: str
    description: str
    price: float
    license_type: str
    seller_name: str
    rating: float
    downloads: int
    tags: List[str]
    created_date: datetime
    preview_available: bool = False

class MarketplaceSearchResponse(BaseModel):
    listings: List[MarketplaceListing]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class BatchProcessingStatus(BaseModel):
    batch_id: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    progress_percentage: float
    estimated_completion: Optional[datetime] = None

class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str
    chroma_status: Optional[str] = None
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime