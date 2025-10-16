# STING Performance Administration Guide

## 🎯 Overview

STING includes intelligent performance optimization that automatically adapts to different deployment environments, from virtual machines to GPU-accelerated hardware. This guide helps administrators configure, monitor, and optimize STING performance for their specific deployment scenario.

## 📊 Performance Profiles

### Available Profiles

| Profile | Use Case | Quantization | Memory Usage | Response Time | Best For |
|---------|----------|--------------|--------------|---------------|----------|
| `auto` | Auto-detect | Dynamic | Dynamic | Dynamic | General deployment |
| `vm_optimized` | Virtual Machines | int8 | ~6GB | 5-15s | VirtualBox, VMware |
| `gpu_accelerated` | GPU/NPU Hardware | none | ~18GB | 2-5s | Native deployment |
| `cloud` | Cloud Deployment | none | ~20GB | 1-3s | AWS, Azure, GCP |

### Profile Details

#### `vm_optimized` (Recommended for Virtual Appliances)
- **Quantization**: int8 (75% memory reduction)
- **Model Size**: ~4GB (down from ~16GB)
- **CPU Threads**: Auto-detected (uses all available cores - 1)
- **Batch Size**: 1 (optimized for single requests)
- **Max Tokens**: 512 (faster responses)
- **Best For**: VirtualBox, VMware, Hyper-V, any CPU-only environment

#### `gpu_accelerated` 
- **Quantization**: none (full precision)
- **Model Size**: ~16GB
- **Precision**: fp16 on GPU, fp32 on CPU
- **Batch Size**: 4 (can handle multiple requests)
- **Max Tokens**: 2048
- **Best For**: Native deployment with NVIDIA CUDA, Apple MPS, AMD ROCm

#### `cloud`
- **Quantization**: none
- **Model Size**: ~16GB 
- **Batch Size**: 8 (high throughput)
- **Max Tokens**: 4096 (long responses)
- **Best For**: AWS p3/p4, Azure NCv3, GCP with GPU

## 🔧 Configuration

### Environment Variables

Add to your `.env` file or environment:

```bash
# Core Performance Settings
PERFORMANCE_PROFILE=vm_optimized    # Choose: auto, vm_optimized, gpu_accelerated, cloud

# CPU Threading (set to "auto" for automatic detection)
OMP_NUM_THREADS=auto               # OpenMP threads
MKL_NUM_THREADS=auto               # Intel Math Kernel Library
TORCH_NUM_THREADS=auto             # PyTorch threads

# Manual Overrides (optional)
TORCH_DEVICE=auto                  # Force device: auto, cpu, cuda, mps
TORCH_PRECISION=fp32               # Force precision: fp32, fp16, bf16  
QUANTIZATION=int8                  # Force quantization: none, int8, int4
```

### Docker Compose Deployment

For production deployment, add to your `docker-compose.yml`:

```yaml
services:
  llm-gateway:
    environment:
      - PERFORMANCE_PROFILE=vm_optimized
      - OMP_NUM_THREADS=auto
      - MKL_NUM_THREADS=auto
      - TORCH_NUM_THREADS=auto
      - TOKENIZERS_PARALLELISM=true
    deploy:
      resources:
        limits:
          memory: 8G          # For vm_optimized
          cpus: '0'           # Use all available CPUs
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sting-llm-gateway
spec:
  template:
    spec:
      containers:
      - name: llm-gateway
        env:
        - name: PERFORMANCE_PROFILE
          value: "vm_optimized"
        - name: OMP_NUM_THREADS
          value: "auto"
        resources:
          limits:
            memory: "8Gi"
            cpu: "4"
          requests:
            memory: "6Gi" 
            cpu: "2"
```

## 🧪 Performance Testing

### Built-in Testing Script

STING includes a performance testing script:

```bash
# Run comprehensive performance tests
./test_performance.sh

# Test specific profile
PERFORMANCE_PROFILE=vm_optimized ./test_performance.sh
```

### Manual Testing

#### Quick Health Check
```bash
curl http://localhost:8085/health
```

Expected response:
```json
{
  "status": "healthy",
  "model": "llama3", 
  "device": "cpu",
  "uptime": 123.45
}
```

#### Performance Test
```bash
# Test chatbot response time
time curl -X POST http://localhost:8081/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test"}'
```

#### Load Testing with Apache Bench
```bash
# Test 10 concurrent requests
ab -n 10 -c 2 -T 'application/json' \
  -p test_payload.json \
  http://localhost:8081/chat/message
```

Where `test_payload.json` contains:
```json
{"message": "Test message", "user_id": "load_test"}
```

## 📈 Monitoring & Optimization

### Key Metrics to Monitor

1. **Response Time**: Target < 15s for vm_optimized, < 5s for gpu_accelerated
2. **Memory Usage**: Monitor via `docker stats` or system monitoring
3. **CPU Utilization**: Should use most available cores during inference
4. **Error Rate**: Monitor for timeouts or OOM errors

### Monitoring Commands

```bash
# Monitor Docker resource usage
docker stats sting-llm-gateway-1

# Check service logs
docker compose logs llm-gateway --tail=50

# Monitor CPU threads
docker compose exec llm-gateway python -c "
import torch, os
print(f'PyTorch threads: {torch.get_num_threads()}')
print(f'OMP threads: {os.environ.get(\"OMP_NUM_THREADS\", \"not set\")}')
"

# Check quantization status
docker compose logs llm-gateway | grep -i quantization
```

### Performance Tuning

#### For Virtual Machines
```bash
# Optimize for VMs
export PERFORMANCE_PROFILE=vm_optimized
export OMP_NUM_THREADS=auto
export QUANTIZATION=int8

# For very limited memory (< 6GB)
export QUANTIZATION=int4  # Further reduces memory usage
```

#### For GPU Systems
```bash
# Optimize for GPU
export PERFORMANCE_PROFILE=gpu_accelerated  
export TORCH_DEVICE=auto
export QUANTIZATION=none
export TORCH_PRECISION=fp16
```

#### For High-Memory Systems
```bash
# Optimize for cloud/high-end hardware
export PERFORMANCE_PROFILE=cloud
export QUANTIZATION=none
export TORCH_PRECISION=fp16  # or bf16 for newer hardware
```

## 🚨 Troubleshooting

### Common Issues

#### Slow Response Times
```bash
# Check current profile
docker compose exec llm-gateway env | grep PERFORMANCE_PROFILE

# Switch to VM optimized
PERFORMANCE_PROFILE=vm_optimized docker compose restart llm-gateway
```

#### Out of Memory Errors
```bash
# Enable aggressive quantization
QUANTIZATION=int4 docker compose restart llm-gateway

# Or reduce model size
MODEL_NAME=phi3 docker compose restart llm-gateway  # Smaller model
```

#### CPU Underutilization
```bash
# Check thread configuration
docker compose exec llm-gateway python -c "
import multiprocessing, torch, os
print(f'Available CPUs: {multiprocessing.cpu_count()}')
print(f'PyTorch threads: {torch.get_num_threads()}')
print(f'OMP_NUM_THREADS: {os.environ.get(\"OMP_NUM_THREADS\")}')
"

# Force thread count
OMP_NUM_THREADS=8 docker compose restart llm-gateway
```

#### GPU Not Detected
```bash
# Check GPU availability in container
docker compose exec llm-gateway python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'MPS available: {torch.backends.mps.is_available()}')
print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')
"

# Note: MPS (Apple Silicon) requires native deployment, not Docker
```

### Log Analysis

#### Check Performance Settings Application
```bash
# Look for these log entries
docker compose logs llm-gateway | grep -E "(performance profile|quantization|device|threads)"
```

Expected logs:
```
INFO:__main__:Using performance profile: vm_optimized
INFO:__main__:Using 8-bit quantization for balanced VM performance  
INFO:__main__:CPU optimization: OMP_NUM_THREADS=7, TORCH_NUM_THREADS=7
INFO:__main__:Using device: cpu
```

#### Performance Benchmarking
```bash
# Enable detailed timing logs
LOG_LEVEL=DEBUG docker compose restart llm-gateway

# Monitor request processing time
docker compose logs -f llm-gateway | grep -E "(request|response|time)"
```

## 🔄 Profile Migration

### Switching Profiles

#### Development to Production
```bash
# Development (fast startup, good for testing)
PERFORMANCE_PROFILE=vm_optimized

# Production (better quality, requires more resources)  
PERFORMANCE_PROFILE=gpu_accelerated
```

#### VM to Native Deployment
```bash
# Stop Docker LLM services
docker compose down llm-gateway llama3-service phi3-service zephyr-service

# Run natively for GPU acceleration
cd llm_service
PERFORMANCE_PROFILE=gpu_accelerated \
TORCH_DEVICE=auto \
python server.py
```

## 📊 Performance Expectations

### Virtual Machine Deployment (vm_optimized)
- **Startup Time**: 30-60 seconds
- **First Response**: 10-20 seconds (model loading)
- **Subsequent Responses**: 5-15 seconds
- **Memory Usage**: 6-8 GB
- **CPU Usage**: 80-100% during inference

### GPU Deployment (gpu_accelerated)  
- **Startup Time**: 60-120 seconds
- **First Response**: 5-10 seconds
- **Subsequent Responses**: 2-5 seconds
- **Memory Usage**: 18-20 GB
- **GPU Usage**: 60-90% during inference

## 🎛️ Advanced Configuration

### Custom Performance Profiles

You can create custom profiles by modifying `conf/config.yml`:

```yaml
llm_service:
  performance:
    custom_profile:
      quantization: "int8"
      cpu_threads: 6
      batch_size: 2
      max_tokens: 1024
      precision: "fp32"
```

### Environment-Specific Optimization

#### Docker Swarm
```yaml
version: '3.8'
services:
  llm-gateway:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 8G
      placement:
        constraints:
          - node.labels.gpu==true  # For GPU nodes
```

#### Kubernetes with GPU
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: 20Gi
  requests:
    nvidia.com/gpu: 1
    memory: 16Gi
```

## 📞 Support

### Getting Help

1. **Check logs**: Always start with `docker compose logs llm-gateway`
2. **Run health check**: `curl http://localhost:8085/health`
3. **Test performance**: `./test_performance.sh`
4. **Monitor resources**: `docker stats`

### Reporting Performance Issues

Include in your report:
- Current performance profile (`echo $PERFORMANCE_PROFILE`)
- System specifications (CPU, RAM, GPU)
- Deployment method (Docker, Kubernetes, native)
- Logs from `docker compose logs llm-gateway`
- Output from health check endpoint

---

**📧 For additional support, refer to the main STING documentation or submit an issue with performance logs and system specifications.**