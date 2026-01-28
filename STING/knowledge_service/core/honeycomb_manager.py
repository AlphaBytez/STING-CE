#!/usr/bin/env python3
"""
Honeycomb Manager - Vector Database Interface
Manages Chroma DB collections and embeddings for Honey Jar storage
"""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class HoneycombManager:
    """Manages vector embeddings storage in Chroma DB"""
    
    def __init__(self, chroma_url: str = "http://chroma:8000"):
        self.chroma_url = chroma_url
        self.client = None
        self.embedding_model = None
        
    async def initialize(self):
        """Initialize connection to Chroma DB and embedding model"""
        try:
            # Initialize Chroma client with proper configuration
            # Parse host and port from chroma_url
            if "://" in self.chroma_url:
                host_port = self.chroma_url.split("://")[1]
            else:
                host_port = self.chroma_url
                
            if ":" in host_port:
                host, port = host_port.split(":")
                port = int(port)
            else:
                host = host_port
                port = 8000
            
            self.client = chromadb.HttpClient(
                host=host,
                port=port
            )
            
            # Initialize embedding model
            logger.info("Loading sentence transformer model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Honeycomb Manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Honeycomb Manager: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Chroma DB health"""
        try:
            # Simple heartbeat
            collections = self.client.list_collections()
            return {
                "status": "healthy",
                "collections_count": len(collections),
                "embedding_model": "all-MiniLM-L6-v2"
            }
        except Exception as e:
            logger.error(f"Chroma health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def create_collection(self, honey_jar_id: str) -> None:
        """Create a new collection for a Honey Jar"""
        try:
            collection_name = f"honeyjar_{honey_jar_id}"
            
            # Create collection with metadata
            self.client.create_collection(
                name=collection_name,
                metadata={
                    "honey_jar_id": honey_jar_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "description": "STING Honey Jar knowledge base"
                }
            )
            
            logger.info(f"📦 Created Chroma collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection for {honey_jar_id}: {e}")
            raise
    
    async def delete_collection(self, honey_jar_id: str) -> None:
        """Delete a collection for a Honey Jar"""
        try:
            collection_name = f"honeyjar_{honey_jar_id}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"🗑️ Deleted Chroma collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete collection for {honey_jar_id}: {e}")
            raise
    
    async def add_document(
        self,
        collection_id: str,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> str:
        """Add a document chunk to a Honey Jar collection"""
        try:
            collection_name = f"honeyjar_{collection_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Generate document ID if not provided
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Add to collection
            collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[document_id]
            )
            
            logger.debug(f"Added document {document_id} to {collection_name}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to add document to {collection_id}: {e}")
            raise
    
    async def search(
        self,
        collection_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in a Honey Jar collection"""
        try:
            collection_name = f"honeyjar_{collection_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search with optional metadata filters
            where_clause = filters if filters else None
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    formatted_results.append({
                        "content": doc,
                        "metadata": metadata,
                        "score": 1.0 - distance,  # Convert distance to similarity score
                        "collection_id": collection_id
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed in {collection_id}: {e}")
            raise
    
    async def search_multiple_collections(
        self,
        collection_ids: List[str],
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search across multiple Honey Jar collections"""
        try:
            all_results = []
            
            # Search each collection
            for collection_id in collection_ids:
                try:
                    results = await self.search(collection_id, query, top_k, filters)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to search collection {collection_id}: {e}")
                    continue
            
            # Sort by score and return top_k
            all_results.sort(key=lambda x: x['score'], reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Multi-collection search failed: {e}")
            raise
    
    async def get_collection_stats(self, honey_jar_id: str) -> Dict[str, Any]:
        """Get statistics for a Honey Jar collection"""
        try:
            collection_name = f"honeyjar_{honey_jar_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Get count
            count = collection.count()
            
            return {
                "honey_jar_id": honey_jar_id,
                "document_count": count,
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {honey_jar_id}: {e}")
            return {
                "honey_jar_id": honey_jar_id,
                "document_count": 0,
                "error": str(e)
            }
    
    async def update_document_metadata(
        self,
        collection_id: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Update metadata for a specific document"""
        try:
            collection_name = f"honeyjar_{collection_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Update metadata
            collection.update(
                ids=[document_id],
                metadatas=[metadata]
            )
            
            logger.debug(f"Updated metadata for document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to update document metadata: {e}")
            raise
    
    async def delete_document(self, collection_id: str, document_id: str) -> None:
        """Delete a specific document from a collection"""
        try:
            collection_name = f"honeyjar_{collection_id}"
            collection = self.client.get_collection(name=collection_name)
            
            collection.delete(ids=[document_id])
            logger.debug(f"Deleted document {document_id} from {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise