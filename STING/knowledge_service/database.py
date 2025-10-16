#!/usr/bin/env python3
"""
Database Models for Knowledge Service

SQLAlchemy models for PostgreSQL persistence of honey pot metadata.
"""

import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from uuid import UUID as PyUUID

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/sting_app')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HoneyJar(Base):
    """Honey Jar metadata stored in PostgreSQL"""
    __tablename__ = "honey_jars"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default="private")  # public, private, premium, enterprise
    status = Column(String(50), default="active")  # active, processing, error, inactive
    owner = Column(String(255), nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSONB, default=list)
    permissions = Column(JSONB, default=dict)
    
    # Statistics
    document_count = Column(Integer, default=0)
    embedding_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    query_count = Column(Integer, default=0)
    average_query_time = Column(Float, default=0.0)

class Document(Base):
    """Document metadata stored in PostgreSQL"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    honey_jar_id = Column(UUID(as_uuid=True), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    size_bytes = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    doc_metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    embedding_count = Column(Integer, default=0)
    processing_time = Column(Float)
    error_message = Column(Text)
    file_path = Column(String(500))

class MarketplaceListing(Base):
    """Marketplace listings stored in PostgreSQL"""
    __tablename__ = "marketplace_listings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    honey_jar_id = Column(UUID(as_uuid=True), nullable=False)
    honey_jar_name = Column(String(255), nullable=False)
    seller_id = Column(String(255), nullable=False)
    seller_name = Column(String(255), nullable=False)
    price = Column(Float, default=0.0)
    license_type = Column(String(100), default="Creative Commons")
    description = Column(Text)
    preview_enabled = Column(Boolean, default=True)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    reviews = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    tags = Column(JSONB, default=list)
    sample_documents = Column(JSONB, default=list)

# Database utility functions
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all tables (for testing)"""
    Base.metadata.drop_all(bind=engine)

# Database operations
class HoneyJarRepository:
    """Repository for honey pot operations"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_honey_jar(self, data: dict) -> HoneyJar:
        """Create a new honey pot"""
        honey_jar = HoneyJar(
            name=data['name'],
            description=data['description'],
            type=data.get('type', 'private'),
            owner=data['owner'],
            tags=data.get('tags', []),
            permissions=data.get('permissions', {})
        )
        self.db.add(honey_jar)
        self.db.commit()
        self.db.refresh(honey_jar)
        return honey_jar
    
    def get_honey_jar(self, honey_jar_id: str) -> HoneyJar:
        """Get honey pot by ID"""
        try:
            # Convert string to UUID if needed
            if isinstance(honey_jar_id, str):
                honey_jar_uuid = PyUUID(honey_jar_id)
            else:
                honey_jar_uuid = honey_jar_id
            return self.db.query(HoneyJar).filter(HoneyJar.id == honey_jar_uuid).first()
        except (ValueError, TypeError) as e:
            # Invalid UUID format
            return None
    
    def list_honey_jars(self, owner: str = None, limit: int = 50, offset: int = 0):
        """List honey pots with optional filtering"""
        query = self.db.query(HoneyJar)
        if owner:
            query = query.filter(HoneyJar.owner == owner)
        return query.offset(offset).limit(limit).all()
    
    def update_honey_jar(self, honey_jar_id: str, data: dict) -> HoneyJar:
        """Update honey pot"""
        honey_jar = self.get_honey_jar(honey_jar_id)  # get_honey_jar already handles UUID conversion
        if honey_jar:
            for key, value in data.items():
                if hasattr(honey_jar, key):
                    setattr(honey_jar, key, value)
            honey_jar.last_updated = datetime.utcnow()
            self.db.commit()
            self.db.refresh(honey_jar)
        return honey_jar

    def delete_honey_jar(self, honey_jar_id: str) -> bool:
        """Delete honey pot"""
        honey_jar = self.get_honey_jar(honey_jar_id)  # get_honey_jar already handles UUID conversion
        if honey_jar:
            self.db.delete(honey_jar)
            self.db.commit()
            return True
        return False
    
    def update_stats(self, honey_jar_id: str, stats: dict):
        """Update honey pot statistics"""
        honey_jar = self.get_honey_jar(honey_jar_id)  # get_honey_jar already handles UUID conversion
        if honey_jar:
            honey_jar.document_count = stats.get('document_count', honey_jar.document_count)
            honey_jar.embedding_count = stats.get('embedding_count', honey_jar.embedding_count)
            honey_jar.total_size_bytes = stats.get('total_size_bytes', honey_jar.total_size_bytes)
            honey_jar.query_count = stats.get('query_count', honey_jar.query_count)
            honey_jar.average_query_time = stats.get('average_query_time', honey_jar.average_query_time)
            honey_jar.last_updated = datetime.utcnow()
            self.db.commit()

    def update_honey_jar_stats(self, honey_jar_id: str):
        """Calculate and update honey jar statistics from documents"""
        from sqlalchemy import func

        try:
            # Convert string to UUID if needed for the query
            if isinstance(honey_jar_id, str):
                honey_jar_uuid = PyUUID(honey_jar_id)
            else:
                honey_jar_uuid = honey_jar_id

            # Get document stats
            stats = self.db.query(
                func.count(Document.id).label('document_count'),
                func.sum(Document.size_bytes).label('total_size_bytes'),
                func.sum(Document.embedding_count).label('embedding_count')
            ).filter(Document.honey_jar_id == honey_jar_uuid).first()

            if stats:
                self.update_stats(honey_jar_id, {
                    'document_count': stats.document_count or 0,
                    'total_size_bytes': stats.total_size_bytes or 0,
                    'embedding_count': stats.embedding_count or 0
                })
        except (ValueError, TypeError) as e:
            # Invalid UUID format - skip stats update
            pass
    
    def get_honey_jar_by_name(self, name: str) -> HoneyJar:
        """Get honey jar by name"""
        return self.db.query(HoneyJar).filter(HoneyJar.name == name).first()

class DocumentRepository:
    """Repository for document operations"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_document(self, honey_jar_id: str, data: dict) -> Document:
        """Create a new document record"""
        try:
            # Convert string to UUID if needed
            if isinstance(honey_jar_id, str):
                honey_jar_uuid = PyUUID(honey_jar_id)
            else:
                honey_jar_uuid = honey_jar_id

            # Debug and fix JSON serialization issue
            import logging
            import json
            logger = logging.getLogger(__name__)

            # Handle tags - convert JSON string to list if needed
            tags_data = data.get('tags', [])
            if isinstance(tags_data, str):
                try:
                    tags_data = json.loads(tags_data)
                    logger.info(f"🔍 FIXED: Converted tags from JSON string to list: {tags_data}")
                except:
                    tags_data = [tags_data]  # Fallback to single item list

            # Handle doc_metadata - convert JSON string to dict if needed
            metadata_data = data.get('doc_metadata', {})
            if isinstance(metadata_data, str):
                try:
                    metadata_data = json.loads(metadata_data)
                    logger.info(f"🔍 FIXED: Converted doc_metadata from JSON string to dict: {metadata_data}")
                except:
                    metadata_data = {}  # Fallback to empty dict

            logger.info(f"🔍 FINAL: tags type: {type(tags_data)}, doc_metadata type: {type(metadata_data)}")

            document = Document(
                honey_jar_id=honey_jar_uuid,
                filename=data['filename'],
                content_type=data.get('content_type'),
                size_bytes=data.get('size_bytes', 0),
                doc_metadata=metadata_data,  # Use the fixed metadata
                tags=tags_data,              # Use the fixed tags
                file_path=data.get('file_path'),
                status=data.get('status', 'pending'),
                embedding_count=data.get('embedding_count', 0)
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except (ValueError, TypeError) as e:
            # Invalid UUID format - raise an error with clear message
            raise ValueError(f"Invalid honey_jar_id format: {honey_jar_id}. Must be a valid UUID.") from e
    
    def get_document(self, document_id: str) -> Document:
        """Get document by ID"""
        try:
            # Convert string to UUID if needed
            if isinstance(document_id, str):
                document_uuid = PyUUID(document_id)
            else:
                document_uuid = document_id
            return self.db.query(Document).filter(Document.id == document_uuid).first()
        except (ValueError, TypeError) as e:
            # Invalid UUID format
            return None
    
    def list_documents(self, honey_jar_id: str):
        """List documents for a honey pot"""
        try:
            # Convert string to UUID if needed
            if isinstance(honey_jar_id, str):
                honey_jar_uuid = PyUUID(honey_jar_id)
            else:
                honey_jar_uuid = honey_jar_id
            return self.db.query(Document).filter(Document.honey_jar_id == honey_jar_uuid).all()
        except (ValueError, TypeError) as e:
            # Invalid UUID format
            return []
    
    def count_documents(self):
        """Count total documents in database"""
        return self.db.query(Document).count()
    
    def update_document_status(self, document_id: str, status: str, error_message: str = None):
        """Update document processing status"""
        document = self.get_document(document_id)  # get_document already handles UUID conversion
        if document:
            document.status = status
            if error_message:
                document.error_message = error_message
            self.db.commit()

    def update_document(self, document_id: str, data: dict) -> Document:
        """Update document"""
        document = self.get_document(document_id)  # get_document already handles UUID conversion
        if document:
            for key, value in data.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            self.db.commit()
            self.db.refresh(document)
        return document

    def delete_document(self, document_id: str) -> bool:
        """Delete document"""
        document = self.get_document(document_id)  # get_document already handles UUID conversion
        if document:
            # Also delete the physical file
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
            self.db.delete(document)
            self.db.commit()
            return True
        return False

# Initialize database on import
if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")