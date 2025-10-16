#!/usr/bin/env python3
"""
STING Knowledge Service with ChromaDB
FastAPI service that provides honey pot knowledge management
with ChromaDB vector database support.
"""

from fastapi import FastAPI, HTTPException
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
    description="Honey pot knowledge management system with ChromaDB support",
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

# Sample data
def initialize_sample_data():
    sample_honey_jar = {
        "id": "sample-1",
        "name": "STING Documentation",
        "description": "Core platform documentation and guides",
        "type": "public",
        "status": "active",
        "owner": "admin",
        "created_date": datetime.now(),
        "last_updated": datetime.now(),
        "tags": ["documentation", "platform", "guides"],
        "stats": {
            "document_count": 5,
            "embedding_count": 150,
            "total_size_bytes": 1024000,
            "query_count": 0,
            "average_query_time": 0.0
        }
    }
    honey_jars_db["sample-1"] = sample_honey_jar

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
            "/honey-pots",
            "/honey-pots/{id}",
            "/search",
            "/bee/context"
        ],
        "note": f"ChromaDB status: {'connected' if chroma_available else 'unavailable'}"
    }

# Honey Jar Management Endpoints
@app.get("/honey-pots")
async def list_honey_jars():
    """List all honey pots"""
    honey_jars = []
    for hp_id, hp_data in honey_jars_db.items():
        honey_jars.append(HoneyJarResponse(
            id=hp_data["id"],
            name=hp_data["name"],
            description=hp_data["description"],
            type=hp_data["type"],
            status=hp_data["status"],
            owner=hp_data["owner"],
            created_date=hp_data["created_date"],
            last_updated=hp_data["last_updated"],
            tags=hp_data["tags"],
            stats=hp_data["stats"]
        ))
    
    return {
        "honey_jars": honey_jars,
        "total_count": len(honey_jars),
        "page": 1,
        "page_size": len(honey_jars),
        "has_more": False
    }

@app.get("/honey-pots/{honey_jar_id}")
async def get_honey_jar(honey_jar_id: str):
    """Get a specific honey pot"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey pot not found")
    
    hp_data = honey_jars_db[honey_jar_id]
    return HoneyJarResponse(
        id=hp_data["id"],
        name=hp_data["name"],
        description=hp_data["description"],
        type=hp_data["type"],
        status=hp_data["status"],
        owner=hp_data["owner"],
        created_date=hp_data["created_date"],
        last_updated=hp_data["last_updated"],
        tags=hp_data["tags"],
        stats=hp_data["stats"]
    )

@app.post("/honey-pots")
async def create_honey_jar(request: HoneyJarCreateRequest):
    """Create a new honey pot"""
    honey_jar_id = str(uuid.uuid4())
    
    honey_jar_data = {
        "id": honey_jar_id,
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "status": "active",
        "owner": "user",  # Would come from auth in full version
        "created_date": datetime.now(),
        "last_updated": datetime.now(),
        "tags": request.tags,
        "stats": {
            "document_count": 0,
            "embedding_count": 0,
            "total_size_bytes": 0,
            "query_count": 0,
            "average_query_time": 0.0
        }
    }
    
    honey_jars_db[honey_jar_id] = honey_jar_data
    
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

@app.delete("/honey-pots/{honey_jar_id}")
async def delete_honey_jar(honey_jar_id: str):
    """Delete a honey pot"""
    if honey_jar_id not in honey_jars_db:
        raise HTTPException(status_code=404, detail="Honey pot not found")
    
    del honey_jars_db[honey_jar_id]
    return {"message": "Honey pot deleted successfully"}

# Search Endpoints
@app.post("/search")
async def search_knowledge(request: SearchRequest):
    """Search across honey pots with ChromaDB or fallback to mock"""
    import time
    start_time = time.time()
    
    if chroma_available and chroma_client:
        try:
            # Try to search in ChromaDB
            collections = chroma_client.list_collections()
            
            if collections:
                # Search in the first available collection for demo
                collection = collections[0]
                results = collection.query(
                    query_texts=[request.query],
                    n_results=min(request.top_k, 10)
                )
                
                # Convert ChromaDB results to our format
                search_results = []
                if results['documents'] and results['documents'][0]:
                    for i, (doc, score) in enumerate(zip(results['documents'][0], results['distances'][0])):
                        # Convert distance to similarity score (1 - distance)
                        similarity_score = max(0, 1 - score)
                        search_results.append(SearchResult(
                            content=doc[:500] + "..." if len(doc) > 500 else doc,
                            score=round(similarity_score, 3),
                            honey_jar_id=results['ids'][0][i] if results['ids'] else f"doc-{i}",
                            honey_jar_name="ChromaDB Collection"
                        ))
                
                processing_time = time.time() - start_time
                return SearchResponse(
                    query=request.query,
                    results=search_results[:request.top_k],
                    total_results=len(search_results),
                    processing_time=processing_time
                )
        
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}, falling back to mock")
    
    # Fallback to mock search results
    mock_results = [
        SearchResult(
            content=f"Sample content matching '{request.query}' from STING documentation",
            score=0.95,
            honey_jar_id="sample-1",
            honey_jar_name="STING Documentation"
        ),
        SearchResult(
            content=f"Additional information about '{request.query}' in the knowledge base",
            score=0.87,
            honey_jar_id="sample-1",
            honey_jar_name="STING Documentation"
        )
    ]
    
    # Limit results to requested amount
    results = mock_results[:request.top_k]
    processing_time = time.time() - start_time
    
    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        processing_time=processing_time
    )

# Bee Integration Endpoint
@app.post("/bee/context")
async def get_bee_context(request: dict):
    """Get relevant context for Bee chatbot (compatible with Bee's expected format)"""
    query = request.get("query", "")
    user_id = request.get("user_id", "anonymous")
    limit = request.get("limit", 5)
    
    logger.info(f"Bee context request: query='{query}', user_id='{user_id}', limit={limit}")
    
    # Enhanced mock context with more realistic honey jar data
    mock_results = [
        {
            "content": f"Demo context for query: {query}. This is sample knowledge base content from STING platform.",
            "score": 0.85,
            "metadata": {
                "source": "honeyjar-ssh",
                "timestamp": "2025-06-25T19:00:00Z",
                "honey_jar_id": "demo-1",
                "honey_jar_name": "STING Demo Knowledge"
            }
        }
    ]
    
    # If query contains specific honey jar terms, add more relevant mock data
    if any(term in query.lower() for term in ["attack", "intrusion", "ssh", "login", "malware", "breach"]):
        mock_results.extend([
            {
                "content": f"Security alert: Multiple failed login attempts detected in SSH honey jar. Related to: {query}",
                "score": 0.92,
                "metadata": {
                    "source": "honeyjar-ssh",
                    "timestamp": "2025-06-25T18:30:00Z",
                    "honey_jar_id": "ssh-01",
                    "honey_jar_name": "SSH Honey Jar Monitor"
                }
            },
            {
                "content": f"Threat intelligence: New attack pattern observed matching query '{query}'. Automated analysis suggests APT activity.",
                "score": 0.78,
                "metadata": {
                    "source": "threat-intel",
                    "timestamp": "2025-06-25T17:45:00Z",
                    "honey_jar_id": "intel-01",
                    "honey_jar_name": "Threat Intelligence Hub"
                }
            }
        ])
    
    # Return format compatible with Bee chatbot expectations
    return {
        "results": mock_results[:limit],  # Use 'results' key as expected by Bee
        "total_results": len(mock_results),
        "query": query,
        "processing_time": 0.05,
        "confidence_score": 0.85
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