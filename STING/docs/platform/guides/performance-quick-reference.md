# STING Performance Quick Reference

## ⚡ Quick Start Commands

### Set Performance Profile
```bash
# For Virtual Machines (Recommended)
echo "PERFORMANCE_PROFILE=vm_optimized" >> .env
docker compose restart llm-gateway

# For GPU Hardware  
echo "PERFORMANCE_PROFILE=gpu_accelerated" >> .env
docker compose restart llm-gateway

# Auto-detect (Default)
echo "PERFORMANCE_PROFILE=auto" >> .env
docker compose restart llm-gateway
```

### Test Performance
```bash
# Run built-in performance test
./test_performance.sh

# Quick health check
curl http://localhost:8085/health

# Quick chat test
curl -X POST http://localhost:8081/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test"}'
```

### Monitor Performance
```bash
# Monitor resource usage
docker stats sting-llm-gateway-1

# Check logs
docker compose logs llm-gateway --tail=20

# Check configuration
docker compose exec llm-gateway env | grep -E "(PERFORMANCE|TORCH|OMP)"
```

## 🎯 Performance Profiles Cheat Sheet

| Scenario | Profile | Command |
|----------|---------|---------|
| **Virtual Machine** | `vm_optimized` | `PERFORMANCE_PROFILE=vm_optimized` |
| **Docker Desktop** | `vm_optimized` | `PERFORMANCE_PROFILE=vm_optimized` |
| **Native Apple Silicon** | `gpu_accelerated` | `PERFORMANCE_PROFILE=gpu_accelerated` |
| **Native NVIDIA GPU** | `gpu_accelerated` | `PERFORMANCE_PROFILE=gpu_accelerated` |
| **AWS/Azure/GCP** | `cloud` | `PERFORMANCE_PROFILE=cloud` |
| **Unsure** | `auto` | `PERFORMANCE_PROFILE=auto` |

## 🔧 Common Fixes

### Slow Performance
```bash
# Switch to VM optimized
PERFORMANCE_PROFILE=vm_optimized docker compose restart llm-gateway

# Enable quantization
QUANTIZATION=int8 docker compose restart llm-gateway
```

### Out of Memory
```bash
# Use aggressive quantization
QUANTIZATION=int4 docker compose restart llm-gateway

# Use smaller model
MODEL_NAME=phi3 docker compose restart llm-gateway
```

### CPU Underutilized
```bash
# Force all CPU cores
OMP_NUM_THREADS=auto docker compose restart llm-gateway

# Check current threading
docker compose exec llm-gateway python -c "import torch; print(f'Threads: {torch.get_num_threads()}')"
```

## 📊 Expected Performance

| Profile | Memory | Response Time | Quality |
|---------|--------|---------------|---------|
| `vm_optimized` | 6-8 GB | 5-15 seconds | Good |
| `gpu_accelerated` | 16-20 GB | 2-5 seconds | Excellent |
| `cloud` | 18-24 GB | 1-3 seconds | Excellent |

## 🚨 Troubleshooting

### Check Current Settings
```bash
# View current profile
echo $PERFORMANCE_PROFILE

# Check environment in container
docker compose exec llm-gateway env | grep PERFORMANCE_PROFILE

# View applied settings in logs
docker compose logs llm-gateway | grep -i "performance profile"
```

### Reset to Defaults
```bash
# Remove custom settings
unset PERFORMANCE_PROFILE
unset QUANTIZATION
unset TORCH_DEVICE

# Restart with auto-detection
PERFORMANCE_PROFILE=auto docker compose restart llm-gateway
```

### Emergency Recovery
```bash
# If services won't start
docker compose down
docker compose up -d db vault kratos app frontend

# Start with minimal LLM
PERFORMANCE_PROFILE=vm_optimized \
QUANTIZATION=int4 \
docker compose up -d llm-gateway
```

## 📁 Files to Check

- **Configuration**: `conf/config.yml`
- **Environment**: `.env` 
- **Performance settings**: `.env.performance`
- **Logs**: `docker compose logs llm-gateway`
- **Test script**: `./test_performance.sh`

## 🎛️ Advanced Tweaking

### For Virtual Appliances
```bash
export PERFORMANCE_PROFILE=vm_optimized
export QUANTIZATION=int8
export OMP_NUM_THREADS=auto
export MAX_TOKENS=512  # Shorter responses = faster
```

### For High-End Hardware
```bash
export PERFORMANCE_PROFILE=gpu_accelerated
export QUANTIZATION=none
export TORCH_PRECISION=fp16
export MAX_TOKENS=2048
```

### For Development
```bash
export PERFORMANCE_PROFILE=vm_optimized
export QUANTIZATION=int8
export MAX_TOKENS=256  # Very fast responses for testing
```

---
💡 **Tip**: Always test changes with `./test_performance.sh` before deploying to production!