#!/usr/bin/env python3
"""
STING Knowledge Service with Database Persistence
FastAPI service that provides honey jar knowledge management
with PostgreSQL database and ChromaDB vector support.
"""

import os
import logging

# Configure logging first before any other imports that might use it
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime
import json
import uuid
import chromadb
from chromadb.config import Settings
from pathlib import Path
import shutil
import tarfile
import zipfile
import tempfile
import fnmatch
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from core.nectar_processor import NectarProcessor
from semantic_search import SemanticSearchEngine
from auth.knowledge_auth import knowledge_auth
from auth.auth_dependencies import get_current_user_flexible
from sqlalchemy.orm import Session
from database import get_db, create_tables, HoneyJar, Document, HoneyJarRepository, DocumentRepository
from pii_integration import pii_integration
from config.security import mask_api_key, SECURITY_CONFIG

# HTTP client for email service API calls
import httpx

# Email service configuration
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL', 'https://app:5050/api/email')
EMAIL_API_TIMEOUT = 10.0  # seconds

async def send_email_notification(endpoint: str, data: dict) -> bool:
    """
    Send email notification via HTTP API to main app.
    
    Args:
        endpoint: Email API endpoint (e.g., 'document/approval')
        data: Email notification data
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        url = f"{EMAIL_SERVICE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=EMAIL_API_TIMEOUT, verify=False) as client:
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            else:
                logger.warning(f"Email API returned status {response.status_code}: {response.text}")
                return False
                
    except httpx.TimeoutException:
        logger.error(f"Email API timeout for endpoint {endpoint}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Email API request failed for {endpoint}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {endpoint}: {e}")
        return False

# Check if email service is available
email_service_available = True  # Assume available, will be checked on first use
logger.info("📧 Email notification system configured (HTTP API mode)")

# Configuration
KNOWLEDGE_PORT = int(os.getenv('KNOWLEDGE_PORT', '8090'))
KNOWLEDGE_HOST = os.getenv('KNOWLEDGE_HOST', '0.0.0.0')
CHROMA_URL = os.getenv('CHROMA_URL', 'http://chroma:8000')
UPLOAD_DIR = Path("/tmp/sting_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize ChromaDB client
try:
    chroma_client = chromadb.HttpClient(host=CHROMA_URL.replace('http://', '').split(':')[0], 
                                       port=int(CHROMA_URL.split(':')[2]))
    # Test connection
    chroma_client.heartbeat()
    chroma_available = True
    logger.info(f"✅ Connected to ChromaDB at {CHROMA_URL}")
except Exception as e:
    chroma_available = False
    chroma_client = None
    logger.warning(f"⚠️ ChromaDB not available at {CHROMA_URL}: {e}")
    logger.info("Running in fallback mode")

# Initialize bulk upload tracking
bulk_uploads = {}  # In-memory storage for bulk upload progress
upload_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent bulk uploads

# Simple Pydantic models
class HoneyJarCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the Honey Jar")
    description: str = Field(..., description="Description of the knowledge base")
    tags: List[str] = Field(default=[], description="Tags for categorization")
    type: str = Field(default="private", description="Type: public, private, or premium")
    permissions: Optional[Dict[str, Any]] = Field(default=None, description="Permission settings")

class HoneyJarResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    status: str
    owner: str
    created_date: datetime
    last_updated: datetime
    tags: List[str]
    stats: Dict[str, Any]

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")

class SearchResult(BaseModel):
    content: str
    score: float
    honey_jar_id: str
    honey_jar_name: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time: float

# Bulk upload models
class BulkUploadOptions(BaseModel):
    recursive: bool = Field(default=True, description="Process directories recursively")
    include_patterns: List[str] = Field(default=["*.md", "*.pdf", "*.docx", "*.txt"], description="File patterns to include")
    exclude_patterns: List[str] = Field(default=["node_modules", ".git", "*.tmp"], description="File patterns to exclude")
    retention_policy: str = Field(default="permanent", description="Retention policy: permanent, 30d, 90d, 1y, custom")
    custom_retention_days: Optional[int] = Field(default=None, description="Custom retention period in days")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing files")
    create_subdirectories: bool = Field(default=True, description="Create subdirectory structure in honey jar")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for all files")

class BulkUploadResponse(BaseModel):
    upload_id: str
    status: str
    files_queued: int
    estimated_completion: Optional[str] = None
    progress_url: str

class BulkUploadFileStatus(BaseModel):
    path: str
    status: str  # queued, processing, completed, failed
    document_id: Optional[str] = None
    size_bytes: Optional[int] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None

class BulkUploadProgress(BaseModel):
    upload_id: str
    status: str  # processing, completed, failed
    progress: Dict[str, int]  # total_files, processed, successful, failed, percentage
    files: List[BulkUploadFileStatus]
    completion_time: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="STING Knowledge Service - The Hive",
    description="Honey jar knowledge management system with database persistence",
    version="2.0.0"
)

# Add security audit middleware for API key operations
@app.middleware("http")
async def security_audit_middleware(request: Request, call_next):
    """Log API key operations for security auditing"""
    start_time = time.time()
    
    # Check if this is an API key request
    api_key = request.headers.get('X-API-Key')
    user_info = None
    
    if api_key and SECURITY_CONFIG.get('log_all_api_key_requests', True):
        # Mask API key for logging
        masked_key = mask_api_key(api_key) if SECURITY_CONFIG.get('mask_api_keys_in_logs', True) else api_key
        
        # Verify API key to get user context
        try:
            user_info = await knowledge_auth.verify_api_key(api_key)
            if user_info:
                logger.info(f"API Key Request: {request.method} {request.url.path} | Key: {masked_key} | User: {user_info.get('email')}")
            else:
                logger.warning(f"Invalid API Key Request: {request.method} {request.url.path} | Key: {masked_key}")
        except Exception as e:
            logger.error(f"API Key Verification Error: {e}")
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Log completion for API key requests
        if api_key and user_info:
            duration = time.time() - start_time
            logger.info(f"API Key Response: {response.status_code} | Duration: {duration:.3f}s | User: {user_info.get('email')}")
        
        return response
        
    except Exception as e:
        # Log failed requests
        if api_key:
            masked_key = mask_api_key(api_key) if SECURITY_CONFIG.get('mask_api_keys_in_logs', True) else api_key
            logger.error(f"API Key Request Failed: {request.method} {request.url.path} | Key: {masked_key} | Error: {e}")
        raise

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NectarProcessor
nectar_processor = NectarProcessor()

# Initialize Semantic Search Engine
semantic_search = SemanticSearchEngine(chroma_client if chroma_available else None)

# Pending documents for approval (kept in memory for now)
pending_documents_db = {}

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and sample data on startup"""
    logger.info("Starting up Knowledge Service with database persistence...")
    
    # Create database tables
    create_tables()
    logger.info("✅ Database tables created/verified")
    
    # Initialize sample honey jars if they don't exist
    db = next(get_db())
    repo = HoneyJarRepository(db)
    
    # Check if sample honey jars exist
    sample_jar = repo.get_honey_jar_by_name("Sample Security Knowledge")
    if not sample_jar:
        # Create sample honey jar
        sample_data = {
            "name": "Sample Security Knowledge",
            "description": "Sample honey jar with security-related documents",
            "type": "public",
            "owner": "system",
            "tags": ["security", "sample", "documentation"]
        }
        sample_jar = repo.create_honey_jar(sample_data)
        logger.info(f"✅ Created sample honey jar: {sample_jar.id}")
    
    support_jar = repo.get_honey_jar_by_name("General Support Knowledge")
    if not support_jar:
        # Create support honey jar
        support_data = {
            "name": "General Support Knowledge",
            "description": "General support documentation and guides",
            "type": "public",
            "owner": "system",
            "tags": ["support", "documentation", "guides"]
        }
        support_jar = repo.create_honey_jar(support_data)
        logger.info(f"✅ Created support honey jar: {support_jar.id}")
    
    db.close()
    
    # Seed sample documents if honey jars are empty
    db = next(get_db())
    repo = HoneyJarRepository(db)
    doc_repo = DocumentRepository(db)
    
    # Check if we need to seed documents
    total_docs = doc_repo.count_documents()
    if total_docs == 0:
        logger.info("No documents found, seeding sample documents...")
        
        # Import sample documents
        from seed_documents import SAMPLE_DOCUMENTS
        
        # Add documents to Sample Security Knowledge
        sample_jar = repo.get_honey_jar_by_name("Sample Security Knowledge")
        if sample_jar:
            security_docs = [
                {
                    "filename": "sting_overview.md",
                    "content_type": "text/markdown", 
                    "size_bytes": 1024,
                    "status": "processed",
                    "doc_metadata": {"sample": True},
                    "tags": ["platform", "overview", "documentation"]
                },
                {
                    "filename": "honey_jar_guide.md",
                    "content_type": "text/markdown",
                    "size_bytes": 2048, 
                    "status": "processed",
                    "doc_metadata": {"sample": True},
                    "tags": ["guide", "setup", "honey-jar"]
                },
                {
                    "filename": "threat_patterns.json",
                    "content_type": "application/json",
                    "size_bytes": 512,
                    "status": "processed", 
                    "doc_metadata": {"sample": True},
                    "tags": ["threats", "patterns", "detection"]
                }
            ]
            
            for doc_data in security_docs[:3]:  # First 3 docs for security jar
                doc = doc_repo.create_document(sample_jar.id, doc_data)
                logger.info(f"Created sample document: {doc.filename}")
                
                # Set embedding count
                doc.embedding_count = 5  # Approximate for sample docs
        
        # Add documents to General Support Knowledge  
        support_jar = repo.get_honey_jar_by_name("General Support Knowledge")
        if support_jar:
            support_docs = [
                {
                    "filename": "bee_chat_guide.md",
                    "content_type": "text/markdown",
                    "size_bytes": 1536,
                    "status": "processed",
                    "doc_metadata": {"sample": True},
                    "tags": ["bee", "chat", "assistant", "guide"]
                },
                {
                    "filename": "platform_faq.md", 
                    "content_type": "text/markdown",
                    "size_bytes": 2560,
                    "status": "processed",
                    "doc_metadata": {"sample": True},
                    "tags": ["faq", "support", "help"]
                }
            ]
            
            for doc_data in support_docs:
                doc = doc_repo.create_document(support_jar.id, doc_data)
                logger.info(f"Created sample document: {doc.filename}")
                
                # Set embedding count
                doc.embedding_count = 5  # Approximate for sample docs
        
        # Update honey jar statistics
        for jar in [sample_jar, support_jar]:
            if jar:
                repo.update_honey_jar_stats(jar.id)
                
        logger.info("✅ Sample documents seeded successfully")
        
        # Now index them in ChromaDB
        if chroma_available:
            logger.info("Indexing sample documents in ChromaDB...")
            db = next(get_db())
            
            # Index documents for each honey jar
            for jar in [sample_jar, support_jar]:
                if jar:
                    collection_name = f"honey_jar_{str(jar.id).replace('-', '_')}"
                    
                    try:
                        # Ensure collection exists
                        collection = semantic_search.get_or_create_collection(collection_name)
                        
                        # Get documents for this jar
                        docs = doc_repo.list_documents(str(jar.id))
                        
                        for doc in docs:
                            # Define content for each document
                            content_map = {
                                "sting_overview.md": """# STING Platform Overview

STING (Security Threat Intelligence Network Gateway) is a comprehensive cybersecurity platform that combines honey jar technology with AI-powered threat analysis.

## Key Features
- Honey Jar Deployment: Deploy various types of honey jars to detect and analyze threats
- AI-Powered Analysis: Use machine learning to identify patterns and predict threats
- Real-time Monitoring: Monitor all honey jar activity in real-time
- Threat Intelligence: Build a knowledge base of threat patterns and behaviors
- Automated Response: Automatically respond to detected threats""",
                                
                                "honey_jar_guide.md": """# Honey Jar Setup Guide

This guide walks you through setting up your first honey jar in STING.

## Step 1: Choose Honey Jar Type
STING supports multiple honey jar types: SSH, Web Application, Database, IoT Device honey jars.

## Step 2: Configure Network Settings
1. Navigate to Hive Manager
2. Click "Create New Honey Jar"
3. Configure network parameters
4. Set up logging and alerts

## Step 3: Deploy and Monitor
Once configured, deploy your honey jar and monitor incoming threats through the dashboard.""",
                                
                                "threat_patterns.json": """{"patterns": [
{"name": "Brute Force SSH", "indicators": ["multiple_failed_logins", "rapid_attempts"], "severity": "medium"},
{"name": "SQL Injection", "indicators": ["union_select", "drop_table"], "severity": "high"},
{"name": "Port Scanning", "indicators": ["sequential_ports", "common_ports"], "severity": "low"}
]}""",
                                
                                "bee_chat_guide.md": """# Bee Chat Assistant Guide

Bee is your AI-powered security assistant that helps analyze threats and provides recommendations.

## Getting Started with Bee
- Ask Questions: Ask Bee about security threats, best practices, or platform features
- Analyze Threats: Upload threat logs for AI-powered analysis
- Get Recommendations: Receive actionable security recommendations

## Example Questions
- "How do I set up a SSH honey jar?"
- "What are the latest threat patterns?"
- "Analyze this suspicious activity log"
- "Recommend security improvements for my network" """,
                                
                                "platform_faq.md": """# Frequently Asked Questions

## Q: What is a honey jar?
A: A honey jar is a decoy system designed to attract and analyze cyber threats.

## Q: How does Bee chat work?
A: Bee uses AI to analyze security data and provide insights based on the honey jar knowledge base.

## Q: Can I create custom honey jars?
A: Yes, STING supports custom honey jar configurations for specific security needs.

## Q: How are threats detected?
A: STING uses pattern matching, behavioral analysis, and machine learning to detect threats."""
                            }
                            
                            content = content_map.get(doc.filename, f"Sample content for {doc.filename}")
                            
                            # Add to ChromaDB
                            semantic_search.add_document(
                                collection_name,
                                doc_id=str(doc.id),
                                content=content,
                                metadata={
                                    "filename": doc.filename,
                                    "honey_jar_id": str(jar.id),
                                    "honey_jar_name": jar.name,
                                    "tags": doc.tags or []
                                }
                            )
                            logger.info(f"✅ Indexed {doc.filename} in ChromaDB")
                            
                    except Exception as e:
                        logger.error(f"Failed to index documents for {jar.name}: {e}")
            
            db.close()
            logger.info("✅ ChromaDB indexing complete")
            
    else:
        logger.info(f"Found {total_docs} existing documents, skipping seed")
    
    db.close()
    
    # Create ChromaDB collections for existing honey jars
    if chroma_available:
        db = next(get_db())
        repo = HoneyJarRepository(db)
        honey_jars = repo.list_honey_jars(limit=100)
        
        for honey_jar in honey_jars:
            collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
            try:
                # Get or create collection
                semantic_search.get_or_create_collection(collection_name)
                logger.info(f"✅ ChromaDB collection ready for honey jar: {honey_jar.name}")
            except Exception as e:
                logger.error(f"Failed to create collection for {honey_jar.name}: {e}")
        
        db.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "knowledge",
        "mode": "database",
        "database": "connected",
        "chroma_status": "connected" if chroma_available else "unavailable",
        "timestamp": datetime.now(),
        "version": "2.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "STING Knowledge Service",
        "description": "Honey jar knowledge management with database persistence",
        "endpoints": {
            "/health": "Service health check",
            "/honey-jars": "List honey jars",
            "/honey-jars/{id}": "Get honey jar details",
            "/search": "Search across honey jars",
            "/bee/context": "Get context for Bee chatbot"
        }
    }

# Honey Jar endpoints
@app.get("/honey-jars", response_model=List[HoneyJarResponse])
async def list_honey_jars(
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """List all honey jars accessible to the user"""
    repo = HoneyJarRepository(db)
    
    # Get all honey jars (in production, filter by user permissions)
    honey_jars = repo.list_honey_jars(limit=limit, offset=offset)
    
    # Convert to response format
    response = []
    for hj in honey_jars:
        response.append(HoneyJarResponse(
            id=str(hj.id),
            name=hj.name,
            description=hj.description,
            type=hj.type,
            status=hj.status,
            owner=hj.owner,
            created_date=hj.created_date,
            last_updated=hj.last_updated,
            tags=hj.tags or [],
            stats={
                "document_count": hj.document_count,
                "embedding_count": hj.embedding_count,
                "total_size_bytes": hj.total_size_bytes,
                "query_count": hj.query_count,
                "average_query_time": hj.average_query_time
            }
        ))
    
    return response

@app.get("/honey-jars/{honey_jar_id}", response_model=HoneyJarResponse)
async def get_honey_jar(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get honey jar details"""
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    return HoneyJarResponse(
        id=str(honey_jar.id),
        name=honey_jar.name,
        description=honey_jar.description,
        type=honey_jar.type,
        status=honey_jar.status,
        owner=honey_jar.owner,
        created_date=honey_jar.created_date,
        last_updated=honey_jar.last_updated,
        tags=honey_jar.tags or [],
        stats={
            "document_count": honey_jar.document_count,
            "embedding_count": honey_jar.embedding_count,
            "total_size_bytes": honey_jar.total_size_bytes,
            "query_count": honey_jar.query_count,
            "average_query_time": honey_jar.average_query_time
        }
    )

@app.post("/honey-jars", response_model=HoneyJarResponse)
async def create_honey_jar(
    request: HoneyJarCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Create a new honey jar"""
    repo = HoneyJarRepository(db)
    
    # Create honey jar data
    honey_jar_data = {
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "owner": current_user.get("email", "anonymous"),
        "tags": request.tags,
        "permissions": request.permissions or {}
    }
    
    # Create in database
    honey_jar = repo.create_honey_jar(honey_jar_data)
    
    # Create directory for uploads
    honey_jar_dir = UPLOAD_DIR / str(honey_jar.id)
    honey_jar_dir.mkdir(exist_ok=True)
    
    # Create ChromaDB collection if available
    if chroma_available:
        collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
        try:
            semantic_search.get_or_create_collection(collection_name)
            logger.info(f"Created ChromaDB collection for honey jar: {honey_jar.name}")
        except Exception as e:
            logger.error(f"Failed to create ChromaDB collection: {e}")
    
    return HoneyJarResponse(
        id=str(honey_jar.id),
        name=honey_jar.name,
        description=honey_jar.description,
        type=honey_jar.type,
        status=honey_jar.status,
        owner=honey_jar.owner,
        created_date=honey_jar.created_date,
        last_updated=honey_jar.last_updated,
        tags=honey_jar.tags or [],
        stats={
            "document_count": 0,
            "embedding_count": 0,
            "total_size_bytes": 0,
            "query_count": 0,
            "average_query_time": 0.0
        }
    )

@app.delete("/honey-jars/{honey_jar_id}")
async def delete_honey_jar(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Delete a honey jar and all its documents"""
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    # Check permissions
    if honey_jar.owner != current_user.get("email") and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Delete all documents
    doc_repo = DocumentRepository(db)
    documents = doc_repo.list_documents(honey_jar_id, limit=1000)
    for doc in documents:
        doc_repo.delete_document(str(doc.id))
    
    # Delete ChromaDB collection if available
    if chroma_available:
        collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
        try:
            chroma_client.delete_collection(collection_name)
            logger.info(f"Deleted ChromaDB collection for honey jar: {honey_jar.name}")
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection: {e}")
    
    # Delete directory
    honey_jar_dir = UPLOAD_DIR / str(honey_jar.id)
    if honey_jar_dir.exists():
        shutil.rmtree(honey_jar_dir)
    
    # Delete from database
    repo.delete_honey_jar(honey_jar_id)
    
    return {"message": "Honey jar deleted successfully"}

# Document endpoints
@app.post("/honey-jars/{honey_jar_id}/documents/upload")
async def upload_document(
    honey_jar_id: str,
    file: UploadFile = File(...),
    tags: List[str] = Form(default=[]),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Upload a document to a honey jar"""
    # Verify honey jar exists
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    # Check permissions
    user_email = current_user.get("email", "anonymous")
    user_role = current_user.get("role", "user")
    
    # Determine if approval is needed
    needs_approval = (
        honey_jar.type == "public" and 
        honey_jar.owner != user_email and 
        user_role != "admin"
    )
    
    # Save file
    honey_jar_dir = UPLOAD_DIR / str(honey_jar.id)
    honey_jar_dir.mkdir(exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_path = honey_jar_dir / f"{file_id}_{file.filename}"
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    doc_repo = DocumentRepository(db)
    document_data = {
        "honey_jar_id": honey_jar_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "status": "pending" if needs_approval else "processing",
        "tags": tags,
        "file_path": str(file_path),
        "doc_metadata": {  # Changed from "metadata" to "doc_metadata" to match the model
            "uploaded_by": user_email,
            "needs_approval": needs_approval
        }
    }
    
    document = doc_repo.create_document(honey_jar_id, document_data)
    
    if needs_approval:
        # Add to pending queue
        pending_documents_db[str(document.id)] = {
            "document_id": str(document.id),
            "honey_jar_id": honey_jar_id,
            "honey_jar_name": honey_jar.name,
            "filename": file.filename,
            "uploaded_by": user_email,
            "uploaded_at": datetime.now().isoformat(),
            "size_bytes": len(content)
        }
        
        # Send pending approval notification to admins
        if email_service_available:
            try:
                # Get admin emails - this could be improved to fetch from database
                admin_emails = [honey_jar.owner]  # Honey jar owner gets notified
                
                # Also send to system admins if we can identify them
                # For now, we'll just send to the honey jar owner
                pending_count = len(pending_documents_db)
                
                for admin_email in admin_emails:
                    email_data = {
                        'admin_email': admin_email,
                        'document_name': file.filename,
                        'honey_jar_name': honey_jar.name,
                        'uploader_name': user_email,
                        'pending_count': pending_count
                    }
                    email_sent = await send_email_notification('document/pending-approval', email_data)
                    if email_sent:
                        logger.info(f"📧 Pending approval notification sent to {admin_email}")
                    else:
                        logger.warning(f"📧 Failed to send pending approval notification to {admin_email}")
            except Exception as e:
                logger.error(f"Error sending pending approval notification: {e}")
        
        return {
            "document_id": str(document.id),
            "status": "pending_approval",
            "message": "Document uploaded successfully and is pending approval",
            "admin_notification_sent": email_service_available
        }
    else:
        # Process immediately
        try:
            # Process with NectarProcessor
            # Read the file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create a mock UploadFile for NectarProcessor
            import io
            class MockUploadFile:
                def __init__(self, content, filename, content_type):
                    self.file = io.BytesIO(content)
                    self.filename = filename
                    self.content_type = content_type
                
                async def read(self):
                    return self.file.read()
            
            mock_file = MockUploadFile(file_content, file.filename, file.content_type or "text/plain")
            
            # Extract text content
            extracted_text = await nectar_processor.extract_text(mock_file)
            
            # Perform PII detection on extracted text
            pii_results = await pii_integration.detect_pii_in_document(
                document_text=extracted_text,
                user_id=user_email,
                document_id=str(document.id),
                honey_jar_id=honey_jar_id,
                honey_jar_type=honey_jar.type,
                detection_mode="auto"
            )
            
            # Chunk the content
            chunks = await nectar_processor.chunk_content(
                extracted_text,
                chunk_size=1000,
                overlap=200,
                strategy="sentence"
            )
            
            processed_doc = {
                "chunks": chunks,
                "metadata": {
                    "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
                    "chunk_count": len(chunks),
                    "pii_analysis": pii_results
                }
            }
            
            # Update document with processing results
            doc_repo.update_document(str(document.id), {
                "status": "completed",
                "embedding_count": len(processed_doc.get("chunks", [])),
                "doc_metadata": {**document.doc_metadata, **processed_doc.get("metadata", {})}
            })
            
            # Add to ChromaDB if available
            if chroma_available and processed_doc.get("chunks"):
                # Add document chunks to semantic search
                semantic_search.add_document_chunks(
                    honey_jar_id=str(honey_jar.id),
                    document_id=str(document.id),
                    chunks=processed_doc["chunks"],
                    metadata={
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "uploaded_by": user_email
                    }
                )
            
            # Update honey jar stats
            repo.update_honey_jar(honey_jar_id, {
                "document_count": honey_jar.document_count + 1,
                "embedding_count": honey_jar.embedding_count + len(processed_doc.get("chunks", [])),
                "total_size_bytes": honey_jar.total_size_bytes + len(content)
            })
            
            return {
                "document_id": str(document.id),
                "status": "completed",
                "message": "Document uploaded and processed successfully",
                "chunks": len(processed_doc.get("chunks", [])),
                "pii_analysis": pii_results
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            doc_repo.update_document(str(document.id), {
                "status": "failed",
                "error_message": str(e)
            })
            raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.get("/honey-jars/{honey_jar_id}/documents")
async def list_documents(
    honey_jar_id: str,
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """List documents in a honey jar"""
    # Verify honey jar exists
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    # Get documents
    doc_repo = DocumentRepository(db)
    documents = doc_repo.list_documents(honey_jar_id, limit=limit, offset=offset)
    
    # Convert to response format
    response = []
    for doc in documents:
        response.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "content_type": doc.content_type,
            "size_bytes": doc.size_bytes,
            "upload_date": doc.upload_date.isoformat(),
            "status": doc.status,
            "tags": doc.tags or [],
            "metadata": doc.doc_metadata or {}
        })
    
    return {
        "honey_jar_id": honey_jar_id,
        "honey_jar_name": honey_jar.name,
        "documents": response,
        "total": len(response)
    }

# Search endpoints
@app.post("/search", response_model=SearchResponse)
async def search_honey_jars(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Search across all accessible honey jars"""
    start_time = datetime.now()
    
    results = []
    
    if semantic_search.available:
        # Use semantic search
        try:
            # Get all accessible honey jars
            repo = HoneyJarRepository(db)
            honey_jars = repo.list_honey_jars(limit=100)
            
            # Search each honey jar's collection
            for honey_jar in honey_jars:
                collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
                try:
                    jar_results = semantic_search.search(
                        query=request.query,
                        honey_jar_ids=[str(honey_jar.id)],
                        limit=request.top_k
                    )
                    
                    for result in jar_results:
                        results.append(SearchResult(
                            content=result["content"],
                            score=result["score"],
                            honey_jar_id=str(honey_jar.id),
                            honey_jar_name=honey_jar.name
                        ))
                except Exception as e:
                    logger.error(f"Error searching collection {collection_name}: {e}")
                    continue
            
            # Sort by score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:request.top_k]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Fall back to keyword search
    
    if not results:
        # Fallback to keyword search
        repo = HoneyJarRepository(db)
        doc_repo = DocumentRepository(db)
        honey_jars = repo.list_honey_jars(limit=100)
        
        query_lower = request.query.lower()
        
        for honey_jar in honey_jars:
            documents = doc_repo.list_documents(str(honey_jar.id), limit=100)
            
            for doc in documents:
                if doc.status != "completed":
                    continue
                
                # Simple keyword matching on filename
                if query_lower in doc.filename.lower():
                    results.append(SearchResult(
                        content=f"Document: {doc.filename}",
                        score=1.0,
                        honey_jar_id=str(honey_jar.id),
                        honey_jar_name=honey_jar.name
                    ))
        
        results = results[:request.top_k]
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        processing_time=processing_time
    )

# Bee Integration Endpoints
@app.post("/bee/context/public")
async def get_public_bee_context(request: dict, db: Session = Depends(get_db)):
    """Get relevant context from public honey jars only - no authentication required"""
    query = request.get("query", "")
    user_id = request.get("user_id", "anonymous")
    limit = request.get("limit", 5)
    
    logger.info(f"Public bee context request: query='{query}', user_id='{user_id}', limit={limit}")
    
    context_results = []
    
    # Get public honey jars
    repo = HoneyJarRepository(db)
    honey_jars = repo.list_honey_jars(limit=100)
    public_jars = [hj for hj in honey_jars if hj.type == "public"]
    
    if semantic_search.available:
        # Use semantic search
        for honey_jar in public_jars:
            collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
            try:
                jar_results = semantic_search.search(
                    query=query,
                    honey_jar_ids=[str(honey_jar.id)],
                    limit=limit
                )
                
                for result in jar_results:
                    context_results.append({
                        "content": result["content"],
                        "score": result["score"],
                        "metadata": {
                            "source": result.get("metadata", {}).get("filename", "Unknown"),
                            "honey_jar_id": str(honey_jar.id),
                            "honey_jar_name": honey_jar.name
                        }
                    })
            except Exception as e:
                logger.error(f"Error searching collection {collection_name}: {e}")
                # Fallback: search documents directly
                try:
                    doc_repo = DocumentRepository(db)
                    documents = doc_repo.list_documents(str(honey_jar.id))
                    logger.info(f"Fallback search: Found {len(documents)} documents in {honey_jar.name}")
                    for doc in documents:
                        if doc.status == "completed" and doc.doc_metadata:
                            extracted_text = doc.doc_metadata.get("extracted_text", "")
                            logger.debug(f"Checking document {doc.filename}, has text: {len(extracted_text)} chars")
                            if query.lower() in extracted_text.lower():
                                logger.info(f"Fallback match found in {doc.filename}")
                                context_results.append({
                                    "content": extracted_text,
                                    "score": 0.5,  # Default score for keyword match
                                    "metadata": {
                                        "source": doc.filename,
                                        "honey_jar_id": str(honey_jar.id),
                                        "honey_jar_name": honey_jar.name
                                    }
                                })
                except Exception as fallback_error:
                    logger.error(f"Fallback search also failed: {fallback_error}")
    else:
        # Fallback to keyword search
        doc_repo = DocumentRepository(db)
        query_lower = query.lower()
        
        for honey_jar in public_jars:
            documents = doc_repo.list_documents(str(honey_jar.id), limit=50)
            
            for doc in documents:
                if doc.status != "completed":
                    continue
                
                # Simple keyword matching
                if query_lower in doc.filename.lower():
                    context_results.append({
                        "content": f"From {doc.filename} in {honey_jar.name}",
                        "score": 0.5,
                        "metadata": {
                            "source": doc.filename,
                            "honey_jar_id": str(honey_jar.id),
                            "honey_jar_name": honey_jar.name
                        }
                    })
    
    # Sort by score and limit
    context_results.sort(key=lambda x: x["score"], reverse=True)
    context_results = context_results[:limit]
    
    logger.info(f"Returning {len(context_results)} results for public bee context query '{query}'")
    
    return {
        "results": context_results,
        "total_results": len(context_results),
        "search_type": "semantic" if semantic_search.available else "keyword"
    }

@app.post("/bee/context")
async def get_bee_context(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get relevant context for Bee chatbot"""
    query = request.get("query", "")
    user_id = request.get("user_id", "anonymous")
    limit = request.get("limit", 5)
    honey_jar_id = request.get("honey_jar_id", None)
    
    logger.info(f"Bee context request: query='{query}', user_id='{user_id}', limit={limit}, honey_jar_id={honey_jar_id}")
    
    context_results = []
    
    # Get honey jars to search
    repo = HoneyJarRepository(db)
    if honey_jar_id:
        honey_jar = repo.get_honey_jar(honey_jar_id)
        if honey_jar:
            honey_jars = [honey_jar]
        else:
            honey_jars = []
    else:
        honey_jars = repo.list_honey_jars(limit=100)
    
    if semantic_search.available:
        # Use semantic search
        for honey_jar in honey_jars:
            collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
            try:
                jar_results = semantic_search.search(
                    query=query,
                    honey_jar_ids=[str(honey_jar.id)],
                    limit=limit
                )
                
                for result in jar_results:
                    context_results.append({
                        "content": result["content"],
                        "score": result["score"],
                        "metadata": {
                            "source": result.get("metadata", {}).get("filename", "Unknown"),
                            "honey_jar_id": str(honey_jar.id),
                            "honey_jar_name": honey_jar.name
                        }
                    })
            except Exception as e:
                logger.error(f"Error searching collection {collection_name}: {e}")
                # Fallback: search documents directly
                try:
                    doc_repo = DocumentRepository(db)
                    documents = doc_repo.list_documents(str(honey_jar.id))
                    logger.info(f"Fallback search: Found {len(documents)} documents in {honey_jar.name}")
                    for doc in documents:
                        if doc.status == "completed" and doc.doc_metadata:
                            extracted_text = doc.doc_metadata.get("extracted_text", "")
                            logger.debug(f"Checking document {doc.filename}, has text: {len(extracted_text)} chars")
                            if query.lower() in extracted_text.lower():
                                logger.info(f"Fallback match found in {doc.filename}")
                                context_results.append({
                                    "content": extracted_text,
                                    "score": 0.5,  # Default score for keyword match
                                    "metadata": {
                                        "source": doc.filename,
                                        "honey_jar_id": str(honey_jar.id),
                                        "honey_jar_name": honey_jar.name
                                    }
                                })
                except Exception as fallback_error:
                    logger.error(f"Fallback search also failed: {fallback_error}")
    else:
        # Fallback to keyword search
        doc_repo = DocumentRepository(db)
        query_lower = query.lower()
        
        for honey_jar in honey_jars:
            documents = doc_repo.list_documents(str(honey_jar.id), limit=50)
            
            for doc in documents:
                if doc.status != "completed":
                    continue
                
                # Read file content for better search
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        with open(doc.file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query_lower in content.lower():
                                # Extract relevant snippet
                                idx = content.lower().find(query_lower)
                                start = max(0, idx - 200)
                                end = min(len(content), idx + 300)
                                snippet = content[start:end]
                                
                                context_results.append({
                                    "content": snippet,
                                    "score": 0.7,
                                    "metadata": {
                                        "source": doc.filename,
                                        "honey_jar_id": str(honey_jar.id),
                                        "honey_jar_name": honey_jar.name
                                    }
                                })
                    except Exception as e:
                        logger.error(f"Error reading file {doc.file_path}: {e}")
    
    # Sort by score and limit
    context_results.sort(key=lambda x: x["score"], reverse=True)
    context_results = context_results[:limit]
    
    return {
        "results": context_results,
        "total_results": len(context_results),
        "search_type": "semantic" if semantic_search.available else "keyword"
    }

# Admin endpoints for pending documents
@app.get("/admin/pending-documents")
async def list_pending_documents(
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """List all pending documents requiring approval (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "pending_documents": list(pending_documents_db.values()),
        "total": len(pending_documents_db)
    }

@app.post("/honey-jars/{honey_jar_id}/documents/{document_id}/approve")
async def approve_document(
    honey_jar_id: str,
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Approve a pending document"""
    # Check permissions
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    if honey_jar.owner != current_user.get("email") and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Remove from pending queue
    if document_id in pending_documents_db:
        del pending_documents_db[document_id]
    
    # Update document status and process
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Process the document
    try:
        # Read the file content
        with open(document.file_path, 'rb') as f:
            file_content = f.read()
        
        # Create a mock UploadFile for NectarProcessor
        import io
        class MockUploadFile:
            def __init__(self, content, filename, content_type):
                self.file = io.BytesIO(content)
                self.filename = filename
                self.content_type = content_type
            
            async def read(self):
                return self.file.read()
        
        mock_file = MockUploadFile(file_content, document.filename, document.content_type or "text/plain")
        
        # Extract text content
        extracted_text = await nectar_processor.extract_text(mock_file)
        
        # Perform PII detection on extracted text
        user_email = current_user.get("email", "anonymous")
        pii_results = await pii_integration.detect_pii_in_document(
            document_text=extracted_text,
            user_id=user_email,
            document_id=document_id,
            honey_jar_id=honey_jar_id,
            honey_jar_type=honey_jar.type,
            detection_mode="auto"
        )
        
        # Chunk the content
        chunks = await nectar_processor.chunk_content(
            extracted_text,
            chunk_size=1000,
            overlap=200,
            strategy="sentence"
        )
        
        processed_doc = {
            "chunks": chunks,
            "metadata": {
                "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
                "chunk_count": len(chunks),
                "pii_analysis": pii_results
            }
        }
        
        # Update document
        doc_repo.update_document(document_id, {
            "status": "completed",
            "embedding_count": len(processed_doc.get("chunks", [])),
            "metadata": {**document.doc_metadata, **processed_doc.get("metadata", {})}
        })
        
        # Add to ChromaDB
        if chroma_available and processed_doc.get("chunks"):
            # Add document chunks to semantic search
            semantic_search.add_document_chunks(
                honey_jar_id=str(honey_jar.id),
                document_id=str(document.id),
                chunks=processed_doc["chunks"],
                metadata={
                    "filename": document.filename,
                    "content_type": document.content_type or "text/plain"
                }
            )
        
        # Update honey jar stats
        repo.update_honey_jar(honey_jar_id, {
            "document_count": honey_jar.document_count + 1,
            "embedding_count": honey_jar.embedding_count + len(processed_doc.get("chunks", [])),
            "total_size_bytes": honey_jar.total_size_bytes + document.size_bytes
        })
        
        # Send approval notification email
        uploader_email = document.doc_metadata.get('uploaded_by') if document.doc_metadata else None
        if email_service_available and uploader_email:
            try:
                email_data = {
                    'recipient_email': uploader_email,
                    'document_name': document.filename,
                    'honey_jar_name': honey_jar.name,
                    'approver_name': current_user.get("email", "Admin")
                }
                email_sent = await send_email_notification('document/approval', email_data)
                if email_sent:
                    logger.info(f"📧 Approval notification sent to {uploader_email}")
                else:
                    logger.warning(f"📧 Failed to send approval notification to {uploader_email}")
            except Exception as e:
                logger.error(f"Error sending approval notification: {e}")
        
        return {
            "message": "Document approved and processed successfully",
            "document_id": document_id,
            "chunks": len(processed_doc.get("chunks", [])),
            "pii_analysis": pii_results,
            "email_notification_sent": email_service_available and uploader_email is not None
        }
        
    except Exception as e:
        logger.error(f"Error processing approved document: {e}")
        doc_repo.update_document(document_id, {
            "status": "failed",
            "error_message": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.post("/honey-jars/{honey_jar_id}/documents/{document_id}/reject")
async def reject_document(
    honey_jar_id: str,
    document_id: str,
    reason: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Reject a pending document"""
    # Check permissions
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    if honey_jar.owner != current_user.get("email") and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Remove from pending queue
    if document_id in pending_documents_db:
        del pending_documents_db[document_id]
    
    # Get document info for email notification before deleting
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_document(document_id)
    
    # Send rejection notification email
    uploader_email = document.doc_metadata.get('uploaded_by') if document and document.doc_metadata else None
    if email_service_available and document and uploader_email:
        try:
            email_data = {
                'recipient_email': uploader_email,
                'document_name': document.filename,
                'honey_jar_name': honey_jar.name,
                'reviewer_name': current_user.get("email", "Admin"),
                'rejection_reason': reason
            }
            email_sent = await send_email_notification('document/rejection', email_data)
            if email_sent:
                logger.info(f"📧 Rejection notification sent to {uploader_email}")
            else:
                logger.warning(f"📧 Failed to send rejection notification to {uploader_email}")
        except Exception as e:
            logger.error(f"Error sending rejection notification: {e}")
    
    # Delete the document
    doc_repo.delete_document(document_id)
    
    return {
        "message": "Document rejected and removed",
        "document_id": document_id,
        "reason": reason,
        "email_notification_sent": email_service_available and document and uploader_email is not None
    }

# PII Analysis Endpoints

@app.get("/honey-jars/{honey_jar_id}/pii-summary")
async def get_honey_jar_pii_summary(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Get PII detection summary for a honey jar"""
    # Verify honey jar exists
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    user_email = current_user.get("email", "anonymous")
    
    # Get PII summary from integration service
    pii_summary = await pii_integration.get_pii_summary_for_honey_jar(
        honey_jar_id=honey_jar_id,
        user_id=user_email
    )
    
    return {
        "honey_jar_id": honey_jar_id,
        "honey_jar_name": honey_jar.name,
        "pii_detection_available": pii_integration.is_available(),
        "summary": pii_summary
    }

@app.post("/honey-jars/{honey_jar_id}/documents/{document_id}/pii-rescan")
async def rescan_document_for_pii(
    honey_jar_id: str,
    document_id: str,
    detection_mode: Optional[str] = Query("auto", description="PII detection mode"),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Rescan a document for PII with specified detection mode"""
    # Verify honey jar and document exist
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_document(document_id)
    
    if not document or document.honey_jar_id != honey_jar_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not pii_integration.is_available():
        raise HTTPException(status_code=503, detail="PII detection service not available")
    
    # Check permissions (only admin, owner, or original uploader can rescan)
    user_email = current_user.get("email", "anonymous")
    user_role = current_user.get("role", "user")
    
    can_rescan = (
        user_role == "admin" or
        honey_jar.owner == user_email or
        document.doc_metadata.get("uploaded_by") == user_email
    )
    
    if not can_rescan:
        raise HTTPException(status_code=403, detail="Insufficient permissions to rescan document")
    
    try:
        # Read the document content
        if not document.file_path or not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="Document file not found")
        
        with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            document_text = f.read()
        
        # Perform PII detection
        pii_results = await pii_integration.detect_pii_in_document(
            document_text=document_text,
            user_id=user_email,
            document_id=document_id,
            honey_jar_id=honey_jar_id,
            honey_jar_type=honey_jar.type,
            detection_mode=detection_mode
        )
        
        # Update document metadata with new PII analysis
        updated_metadata = document.doc_metadata or {}
        updated_metadata["pii_analysis"] = pii_results
        updated_metadata["last_pii_scan"] = datetime.now().isoformat()
        updated_metadata["pii_scan_mode"] = detection_mode
        
        doc_repo.update_document(document_id, {
            "doc_metadata": updated_metadata
        })
        
        return {
            "document_id": document_id,
            "detection_mode": detection_mode,
            "pii_analysis": pii_results,
            "message": "PII rescan completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error rescanning document {document_id} for PII: {e}")
        raise HTTPException(status_code=500, detail=f"PII rescan failed: {str(e)}")

@app.get("/pii/status")
async def get_pii_service_status(
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get PII detection service status"""
    return {
        "pii_detection_available": pii_integration.is_available(),
        "supported_modes": ["auto", "general", "medical", "legal", "financial"] if pii_integration.is_available() else [],
        "service_info": {
            "audit_logging": True if pii_integration.is_available() else False,
            "compliance_frameworks": ["HIPAA", "GDPR", "PCI-DSS", "Attorney-Client", "CCPA"] if pii_integration.is_available() else []
        }
    }

# Bulk upload helper functions
def extract_archive(archive_file: str, extract_dir: str) -> bool:
    """Extract tar.gz, tar, or zip archive"""
    try:
        if archive_file.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(archive_file, 'r:gz') as tar:
                tar.extractall(extract_dir)
        elif archive_file.endswith('.tar'):
            with tarfile.open(archive_file, 'r') as tar:
                tar.extractall(extract_dir)
        elif archive_file.endswith('.zip'):
            with zipfile.ZipFile(archive_file, 'r') as zip_file:
                zip_file.extractall(extract_dir)
        else:
            logger.error(f"Unsupported archive format: {archive_file}")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to extract archive {archive_file}: {e}")
        return False

def should_include_file(file_path: str, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
    """Check if file should be included based on patterns"""
    file_name = os.path.basename(file_path)
    
    # Check exclude patterns first
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
            return False
    
    # Check include patterns
    for pattern in include_patterns:
        if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
            return True
    
    return False

def get_files_from_directory(directory: str, options: BulkUploadOptions) -> List[str]:
    """Get list of files to process based on options"""
    files = []
    directory_path = Path(directory)
    
    if options.recursive:
        pattern = "**/*"
    else:
        pattern = "*"
        
    for file_path in directory_path.rglob(pattern) if options.recursive else directory_path.glob(pattern):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(directory_path))
            if should_include_file(rel_path, options.include_patterns, options.exclude_patterns):
                files.append(str(file_path))
    
    return files

def process_bulk_upload(upload_id: str, honey_jar_id: str, files: List[str], options: BulkUploadOptions, current_user: Dict[str, Any]):
    """Process bulk upload in background thread"""
    try:
        with upload_lock:
            if upload_id not in bulk_uploads:
                return
            bulk_uploads[upload_id]['status'] = 'processing'
            bulk_uploads[upload_id]['progress']['total_files'] = len(files)
        
        # Create database session
        from database import get_db
        db = next(get_db())
        
        try:
            doc_repo = DocumentRepository(db)
            honey_jar_repo = HoneyJarRepository(db)
            
            # Verify honey jar exists
            honey_jar = honey_jar_repo.get_honey_jar(honey_jar_id)
            if not honey_jar:
                with upload_lock:
                    bulk_uploads[upload_id]['status'] = 'failed'
                    bulk_uploads[upload_id]['error'] = 'Honey jar not found'
                return
            
            processed = 0
            successful = 0
            failed = 0
            
            for file_path in files:
                try:
                    start_time = time.time()
                    
                    # Update progress
                    with upload_lock:
                        bulk_uploads[upload_id]['files'].append({
                            'path': file_path,
                            'status': 'processing',
                            'size_bytes': os.path.getsize(file_path)
                        })
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Create document
                    file_name = os.path.basename(file_path)
                    
                    # Determine subdirectory if enabled
                    rel_dir = ""
                    if options.create_subdirectories:
                        rel_dir = os.path.dirname(file_path)
                        if rel_dir and rel_dir != ".":
                            file_name = f"{rel_dir}/{file_name}"
                    
                    # Create metadata
                    metadata = {
                        'upload_id': upload_id,
                        'bulk_upload': True,
                        'retention_policy': options.retention_policy
                    }
                    if options.metadata:
                        metadata.update(options.metadata)
                    
                    # Add document to database
                    document_data = {
                        'filename': file_name,
                        'content_type': f'text/{os.path.splitext(file_name)[1][1:]}' if os.path.splitext(file_name)[1] else 'text/plain',
                        'size_bytes': len(file_content),
                        'status': 'approved' if honey_jar.owner == current_user.get('id') else 'pending',
                        'doc_metadata': metadata,
                        'tags': [],
                        'file_path': file_path
                    }
                    document = doc_repo.create_document(honey_jar_id, document_data)
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    # Update file status
                    with upload_lock:
                        for file_info in bulk_uploads[upload_id]['files']:
                            if file_info['path'] == file_path:
                                file_info.update({
                                    'status': 'completed',
                                    'document_id': document.id,
                                    'processing_time_ms': processing_time
                                })
                                break
                    
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {e}")
                    
                    # Update file status
                    with upload_lock:
                        for file_info in bulk_uploads[upload_id]['files']:
                            if file_info['path'] == file_path:
                                file_info.update({
                                    'status': 'failed',
                                    'error': str(e)
                                })
                                break
                    
                    failed += 1
                
                processed += 1
                
                # Update progress
                with upload_lock:
                    bulk_uploads[upload_id]['progress'].update({
                        'processed': processed,
                        'successful': successful,
                        'failed': failed,
                        'percentage': int((processed / len(files)) * 100)
                    })
        
        finally:
            db.close()
            
        # Mark as completed
        with upload_lock:
            bulk_uploads[upload_id]['status'] = 'completed'
            bulk_uploads[upload_id]['completion_time'] = datetime.now().isoformat()
            
    except Exception as e:
        logger.error(f"Bulk upload {upload_id} failed: {e}")
        with upload_lock:
            bulk_uploads[upload_id]['status'] = 'failed'
            bulk_uploads[upload_id]['error'] = str(e)

# Bulk upload endpoints
@app.post("/honey-jars/{honey_jar_id}/upload-directory", response_model=BulkUploadResponse)
async def upload_directory(
    honey_jar_id: str,
    directory: UploadFile = File(..., description="Tar/zip archive of directory"),
    options: str = Form(default='{}', description="JSON options for bulk upload"),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """Upload an entire directory to a honey jar"""
    
    try:
        # Parse options
        upload_options = BulkUploadOptions.parse_raw(options)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid options JSON: {str(e)}")
    
    # Verify honey jar exists and user has permission
    repo = HoneyJarRepository(db)
    honey_jar = repo.get_honey_jar(honey_jar_id)
    if not honey_jar:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    # Check upload permissions
    user_role = current_user.get('role', 'user')
    is_admin = user_role.lower() == 'admin'
    is_owner = honey_jar.owner == current_user.get('id')
    
    if not (is_admin or is_owner):
        if honey_jar.type != 'public':
            raise HTTPException(status_code=403, detail="No permission to upload to this honey jar")
    
    # Generate upload ID
    upload_id = f"bulk_upload_{uuid.uuid4().hex[:12]}"
    
    try:
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded archive
            archive_path = os.path.join(temp_dir, "archive")
            with open(archive_path, "wb") as f:
                content = await directory.read()
                f.write(content)
            
            # Extract archive
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir)
            
            if not extract_archive(archive_path, extract_dir):
                raise HTTPException(status_code=400, detail="Failed to extract archive")
            
            # Get list of files to process
            files = get_files_from_directory(extract_dir, upload_options)
            
            if not files:
                raise HTTPException(status_code=400, detail="No files found matching the criteria")
            
            # Initialize upload tracking
            with upload_lock:
                bulk_uploads[upload_id] = {
                    'upload_id': upload_id,
                    'status': 'queued',
                    'honey_jar_id': honey_jar_id,
                    'user_id': current_user.get('id'),
                    'progress': {
                        'total_files': len(files),
                        'processed': 0,
                        'successful': 0,
                        'failed': 0,
                        'percentage': 0
                    },
                    'files': [],
                    'created_at': datetime.now().isoformat()
                }
            
            # Copy files to permanent temp location for background processing
            perm_temp_dir = os.path.join(str(UPLOAD_DIR), upload_id)
            os.makedirs(perm_temp_dir)
            shutil.copytree(extract_dir, perm_temp_dir, dirs_exist_ok=True)
            
            # Get updated file paths
            updated_files = [f.replace(extract_dir, perm_temp_dir) for f in files]
            
            # Start background processing
            executor.submit(process_bulk_upload, upload_id, honey_jar_id, updated_files, upload_options, current_user)
            
            return BulkUploadResponse(
                upload_id=upload_id,
                status='queued',
                files_queued=len(files),
                progress_url=f"/uploads/{upload_id}/status"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")

@app.get("/uploads/{upload_id}/status", response_model=BulkUploadProgress)
async def get_upload_status(
    upload_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get status of a bulk upload"""
    
    with upload_lock:
        if upload_id not in bulk_uploads:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload_info = bulk_uploads[upload_id]
        
        # Check if user owns this upload
        if upload_info['user_id'] != current_user.get('id') and current_user.get('role', '').lower() != 'admin':
            raise HTTPException(status_code=403, detail="No permission to view this upload")
        
        return BulkUploadProgress(
            upload_id=upload_id,
            status=upload_info['status'],
            progress=upload_info['progress'],
            files=[BulkUploadFileStatus(**f) for f in upload_info['files']],
            completion_time=upload_info.get('completion_time')
        )

# Add to HoneyJarRepository class
def get_honey_jar_by_name(self, name: str) -> HoneyJar:
    """Get honey jar by name"""
    return self.db.query(HoneyJar).filter(HoneyJar.name == name).first()

# Update HoneyJarRepository to include the new method
HoneyJarRepository.get_honey_jar_by_name = get_honey_jar_by_name

if __name__ == "__main__":
    uvicorn.run(app, host=KNOWLEDGE_HOST, port=KNOWLEDGE_PORT, log_level="info")