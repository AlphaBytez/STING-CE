# Honey Jars Guide

## What are Honey Jars?

This guide provides an overview of Honey Jars - STING's intelligent knowledge containers. For comprehensive details, see:
- `docs/features/HONEY_JAR_USER_GUIDE.md` - Complete user guide with step-by-step instructions
- `docs/features/HONEY_JAR_TECHNICAL_REFERENCE.md` - Technical implementation details
- `docs/features/HONEY_JAR_EXPORT_IMPORT_SYSTEM.md` - Export/import system (HJX format)
- `docs/features/HONEY_JAR_ACCESS_CONTROL.md` - Permissions and security

Honey Jars are STING's intelligent knowledge containers that store, organize, and make your documents searchable through AI-powered semantic search. Think of them as secure, smart filing cabinets that understand the meaning of your content.

## Creating Honey Jars

### Basic Setup
1. Navigate to **Hive Manager** from your dashboard
2. Click **"Create New Honey Jar"**
3. Fill in the required information:
   - **Name**: Choose a descriptive name
   - **Description**: Brief explanation of the jar's purpose
   - **Category**: Select from predefined categories
   - **Privacy Level**: Public or Private
   - **Tags**: Add relevant keywords for searchability

### Honey Jar Categories
- **Documentation**: Technical docs, user guides, procedures
- **Marketing**: Campaigns, copy, promotional materials
- **HR**: Policies, procedures, employee documents
- **Finance**: Reports, budgets, financial data
- **Security**: Protocols, incident reports, audit logs
- **Research**: R&D documents, studies, analysis
- **Legal**: Contracts, agreements, compliance docs
- **Customer Service**: Support tickets, FAQs, responses

## Managing Documents

### Uploading Files
1. Select your honey jar from the Hive Manager
2. Click **"Upload Documents"**
3. Drag and drop files or click to browse
4. Supported formats:
   - **Text**: .txt, .md, .rtf
   - **Documents**: .pdf, .docx, .odt
   - **Spreadsheets**: .xlsx, .csv, .ods
   - **Presentations**: .pptx, .odp
   - **Images**: .jpg, .png, .gif (with OCR)
   - **Archives**: .zip (extracts contents)

### Document Processing
After upload, STING automatically:
- **Extracts Text**: From PDFs, images, and documents
- **Detects PII**: Identifies sensitive information
- **Categorizes Content**: Assigns relevant tags
- **Creates Embeddings**: For AI search capabilities
- **Generates Summaries**: Brief content overviews

### Document Status
- **Processing**: Being analyzed and indexed
- **Ready**: Available for search and chat
- **Error**: Failed processing (review required)
- **Pending Approval**: Waiting for admin review (if enabled)

## Permissions and Sharing

### Permission Levels
- **Owner**: Full control, can delete jar and all contents
- **Editor**: Can add, edit, and remove documents
- **Viewer**: Can read documents and chat with jar
- **No Access**: Cannot see or interact with jar

### Sharing Options
1. **Public Jars**: Accessible to all users in your organization
2. **Private Jars**: Only accessible to specific users
3. **Team Jars**: Shared with specific teams or groups
4. **Read-Only**: Viewers can see content but not modify

### Managing Access
1. Go to your honey jar settings
2. Click **"Manage Permissions"**
3. Add users by email or username
4. Set their permission level
5. Save changes

## Search and Discovery

### Finding Honey Jars
- **Browse**: View all jars in the Hive Manager
- **Search**: Use keywords to find specific jars
- **Filter**: By category, owner, or privacy level
- **Sort**: By name, creation date, or last modified

### Document Search
- **Full-Text Search**: Search within document contents
- **Metadata Search**: Find by title, tags, or author
- **Date Filters**: Narrow by creation or modification date
- **File Type Filters**: Search specific document types

## AI Integration

### Bee Chat Integration
1. Select a honey jar in Bee Chat
2. Ask questions about the documents
3. Get intelligent responses with citations
4. Follow up with related questions

### Smart Suggestions
- **Related Documents**: Discover connected content
- **Similar Jars**: Find jars with related themes
- **Content Gaps**: Identify missing information
- **Update Notifications**: Know when content changes

## Organization Best Practices

### Naming Conventions
- Use clear, descriptive names
- Include date ranges for time-sensitive content
- Use consistent abbreviations
- Examples:
  - "Q3 2024 Marketing Materials"
  - "Employee Handbook v2.1"
  - "Security Protocols - 2024"

### Tagging Strategy
- Use specific, relevant tags
- Create a tag taxonomy for your organization
- Include both broad and specific tags
- Examples: `quarterly-report`, `finance`, `2024`, `budget`

### Regular Maintenance
- **Monthly Reviews**: Check for outdated content
- **Archive Old Jars**: Move inactive jars to archives
- **Update Descriptions**: Keep jar descriptions current
- **Review Permissions**: Ensure access is still appropriate

## Advanced Features

### Honey Reserve (Storage Management)
- **Quota Monitoring**: Track storage usage per jar
- **Automatic Cleanup**: Remove temporary files after 48 hours
- **Compression**: Optimize storage for large documents
- **Retention Policies**: Set automatic deletion rules

### PII Protection
- **Automatic Detection**: Identify sensitive information
- **Scrubbing Options**: Remove or mask PII automatically
- **Compliance Reports**: Generate privacy compliance reports
- **Audit Trails**: Track all PII-related operations

### Versioning
- **Document Versions**: Track changes to documents
- **Rollback**: Restore previous versions
- **Change Logs**: See who changed what and when
- **Compare Versions**: View differences between versions

## Troubleshooting

### Common Issues

#### "Document Failed to Process"
- Check file format is supported
- Ensure file isn't corrupted
- Try re-uploading the document
- Contact support if issue persists

#### "Cannot Access Honey Jar"
- Verify you have the correct permissions
- Check if the jar is private
- Ask the owner to grant you access
- Ensure you're logged into the correct account

#### "Search Results Not Appearing"
- Allow time for document processing
- Check that documents show "Ready" status
- Try different search terms
- Verify the jar contains relevant content

### Performance Tips
- **Batch Uploads**: Upload multiple files at once for efficiency
- **Compress Large Files**: Use ZIP archives for multiple documents
- **Regular Cleanup**: Remove unnecessary documents periodically
- **Optimize PDFs**: Use compressed PDFs when possible

## Integration Options

### API Access
- RESTful API for programmatic access
- Upload documents via API
- Query jar contents programmatically
- Manage permissions through API

### Webhooks
- Receive notifications for jar changes
- Trigger external workflows
- Sync with other systems
- Monitor document processing status

### Export Options
- **Full Jar Export**: Download all documents as ZIP
- **Metadata Export**: Export jar structure as JSON/CSV
- **Search Results**: Export search results
- **Reports**: Generate and export jar statistics

For more information or support with Honey Jars, contact support@alphabytez.com or visit the help section in your STING dashboard.