import os
import logging
import torch
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import uvicorn
import traceback
import re
from utils.knowledge_base_loader import get_sting_system_prompt
from utils.model_lifecycle_manager import get_lifecycle_manager
from utils.task_router import get_task_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/TinyLlama-1.1B-Chat")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "auto")  # cuda, mps, cpu, or auto
TORCH_DEVICE = os.environ.get("TORCH_DEVICE", "auto")  # New: auto-detect best device
TORCH_PRECISION = os.environ.get("TORCH_PRECISION", "fp32")  # fp32, fp16, bf16
MODEL_NAME = os.environ.get("MODEL_NAME", "tinyllama")
QUANTIZATION = os.environ.get("QUANTIZATION", "none")  # int8, int4, or none
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "4096"))
PERFORMANCE_PROFILE = os.environ.get("PERFORMANCE_PROFILE", "auto")  # auto, vm_optimized, gpu_accelerated, cloud

# Performance settings
OMP_NUM_THREADS = os.environ.get("OMP_NUM_THREADS", "auto")
TORCH_NUM_THREADS = os.environ.get("TORCH_NUM_THREADS", "auto")

app = FastAPI(title="STING LLM Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Message format
class Message(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None
    
class ChatResponse(BaseModel):
    model: str
    response: str
    usage: Dict[str, int]

# Global lifecycle manager and task router
lifecycle_manager = None
task_router = None

def filter_thinking_tags(text):
    """Remove DeepSeek thinking tags for cleaner enterprise output"""
    # First, try to remove complete think blocks
    if "<think>" in text and "</think>" in text:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Also handle cases where we have partial tags or the content before </think>
    # This catches cases where the model starts thinking without the opening tag
    if "</think>" in text:
        # Find everything up to and including </think>
        text = re.sub(r'^.*?</think>\s*', '', text, flags=re.DOTALL)
    
    # Remove any orphaned <think> tags
    text = text.replace("<think>", "")
    
    # Clean up any extra whitespace or newlines
    text = text.strip()
    return text

def get_best_device():
    """Auto-detect the best available device with cross-platform support"""
    if TORCH_DEVICE != "auto" and DEVICE_TYPE != "auto":
        # Use explicit device if set
        return TORCH_DEVICE if TORCH_DEVICE != "auto" else DEVICE_TYPE
    
    # Auto-detection priority: MPS > CUDA > CPU
    if torch.backends.mps.is_available():
        logger.info("🚀 MPS (Metal Performance Shaders) detected - Using Mac GPU acceleration!")
        logger.info(f"   MPS built: {torch.backends.mps.is_built()}")
        logger.info(f"   Platform: macOS on Apple Silicon")
        return "mps"
    elif torch.cuda.is_available():
        logger.info("🚀 CUDA detected - Using NVIDIA GPU acceleration!")
        logger.info(f"   CUDA version: {torch.version.cuda}")
        logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
        return "cuda"
    else:
        logger.info("💻 Using CPU (no GPU acceleration available)")
        logger.info(f"   CPU threads: {torch.get_num_threads()}")
        return "cpu"

def get_torch_dtype():
    """Get the appropriate torch dtype based on precision setting"""
    precision = TORCH_PRECISION.lower()
    
    if precision == "fp16":
        return torch.float16
    elif precision == "bf16":
        return torch.bfloat16
    else:  # fp32 or default
        return torch.float32

def get_performance_settings():
    """Get optimized settings based on performance profile and detected hardware"""
    device = get_best_device()
    
    # Auto-detect best profile if set to auto
    if PERFORMANCE_PROFILE == "auto":
        if device == "cpu":
            profile = "vm_optimized"
        elif device in ["cuda", "mps"]:
            profile = "gpu_accelerated"
        else:
            profile = "vm_optimized"
    else:
        profile = PERFORMANCE_PROFILE
    
    # Define performance profiles
    profiles = {
        "vm_optimized": {
            "quantization": "int8",
            "max_tokens": 512,
            "batch_size": 1,
            "precision": "fp32",
            "cpu_threads": "auto"
        },
        "cpu_optimized": {
            "quantization": "none",
            "max_tokens": 1024,
            "batch_size": 1,
            "precision": "fp32",
            "cpu_threads": "auto"
        },
        "gpu_accelerated": {
            "quantization": "none",
            "max_tokens": 2048,
            "batch_size": 4,
            "precision": "fp16" if device != "cpu" else "fp32",
            "cpu_threads": 4
        },
        "cloud": {
            "quantization": "none", 
            "max_tokens": 4096,
            "batch_size": 8,
            "precision": "fp16" if device != "cpu" else "fp32",
            "cpu_threads": 2
        }
    }
    
    settings = profiles.get(profile, profiles["vm_optimized"])
    logger.info(f"Using performance profile: {profile} with settings: {settings}")
    
    return profile, settings

def optimize_cpu_threading():
    """Optimize CPU threading based on hardware and performance profile"""
    import os
    import multiprocessing
    
    cpu_count = multiprocessing.cpu_count()
    
    # Set threading based on profile
    if OMP_NUM_THREADS == "auto":
        # Use most CPUs for VM deployment, fewer for GPU deployment
        if PERFORMANCE_PROFILE == "vm_optimized":
            threads = max(1, cpu_count - 1)  # Leave one core for system
        else:
            threads = max(1, cpu_count // 2)  # Use half for other profiles
            
        os.environ["OMP_NUM_THREADS"] = str(threads)
        
    if TORCH_NUM_THREADS == "auto":
        threads = int(os.environ.get("OMP_NUM_THREADS", cpu_count // 2))
        torch.set_num_threads(threads)
        
    logger.info(f"CPU optimization: OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')}, "
                f"TORCH_NUM_THREADS={torch.get_num_threads()}")

# We'll get the appropriate prompt dynamically based on the model being used
def get_model_system_prompt(model_name: str) -> str:
    """Get appropriate STING system prompt based on model size"""
    model_size = 'small' if 'tiny' in model_name.lower() or 'phi2' in model_name.lower() else 'large'
    return get_sting_system_prompt(model_size=model_size)

# Define Llama 3 chat template (we'll insert STING prompt dynamically)
LLAMA_3_CHAT_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ system_prompt | default('You are a helpful AI assistant.') }}<|eot_id|>

{% for message in messages %}
<|start_header_id|>{{ message["role"] }}<|end_header_id|>

{{ message["content"] }}<|eot_id|>
{% endfor %}

<|start_header_id|>assistant<|end_header_id|>

"""

# Load lifecycle manager on startup
@app.on_event("startup")
async def startup_event():
    global lifecycle_manager, task_router
    
    logger.info(f"Starting LLM service with dynamic model loading")
    logger.info(f"Default model: {MODEL_NAME}, Path: {MODEL_PATH}")
    
    try:
        start_time = time.time()
        
        # Optimize CPU threading first
        optimize_cpu_threading()
        
        # Initialize lifecycle manager
        lifecycle_manager = get_lifecycle_manager()
        logger.info("Initialized model lifecycle manager")
        
        # Initialize task router
        task_router = get_task_router()
        logger.info("Initialized task router")
        
        # Get performance settings
        profile, perf_settings = get_performance_settings()
        logger.info(f"Performance profile: {profile}")
        
        # Log lifecycle configuration
        lazy_loading = os.getenv('LLM_LAZY_LOADING', 'true').lower() == 'true'
        preload = os.getenv('LLM_PRELOAD_ON_STARTUP', 'false').lower() == 'true'
        dev_mode = os.getenv('LLM_DEVELOPMENT_MODE', 'false').lower() == 'true'
        idle_timeout = int(os.getenv('LLM_IDLE_TIMEOUT', '30'))
        
        logger.info(f"Lifecycle settings: lazy_loading={lazy_loading}, preload={preload}, "
                   f"dev_mode={dev_mode}, idle_timeout={idle_timeout}min")
        
        # If preload is enabled or we're not using lazy loading, load the default model
        if preload or not lazy_loading:
            logger.info(f"Preloading default model: {MODEL_NAME}")
            device = get_best_device()
            dtype = get_torch_dtype()
            lifecycle_manager.get_model(MODEL_NAME, device, dtype)
            logger.info("Default model preloaded and ready")
        else:
            logger.info("Lazy loading enabled - models will be loaded on first request")
        
        load_time = time.time() - start_time
        logger.info(f"Startup completed in {load_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Failed during startup: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown - unload all models"""
    global lifecycle_manager
    if lifecycle_manager:
        lifecycle_manager.shutdown()
        logger.info("Lifecycle manager shutdown complete")

@app.get("/health")
def health_check():
    loaded_models = lifecycle_manager.get_loaded_models() if lifecycle_manager else {}
    return {
        "status": "healthy",
        "default_model": MODEL_NAME,
        "loaded_models": loaded_models,
        "uptime": time.time() - startup_time
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Extract user message for task routing
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        # Convert messages to dict format for routing
        conversation_history = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Get available models from lifecycle manager
        available_models = list(lifecycle_manager.models.keys()) if lifecycle_manager else []
        
        # Route to appropriate model
        routing_decision = task_router.route_request(
            message=user_message,
            conversation_history=conversation_history,
            requested_model=request.model,
            available_models=available_models
        )
        
        model_name = routing_decision['model']
        logger.info(f"Task routing: {routing_decision['task_type']} -> {model_name} ({routing_decision['reason']})")
        
        # Get model from lifecycle manager
        device = get_best_device()
        dtype = get_torch_dtype()
        model, tokenizer = lifecycle_manager.get_model(model_name, device, dtype)
        
        # Prepare the input
        messages = request.messages
        
        # Prepare system prompt if provided
        if request.system_prompt:
            messages = [Message(role="system", content=request.system_prompt)] + messages
            
        # Format conversation for the model
        conversation = []
        for msg in messages:
            if msg.role == "user":
                conversation.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                conversation.append({"role": "assistant", "content": msg.content})
            elif msg.role == "system":
                conversation.append({"role": "system", "content": msg.content})
        
        # Check if conversation is empty and provide default
        if not conversation:
            conversation = [{"role": "user", "content": "Hello"}]
        
        # Generate response using chat template with generation prompt
        input_tokens = tokenizer.apply_chat_template(
            conversation, 
            return_tensors="pt",
            add_generation_prompt=True
        )
        
        # Move tensors to the same device as the model
        model_device = next(model.parameters()).device
        input_tokens = input_tokens.to(model_device)
            
        # Create attention mask on the same device
        attention_mask = torch.ones_like(input_tokens).to(model_device)
        
        # Set pad token if needed
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        with torch.no_grad():
            # Check if this is a Phi-3 model and apply cache fix
            model_config = getattr(model, 'config', None)
            model_type = getattr(model_config, 'model_type', '').lower()
            
            generation_kwargs = {
                'input_ids': input_tokens,
                'attention_mask': attention_mask,
                'max_new_tokens': request.max_tokens,  # Use max_new_tokens instead of max_length
                'do_sample': True,
                'temperature': request.temperature,
                'pad_token_id': tokenizer.pad_token_id,
                'return_dict_in_generate': True,
                'output_scores': False,  # Don't store scores to save memory
                'output_hidden_states': False,
                'output_attentions': False,
            }
            
            # Apply Phi-3 specific fixes
            if 'phi' in model_type or 'phi3' in model_name.lower():
                logger.info("Applying Phi-3 cache optimizations...")
                
                # Remove problematic cache parameter and use default cache
                generation_kwargs.update({
                    'use_cache': False,  # Disable cache entirely to avoid dynamic cache issues
                })
                
                # Clear any existing cache
                if hasattr(model, 'clear_cache'):
                    model.clear_cache()
                    
                # Force garbage collection to prevent memory issues
                import gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    # Clear MPS cache if available
                    torch.mps.empty_cache()
            
            outputs = model.generate(**generation_kwargs)
        
        # Decode the response (handle both dict and tensor outputs)
        if hasattr(outputs, 'sequences'):
            # Dict output from return_dict_in_generate=True
            generated_tokens = outputs.sequences[0][input_tokens.shape[1]:]
            output_token_count = len(generated_tokens)
        else:
            # Tensor output
            generated_tokens = outputs[0][input_tokens.shape[1]:]
            output_token_count = outputs.shape[1] - input_tokens.shape[1]
            
        response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        response_text = filter_thinking_tags(response_text)
        
        # Count tokens
        input_token_count = input_tokens.shape[1]
        
        return {
            "model": model_name,  # Return the actual model used
            "response": response_text,
            "usage": {
                "prompt_tokens": input_token_count,
                "completion_tokens": output_token_count,
                "total_tokens": input_token_count + output_token_count
            }
        }
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

@app.post("/generate")
async def generate_endpoint(request: Request):
    try:
        # Parse request body
        body = await request.json()
        requested_model = body.get("model")
        
        # Extract message for task routing
        user_message = ""
        if "message" in body:
            user_message = body["message"]
        elif "messages" in body:
            # Find last user message
            for msg in reversed(body.get("messages", [])):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
        
        # Get available models
        available_models = list(lifecycle_manager.models.keys()) if lifecycle_manager else []
        
        # Route to appropriate model
        routing_decision = task_router.route_request(
            message=user_message,
            requested_model=requested_model,
            available_models=available_models
        )
        
        model_name = routing_decision['model']
        logger.info(f"Task routing: {routing_decision['task_type']} -> {model_name} ({routing_decision['reason']})")
        
        # Get model from lifecycle manager
        device = get_best_device()
        dtype = get_torch_dtype()
        model, tokenizer = lifecycle_manager.get_model(model_name, device, dtype)
        
        max_tokens = body.get("max_tokens", 2048)
        temperature = body.get("temperature", 0.7)
        
        # Get appropriate system prompt for this model
        model_system_prompt = get_model_system_prompt(model_name)
        
        # Support both "message" (chatbot format) and "messages" (chat format)
        if "message" in body:
            # Single message format from chatbot
            message_content = body["message"]
            # Always include STING system prompt for single messages
            conversation = [
                {"role": "system", "content": model_system_prompt},
                {"role": "user", "content": message_content}
            ]
        else:
            # Messages array format
            messages = body.get("messages", [])
            conversation = []
            
            # Add STING system prompt if no system message exists
            has_system = any(msg.get("role") == "system" for msg in messages)
            if not has_system:
                conversation.append({"role": "system", "content": model_system_prompt})
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation.append({"role": role, "content": content})
        
        # Check if conversation is empty and provide default
        if not conversation:
            conversation = [
                {"role": "system", "content": model_system_prompt},
                {"role": "user", "content": "Hello"}
            ]
        
        # Generate response using chat template with generation prompt
        input_tokens = tokenizer.apply_chat_template(
            conversation, 
            return_tensors="pt",
            add_generation_prompt=True
        )
        
        # Move tensors to the same device as the model (supports MPS, CUDA, CPU)
        model_device = next(model.parameters()).device
        input_tokens = input_tokens.to(model_device)
        
        # Ensure input_tokens is on the correct device
        if str(model_device).startswith('mps'):
            # MPS requires special handling
            input_tokens = input_tokens.to('mps')
            
        # Create attention mask
        attention_mask = torch.ones_like(input_tokens)
        
        # Set pad token if needed
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        with torch.no_grad():
            # MPS fix: ensure all tensors are on the same device
            if str(model_device).startswith('mps'):
                # For MPS, we need to be more careful with generation parameters
                outputs = model.generate(
                    input_tokens,
                    attention_mask=attention_mask,
                    max_new_tokens=max_tokens,  # Use max_new_tokens instead of max_length for MPS
                    do_sample=True,
                    temperature=temperature,
                    pad_token_id=tokenizer.pad_token_id,
                    use_cache=False  # Disable cache to avoid DynamicCache compatibility issues
                )
            else:
                outputs = model.generate(
                    input_tokens,
                    attention_mask=attention_mask,
                    max_new_tokens=max_tokens,  # Use max_new_tokens consistently
                    do_sample=True,
                    temperature=temperature,
                    pad_token_id=tokenizer.pad_token_id,
                    use_cache=False  # Disable cache to avoid DynamicCache compatibility issues
                )
        
        # Decode the response
        response_text = tokenizer.decode(outputs[0][input_tokens.shape[1]:], skip_special_tokens=True)
        response_text = filter_thinking_tags(response_text)
        
        # Count tokens (rough estimation)
        input_token_count = input_tokens.shape[1]
        output_token_count = outputs.shape[1] - input_tokens.shape[1]
        
        return {
            "text": response_text,
            "usage": {
                "prompt_tokens": input_token_count,
                "completion_tokens": output_token_count,
                "total_tokens": input_token_count + output_token_count
            }
        }
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

@app.get("/models")
async def list_models():
    """List all available models and their status"""
    if not lifecycle_manager:
        raise HTTPException(status_code=503, detail="Lifecycle manager not initialized")
    
    loaded = lifecycle_manager.get_loaded_models()
    available = list(lifecycle_manager.models.keys())
    
    return {
        "available_models": available,
        "loaded_models": loaded,
        "default_model": MODEL_NAME,
        "max_loaded_models": lifecycle_manager.max_loaded_models,
        "idle_timeout_minutes": lifecycle_manager.idle_timeout_minutes,
        "development_mode": lifecycle_manager.development_mode
    }

@app.post("/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Manually unload a specific model"""
    if not lifecycle_manager:
        raise HTTPException(status_code=503, detail="Lifecycle manager not initialized")
    
    if model_name not in lifecycle_manager.models:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    lifecycle_manager.unload_model(model_name)
    return {"message": f"Model {model_name} unloaded successfully"}

@app.post("/route")
async def route_endpoint(request: Request):
    """Analyze a message and return routing decision without generating response"""
    try:
        body = await request.json()
        message = body.get("message", "")
        requested_model = body.get("model")
        conversation_history = body.get("conversation_history")
        
        # Get available models
        available_models = list(lifecycle_manager.models.keys()) if lifecycle_manager else []
        
        # Get routing decision
        routing_decision = task_router.route_request(
            message=message,
            conversation_history=conversation_history,
            requested_model=requested_model,
            available_models=available_models
        )
        
        # Add additional info
        routing_decision['available_models'] = available_models
        routing_decision['task_routing_enabled'] = task_router.enabled
        
        return routing_decision
        
    except Exception as e:
        logger.error(f"Routing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Routing analysis failed: {str(e)}")

@app.post("/models/{model_name}/load")
async def load_model_endpoint(model_name: str):
    """Preload a specific model without generating any text"""
    if not lifecycle_manager:
        raise HTTPException(status_code=503, detail="Lifecycle manager not initialized")
    
    if model_name not in lifecycle_manager.models:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    try:
        # Load the model
        device = get_best_device()
        dtype = get_torch_dtype()
        start_time = time.time()
        
        model, tokenizer = lifecycle_manager.get_model(model_name, device, dtype)
        
        load_time = time.time() - start_time
        
        return {
            "message": f"Model {model_name} loaded successfully",
            "load_time_seconds": round(load_time, 2),
            "device": str(device),
            "dtype": str(dtype)
        }
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

@app.post("/models/preload")
async def preload_models_endpoint(request: Request):
    """Preload multiple models based on priority or explicit list"""
    try:
        body = await request.json() if await request.body() else {}
        models_to_load = body.get("models", [])
        
        if not models_to_load:
            # Default: load highest priority models
            sorted_models = sorted(
                lifecycle_manager.models.items(),
                key=lambda x: x[1].priority
            )
            models_to_load = [name for name, _ in sorted_models[:2]]  # Top 2 priority models
        
        results = {}
        device = get_best_device()
        dtype = get_torch_dtype()
        
        for model_name in models_to_load:
            if model_name not in lifecycle_manager.models:
                results[model_name] = {"status": "error", "message": "Model not found"}
                continue
                
            try:
                start_time = time.time()
                model, tokenizer = lifecycle_manager.get_model(model_name, device, dtype)
                load_time = time.time() - start_time
                
                results[model_name] = {
                    "status": "success",
                    "load_time_seconds": round(load_time, 2)
                }
            except Exception as e:
                results[model_name] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return {
            "preloaded": results,
            "loaded_models": lifecycle_manager.get_loaded_models()
        }
        
    except Exception as e:
        logger.error(f"Preload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preload failed: {str(e)}")

# Track startup time
startup_time = time.time()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host=host, port=port, log_level="info")