#!/usr/bin/env python3
"""
STING Knowledge Service with ChromaDB
FastAPI service that provides honey jar knowledge management
with ChromaDB vector database support.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import logging
import uvicorn
from datetime import datetime
import json
import uuid
import chromadb
from chromadb.config import Settings
from pathlib import Path
import shutil
from core.nectar_processor import NectarProcessor
from semantic_search import SemanticSearchEngine
from auth.knowledge_auth import knowledge_auth
from auth.auth_dependencies import get_current_user_flexible

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KNOWLEDGE_PORT = int(os.getenv('KNOWLEDGE_PORT', '8090'))
KNOWLEDGE_HOST = os.getenv('KNOWLEDGE_HOST', '0.0.0.0')
CHROMA_URL = os.getenv('CHROMA_URL', 'http://chroma:8000')

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

# Create FastAPI app
app = FastAPI(
    title="STING Knowledge Service - The Hive",
    description="Honey jar knowledge management system with ChromaDB support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
honey_jars_db = {}
documents_db = {}
pending_documents_db = {}  # For document approval workflow

# Initialize NectarProcessor
nectar_processor = NectarProcessor()

# Initialize Semantic Search Engine
semantic_search = SemanticSearchEngine(
    chroma_host=CHROMA_URL.replace('http://', '').split(':')[0],
    chroma_port=int(CHROMA_URL.split(':')[2]) if ':' in CHROMA_URL.split('//')[-1] else 8000
)

# Sample data
def initialize_sample_data():
    # STING Platform Documentation (public)
    sample_honey_jar = {
        "id": "sample-1",
        "name": "STING Platform Documentation",
        "description": "Core documentation and guides for the STING platform",
        "type": "public",
        "status": "active",
        "owner": "admin",
        "created_date": datetime.now(),
        "last_updated": datetime.now(),
        "tags": ["documentation", "platform", "guides"],
        "permissions": {
            "public_read": True,
            "allowed_roles": [],
            "allowed_teams": [],
            "allowed_users": []
        },
        "stats": {
            "document_count": 0,
            "embedding_count": 0,
            "total_size_bytes": 0,
            "last_accessed": datetime.now()
        }
    }
    
    # General Support Knowledge Base (public)
    support_honey_jar = {
        "id": "support-general",
        "name": "General Support Knowledge",
        "description": "FAQs, troubleshooting guides, and common solutions",
        "type": "public",
        "status": "active",
        "owner": "admin",
        "created_date": datetime.now(),
        "last_updated": datetime.now(),
        "tags": ["support", "faq", "troubleshooting"],
        "permissions": {
            "public_read": True,
            "allowed_roles": [],
            "allowed_teams": [],
            "allowed_users": []
        },
        "stats": {
            "document_count": 0,
            "embedding_count": 0,
            "total_size_bytes": 0,
            "last_accessed": datetime.now()
        }
    }
    
    honey_jars_db["sample-1"] = sample_honey_jar
    honey_jars_db["support-general"] = support_honey_jar
    
    # Load sample documents if they exist
    try:
        from seed_documents import initialize_sample_documents
        stats = initialize_sample_documents()
        
        # Update honey jar stats with sample documents
        honey_jars_db["sample-1"]["stats"]["document_count"] = stats["document_count"]
        honey_jars_db["sample-1"]["stats"]["embedding_count"] = stats["embedding_count"]
        honey_jars_db["sample-1"]["stats"]["total_size_bytes"] = stats["total_size_bytes"]
        
        # Load documents into memory
        sample_dir = Path("/tmp/sting_uploads/sample-1")
        db_file = sample_dir / "documents.json"
        if db_file.exists():
            with open(db_file, 'r') as f:
                documents_db["sample-1"] = json.load(f)
        
        logger.info(f"✅ Loaded {stats['document_count']} sample documents into honey jar 'sample-1'")
    except Exception as e:
        logger.warning(f"Could not load sample documents: {e}")

initialize_sample_data()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "knowledge",
        "mode": "full" if chroma_available else "minimal",
        "chroma_status": "connected" if chroma_available else "unavailable",
        "timestamp": datetime.now(),
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "STING Knowledge Service - Minimal Mode",
        "endpoints": [
            "/health",
            "/honey-jars",
            "/honey-jars/{id}",
            "/honey-jars/{id}/documents",
            "/honey-jars/{id}/documents/{doc_id}",
            "/search",
            "/bee/context"
        ],
        "note": f"ChromaDB status: {'connected' if chroma_available else 'unavailable'}"
    }

# Honey Jar Management Endpoints
@app.get("/honey-jars")
async def list_honey_jars(
    page: int = 1, 
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """List all honey jars that the current user has access to"""
    accessible_jars = []
    
    # Debug logging
    logger.info(f"Listing honey jars for user: {current_user.get('email')}, role: {current_user.get('role')}")
    logger.info(f"Total honey jars in DB: {len(honey_jars_db)}")
    
    for hj_id, hj_data in honey_jars_db.items():
        # Check if user can access this honey jar
        can_access = await knowledge_auth.can_access_honey_jar(current_user, hj_data)
        logger.info(f"Checking access to {hj_id}: type={hj_data.get('type')}, owner={hj_data.get('owner')}, can_access={can_access}")
        
        if can_access:
            accessible_jars.append(HoneyJarResponse(
                id=hj_data["id"],
                name=hj_data["name"],
                description=hj_data["description"],
                type=hj_data["type"],
                status=hj_data["status"],
                owner=hj_data["owner"],
                created_date=hj_data["created_date"],
                last_updated=hj_data["last_updated"],
                tags=hj_data["tags"],
                stats=hj_data["stats"]
            ))
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_jars = accessible_jars[start_idx:end_idx]
    
    # Log access attempt
    await knowledge_auth.log_access_attempt(
        current_user, "honey_jars", "list", True,
        {"count": len(accessible_jars)}
    )
    
    return {
        "items": paginated_jars,  # Changed from honey_jars to items for frontend compatibility
        "total_count": len(accessible_jars),
        "page": page,
        "page_size": page_size,
        "has_more": end_idx < len(accessible_jars)
    }

@app.get("/honey-jars/{honey_jar_id}")
async def get_honey_jar(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get a specific honey jar"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check access permission
    if not await knowledge_auth.can_access_honey_jar(current_user, hj_data):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "read", False
        )
        raise HTTPException(status_code=403, detail="Access denied to this honey jar")
    
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "read", True
    )
    
    return HoneyJarResponse(
        id=hj_data["id"],
        name=hj_data["name"],
        description=hj_data["description"],
        type=hj_data["type"],
        status=hj_data["status"],
        owner=hj_data["owner"],
        created_date=hj_data["created_date"],
        last_updated=hj_data["last_updated"],
        tags=hj_data["tags"],
        stats=hj_data["stats"]
    )

@app.post("/honey-jars")
async def create_honey_jar(
    request: HoneyJarCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Create a new honey jar"""
    # Check if user can create honey jars
    if not await knowledge_auth.can_create_honey_jar(current_user):
        await knowledge_auth.log_access_attempt(
            current_user, "honey_jars", "create", False
        )
        raise HTTPException(status_code=403, detail="You don't have permission to create honey jars")
    
    honey_jar_id = str(uuid.uuid4())
    
    # Set default permissions if not provided
    permissions = request.permissions or {}
    if not permissions:
        # Default permissions based on type
        if request.type == "public":
            permissions = {
                "public_read": True,
                "public_write": False,
                "allowed_users": [],
                "allowed_roles": [],
                "allowed_teams": []
            }
        else:
            permissions = {
                "public_read": False,
                "public_write": False,
                "allowed_users": [],
                "allowed_roles": [],
                "allowed_teams": []
            }
    
    honey_jar_data = {
        "id": honey_jar_id,
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "status": "active",
        "owner": current_user.get("email", "unknown"),
        "created_date": datetime.now(),
        "last_updated": datetime.now(),
        "tags": request.tags,
        "permissions": permissions,
        "stats": {
            "document_count": 0,
            "embedding_count": 0,
            "total_size_bytes": 0,
            "query_count": 0,
            "average_query_time": 0.0
        }
    }
    
    honey_jars_db[honey_jar_id] = honey_jar_data
    
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "create", True,
        {"name": request.name, "type": request.type}
    )
    
    return HoneyJarResponse(
        id=honey_jar_data["id"],
        name=honey_jar_data["name"],
        description=honey_jar_data["description"],
        type=honey_jar_data["type"],
        status=honey_jar_data["status"],
        owner=honey_jar_data["owner"],
        created_date=honey_jar_data["created_date"],
        last_updated=honey_jar_data["last_updated"],
        tags=honey_jar_data["tags"],
        stats=honey_jar_data["stats"]
    )

@app.delete("/honey-jars/{honey_jar_id}")
async def delete_honey_jar(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Delete a honey jar"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check delete permission
    if not await knowledge_auth.can_delete_honey_jar(current_user, hj_data):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "delete", False
        )
        raise HTTPException(status_code=403, detail="You don't have permission to delete this honey jar")
    
    del honey_jars_db[honey_jar_id]
    
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "delete", True,
        {"name": hj_data["name"]}
    )
    
    return {"message": "Honey jar deleted successfully"}

# Search Endpoints
@app.post("/search")
async def search_knowledge(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Search across honey jars with semantic search or fallback to keyword search"""
    import time
    start_time = time.time()
    
    # Log search attempt
    await knowledge_auth.log_access_attempt(
        current_user, "search", "query", True,
        {"query": request.query[:100], "top_k": request.top_k}
    )
    
    # Try semantic search first
    if semantic_search.available:
        try:
            # Perform semantic search
            semantic_results = semantic_search.search(
                query=request.query,
                honey_jar_ids=None,  # Search all honey jars
                limit=request.top_k
            )
            
            if semantic_results:
                # Convert to our response format
                search_results = []
                for result in semantic_results:
                    honey_jar = honey_jars_db.get(result['honey_jar_id'])
                    search_results.append(SearchResult(
                        content=result['content'][:500] + "..." if len(result['content']) > 500 else result['content'],
                        score=round(result['score'], 3),
                        honey_jar_id=result['honey_jar_id'],
                        honey_jar_name=honey_jar['name'] if honey_jar else "Unknown"
                    ))
                
                processing_time = time.time() - start_time
                return SearchResponse(
                    query=request.query,
                    results=search_results,
                    total_results=len(search_results),
                    processing_time=processing_time
                )
        
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to keyword search")
    
    # Search through our document chunks
    search_results = []
    query_lower = request.query.lower()
    
    # Extract meaningful keywords from query, ignoring common words
    stop_words = {"what", "is", "the", "a", "an", "how", "why", "when", "where", "who", "which", "are", "was", "were", "been", "be", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "them", "their", "there", "here", "about", "for", "with", "from", "to", "of", "in", "on", "at", "by"}
    
    # Split query into words and filter out stop words
    # Also remove punctuation from words
    import string
    query_words = []
    for word in query_lower.split():
        # Remove punctuation from the word
        word_clean = word.strip(string.punctuation)
        if word_clean not in stop_words and len(word_clean) >= 2:
            query_words.append(word_clean)
    
    # If no meaningful words after filtering, use original query
    if not query_words:
        query_words = [query_lower]
    
    logger.info(f"Search keywords: {query_words}")
    
    # Search through all documents in all honey jars the user has access to
    for hj_id, documents in documents_db.items():
        honey_jar = honey_jars_db.get(hj_id)
        if not honey_jar:
            continue
        
        # Check if user has access to this honey jar
        if not await knowledge_auth.can_access_honey_jar(current_user, honey_jar):
            continue
            
        for doc_id, document in documents.items():
            if document.get("status") != "ready":
                continue
                
            # Search through chunks
            chunks = document.get("chunks", [])
            for chunk_idx, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                
                # Count how many keywords match
                matching_keywords = 0
                total_frequency = 0
                
                for keyword in query_words:
                    if keyword in chunk_lower:
                        matching_keywords += 1
                        total_frequency += chunk_lower.count(keyword)
                
                # Only include chunks that match at least one keyword
                if matching_keywords > 0:
                    # Score based on percentage of keywords matched and frequency
                    keyword_coverage = matching_keywords / len(query_words)
                    frequency_bonus = min(0.3, total_frequency * 0.05)
                    score = min(0.95, (keyword_coverage * 0.6) + frequency_bonus)
                    
                    search_results.append(SearchResult(
                        content=chunk[:500] + "..." if len(chunk) > 500 else chunk,
                        score=score,
                        honey_jar_id=hj_id,
                        honey_jar_name=honey_jar["name"]
                    ))
    
    # Sort by score and limit results
    search_results.sort(key=lambda x: x.score, reverse=True)
    results = search_results[:request.top_k]
    
    # If no results, provide a default message
    if not results:
        results = [
            SearchResult(
                content=f"No results found for '{request.query}'. Try uploading more documents or using different search terms.",
                score=0.0,
                honey_jar_id="none",
                honey_jar_name="No Results"
            )
        ]
    processing_time = time.time() - start_time
    
    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        processing_time=processing_time
    )

# Public Bee Context Endpoint (for public honey jars only)
@app.post("/bee/context/public")
async def get_public_bee_context(request: dict):
    """Get relevant context from public honey jars only - no authentication required"""
    query = request.get("query", "")
    user_id = request.get("user_id", "anonymous")
    limit = request.get("limit", 5)
    
    logger.info(f"Public bee context request: query='{query}', user_id='{user_id}', limit={limit}")
    
    context_results = []
    
    # Fallback to keyword search for public honey jars
    query_lower = query.lower()
    
    # Extract meaningful keywords from query
    stop_words = {"what", "is", "the", "a", "an", "how", "why", "when", "where", "who", "which", "are", "was", "were", "been", "be", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "them", "their", "there", "here", "about", "for", "with", "from", "to", "of", "in", "on", "at", "by"}
    
    import string
    query_words = []
    for word in query_lower.split():
        word_clean = word.strip(string.punctuation)
        if word_clean not in stop_words and len(word_clean) >= 2:
            query_words.append(word_clean)
    
    if not query_words:
        query_words = [query_lower]
    
    logger.info(f"Public keyword search for words: {query_words}")
    
    # Search only through public honey jars
    for hj_id, documents in documents_db.items():
        honey_jar = honey_jars_db.get(hj_id)
        if not honey_jar:
            continue
        
        # Only search public honey jars
        if honey_jar.get("type") != "public":
            continue
            
        for doc_id, document in documents.items():
            if document.get("status") != "ready":
                continue
                
            # Search through chunks
            chunks = document.get("chunks", [])
            for chunk_idx, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                
                # Count keyword matches
                matching_keywords = 0
                total_frequency = 0
                
                for keyword in query_words:
                    if keyword in chunk_lower:
                        matching_keywords += 1
                        total_frequency += chunk_lower.count(keyword)
                
                # Only include chunks that match
                if matching_keywords > 0:
                    keyword_coverage = matching_keywords / len(query_words)
                    frequency_bonus = min(0.3, total_frequency * 0.05)
                    score = min(0.95, (keyword_coverage * 0.6) + frequency_bonus)
                    
                    # Handle timestamp
                    upload_date = document["upload_date"]
                    if isinstance(upload_date, str):
                        timestamp = upload_date
                    else:
                        timestamp = upload_date.isoformat()
                        
                    context_results.append({
                        "content": chunk[:500] + "..." if len(chunk) > 500 else chunk,
                        "score": score,
                        "metadata": {
                            "source": document["filename"],
                            "timestamp": timestamp,
                            "honey_jar_id": hj_id,
                            "honey_jar_name": honey_jar["name"]
                        }
                    })
    
    # Sort and limit results
    context_results.sort(key=lambda x: x["score"], reverse=True)
    context_results = context_results[:limit]
    
    return {
        "results": context_results,
        "total_results": len(context_results),
        "query": query,
        "processing_time": 0.05,
        "confidence_score": 0.85 if context_results else 0.0,
        "search_type": "keyword"
    }

# Bee Integration Endpoint
@app.post("/bee/context")
async def get_bee_context(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get relevant context for Bee chatbot using semantic search"""
    query = request.get("query", "")
    user_id = request.get("user_id", "anonymous")
    limit = request.get("limit", 5)
    honey_jar_id = request.get("honey_jar_id", None)
    
    logger.info(f"Bee context request: query='{query}', user_id='{user_id}', limit={limit}, honey_jar_id={honey_jar_id}")
    
    context_results = []
    
    # Try semantic search first
    if semantic_search.available:
        try:
            # Perform semantic search
            honey_jar_ids = [honey_jar_id] if honey_jar_id else None
            semantic_results = semantic_search.search(
                query=query,
                honey_jar_ids=honey_jar_ids,
                limit=limit
            )
            
            if semantic_results:
                # Convert to Bee's expected format
                for result in semantic_results:
                    metadata = result.get('metadata', {})
                    
                    # Handle timestamp
                    timestamp = metadata.get('timestamp', datetime.now().isoformat())
                    if not isinstance(timestamp, str):
                        timestamp = timestamp.isoformat()
                    
                    context_results.append({
                        "content": result['content'][:500] + "..." if len(result['content']) > 500 else result['content'],
                        "score": result['score'],
                        "metadata": {
                            "source": metadata.get('filename', 'Unknown'),
                            "timestamp": timestamp,
                            "honey_jar_id": result['honey_jar_id'],
                            "honey_jar_name": metadata.get('honey_jar_name', 'Unknown')
                        }
                    })
                
                # Return early if we have semantic results
                return {
                    "results": context_results,
                    "total_results": len(context_results),
                    "query": query,
                    "processing_time": 0.05,
                    "confidence_score": 0.85 if context_results else 0.0,
                    "search_type": "semantic"
                }
        
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to keyword search")
    
    # Fallback to keyword search
    query_lower = query.lower()
    
    # Extract meaningful keywords from query, ignoring common words
    stop_words = {"what", "is", "the", "a", "an", "how", "why", "when", "where", "who", "which", "are", "was", "were", "been", "be", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "them", "their", "there", "here", "about", "for", "with", "from", "to", "of", "in", "on", "at", "by"}
    
    # Split query into words and filter out stop words
    # Also remove punctuation from words
    import string
    query_words = []
    for word in query_lower.split():
        # Remove punctuation from the word
        word_clean = word.strip(string.punctuation)
        if word_clean not in stop_words and len(word_clean) >= 2:
            query_words.append(word_clean)
    
    # If no meaningful words after filtering, use original query
    if not query_words:
        query_words = [query_lower]
    
    logger.info(f"Keyword search for words: {query_words}")
    
    # If honey_jar_id specified, only search that jar
    search_jars = {honey_jar_id: documents_db.get(honey_jar_id, {})} if honey_jar_id else documents_db
    
    # Search through documents
    for hj_id, documents in search_jars.items():
        honey_jar = honey_jars_db.get(hj_id)
        if not honey_jar:
            continue
        
        # Check if user has access to this honey jar
        if not await knowledge_auth.can_access_honey_jar(current_user, honey_jar):
            continue
            
        for doc_id, document in documents.items():
            if document.get("status") != "ready":
                continue
                
            # Search through chunks
            chunks = document.get("chunks", [])
            for chunk_idx, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                
                # Count how many keywords match
                matching_keywords = 0
                total_frequency = 0
                
                for keyword in query_words:
                    if keyword in chunk_lower:
                        matching_keywords += 1
                        total_frequency += chunk_lower.count(keyword)
                
                # Only include chunks that match at least one keyword
                if matching_keywords > 0:
                    # Score based on percentage of keywords matched and frequency
                    keyword_coverage = matching_keywords / len(query_words)
                    frequency_bonus = min(0.3, total_frequency * 0.05)
                    score = min(0.95, (keyword_coverage * 0.6) + frequency_bonus)
                    
                    # Handle upload_date - could be string or datetime
                    upload_date = document["upload_date"]
                    if isinstance(upload_date, str):
                        timestamp = upload_date
                    else:
                        timestamp = upload_date.isoformat()
                        
                    context_results.append({
                        "content": chunk[:500] + "..." if len(chunk) > 500 else chunk,
                        "score": score,
                        "metadata": {
                            "source": document["filename"],
                            "timestamp": timestamp,
                            "honey_jar_id": hj_id,
                            "honey_jar_name": honey_jar["name"]
                        }
                    })
    
    # Sort by score and limit results
    context_results.sort(key=lambda x: x["score"], reverse=True)
    context_results = context_results[:limit]
    
    # If no results found, return empty
    if not context_results:
        context_results = []
    
    # Return format compatible with Bee chatbot expectations
    return {
        "results": context_results,  # Use 'results' key as expected by Bee
        "total_results": len(context_results),
        "query": query,
        "processing_time": 0.05,
        "confidence_score": 0.85 if context_results else 0.0
    }

# Document Management Endpoints
@app.post("/honey-jars/{honey_jar_id}/documents")
async def upload_documents(
    honey_jar_id: str,
    files: List[UploadFile] = File(...),
    metadata: str = Form(default="{}"),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Upload documents to a honey jar"""
    # Check if honey jar exists
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Determine if user can upload directly or needs approval
    user_role = current_user.get("role", "user")
    is_admin = user_role == "admin"
    is_owner = hj_data.get("owner") == current_user.get("email")
    is_public = hj_data.get("type") == "public"
    
    # Check permissions
    can_direct_upload = await knowledge_auth.can_edit_honey_jar(current_user, hj_data)
    requires_approval = False
    
    if not can_direct_upload:
        # For public honey jars, allow any authenticated user to upload to pending
        if is_public:
            requires_approval = True
            logger.info(f"User {current_user.get('email')} uploading to pending for public honey jar {honey_jar_id}")
        else:
            await knowledge_auth.log_access_attempt(
                current_user, f"honey_jar:{honey_jar_id}", "upload", False
            )
            raise HTTPException(status_code=403, detail="You don't have permission to upload to this honey jar")
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(f"/tmp/sting_uploads/{honey_jar_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_docs = []
    
    try:
        metadata_dict = json.loads(metadata)
    except:
        metadata_dict = {}
    
    for file in files:
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Save file temporarily
        file_path = upload_dir / f"{doc_id}_{file.filename}"
        
        # Reset file position before reading
        file.file.seek(0)
        content = await file.read()
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Reset file position for NectarProcessor
        file.file.seek(0)
        
        # Create document record
        document = {
            "id": doc_id,
            "honey_jar_id": honey_jar_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": file_path.stat().st_size,
            "upload_date": datetime.now(),
            "status": "processing",
            "metadata": metadata_dict,
            "file_path": str(file_path),
            "uploaded_by": current_user.get("email"),
            "uploaded_by_id": current_user.get("id"),
            "approval_status": "pending" if requires_approval else "approved",
            "approved_by": current_user.get("email") if not requires_approval else None,
            "approved_date": datetime.now() if not requires_approval else None
        }
        
        # Store document info in appropriate database
        if requires_approval:
            # Store in pending documents
            if honey_jar_id not in pending_documents_db:
                pending_documents_db[honey_jar_id] = {}
            pending_documents_db[honey_jar_id][doc_id] = document
        else:
            # Store in main documents
            if honey_jar_id not in documents_db:
                documents_db[honey_jar_id] = {}
            documents_db[honey_jar_id][doc_id] = document
        
        # Update honey jar stats
        honey_jar = honey_jars_db[honey_jar_id]
        honey_jar["stats"]["document_count"] = honey_jar["stats"].get("document_count", 0) + 1
        honey_jar["stats"]["total_size_bytes"] = honey_jar["stats"].get("total_size_bytes", 0) + document["size_bytes"]
        honey_jar["last_updated"] = datetime.now()
        
        # Process the document with NectarProcessor
        try:
            # Extract text content
            extracted_text = await nectar_processor.extract_text(file)
            
            # Chunk the content
            chunks = await nectar_processor.chunk_content(
                extracted_text,
                chunk_size=1000,
                overlap=200,
                strategy="sentence"
            )
            
            # Store extracted text and chunks with document
            document["extracted_text"] = extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
            document["chunk_count"] = len(chunks)
            document["status"] = "ready"
            
            # Update stats
            honey_jar["stats"]["embedding_count"] = honey_jar["stats"].get("embedding_count", 0) + len(chunks)
            
            # Store chunks for later use
            document["chunks"] = chunks
            
            # Add chunks to ChromaDB for semantic search
            if semantic_search.available:
                chunk_metadata = {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "timestamp": datetime.now().isoformat(),
                    "honey_jar_name": honey_jar["name"]
                }
                semantic_search.add_document_chunks(
                    honey_jar_id=honey_jar_id,
                    document_id=doc_id,
                    chunks=chunks,
                    metadata=chunk_metadata
                )
            
            logger.info(f"Processed {file.filename}: extracted {len(extracted_text)} chars, created {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to process document {file.filename}: {e}")
            document["status"] = "error"
            document["error"] = str(e)
        
        uploaded_docs.append({
            "id": doc_id,
            "filename": file.filename,
            "size_bytes": document["size_bytes"],
            "status": document["status"],
            "approval_status": document["approval_status"]
        })
    
    # Log successful upload
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "upload", True,
        {"files_count": len(uploaded_docs), "total_size": sum(d["size_bytes"] for d in uploaded_docs)}
    )
    
    message = f"Successfully uploaded {len(uploaded_docs)} documents"
    if requires_approval:
        message += ". Documents are pending admin approval."
    
    return {
        "honey_jar_id": honey_jar_id,
        "documents_uploaded": len(uploaded_docs),
        "documents": uploaded_docs,
        "message": message,
        "requires_approval": requires_approval
    }

@app.get("/honey-jars/{honey_jar_id}/documents")
async def get_documents(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get list of documents in a honey jar"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check access permission
    if not await knowledge_auth.can_access_honey_jar(current_user, hj_data):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "list_documents", False
        )
        raise HTTPException(status_code=403, detail="Access denied to this honey jar")
    
    # Get documents for this honey jar
    jar_docs = documents_db.get(honey_jar_id, {})
    
    documents = []
    for doc_id, doc in jar_docs.items():
        documents.append({
            "id": doc["id"],
            "filename": doc["filename"],
            "content_type": doc["content_type"],
            "size_bytes": doc["size_bytes"],
            "upload_date": doc["upload_date"],
            "status": doc["status"],
            "metadata": doc.get("metadata", {})
        })
    
    return {
        "honey_jar_id": honey_jar_id,
        "total_documents": len(documents),
        "documents": documents
    }

@app.delete("/honey-jars/{honey_jar_id}/documents/{document_id}")
async def delete_document(
    honey_jar_id: str, 
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Delete a document from a honey jar"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check edit permission
    if not await knowledge_auth.can_edit_honey_jar(current_user, hj_data):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "delete_document", False
        )
        raise HTTPException(status_code=403, detail="You don't have permission to delete documents from this honey jar")
    
    if honey_jar_id not in documents_db or document_id not in documents_db[honey_jar_id]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get document info
    document = documents_db[honey_jar_id][document_id]
    
    # Delete file if it exists
    file_path = Path(document.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
    
    # Update honey jar stats
    honey_jar = honey_jars_db[honey_jar_id]
    honey_jar["stats"]["document_count"] = max(0, honey_jar["stats"].get("document_count", 1) - 1)
    honey_jar["stats"]["total_size_bytes"] = max(0, honey_jar["stats"].get("total_size_bytes", 0) - document["size_bytes"])
    honey_jar["stats"]["embedding_count"] = max(0, honey_jar["stats"].get("embedding_count", 30) - 30)
    honey_jar["last_updated"] = datetime.now()
    
    # Remove document from db
    del documents_db[honey_jar_id][document_id]
    
    return {
        "message": f"Document {document_id} deleted successfully",
        "filename": document["filename"]
    }

@app.post("/honey-jars/{honey_jar_id}/ripen")
async def ripen_honey_jar(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """
    Ripen (reprocess) all documents in a honey jar.
    This refreshes text extraction, chunks, and embeddings.
    """
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check permission - only admins and owners can ripen
    user_role = current_user.get("role", "user")
    is_admin = user_role == "admin"
    is_owner = hj_data.get("owner") == current_user.get("email")
    
    if not (is_admin or is_owner):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "ripen", False
        )
        raise HTTPException(
            status_code=403, 
            detail="Only administrators and honey jar owners can ripen honey jars"
        )
    
    # Get all documents for this honey jar
    jar_docs = documents_db.get(honey_jar_id, {})
    if not jar_docs:
        return {
            "message": "No documents to ripen",
            "processed": 0,
            "failed": 0
        }
    
    processed_count = 0
    failed_count = 0
    total_chunks = 0
    
    # Clear existing ChromaDB collection if semantic search is available
    if semantic_search.available:
        collection = semantic_search.get_or_create_collection(honey_jar_id)
        if collection:
            try:
                # Delete all existing embeddings for this honey jar
                collection.delete(where={"honey_jar_id": honey_jar_id})
                logger.info(f"Cleared existing embeddings for honey jar {honey_jar_id}")
            except Exception as e:
                logger.warning(f"Failed to clear embeddings: {e}")
    
    # Process each document
    for doc_id, document in jar_docs.items():
        try:
            # Skip if file doesn't exist
            file_path = Path(document.get("file_path", ""))
            if not file_path.exists():
                logger.warning(f"File not found for document {doc_id}: {file_path}")
                failed_count += 1
                continue
            
            # Create a mock UploadFile object for NectarProcessor
            class MockUploadFile:
                def __init__(self, filepath, filename, content_type):
                    self.file = open(filepath, 'rb')
                    self.filename = filename
                    self.content_type = content_type
                
                async def read(self):
                    return self.file.read()
                
                def __del__(self):
                    self.file.close()
            
            mock_file = MockUploadFile(
                file_path, 
                document["filename"], 
                document["content_type"]
            )
            
            # Re-extract text content
            extracted_text = await nectar_processor.extract_text(mock_file)
            
            # Re-chunk the content
            chunks = await nectar_processor.chunk_content(
                extracted_text,
                chunk_size=1000,
                overlap=200,
                strategy="sentence"
            )
            
            # Update document with new extraction
            document["extracted_text"] = extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
            document["chunk_count"] = len(chunks)
            document["chunks"] = chunks
            document["last_ripened"] = datetime.now()
            document["status"] = "ready"
            
            total_chunks += len(chunks)
            
            # Add chunks to ChromaDB for semantic search
            if semantic_search.available:
                chunk_metadata = {
                    "filename": document["filename"],
                    "content_type": document["content_type"],
                    "timestamp": datetime.now().isoformat(),
                    "honey_jar_name": hj_data["name"]
                }
                semantic_search.add_document_chunks(
                    honey_jar_id=honey_jar_id,
                    document_id=doc_id,
                    chunks=chunks,
                    metadata=chunk_metadata
                )
            
            processed_count += 1
            logger.info(f"Ripened document {document['filename']}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to ripen document {doc_id}: {e}")
            document["status"] = "ripen_error"
            document["ripen_error"] = str(e)
            failed_count += 1
    
    # Update honey jar stats
    hj_data["stats"]["embedding_count"] = total_chunks
    hj_data["last_ripened"] = datetime.now()
    hj_data["last_updated"] = datetime.now()
    
    # Log the ripen action
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "ripen", True,
        {"processed": processed_count, "failed": failed_count, "total_chunks": total_chunks}
    )
    
    return {
        "message": f"Honey jar ripened successfully",
        "honey_jar_id": honey_jar_id,
        "processed": processed_count,
        "failed": failed_count,
        "total_chunks": total_chunks,
        "ripened_at": datetime.now().isoformat()
    }

# Marketplace endpoints (mock)
@app.post("/marketplace/search")
async def search_marketplace(request: dict):
    """Search marketplace listings (mock implementation)"""
    return {
        "listings": [
            {
                "id": "market-1",
                "honey_jar_name": "AI Research Papers",
                "description": "Collection of AI research papers",
                "price": 0,
                "license_type": "Creative Commons",
                "seller_name": "Research Hub",
                "rating": 4.8,
                "downloads": 1234,
                "tags": ["ai", "research", "papers"],
                "created_date": datetime.now().isoformat()
            }
        ],
        "total_count": 1,
        "page": 1,
        "page_size": 20,
        "has_more": False
    }

# Honey Jar Export Endpoints
@app.get("/honey-jars/{honey_jar_id}/export")
async def export_honey_jar(
    honey_jar_id: str, 
    format: str = Query(default="hjx", enum=["hjx", "json", "tar"]),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """
    Export a honey jar in various formats:
    - hjx: STING Honey Jar Export format (recommended)
    - json: Plain JSON format
    - tar: TAR archive with all documents
    """
    from fastapi.responses import StreamingResponse
    import tarfile
    import io
    import tempfile
    
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Check access permission
    if not await knowledge_auth.can_access_honey_jar(current_user, hj_data):
        await knowledge_auth.log_access_attempt(
            current_user, f"honey_jar:{honey_jar_id}", "export", False
        )
        raise HTTPException(status_code=403, detail="Access denied to this honey jar")
    
    honey_jar = honey_jars_db[honey_jar_id]
    jar_docs = documents_db.get(honey_jar_id, {})
    
    if format == "hjx":
        # Create HJX format (JSON manifest + documents in a tar.gz)
        manifest = {
            "version": "1.0",
            "export_date": datetime.now().isoformat(),
            "honey_jar": {
                "id": honey_jar["id"],
                "name": honey_jar["name"],
                "description": honey_jar["description"],
                "type": honey_jar["type"],
                "tags": honey_jar["tags"],
                "created_date": honey_jar["created_date"].isoformat(),
                "stats": honey_jar["stats"]
            },
            "documents": []
        }
        
        # Create tar buffer
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add manifest
            manifest_data = json.dumps(manifest, indent=2)
            manifest_info = tarfile.TarInfo(name="manifest.json")
            manifest_info.size = len(manifest_data.encode())
            tar.addfile(manifest_info, io.BytesIO(manifest_data.encode()))
            
            # Add documents
            documents_dir = "documents/"
            for doc_id, doc in jar_docs.items():
                # Add document metadata to manifest
                manifest["documents"].append({
                    "id": doc["id"],
                    "filename": doc["filename"],
                    "content_type": doc["content_type"],
                    "size_bytes": doc["size_bytes"],
                    "upload_date": doc["upload_date"],
                    "metadata": doc.get("metadata", {})
                })
                
                # Add document file if it exists
                file_path = Path(doc.get("file_path", ""))
                if file_path.exists():
                    doc_info = tarfile.TarInfo(name=f"{documents_dir}{doc['filename']}")
                    doc_info.size = doc["size_bytes"]
                    with open(file_path, 'rb') as f:
                        tar.addfile(doc_info, f)
            
            # Update manifest in tar with documents
            manifest_data = json.dumps(manifest, indent=2)
            manifest_info = tarfile.TarInfo(name="manifest.json")
            manifest_info.size = len(manifest_data.encode())
            tar.addfile(manifest_info, io.BytesIO(manifest_data.encode()))
        
        tar_buffer.seek(0)
        return StreamingResponse(
            tar_buffer,
            media_type="application/x-tar",
            headers={
                "Content-Disposition": f'attachment; filename="{honey_jar["name"].replace(" ", "_")}.hjx"'
            }
        )
    
    elif format == "json":
        # Simple JSON export
        export_data = {
            "honey_jar": honey_jar,
            "documents": list(jar_docs.values()),
            "export_date": datetime.now().isoformat()
        }
        
        return StreamingResponse(
            io.BytesIO(json.dumps(export_data, indent=2, default=str).encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{honey_jar["name"].replace(" ", "_")}_export.json"'
            }
        )
    
    elif format == "tar":
        # TAR archive with all documents
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add honey jar info
            info_data = json.dumps(honey_jar, indent=2, default=str)
            info_file = tarfile.TarInfo(name="honey_jar_info.json")
            info_file.size = len(info_data.encode())
            tar.addfile(info_file, io.BytesIO(info_data.encode()))
            
            # Add all documents
            for doc_id, doc in jar_docs.items():
                file_path = Path(doc.get("file_path", ""))
                if file_path.exists():
                    tar.add(file_path, arcname=f"documents/{doc['filename']}")
        
        tar_buffer.seek(0)
        return StreamingResponse(
            tar_buffer,
            media_type="application/x-tar",
            headers={
                "Content-Disposition": f'attachment; filename="{honey_jar["name"].replace(" ", "_")}_documents.tar.gz"'
            }
        )

@app.post("/honey-jars/import")
async def import_honey_jar(file: UploadFile = File(...)):
    """Import a honey jar from HJX format"""
    import tarfile
    import tempfile
    
    if not file.filename.endswith('.hjx'):
        raise HTTPException(status_code=400, detail="Only .hjx files are supported for import")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / file.filename
        
        # Save uploaded file
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Extract and process
        try:
            with tarfile.open(temp_path, 'r:gz') as tar:
                # Extract manifest
                manifest_member = tar.getmember("manifest.json")
                manifest_file = tar.extractfile(manifest_member)
                manifest = json.load(manifest_file)
                
                # Validate version
                if manifest.get("version") != "1.0":
                    raise HTTPException(status_code=400, detail="Unsupported HJX version")
                
                # Create new honey jar
                honey_jar_data = manifest["honey_jar"]
                new_id = str(uuid.uuid4())
                honey_jar_data["id"] = new_id
                honey_jar_data["created_date"] = datetime.now()
                honey_jar_data["last_updated"] = datetime.now()
                honey_jar_data["owner"] = "imported"
                
                honey_jars_db[new_id] = honey_jar_data
                documents_db[new_id] = {}
                
                # Extract documents
                upload_dir = Path(f"/tmp/sting_uploads/{new_id}")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                for doc_info in manifest.get("documents", []):
                    doc_filename = f"documents/{doc_info['filename']}"
                    try:
                        tar.extract(doc_filename, path=temp_dir)
                        
                        # Copy to upload directory
                        src_path = Path(temp_dir) / doc_filename
                        dst_path = upload_dir / f"{doc_info['id']}_{doc_info['filename']}"
                        shutil.copy2(src_path, dst_path)
                        
                        # Add to documents database
                        documents_db[new_id][doc_info["id"]] = {
                            **doc_info,
                            "honey_jar_id": new_id,
                            "file_path": str(dst_path),
                            "status": "ready"
                        }
                    except KeyError:
                        logger.warning(f"Document {doc_filename} not found in archive")
                
                return {
                    "success": True,
                    "honey_jar_id": new_id,
                    "message": f"Successfully imported honey jar '{honey_jar_data['name']}' with {len(documents_db[new_id])} documents"
                }
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to import honey jar: {str(e)}")

# Pending Documents Management Endpoints
@app.get("/honey-jars/{honey_jar_id}/pending-documents")
async def get_pending_documents(
    honey_jar_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Get pending documents for a honey jar (admin only)"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Only admins and owners can view pending documents
    user_role = current_user.get("role", "user")
    is_admin = user_role == "admin"
    is_owner = hj_data.get("owner") == current_user.get("email")
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only admins and honey jar owners can view pending documents")
    
    # Get pending documents
    pending_docs = pending_documents_db.get(honey_jar_id, {})
    
    documents = []
    for doc_id, doc in pending_docs.items():
        documents.append({
            "id": doc["id"],
            "filename": doc["filename"],
            "content_type": doc["content_type"],
            "size_bytes": doc["size_bytes"],
            "upload_date": doc["upload_date"],
            "uploaded_by": doc["uploaded_by"],
            "status": doc["status"],
            "approval_status": doc["approval_status"],
            "metadata": doc.get("metadata", {})
        })
    
    return {
        "honey_jar_id": honey_jar_id,
        "total_pending": len(documents),
        "documents": documents
    }

@app.post("/honey-jars/{honey_jar_id}/documents/{document_id}/approve")
async def approve_document(
    honey_jar_id: str,
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Approve a pending document (admin only)"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Only admins and owners can approve documents
    user_role = current_user.get("role", "user")
    is_admin = user_role == "admin"
    is_owner = hj_data.get("owner") == current_user.get("email")
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only admins and honey jar owners can approve documents")
    
    # Check if document exists in pending
    if honey_jar_id not in pending_documents_db or document_id not in pending_documents_db[honey_jar_id]:
        raise HTTPException(status_code=404, detail="Pending document not found")
    
    # Move document from pending to approved
    document = pending_documents_db[honey_jar_id][document_id]
    document["approval_status"] = "approved"
    document["approved_by"] = current_user.get("email")
    document["approved_date"] = datetime.now()
    
    # Move to main documents
    if honey_jar_id not in documents_db:
        documents_db[honey_jar_id] = {}
    documents_db[honey_jar_id][document_id] = document
    
    # Remove from pending
    del pending_documents_db[honey_jar_id][document_id]
    
    # Log approval
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "approve_document", True,
        {"document_id": document_id, "filename": document["filename"]}
    )
    
    return {
        "success": True,
        "message": f"Document '{document['filename']}' approved successfully",
        "document_id": document_id
    }

@app.post("/honey-jars/{honey_jar_id}/documents/{document_id}/reject")
async def reject_document(
    honey_jar_id: str,
    document_id: str,
    reason: str = Form(default=""),
    current_user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """Reject a pending document (admin only)"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey jar not found")
    
    hj_data = honey_jars_db[honey_jar_id]
    
    # Only admins and owners can reject documents
    user_role = current_user.get("role", "user")
    is_admin = user_role == "admin"
    is_owner = hj_data.get("owner") == current_user.get("email")
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only admins and honey jar owners can reject documents")
    
    # Check if document exists in pending
    if honey_jar_id not in pending_documents_db or document_id not in pending_documents_db[honey_jar_id]:
        raise HTTPException(status_code=404, detail="Pending document not found")
    
    # Get document info
    document = pending_documents_db[honey_jar_id][document_id]
    
    # Delete file
    file_path = Path(document.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
    
    # Remove from pending
    del pending_documents_db[honey_jar_id][document_id]
    
    # Log rejection
    await knowledge_auth.log_access_attempt(
        current_user, f"honey_jar:{honey_jar_id}", "reject_document", True,
        {"document_id": document_id, "filename": document["filename"], "reason": reason}
    )
    
    return {
        "success": True,
        "message": f"Document '{document['filename']}' rejected",
        "document_id": document_id,
        "reason": reason
    }

if __name__ == "__main__":
    mode_text = "with ChromaDB support" if chroma_available else "in minimal mode"
    logger.info(f"🍯 Starting STING Knowledge Service {mode_text} on {KNOWLEDGE_HOST}:{KNOWLEDGE_PORT}")
    logger.info(f"📊 ChromaDB URL: {CHROMA_URL}")
    uvicorn.run(
        app,
        host=KNOWLEDGE_HOST,
        port=KNOWLEDGE_PORT,
        log_level="info"
    )