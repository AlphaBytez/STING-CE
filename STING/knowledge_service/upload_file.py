#!/usr/bin/env python3
"""
Script to upload a file to a honey jar
"""

import sys
import os
import io
from pathlib import Path
import shutil
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, HoneyJar, Document
from core.nectar_processor import NectarProcessor
from semantic_search import SemanticSearchEngine
import chromadb

def upload_file_to_honey_jar(file_path: str, honey_jar_name: str):
    """Upload a file to a honey jar"""
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Find the honey jar by name
        honey_jar = db.query(HoneyJar).filter(HoneyJar.name == honey_jar_name).first()
        
        if not honey_jar:
            print(f"Error: Honey jar '{honey_jar_name}' not found")
            return False
        
        print(f"Found honey jar: {honey_jar.name} (ID: {honey_jar.id})")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return False
        
        # Create upload directory
        upload_dir = Path("/tmp/sting_uploads") / str(honey_jar.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to upload directory with unique ID
        file_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)
        dest_path = upload_dir / f"{file_id}_{filename}"
        
        shutil.copy2(file_path, dest_path)
        print(f"Copied file to: {dest_path}")
        
        # Get file size
        file_size = os.path.getsize(dest_path)
        
        # Create document record
        document = Document(
            honey_jar_id=honey_jar.id,
            filename=filename,
            content_type="text/markdown",
            size_bytes=file_size,
            upload_date=datetime.utcnow(),
            status="processing",
            file_path=str(dest_path),
            doc_metadata={
                "uploaded_by": "system",
                "upload_method": "script"
            }
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        print(f"Created document record: {document.id}")
        
        # Process the document
        try:
            nectar_processor = NectarProcessor()
            
            # Create a simple file-like object
            with open(dest_path, 'rb') as f:
                content = f.read()
            
            # Create a mock UploadFile for NectarProcessor
            class MockUploadFile:
                def __init__(self, content, filename, content_type):
                    self.file = io.BytesIO(content)
                    self.filename = filename
                    self.content_type = content_type
                
                async def read(self):
                    return self.file.read()
            
            mock_file = MockUploadFile(content, filename, "text/markdown")
            
            # Extract text content
            import asyncio
            extracted_text = asyncio.run(nectar_processor.extract_text(mock_file))
            
            # Chunk the content
            chunks = asyncio.run(nectar_processor.chunk_content(
                extracted_text,
                chunk_size=1000,
                overlap=200,
                strategy="sentence"
            ))
            
            processed_doc = {
                "chunks": chunks,
                "metadata": {
                    "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
                    "chunk_count": len(chunks)
                }
            }
            
            # Update document status
            document.status = "completed"
            document.embedding_count = len(processed_doc.get("chunks", []))
            document.doc_metadata = {**document.doc_metadata, **processed_doc.get("metadata", {})}
            db.commit()
            
            print(f"Processed document: {len(processed_doc.get('chunks', []))} chunks")
            
            # Add to ChromaDB if available
            try:
                chroma_client = chromadb.HttpClient(host="chroma", port=8000)
                chroma_client.heartbeat()
                
                semantic_search = SemanticSearchEngine(chroma_client)
                semantic_search.add_document_chunks(
                    honey_jar_id=str(honey_jar.id),
                    document_id=str(document.id),
                    chunks=processed_doc["chunks"],
                    metadata={
                        "filename": filename,
                        "content_type": "text/markdown"
                    }
                )
                print(f"Added chunks to ChromaDB")
                
            except Exception as e:
                print(f"Warning: Could not add to ChromaDB: {e}")
            
            # Update honey jar stats
            honey_jar.document_count += 1
            honey_jar.embedding_count += len(processed_doc.get("chunks", []))
            honey_jar.total_size_bytes += file_size
            honey_jar.last_updated = datetime.utcnow()
            db.commit()
            
            print(f"✅ Successfully uploaded {filename} to {honey_jar.name}")
            return True
            
        except Exception as e:
            print(f"Error processing document: {e}")
            document.status = "failed"
            document.error_message = str(e)
            db.commit()
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upload_file.py <file_path> <honey_jar_name>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    honey_jar_name = sys.argv[2]
    
    success = upload_file_to_honey_jar(file_path, honey_jar_name)
    sys.exit(0 if success else 1)