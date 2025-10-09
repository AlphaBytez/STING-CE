# Developer Preview Guide

This guide explains how to work with the STING CE Developer Preview.

## Purpose

The STING CE Developer Preview provides a clean, focused version of the platform that:
- Removes deprecated features and code
- Focuses on core functionality for developers
- Provides a stable foundation for building AI applications
- Maintains security and privacy features

## Key Components

### Core Services
1. **Backend API** - Flask/Python services for business logic
2. **Authentication** - Ory Kratos passwordless identity management
3. **Knowledge Management** - Honey Jar system with vector search
4. **LLM Integration** - Ollama support for local AI models
5. **Chatbot Engine** - Bee assistant with context awareness
6. **Messaging System** - Encrypted messaging capabilities

### Architecture Overview

```
┌─────────────┐     ┌────────────┐     ┌───────────────┐     ┌──────────────┐
│   Frontend  │────▶│  Backend   │────▶│  Knowledge    │────▶│    Chroma    │
│   (React)   │     │   (Flask)  │     │   Service     │     │  Vector DB   │
└─────────────┘     └─────┬──────┘     └───────────────┘     └──────────────┘
       │                  │                     │
       │                  ▼                     │
       │            ┌────────────┐              │
       │            │  External  │              │
       │            │ AI Service │◀─────────────┘
       │            │ (Ollama)   │
       ▼            └────────────┘
┌─────────────┐     ┌────────────┐     ┌───────────────┐
│   Kratos    │     │ PostgreSQL │     │    Redis      │
│    Auth     │     │            │     │   Cache       │
└─────────────┘     └────────────┘     └───────────────┘
```

## Service Details

### Backend API (Port 5050)
Main application server handling:
- User management and profiles
- Honey Jar (document storage)
- Honey Reserve (encrypted storage)
- Nectar Bot API key management
- Integration orchestration

### Knowledge Service (Port 8090)
Vector search and document processing:
- Document ingestion and chunking
- Embedding generation
- Semantic search
- Context retrieval

### Chatbot Service (Port 8888)
"Bee" AI assistant:
- Conversational AI
- Context-aware responses
- Tool integration
- Multi-turn dialogue

### External AI Service (Port 8091)
Ollama integration layer:
- Model management
- Inference requests
- Streaming responses
- PII filtering

### Messaging Service (Port 8889)
Encrypted messaging system:
- Message queue management
- Real-time notifications
- Redis-backed persistence

## Development Workflow

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/sting-ce-dev-preview.git
cd sting-ce-dev-preview

# Review and customize environment files
nano conf/env/app.env
nano conf/env/kratos.env
# ... etc
```

### 2. Start Development Environment

```bash
# Build all services
./manage_sting_dev.sh build

# Start all services
./manage_sting_dev.sh start

# Check status
./manage_sting_dev.sh status
```

### 3. Working with Services

```bash
# View logs for a specific service
./manage_sting_dev.sh logs app
./manage_sting_dev.sh logs knowledge

# Restart after code changes
./manage_sting_dev.sh restart app

# Update service (rebuild and restart)
./manage_sting_dev.sh update app
```

### 4. Testing

```bash
# Test backend API
curl http://localhost:5050/health

# Test knowledge service
curl http://localhost:8090/health

# Test chatbot
curl http://localhost:8888/health

# Access Chroma directly
curl http://localhost:8000/api/v1/heartbeat
```

## Configuration

### Environment Files

All service configuration is in `conf/env/`:
- `app.env` - Backend API configuration
- `kratos.env` - Authentication service
- `knowledge.env` - Knowledge/vector search
- `chatbot.env` - Bee chatbot
- `external-ai.env` - Ollama integration

### Database Initialization

Database schemas and initial data are in `database/init_scripts/`.

### Kratos Configuration

Identity schemas and email templates are in `kratos/`:
- `identity_schemas/` - User identity definitions
- `courier_templates/` - Email templates for magic links

## Best Practices

### 1. Service Development
- Keep services loosely coupled
- Use environment variables for configuration
- Implement health check endpoints
- Add comprehensive logging

### 2. API Design
- Follow RESTful principles
- Use proper HTTP status codes
- Version your APIs
- Document all endpoints

### 3. Security
- Never commit secrets
- Use environment variables
- Implement proper authentication
- Validate all inputs

### 4. Testing
- Write unit tests for business logic
- Add integration tests for APIs
- Test service interactions
- Use mock data for development

## Troubleshooting

### Services Won't Start

```bash
# Check Docker status
docker ps -a

# View service logs
./manage_sting_dev.sh logs <service-name>

# Rebuild specific service
./manage_sting_dev.sh update <service-name>
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep sting-ce-dev-db

# Test database connection
docker exec -it sting-ce-dev-db psql -U postgres -d sting_app
```

### Port Conflicts

If ports are already in use, edit `docker-compose.dev.yml` to change port mappings:

```yaml
ports:
  - "5051:5050"  # Change host port from 5050 to 5051
```

## Next Steps

1. **Explore the APIs** - Review docs/api/ for endpoint documentation
2. **Add Features** - Build new functionality in the service directories
3. **Write Tests** - Add tests in each service's test directory
4. **Deploy** - Configure for production deployment
5. **Contribute** - Submit pull requests with improvements

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/sting-ce-dev-preview/issues
- Documentation: docs/ directory
- Community: [Discord/Slack/Forum link]
