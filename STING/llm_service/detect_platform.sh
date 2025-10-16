#!/bin/bash

# Platform detection script for optimal LLM inference
# Detects available hardware and sets appropriate environment variables

echo "🔍 Detecting hardware platform for optimal LLM configuration..."

# Initialize default values
DEVICE="cpu"
DEVICE_TYPE="cpu"
QUANTIZATION="int8"
NUM_GPU=0
CPU_THREADS=$(nproc)
CUDA_VISIBLE_DEVICES=""

# Check for NVIDIA GPUs with CUDA
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,compute_capability.major --format=csv,noheader)
    if [ $? -eq 0 ] && [ -n "$GPU_INFO" ]; then
        echo "✅ NVIDIA GPU detected!"
        
        # Count available GPUs
        NUM_GPU=$(echo "$GPU_INFO" | wc -l)
        echo "   Found $NUM_GPU GPU(s)"
        
        # Get CUDA compute capability to determine appropriate quantization
        CC_MAJOR=$(echo "$GPU_INFO" | head -1 | awk -F', ' '{print $3}')
        GPU_MEM=$(echo "$GPU_INFO" | head -1 | awk -F', ' '{print $2}' | awk -F' ' '{print $1}')
        GPU_NAME=$(echo "$GPU_INFO" | head -1 | awk -F', ' '{print $1}')
        
        echo "   GPU: $GPU_NAME with ${GPU_MEM}MB memory"
        echo "   CUDA Compute Capability: $CC_MAJOR"
        
        # Set device type based on GPU capabilities
        DEVICE="cuda"
        DEVICE_TYPE="cuda"
        
        # Select quantization based on GPU memory and compute capability
        if [ "$CC_MAJOR" -ge 8 ] && [ "$GPU_MEM" -gt 16000 ]; then
            # High-end GPUs can use lower quantization for better quality
            QUANTIZATION="int4"
            echo "   Using int4 quantization (high-end GPU)"
        elif [ "$CC_MAJOR" -ge 7 ] && [ "$GPU_MEM" -gt 8000 ]; then
            # Mid-range GPUs
            QUANTIZATION="int8"
            echo "   Using int8 quantization (mid-range GPU)"
        else
            # Lower-end GPUs need higher quantization to fit models in memory
            QUANTIZATION="int8_float16"
            echo "   Using int8_float16 quantization (standard GPU)"
        fi
        
        # Set CUDA visible devices to all available GPUs
        CUDA_VISIBLE_DEVICES=$(seq -s "," 0 $((NUM_GPU-1)))
    fi
elif [ "$(uname)" = "Darwin" ] && [ "$(sysctl -n hw.optional.arm64)" = "1" ]; then
    # Apple Silicon (M1/M2/M3) with MPS support
    echo "✅ Apple Silicon detected, using MPS acceleration"
    DEVICE="mps"
    DEVICE_TYPE="mps"
    QUANTIZATION="int8"  # MPS generally works well with int8
else
    # CPU fallback
    echo "✅ Using CPU for inference"
    
    # Optimize based on available CPU cores
    if [ "$CPU_THREADS" -ge 16 ]; then
        echo "   High-core CPU detected ($CPU_THREADS cores)"
        QUANTIZATION="int8"
    else
        echo "   Standard CPU detected ($CPU_THREADS cores)"
        QUANTIZATION="int8_float16"  # Lower precision to improve speed on fewer cores
    fi
fi

# Set environment variables
export DEVICE=$DEVICE
export DEVICE_TYPE=$DEVICE_TYPE
export QUANTIZATION=$QUANTIZATION
export NUM_GPU=$NUM_GPU
export CPU_THREADS=$CPU_THREADS
export CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

# Print configuration summary
echo "📊 LLM Configuration:"
echo "   Device: $DEVICE"
echo "   Device Type: $DEVICE_TYPE"
echo "   Quantization: $QUANTIZATION"
echo "   GPU Count: $NUM_GPU"
echo "   CPU Threads: $CPU_THREADS"
echo "   CUDA Devices: $CUDA_VISIBLE_DEVICES"

# Launch the command passed to the script
echo "🚀 Launching model server with optimal settings..."
exec "$@"

