# STING Knowledge Repositories

This directory contains modular knowledge repositories that feed into STING's Honey Jar system, enabling Bee to provide contextual, organization-specific assistance.

## Directory Structure

```
knowledge/
├── sting-platform-docs/      # Core STING platform documentation
├── sting-security-docs/       # Security features and compliance guides  
├── sting-deployment-docs/     # Installation, ops, and troubleshooting
├── custom-org-knowledge/      # Organization-specific documentation
└── external-integrations/     # MCP connectors and API integration guides
```

## Repository Architecture

Each knowledge repository follows a standardized structure:

- **`manifest.json`** - Package metadata, versioning, and honey jar configuration
- **`version.txt`** - Semantic version tracking
- **`*.md files`** - Documentation content (Markdown format)
- **Subdirectories** - Organized by topic/category

## Using Knowledge Repositories

### Upload to Honey Jars
```bash
# Upload all repositories
./manage_sting.sh upload-knowledge

# Upload specific repository with updates
./manage_sting.sh upload-knowledge --update --version 1.1.0

# Dry run to preview uploads
./manage_sting.sh upload-knowledge --dry-run
```

### Bee Integration
Once uploaded, Bee automatically has access to all knowledge repositories and can:
- Answer questions about STING features and configuration
- Provide troubleshooting guidance
- Reference organization-specific procedures
- Suggest optimizations based on deployment patterns

## Repository Purposes

### 🔧 sting-platform-docs
**Core platform documentation**
- Authentication and user management
- Honey Jar knowledge system
- Bee assistant capabilities
- API reference and integration guides

### 🔒 sting-security-docs  
**Security and compliance**
- WebAuthn/Passkey implementation
- PII compliance frameworks (GDPR, HIPAA, CCPA)
- Security architecture and threat modeling
- Encryption and data protection

### 🚀 sting-deployment-docs
**Operations and deployment**
- Hardware requirements and scaling guidance
- Docker resource optimization
- Installation and troubleshooting
- Performance monitoring and tuning

### 🏢 custom-org-knowledge
**Organization-specific content**
- Internal policies and procedures  
- Team contacts and responsibilities
- Custom workflows and integrations
- Organization-specific compliance requirements

### 🔌 external-integrations
**Third-party connectivity**
- Model Context Protocol (MCP) architecture
- GitHub, Slack, and database connectors
- API integration patterns
- Enterprise system connectivity

## Creating New Repositories

1. **Create directory structure**:
   ```bash
   mkdir -p knowledge/my-new-repo
   cd knowledge/my-new-repo
   ```

2. **Create manifest.json**:
   ```json
   {
     "id": "my-new-repo",
     "name": "My Knowledge Base",
     "description": "Description of contents",
     "version": "1.0.0",
     "category": "custom",
     "tags": ["relevant", "tags"],
     "honey_jar": {
       "type": "internal",
       "status": "active",
       "owner": "admin@sting.local",
       "permissions": {...},
       "config": {...}
     },
     "documents": {...}
   }
   ```

3. **Create version.txt**:
   ```bash
   echo "1.0.0" > version.txt
   ```

4. **Add documentation files** and update manifest.json documents section

5. **Upload to Honey Jar**:
   ```bash
   ./manage_sting.sh upload-knowledge
   ```

## Version Management

Each repository is independently versioned:
- **Semantic versioning** (major.minor.patch)
- **Independent updates** - repositories can be updated separately
- **Version tracking** in honey jar metadata
- **Change detection** - only modified content is reprocessed

## Benefits of Modular Structure

### For Teams
- **Separate ownership** - different teams maintain relevant repositories
- **Independent updates** - no need to coordinate releases
- **Focused content** - each repository has a clear scope
- **Git integration** - each repository can be a separate Git repo

### For Bee Assistant
- **Contextual knowledge** - understands organization-specific context
- **First-line support** - answers common questions automatically  
- **Continuous learning** - improves responses as knowledge grows
- **Cross-repository connections** - links related information

### For Organizations  
- **Knowledge consolidation** - single source of truth for all documentation
- **Automated assistance** - reduces support ticket volume
- **Onboarding acceleration** - new team members get instant context
- **Compliance support** - consistent policy application and guidance

## Best Practices

### Content Organization
- **Clear categorization** - use manifest.json categories and tags
- **Consistent formatting** - follow Markdown standards
- **Regular updates** - keep documentation current
- **Cross-references** - link related concepts between repositories

### Security Considerations
- **Sensitive data** - never include passwords, keys, or PII in documentation
- **Access controls** - configure appropriate permissions in manifest.json
- **Review process** - establish content review workflows
- **Audit trails** - track who updates what content

### Performance Optimization
- **Chunk strategy** - configure appropriate chunking for content type
- **Embedding efficiency** - use consistent terminology for better search
- **Incremental updates** - only upload changed content
- **Regular cleanup** - remove outdated documentation

This modular approach transforms STING from a platform into an intelligent assistant that understands your organization's unique context and can provide tailored support and guidance.