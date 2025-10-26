"""
LLM Service Management Routes
Provides API endpoints for managing the native LLM service
"""

import requests
import subprocess
import os
import logging
import threading
import time
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request
from functools import wraps

logger = logging.getLogger(__name__)

# Create blueprint
llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

# Configuration
NATIVE_LLM_URL = os.environ.get('NATIVE_LLM_URL', 'http://localhost:8086')
STING_LLM_SCRIPT = os.environ.get('STING_LLM_SCRIPT', './sting-llm')

# Progress tracking storage (in production, use Redis or database)
progress_storage = {}
progress_lock = threading.Lock()

def require_auth(f):
    """Decorator to require authentication for LLM management endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: Implement proper authentication check
        # For now, we'll allow all requests
        # In production, check if user is authenticated and has admin privileges
        return f(*args, **kwargs)
    return decorated_function

def handle_llm_service_error(func):
    """Decorator to handle LLM service connection errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            return jsonify({
                'error': 'LLM service is not running or not accessible',
                'suggestion': 'Try starting the service with: ./sting-llm start'
            }), 503
        except requests.exceptions.Timeout:
            return jsonify({
                'error': 'LLM service request timed out',
                'suggestion': 'The service may be overloaded. Try again in a moment.'
            }), 504
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            return jsonify({
                'error': 'Internal server error',
                'message': str(e)
            }), 500
    return wrapper

def update_progress(operation_id, status, progress=0, message="", logs=None):
    """Update progress for a long-running operation"""
    with progress_lock:
        if operation_id not in progress_storage:
            progress_storage[operation_id] = {
                'status': 'initializing',
                'progress': 0,
                'message': '',
                'logs': [],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        
        progress_storage[operation_id].update({
            'status': status,
            'progress': min(100, max(0, progress)),
            'message': message,
            'updated_at': datetime.utcnow()
        })
        
        if logs:
            progress_storage[operation_id]['logs'].extend(logs if isinstance(logs, list) else [logs])
            # Keep only last 100 log entries
            progress_storage[operation_id]['logs'] = progress_storage[operation_id]['logs'][-100:]

def load_model_async(model_name, operation_id):
    """Load model asynchronously with progress tracking"""
    try:
        update_progress(operation_id, 'starting', 5, f'Initializing model loading for {model_name}...')
        
        # Start the sting-llm load process
        update_progress(operation_id, 'downloading', 10, 'Starting model download/loading...')
        
        process = subprocess.Popen(
            [STING_LLM_SCRIPT, 'load', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        progress_value = 10
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            
            if output:
                line = output.strip()
                # Parse progress from output
                if 'downloading' in line.lower() or 'fetching' in line.lower():
                    progress_value = min(60, progress_value + 5)
                    update_progress(operation_id, 'downloading', progress_value, 'Downloading model files...', [line])
                elif 'loading' in line.lower() or 'initializing' in line.lower():
                    progress_value = min(85, progress_value + 10)
                    update_progress(operation_id, 'loading', progress_value, 'Loading model into memory...', [line])
                elif 'ready' in line.lower() or 'success' in line.lower():
                    progress_value = 95
                    update_progress(operation_id, 'finalizing', progress_value, 'Finalizing model setup...', [line])
                else:
                    update_progress(operation_id, None, None, None, [line])
        
        rc = process.poll()
        if rc == 0:
            update_progress(operation_id, 'completed', 100, f'Model {model_name} loaded successfully!')
            
            # Verify model is actually loaded
            try:
                response = requests.get(f'{NATIVE_LLM_URL}/models', timeout=10)
                if response.ok:
                    models_data = response.json()
                    loaded_models = models_data.get('loaded_models', {})
                    if model_name in loaded_models:
                        update_progress(operation_id, 'completed', 100, f'Model {model_name} is ready for use!')
                    else:
                        update_progress(operation_id, 'error', 100, f'Model loaded but not found in active models')
            except Exception as e:
                update_progress(operation_id, 'completed', 100, f'Model {model_name} loaded (verification failed: {e})')
        else:
            update_progress(operation_id, 'error', progress_value, f'Failed to load model {model_name}')
            
    except Exception as e:
        logger.error(f"Error in async model loading: {e}")
        update_progress(operation_id, 'error', 0, f'Error loading model: {str(e)}')

@llm_bp.route('/health', methods=['GET'])
@handle_llm_service_error
def health_check():
    """Check LLM service health"""
    response = requests.get(f'{NATIVE_LLM_URL}/health', timeout=10)
    return jsonify(response.json()), response.status_code

@llm_bp.route('/models', methods=['GET'])
@handle_llm_service_error
def get_models():
    """Get available and loaded models"""
    response = requests.get(f'{NATIVE_LLM_URL}/models', timeout=10)
    return jsonify(response.json()), response.status_code

@llm_bp.route('/load', methods=['POST'])
@require_auth
def load_model():
    """Load a specific model asynchronously with progress tracking"""
    data = request.get_json()
    if not data or 'model_name' not in data:
        return jsonify({'error': 'model_name is required'}), 400
    
    model_name = data['model_name']
    operation_id = str(uuid.uuid4())
    
    # Start async loading
    thread = threading.Thread(
        target=load_model_async,
        args=(model_name, operation_id),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'operation_id': operation_id,
        'message': f'Model loading started for {model_name}',
        'status': 'started'
    }), 202

@llm_bp.route('/unload', methods=['POST'])
@require_auth
@handle_llm_service_error
def unload_model():
    """Unload a specific model"""
    data = request.get_json()
    if not data or 'model_name' not in data:
        return jsonify({'error': 'model_name is required'}), 400
    
    model_name = data['model_name']
    response = requests.post(
        f'{NATIVE_LLM_URL}/unload',
        json={'model_name': model_name},
        timeout=15
    )
    return jsonify(response.json()), response.status_code

@llm_bp.route('/progress/<operation_id>', methods=['GET'])
def get_progress(operation_id):
    """Get progress for a specific operation"""
    with progress_lock:
        if operation_id not in progress_storage:
            return jsonify({'error': 'Operation not found'}), 404
        
        progress_data = progress_storage[operation_id].copy()
        
        # Convert datetime to string for JSON serialization
        if 'created_at' in progress_data:
            progress_data['created_at'] = progress_data['created_at'].isoformat()
        if 'updated_at' in progress_data:
            progress_data['updated_at'] = progress_data['updated_at'].isoformat()
        
        return jsonify(progress_data), 200

@llm_bp.route('/progress', methods=['GET'])
def get_all_progress():
    """Get all active operations"""
    with progress_lock:
        result = {}
        for op_id, data in progress_storage.items():
            result[op_id] = {
                'status': data['status'],
                'progress': data['progress'],
                'message': data['message'],
                'created_at': data['created_at'].isoformat(),
                'updated_at': data['updated_at'].isoformat()
            }
        return jsonify(result), 200

@llm_bp.route('/progress/<operation_id>', methods=['DELETE'])
def clear_progress(operation_id):
    """Clear progress data for a specific operation"""
    with progress_lock:
        if operation_id in progress_storage:
            del progress_storage[operation_id]
            return jsonify({'message': 'Progress data cleared'}), 200
        return jsonify({'error': 'Operation not found'}), 404

@llm_bp.route('/restart', methods=['POST'])
@require_auth
def restart_service():
    """Restart the LLM service"""
    try:
        # First, stop the service
        stop_result = subprocess.run(
            [STING_LLM_SCRIPT, 'stop'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if stop_result.returncode != 0:
            logger.warning(f"Stop command returned {stop_result.returncode}: {stop_result.stderr}")
        
        # Then start it again
        start_result = subprocess.run(
            [STING_LLM_SCRIPT, 'start'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if start_result.returncode == 0:
            return jsonify({
                'message': 'LLM service restarted successfully',
                'stdout': start_result.stdout
            }), 200
        else:
            return jsonify({
                'error': 'Failed to restart LLM service',
                'stderr': start_result.stderr,
                'stdout': start_result.stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Restart operation timed out',
            'suggestion': 'Try manually restarting with: ./sting-llm restart'
        }), 504
    except Exception as e:
        logger.error(f"Error restarting LLM service: {e}")
        return jsonify({
            'error': 'Failed to restart LLM service',
            'message': str(e)
        }), 500

@llm_bp.route('/status', methods=['GET'])
@handle_llm_service_error
def get_service_status():
    """Get detailed service status"""
    try:
        # Get basic health
        health_response = requests.get(f'{NATIVE_LLM_URL}/health', timeout=5)
        health_data = health_response.json()
        
        # Get model information
        models_response = requests.get(f'{NATIVE_LLM_URL}/models', timeout=5)
        models_data = models_response.json()
        
        return jsonify({
            'service_healthy': health_response.status_code == 200,
            'uptime': health_data.get('uptime', 0),
            'available_models': models_data.get('available_models', []),
            'loaded_models': models_data.get('loaded_models', {}),
            'default_model': models_data.get('default_model', ''),
            'max_loaded_models': models_data.get('max_loaded_models', 0),
            'idle_timeout_minutes': models_data.get('idle_timeout_minutes', 0)
        }), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            'service_healthy': False,
            'error': 'Service not accessible',
            'available_models': [],
            'loaded_models': {},
            'default_model': '',
            'max_loaded_models': 0,
            'idle_timeout_minutes': 0
        }), 503

@llm_bp.route('/config', methods=['GET'])
@require_auth
def get_config():
    """Get LLM service configuration"""
    try:
        # Read configuration from config.yml
        import yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'conf', 'config.yml')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                llm_config = config.get('llm_service', {})
                
                return jsonify({
                    'models_directory': os.environ.get('STING_MODELS_DIR', '~/.sting-ce/models'),
                    'config_file': config_path,
                    'default_model': llm_config.get('default_model', 'phi3'),
                    'enabled_models': {k: v for k, v in llm_config.get('models', {}).items() if v.get('enabled', False)},
                    'performance_profile': llm_config.get('performance', {}).get('profile', 'vm_optimized'),
                    'model_lifecycle': llm_config.get('model_lifecycle', {}),
                    'hardware_acceleration': llm_config.get('hardware', {})
                }), 200
        else:
            return jsonify({
                'error': 'Configuration file not found',
                'config_file': config_path
            }), 404
            
    except Exception as e:
        logger.error(f"Error reading configuration: {e}")
        return jsonify({
            'error': 'Failed to read configuration',
            'message': str(e)
        }), 500

@llm_bp.route('/chat', methods=['POST'])
@handle_llm_service_error
def chat():
    """Proxy chat requests to the LLM service"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Forward the request to the LLM service
    response = requests.post(
        f'{NATIVE_LLM_URL}/chat',
        json=data,
        timeout=60  # Chat can take longer
    )
    return jsonify(response.json()), response.status_code

# Error handlers
@llm_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@llm_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405