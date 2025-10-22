# STING Documentation - Reorganized Structure

This directory contains the reorganized STING documentation for better navigation and searchability.

## 📁 Directory Structure

### `/admin/` - Administrative Documentation
- Admin setup guides
- User management
- System administration
- Recovery procedures

### `/api/` - API References
- REST API documentation  
- WebAuthn API references
- Integration guides
- API examples

### `/architecture/` - Technical Architecture
- System architecture documents
- Database schemas
- Service interactions
- Security architecture

### `/features/` - Feature Documentation
- Individual feature guides
- Bee Chat system
- Honey Reserve storage
- PII compliance
- Authentication systems

### `/guides/` - User & Developer Guides
- Quick start guides
- Development workflows
- Testing procedures
- Best practices

### `/public-bee/` - Public Bee Service Documentation
- AI-as-a-Service setup
- Bot configuration
- API documentation
- Scaling guides

### `/security/` - Security Documentation
- Security policies
- Authentication flows
- Compliance guides
- Audit procedures

### `/troubleshooting/` - Common Issues & Solutions
- Known issues
- Error resolution
- Debugging guides
- FAQ

### `/development/` - Development Documentation
- Development setup
- Code standards
- Build processes
- Deployment guides

## 🔍 Finding Documentation

Use these commands to search across all documentation:

```bash
# Search for specific topics
grep -r "authentication" docs/organized/
grep -r "admin" docs/organized/admin/
grep -r "API" docs/organized/api/

# List all files in a category
find docs/organized/features/ -name "*.md"
```

## 📝 Contributing

When adding new documentation:
1. Choose the appropriate category
2. Use descriptive filenames
3. Include proper headers and table of contents
4. Cross-reference related documents

## 🚀 Quick Links

- [Admin Setup Guide](admin/ADMIN_SETUP.md)
- [API Reference](api/API_REFERENCE.md)
- [Architecture Overview](architecture/ARCHITECTURE.md)
- [Public Bee Setup](public-bee/PUBLIC_BEE_SETUP.md)
- [Security Guide](security/SECURITY_GUIDE.md)
- [Troubleshooting](troubleshooting/COMMON_ISSUES.md)

---
*Last updated: August 2025*