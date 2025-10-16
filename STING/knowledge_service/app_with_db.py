#!/usr/bin/env python3
"""
STING Knowledge Service with Database Persistence
FastAPI service that provides honey jar knowledge management
with PostgreSQL database and ChromaDB vector support.
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
from sqlalchemy.orm import Session
from database import get_db, create_tables, HoneyJar, Document, HoneyJarRepository, DocumentRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    description="Honey jar knowledge management system with database persistence",
    version="2.0.0"
)

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
        "metadata": {
            "uploaded_by": user_email,
            "needs_approval": needs_approval
        }
    }
    
    document = doc_repo.create_document(document_data)
    
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
        
        return {
            "document_id": str(document.id),
            "status": "pending_approval",
            "message": "Document uploaded successfully and is pending approval"
        }
    else:
        # Process immediately
        try:
            # Process with NectarProcessor
            processed_doc = nectar_processor.process_document(
                file_path=str(file_path),
                doc_type=file.content_type or "text/plain"
            )
            
            # Update document with processing results
            doc_repo.update_document(str(document.id), {
                "status": "completed",
                "embedding_count": len(processed_doc.get("chunks", [])),
                "metadata": {**document.metadata, **processed_doc.get("metadata", {})}
            })
            
            # Add to ChromaDB if available
            if chroma_available and processed_doc.get("chunks"):
                collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
                semantic_search.add_documents(
                    collection_name=collection_name,
                    documents=processed_doc["chunks"],
                    ids=[f"{document.id}_{i}" for i in range(len(processed_doc["chunks"]))],
                    metadata_list=[{
                        "document_id": str(document.id),
                        "honey_jar_id": honey_jar_id,
                        "filename": file.filename,
                        "chunk_index": i
                    } for i in range(len(processed_doc["chunks"]))]
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
                "chunks": len(processed_doc.get("chunks", []))
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
            "metadata": doc.metadata or {}
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
                        collection_name=collection_name,
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
                    collection_name=collection_name,
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
                continue
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
                    collection_name=collection_name,
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
                continue
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
        processed_doc = nectar_processor.process_document(
            file_path=document.file_path,
            doc_type=document.content_type or "text/plain"
        )
        
        # Update document
        doc_repo.update_document(document_id, {
            "status": "completed",
            "embedding_count": len(processed_doc.get("chunks", [])),
            "metadata": {**document.metadata, **processed_doc.get("metadata", {})}
        })
        
        # Add to ChromaDB
        if chroma_available and processed_doc.get("chunks"):
            collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
            semantic_search.add_documents(
                collection_name=collection_name,
                documents=processed_doc["chunks"],
                ids=[f"{document.id}_{i}" for i in range(len(processed_doc["chunks"]))],
                metadata_list=[{
                    "document_id": str(document.id),
                    "honey_jar_id": honey_jar_id,
                    "filename": document.filename,
                    "chunk_index": i
                } for i in range(len(processed_doc["chunks"]))]
            )
        
        # Update honey jar stats
        repo.update_honey_jar(honey_jar_id, {
            "document_count": honey_jar.document_count + 1,
            "embedding_count": honey_jar.embedding_count + len(processed_doc.get("chunks", [])),
            "total_size_bytes": honey_jar.total_size_bytes + document.size_bytes
        })
        
        return {
            "message": "Document approved and processed successfully",
            "document_id": document_id,
            "chunks": len(processed_doc.get("chunks", []))
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
    
    # Delete the document
    doc_repo = DocumentRepository(db)
    doc_repo.delete_document(document_id)
    
    return {
        "message": "Document rejected and removed",
        "document_id": document_id,
        "reason": reason
    }

# Add to HoneyJarRepository class
def get_honey_jar_by_name(self, name: str) -> HoneyJar:
    """Get honey jar by name"""
    return self.db.query(HoneyJar).filter(HoneyJar.name == name).first()

# Update HoneyJarRepository to include the new method
HoneyJarRepository.get_honey_jar_by_name = get_honey_jar_by_name

if __name__ == "__main__":
    uvicorn.run(app, host=KNOWLEDGE_HOST, port=KNOWLEDGE_PORT, log_level="info")