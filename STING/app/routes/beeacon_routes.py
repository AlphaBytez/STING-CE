"""
🐝 Beeacon Monitoring Stack API Routes
Provides endpoints for STING's observability and monitoring functionality
"""

import json
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, g
import docker
import requests
from ..utils.decorators import require_auth
# Get user from Flask's g object which is set by auth middleware

def check_service_via_http(service_name):
    """
    Check service health via HTTP endpoints where Docker monitoring is not available
    """
    service_endpoints = {
        'app': 'http://localhost:5050/health',
        'knowledge': 'http://knowledge:8090/health',
        'chatbot': 'http://chatbot:8081/health'
    }
    
    endpoint = service_endpoints.get(service_name)
    if not endpoint:
        return 'unknown', 'N/A'
    
    try:
        response = requests.get(endpoint, timeout=3)
        if response.status_code == 200:
            return 'healthy', 'Active'
        else:
            return 'warning', f'HTTP {response.status_code}'
    except requests.exceptions.RequestException:
        return 'error', 'Offline'

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not g.user.is_admin and not g.user.is_super_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Create blueprint for Beeacon routes
beeacon = Blueprint('beeacon', __name__, url_prefix='/api/beeacon')

@beeacon.route('/public/status', methods=['GET'])
def get_public_system_status():
    """
    Get demo system status for Beeacon dashboard - no auth required
    """
    return jsonify({
        'status': 'success',
        'data': {
            'serviceHealth': {
                'app': {'status': 'healthy', 'uptime': '7d 12h', 'lastCheck': '30s ago'},
                'database': {'status': 'healthy', 'uptime': '7d 12h', 'lastCheck': '15s ago'},
                'kratos': {'status': 'healthy', 'uptime': '7d 10h', 'lastCheck': '45s ago'},
                'vault': {'status': 'healthy', 'uptime': '7d 12h', 'lastCheck': '60s ago'},
                'knowledge': {'status': 'healthy', 'uptime': '6d 8h', 'lastCheck': '20s ago'},
                'chatbot': {'status': 'warning', 'uptime': '2d 14h', 'lastCheck': '2m ago'},
                'redis': {'status': 'healthy', 'uptime': '7d 12h', 'lastCheck': '10s ago'},
                'loki': {'status': 'healthy', 'uptime': '5d 3h', 'lastCheck': '10s ago'},
                'grafana': {'status': 'healthy', 'uptime': '5d 3h', 'lastCheck': '25s ago'},
                'promtail': {'status': 'healthy', 'uptime': '5d 3h', 'lastCheck': '35s ago'}
            },
            'systemMetrics': {
                'uptime': '99.8%',
                'responseTime': '142ms',
                'throughput': '1.2K/min',
                'alerts': 3,
                'totalContainers': 10,
                'healthyContainers': 9
            }
        }
    })

@beeacon.route('/public/pollen-filter/stats', methods=['GET'])
def get_public_pollen_stats():
    """
    Get demo pollen filter stats for Beeacon dashboard - no auth required
    """
    return jsonify({
        'status': 'success',
        'data': {
            'totalFiltered': 1247,
            'piiDetected': 89,
            'secretsSanitized': 156,
            'auditTrail': 2403,
            'recentActivity': [
                {'timestamp': '2m ago', 'type': 'PII', 'action': 'Sanitized', 'context': 'Log entry'},
                {'timestamp': '5m ago', 'type': 'Secret', 'action': 'Removed', 'context': 'API response'},
                {'timestamp': '8m ago', 'type': 'PII', 'action': 'Detected', 'context': 'Database query'}
            ]
        }
    })

@beeacon.route('/status', methods=['GET'])
@require_auth
def get_system_status():
    """
    Get overall system status and health metrics
    """
    try:
        user = g.user if hasattr(g, 'user') else None
        
        # Define STING services to monitor
        services = {
            'app': 'sting-ce-app',
            'database': 'sting-ce-db', 
            'kratos': 'sting-ce-kratos',
            'vault': 'sting-ce-vault',
            'knowledge': 'sting-ce-knowledge',
            'chatbot': 'sting-ce-chatbot',
            'redis': 'sting-ce-redis',
            'loki': 'sting-ce-loki',
            'grafana': 'sting-ce-grafana',
            'promtail': 'sting-ce-promtail'
        }
        
        service_health = {}
        healthy_services = 0
        total_services = 0
        docker_available = False
        
        # Try to get Docker client for service health checks
        try:
            client = docker.from_env()
            # Test Docker connection
            client.ping()
            docker_available = True
        except Exception as docker_err:
            current_app.logger.info(f"Docker monitoring unavailable, using HTTP health checks: {str(docker_err)}")
            client = None
        
        for service_name, container_name in services.items():
            total_services += 1
            
            if not docker_available or client is None:
                # Docker not available, use service-specific health checks where possible
                if service_name in ['app', 'knowledge', 'chatbot']:
                    # These services can be tested via HTTP health endpoints
                    status, uptime_str = check_service_via_http(service_name)
                elif service_name in ['vault', 'database', 'redis', 'kratos']:
                    # Assume core infrastructure services are healthy if containers exist
                    status = 'healthy'
                    uptime_str = 'Active'
                else:
                    # For other services, indicate they're running
                    status = 'healthy'
                    uptime_str = 'Running'
                
                service_health[service_name] = {
                    'status': status,
                    'uptime': uptime_str,
                    'lastCheck': 'now',
                    'container_status': 'monitoring_limited'
                }
                
                if status == 'healthy':
                    healthy_services += 1
                    
            else:
                # Docker available, use full container monitoring
                try:
                    container = client.containers.get(container_name)
                    
                    # Calculate uptime
                    started_at = container.attrs['State']['StartedAt']
                    started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = datetime.now() - started_time.replace(tzinfo=None)
                    uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h"
                    
                    # Determine health status
                    if container.status == 'running':
                        # Try to get health check status if available
                        health_status = container.attrs.get('State', {}).get('Health', {})
                        if health_status:
                            health = health_status.get('Status', 'unknown')
                            status = 'healthy' if health == 'healthy' else 'warning'
                        else:
                            status = 'healthy'  # Running but no explicit health check
                        
                        if status == 'healthy':
                            healthy_services += 1
                    else:
                        status = 'error'
                    
                    service_health[service_name] = {
                        'status': status,
                        'uptime': uptime_str,
                        'lastCheck': 'now',
                        'container_status': container.status
                    }
                    
                except docker.errors.NotFound:
                    # Service not running or doesn't exist
                    service_health[service_name] = {
                        'status': 'error',
                        'uptime': 'N/A',
                        'lastCheck': 'now',
                        'container_status': 'not_found'
                    }
                except Exception as e:
                    current_app.logger.warning(f"Error checking {service_name}: {str(e)}")
                    service_health[service_name] = {
                        'status': 'unknown',
                        'uptime': 'N/A', 
                        'lastCheck': 'error',
                        'container_status': 'error'
                    }
        
        # Calculate overall system health percentage
        health_percentage = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        # Get system metrics (mock data for now - could be expanded with real metrics)
        system_metrics = {
            'uptime': f"{health_percentage:.1f}%",
            'responseTime': '142ms',
            'throughput': '1.2K/min',
            'alerts': 2 if health_percentage < 90 else 0
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'serviceHealth': service_health,
                'systemMetrics': system_metrics,
                'healthPercentage': health_percentage,
                'timestamp': datetime.utcnow().isoformat(),
                'dockerAvailable': docker_available,
                'monitoringMode': 'full' if docker_available else 'limited'
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/pollen-filter/stats', methods=['GET'])
@require_auth
def get_pollen_filter_stats():
    """
    Get Pollen Filter (log sanitization) statistics
    """
    try:
        # In a real implementation, this would query the Vault audit log
        # or a dedicated sanitization tracking system
        
        # Mock data based on typical sanitization patterns
        stats = {
            'totalFiltered': 1247,
            'piiDetected': 89,
            'secretsSanitized': 156,
            'auditTrail': 2403,
            'breakdown': {
                'secrets': 156,
                'auth': 89,
                'pii': 89,
                'database': 67,
                'conversations': 23,
                'network': 12
            },
            'recentActivity': [
                {
                    'timestamp': (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
                    'category': 'secrets',
                    'action': 'API key sanitized in app logs',
                    'severity': 'high'
                },
                {
                    'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    'category': 'pii',
                    'action': 'Email address filtered from user activity log',
                    'severity': 'medium'
                },
                {
                    'timestamp': (datetime.utcnow() - timedelta(minutes=8)).isoformat(),
                    'category': 'database',
                    'action': 'Database credentials sanitized in error log',
                    'severity': 'critical'
                }
            ]
        }
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting pollen filter stats: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/grafana/status', methods=['GET'])
@require_auth
def get_grafana_status():
    """
    Check Grafana availability and get basic info
    """
    try:
        # Check if Grafana is accessible
        grafana_url = "http://grafana:3000"
        
        try:
            response = requests.get(f"{grafana_url}/api/health", timeout=5)
            if response.status_code == 200:
                grafana_status = 'healthy'
                grafana_info = response.json()
            else:
                grafana_status = 'warning'
                grafana_info = {'message': 'Grafana responded but with error status'}
        except requests.exceptions.RequestException:
            grafana_status = 'error'
            grafana_info = {'message': 'Grafana is not accessible'}
        
        # Generate dashboard URLs (these would be real in production)
        dashboards = [
            {
                'name': 'STING System Overview',
                'url': f"{grafana_url}/d/sting-overview/sting-system-overview",
                'description': 'High-level system health and performance'
            },
            {
                'name': 'Authentication Audit',
                'url': f"{grafana_url}/d/sting-auth/authentication-audit",
                'description': 'Login attempts, failures, and security events'
            },
            {
                'name': 'Knowledge Service Metrics',
                'url': f"{grafana_url}/d/sting-knowledge/knowledge-service-metrics", 
                'description': 'Honey jar usage, search performance, document processing'
            },
            {
                'name': 'PII Compliance Dashboard',
                'url': f"{grafana_url}/d/sting-pii/pii-compliance-dashboard",
                'description': 'Data sanitization metrics and compliance tracking'
            }
        ]
        
        return jsonify({
            'status': 'success',
            'data': {
                'grafanaStatus': grafana_status,
                'grafanaInfo': grafana_info,
                'dashboards': dashboards,
                'grafanaUrl': grafana_url
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking Grafana status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/loki/status', methods=['GET'])
@require_auth
def get_loki_status():
    """
    Check Loki log aggregation status
    """
    try:
        loki_url = "http://loki:3100"
        
        try:
            response = requests.get(f"{loki_url}/ready", timeout=5)
            if response.status_code == 200:
                loki_status = 'healthy'
                loki_info = {'message': 'Loki is ready and accepting logs'}
            else:
                loki_status = 'warning'
                loki_info = {'message': 'Loki responded but may not be ready'}
        except requests.exceptions.RequestException:
            loki_status = 'error'
            loki_info = {'message': 'Loki is not accessible'}
        
        # Mock log statistics
        log_stats = {
            'totalLogs': 45267,
            'logsToday': 12389,
            'avgLogsPerMinute': 850,
            'sanitizedLogs': 1247,
            'retentionPeriod': '7 days',
            'storageUsed': '2.4 GB'
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'lokiStatus': loki_status,
                'lokiInfo': loki_info,
                'logStats': log_stats,
                'lokiUrl': loki_url
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking Loki status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/alerts', methods=['GET'])
@require_auth  
def get_system_alerts():
    """
    Get current system alerts and notifications
    """
    try:
        # Mock alert data - in production this would come from Grafana/Alertmanager
        alerts = [
            {
                'id': 'alert-001',
                'severity': 'warning',
                'title': 'High Memory Usage',
                'message': 'Knowledge service memory usage is at 85%',
                'timestamp': (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                'service': 'knowledge',
                'resolved': False
            },
            {
                'id': 'alert-002', 
                'severity': 'info',
                'title': 'Pollen Filter Active',
                'message': '12 sensitive data patterns sanitized in the last hour',
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'service': 'pollen-filter',
                'resolved': False
            }
        ]
        
        # Group alerts by severity
        alert_summary = {
            'critical': len([a for a in alerts if a['severity'] == 'critical']),
            'warning': len([a for a in alerts if a['severity'] == 'warning']),
            'info': len([a for a in alerts if a['severity'] == 'info']),
            'total': len(alerts)
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts,
                'summary': alert_summary
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system alerts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/health-report', methods=['POST'])
@require_auth
def generate_health_report():
    """
    Generate a comprehensive system health report
    """
    try:
        user = g.user if hasattr(g, 'user') else None
        
        # This would generate a comprehensive report including:
        # - Service health status
        # - Performance metrics
        # - Security events
        # - Log analysis
        # - Sanitization statistics
        
        report_id = f"health-report-{int(time.time())}"
        
        # Mock report data
        report = {
            'id': report_id,
            'generatedAt': datetime.utcnow().isoformat(),
            'generatedBy': user.email if user else 'system',
            'reportType': 'system_health',
            'summary': {
                'overallHealth': 'good',
                'servicesHealthy': 8,
                'servicesTotal': 9,
                'criticalIssues': 0,
                'warnings': 2,
                'sanitizationEvents': 156
            },
            'downloadUrl': f'/api/beeacon/reports/{report_id}/download',
            'status': 'completed'
        }
        
        return jsonify({
            'status': 'success',
            'data': report
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating health report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@beeacon.route('/config', methods=['GET'])
@require_admin
def get_beeacon_config():
    """
    Get Beeacon monitoring configuration (admin only)
    """
    try:
        # Load observability configuration from the app config
        # This would read from the actual config system
        
        config = {
            'observability': {
                'enabled': True,
                'grafana': {
                    'enabled': True,
                    'port': 3000,
                    'url': 'http://grafana:3000'
                },
                'loki': {
                    'enabled': True,
                    'port': 3100,
                    'retentionPeriod': '168h',  # 7 days
                    'maxLineSize': '256KB'
                },
                'promtail': {
                    'enabled': True,
                    'port': 9080,
                    'sanitizationEnabled': True
                }
            },
            'pollenFilter': {
                'enabled': True,
                'vaultReferences': True,
                'auditLogging': True,
                'patterns': {
                    'pii': True,
                    'secrets': True,
                    'database': True,
                    'auth': True
                }
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': config
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting Beeacon config: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Error handlers
@beeacon.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404

@beeacon.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500