# 🐝 Bee Chat File Uploads Guide

## Overview

Bee Chat supports two distinct file upload paths to meet different user needs:

1. **Temporary Chat Uploads** - Files uploaded for analysis within the current chat session
2. **Honey Jar Uploads** - Files permanently stored in the knowledge base for future reference

## Understanding the Difference

### Temporary Chat Uploads
- **Purpose**: Quick file analysis without permanent storage
- **Retention**: 24-48 hours (configurable)
- **Access**: Only available within your current chat session
- **Use Cases**: 
  - Analyzing a document for immediate questions
  - Getting help understanding a file's contents
  - Temporary document review

### Honey Jar Uploads
- **Purpose**: Building a searchable knowledge base
- **Retention**: Permanent until manually deleted
- **Access**: Available to all users with honey jar permissions
- **Use Cases**:
  - Creating organizational knowledge bases
  - Storing reference documentation
  - Building shared resources

## How to Upload Files

### In Bee Chat

1. Click the **Pollen Basket** (🧺) floating action button
2. Select **"Gather Nectar"** (📎) to upload a file
3. Choose your upload type:
   - **"Analyze in this chat"** - Temporary upload
   - **"Save to Honey Jar"** - Permanent storage

### Visual Indicators

When uploading files, you'll see clear indicators:
- 🕐 **Temporary Upload**: "This file will be available for 48 hours"
- 🏺 **Honey Jar Upload**: "Saving to: [Honey Jar Name]"

## Supported File Types

| Format | Extensions | Max Size | Best For |
|--------|------------|----------|----------|
| Documents | .pdf, .docx, .txt | 100MB | Reports, guides, documentation |
| Data | .json, .csv | 100MB | Structured data, configurations |
| Web | .html, .md | 100MB | Web content, markdown docs |
| Images* | .png, .jpg, .jpeg | 100MB | Screenshots, diagrams |

*Image text extraction coming soon

## File Processing

### What Happens to Your Files

1. **Text Extraction**: Content is extracted from your document
2. **Chunking**: Large documents are split into searchable segments
3. **Indexing**: Content is indexed for semantic search
4. **Encryption**: Files are encrypted with your user-specific key

### Processing Time

- Small files (<1MB): Instant
- Medium files (1-10MB): 5-30 seconds
- Large files (10-100MB): 1-5 minutes

## Managing Your Uploads

### Honey Reserve (Storage Quota)

Each user has a **Honey Reserve** of 1GB for storing:
- Temporary chat uploads
- Personal honey jar documents
- Exported reports

Check your usage:
1. Go to Dashboard → Profile
2. View your "Honey Reserve" meter
3. See breakdown by category

### Automatic Cleanup

- Temporary files are automatically deleted after their retention period
- You'll receive a warning when approaching your storage limit
- Oldest temporary files are removed first if quota is exceeded

## Best Practices

### For Temporary Uploads
- Use for one-time analysis needs
- Don't upload sensitive data you need to preserve
- Download any generated insights before expiration

### For Honey Jar Storage
- Organize documents into appropriate honey jars
- Use descriptive filenames
- Add metadata tags for better searchability
- Regularly review and clean up old documents

## Privacy & Security

### Your Files Are Protected
- **Encryption**: All files are encrypted at rest
- **Access Control**: Only you can access your temporary uploads
- **Audit Trail**: All file access is logged
- **Data Deletion**: Files are securely wiped when deleted

### GDPR Compliance
- Export all your data anytime
- Request complete data deletion
- View access logs for your files
- Automated retention policy enforcement

## Troubleshooting

### Common Issues

**"Upload failed" error**
- Check file size (max 100MB)
- Verify file format is supported
- Ensure you have available Honey Reserve space

**"File not found" in chat**
- Temporary files may have expired
- Check if file was uploaded to a honey jar instead

**Bee can't find uploaded content**
- Allow 30 seconds for processing
- Try rephrasing your question
- Specify the filename in your query

### Getting Help

If you encounter issues:
1. Check your Honey Reserve usage
2. Verify the file format is supported
3. Contact support with the upload timestamp

## Advanced Features

### Batch Uploads
- Select multiple files at once
- All files share the same upload type
- Progress shown for each file

### API Access
For programmatic uploads:
```bash
# Temporary upload
curl -X POST https://sting.local/api/bee/upload-temp \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"

# Honey jar upload  
curl -X POST https://sting.local/api/honey-jars/JAR_ID/documents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

---

*Remember: Bee Chat is here to help you understand and analyze your documents. Choose the right upload type for your needs!*