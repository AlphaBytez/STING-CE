# Honey Jar User Guide

## Overview

Honey Jars are STING's intelligent knowledge containers that store, organize, and make your documents searchable through AI-powered semantic search. Think of them as secure, smart filing cabinets that understand the meaning of your content.

## Key Features

### 🍯 Document Management
- **Multi-format Support**: Upload PDF, Word, Markdown, JSON, HTML, and text files
- **Bulk Upload**: Drag and drop multiple files at once
- **Real-time Processing**: Watch as documents are processed and indexed
- **Metadata Tagging**: Organize documents with custom tags and categories

### 🔍 Intelligent Search
- **Semantic Search**: Find documents by meaning, not just keywords
- **Vector Embeddings**: Documents are converted to AI-understandable formats
- **Relevance Scoring**: Results ranked by semantic similarity

### 🐝 Query with Bee Integration
- **Context-Aware Chat**: Ask Bee questions about specific honey jar contents
- **Automatic Context**: Bee understands which honey jar you're discussing
- **Natural Language**: Ask questions in plain English

### 📦 Export & Sharing
- **HJX Format**: STING's proprietary Honey Jar Export format (recommended)
  - Includes all documents and metadata
  - Preserves embeddings and search capabilities
  - Can be imported into other STING instances
- **JSON Export**: Plain JSON with all metadata for integration
- **TAR Archive**: Simple archive of all documents for backup

## Getting Started

### Creating Your First Honey Jar

1. Navigate to the **Honey Jars** tab in your dashboard
2. Click **Create Honey Jar** button
3. Fill in:
   - **Name**: A descriptive name for your knowledge base
   - **Description**: What this honey jar contains
   - **Type**: Choose visibility level:
     - `Public`: Accessible to all users
     - `Private`: Only you can access
     - `Team`: Shared with your team
     - `Restricted`: Specific user permissions

### Uploading Documents

1. Open a honey jar by clicking on it
2. Click the green **Upload Documents** button
3. Select files or drag & drop them
4. Wait for processing to complete (progress shown in real-time)

**Note on Document Approval**:
- **Admin users**: Documents are uploaded immediately
- **Honey jar owners**: Documents are uploaded immediately to their own honey jars
- **Regular users on public honey jars**: Documents go to a pending queue for admin approval
- You'll see a message indicating if your documents require approval

### Querying with Bee

1. In the honey jar details view, click **Query with Bee**
2. You'll be taken to the chat interface with:
   - The honey jar context pre-loaded
   - A suggested initial question
   - Visual indicator showing which honey jar is active
3. Ask questions naturally - Bee will search only within that honey jar
4. Click the X button next to the honey jar name to clear context

### Exporting Honey Jars

1. Open the honey jar you want to export
2. Click the **Export** button
3. Choose your format:
   - **HJX Format** (recommended): Complete export with all data
   - **JSON Format**: For developers and integrations
   - **TAR Archive**: Simple document backup
4. The download will start automatically

## Advanced Features

### Sample Documents

New honey jars come pre-loaded with sample STING documentation:
- Platform Overview
- Honeypot Setup Guide
- API Reference
- Security Best Practices
- Threat Analysis Patterns

These help you understand the system and can be deleted if not needed.

### Search Capabilities

The knowledge service uses advanced vector search technology:
- Documents are chunked into semantic segments
- Each segment is converted to a high-dimensional vector
- Searches find conceptually similar content, not just keyword matches

### Integration with Bee

When you query with Bee while a honey jar is active:
- Bee searches only within that specific honey jar
- Responses are enhanced with relevant document snippets
- Source documents are referenced in responses
- Context remains active until manually cleared

## Best Practices

### Document Organization

1. **Use Descriptive Names**: Name honey jars clearly (e.g., "Q4 2024 Financial Reports")
2. **Tag Consistently**: Use standardized tags across your organization
3. **Regular Updates**: Keep documents current by removing outdated versions
4. **Size Limits**: Keep individual documents under 50MB for optimal performance

### Security Considerations

1. **Access Control**: Set appropriate visibility levels for sensitive data
2. **Regular Audits**: Review who has access to your honey jars
3. **Export Carefully**: Exported honey jars contain all document content
4. **Delete Securely**: Removing documents permanently deletes them

### Performance Tips

1. **Batch Uploads**: Upload multiple related documents together
2. **Wait for Processing**: Let documents fully process before searching
3. **Use Specific Queries**: More specific questions yield better results
4. **Monitor Stats**: Check document and embedding counts regularly

## Troubleshooting

### Common Issues

**"Using offline data" warning**
- This appears when the knowledge service is temporarily unavailable
- Your data is safe - try refreshing the page
- If persistent, contact your administrator

**Upload failures**
- Check file size (max 50MB per file)
- Ensure file format is supported
- Verify you have upload permissions for the honey jar
- If you see "permission denied", you may need admin approval for uploads

**Query with Bee not working**
- Ensure you're logged in
- Check that the honey jar has processed documents
- Try clearing browser cache if navigation fails

**Export taking too long**
- Large honey jars may take time to package
- Check your browser's download folder
- Try a different export format if one fails

### Getting Help

For additional support:
- Check the platform documentation in the sample honey jar
- Contact your system administrator
- Submit a support ticket through the help menu

## Glossary

- **Honey Jar**: A knowledge container storing related documents
- **Embeddings**: Mathematical representations of document meaning
- **Vector Search**: Finding documents by conceptual similarity
- **HJX Format**: Honey Jar Export - STING's native export format
- **Semantic Search**: Search by meaning rather than exact keywords
- **Nectar Processing**: The system that extracts and indexes document content