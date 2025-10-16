# STING CE Model Modes Guide

## Overview

STING CE now supports two model modes to balance performance, quality, and resource usage:

1. **Small Models Mode** (Default) - Fast, lightweight models ideal for most use cases
2. **Performance Mode** - Large, state-of-the-art models for maximum quality

## Quick Start

### Using the Model Manager

The easiest way to manage model modes is using the model manager script:

```bash
# Check current status
./sting-model-manager.sh status

# Switch to small models (default)
./sting-model-manager.sh small

# Switch to performance models
./sting-model-manager.sh performance

# Download small models
./sting-model-manager.sh download
```

## Model Comparison

### Small Models Mode (Recommended)

| Model | Size | Use Case | Memory Usage |
|-------|------|----------|--------------|
| DeepSeek-R1-1.5B | 1.5GB | Reasoning & logic | ~3GB |
| TinyLlama-1.1B | 2.2GB | General chat | ~3GB |
| DialoGPT-medium | 345MB | Conversations | ~1GB |

**Total Download**: ~5GB  
**Total RAM Required**: 8GB  
**Startup Time**: 30-60 seconds

### Performance Mode

| Model | Size | Use Case | Memory Usage |
|-------|------|----------|--------------|
| Llama-3.1-8B | 16GB | State-of-the-art | ~16GB |
| Phi-3-medium-128k | 28GB | Long context | ~32GB |
| Zephyr-7B | 14GB | Technical tasks | ~16GB |

**Total Download**: ~58GB  
**Total RAM Required**: 32GB+  
**Startup Time**: 5-10 minutes

## Installation

### Option 1: Install with Small Models (Recommended)

```bash
# Download small models first
./download_optimized_models.sh

# Install STING with small models
./manage_sting.sh install

# The system will use small models by default
```

### Option 2: Manual Model Download

```bash
# For small models only
./download_optimized_models.sh

# For large models (optional)
./manage_sting.sh download_models
```

## Switching Between Modes

### Method 1: Using Model Manager (Easiest)

```bash
# Switch to small models
./sting-model-manager.sh small

# Switch to performance models
./sting-model-manager.sh performance
```

### Method 2: Using Docker Compose

```bash
# For small models
docker compose -f docker-compose.yml -f docker-compose.small-models.yml up -d

# For performance models
docker compose -f docker-compose.yml -f docker-compose.performance-models.yml up -d
```

### Method 3: Environment Variables

```bash
# Set active model
export ACTIVE_MODEL=deepseek-1.5b  # or tinyllama, dialogpt, llama3, phi3, zephyr

# Restart services
docker compose restart llm-gateway
```

## Model Selection Guide

### When to Use Small Models

- Development and testing
- Resource-constrained environments (VMs, older hardware)
- Quick prototyping
- General chatbot conversations
- Fast response times needed

### When to Use Performance Models

- Production deployments with ample resources
- Complex reasoning tasks
- Code generation
- Technical documentation
- Multi-language support
- Maximum quality requirements

## DeepSeek Models

We've added DeepSeek models as an excellent middle ground:

- **DeepSeek-R1-1.5B**: Despite its small size, it offers GPT-4 level reasoning
- **DeepSeek-7B-Chat**: Larger variant for better quality (optional download)

### Why DeepSeek?

1. Superior reasoning capabilities for their size
2. Open source with commercial use allowed
3. Optimized for both English and Chinese
4. Excellent benchmark performance

## Troubleshooting

### Models Not Loading

```bash
# Check if models are downloaded
ls -la ~/Downloads/llm_models/

# Check service logs
docker logs sting-ce-llm-gateway-1

# Verify model service is running
./sting-model-manager.sh status
```

### Out of Memory Errors

```bash
# Switch to small models
./sting-model-manager.sh small

# Or limit memory usage
export TORCH_NUM_THREADS=2
docker compose restart
```

### Slow Response Times

1. Ensure you're using small models for development
2. Check available RAM: `free -h`
3. Consider using DialoGPT for fastest responses

## Performance Tips

### For Small Models
- Use `PERFORMANCE_PROFILE=vm_optimized`
- Enable response caching
- Use batch processing for multiple requests

### For Large Models
- Use GPU acceleration if available
- Increase Docker memory limits
- Use quantization: `export QUANTIZATION=int8`

## API Usage

The API remains the same regardless of model mode:

```bash
# Test with any model
curl -X POST http://localhost:8085/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "model": "deepseek-1.5b"}'
```

Available model names:
- Small: `deepseek-1.5b`, `tinyllama`, `dialogpt`
- Performance: `llama3`, `phi3`, `zephyr`

## Future Enhancements

- Auto-switching based on query complexity
- Model ensemble for best of both worlds
- Dynamic loading/unloading based on usage
- Support for GGUF quantized models