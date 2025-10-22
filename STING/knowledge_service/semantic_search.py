#!/usr/bin/env python3
"""
Semantic Search implementation for STING Knowledge Service
Uses ChromaDB for vector embeddings and similarity search
"""

import chromadb
from chromadb.config import Settings
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SemanticSearchEngine:
    """Handles semantic search using ChromaDB"""
    
    def __init__(self, chroma_client=None):
        """Initialize with ChromaDB client"""
        if chroma_client:
            self.client = chroma_client
            self.available = True
            logger.info("✅ Using provided ChromaDB client")
        else:
            # Try to create a new connection
            try:
                self.client = chromadb.HttpClient(
                    host="chroma",
                    port=8000,
                    settings=Settings(anonymized_telemetry=False)
                )
                self.available = True
                logger.info("✅ Connected to ChromaDB at chroma:8000")
            except Exception as e:
                logger.error(f"Failed to connect to ChromaDB: {e}")
                self.available = False
                self.client = None
    
    def get_or_create_collection(self, honey_jar_id: str) -> Optional[Any]:
        """Get or create a collection for a honey jar"""
        if not self.available:
            return None
            
        collection_name = f"honey_jar_{honey_jar_id}".replace("-", "_")
        
        try:
            # Try to get existing collection
            return self.client.get_collection(name=collection_name)
        except:
            # Create new collection
            try:
                return self.client.create_collection(
                    name=collection_name,
                    metadata={"honey_jar_id": honey_jar_id}
                )
            except Exception as e:
                logger.error(f"Failed to create collection {collection_name}: {e}")
                return None
    
    def add_document_chunks(self, honey_jar_id: str, document_id: str, 
                          chunks: List[str], metadata: Dict[str, Any]) -> bool:
        """Add document chunks to ChromaDB for semantic search"""
        if not self.available:
            return False
            
        collection = self.get_or_create_collection(honey_jar_id)
        if not collection:
            return False
            
        try:
            # Create unique IDs for each chunk
            chunk_ids = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                # Create deterministic chunk ID
                chunk_content = f"{document_id}_{i}_{chunk}"
                chunk_id = hashlib.md5(chunk_content.encode()).hexdigest()
                chunk_ids.append(chunk_id)
                
                # Add chunk-specific metadata
                chunk_metadata = {
                    **metadata,
                    "chunk_index": i,
                    "document_id": document_id,
                    "honey_jar_id": honey_jar_id
                }
                chunk_metadatas.append(chunk_metadata)
            
            # Add to ChromaDB (it will create embeddings automatically)
            collection.add(
                documents=chunks,
                ids=chunk_ids,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Added {len(chunks)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunks to ChromaDB: {e}")
            return False
    
    def search(self, query: str, honey_jar_ids: Optional[List[str]] = None, 
               limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search across honey jars"""
        if not self.available:
            return []
            
        results = []
        
        # If specific honey jars specified, search only those
        if honey_jar_ids:
            collections_to_search = []
            for hj_id in honey_jar_ids:
                collection = self.get_or_create_collection(hj_id)
                if collection:
                    collections_to_search.append((hj_id, collection))
        else:
            # Search all collections
            try:
                all_collections = self.client.list_collections()
                collections_to_search = []
                for coll in all_collections:
                    if coll.name.startswith("honey_jar_"):
                        hj_id = coll.metadata.get("honey_jar_id", coll.name)
                        collections_to_search.append((hj_id, coll))
            except Exception as e:
                logger.error(f"Failed to list collections: {e}")
                return []
        
        # Search each collection
        for honey_jar_id, collection in collections_to_search:
            try:
                # Query the collection
                query_results = collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                # Process results
                if query_results['documents'] and query_results['documents'][0]:
                    for i, doc in enumerate(query_results['documents'][0]):
                        # Convert distance to similarity score (1 - normalized distance)
                        distance = query_results['distances'][0][i]
                        score = max(0, 1 - (distance / 2))  # Normalize to 0-1
                        
                        metadata = query_results['metadatas'][0][i] if query_results['metadatas'] else {}
                        
                        results.append({
                            'content': doc,
                            'score': score,
                            'honey_jar_id': honey_jar_id,
                            'metadata': metadata,
                            'id': query_results['ids'][0][i] if query_results['ids'] else None
                        })
                        
            except Exception as e:
                logger.error(f"Failed to search collection {honey_jar_id}: {e}")
                continue
        
        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def delete_document_chunks(self, honey_jar_id: str, document_id: str) -> bool:
        """Remove all chunks for a document from ChromaDB"""
        if not self.available:
            return False
            
        collection = self.get_or_create_collection(honey_jar_id)
        if not collection:
            return False
            
        try:
            # Get all chunk IDs for this document
            results = collection.get(
                where={"document_id": {"$eq": document_id}}
            )
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunks from ChromaDB: {e}")
            return False
    
    def get_collection_stats(self, honey_jar_id: str) -> Dict[str, Any]:
        """Get statistics for a honey jar's collection"""
        if not self.available:
            return {"available": False}
            
        collection = self.get_or_create_collection(honey_jar_id)
        if not collection:
            return {"available": False}
            
        try:
            # Get collection count
            count = collection.count()
            
            return {
                "available": True,
                "chunk_count": count,
                "collection_name": f"honey_jar_{honey_jar_id}".replace("-", "_")
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"available": False, "error": str(e)}