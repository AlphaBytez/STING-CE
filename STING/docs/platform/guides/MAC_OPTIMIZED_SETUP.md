# Mac-Optimized Setup for STING-CE

## Overview

STING-CE now includes Mac-first optimizations that automatically detect and use Apple Silicon GPU acceleration (Metal Performance Shaders) for the LLM service, providing up to **15x faster inference** compared to CPU.

## Automatic Platform Detection

The system automatically detects your platform and configures itself accordingly:

- **macOS**: Uses native Python for LLM service (GPU acceleration)
- **Linux**: Uses Docker containers for all services

## Quick Start on Mac

1. **Install STING-CE**:
   ```bash
   ./manage_sting.sh install
   ```
   The installer will automatically:
   - Detect macOS
   - Configure native LLM service with MPS
   - Start other services in Docker
   - Set up proper networking between native and containerized services

2. **Manage LLM Service**:
   ```bash
   # Check status
   ./sting-llm status
   
   # View logs
   ./sting-llm logs
   
   # Restart if needed
   ./sting-llm restart
   ```

## Architecture on Mac

```
┌─────────────────────────────────────────────────────────┐
│                    Host Machine (macOS)                  │
├─────────────────────────────────────────────────────────┤
│  Native Python Process                                   │
│  ┌─────────────────────┐                               │
│  │   LLM Service       │                               │
│  │   - Port: 8085      │                               │
│  │   - Device: MPS     │                               │
│  │   - Memory: 16GB    │                               │
│  └─────────────────────┘                               │
│           ↕                                             │
├─────────────────────────────────────────────────────────┤
│  Docker Containers                                       │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │    Chatbot      │  │    Frontend     │              │
│  │  Connects to    │  │   React App     │              │
│  │ host.docker.    │  │                 │              │
│  │ internal:8085   │  │                 │              │
│  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │     Kratos      │  │    Database     │              │
│  │  Auth Service   │  │   PostgreSQL    │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

## Performance Benefits

| Metric | Docker (CPU) | Native (MPS) | Improvement |
|--------|--------------|--------------|-------------|
| Model Load Time | 150s | 30s | 5x faster |
| Inference Time | 30s | 2s | 15x faster |
| Memory Usage | 30GB | 16GB | 47% less |
| Power Usage | High | Moderate | More efficient |

## Configuration Details

### Environment Variables

The system automatically sets these for Mac:

```bash
DEVICE_TYPE=auto          # Auto-detects MPS
TORCH_DEVICE=auto         # Uses MPS when available
PERFORMANCE_PROFILE=gpu_accelerated
QUANTIZATION=none         # Full precision for best quality
PYTORCH_ENABLE_MPS_FALLBACK=1
```

### Network Configuration

- Native LLM service: `localhost:8085`
- Docker services access via: `host.docker.internal:8085`
- Automatic hostname mapping in `docker-compose.mac.yml`

## Troubleshooting

### MPS Not Detected

1. **Check PyTorch version**:
   ```bash
   python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
   python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
   ```

2. **Update PyTorch** if needed:
   ```bash
   pip3 install --upgrade torch torchvision
   ```

### Service Connection Issues

1. **Check native service**:
   ```bash
   curl http://localhost:8085/health
   ```

2. **Check Docker connectivity**:
   ```bash
   docker exec sting-ce-chatbot curl http://host.docker.internal:8085/health
   ```

### Memory Issues

1. **Monitor memory usage**:
   ```bash
   # During model loading
   top -pid $(cat ~/.sting-ce/run/llm-gateway.pid)
   ```

2. **Use smaller models** if needed:
   ```bash
   export MODEL_NAME=phi3  # 3.8B parameters
   ./sting-llm restart
   ```

## Manual Control

If you need manual control over the LLM service:

### Start Native Service Manually

```bash
# Stop automatic service
./manage_sting.sh stop llm-gateway

# Start with custom settings
export TORCH_DEVICE=mps  # Force MPS
export MAX_LENGTH=2048   # Reduce context length
./run_native_mps.sh
```

### Use Docker Instead

```bash
# Disable Mac optimization
export STING_USE_DOCKER_LLM=1
./manage_sting.sh restart llm-gateway
```

## Development Tips

1. **Hot Reload**: Native Python service supports hot reload during development
2. **Debugging**: Use `TORCH_LOGS=+dynamo` for detailed PyTorch logs
3. **Profiling**: Use `PYTORCH_ENABLE_PROFILING=1` for performance analysis

## Future Improvements

1. **Unified Inference Server**: Single binary with MPS/CUDA/CPU support
2. **Model Caching**: Shared model cache between native and Docker
3. **Dynamic Switching**: Switch between native/Docker without restart
4. **Multi-Model Support**: Run different models on different devices

## Summary

The Mac-optimized setup provides:

- ✅ Automatic MPS (GPU) detection and usage
- ✅ 15x faster inference than CPU
- ✅ Seamless integration with Docker services
- ✅ Zero configuration required
- ✅ Fallback to CPU if MPS unavailable

Just run `./manage_sting.sh install` and enjoy blazing-fast AI on your Mac!