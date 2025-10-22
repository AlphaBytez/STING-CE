# LLM Service Always-Ready Architecture Plan

## Overview
STING's LLM service must be a core, always-ready service that starts automatically during installation and remains available to serve requests at any time. This document outlines the plan to ensure reliable LLM service availability.

## Current Issues
1. **Installation Gap**: `msting llm start` is not executed during installation
2. **Dependency Failures**: Python dependencies for LLM service are not properly installed
3. **Service Readiness**: No verification that LLM service is actually ready to serve requests

## Requirements
- LLM service MUST start automatically during installation
- Service MUST be verified as ready before installation completes
- Service MUST remain running and ready to serve requests 24/7
- No aggressive power-saving or memory offloading for core functionality

## Implementation Plan

### 1. Installation Enhancement
- Add LLM service startup to the installation workflow
- Ensure Python dependencies are installed in the virtual environment
- Verify service health before declaring installation complete

### 2. Service Readiness Verification
```bash
# Check if LLM gateway is responding
curl -f http://localhost:8086/health || exit 1
# Test actual model loading
curl -X POST http://localhost:8086/models/load -d '{"model": "default"}' || exit 1
# Verify model can generate responses
curl -X POST http://localhost:8086/generate -d '{"prompt": "test", "max_tokens": 10}' || exit 1
```

### 3. Resource Management Strategy
- **Primary Mode**: Always-ready, full service availability
- **Optional Power Saving** (future enhancement):
  - Keep models loaded for X minutes after last request
  - Spin down to low-power state but maintain quick restart capability
  - Never fully unload core models

### 4. Service Architecture
```
Installation Flow:
1. Install base services
2. Start LLM gateway
3. Load default model
4. Verify service readiness
5. Complete installation only if LLM is ready
```

### 5. Monitoring and Recovery
- Health checks every 30 seconds
- Automatic restart on failure
- Alert logging for service issues
- Integration with debug page for manual checks

## Implementation Steps

### Phase 1: Fix Installation (Immediate)
1. Add LLM dependency installation to setup process
2. Add `msting llm start` to installation workflow
3. Add readiness verification before installation completes

### Phase 2: Enhance Reliability
1. Implement comprehensive health checks
2. Add automatic recovery mechanisms
3. Create troubleshooting scripts

### Phase 3: Debug Page Integration
1. Add LLM status indicator
2. Add manual health check button
3. Add service restart capabilities
4. Display model loading status

## Configuration Updates Needed
- Set `llm_service.enabled: true` by default
- Configure `llm_service.always_ready: true`
- Set appropriate startup timeouts for model loading
- Document hardware requirements clearly

## Documentation Updates
- Clarify that LLM service is a core, always-on component
- Document minimum hardware requirements
- Provide troubleshooting guide for LLM service issues
- Add monitoring best practices

## Success Criteria
- LLM service starts automatically during every installation
- Service responds to health checks within 5 seconds
- Models remain loaded and ready to serve
- Zero manual intervention required for basic operation