import os
import logging
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn
import re
from filtering.filter_manager import FilterManager
from gateway import filter_api

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-gateway")

app = FastAPI(title="LLM Gateway Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include filter management API
app.include_router(filter_api.router)

# Load configuration from environment
PORT = int(os.environ.get("LLM_GATEWAY_PORT", 8080))
DEFAULT_MODEL = os.environ.get("LLM_DEFAULT_MODEL", "llama3")
MODELS_ENABLED = os.environ.get("LLM_MODELS_ENABLED", "llama3,phi3,zephyr").split(",")
FILTERING_ENABLED = os.environ.get("LLM_FILTERING_ENABLED", "true").lower() == "true"
SERVICE_TIMEOUT = int(os.environ.get("LLM_SERVICE_TIMEOUT", 30))
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", 3))

# Routing configuration
ROUTING_ENABLED = os.environ.get("LLM_ROUTING_ENABLED", "true").lower() == "true"
DEFAULT_THRESHOLD = float(os.environ.get("LLM_ROUTING_THRESHOLD", 0.6))
INFORMATION_MODEL = os.environ.get("LLM_INFORMATION_MODEL", "phi3")
CREATIVE_MODEL = os.environ.get("LLM_CREATIVE_MODEL", "llama3")
TECHNICAL_MODEL = os.environ.get("LLM_TECHNICAL_MODEL", "zephyr")

# LLM service URLs - now using Ollama/External AI
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
EXTERNAL_AI_HOST = os.environ.get("EXTERNAL_AI_HOST", "http://host.docker.internal:8091")

# Map model names to the appropriate service
MODEL_SERVICES = {
    "llama3": f"{EXTERNAL_AI_HOST}/v1/chat/completions",
    "phi3": f"{EXTERNAL_AI_HOST}/v1/chat/completions",
    "zephyr": f"{EXTERNAL_AI_HOST}/v1/chat/completions",
    "deepseek": f"{EXTERNAL_AI_HOST}/v1/chat/completions",
    "tinyllama": f"{EXTERNAL_AI_HOST}/v1/chat/completions"
}

# Initialize filter manager
filter_config = {
    "toxicity": {
        "enabled": os.environ.get("LLM_TOXICITY_ENABLED", "true").lower() == "true",
        "threshold": float(os.environ.get("LLM_TOXICITY_THRESHOLD", 0.7))
    },
    "data_leakage": {
        "enabled": os.environ.get("LLM_DATA_LEAKAGE_ENABLED", "true").lower() == "true"
    }
}
filter_manager = FilterManager(filter_config)

# Load any custom filters
filter_manager.load_custom_filters()

# Track service health
service_health = {model: False for model in MODEL_SERVICES}
last_health_check = {model: 0 for model in MODEL_SERVICES}
HEALTH_CHECK_INTERVAL = 60  # seconds

# Request/response counters
request_count = 0
error_count = 0
filtered_count = 0
routing_stats = {model: 0 for model in MODEL_SERVICES}

# Pydantic models
class GenerationRequest(BaseModel):
    message: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    routing_disabled: Optional[bool] = False

class GenerationResponse(BaseModel):
    response: str
    model: str
    filtered: bool = False
    filter_reason: Optional[str] = None
    processing_time: float
    routed: bool = False

# Content type patterns for smart routing
CONTENT_PATTERNS = {
    "information": [
        r"(what|who|when|where|why|how)\s+is",
        r"explain",
        r"describe",
        r"inform",
        r"tell\s+me\s+about",
        r"facts",
        r"information\s+on",
        r"background\s+of",
        r"history\s+of",
        r"definition\s+of"
    ],
    "creative": [
        r"story",
        r"write\s+a",
        r"create\s+a",
        r"imagine",
        r"poem",
        r"song",
        r"fiction",
        r"creative",
        r"brainstorm",
        r"generate\s+ideas"
    ],
    "technical": [
        r"code",
        r"programming",
        r"function",
        r"algorithm",
        r"technical",
        r"debug",
        r"compute",
        r"calculate",
        r"implement",
        r"analyze\s+data"
    ]
}

# Compiled patterns for efficiency
COMPILED_PATTERNS = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in CONTENT_PATTERNS.items()
}

# Dependency to get filter manager
def get_filter_manager():
    return filter_manager

async def check_service_health(model: str) -> bool:
    """Check if a model service is healthy"""
    current_time = time.time()
    
    # Only check health every HEALTH_CHECK_INTERVAL seconds
    if current_time - last_health_check[model] < HEALTH_CHECK_INTERVAL and service_health[model]:
        return service_health[model]
    
    # Update last check time
    last_health_check[model] = current_time
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(MODEL_SERVICES[model].replace("/generate", "/health"))
            
        if response.status_code == 200:
            service_health[model] = True
            return True
        else:
            service_health[model] = False
            logger.warning(f"Health check failed for {model}: {response.status_code}")
            return False
            
    except Exception as e:
        service_health[model] = False
        logger.warning(f"Health check failed for {model}: {str(e)}")
        return False

def determine_content_type(message: str) -> str:
    """Determine the type of content based on the message"""
    scores = {category: 0 for category in CONTENT_PATTERNS}
    
    # Check each category
    for category, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                scores[category] += 1
                
    # Find the highest scoring category
    if max(scores.values()) > 0:
        max_category = max(scores.items(), key=lambda x: x[1])[0]
        if scores[max_category] >= DEFAULT_THRESHOLD * len(COMPILED_PATTERNS[max_category]):
            return max_category
            
    # Default to information if nothing matches strongly
    return "information"

def select_model_for_content(content_type: str, requested_model: Optional[str] = None) -> str:
    """Select the appropriate model based on content type and availability"""
    # Use explicitly requested model if provided and available
    if requested_model and requested_model in MODELS_ENABLED:
        return requested_model
        
    # Map content type to preferred model
    model_mapping = {
        "information": INFORMATION_MODEL,
        "creative": CREATIVE_MODEL,
        "technical": TECHNICAL_MODEL
    }
    
    preferred_model = model_mapping.get(content_type, DEFAULT_MODEL)
    
    # Make sure preferred model is in enabled models
    if preferred_model in MODELS_ENABLED:
        return preferred_model
        
    # Fallback to default model
    return DEFAULT_MODEL

@app.post("/generate", response_model=GenerationResponse)
async def generate(
    request: GenerationRequest,
    filter_mgr: FilterManager = Depends(get_filter_manager)
):
    """Generate text from the specified model with content filtering and smart routing"""
    global request_count, error_count, filtered_count
    
    start_time = time.time()
    request_count += 1
    
    selected_model = request.model
    was_routed = False
    
    # Apply content-based routing if enabled and not explicitly disabled for this request
    if ROUTING_ENABLED and not request.routing_disabled and not selected_model:
        content_type = determine_content_type(request.message)
        selected_model = select_model_for_content(content_type)
        was_routed = True
        logger.info(f"Routed request to {selected_model} based on content type: {content_type}")
    
    # Final model selection, fallback to default if needed
    model = selected_model if selected_model in MODELS_ENABLED else DEFAULT_MODEL
    
    # Update routing statistics
    if was_routed:
        routing_stats[model] = routing_stats.get(model, 0) + 1
    
    # Check if model service is healthy
    if not await check_service_health(model):
        # Try to find a healthy alternative
        for alt_model in MODELS_ENABLED:
            if await check_service_health(alt_model):
                logger.info(f"Falling back to {alt_model} as {model} is unavailable")
                model = alt_model
                break
        else:
            error_count += 1
            raise HTTPException(status_code=503, detail="No LLM services are currently available")
    
    # First check the input for problematic content
    if FILTERING_ENABLED:
        should_filter, reason = filter_mgr.check_text(request.message)
        if should_filter:
            filtered_count += 1
            return GenerationResponse(
                response="I apologize, but I cannot process this request as it appears to contain inappropriate content.",
                model=model,
                filtered=True,
                filter_reason=reason,
                processing_time=time.time() - start_time,
                routed=was_routed
            )
    
    # Prepare request to model service
    payload = {
        "message": request.message
    }
    
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
        
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    
    # Send request to model service with retries
    model_response = None
    error_message = None
    
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
                response = await client.post(MODEL_SERVICES[model], json=payload)
                
                if response.status_code == 200:
                    model_response = response.json()
                    break
                else:
                    error_message = f"Model service returned error: {response.status_code}"
                    logger.warning(f"Attempt {attempt+1}: {error_message}")
                    
                    # If service is down, mark it as unhealthy
                    if response.status_code >= 500:
                        service_health[model] = False
                        
        except Exception as e:
            error_message = f"Error calling model service: {str(e)}"
            logger.warning(f"Attempt {attempt+1}: {error_message}")
            service_health[model] = False
    
    if model_response is None:
        error_count += 1
        raise HTTPException(status_code=500, detail=error_message or "Failed to get response from model service")
    
    response_text = model_response.get("response", "")
    
    # Apply content filtering to the response
    if FILTERING_ENABLED:
        should_filter, reason = filter_mgr.check_text(response_text)
        if should_filter:
            filtered_count += 1
            return GenerationResponse(
                response="I apologize, but I cannot provide the response as it may contain inappropriate content.",
                model=model,
                filtered=True,
                filter_reason=reason,
                processing_time=time.time() - start_time,
                routed=was_routed
            )
    
    # Return the final response
    return GenerationResponse(
        response=response_text,
        model=model,
        filtered=False,
        processing_time=time.time() - start_time,
        routed=was_routed
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check the health of all model services
    service_status = {}
    for model in MODEL_SERVICES:
        service_status[model] = await check_service_health(model)
    
    # Overall health status
    healthy = any(service_status.values())
    
    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": time.time(),
        "services": service_status,
        "filtering_enabled": FILTERING_ENABLED,
        "routing_enabled": ROUTING_ENABLED,
        "default_model": DEFAULT_MODEL
    }

@app.get("/stats")
async def get_stats(filter_mgr: FilterManager = Depends(get_filter_manager)):
    """Get statistics about the gateway and filters"""
    return {
        "uptime": time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0,
        "requests": {
            "total": request_count,
            "errors": error_count,
            "filtered": filtered_count,
            "success_rate": (request_count - error_count - filtered_count) / request_count if request_count > 0 else 0
        },
        "routing": {
            "enabled": ROUTING_ENABLED,
            "stats": routing_stats
        },
        "services": service_health,
        "filters": filter_mgr.get_stats()
    }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    app.state.start_time = time.time()
    
    # Initialize health checks for all services
    for model in MODEL_SERVICES:
        await check_service_health(model)
        
    # Log startup information
    enabled_models = ", ".join(MODELS_ENABLED)
    logger.info(f"LLM Gateway started with models: {enabled_models}")
    logger.info(f"Filtering enabled: {FILTERING_ENABLED}")
    logger.info(f"Content routing enabled: {ROUTING_ENABLED}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)