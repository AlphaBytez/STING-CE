# Model Context Protocol (MCP) Integration Architecture

## Overview

STING leverages Anthropic's Model Context Protocol (MCP) to enable secure, standardized connections between Bee (our AI assistant) and external data sources including databases, APIs, and enterprise systems.

## MCP Architecture in STING

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bee Assistant │◄──►│   MCP Server    │◄──►│ External Source │
│                 │    │   (STING)       │    │   (GitHub)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐               │
         └─────────────►│ Sanitization   │◄──────────────┘
                        │ Pipeline       │
                        └─────────────────┘
```

### MCP Server Implementation

**Location**: `/mcp_servers/sting_mcp_server.py`

```python
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool

class STINGMCPServer:
    """Base MCP server for STING data connectivity"""
    
    async def get_available_tools(self):
        return [
            Tool(
                name="query_honey_jar",
                description="Search knowledge bases with PII scrubbing",
                parameters={
                    "query": {"type": "string"},
                    "jar_id": {"type": "string"},
                    "sanitization_level": {"enum": ["basic", "strict", "gdpr"]}
                }
            ),
            Tool(
                name="get_system_reports", 
                description="Retrieve sanitized system reports",
                parameters={
                    "report_type": {"enum": ["security", "performance", "usage"]},
                    "time_range": {"type": "string"}
                }
            )
        ]
```

## Enterprise Integration Patterns

### 1. GitHub Knowledge Sync

**Use Case**: Automatically sync documentation from private GitHub repositories

```yaml
github_connector:
  type: mcp_server
  endpoint: "https://api.github.com"
  authentication:
    type: github_app
    app_id: "${GITHUB_APP_ID}"
    private_key: "${GITHUB_PRIVATE_KEY}"
  
  sync_rules:
    - repo: "company/internal-docs"
      paths: ["docs/**/*.md", "README.md"]
      honey_jar: "company-documentation"
      schedule: "0 */6 * * *"  # Every 6 hours
      
    - repo: "company/api-docs"  
      paths: ["api/**/*.yaml", "openapi.json"]
      honey_jar: "api-documentation"
      auto_generate_examples: true
```

### 2. Slack Team Knowledge

**Use Case**: Index relevant Slack conversations and shared files

```yaml
slack_connector:
  type: mcp_server
  endpoint: "https://slack.com/api"
  authentication:
    type: oauth2
    bot_token: "${SLACK_BOT_TOKEN}"
    
  indexing_rules:
    channels: ["#engineering", "#product", "#support"]
    file_types: [".pdf", ".docx", ".md"]
    exclude_patterns: ["password", "api_key", "secret"]
    pii_scrubbing: "strict"
    retention_days: 30
```

### 3. Database Knowledge Mining

**Use Case**: Extract documentation and metadata from databases

```yaml
database_connector:
  type: mcp_server
  connection:
    driver: "postgresql"
    host: "${DB_HOST}"
    database: "${DB_NAME}"
    
  extraction_rules:
    - table_comments: true
      column_descriptions: true
      constraint_documentation: true
    - stored_procedures: true
      function_documentation: true
    - sample_queries: 
        enabled: true
        sanitize_data: true
        max_rows: 10
```

## Security & Privacy

### Data Sanitization Pipeline

**Automatic PII Detection**:
- Email addresses → `[EMAIL_REDACTED]`
- Phone numbers → `[PHONE_REDACTED]`  
- SSNs/Tax IDs → `[ID_REDACTED]`
- API keys/secrets → `[SECRET_REDACTED]`

**Configurable Sanitization Levels**:
- **Basic**: Remove obvious secrets and tokens
- **Strict**: Remove all potential PII patterns
- **GDPR**: Full compliance mode with audit logging

### Authentication Security

All MCP connections use secure authentication:
- **OAuth2**: For APIs supporting standard flows
- **API Keys**: Stored in HashiCorp Vault
- **Certificates**: Mutual TLS for database connections
- **JWT**: For service-to-service authentication

## Deployment Configuration

### MCP Server Registry

**Location**: `/mcp_servers/registry.yaml`

```yaml
servers:
  sting-platform:
    command: ["python", "/app/mcp_servers/sting_mcp_server.py"]
    environment:
      STING_API_KEY: "${STING_MCP_API_KEY}"
      SANITIZATION_LEVEL: "strict"
      
  github-sync:
    command: ["python", "/app/mcp_servers/github_connector.py"] 
    environment:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
      SYNC_SCHEDULE: "0 */6 * * *"
      
  slack-knowledge:
    command: ["python", "/app/mcp_servers/slack_connector.py"]
    environment:
      SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
      CHANNEL_WHITELIST: "engineering,product,support"
```

### Container Integration

MCP servers run as sidecar containers alongside STING:

```yaml
mcp-gateway:
  build: ./mcp_servers
  environment:
    - MCP_REGISTRY_PATH=/app/registry.yaml
    - STING_API_URL=https://app:5050
  volumes:
    - ./mcp_servers:/app/mcp_servers
    - mcp_data:/app/data
  depends_on:
    - app
    - knowledge
```

## Benefits for Organizations

### Knowledge Consolidation
- **Single Interface**: Bee can access all organizational knowledge through MCP
- **Contextual Responses**: Answers include relevant context from multiple sources  
- **Version Tracking**: Automatic updates when source documents change

### Developer Productivity  
- **API Documentation**: Auto-generated examples from OpenAPI specs
- **Code Context**: Repository structure and documentation accessible to Bee
- **Troubleshooting**: System logs and metrics available for debugging

### Compliance & Governance
- **Audit Trail**: All data access logged and monitored
- **Data Residency**: Knowledge stays within organizational boundaries
- **Access Control**: Fine-grained permissions per data source

This MCP architecture transforms STING into a comprehensive knowledge platform that securely connects to your entire organizational ecosystem while maintaining privacy and compliance requirements.