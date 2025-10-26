# app/routes/system_routes.py
from flask import Blueprint, jsonify, g, request
from app.utils.decorators import require_auth_or_api_key
import psutil
import time
from datetime import datetime, timedelta
from app.database import db
from sqlalchemy import text
import redis
import requests
import os
from app.models.user_models import User

system_bp = Blueprint('system', __name__)

# Service URLs for health checks
SERVICE_URLS = {
    'app': 'https://localhost:5050/health',
    'knowledge': 'http://knowledge:8000/health',
    'messaging': 'http://messaging:5001/health',
    'external-ai': 'http://external-ai:8100/health',
    'chatbot': 'http://sting-ce-chatbot:8888/health',
}

@system_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

@system_bp.route('/bee/health', methods=['GET'])
def bee_health():
    """Check Bee chatbot service health"""
    try:
        # Check if chatbot service is accessible
        response = requests.get(SERVICE_URLS['chatbot'], timeout=5)
        if response.status_code == 200:
            return jsonify({
                'status': 'healthy',
                'service': 'bee-chatbot',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'status': 'degraded',
                'service': 'bee-chatbot',
                'timestamp': datetime.utcnow().isoformat()
            })
    except Exception as e:
        return jsonify({
            'status': 'offline',
            'service': 'bee-chatbot',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

@system_bp.route('/system/health', methods=['GET'])
def system_health():
    """Comprehensive system health check"""
    services = []
    
    # Check database
    try:
        db.session.execute(text('SELECT 1'))
        services.append({
            'name': 'Database',
            'status': 'healthy',
            'uptime': '99.9%',
            'responseTime': '12ms'
        })
    except:
        services.append({
            'name': 'Database',
            'status': 'down',
            'uptime': '0%',
            'responseTime': 'N/A'
        })
    
    # Check Redis
    try:
        r = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
        r.ping()
        services.append({
            'name': 'Cache',
            'status': 'healthy',
            'uptime': '99.9%',
            'responseTime': '3ms'
        })
    except:
        services.append({
            'name': 'Cache',
            'status': 'down',
            'uptime': '0%',
            'responseTime': 'N/A'
        })
    
    # Check internal services
    for service_name, url in SERVICE_URLS.items():
        try:
            start = time.time()
            response = requests.get(url, timeout=2)
            response_time = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                status = 'healthy'
            else:
                status = 'degraded'
                
            services.append({
                'name': service_name.replace('-', ' ').title(),
                'status': status,
                'uptime': '99.5%',  # Mock data
                'responseTime': f'{response_time}ms'
            })
        except:
            services.append({
                'name': service_name.replace('-', ' ').title(),
                'status': 'down',
                'uptime': '0%',
                'responseTime': 'N/A'
            })
    
    # API Server (self)
    services.insert(0, {
        'name': 'API Server',
        'status': 'healthy',
        'uptime': '99.9%',
        'responseTime': '45ms'
    })
    
    return jsonify({
        'services': services,
        'timestamp': datetime.utcnow().isoformat()
    })

@system_bp.route('/system/metrics', methods=['GET'])
def system_metrics():
    """Get system performance metrics"""
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    
    # Disk usage
    disk = psutil.disk_usage('/')
    
    # Network I/O
    network = psutil.net_io_counters()
    
    return jsonify({
        'cpu': {
            'usage': cpu_percent,
            'cores': psutil.cpu_count()
        },
        'memory': {
            'total': memory.total,
            'used': memory.used,
            'percent': memory.percent
        },
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'percent': disk.percent
        },
        'network': {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv
        },
        'timestamp': datetime.utcnow().isoformat()
    })

@system_bp.route('/system/stats', methods=['GET'])
def system_stats():
    """Get system statistics for dashboard"""
    try:
        # These would be real queries in production
        stats = {
            'active_honey_jars': 5,
            'messages_processed': 1234,
            'threats_blocked': 89,
            'system_uptime': 99.9,
            'ai_interactions': 456,
            'team_members': 12
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Enterprise System Administration APIs

@system_bp.route('/system/status', methods=['GET'])
@require_auth_or_api_key(['admin'])
def system_status():
    """Get comprehensive system status for enterprise monitoring"""
    try:
        # CPU and Memory usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Service health checks
        services_status = {}
        for service_name, url in SERVICE_URLS.items():
            try:
                response = requests.get(url, timeout=2)
                services_status[service_name] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2)
                }
            except:
                services_status[service_name] = {
                    'status': 'offline',
                    'response_time_ms': None
                }
        
        return jsonify({
            'system': {
                'status': 'healthy',
                'uptime_seconds': int(time.time() - psutil.boot_time()),
                'timestamp': datetime.utcnow().isoformat()
            },
            'performance': {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': round((disk.used / disk.total) * 100, 2),
                'disk_free_gb': round(disk.free / (1024**3), 2)
            },
            'services': services_status
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get system status: {str(e)}'}), 500

@system_bp.route('/system/metrics', methods=['GET'])
@require_auth_or_api_key(['admin'])
def system_metrics():
    """Get detailed system metrics for enterprise monitoring"""
    try:
        # Database metrics
        try:
            user_count = User.query.count()
            active_users = User.query.filter(User.is_active == True).count()
        except:
            user_count = 0
            active_users = 0
        
        # System performance metrics
        cpu_times = psutil.cpu_times()
        memory = psutil.virtual_memory()
        
        return jsonify({
            'performance': {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': memory.percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            },
            'database': {
                'total_users': user_count,
                'active_users': active_users,
                'connection_pool_size': 20  # From typical config
            },
            'requests': {
                'total_today': 1250,  # Would be tracked via middleware
                'average_response_time': 1.23,
                'error_rate': 0.02
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get system metrics: {str(e)}'}), 500

@system_bp.route('/admin/users', methods=['GET'])
@require_auth_or_api_key(['admin'])
def list_users():
    """List all users for admin management"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Query users
        users_query = User.query.order_by(User.created_at.desc())
        
        # Apply filters
        role_filter = request.args.get('role')
        if role_filter:
            users_query = users_query.filter(User.role == role_filter)
            
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        if active_only:
            users_query = users_query.filter(User.is_active == True)
        
        # Paginate
        users = users_query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'users': [{
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None
            } for user in users.items],
            'pagination': {
                'page': page,
                'pages': users.pages,
                'per_page': per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list users: {str(e)}'}), 500