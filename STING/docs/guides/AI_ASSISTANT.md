# AI Assistant Guide for STING

This document provides essential information for AI assistants working on the STING (Security Testing Intelligence and Network Guardian) project.

## Project Overview

STING is a comprehensive cybersecurity platform that combines:
- **Network Security Testing**: Automated vulnerability scanning and penetration testing
- **AI-Powered Analysis**: LLM-based report generation and threat intelligence
- **Knowledge Management**: Centralized security knowledge base and documentation
- **Cross-Platform Support**: Mac, Linux, and Windows WSL compatibility

## Architecture Overview

```
Frontend (React) → Backend Services → External AI Service → Ollama/LLM
                 ↓
            Database Layer (PostgreSQL)
                 ↓
            Knowledge Base & File Storage
```

### Core Services
- **Frontend**: React-based web interface (port 8443)
- **Backend**: Python FastAPI services (port 8000)
- **External AI Service**: LLM bridge service (port 8091)
- **Ollama**: Local LLM server (port 11434)
- **Database**: PostgreSQL with custom schemas

## Key Commands & Scripts

### Service Management
```bash
# Start all services
./sting-services start

# Start LLM services (modern Ollama-based)
./sting-llm start

# Check service status
./sting-services status
./sting-llm status

# Install Ollama (if not present)
./sting-services install-ollama
```

### Development & Testing
```bash
# Run tests
npm test                    # Frontend tests
python -m pytest          # Backend tests

# Linting & Type Checking
npm run lint               # Frontend linting
npm run typecheck         # TypeScript checking
ruff check .              # Python linting
mypy .                    # Python type checking

# Build & Deploy
docker-compose up --build  # Full rebuild
npm run build             # Frontend build only
```

### Database & Migration
```bash
# Database operations
python manage_users.py     # User management
python migration_helper.py # Schema migrations
```

## Important File Locations

### Configuration
- `conf/config.yml.default` - Main configuration template
- `conf/config_loader.py` - Configuration management
- `.env` - Environment variables
- `docker-compose.yml` - Service orchestration

### Core Services
- `external_ai_service/app.py` - AI service bridge
- `backend/` - Main backend services
- `frontend/src/` - React frontend components
- `scripts/` - Installation and utility scripts

### Documentation
- `README.md` - Main project documentation
- `OLLAMA_MIGRATION_PROGRESS.md` - Recent migration details
- Various `*.md` files for specific features/fixes

## Development Guidelines

### Code Style & Standards
- **Python**: Follow PEP 8, use type hints, prefer async/await
- **JavaScript/React**: Use modern ES6+, functional components, hooks
- **Configuration**: YAML for config files, environment variables for secrets
- **Documentation**: Markdown for docs, inline comments for complex logic

### Testing Requirements
- Always run linting and type checking before committing
- Test both modern (Ollama) and legacy LLM modes when applicable
- Verify cross-platform compatibility (Mac/Linux/WSL)
- Test service startup order and dependencies

### Security Considerations
- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive configuration
- Validate all user inputs and API responses
- Follow principle of least privilege for service permissions

## Common Tasks

### Adding New Features
1. Plan the task using todo management tools
2. Research existing codebase patterns and conventions
3. Implement following established architecture patterns
4. Add appropriate tests and documentation
5. Run linting/type checking before completion
6. Test in both development and production-like environments

### Debugging Issues
1. Check service logs: `docker-compose logs [service-name]`
2. Verify service health endpoints
3. Check configuration files for consistency
4. Test individual components in isolation
5. Use debugging scripts in project root

### Configuration Changes
1. Update `conf/config.yml.default` for new options
2. Modify `conf/config_loader.py` for new config classes
3. Update environment variable documentation
4. Test with both default and custom configurations

## Migration Context (Ollama Integration)

The project recently migrated from Mac-only LLM server to universal Ollama-based solution:

### Modern Stack (Recommended)
- Uses Ollama for cross-platform LLM support
- Default model: `phi3:mini` (optimal speed/quality balance)
- Universal installer supports Mac/Linux/Windows WSL
- Service bridge handles API translation

### Legacy Stack (Deprecated)
- Mac-only LLM server implementation
- Maintained for backward compatibility
- Will be removed in future versions

### Key Migration Files
- `external_ai_service/app.py` - New AI service bridge
- `scripts/install_ollama.sh` - Universal Ollama installer
- `sting-llm` - Modern/legacy mode management script

## Troubleshooting

### Common Issues
1. **Service startup failures**: Check Docker daemon, port conflicts
2. **LLM connection issues**: Verify Ollama installation and model availability
3. **Frontend build errors**: Clear node_modules, check dependencies
4. **Database connection**: Verify PostgreSQL service and credentials
5. **Permission errors**: Check file ownership and Docker permissions

### Debug Commands
```bash
# Service health checks
curl http://localhost:8091/health    # AI service
curl http://localhost:11434/api/tags # Ollama models

# Log inspection
docker-compose logs -f [service]     # Live service logs
tail -f bee.log                      # Application logs

# System verification
./check-mac-setup.sh                 # Mac-specific checks
docker system prune                  # Clean Docker resources
```

## Best Practices for AI Assistants

1. **Always use todo management** for complex tasks
2. **Read existing code** before making changes to understand patterns
3. **Test thoroughly** - run lints, type checks, and functional tests
4. **Follow security practices** - never expose secrets or credentials
5. **Document changes** - update relevant documentation files
6. **Verify cross-platform compatibility** when possible
7. **Use existing utilities** - leverage project scripts and tools
8. **Maintain backward compatibility** unless explicitly migrating

## Getting Help

- Check existing documentation files (*.md) for specific topics
- Review recent migration progress in `OLLAMA_MIGRATION_PROGRESS.md`
- Examine service logs for runtime issues
- Test individual components to isolate problems
- Use project scripts for common operations rather than manual commands

---

*This document should be updated as the project evolves. When making significant architectural changes, please update this guide accordingly.*