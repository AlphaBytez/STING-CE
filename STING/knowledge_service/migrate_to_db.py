#!/usr/bin/env python3
"""
Migration script to import existing honey jars and documents into database
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from database import engine, SessionLocal, create_tables, HoneyJar, Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/tmp/sting_uploads")

def migrate_honey_jars():
    """Migrate existing honey jars and documents to database"""
    
    # Create tables if they don't exist
    create_tables()
    logger.info("✅ Database tables created/verified")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Define default honey jars that should exist
        default_honey_jars = {
            "sample-1": {
                "name": "Sample Security Knowledge",
                "description": "Sample honey jar with security-related documents",
                "type": "public",
                "owner": "system",
                "tags": ["security", "sample", "documentation"]
            },
            "support-general": {
                "name": "General Support Knowledge",
                "description": "General support documentation and guides",
                "type": "public", 
                "owner": "system",
                "tags": ["support", "documentation", "guides"]
            }
        }
        
        # Track ID mappings
        id_mappings = {}
        
        # Create default honey jars in database
        for old_id, jar_data in default_honey_jars.items():
            # Check if already exists
            existing = db.query(HoneyJar).filter(HoneyJar.name == jar_data["name"]).first()
            
            if existing:
                logger.info(f"Honey jar '{jar_data['name']}' already exists with ID: {existing.id}")
                id_mappings[old_id] = str(existing.id)
            else:
                # Create new honey jar
                honey_jar = HoneyJar(
                    name=jar_data["name"],
                    description=jar_data["description"],
                    type=jar_data["type"],
                    owner=jar_data["owner"],
                    tags=jar_data["tags"],
                    status="active",
                    created_date=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                db.add(honey_jar)
                db.commit()
                db.refresh(honey_jar)
                logger.info(f"✅ Created honey jar '{jar_data['name']}' with ID: {honey_jar.id}")
                id_mappings[old_id] = str(honey_jar.id)
        
        # Scan upload directory for existing files
        if UPLOAD_DIR.exists():
            logger.info(f"Scanning {UPLOAD_DIR} for existing files...")
            
            for old_jar_dir in UPLOAD_DIR.iterdir():
                if not old_jar_dir.is_dir():
                    continue
                
                old_jar_id = old_jar_dir.name
                
                # Get the new honey jar ID
                if old_jar_id in id_mappings:
                    new_jar_id = id_mappings[old_jar_id]
                else:
                    # Try to find by directory name pattern
                    logger.warning(f"Unknown honey jar directory: {old_jar_id}, skipping...")
                    continue
                
                logger.info(f"Processing files in {old_jar_dir}...")
                
                # Get the honey jar
                honey_jar = db.query(HoneyJar).filter(HoneyJar.id == new_jar_id).first()
                if not honey_jar:
                    logger.error(f"Honey jar not found for ID: {new_jar_id}")
                    continue
                
                # Create new directory with proper UUID
                new_jar_dir = UPLOAD_DIR / new_jar_id
                if old_jar_id != new_jar_id and not new_jar_dir.exists():
                    logger.info(f"Creating new directory: {new_jar_dir}")
                    new_jar_dir.mkdir(exist_ok=True)
                
                # Process each file
                document_count = 0
                total_size = 0
                
                for file_path in old_jar_dir.glob("*"):
                    if not file_path.is_file():
                        continue
                    
                    # Extract original filename (remove UUID prefix if present)
                    filename = file_path.name
                    if "_" in filename and len(filename.split("_")[0]) == 36:
                        # Remove UUID prefix
                        original_filename = "_".join(filename.split("_")[1:])
                    else:
                        original_filename = filename
                    
                    # Check if document already exists
                    existing_doc = db.query(Document).filter(
                        Document.honey_jar_id == new_jar_id,
                        Document.filename == original_filename
                    ).first()
                    
                    if existing_doc:
                        logger.info(f"Document '{original_filename}' already exists, skipping...")
                        continue
                    
                    # Get file info
                    file_size = file_path.stat().st_size
                    
                    # Determine content type
                    content_type = "text/plain"
                    if file_path.suffix.lower() == ".md":
                        content_type = "text/markdown"
                    elif file_path.suffix.lower() == ".json":
                        content_type = "application/json"
                    elif file_path.suffix.lower() == ".pdf":
                        content_type = "application/pdf"
                    
                    # Move file to new location if needed
                    new_file_path = new_jar_dir / file_path.name
                    if old_jar_id != new_jar_id:
                        logger.info(f"Moving {file_path} to {new_file_path}")
                        file_path.rename(new_file_path)
                        file_path = new_file_path
                    
                    # Create document record
                    document = Document(
                        honey_jar_id=new_jar_id,
                        filename=original_filename,
                        content_type=content_type,
                        size_bytes=file_size,
                        upload_date=datetime.utcnow(),
                        status="completed",  # Assume existing files are already processed
                        file_path=str(file_path),
                        doc_metadata={
                            "migrated": True,
                            "original_path": str(file_path)
                        }
                    )
                    db.add(document)
                    document_count += 1
                    total_size += file_size
                    
                    logger.info(f"✅ Migrated document: {original_filename}")
                
                # Update honey jar stats
                if document_count > 0:
                    honey_jar.document_count = document_count
                    honey_jar.total_size_bytes = total_size
                    honey_jar.last_updated = datetime.utcnow()
                    db.commit()
                    logger.info(f"Updated honey jar stats: {document_count} documents, {total_size} bytes")
                
                # Remove old directory if it was renamed
                if old_jar_id != new_jar_id and old_jar_dir.exists():
                    try:
                        old_jar_dir.rmdir()
                        logger.info(f"Removed old directory: {old_jar_dir}")
                    except:
                        logger.warning(f"Could not remove old directory: {old_jar_dir}")
        
        # Check for any documents.json files
        for jar_dir in UPLOAD_DIR.iterdir():
            if not jar_dir.is_dir():
                continue
            
            docs_json = jar_dir / "documents.json"
            if docs_json.exists():
                logger.info(f"Found documents.json in {jar_dir}, processing metadata...")
                
                try:
                    with open(docs_json, 'r') as f:
                        docs_data = json.load(f)
                    
                    # Update document metadata based on documents.json
                    for doc_id, doc_info in docs_data.items():
                        filename = doc_info.get("filename")
                        if filename:
                            # Find document by filename
                            document = db.query(Document).filter(
                                Document.filename == filename,
                                Document.honey_jar_id == jar_dir.name
                            ).first()
                            
                            if document and doc_info.get("chunks"):
                                document.embedding_count = len(doc_info["chunks"])
                                document.doc_metadata = {
                                    **document.doc_metadata,
                                    "has_chunks": True,
                                    "chunk_count": len(doc_info["chunks"])
                                }
                                logger.info(f"Updated metadata for {filename}")
                    
                    db.commit()
                    
                    # Rename documents.json to indicate it's been processed
                    docs_json.rename(jar_dir / "documents.json.migrated")
                    
                except Exception as e:
                    logger.error(f"Error processing documents.json: {e}")
        
        db.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Print summary
        total_jars = db.query(HoneyJar).count()
        total_docs = db.query(Document).count()
        logger.info(f"\nMigration Summary:")
        logger.info(f"- Total honey jars: {total_jars}")
        logger.info(f"- Total documents: {total_docs}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_migration():
    """Verify the migration was successful"""
    db = SessionLocal()
    
    try:
        # List all honey jars
        honey_jars = db.query(HoneyJar).all()
        logger.info("\n📋 Honey Jars in Database:")
        for jar in honey_jars:
            logger.info(f"  - {jar.name} (ID: {jar.id})")
            logger.info(f"    Type: {jar.type}, Owner: {jar.owner}")
            logger.info(f"    Documents: {jar.document_count}, Size: {jar.total_size_bytes} bytes")
        
        # List documents
        logger.info("\n📄 Documents in Database:")
        documents = db.query(Document).all()
        for doc in documents[:10]:  # Show first 10
            honey_jar = db.query(HoneyJar).filter(HoneyJar.id == doc.honey_jar_id).first()
            logger.info(f"  - {doc.filename} in {honey_jar.name if honey_jar else 'Unknown'}")
            logger.info(f"    Status: {doc.status}, Size: {doc.size_bytes} bytes")
        
        if len(documents) > 10:
            logger.info(f"  ... and {len(documents) - 10} more documents")
            
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting honey jar migration to database...")
    migrate_honey_jars()
    verify_migration()