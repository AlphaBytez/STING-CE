# Hardware Acceleration Guide for STING-CE

## Overview

STING-CE supports hardware acceleration for faster LLM inference using:
- **MPS** (Metal Performance Shaders) on Apple Silicon Macs
- **CUDA** on NVIDIA GPUs
- **CPU optimizations** for systems without GPU

## Current Status

### Docker Limitations

Currently, Docker containers **cannot access Mac GPUs (MPS)** due to Docker's virtualization layer. The LLM service will fall back to CPU when running in Docker.

### Native Execution for Mac GPU

To use Apple Silicon GPU acceleration, run the LLM service natively:

```bash
# Use the provided script
./run_native_mps.sh

# Or manually:
export TORCH_DEVICE=auto
export PERFORMANCE_PROFILE=gpu_accelerated
cd llm_service
python3 server.py
```

## Performance Comparison

| Configuration | Load Time | Inference Speed | Memory Usage |
|--------------|-----------|-----------------|--------------|
| CPU (Docker) | ~2.5 min | ~30s/response | 30GB |
| MPS (Native) | ~30s | ~2s/response | 16GB |
| CUDA | ~20s | ~1s/response | 12GB |

## Setup Instructions

### 1. Apple Silicon Mac (M1/M2/M3)

**Requirements:**
- macOS 12.0+
- Python 3.9+
- PyTorch 2.0+ with MPS support

**Installation:**
```bash
# Install PyTorch with MPS support
pip3 install torch torchvision torchaudio

# Verify MPS availability
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

**Running:**
```bash
# Stop Docker LLM service
docker compose stop llm-gateway

# Run native service
./run_native_mps.sh
```

### 2. NVIDIA GPU (Linux/Windows)

**Requirements:**
- CUDA 11.8+
- NVIDIA Driver 450+
- nvidia-docker2

**Docker Configuration:**
```yaml
llm-gateway:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 3. CPU Optimization

For systems without GPU, optimize CPU performance:

```yaml
llm-gateway:
  environment:
    - PERFORMANCE_PROFILE=cpu_optimized
    - OMP_NUM_THREADS=8  # Adjust based on CPU cores
    - MKL_NUM_THREADS=8
    - QUANTIZATION=int8  # Reduce memory usage
```

## Troubleshooting

### MPS Not Detected

1. Check PyTorch version:
```bash
pip3 show torch | grep Version
# Should be 2.0+
```

2. Verify MPS support:
```python
import torch
print(torch.backends.mps.is_available())
print(torch.backends.mps.is_built())
```

3. Update PyTorch:
```bash
pip3 install --upgrade torch torchvision
```

### High Memory Usage

1. Enable quantization:
```bash
export QUANTIZATION=int8
```

2. Use smaller models:
```bash
export MODEL_NAME=phi3  # 3.8B params
```

3. Reduce batch size:
```bash
export BATCH_SIZE=1
```

### Slow Inference

1. Check device usage:
```python
# In server.py logs
INFO:__main__:Using device: mps  # Good
INFO:__main__:Using device: cpu  # Slow
```

2. Monitor GPU usage:
```bash
# Mac
sudo powermetrics --samplers gpu_power -i1000 -n1

# NVIDIA
nvidia-smi
```

## Best Practices

1. **Development**: Use Docker with CPU for consistency
2. **Production**: Use native GPU execution for performance
3. **Testing**: Profile both configurations
4. **Monitoring**: Track GPU memory and utilization

## Future Improvements

1. **Docker GPU Support**: Waiting for Docker Desktop MPS passthrough
2. **Multi-GPU**: Support for multiple GPUs
3. **Mixed Precision**: FP16/BF16 for faster inference
4. **Dynamic Batching**: Better throughput for multiple users

## Performance Optimization Tips

### For MPS (Apple Silicon)

```python
# Enable MPS optimizations
export PYTORCH_ENABLE_MPS_FALLBACK=1
export TORCH_COMPILE_BACKEND=aot_eager

# Use appropriate precision
export TORCH_PRECISION=fp16  # Faster on MPS
```

### For CPU

```python
# Enable all CPU optimizations
export OMP_NUM_THREADS=$(sysctl -n hw.ncpu)
export MKL_NUM_THREADS=$(sysctl -n hw.ncpu)
export NUMEXPR_MAX_THREADS=$(sysctl -n hw.ncpu)
```

### Memory Management

```python
# Reduce memory fragmentation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Enable memory efficient attention
export TORCH_CUDNN_V8_API_ENABLED=1
```