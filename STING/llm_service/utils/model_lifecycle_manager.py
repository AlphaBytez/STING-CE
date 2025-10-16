"""
Model Lifecycle Manager
Handles dynamic loading/unloading of models with idle timeout and memory management
"""

import os
import time
import logging
import threading
import torch
import gc
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from transformers import AutoTokenizer, AutoModelForCausalLM
import yaml

logger = logging.getLogger(__name__)


class ModelInfo:
    """Tracks model state and usage"""
    def __init__(self, name: str, path: str, priority: int = 10):
        self.name = name
        self.path = path
        self.priority = priority
        self.last_used = time.time()
        self.load_count = 0
        self.is_loaded = False
        self.model = None
        self.tokenizer = None
        self.lock = threading.Lock()


class ModelLifecycleManager:
    """Manages dynamic model loading/unloading with configurable policies"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Extract lifecycle settings
        lifecycle_config = self.config.get('llm_service', {}).get('model_lifecycle', {})
        self.lazy_loading = lifecycle_config.get('lazy_loading', True)
        self.idle_timeout_minutes = lifecycle_config.get('idle_timeout', 30)
        self.max_loaded_models = lifecycle_config.get('max_loaded_models', 2)
        self.preload_on_startup = lifecycle_config.get('preload_on_startup', False)
        self.development_mode = lifecycle_config.get('development_mode', False)
        self.model_priorities = lifecycle_config.get('model_priorities', {})
        
        # Model registry
        self.models: Dict[str, ModelInfo] = {}
        self._initialize_models()
        
        # Cleanup thread
        self.cleanup_thread = None
        self.stop_cleanup = threading.Event()
        
        # Global lock for model operations
        self.global_lock = threading.Lock()
        
        # Start cleanup thread if not in development mode
        if not self.development_mode and self.idle_timeout_minutes > 0:
            self._start_cleanup_thread()
            
        # Preload models if configured
        if self.preload_on_startup:
            self._preload_models()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_path is None:
            possible_paths = [
                '/app/conf/config.yml',
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'conf', 'config.yml'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'conf', 'config.yml'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        # Return default config
        return {
            'llm_service': {
                'model_lifecycle': {
                    'lazy_loading': True,
                    'idle_timeout': 30,
                    'max_loaded_models': 2,
                    'preload_on_startup': False,
                    'development_mode': False
                }
            }
        }
    
    def _initialize_models(self):
        """Initialize model registry from config"""
        models_config = self.config.get('llm_service', {}).get('models', {})
        
        # Get base models directory from environment or config
        models_base_dir = os.getenv('STING_MODELS_DIR', '/Users/captain-wolf/Downloads/llm_models')
        
        # Check environment variables for model paths first (higher priority)
        env_model_path = os.getenv('MODEL_PATH')
        env_model_name = os.getenv('MODEL_NAME', 'tinyllama')
        
        if env_model_path:
            # Check if it's a HuggingFace model name (contains slash or is a known HF model)
            if '/' in env_model_path or not env_model_path.startswith('/'):
                # Use HuggingFace model name directly
                path = env_model_path
                priority = self.model_priorities.get(env_model_name, 1)
                self.models[env_model_name] = ModelInfo(env_model_name, path, priority)
                logger.info(f"Using HuggingFace model from environment: {env_model_name} -> {path}")
            else:
                # Local path
                priority = self.model_priorities.get(env_model_name, 1)
                self.models[env_model_name] = ModelInfo(env_model_name, env_model_path, priority)
                logger.info(f"Using local model from environment: {env_model_name} -> {env_model_path}")
        
        # Model name to path mapping (fallback for local directory scanning)
        model_paths = {
            'tinyllama': 'TinyLlama-1.1B-Chat',  # Use actual TinyLlama model
            'llama3': 'DeepSeek-R1-Distill-Qwen-1.5B',  # Map llama3 to working DeepSeek model
            'phi2': 'phi-2',
            'phi3': 'phi-3-mini-4k',
            'phi3_mini': 'phi-3-mini-4k',
            'zephyr': 'zephyr-7b',
            'dialogpt': 'DialoGPT-medium',
            'deepseek-1.5b': 'DeepSeek-R1-Distill-Qwen-1.5B'
        }
        
        # Only scan local directory if no environment model path is set
        if not env_model_path:
            logger.info("Registering available models from local directory")
            for model_name, model_subdir in model_paths.items():
                path = os.path.join(models_base_dir, model_subdir)
                if os.path.exists(path):
                    priority = self.model_priorities.get(model_name, 10)
                    self.models[model_name] = ModelInfo(model_name, path, priority)
                    logger.info(f"Registered model: {model_name} at {path} (priority: {priority})")
                else:
                    logger.debug(f"Model {model_name} not found at {path}, skipping")
        
        # Also register models from config if available (but don't override environment models)
        if models_config and not env_model_path:
            for model_name, model_cfg in models_config.items():
                if model_cfg.get('enabled', True) and model_name not in self.models:
                    # Use path from config directly - it should be a HuggingFace model ID
                    path = model_cfg.get('path', f'{model_name}')
                    
                    # Only convert to local path if it starts with /app/models/ (Docker path)
                    if path.startswith('/app/models/'):
                        model_subdir = path.replace('/app/models/', '')
                        local_path = os.path.join(models_base_dir, model_subdir)
                        # Check if local model exists, otherwise use HF model ID
                        if os.path.exists(local_path):
                            path = local_path
                        else:
                            # Assume it's a HuggingFace model ID
                            logger.info(f"Local model not found at {local_path}, will use HuggingFace model")
                    
                    priority = self.model_priorities.get(model_name, 10)
                    self.models[model_name] = ModelInfo(model_name, path, priority)
                    logger.info(f"Registered model from config: {model_name} at {path} (priority: {priority})")
    
    def _start_cleanup_thread(self):
        """Start background thread for idle model cleanup"""
        def cleanup_loop():
            while not self.stop_cleanup.is_set():
                try:
                    self._cleanup_idle_models()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
                
                # Check every minute
                self.stop_cleanup.wait(60)
        
        self.cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("Started model cleanup thread")
    
    def _cleanup_idle_models(self):
        """Unload models that have been idle too long"""
        if self.development_mode or self.idle_timeout_minutes <= 0:
            return
            
        current_time = time.time()
        idle_threshold = current_time - (self.idle_timeout_minutes * 60)
        
        with self.global_lock:
            for model_name, model_info in self.models.items():
                if model_info.is_loaded and model_info.last_used < idle_threshold:
                    logger.info(f"Unloading idle model: {model_name}")
                    self._unload_model(model_info)
    
    def _preload_models(self):
        """Preload high-priority models on startup"""
        sorted_models = sorted(
            self.models.items(),
            key=lambda x: x[1].priority
        )
        
        loaded_count = 0
        for model_name, model_info in sorted_models:
            if loaded_count >= self.max_loaded_models:
                break
                
            try:
                logger.info(f"Preloading model: {model_name}")
                self._load_model(model_info)
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to preload {model_name}: {e}")
    
    def get_model(self, model_name: str, device: str = "auto", 
                  dtype: Optional[torch.dtype] = None) -> Tuple[Any, Any]:
        """
        Get a model, loading it if necessary
        
        Returns:
            Tuple of (model, tokenizer)
        """
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        
        model_info = self.models[model_name]
        
        with model_info.lock:
            # Update last used time
            model_info.last_used = time.time()
            
            # Load if not already loaded
            if not model_info.is_loaded:
                # Check if we need to evict models first
                self._enforce_model_limit(exclude_model=model_name)
                
                # Load the model
                self._load_model(model_info, device, dtype)
            
            return model_info.model, model_info.tokenizer
    
    def _load_model(self, model_info: ModelInfo, device: str = "auto", 
                    dtype: Optional[torch.dtype] = None):
        """Load a model into memory"""
        logger.info(f"Loading model: {model_info.name} from {model_info.path}")
        
        try:
            # Check if path is local or HuggingFace model ID
            import os
            is_local_path = os.path.isdir(model_info.path)
            
            # Load tokenizer
            if is_local_path:
                # For local paths, ensure we use the absolute path
                model_path = os.path.abspath(model_info.path)
                model_info.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    local_files_only=True,
                    trust_remote_code=True
                )
            else:
                # For HuggingFace model IDs
                model_info.tokenizer = AutoTokenizer.from_pretrained(
                    model_info.path,
                    trust_remote_code=True
                )
            
            # Set chat template for models that need it
            if model_info.name == "llama3" and not model_info.tokenizer.chat_template:
                # Llama 3 chat template
                model_info.tokenizer.chat_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ system_prompt | default('You are a helpful AI assistant.') }}<|eot_id|>

{% for message in messages %}
<|start_header_id|>{{ message["role"] }}<|end_header_id|>

{{ message["content"] }}<|eot_id|>
{% endfor %}

<|start_header_id|>assistant<|end_header_id|>

"""
                logger.info(f"Set chat template for {model_info.name}")
            elif model_info.name == "phi3" and not model_info.tokenizer.chat_template:
                # Phi-3 chat template
                model_info.tokenizer.chat_template = """<|system|>
{{ system_prompt | default('You are a helpful AI assistant.') }}<|end|>
{% for message in messages %}
{% if message['role'] == 'user' %}
<|user|>
{{ message['content'] }}<|end|>
{% elif message['role'] == 'assistant' %}
<|assistant|>
{{ message['content'] }}<|end|>
{% endif %}
{% endfor %}
<|assistant|>
"""
                logger.info(f"Set chat template for {model_info.name}")
            elif model_info.name == "phi2" and not model_info.tokenizer.chat_template:
                # Phi-2 simple chat template
                model_info.tokenizer.chat_template = """{% for message in messages %}{% if message['role'] == 'user' %}Human: {{ message['content'] }}
{% elif message['role'] == 'assistant' %}Assistant: {{ message['content'] }}
{% endif %}{% endfor %}Assistant: """
                logger.info(f"Set chat template for {model_info.name}")
            
            # Determine device
            if device == "auto":
                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"
            
            # Load model with appropriate settings
            model_kwargs = {
                'pretrained_model_name_or_path': model_path if is_local_path else model_info.path,
                'local_files_only': is_local_path,
                'torch_dtype': dtype or torch.float16 if device != "cpu" else torch.float32,
                'low_cpu_mem_usage': True,
                'trust_remote_code': True
            }
            
            # Don't use device_map for MPS
            if device != "mps":
                model_kwargs['device_map'] = device
            
            model_info.model = AutoModelForCausalLM.from_pretrained(**model_kwargs)
            
            # Move to device if MPS
            if device == "mps":
                model_info.model = model_info.model.to(device)
            
            model_info.is_loaded = True
            model_info.load_count += 1
            logger.info(f"Successfully loaded {model_info.name} on {device}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_info.name}: {e}")
            raise
    
    def _unload_model(self, model_info: ModelInfo):
        """Unload a model from memory"""
        if not model_info.is_loaded:
            return
            
        try:
            # Delete model and tokenizer
            if model_info.model is not None:
                del model_info.model
                model_info.model = None
                
            if model_info.tokenizer is not None:
                del model_info.tokenizer
                model_info.tokenizer = None
            
            # Clear CUDA/MPS cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if torch.backends.mps.is_available():
                # MPS doesn't have explicit cache clearing yet
                pass
            
            # Force garbage collection
            gc.collect()
            
            model_info.is_loaded = False
            logger.info(f"Unloaded model: {model_info.name}")
            
        except Exception as e:
            logger.error(f"Error unloading model {model_info.name}: {e}")
    
    def _enforce_model_limit(self, exclude_model: Optional[str] = None):
        """Ensure we don't exceed max loaded models by evicting if necessary"""
        loaded_models = [
            (name, info) for name, info in self.models.items()
            if info.is_loaded and name != exclude_model
        ]
        
        if len(loaded_models) >= self.max_loaded_models:
            # Sort by priority (higher number = lower priority) and last used time
            loaded_models.sort(
                key=lambda x: (x[1].priority, -x[1].last_used),
                reverse=True
            )
            
            # Evict the lowest priority/least recently used model
            model_to_evict = loaded_models[0]
            logger.info(f"Evicting model {model_to_evict[0]} to make room")
            self._unload_model(model_to_evict[1])
    
    def unload_model(self, model_name: str):
        """Manually unload a specific model"""
        if model_name in self.models:
            model_info = self.models[model_name]
            with model_info.lock:
                self._unload_model(model_info)
    
    def get_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently loaded models"""
        result = {}
        for name, info in self.models.items():
            if info.is_loaded:
                result[name] = {
                    'last_used': datetime.fromtimestamp(info.last_used).isoformat(),
                    'load_count': info.load_count,
                    'priority': info.priority
                }
        return result
    
    def shutdown(self):
        """Clean shutdown - unload all models and stop cleanup thread"""
        logger.info("Shutting down ModelLifecycleManager")
        
        # Stop cleanup thread
        if self.cleanup_thread:
            self.stop_cleanup.set()
            self.cleanup_thread.join(timeout=5)
        
        # Unload all models
        with self.global_lock:
            for model_info in self.models.values():
                if model_info.is_loaded:
                    self._unload_model(model_info)


# Global instance
_lifecycle_manager: Optional[ModelLifecycleManager] = None


def get_lifecycle_manager() -> ModelLifecycleManager:
    """Get or create the global lifecycle manager instance"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = ModelLifecycleManager()
    return _lifecycle_manager