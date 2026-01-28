#!/usr/bin/env python3
"""
Seed sample documents into the default honey jar
"""

import os
import json
from datetime import datetime
import uuid
from pathlib import Path

# Sample documents data
SAMPLE_DOCUMENTS = [
    {
        "filename": "sting_platform_overview.md",
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
- **Profile Service**: Manage security profiles and configurations
""",
        "type": "markdown",
        "tags": ["platform", "overview", "documentation"]
    },
    {
        "filename": "honey_jar_setup_guide.md",
        "content": """# Honey Jar Setup Guide

This guide walks you through setting up your first honey jar in STING.

## Prerequisites

- STING platform installed and running
- Admin access to the Hive Manager
- Network configuration permissions

## Step 1: Choose Honey Jar Type

STING supports multiple honey jar types:
- SSH Honey Jars
- Web Application Honey Jars
- Database Honey Jars
- IoT Device Honey Jars

## Step 2: Configure Network Settings

1. Navigate to Hive Manager
2. Click "Create New Honey Jar"
3. Configure network parameters
4. Set up logging and alerts

## Step 3: Deploy and Monitor

Once configured, deploy your honey jar and monitor incoming threats through the dashboard.
""",
        "type": "markdown",
        "tags": ["honey jar", "setup", "guide"]
    },
    {
        "filename": "threat_analysis_patterns.json",
        "content": json.dumps({
            "patterns": [
                {
                    "name": "Brute Force SSH",
                    "indicators": ["multiple_failed_logins", "rapid_attempts", "common_passwords"],
                    "severity": "medium",
                    "response": "block_ip_temporary"
                },
                {
                    "name": "SQL Injection Attempt",
                    "indicators": ["sql_keywords", "union_select", "database_errors"],
                    "severity": "high",
                    "response": "block_and_alert"
                },
                {
                    "name": "Port Scanning",
                    "indicators": ["sequential_port_access", "rapid_connections", "incomplete_handshakes"],
                    "severity": "low",
                    "response": "monitor_only"
                }
            ]
        }, indent=2),
        "type": "json",
        "tags": ["threat", "patterns", "analysis"]
    },
    {
        "filename": "api_reference.md",
        "content": """# STING API Reference

## Authentication

All API requests require authentication using JWT tokens.

```
Authorization: Bearer <your-token>
```

## Endpoints

### Honey Jars

- `GET /api/honey-jars` - List all honey jars
- `POST /api/honey-jars` - Create new honey jar
- `GET /api/honey-jars/{id}` - Get honey jar details
- `DELETE /api/honey-jars/{id}` - Delete honey jar

### Documents

- `POST /api/honey-jars/{id}/documents` - Upload documents
- `GET /api/honey-jars/{id}/documents` - List documents
- `DELETE /api/honey-jars/{id}/documents/{doc_id}` - Delete document

### Search

- `POST /api/search` - Search across honey jars

## Response Format

All responses follow this format:
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed"
}
```
""",
        "type": "markdown",
        "tags": ["api", "reference", "documentation"]
    },
    {
        "filename": "security_best_practices.txt",
        "content": """STING Security Best Practices

1. Regular Updates
   - Keep STING platform updated
   - Update honey jar signatures regularly
   - Patch vulnerabilities promptly

2. Network Isolation
   - Deploy honey jars in isolated network segments
   - Use VLANs for separation
   - Implement strict firewall rules

3. Data Protection
   - Encrypt all stored threat data
   - Use secure communication channels
   - Regular backup of honey jar data

4. Access Control
   - Implement role-based access control
   - Use strong authentication
   - Enable audit logging

5. Monitoring
   - Set up alerts for suspicious activity
   - Regular review of honey jar logs
   - Automated threat reporting
""",
        "type": "text",
        "tags": ["security", "best practices", "guidelines"]
    }
]

def initialize_sample_documents():
    """Create sample documents in the knowledge service's temporary storage"""
    
    # Create sample documents directory
    sample_dir = Path("/tmp/sting_uploads/sample-1")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize documents database
    documents_db = {}
    total_chunks = 0
    
    # Create each sample document
    for doc_data in SAMPLE_DOCUMENTS:
        doc_id = str(uuid.uuid4())
        
        # Save file
        file_path = sample_dir / f"{doc_id}_{doc_data['filename']}"
        with open(file_path, 'w') as f:
            f.write(doc_data['content'])
        
        # Create simple chunks for search (split by paragraphs/sections)
        content = doc_data['content']
        chunks = []
        
        # Split content into chunks based on document type
        if doc_data['type'] == 'markdown':
            # Split by sections (##) or paragraphs
            sections = content.split('\n\n')
            for section in sections:
                if section.strip():
                    chunks.append(section.strip())
        elif doc_data['type'] == 'json':
            # For JSON, use the whole content as one chunk
            chunks = [content]
        else:
            # For text files, split by double newlines
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    chunks.append(para.strip())
        
        # Create document record
        document = {
            "id": doc_id,
            "honey_jar_id": "sample-1",
            "filename": doc_data['filename'],
            "content_type": f"text/{doc_data['type']}",
            "size_bytes": len(doc_data['content'].encode()),
            "upload_date": datetime.now().isoformat(),
            "status": "ready",
            "metadata": {
                "tags": doc_data['tags'],
                "sample_data": True
            },
            "file_path": str(file_path),
            "extracted_text": content[:1000] + "..." if len(content) > 1000 else content,
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
        
        documents_db[doc_id] = document
        total_chunks += len(chunks)
    
    # Save documents database
    db_file = sample_dir / "documents.json"
    with open(db_file, 'w') as f:
        json.dump(documents_db, f, indent=2)
    
    print(f"✅ Created {len(SAMPLE_DOCUMENTS)} sample documents in {sample_dir}")
    print(f"📄 Documents database saved to {db_file}")
    
    # Return summary for updating honey jar stats
    total_size = sum(len(doc['content'].encode()) for doc in SAMPLE_DOCUMENTS)
    return {
        "document_count": len(SAMPLE_DOCUMENTS),
        "total_size_bytes": total_size,
        "embedding_count": total_chunks  # Actual chunk count
    }

if __name__ == "__main__":
    stats = initialize_sample_documents()
    print(f"\n📊 Summary:")
    print(f"  - Documents: {stats['document_count']}")
    print(f"  - Total size: {stats['total_size_bytes']:,} bytes")
    print(f"  - Embeddings: {stats['embedding_count']}")