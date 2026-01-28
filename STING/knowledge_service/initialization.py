#!/usr/bin/env python3
"""
Unified initialization system for the Knowledge Service
Handles database setup, honey jar creation, document seeding, and indexing
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from database import (
    Base, create_tables, get_db,
    HoneyJar, Document, HoneyJarRepository, DocumentRepository
)
from semantic_search import SemanticSearchEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample documents with full content
SAMPLE_DOCUMENTS = {
    "knowledge": [
        {
            "filename": "sting_overview.md",
            "content": """# STING Platform Overview

STING (Secure Trusted Intelligence and Networking Guardian) is a comprehensive knowledge management and AI document analysis platform with secure, private LLM deployment capabilities.

## Key Features

1. **Honey Jars**: Organized knowledge repositories with semantic search
2. **AI-Powered Analysis**: Use machine learning to analyze and understand documents  
3. **Bee Chat**: Conversational AI assistant connected to your knowledge bases
4. **Document Processing**: Upload and index documents for intelligent retrieval
5. **Report Generation**: Create comprehensive reports from your knowledge

## Architecture

- **Honey Jars**: Knowledge repositories that store and organize your documents
- **Hive Manager**: Central management for all your knowledge bases
- **Bee Chatbot**: AI assistant for querying and analyzing your documents
- **Knowledge Service**: Manages document indexing and semantic search

## Getting Started

1. Login to the STING dashboard
2. Navigate to Honey Jars to view existing knowledge bases
3. Use Bee Chat to query your documents
4. Upload documents to build your knowledge base""",
            "tags": ["platform", "overview", "documentation", "getting-started"]
        },
        {
            "filename": "honey_jar_guide.md", 
            "content": """# Honey Jar Setup Guide

This guide walks you through setting up your first honey jar in STING.

## What is a Honey Jar?

A honey jar in STING is a knowledge repository that stores and organizes your documents and information. Think of it as an intelligent document collection with semantic search capabilities.

## Types of Honey Jars

1. **Public Honey Jars**: Accessible to all users, contains general knowledge
2. **Private Honey Jars**: Restricted access, for sensitive documents
3. **Team Honey Jars**: Shared among team members

## Creating a Honey Jar

### Step 1: Navigate to Hive Manager
- Login to STING dashboard
- Click on "Honey Jars" in the navigation menu
- Click "Create New Honey Jar"

### Step 2: Configure Basic Settings
- **Name**: Choose a descriptive name
- **Description**: Explain the purpose of this honey jar
- **Type**: Select public, private, or team
- **Tags**: Add relevant tags for easy discovery

### Step 3: Set Permissions
- Define who can view the honey jar
- Set upload permissions
- Configure approval workflows if needed

### Step 4: Add Initial Content
- Upload documents (PDF, Word, Markdown, etc.)
- Import existing knowledge bases
- Add reference materials

## Best Practices

- Use clear, descriptive names
- Organize content with consistent tags
- Regularly update honey jars with new documents
- Review and clean up outdated information""",
            "tags": ["guide", "setup", "honey-jar", "tutorial"]
        },
        {
            "filename": "document_organization.md",
            "content": """# Document Organization Best Practices

## Overview
This document outlines best practices for organizing knowledge in STING honey jars.

## Organization Strategies

### 1. By Topic or Project
- **Use Case**: Team documentation, project files
- **Structure**: Create separate honey jars per project
- **Benefits**: Clear boundaries, easy permission management

### 2. By Department
- **Use Case**: Company-wide knowledge management
- **Structure**: One honey jar per department
- **Benefits**: Organizational alignment, natural access controls

### 3. By Document Type
- **Use Case**: Reference materials, templates
- **Structure**: Separate jars for policies, procedures, templates
- **Benefits**: Easy to find specific document types

### 4. By Access Level
- **Use Case**: Sensitive vs. general documents
- **Structure**: Public, internal, confidential honey jars
- **Benefits**: Clear security boundaries

### 5. By Time Period
- **Use Case**: Archival, historical records
- **Structure**: Yearly or quarterly archives
- **Benefits**: Better performance, cleaner active jars

## Tips for Effective Knowledge Management

STING honey jars work best when you:
- Add descriptive tags to documents
- Write clear document titles
- Use consistent naming conventions
- Regularly review and update content""",
            "tags": ["organization", "best-practices", "documentation", "knowledge-management"]
        }
    ],
    "support": [
        {
            "filename": "bee_chat_guide.md",
            "content": """# Bee Chat Assistant Guide

Bee is your AI-powered knowledge assistant that helps you find information and generate insights from your documents.

## Getting Started with Bee

### Accessing Bee Chat
1. Click on the Bee icon in the navigation bar
2. Or navigate to the Chat section of the dashboard

### What Can Bee Help With?

- **Document Questions**: Ask about content in your honey jars
- **Research Assistance**: Summarize documents, find key points
- **Report Generation**: Create reports from your knowledge bases
- **Platform Help**: Learn how to use STING features

## Example Interactions

### Asking Questions
- "What does our policy say about remote work?"
- "Summarize the Q4 financial report"
- "Find all mentions of Project Alpha"
- "What are the key points in this document?"

### Document Analysis
- "Compare these two contracts"
- "What are the main themes across these documents?"
- "Extract action items from these meeting notes"

### Getting Recommendations
- "How should I organize my legal documents?"
- "What tags would work best for this content?"
- "Help me create a summary for stakeholders"

## Tips for Better Results

1. **Be Specific**: Provide context and details in your questions
2. **Use Honey Jar Knowledge**: Bee can access documents in your honey jars
3. **Upload Relevant Files**: Share documents for analysis
4. **Follow Up**: Ask clarifying questions to get deeper insights

## Advanced Features

- **Context Awareness**: Bee remembers your conversation history
- **Multi-format Analysis**: Can analyze PDFs, Word docs, and more
- **Integration**: Connects with honey jar knowledge bases
- **Learning**: Improves responses based on your feedback""",
            "tags": ["bee", "chat", "assistant", "guide", "ai"]
        },
        {
            "filename": "platform_faq.md",
            "content": """# STING Platform FAQ

## General Questions

### Q: What is STING?
**A**: STING (Secure Trusted Intelligence and Networking Guardian) is a comprehensive knowledge management and AI document analysis platform. It helps organizations store, organize, and intelligently search their documents using AI.

### Q: What is a honey jar?
**A**: In STING, a honey jar is a knowledge repository that stores and organizes your documents. Think of it as an intelligent document collection with AI-powered semantic search.

### Q: How is STING different from traditional document management?
**A**: STING combines:
- Intelligent knowledge management (honey jars)
- AI-powered analysis (Bee chat)
- Semantic search capabilities
- Report generation from your documents

## Getting Started

### Q: How do I create my first honey jar?
**A**: Navigate to the Honey Jars section and click "Create New". Follow the setup wizard to configure name, type, and permissions.

### Q: Can I import existing documents?
**A**: Yes! You can upload documents in various formats (PDF, Word, Markdown, text) to any honey jar you have access to.

### Q: Is there a limit to honey jar storage?
**A**: Each user has a 1GB Honey Reserve quota. Team and enterprise plans offer increased storage.

## Bee Chat Assistant

### Q: How does Bee chat work?
**A**: Bee is an AI assistant that can access your honey jars to provide contextual answers based on your documents.

### Q: Can Bee analyze my documents?
**A**: Yes, you can upload documents directly in the chat for analysis. Bee can summarize, extract key points, and answer questions about them.

### Q: Is my chat history saved?
**A**: Yes, chat history is saved and can be searched. You can also export conversations.

## Privacy & Access

### Q: Is my data secure in STING?
**A**: Yes, all data is encrypted at rest and in transit. Private honey jars are only accessible to authorized users.

### Q: Who can see my honey jars?
**A**: It depends on the type:
- Public: All users can view
- Private: Only you can access
- Team: Only team members can access

### Q: Can I delete my data?
**A**: Yes, you have full control over your data and can delete documents or entire honey jars.
- Team: Only team members can access

### Q: Can I delete my data?
**A**: Yes, you have full control over your data and can delete documents or entire honey jars.

## Technical Questions

### Q: What file formats are supported?
**A**: STING supports:
- Text files (.txt, .log, .md)
- JSON and XML
- CSV files
- PDF documents
- And more

### Q: Is there an API?
**A**: Yes, STING provides REST APIs for integration with other security tools.

### Q: Can I self-host STING?
**A**: Yes, STING-CE (Community Edition) can be self-hosted. See the installation guide for details.""",
            "tags": ["faq", "support", "help", "questions"]
        }
    ]
}


class InitializationManager:
    """Manages the complete initialization process for the Knowledge Service"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.honey_jar_repo = HoneyJarRepository(db_session)
        self.doc_repo = DocumentRepository(db_session)
        self.semantic_search = None
        self.initialized = False
        
    def initialize(self) -> bool:
        """
        Run the complete initialization process.
        Returns True if initialization was successful.
        """
        try:
            logger.info("="*60)
            logger.info("🐝 STING Knowledge Service Initialization Starting")
            logger.info("="*60)
            
            # Step 1: Create database tables
            logger.info("\n📊 Step 1/5: Creating database tables...")
            self._create_database_tables()
            
            # Step 2: Check if this is a fresh install
            is_fresh = self._is_fresh_install()
            logger.info(f"\n🔍 Fresh install detected: {is_fresh}")
            
            # Step 3: Create default honey jars
            logger.info("\n🍯 Step 2/5: Creating default honey jars...")
            honey_jars = self._create_default_honey_jars()
            
            # Step 4: Initialize semantic search
            logger.info("\n🔎 Step 3/5: Initializing semantic search...")
            self._initialize_semantic_search()
            
            # Step 5: Seed sample documents (if fresh install)
            if is_fresh:
                logger.info("\n📄 Step 4/5: Seeding sample documents...")
                self._seed_sample_documents(honey_jars)
            else:
                logger.info("\n📄 Step 4/5: Skipping document seeding (not a fresh install)")
            
            # Step 6: Ensure all documents are indexed
            logger.info("\n🔍 Step 5/5: Indexing documents in vector database...")
            self._ensure_documents_indexed(honey_jars)
            
            # Mark initialization complete
            self._mark_initialized()
            
            logger.info("\n" + "="*60)
            logger.info("✅ STING Knowledge Service Initialization Complete!")
            logger.info("="*60 + "\n")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            logger.exception(e)
            return False
        finally:
            # Don't close the session here - let the caller manage it
            pass
    
    def _create_database_tables(self):
        """Create all required database tables"""
        create_tables()
        logger.info("✅ Database tables created/verified")
    
    def _is_fresh_install(self) -> bool:
        """Check if this is a fresh installation"""
        # Check if we have any documents
        doc_count = self.doc_repo.count_documents() if hasattr(self.doc_repo, 'count_documents') else 0
        
        # Check if system has been initialized before
        # For now, we'll use document count as a proxy
        # TODO: Add proper system_config table
        
        is_fresh = doc_count == 0
        logger.info(f"Document count: {doc_count}")
        
        return is_fresh
    
    def _create_default_honey_jars(self) -> Dict[str, HoneyJar]:
        """Create default honey jars if they don't exist"""
        honey_jars = {}
        
        default_jars = [
            {
                "name": "Sample Security Knowledge",
                "description": "Sample honey jar with security-related documents for demonstration",
                "type": "public",
                "owner": "system",
                "tags": ["security", "sample", "documentation"]
            },
            {
                "name": "General Support Knowledge",
                "description": "General support documentation, guides, and FAQs",
                "type": "public",
                "owner": "system",
                "tags": ["support", "documentation", "guides", "faq"]
            }
        ]
        
        for jar_data in default_jars:
            # Check if already exists
            existing = self.honey_jar_repo.get_honey_jar_by_name(jar_data["name"])
            
            if existing:
                logger.info(f"✅ Honey jar already exists: {jar_data['name']}")
                honey_jars[jar_data["name"]] = existing
            else:
                # Create new honey jar
                honey_jar = self.honey_jar_repo.create_honey_jar(jar_data)
                logger.info(f"✅ Created honey jar: {jar_data['name']} (ID: {honey_jar.id})")
                honey_jars[jar_data["name"]] = honey_jar
        
        return honey_jars
    
    def _initialize_semantic_search(self):
        """Initialize the semantic search engine"""
        try:
            self.semantic_search = SemanticSearchEngine()
            if self.semantic_search.available:
                logger.info("✅ Semantic search engine initialized")
            else:
                logger.warning("⚠️  Semantic search not available - vector search disabled")
        except Exception as e:
            logger.error(f"❌ Failed to initialize semantic search: {e}")
            self.semantic_search = None
    
    def _seed_sample_documents(self, honey_jars: Dict[str, HoneyJar]):
        """Seed sample documents into honey jars"""
        
        # Seed security documents
        security_jar = honey_jars.get("Sample Security Knowledge")
        if security_jar:
            logger.info(f"\n📝 Seeding documents for: {security_jar.name}")
            
            for doc_data in SAMPLE_DOCUMENTS["security"]:
                # Create document record
                doc_record = {
                    "filename": doc_data["filename"],
                    "content_type": "text/markdown",
                    "size_bytes": len(doc_data["content"].encode()),
                    "status": "processed",
                    "doc_metadata": {"sample": True, "source": "seed"},
                    "tags": doc_data["tags"],
                    "embedding_count": 0  # Will be updated after indexing
                }
                
                # Create in database
                doc = self.doc_repo.create_document(security_jar.id, doc_record)
                logger.info(f"  ✅ Created document: {doc.filename}")
                
                # Index in vector database if available
                if self.semantic_search and self.semantic_search.available:
                    self._index_document(security_jar, doc, doc_data["content"])
        
        # Seed support documents
        support_jar = honey_jars.get("General Support Knowledge")
        if support_jar:
            logger.info(f"\n📝 Seeding documents for: {support_jar.name}")
            
            for doc_data in SAMPLE_DOCUMENTS["support"]:
                # Create document record
                doc_record = {
                    "filename": doc_data["filename"],
                    "content_type": "text/markdown",
                    "size_bytes": len(doc_data["content"].encode()),
                    "status": "processed",
                    "doc_metadata": {"sample": True, "source": "seed"},
                    "tags": doc_data["tags"],
                    "embedding_count": 0
                }
                
                # Create in database
                doc = self.doc_repo.create_document(support_jar.id, doc_record)
                logger.info(f"  ✅ Created document: {doc.filename}")
                
                # Index in vector database if available
                if self.semantic_search and self.semantic_search.available:
                    self._index_document(support_jar, doc, doc_data["content"])
        
        # Update honey jar statistics
        for jar in honey_jars.values():
            self.honey_jar_repo.update_honey_jar_stats(jar.id)
        
        logger.info("\n✅ Sample documents seeded successfully")
    
    def _index_document(self, honey_jar: HoneyJar, document: Document, content: str):
        """Index a single document in the vector database"""
        try:
            collection_name = f"honey_jar_{str(honey_jar.id).replace('-', '_')}"
            
            # Ensure collection exists
            self.semantic_search.get_or_create_collection(collection_name)
            
            # Add document to vector store
            self.semantic_search.add_document_chunks(
                collection_name,
                doc_id=str(document.id),
                content=content,
                metadata={
                    "filename": document.filename,
                    "honey_jar_id": str(honey_jar.id),
                    "honey_jar_name": honey_jar.name,
                    "tags": document.tags or [],
                    "content_type": document.content_type or "text/plain"
                }
            )
            
            # Update embedding count
            document.embedding_count = 1
            self.db.commit()
            
            logger.info(f"    🔍 Indexed: {document.filename}")
            
        except Exception as e:
            logger.error(f"    ❌ Failed to index {document.filename}: {e}")
    
    def _ensure_documents_indexed(self, honey_jars: Dict[str, HoneyJar]):
        """Ensure all documents are properly indexed in the vector database"""
        if not self.semantic_search or not self.semantic_search.available:
            logger.warning("⚠️  Semantic search not available - skipping indexing")
            return
        
        # Create collections for all honey jars
        all_jars = self.honey_jar_repo.list_honey_jars(limit=100)
        
        for jar in all_jars:
            collection_name = f"honey_jar_{str(jar.id).replace('-', '_')}"
            try:
                self.semantic_search.get_or_create_collection(collection_name)
                logger.info(f"✅ Collection ready for: {jar.name}")
            except Exception as e:
                logger.error(f"❌ Failed to create collection for {jar.name}: {e}")
    
    def _mark_initialized(self):
        """Mark the system as initialized"""
        # TODO: Implement proper system_config table
        # For now, we'll just log it
        logger.info("\n✅ System marked as initialized")


def run_initialization():
    """Run the initialization process"""
    db = next(get_db())
    try:
        manager = InitializationManager(db)
        success = manager.initialize()
        
        if success:
            logger.info("Initialization completed successfully")
        else:
            logger.error("Initialization failed")
            
        return success
        
    finally:
        db.close()


if __name__ == "__main__":
    # Allow running directly for testing
    run_initialization()