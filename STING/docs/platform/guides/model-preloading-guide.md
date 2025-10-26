# Model Preloading Guide for STING-CE

## Overview

STING-CE now supports model preloading to ensure fast response times for users. This guide explains the configuration and best practices.

## Why Preload Models?

Loading large language models (8B+ parameters) can take several minutes on CPU:
- Llama 3 8B: ~2.5 minutes on CPU
- Without preloading: First user waits 2.5+ minutes
- With preloading: All users get instant responses

## Configuration

### 1. Automatic Preloading (Default)

The LLM gateway now preloads models during startup:

```python
# In llm_service/server.py
@app.on_event("startup")
async def startup_event():
    # ... initialization ...
    logger.info("Preloading model to ensure fast response times...")
    load_model_if_needed()
    logger.info("Model preloaded and ready for requests")
```

### 2. Health Check Configuration

The docker-compose.yml is configured to allow sufficient time for model loading:

```yaml
llm-gateway:
  healthcheck:
    start_period: 300s  # 5 minutes for model loading
    interval: 30s
    timeout: 10s
    retries: 10
```

### 3. Performance Profiles

Choose the right profile for your hardware:

- **cpu_optimized**: No quantization, full precision (best quality, slower)
- **vm_optimized**: INT8 quantization (balanced quality/speed) 
- **gpu_accelerated**: Full precision with GPU support

Set via environment variable:
```bash
PERFORMANCE_PROFILE=cpu_optimized
```

## Best Practices

### 1. Resource Allocation

Ensure sufficient resources:
- **RAM**: At least 16GB for 8B models
- **CPU**: Multi-core processor recommended
- **Storage**: 20GB+ for model files

### 2. Model Selection

For faster loading on limited hardware:
- Use smaller models (Phi-3, TinyLlama)
- Enable quantization for larger models
- Consider GPU acceleration if available

### 3. Multi-Stage Deployment

For production environments:

```yaml
# Stage 1: Download models
llm-base:
  build:
    context: ./llm_service
    dockerfile: Dockerfile.llm-base
  # Downloads and caches models

# Stage 2: Run gateway with preloading
llm-gateway:
  depends_on:
    - llm-base
  # Models already downloaded, just load into memory
```

### 4. Monitoring

Check model loading status:

```bash
# View startup logs
docker logs sting-llm-gateway-1

# Check health
curl http://localhost:8085/health

# Monitor memory usage
docker stats sting-llm-gateway-1
```

## Troubleshooting

### Model Loading Times Out

If models fail to load within 5 minutes:

1. Increase start_period in healthcheck
2. Check available memory
3. Consider using quantization
4. Use smaller models

### Out of Memory Errors

1. Reduce model size with quantization:
   ```bash
   QUANTIZATION=int8
   ```

2. Increase Docker memory limits:
   ```yaml
   mem_limit: 16G
   ```

3. Use swap space as last resort

### Slow Response Times

1. Enable CPU optimization:
   ```bash
   OMP_NUM_THREADS=8
   TORCH_NUM_THREADS=8
   ```

2. Use performance profiling:
   ```bash
   TORCH_PROFILER_ENABLED=1
   ```

## Future Improvements

1. **Model Warm-up**: Run sample queries during startup
2. **Progressive Loading**: Load models in background while serving
3. **Model Caching**: Keep frequently used models in memory
4. **Auto-scaling**: Scale based on request patterns

## Example Configuration

Optimal configuration for production:

```yaml
llm-gateway:
  environment:
    - PERFORMANCE_PROFILE=cpu_optimized
    - QUANTIZATION=none
    - MODEL_PRELOAD=true
    - OMP_NUM_THREADS=auto
    - TORCH_NUM_THREADS=auto
  healthcheck:
    start_period: 300s
    interval: 30s
    retries: 10
  deploy:
    resources:
      limits:
        memory: 16G
      reservations:
        memory: 12G
```

This ensures models are preloaded, health checks allow sufficient time, and resources are properly allocated.