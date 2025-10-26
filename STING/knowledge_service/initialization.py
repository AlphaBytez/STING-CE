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
    "security": [
        {
            "filename": "sting_overview.md",
            "content": """# STING Platform Overview

STING (Security Threat Intelligence Network Gateway) is a comprehensive cybersecurity platform that combines honey jar technology with AI-powered threat analysis.

## Key Features

1. **Honey Jar Deployment**: Deploy various types of honey jars to detect and analyze threats
2. **AI-Powered Analysis**: Use machine learning to identify patterns and predict threats  
3. **Real-time Monitoring**: Monitor all honey jar activity in real-time
4. **Threat Intelligence**: Build a knowledge base of threat patterns and behaviors
5. **Automated Response**: Automatically respond to detected threats

## Architecture

- **Honey Jars**: Knowledge bases that store threat intelligence
- **Hive Manager**: Central management for all honey jar deployments
- **Bee Chatbot**: AI assistant for threat analysis
- **Knowledge Service**: Manages and indexes security knowledge

## Getting Started

1. Login to the STING dashboard
2. Navigate to Honey Jars to view existing knowledge bases
3. Use Bee Chat to query security information
4. Upload new threat intelligence documents""",
            "tags": ["platform", "overview", "documentation", "getting-started"]
        },
        {
            "filename": "honey_jar_guide.md", 
            "content": """# Honey Jar Setup Guide

This guide walks you through setting up your first honey jar in STING.

## What is a Honey Jar?

A honey jar in STING is a knowledge repository that stores and organizes security-related information. Think of it as a specialized database for threat intelligence.

## Types of Honey Jars

1. **Public Honey Jars**: Accessible to all users, contains general security knowledge
2. **Private Honey Jars**: Restricted access, for sensitive security data
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
- Upload threat intelligence documents
- Import security logs
- Add analysis reports

## Best Practices

- Use clear, descriptive names
- Organize content with consistent tags
- Regular update honey jars with new intelligence
- Review and clean up outdated information""",
            "tags": ["guide", "setup", "honey-jar", "tutorial"]
        },
        {
            "filename": "threat_patterns.md",
            "content": """# Common Threat Patterns

## Overview
This document outlines common threat patterns detected by STING honey jars.

## Attack Patterns

### 1. Brute Force Attacks
- **Indicators**: Multiple failed login attempts, sequential password testing
- **Common Targets**: SSH, RDP, Web login forms
- **Mitigation**: Rate limiting, account lockouts, strong password policies

### 2. SQL Injection
- **Indicators**: Malformed SQL in input fields, UNION SELECT statements
- **Common Targets**: Web applications, API endpoints
- **Mitigation**: Parameterized queries, input validation, WAF rules

### 3. Port Scanning
- **Indicators**: Sequential port connections, service enumeration
- **Common Targets**: All network services
- **Mitigation**: Firewall rules, IDS/IPS, port knocking

### 4. Malware Droppers
- **Indicators**: Suspicious file uploads, encoded payloads
- **Common Targets**: File upload endpoints, email attachments
- **Mitigation**: File type validation, sandboxing, antivirus scanning

### 5. Botnet Recruitment
- **Indicators**: C2 communication attempts, periodic beaconing
- **Common Targets**: IoT devices, compromised servers
- **Mitigation**: Network segmentation, outbound filtering

## Detection with STING

STING honey jars are configured to detect these patterns through:
- Log analysis
- Behavioral monitoring  
- Pattern matching
- Machine learning models""",
            "tags": ["threats", "patterns", "security", "detection"]
        }
    ],
    "support": [
        {
            "filename": "bee_chat_guide.md",
            "content": """# Bee Chat Assistant Guide

Bee is your AI-powered security assistant that helps analyze threats and provides recommendations.

## Getting Started with Bee

### Accessing Bee Chat
1. Click on the Bee icon in the navigation bar
2. Or navigate to the Chat section of the dashboard

### What Can Bee Help With?

- **Security Questions**: Ask about threats, vulnerabilities, and best practices
- **Threat Analysis**: Upload logs or describe suspicious activity
- **Recommendations**: Get actionable security advice
- **Platform Help**: Learn how to use STING features

## Example Interactions

### Asking Questions
- "What is a SQL injection attack?"
- "How do I set up a SSH honey jar?"
- "What are the latest threat patterns?"
- "Explain cross-site scripting"

### Analyzing Threats
- "Analyze this Apache access log for suspicious activity"
- "Is this network traffic pattern normal?"
- "Help me understand this security alert"

### Getting Recommendations
- "How can I improve my network security?"
- "What honey jars should I deploy for a web application?"
- "Recommend security tools for endpoint protection"

## Tips for Better Results

1. **Be Specific**: Provide context and details in your questions
2. **Use Honey Jar Knowledge**: Bee can access all public honey jars
3. **Upload Relevant Files**: Share logs, configs, or reports for analysis
4. **Follow Up**: Ask clarifying questions to get deeper insights

## Advanced Features

- **Context Awareness**: Bee remembers your conversation history
- **Multi-modal Analysis**: Can analyze text, logs, and structured data
- **Integration**: Connects with honey jar knowledge bases
- **Learning**: Improves responses based on your feedback""",
            "tags": ["bee", "chat", "assistant", "guide", "ai"]
        },
        {
            "filename": "platform_faq.md",
            "content": """# STING Platform FAQ

## General Questions

### Q: What is STING?
**A**: STING (Security Threat Intelligence Network Gateway) is a comprehensive cybersecurity platform that uses honey jar technology and AI to detect, analyze, and respond to security threats.

### Q: What is a honey jar?
**A**: In STING, a honey jar is a knowledge repository that stores security-related information, threat intelligence, and analysis results. It's like a specialized database for cybersecurity data.

### Q: How is STING different from traditional security tools?
**A**: STING combines:
- Knowledge management (honey jars)
- AI-powered analysis (Bee chat)
- Active threat detection
- Collaborative security intelligence

## Getting Started

### Q: How do I create my first honey jar?
**A**: Navigate to the Honey Jars section and click "Create New". Follow the setup wizard to configure name, type, and permissions.

### Q: Can I import existing security data?
**A**: Yes! You can upload documents, logs, and reports to any honey jar you have access to.

### Q: Is there a limit to honey jar storage?
**A**: Each user has a 1GB Honey Reserve quota. Team and enterprise plans offer increased storage.

## Bee Chat Assistant

### Q: How does Bee chat work?
**A**: Bee is an AI assistant trained on cybersecurity knowledge. It can access public honey jars to provide contextual answers and analysis.

### Q: Can Bee analyze my logs?
**A**: Yes, you can upload logs directly in the chat for analysis. Bee can identify patterns and potential threats.

### Q: Is my chat history saved?
**A**: Yes, chat history is saved and can be searched. You can also export conversations.

## Security & Privacy

### Q: Is my data secure in STING?
**A**: Yes, all data is encrypted at rest and in transit. Private honey jars are only accessible to authorized users.

### Q: Who can see my honey jars?
**A**: It depends on the type:
- Public: All users can view
- Private: Only you can access
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