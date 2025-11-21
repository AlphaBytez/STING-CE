#!/usr/bin/env python3
"""
STING External AI Service
Bridge between frontend and Ollama for AI-powered features
"""

import os
import logging
import asyncio
import aiohttp
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import Queue Manager
from llm_queue_manager import LLMQueueManager, QueuedRequest, RequestStatus, UserRole

# Import Bee Context Manager for enhanced chat capabilities
from bee_context_manager import BeeContextManager

# Configure logging first (before PII import that may fail)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import PII Serialization Middleware
import sys
# Add middleware directory to path to avoid app.py vs app package conflict
sys.path.insert(0, '/app/app/middleware')
try:
    from pii_serialization import PIIMiddleware, EnhancedDeserializer, ImprovedCacheManager, ModeDetector
except Exception as e:
    logger.warning(f"Failed to load PII middleware: {e}")
    PIIMiddleware = None
    EnhancedDeserializer = None
    ImprovedCacheManager = None
    ModeDetector = None

# Get CORS origins from environment or use defaults
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else [
    "https://localhost:8443",
    "http://localhost:8443",
    "https://127.0.0.1:8443",
    "http://127.0.0.1:8443",
    "http://localhost",
    "https://localhost",
    "http://host.docker.internal:8443",
    "https://host.docker.internal:8443"
]

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SERVICE_PORT = int(os.getenv("EXTERNAL_AI_PORT", "8091"))
SERVICE_HOST = os.getenv("EXTERNAL_AI_HOST", "0.0.0.0")

app = FastAPI(
    title="STING External AI Service",
    description="Bridge service for AI providers including Ollama",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ReportRequest(BaseModel):
    templateId: str
    provider: str
    privacyLevel: str
    dataSources: List[str]
    requiredFields: Dict[str, Any]
    authenticatedAt: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    user_role: Optional[str] = "worker"
    async_mode: Optional[bool] = True  # Default to async for reports

class OllamaGenerateRequest(BaseModel):
    model: str
    prompt: str
    options: Optional[Dict[str, Any]] = {}

class KnowledgeSyncRequest(BaseModel):
    data: Dict[str, Any]
    targetProvider: str = "ollama"
    syncType: str = "incremental"

class EmbeddingRequest(BaseModel):
    documents: List[str]
    provider: str = "ollama"
    model: str = "nomic-embed-text"

class BeeChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None
    tools_enabled: List[str] = []
    require_auth: bool = False
    encryption_required: bool = False
    context: Optional[Dict[str, Any]] = None
    user_role: Optional[str] = "worker"  # Default role if not specified
    async_mode: Optional[bool] = False  # Whether to use queue or direct processing
    honey_jar_id: Optional[str] = None  # ID of honey jar to use for context

# AI Provider configurations
AI_PROVIDERS = {
    "ollama": {
        "id": "ollama",
        "name": "Ollama Local",
        "description": "Local Ollama deployment for maximum privacy and control",
        "capabilities": ["text-analysis", "summarization", "insights", "code-review", "agent-tasks"],
        "privacyLevel": "high",
        "estimatedCost": 0.0,
        "maxTokens": 32000,
        "type": "local",
        "defaultModel": "qwen2.5-14b-instruct",
        "endpoint": OLLAMA_BASE_URL,
        "features": {
            "knowledgeSync": True,
            "agentTasks": True,
            "codeAnalysis": True,
            "multiModal": False
        }
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI GPT-4",
        "description": "Advanced language model for comprehensive analysis",
        "capabilities": ["text-analysis", "summarization", "insights", "recommendations"],
        "privacyLevel": "medium",
        "estimatedCost": 0.03,
        "maxTokens": 128000,
        "type": "cloud"
    },
    "claude": {
        "id": "claude",
        "name": "Anthropic Claude",
        "description": "Constitutional AI for safe and helpful analysis",
        "capabilities": ["text-analysis", "summarization", "code-review", "research"],
        "privacyLevel": "medium",
        "estimatedCost": 0.025,
        "maxTokens": 200000,
        "type": "cloud"
    }
}

class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        # Remove trailing slash to prevent double slashes in URLs
        self.base_url = base_url.rstrip('/')
        
    async def check_status(self) -> Dict[str, Any]:
        """Check if LLM service is running (OpenAI-compatible API standard)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
                async with session.get(f"{self.base_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("data", [])
                        logger.debug(f"Connected via OpenAI-compatible API: {len(models)} models available")
                        return {
                            "running": True,
                            "models": len(models),
                            "endpoint": self.base_url,
                            "api_type": "openai_compatible"
                        }
                    else:
                        logger.warning(f"LLM service returned status {response.status}")
                        return {"running": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Failed to check LLM service status: {e}")
            return {"running": False, "error": str(e)}
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available models (OpenAI-compatible API standard)"""
        logger.info(f"🔍 Attempting to fetch models from {self.base_url}/v1/models")
        try:
            async with aiohttp.ClientSession() as session:
                # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
                async with session.get(f"{self.base_url}/v1/models") as response:
                    logger.info(f"📡 Got response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"📦 Response data keys: {data.keys()}")
                        # Convert OpenAI format to Ollama-like format for compatibility
                        models = []
                        for model in data.get("data", []):
                            models.append({
                                "name": model.get("id"),
                                "modified_at": model.get("created", ""),
                                "size": 0,  # Not provided by OpenAI API
                                "digest": "",
                                "details": {"format": "openai_compatible"}
                            })
                        logger.info(f"✅ Retrieved {len(models)} models via OpenAI-compatible API")
                        return models
                    else:
                        logger.warning(f"❌ Failed to get models: HTTP {response.status}")
                        return []  # Return empty list instead of raising exception
        except HTTPException:
            raise  # Re-raise HTTPException for API endpoints
        except Exception as e:
            logger.error(f"❌ Exception in get_models: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []  # Return empty list for startup robustness
    
    async def generate(self, model: str, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate text using OpenAI-compatible API only (/v1/chat/completions)"""
        try:
            import time
            start_time = time.time()

            max_tokens_value = options.get("num_predict", 2048) if options else 2048

            # Set timeout for LLM generation
            # Conservative timeout for long-form report generation (up to 16K tokens)
            # At ~10 tokens/sec, 16K tokens ≈ 27 minutes. Set to 45 min for safety.
            timeout_seconds = 2700  # 45 minutes - reports are queued, so longer timeout is acceptable
            # Set total timeout but sock_read=None for non-streaming responses
            # In non-streaming mode, LM Studio doesn't send data until fully generated
            # so sock_read needs to be unlimited (None) to avoid timeout during generation
            timeout = aiohttp.ClientTimeout(total=timeout_seconds, sock_read=None)

            openai_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": options.get("temperature", 0.7) if options else 0.7,
                "max_tokens": max_tokens_value
            }
            logger.info(f"📤 Sending to LLM: max_tokens={max_tokens_value}, model={model}, timeout={timeout_seconds}s")

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=openai_payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Calculate duration since OpenAI API doesn't provide it
                        duration_ns = int((time.time() - start_time) * 1e9)

                        # Convert OpenAI format to Ollama format for compatibility
                        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                        finish_reason = data.get("choices", [{}])[0].get("finish_reason", "unknown")
                        logger.info(f"✅ OpenAI-compatible API successful for model {model}")
                        logger.info(f"📊 Token usage: completion={completion_tokens}, requested_max={max_tokens_value}, finish_reason={finish_reason}")
                        return {
                            "response": data["choices"][0]["message"]["content"],
                            "model": data.get("model", model),
                            "created_at": data.get("created", ""),
                            "done": True,
                            "eval_count": completion_tokens,
                            "total_duration": duration_ns
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ OpenAI API returned status {response.status}: {error_text}")
                        raise HTTPException(status_code=response.status, detail=f"LLM API error: {error_text}")
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            logger.error(f"Failed to generate: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

# Initialize Ollama client
ollama_client = OllamaClient()

# Initialize Queue Manager
queue_manager = LLMQueueManager()

# Initialize Bee Context Manager
bee_context_manager = BeeContextManager()

# Initialize PII Middleware (basic initialization, enhanced components added in startup_event)
pii_middleware = None
mode_detector = None
app_config = None  # Store config for startup event
llm_config = {}   # Store LLM configuration (max_tokens, temperature, etc.)
if PIIMiddleware is not None:
    try:
        import yaml
        config_path = os.getenv("CONFIG_PATH", "/app/conf/config.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                app_config = yaml.safe_load(f)
                security_config = app_config.get('security', {})
                pii_middleware = PIIMiddleware(security_config)

                # Load LLM configuration for Bee chat
                conversation_config = security_config.get('conversation', {})
                llm_config.update({
                    'max_tokens': conversation_config.get('max_tokens', 4096),
                    'temperature': conversation_config.get('temperature', 0.7),
                })
                logger.info(f"LLM config loaded: max_tokens={llm_config['max_tokens']}, temperature={llm_config['temperature']}")

                # Load report generation configuration
                llm_service_config = app_config.get('llm_service', {})
                report_gen_config = llm_service_config.get('report_generation', {})
                llm_config.update({
                    'report_model': report_gen_config.get('model', 'qwen2.5-14b-instruct'),
                    'report_fallback_model': report_gen_config.get('fallback_model', 'qwen2.5-14b-instruct'),
                    'report_max_tokens': report_gen_config.get('max_tokens', 8192),
                    'report_min_output_tokens': report_gen_config.get('min_output_tokens', 4500),
                })
                logger.info(f"Report generation config loaded: model={llm_config['report_model']}, max_tokens={llm_config['report_max_tokens']}")

                # Initialize mode detector for intelligent PII protection mode selection
                if ModeDetector is not None:
                    pii_config = security_config.get('message_pii_protection', {})
                    mode_detector = ModeDetector(pii_config)
                    logger.info("PII mode detector initialized (auto-detection enabled)")

                logger.info("PII middleware initialized (will upgrade to enhanced mode in startup)")
        else:
            logger.warning(f"Config file not found at {config_path}, PII middleware disabled")
    except Exception as e:
        logger.error(f"Failed to initialize PII middleware: {e}")
        logger.warning("PII protection will be disabled for this service")
else:
    logger.warning("PII middleware module not available, protection disabled")

# Worker task handle
worker_task = None

# Global flag for indexing status (threading.Event for async-safe status)
is_indexing = threading.Event()

@app.get("/health")
async def health_check():
    """Health check endpoint that remains responsive during indexing"""
    if is_indexing.is_set():
        # During indexing, return a special status but still respond
        return {
            "status": "healthy",
            "service": "external-ai",
            "indexing": True,
            "timestamp": datetime.now().isoformat()
        }
    return {
        "status": "healthy",
        "service": "external-ai",
        "indexing": False,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/pii/diagnostics")
async def pii_diagnostics():
    """
    PII Protection System Health and Diagnostics Endpoint

    Returns comprehensive diagnostics about the PII protection system including:
    - Cache performance metrics (hit rate, misses, errors)
    - Redis connection status
    - System health score
    - Operational recommendations

    This endpoint is critical for enterprise audit compliance and monitoring.
    """
    if not pii_middleware:
        return {
            "status": "disabled",
            "message": "PII protection middleware not loaded",
            "timestamp": datetime.now().isoformat()
        }

    # Check if enhanced deserializer is available
    if isinstance(getattr(pii_middleware, 'deserializer', None), EnhancedDeserializer):
        # Get comprehensive diagnostics from enhanced components
        deserializer = pii_middleware.deserializer
        cache_manager = pii_middleware.cache_manager

        # Get cache diagnostics
        if hasattr(cache_manager, 'get_diagnostics'):
            cache_diagnostics = cache_manager.get_diagnostics()
            cache_stats = cache_diagnostics.get('cache_stats', {})

            # Calculate health metrics
            total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            if total_requests > 0:
                hit_rate = cache_stats.get('hits', 0) / total_requests
                health_score = "healthy" if hit_rate > 0.8 else "degraded" if hit_rate > 0.5 else "unhealthy"
            else:
                hit_rate = 0
                health_score = "no_data"

            # Generate recommendations
            recommendations = []
            if cache_stats.get('misses', 0) > cache_stats.get('hits', 0):
                recommendations.append("High cache miss rate - consider increasing TTL in config.yml (current: 300s)")
            if cache_stats.get('errors', 0) > 10:
                recommendations.append("Redis connection issues detected - check Redis connectivity and logs")
            if cache_stats.get('fallback_used', 0) > 100:
                recommendations.append("Heavy fallback usage - Redis may be unavailable or overloaded")
            if cache_diagnostics.get('local_cache_size', 0) > 1000:
                recommendations.append("Large local cache - consider increasing Redis stability")

            # Get mode detection info
            mode_detection_info = None
            if mode_detector:
                # Detect mode for current Ollama endpoint
                detected_mode, mode_config = mode_detector.detect_mode(
                    endpoint_url=OLLAMA_BASE_URL,
                    provider="ollama",
                    context="chat"
                )
                mode_detection_info = {
                    "enabled": mode_detector.auto_detection_config.get('enabled', False),
                    "current_endpoint": OLLAMA_BASE_URL,
                    "detected_mode": detected_mode,
                    "protection_level": mode_config.get('protection_level', 'unknown'),
                    "mode_enabled": mode_config.get('enabled', False),
                    "protected_pii_types": mode_config.get('pii_types', []),
                    "detection_method": "auto_detected" if mode_detector.auto_detection_config.get('enabled') else "manual_config",
                    "fallback_mode": mode_detector.auto_detection_config.get('fallback_mode', 'external'),
                    "trusted_networks": mode_detector.auto_detection_config.get('trusted_networks', []),
                    "request_overrides_enabled": mode_detector.override_config.get('enabled', False)
                }

            return {
                "status": health_score,
                "hit_rate": round(hit_rate, 3),
                "cache_diagnostics": cache_diagnostics,
                "deserializer_diagnostics": deserializer.diagnostics,
                "mode_detection": mode_detection_info,
                "recommendations": recommendations,
                "enhanced_mode": True,
                "features": {
                    "position_tracking": True,
                    "visual_indicators": True,
                    "fallback_cache": True,
                    "diagnostics": True,
                    "intelligent_mode_detection": mode_detector is not None
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Enhanced deserializer but no full diagnostics
            return {
                "status": "enhanced_basic",
                "message": "Enhanced deserializer active but cache diagnostics unavailable",
                "deserializer_diagnostics": deserializer.diagnostics,
                "enhanced_mode": True,
                "timestamp": datetime.now().isoformat()
            }
    else:
        # Basic middleware without enhanced features
        return {
            "status": "basic",
            "message": "Basic PII middleware active (no position tracking or visual indicators)",
            "enhanced_mode": False,
            "features": {
                "position_tracking": False,
                "visual_indicators": False,
                "fallback_cache": False,
                "diagnostics": False
            },
            "recommendation": "Restart service to enable enhanced PII features with visual indicators",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/providers")
async def get_providers():
    """Get available AI providers"""
    return list(AI_PROVIDERS.values())

@app.get("/ollama/status")
async def get_ollama_status():
    """Check Ollama status"""
    return await ollama_client.check_status()

@app.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models"""
    return await ollama_client.get_models()

@app.post("/ollama/generate")
async def ollama_generate(request: OllamaGenerateRequest):
    """Generate text using Ollama"""
    return await ollama_client.generate(request.model, request.prompt, request.options)

@app.post("/reports/generate")
async def generate_report(request: ReportRequest):
    """Generate AI-powered report"""
    try:
        # If async mode, enqueue the request
        if request.async_mode:
            request_id = await queue_manager.enqueue_request(
                user_id=request.user_id,
                user_role=request.user_role,
                request_type="report",
                payload={
                    "templateId": request.templateId,
                    "provider": request.provider,
                    "privacyLevel": request.privacyLevel,
                    "dataSources": request.dataSources,
                    "requiredFields": request.requiredFields
                },
                priority_boost=2  # Reports get priority boost
            )
            
            return {
                "request_id": request_id,
                "status": "queued",
                "message": "Report generation queued",
                "check_status_url": f"/queue/status/{request_id}"
            }
        
        # Synchronous mode - process immediately
        # For now, route all reports to Ollama if provider is ollama
        if request.provider == "ollama":
            # Check if Ollama is available
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # Get available models
            models = await ollama_client.get_models()
            if not models:
                raise HTTPException(status_code=503, detail="No Ollama models available")
            
            # Use the configured default model or fall back to first available
            default_model = AI_PROVIDERS["ollama"]["defaultModel"]
            available_models = [m["name"] for m in models]
            
            if default_model not in available_models:
                logger.warning(f"Default model '{default_model}' not found. Available models: {available_models}")
                if available_models:
                    model_name = available_models[0]
                    logger.info(f"Using fallback model: {model_name}")
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"No models available. Please install a model using: 'ollama pull {default_model}'"
                    )
            else:
                model_name = default_model
            
            # Create report prompt based on template
            prompt = f"""
Generate a comprehensive report for template: {request.templateId}

Data Sources: {', '.join(request.dataSources)}
Privacy Level: {request.privacyLevel}
Required Fields: {json.dumps(request.requiredFields, indent=2)}

Please provide:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Recommendations
5. Conclusion

Format the response as a structured report.
"""
            
            # Generate report using Ollama
            result = await ollama_client.generate(model_name, prompt)
            
            return {
                "reportId": f"report_{int(datetime.now().timestamp())}",
                "status": "completed",
                "provider": request.provider,
                "model": model_name,
                "content": result.get("response", ""),
                "generatedAt": datetime.now().isoformat(),
                "privacyLevel": request.privacyLevel,
                "tokensUsed": result.get("eval_count", 0),
                "processingTime": result.get('total_duration', 0) / 1e9
            }
        else:
            # For other providers, return a placeholder response
            return {
                "reportId": f"report_{int(datetime.now().timestamp())}",
                "status": "pending",
                "provider": request.provider,
                "message": f"Report generation with {request.provider} is not yet implemented",
                "estimatedCompletion": "5-10 minutes"
            }
            
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bee/chat")
async def bee_chat(request: BeeChatRequest):
    """Unified Bee chat endpoint that can handle both conversations and report generation"""
    try:
        # If async mode, enqueue the request
        if request.async_mode:
            request_id = await queue_manager.enqueue_request(
                user_id=request.user_id,
                user_role=request.user_role,
                request_type="chat",
                payload={
                    "message": request.message,
                    "conversation_id": request.conversation_id,
                    "tools_enabled": request.tools_enabled,
                    "context": request.context,
                    "encryption_required": request.encryption_required
                }
            )
            
            return {
                "request_id": request_id,
                "status": "queued",
                "message": "Request queued for processing",
                "check_status_url": f"/queue/status/{request_id}"
            }
        
        # Synchronous mode - process immediately
        # Check if Ollama is available
        status = await ollama_client.check_status()
        if not status.get("running"):
            raise HTTPException(status_code=503, detail="Ollama service is not available")
        
        # Get available models
        models = await ollama_client.get_models()
        if not models:
            raise HTTPException(status_code=503, detail="No Ollama models available")
        
        # Use the configured default model or fall back to first available
        default_model = AI_PROVIDERS["ollama"]["defaultModel"]
        available_models = [m["name"] for m in models]
        
        if default_model not in available_models:
            logger.warning(f"Default model '{default_model}' not found. Available models: {available_models}")
            if available_models:
                model_name = available_models[0]
                logger.info(f"Using fallback model: {model_name}")
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"No models available. Please install a model using: 'ollama pull {default_model}'"
                )
        else:
            model_name = default_model
        
        # Detect if user is asking for a report
        # Check context first (explicit report generation from report worker)
        is_report_request = request.context and request.context.get('generation_mode') == 'report'

        # If not explicitly set in context, check keywords in message
        if not is_report_request:
            report_keywords = ["generate report", "create report", "report on", "analyze", "summary report", "detailed analysis", "word analysis", "word report"]
            is_report_request = any(keyword in request.message.lower() for keyword in report_keywords)

        if is_report_request:
            # Override model for report generation - use model from config (user-editable in config.yml)
            report_model = llm_config.get('report_model', model_name)
            fallback_model = llm_config.get('report_fallback_model', model_name)
            logger.info(f"🔄 Switching to report-optimized model: {report_model} (from {model_name})")

            # Verify report model is available, fall back if necessary
            if report_model in available_models:
                model_name = report_model
            elif fallback_model in available_models:
                logger.warning(f"Report model '{report_model}' not available, using fallback: {fallback_model}")
                model_name = fallback_model
            else:
                logger.warning(f"Neither report model '{report_model}' nor fallback '{fallback_model}' available, using default: {model_name}")

            # Handle as report generation with enhanced context
            enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
                request.message,
                request.user_id,
                conversation_id=request.conversation_id,
                conversation_history=None,
                honey_jar_id=request.honey_jar_id
            )

            report_prompt = f"""{enhanced_prompt}

You are generating a professional enterprise report. This MUST be a comprehensive, detailed document.

CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE:
1. Minimum length: 3500-5000 words (approximately 4500-7000 tokens)
2. Each major section MUST contain 4-6 substantial paragraphs with specific details
3. DO NOT use LaTeX notation like \\boxed{{}} - write in plain professional prose
4. DO NOT stop until you have thoroughly covered all sections with extensive detail
5. Provide concrete examples, data points, and technical specifics throughout

REQUIRED STRUCTURE (follow this exactly):

1. **Executive Summary** (400-600 words)
   Write 4-5 detailed paragraphs covering:
   - Comprehensive overview of the analysis scope and methodology
   - All key findings with specific metrics and observations
   - Critical implications and business impact
   - High-level recommendations summary

2. **Detailed Analysis** (1500-2000 words minimum)
   Write 6-8 comprehensive paragraphs covering:
   - In-depth technical examination with specific architecture details
   - Multiple data points, configurations, and system behaviors
   - Security analysis with threat models and mitigation details
   - Performance characteristics and scalability considerations
   - Integration points and API specifications
   - Detailed technical workflows and data flows

3. **Recommendations** (800-1200 words)
   Write 5-7 detailed paragraphs covering:
   - Specific, actionable next steps with implementation details
   - Best practices with concrete examples
   - Risk mitigation strategies with prioritization
   - Resource requirements and timelines
   - Success metrics and monitoring approaches

4. **Conclusion** (400-600 words)
   Write 4-5 paragraphs covering:
   - Comprehensive summary of all key findings
   - Strategic implications for the organization
   - Future roadmap and evolution considerations
   - Final recommendations prioritized by impact

FORMATTING RULES:
- Use markdown headers (##) for sections
- Write in clear, professional business prose
- Include specific technical details and examples
- Avoid brevity - elaborate thoroughly on each point
- NO mathematical notation or LaTeX formatting
- Maintain professional enterprise report tone throughout

Begin the report now. Remember: This must be thorough and comprehensive with substantial detail in every section.
"""

            # PII Protection: Serialize before sending to LLM
            pii_context = {}
            protection_mode = "external"  # Default fallback
            if pii_middleware:
                try:
                    # Intelligent mode detection based on endpoint and context
                    if mode_detector:
                        protection_mode, mode_config = mode_detector.detect_mode(
                            endpoint_url=OLLAMA_BASE_URL,
                            provider="ollama",
                            context="report",  # Report context uses selective protection
                            user_role=request.user_role or "user"
                        )
                        logger.info(f"PII protection mode for report: {protection_mode} (level: {mode_config.get('protection_level')})")

                    report_prompt, pii_context = await pii_middleware.serialize_message(
                        message=report_prompt,
                        conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                        user_id=request.user_id,
                        mode=protection_mode
                    )
                    pii_context['protection_mode'] = protection_mode  # Add mode info to context
                except Exception as e:
                    logger.error(f"PII serialization failed: {e}")
                    # Continue without serialization on error

            # Prepare LLM options with higher max_tokens for comprehensive reports
            report_llm_options = {
                'num_predict': llm_config.get('report_max_tokens', 8192),  # Higher limit for detailed reports
                'temperature': llm_config.get('temperature', 0.7),
            }
            logger.info(f"🔍 Report generation: num_predict={report_llm_options['num_predict']}, model={model_name}")

            result = await ollama_client.generate(model_name, report_prompt, report_llm_options)

            # Strip <think> tags from response (internal reasoning not shown to user)
            import re
            raw_response = result.get("response", "")
            # Remove complete think blocks
            clean_response = re.sub(r'<think>.*?</think>\s*', '', raw_response, flags=re.DOTALL)
            # Remove orphaned/malformed think tags (opening or closing without pair)
            clean_response = re.sub(r'</?think>\s*', '', clean_response, flags=re.DOTALL)
            # Remove "User:" and "Bee:" labels that the model might echo back
            clean_response = re.sub(r'^User:\s*.*?\n\nBee:\s*', '', clean_response, flags=re.DOTALL | re.MULTILINE)
            clean_response = re.sub(r'^User:\s*', '', clean_response, flags=re.MULTILINE)
            clean_response = re.sub(r'^Bee:\s*', '', clean_response, flags=re.MULTILINE)
            # Clean up stray punctuation marks that might be left behind
            clean_response = re.sub(r'^\s*[,)}\]]\s*', '', clean_response, flags=re.MULTILINE)  # Remove leading punctuation
            clean_response = re.sub(r'\n\s*[,)}\]]\s*\n', '\n', clean_response)  # Remove punctuation on its own line
            clean_response = re.sub(r'\s+([,)}\]])\s+', r'\1 ', clean_response)  # Fix spacing around punctuation

            # Remove LaTeX notation and mathematical formatting (reports should be plain prose)
            clean_response = re.sub(r'\\boxed\{([^}]*)\}', r'\1', clean_response)  # Remove \boxed{content} -> content
            clean_response = re.sub(r'\\text\{([^}]*)\}', r'\1', clean_response)  # Remove \text{content} -> content
            clean_response = re.sub(r'\$\$[^$]*\$\$', '', clean_response)  # Remove display math $$...$$
            clean_response = re.sub(r'\$[^$]*\$', '', clean_response)  # Remove inline math $...$
            clean_response = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean_response)  # Remove other LaTeX commands
            clean_response = re.sub(r'Final Answer[:\s]*', '', clean_response, flags=re.IGNORECASE)  # Remove "Final Answer:" prefix

            # PII Protection: Deserialize response with enhanced metadata for visual indicators
            pii_protected_metadata = None
            if pii_middleware and pii_context:
                try:
                    # Try enhanced deserialization with metadata
                    if hasattr(pii_middleware, 'deserialize_response_with_metadata'):
                        clean_response, deser_metadata = await pii_middleware.deserialize_response_with_metadata(
                            response=clean_response,
                            context=pii_context,
                            enable_diagnostics=True,
                            track_positions=True
                        )

                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': deser_metadata.get('tokens_replaced', 0),
                            'protection_quality': 'complete' if deser_metadata.get('tokens_missed', 0) == 0 else 'partial',
                            'pii_annotations': deser_metadata.get('pii_metadata', [])
                        }
                    else:
                        # Fallback to basic deserialization
                        clean_response = await pii_middleware.deserialize_response(
                            response=clean_response,
                            context=pii_context
                        )
                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': pii_context.get('pii_count', 0),
                            'protection_quality': 'unknown',
                            'pii_annotations': []
                        }
                except Exception as e:
                    logger.error(f"PII deserialization failed: {e}")
                    pii_protected_metadata = {
                        'protection_active': True,
                        'protection_quality': 'failed',
                        'error': str(e)
                    }

            return {
                "response": clean_response.strip(),
                "conversation_id": request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "bee_personality": "professional_analyst",
                "tools_used": ["report_generator"],
                "processing_time": result.get('total_duration', 0) / 1e9,
                "report_generated": True,
                "report_metadata": {
                    "type": "conversational_report",
                    "model": model_name,
                    "tokens_used": result.get("eval_count", 0),
                    "privacy_level": "high" if not request.encryption_required else "maximum"
                },
                "pii_protection": pii_protected_metadata  # NEW: PII metadata for frontend visual indicators
            }
        else:
            # Handle as regular conversation
            # Check if this is a Nectar Bot request with custom system prompt
            bot_context = request.context.get('bot_context') if request.context else None
            nectar_bot_system_prompt = None
            if bot_context and bot_context.get('is_nectar_bot'):
                nectar_bot_system_prompt = bot_context.get('system_prompt')
                logger.info(f"Using Nectar Bot system prompt for bot: {bot_context.get('bot_name')}")

            # Use the BeeContextManager to build enhanced prompt with honey jar context AND conversation history
            enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
                request.message,
                request.user_id,
                conversation_id=request.conversation_id,  # Pass conversation_id to load history from Redis
                conversation_history=None,  # Will be loaded from Redis automatically
                honey_jar_id=request.honey_jar_id,
                custom_system_prompt=nectar_bot_system_prompt  # Pass custom prompt for Nectar Bots
            )

            # Save user message to conversation history
            if request.conversation_id:
                await bee_context_manager.save_message_to_history(
                    conversation_id=request.conversation_id,
                    user_id=request.user_id,
                    role="user",
                    content=request.message
                )

            # PII Protection: Serialize before sending to LLM
            pii_context = {}
            protection_mode = "external"  # Default fallback
            if pii_middleware:
                try:
                    # Intelligent mode detection based on endpoint and context
                    if mode_detector:
                        protection_mode, mode_config = mode_detector.detect_mode(
                            endpoint_url=OLLAMA_BASE_URL,
                            provider="ollama",
                            context="chat",  # Chat context
                            user_role=request.user_role or "user"
                        )
                        logger.info(f"PII protection mode for chat: {protection_mode} (level: {mode_config.get('protection_level')})")

                    enhanced_prompt, pii_context = await pii_middleware.serialize_message(
                        message=enhanced_prompt,
                        conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                        user_id=request.user_id,
                        mode=protection_mode
                    )
                    pii_context['protection_mode'] = protection_mode  # Add mode info to context
                except Exception as e:
                    logger.error(f"PII serialization failed: {e}")
                    # Continue without serialization on error

            # Prepare LLM options with max_tokens from config
            llm_options = {
                'num_predict': llm_config.get('max_tokens', 4096),
                'temperature': llm_config.get('temperature', 0.7),
            }

            result = await ollama_client.generate(model_name, enhanced_prompt, llm_options)

            # Strip <think> tags and reasoning explanations from response (internal reasoning not shown to user)
            import re
            raw_response = result.get("response", "")
            # Remove everything between <think> and </think> tags, including the tags
            clean_response = re.sub(r'<think>.*?</think>\s*', '', raw_response, flags=re.DOTALL)
            # Remove orphaned/malformed think tags (opening or closing without pair)
            clean_response = re.sub(r'</?think>\s*', '', clean_response, flags=re.DOTALL)
            # Also remove "Explanation:" sections that Phi-4 sometimes adds
            clean_response = re.sub(r'\n\s*Explanation:.*', '', clean_response, flags=re.DOTALL)
            # Remove "Reasoning:" sections too
            clean_response = re.sub(r'\n\s*Reasoning:.*', '', clean_response, flags=re.DOTALL)
            # Remove "User:" and "Bee:" labels that the model might echo back
            clean_response = re.sub(r'^User:\s*.*?\n\nBee:\s*', '', clean_response, flags=re.DOTALL | re.MULTILINE)
            clean_response = re.sub(r'^User:\s*', '', clean_response, flags=re.MULTILINE)
            clean_response = re.sub(r'^Bee:\s*', '', clean_response, flags=re.MULTILINE)
            # Clean up stray punctuation marks that might be left behind
            clean_response = re.sub(r'^\s*[,)}\]]\s*', '', clean_response, flags=re.MULTILINE)  # Remove leading punctuation
            clean_response = re.sub(r'\n\s*[,)}\]]\s*\n', '\n', clean_response)  # Remove punctuation on its own line
            clean_response = re.sub(r'\s+([,)}\]])\s+', r'\1 ', clean_response)  # Fix spacing around punctuation

            # Remove LaTeX notation and mathematical formatting (reports should be plain prose)
            clean_response = re.sub(r'\\boxed\{([^}]*)\}', r'\1', clean_response)  # Remove \boxed{content} -> content
            clean_response = re.sub(r'\\text\{([^}]*)\}', r'\1', clean_response)  # Remove \text{content} -> content
            clean_response = re.sub(r'\$\$[^$]*\$\$', '', clean_response)  # Remove display math $$...$$
            clean_response = re.sub(r'\$[^$]*\$', '', clean_response)  # Remove inline math $...$
            clean_response = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean_response)  # Remove other LaTeX commands
            clean_response = re.sub(r'Final Answer[:\s]*', '', clean_response, flags=re.IGNORECASE)  # Remove "Final Answer:" prefix

            # PII Protection: Deserialize response with enhanced metadata for visual indicators
            pii_protected_metadata = None
            if pii_middleware and pii_context:
                try:
                    # Try enhanced deserialization with metadata
                    if hasattr(pii_middleware, 'deserialize_response_with_metadata'):
                        clean_response, deser_metadata = await pii_middleware.deserialize_response_with_metadata(
                            response=clean_response,
                            context=pii_context,
                            enable_diagnostics=True,
                            track_positions=True
                        )

                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': deser_metadata.get('tokens_replaced', 0),
                            'protection_quality': 'complete' if deser_metadata.get('tokens_missed', 0) == 0 else 'partial',
                            'pii_annotations': deser_metadata.get('pii_metadata', [])
                        }
                    else:
                        # Fallback to basic deserialization
                        clean_response = await pii_middleware.deserialize_response(
                            response=clean_response,
                            context=pii_context
                        )
                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': pii_context.get('pii_count', 0),
                            'protection_quality': 'unknown',
                            'pii_annotations': []
                        }
                except Exception as e:
                    logger.error(f"PII deserialization failed: {e}")
                    pii_protected_metadata = {
                        'protection_active': True,
                        'protection_quality': 'failed',
                        'error': str(e)
                    }

            # Save assistant response to conversation history
            conversation_id = request.conversation_id or f"conv_{int(datetime.now().timestamp())}"
            if conversation_id:
                await bee_context_manager.save_message_to_history(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    role="assistant",
                    content=clean_response.strip()
                )

            return {
                "response": clean_response.strip(),
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "tools_used": request.tools_enabled,
                "processing_time": result.get('total_duration', 0) / 1e9,
                "report_generated": False,
                "pii_protection": pii_protected_metadata  # NEW: PII metadata for frontend visual indicators
            }
            
    except Exception as e:
        logger.error(f"Failed to process Bee chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/sync")
async def sync_knowledge(request: KnowledgeSyncRequest):
    """Sync knowledge base with local AI"""
    try:
        if request.targetProvider == "ollama":
            # Check Ollama status
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # Simulate knowledge sync process
            data_size = len(json.dumps(request.data))
            
            # In a real implementation, this would:
            # 1. Process the knowledge data
            # 2. Create embeddings using Ollama
            # 3. Store in vector database
            # 4. Update knowledge base
            
            return {
                "syncId": f"sync_{int(datetime.now().timestamp())}",
                "status": "completed",
                "targetProvider": request.targetProvider,
                "syncType": request.syncType,
                "dataSize": f"{data_size / 1024:.2f} KB",
                "documentsProcessed": len(request.data.get("honeyJars", [])) + len(request.data.get("reports", [])),
                "processingTime": "2.3 seconds",
                "completedAt": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {request.targetProvider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to sync knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for documents"""
    try:
        if request.provider == "ollama":
            # Check Ollama status
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # In a real implementation, this would use Ollama's embedding model
            # For now, return mock embeddings
            embeddings = []
            for i, doc in enumerate(request.documents):
                embeddings.append({
                    "document": doc[:100] + "..." if len(doc) > 100 else doc,
                    "embedding": [0.1] * 384,  # Mock 384-dimensional embedding
                    "index": i
                })
            
            return {
                "embeddings": embeddings,
                "model": request.model,
                "dimensions": 384,
                "processingTime": f"{len(request.documents) * 0.1:.1f} seconds",
                "provider": request.provider
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {request.provider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status/{request_id}")
async def get_queue_status(request_id: str):
    """Get status of a queued request"""
    status = await queue_manager.get_request_status(request_id)
    
    if status:
        return status
    else:
        raise HTTPException(status_code=404, detail="Request not found")

@app.get("/queue/stats")
async def get_queue_stats():
    """Get overall queue statistics"""
    return await queue_manager.get_queue_stats()

@app.post("/queue/cancel/{request_id}")
async def cancel_request(request_id: str):
    """Cancel a queued request"""
    success = await queue_manager.cancel_request(request_id)
    
    if success:
        return {"message": f"Request {request_id} cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Request not found or already processing")

@app.post("/admin/index-knowledge")
async def trigger_indexing():
    """Manually trigger knowledge indexing (admin endpoint)"""
    try:
        if not bee_context_manager.knowledge_indexer or not bee_context_manager.knowledge_indexer.enabled:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        # Get current stats
        stats = bee_context_manager.knowledge_indexer.get_stats()
        current_count = stats.get('document_count', 0)

        # Clear existing collection
        if current_count > 0:
            logger.info(f"Clearing existing {current_count} documents...")
            bee_context_manager.knowledge_indexer.clear_collection()

        # Load brain knowledge
        brain_knowledge = await bee_context_manager.load_brain_knowledge()

        # Trigger background indexing
        asyncio.create_task(index_knowledge_background(brain_knowledge))

        return {
            "status": "indexing_started",
            "message": "Knowledge indexing started in background",
            "previous_count": current_count,
            "check_status_url": "/admin/index-status"
        }

    except Exception as e:
        logger.error(f"Failed to trigger indexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/index-status")
async def get_index_status():
    """Get current indexing status"""
    try:
        if not bee_context_manager.knowledge_indexer or not bee_context_manager.knowledge_indexer.enabled:
            return {
                "status": "disabled",
                "message": "ChromaDB not available"
            }

        stats = bee_context_manager.knowledge_indexer.get_stats()

        return {
            "status": "active" if stats.get('document_count', 0) > 0 else "empty",
            "document_count": stats.get('document_count', 0),
            "collection_name": stats.get('collection_name'),
            "semantic_search_enabled": stats.get('document_count', 0) > 0
        }

    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/search")
async def search_knowledge(request: Dict[str, Any]):
    """Search knowledge base"""
    try:
        query = request.get("query", "")
        provider = request.get("provider", "ollama")
        limit = request.get("limit", 10)
        
        if provider == "ollama":
            # Mock search results
            results = [
                {
                    "content": f"Knowledge about {query} from honey jar data",
                    "score": 0.95,
                    "source": "honey_jar_1"
                },
                {
                    "content": f"Related information on {query} patterns",
                    "score": 0.87,
                    "source": "report_analysis"
                },
                {
                    "content": f"Historical data regarding {query} trends",
                    "score": 0.82,
                    "source": "historical_logs"
                }
            ]
            
            return {
                "query": query,
                "results": results[:limit],
                "totalResults": len(results),
                "searchTime": "0.234 seconds",
                "provider": provider,
                "knowledgeBaseVersion": "1.2.3"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to search knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Queue worker logic
async def process_queue_worker():
    """Background worker to process queued requests"""
    logger.info("Starting queue worker...")
    
    while True:
        try:
            # Get next request from queue
            request = await queue_manager.get_next_request()
            
            if request:
                logger.info(f"Processing request {request.request_id} of type {request.request_type}")
                
                try:
                    # Route to appropriate handler based on request type
                    if request.request_type == "chat":
                        result = await process_chat_request(request)
                    elif request.request_type == "report":
                        result = await process_report_request(request)
                    elif request.request_type == "embedding":
                        result = await process_embedding_request(request)
                    else:
                        raise Exception(f"Unknown request type: {request.request_type}")
                    
                    # Mark as complete
                    await queue_manager.mark_request_complete(request, result)
                    
                except Exception as e:
                    logger.error(f"Error processing request {request.request_id}: {e}")
                    
                    # Retry logic
                    if request.retry_count < 3:
                        request.retry_count += 1
                        await queue_manager.enqueue_request(
                            request.user_id,
                            request.user_role,
                            request.request_type,
                            request.payload,
                            priority_boost=1  # Boost priority for retries
                        )
                        logger.info(f"Requeued request {request.request_id} (retry {request.retry_count})")
                    else:
                        await queue_manager.mark_request_complete(request, None, str(e))
            else:
                # No requests in queue, wait a bit
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Queue worker error: {e}")
            await asyncio.sleep(1)  # Back off on error

async def process_chat_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process a chat request"""
    payload = request.payload
    message = payload.get("message", "")
    
    # Check if this is a report request
    report_keywords = ["generate report", "create report", "report on", "analyze", "summary report", "detailed analysis"]
    is_report_request = any(keyword in message.lower() for keyword in report_keywords)
    
    if is_report_request:
        # Handle as report with enhanced formatting
        report_prompt = f"""{message}

Since this is a report request, please generate a comprehensive report that includes:

1. **Executive Summary**
   - Brief overview of the analysis
   - Key findings at a glance

2. **Detailed Analysis**
   - In-depth examination of the topic
   - Data points and insights
   - Technical details where relevant

3. **Recommendations**
   - Actionable next steps
   - Best practices
   - Risk mitigation strategies

4. **Conclusion**
   - Summary of key takeaways
   - Future considerations

Format the response as a structured report with clear sections and professional tone.
Include relevant security considerations where applicable.
"""
        # Get available models and use the appropriate one
        models = await ollama_client.get_models()
        if not models:
            raise HTTPException(status_code=503, detail="No Ollama models available")
        
        default_model = AI_PROVIDERS["ollama"]["defaultModel"]
        available_models = [m["name"] for m in models]
        
        if default_model not in available_models:
            model = available_models[0]
            logger.warning(f"Default model '{default_model}' not found, using {model}")
        else:
            model = default_model
            
        result = await ollama_client.generate(model, report_prompt)
        
        return {
            "response": result.get("response", ""),
            "conversation_id": payload.get("conversation_id") or f"conv_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "bee_personality": "professional_analyst",
            "tools_used": ["report_generator"],
            "processing_time": result.get('total_duration', 0) / 1e9,
            "report_generated": True,
            "report_metadata": {
                "type": "conversational_report",
                "model": model,
                "tokens_used": result.get("eval_count", 0),
                "privacy_level": "high" if not payload.get("encryption_required") else "maximum"
            }
        }
    else:
        # Handle as regular conversation using BeeContextManager for enhanced context
        enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
            payload.get("message", ""),
            payload.get("user_id", "anonymous"),
            conversation_history=None,  # Could pass history if available
            honey_jar_id=payload.get("honey_jar_id")
        )
        
        # Get available models and use the appropriate one
        models = await ollama_client.get_models()
        if not models:
            raise HTTPException(status_code=503, detail="No Ollama models available")
        
        default_model = AI_PROVIDERS["ollama"]["defaultModel"]
        available_models = [m["name"] for m in models]
        
        if default_model not in available_models:
            model = available_models[0]
            logger.warning(f"Default model '{default_model}' not found, using {model}")
        else:
            model = default_model
            
        result = await ollama_client.generate(model, enhanced_prompt)
        
        return {
            "response": result.get("response", ""),
            "conversation_id": payload.get("conversation_id") or f"conv_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "tools_used": payload.get("tools_enabled", []),
            "processing_time": result.get('total_duration', 0) / 1e9,  # Return numeric value, not string
            "report_generated": False
        }

async def process_report_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process a report generation request"""
    payload = request.payload
    
    # Similar to existing report generation logic
    prompt = f"""CRITICAL INSTRUCTION: Generate an EXTREMELY comprehensive, detailed report. This is a professional-grade analytical document that must be thorough and exhaustive. DO NOT write a brief summary - this requires substantial depth and analysis.

REPORT REQUIREMENTS:
- Template: {payload.get('templateId')}
- Data Sources: {', '.join(payload.get('dataSources', []))}
- Privacy Level: {payload.get('privacyLevel')}
- Required Fields: {json.dumps(payload.get('requiredFields', {}), indent=2)}

MANDATORY SECTIONS (Each section must be detailed and comprehensive):

1. EXECUTIVE SUMMARY (minimum 500 words)
   - Provide a thorough overview covering all key aspects
   - Include context, scope, and high-level findings
   - Summarize critical insights and recommendations
   - DO NOT make this brief - it should be substantial

2. DETAILED FINDINGS (minimum 2000 words)
   - Present comprehensive analysis of all data sources
   - Include specific examples, metrics, and observations
   - Break down findings by category with detailed subsections
   - Provide context and interpretation for each finding
   - Include quantitative and qualitative analysis

3. IN-DEPTH TECHNICAL ANALYSIS (minimum 2000 words)
   - Conduct thorough examination of technical aspects
   - Analyze patterns, trends, and correlations
   - Discuss methodology and analytical approaches
   - Present detailed evidence supporting conclusions
   - Include comparative analysis where relevant

4. COMPREHENSIVE RECOMMENDATIONS (minimum 1500 words)
   - Provide detailed, actionable recommendations
   - Explain rationale and expected outcomes for each
   - Include implementation considerations and priorities
   - Discuss potential challenges and mitigation strategies
   - Present both short-term and long-term recommendations

5. RISK ASSESSMENT & CONSIDERATIONS (minimum 1000 words)
   - Analyze potential risks and vulnerabilities
   - Evaluate likelihood and impact of identified risks
   - Discuss compliance and regulatory considerations
   - Provide risk mitigation strategies

6. CONCLUSION & NEXT STEPS (minimum 500 words)
   - Synthesize key points from the entire analysis
   - Provide clear, actionable next steps
   - Include timeline and resource considerations
   - Summarize critical takeaways

WRITING REQUIREMENTS:
- Write in a professional, analytical tone
- Use specific examples and concrete details throughout
- Include relevant technical terminology appropriately
- Structure with clear headings and subheadings
- Ensure logical flow between sections
- Maintain depth and substance in every section
- DO NOT stop writing until all sections are thoroughly covered
- Target total length: 10,000+ words for comprehensive coverage

BEGIN COMPREHENSIVE REPORT:
"""
    
    # Get available models and use the appropriate one
    models = await ollama_client.get_models()
    if not models:
        raise HTTPException(status_code=503, detail="No Ollama models available")

    # Use report-specific model from config
    report_model = llm_config.get('report_model', AI_PROVIDERS["ollama"]["defaultModel"])
    report_fallback = llm_config.get('report_fallback_model', AI_PROVIDERS["ollama"]["defaultModel"])
    available_models = [m["name"] for m in models]

    # Try report model first, then fallback, then first available
    if report_model in available_models:
        model = report_model
        logger.info(f"Using configured report model: {model}")
    elif report_fallback in available_models:
        model = report_fallback
        logger.warning(f"Report model '{report_model}' not found, using fallback: {model}")
    else:
        model = available_models[0]
        logger.warning(f"Neither report model '{report_model}' nor fallback found, using: {model}")

    # Prepare options with report-specific max_tokens
    report_max_tokens = llm_config.get('report_max_tokens', 8192)
    options = {
        "num_predict": report_max_tokens,
        "temperature": 0.7
    }
    logger.info(f"Report generation: model={model}, max_tokens={report_max_tokens}")

    result = await ollama_client.generate(model, prompt, options)
    
    return {
        "reportId": f"report_{request.request_id}",
        "content": result.get("response", ""),
        "model": model,
        "tokensUsed": result.get("eval_count", 0),
        "processingTime": result.get('total_duration', 0) / 1e9
    }

async def process_embedding_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process an embedding request"""
    # Placeholder for embedding logic
    return {
        "embeddings": [],
        "model": "nomic-embed-text",
        "dimensions": 384
    }

async def index_knowledge_background(brain_knowledge: str):
    """Background task to index knowledge in ChromaDB without blocking startup"""
    try:
        is_indexing.set()  # Mark indexing as in progress
        logger.info("🔄 Background indexing started...")

        # Delay to ensure service is fully started
        await asyncio.sleep(5)

        # Index brain knowledge with progress updates
        if brain_knowledge:
            logger.info(f"📖 Indexing brain knowledge ({len(brain_knowledge)} chars)...")
            logger.info("⏳ This may take 30-60 seconds for embedding generation...")

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                bee_context_manager.knowledge_indexer.index_brain_knowledge,
                brain_knowledge
            )

            if success:
                logger.info("✅ Brain knowledge indexed successfully")
            else:
                logger.error("❌ Failed to index brain knowledge")

            # Small delay between brain and docs indexing
            await asyncio.sleep(2)

        # Index documentation
        from pathlib import Path
        docs_path = Path(__file__).parent.parent / "docs"
        if docs_path.exists():
            logger.info("📚 Indexing documentation...")
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                bee_context_manager.knowledge_indexer.index_documentation,
                docs_path
            )
            if success:
                logger.info("✅ Documentation indexed successfully")
            else:
                logger.warning("⚠️  Documentation indexing incomplete")

        # Show final stats
        stats = bee_context_manager.knowledge_indexer.get_stats()
        logger.info(f"🎉 Indexing complete! {stats.get('document_count', 0)} document chunks indexed")

    except Exception as e:
        logger.error(f"Background indexing failed: {e}", exc_info=True)
    finally:
        is_indexing.clear()  # Clear indexing flag when done

async def pii_cache_cleanup_task(cache_manager):
    """
    Background task to maintain PII cache health.
    Runs cleanup every 5 minutes to remove expired entries.
    """
    logger.info("🧹 PII cache cleanup task started")
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes (matches config cleanup interval)
            await cache_manager.cleanup_expired()
            logger.debug("PII cache cleanup completed")
        except asyncio.CancelledError:
            logger.info("PII cache cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"PII cache cleanup error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global worker_task, pii_middleware

    # Initialize queue manager
    await queue_manager.initialize()

    # Upgrade PII middleware to enhanced mode with async components
    if pii_middleware and EnhancedDeserializer and ImprovedCacheManager and app_config:
        try:
            # Get Redis configuration from config
            redis_db = app_config.get('security', {}).get('message_pii_protection', {}).get('serialization', {}).get('redis_db', 3)
            redis_url = f"redis://redis:6379/{redis_db}"

            # Initialize improved cache manager with async connection
            improved_cache = ImprovedCacheManager(redis_url=redis_url)
            await improved_cache.connect()

            # Replace with enhanced deserializer
            pii_middleware.deserializer = EnhancedDeserializer(improved_cache)
            pii_middleware.cache_manager = improved_cache

            logger.info("✨ Enhanced PII middleware activated: position tracking + visual indicators enabled")

            # Start background cache cleanup task
            asyncio.create_task(pii_cache_cleanup_task(improved_cache))
        except Exception as enhance_error:
            logger.warning(f"Failed to upgrade to enhanced PII components: {enhance_error}")
            logger.info("Continuing with basic PII middleware")

    # Initialize Bee Context Manager and load brain knowledge
    logger.info("Loading Bee Brain knowledge into memory...")
    brain_knowledge = await bee_context_manager.load_brain_knowledge()
    if brain_knowledge:
        logger.info(f"✅ Bee Brain loaded successfully: {len(brain_knowledge)} characters")
    else:
        logger.warning("⚠️ Bee Brain knowledge not loaded - using fallback mode")

    # Start queue worker
    worker_task = asyncio.create_task(process_queue_worker())

    # ChromaDB semantic search - auto-index in background with batching
    if bee_context_manager.knowledge_indexer and bee_context_manager.knowledge_indexer.enabled:
        try:
            stats = bee_context_manager.knowledge_indexer.get_stats()
            doc_count = stats.get('document_count', 0)
            logger.info(f"📊 ChromaDB status: {doc_count} document chunks indexed")

            # Disabled auto-indexing for testing - use POST /admin/index-knowledge to index manually
            if doc_count == 0:
                logger.warning("📚 ChromaDB not indexed. Use POST /admin/index-knowledge to index manually.")
            else:
                logger.info(f"✅ ChromaDB already contains {doc_count} documents, semantic search enabled")
        except Exception as e:
            logger.warning(f"ChromaDB check failed: {e}. Using keyword fallback.")

    logger.info("External AI Service started successfully with Bee Brain system")
    
    # Check Ollama models on startup
    try:
        models = await ollama_client.get_models()
        if models:
            model_names = [m["name"] for m in models]
            logger.info(f"Available Ollama models: {model_names}")
            
            # Check if default model is available
            default_model = AI_PROVIDERS["ollama"]["defaultModel"]
            if default_model not in model_names:
                logger.warning(f"⚠️  Default model '{default_model}' not found!")
                logger.warning(f"📌 To install it, run: ollama pull {default_model.split(':')[0]}")
                logger.info(f"🔄 Will use fallback model: {model_names[0] if model_names else 'none'}")
        else:
            logger.error("❌ No Ollama models found!")
            logger.error("📌 Please install at least one model:")
            logger.error("   - For general use: ollama pull llama3.3")
            logger.error("   - For code tasks: ollama pull deepseek-coder-v2")
            logger.error("   - For smaller model: ollama pull phi3")
    except Exception as e:
        logger.error(f"⚠️  Could not check Ollama models: {e}")
        logger.error("📌 Make sure Ollama is running: ollama serve")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global worker_task
    
    # Cancel worker task
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    
    # Close queue manager
    await queue_manager.close()
    
    logger.info("External AI Service shut down")

if __name__ == "__main__":
    logger.info(f"Starting STING External AI Service on {SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"Ollama endpoint: {OLLAMA_BASE_URL}")
    
    uvicorn.run(
        app,
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        log_level="info"
    )