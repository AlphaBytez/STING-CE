"""
System Context Service for Enhanced Bee Intelligence

This service aggregates system information from existing STING services to provide
contextual awareness to Bee without creating new dependencies.

Features:
- Real-time system metrics via existing psutil integration
- Environment detection from environment.py 
- Service health from system_routes.py
- Redis status (used by AAL2)
- Timezone support for VM deployments
"""

import os
import platform
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import redis
import requests

logger = logging.getLogger(__name__)

class SystemContextService:
    """Provides system context for enhanced AI responses"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.context_cache_duration = 60  # Cache for 60 seconds
        self._last_context = None
        self._last_context_time = None
        
    def _get_redis_client(self):
        """Get Redis client (same instance used by AAL2)"""
        try:
            return redis.from_url('redis://redis:6379/0')
        except Exception as e:
            logger.warning(f"Redis not available for system context: {e}")
            return None
    
    def _get_system_timezone(self) -> str:
        """Get system timezone with fallback to UTC"""
        # Priority: TZ env var > system timezone > UTC
        tz = os.getenv('TZ')
        if tz:
            return tz
        
        # Try to detect system timezone
        try:
            import tzlocal
            return str(tzlocal.get_localzone())
        except ImportError:
            logger.info("tzlocal not available, using UTC")
        except Exception as e:
            logger.warning(f"Failed to get system timezone: {e}")
        
        return 'UTC'
    
    def _get_datetime_context(self) -> Dict[str, Any]:
        """Get current datetime with timezone context"""
        system_tz = self._get_system_timezone()
        now_utc = datetime.now(timezone.utc)
        
        return {
            'utc_iso': now_utc.isoformat(),
            'utc_human': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'timezone': system_tz,
            'local_time': f"Current time in {system_tz}",
            'timestamp': now_utc.timestamp()
        }
    
    def _get_environment_context(self) -> Dict[str, Any]:
        """Get environment context from existing environment.py"""
        try:
            from app.utils.environment import get_environment, log_environment_info
            
            env = get_environment()
            platform_info = {
                'system': platform.system(),
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'machine': platform.machine(),
                'processor': platform.processor() if hasattr(platform, 'processor') else 'Unknown'
            }
            
            return {
                'deployment_type': env,
                'platform': platform_info,
                'is_containerized': env in ['docker', 'docker-wsl2'],
                'is_vm': env in ['vm', 'wsl2', 'docker-wsl2']
            }
        except Exception as e:
            logger.warning(f"Failed to get environment context: {e}")
            return {
                'deployment_type': 'unknown',
                'platform': {'system': platform.system()},
                'is_containerized': False,
                'is_vm': False
            }
    
    def _get_redis_context(self) -> Dict[str, Any]:
        """Get Redis status (important for AAL2 functionality)"""
        redis_status = {
            'available': False,
            'connection': 'disconnected',
            'aal2_compatible': False
        }
        
        if self.redis_client:
            try:
                # Test connection
                self.redis_client.ping()
                redis_status.update({
                    'available': True,
                    'connection': 'connected',
                    'aal2_compatible': True
                })
                
                # Check AAL2 keys (optional debug info)
                try:
                    aal2_keys = self.redis_client.keys('sting:custom_aal2:*')
                    redis_status['active_aal2_sessions'] = len(aal2_keys) if aal2_keys else 0
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Redis ping failed: {e}")
                redis_status['connection'] = f'failed: {str(e)[:50]}'
        
        return redis_status
    
    def _get_system_performance(self) -> Dict[str, Any]:
        """Get basic system performance metrics"""
        try:
            import psutil
            
            # Get CPU usage (quick sample)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get memory info
            memory = psutil.virtual_memory()
            
            # Get basic disk info
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage_percent': round(cpu_percent, 1),
                'memory_usage_percent': round(memory.percent, 1),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': round((disk.used / disk.total) * 100, 1),
                'system_load': 'normal' if cpu_percent < 80 and memory.percent < 85 else 'high'
            }
        except Exception as e:
            logger.warning(f"Failed to get performance metrics: {e}")
            return {
                'cpu_usage_percent': 0,
                'memory_usage_percent': 0,
                'system_load': 'unknown'
            }
    
    async def _get_services_health(self) -> Dict[str, Any]:
        """Get basic service health status from existing endpoints"""
        services_status = {
            'app': 'unknown',
            'database': 'unknown',
            'redis': 'unknown',
            'overall': 'unknown'
        }
        
        try:
            # Check database via existing system routes logic
            try:
                from app.database import db
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                services_status['database'] = 'healthy'
            except:
                services_status['database'] = 'unhealthy'
            
            # Redis status from our check
            redis_status = self._get_redis_context()
            services_status['redis'] = 'healthy' if redis_status['available'] else 'unhealthy'
            
            # App service is healthy if we're running
            services_status['app'] = 'healthy'
            
            # Overall status
            unhealthy_services = [k for k, v in services_status.items() if v == 'unhealthy' and k != 'overall']
            if not unhealthy_services:
                services_status['overall'] = 'healthy'
            elif len(unhealthy_services) == 1:
                services_status['overall'] = 'degraded'
            else:
                services_status['overall'] = 'unhealthy'
                
        except Exception as e:
            logger.warning(f"Failed to get services health: {e}")
            services_status['overall'] = 'unknown'
        
        return services_status
    
    async def get_enhanced_system_context(self) -> Dict[str, Any]:
        """
        Get comprehensive system context for Bee intelligence
        
        Returns:
            Dict containing all system context information
        """
        try:
            # Check cache first
            now = datetime.now()
            if (self._last_context and self._last_context_time and 
                (now - self._last_context_time).total_seconds() < self.context_cache_duration):
                logger.debug("Using cached system context")
                return self._last_context
            
            logger.info("Gathering fresh system context...")
            
            # Gather all context components
            datetime_context = self._get_datetime_context()
            environment_context = self._get_environment_context()
            redis_context = self._get_redis_context()
            performance_context = self._get_system_performance()
            services_context = await self._get_services_health()
            
            # Build comprehensive context
            context = {
                'timestamp': datetime_context['utc_iso'],
                'datetime': {
                    'utc': datetime_context['utc_human'],
                    'timezone': datetime_context['timezone'],
                    'iso': datetime_context['utc_iso']
                },
                'environment': environment_context,
                'services': services_context,
                'redis': redis_context,
                'performance': performance_context,
                'system': {
                    'platform': environment_context['platform']['system'],
                    'deployment': environment_context['deployment_type'],
                    'python_version': environment_context['platform']['python_version']
                }
            }
            
            # Cache the context
            self._last_context = context
            self._last_context_time = now
            
            logger.info(f"System context gathered: {environment_context['deployment_type']} environment, "
                       f"{services_context['overall']} services, Redis {'available' if redis_context['available'] else 'unavailable'}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error gathering system context: {e}")
            
            # Return minimal fallback context
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'datetime': {
                    'utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'timezone': self._get_system_timezone(),
                    'iso': datetime.now(timezone.utc).isoformat()
                },
                'environment': {'deployment_type': 'unknown'},
                'services': {'overall': 'unknown'},
                'redis': {'available': False},
                'performance': {'system_load': 'unknown'},
                'system': {
                    'platform': platform.system(),
                    'deployment': 'unknown',
                    'python_version': platform.python_version()
                },
                'error': 'Failed to gather complete system context'
            }
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format system context for inclusion in AI prompts
        
        Args:
            context: System context from get_enhanced_system_context()
            
        Returns:
            Formatted string for prompt injection
        """
        try:
            # Extract key information
            dt = context['datetime']
            env = context['environment']
            services = context['services']
            redis = context['redis']
            perf = context['performance']
            
            # Build formatted context
            context_lines = [
                "## Current System Context:",
                f"- **Date/Time**: {dt['utc']} ({dt['timezone']})",
                f"- **Environment**: {env['deployment_type'].title().replace('_', ' ')}",
                f"- **Platform**: {context['system']['platform']} (Python {context['system']['python_version']})",
                f"- **Services**: {services['overall'].title()} (Database: {services['database']}, Redis: {services['redis']})",
                f"- **Performance**: {perf['system_load'].title()} load (CPU: {perf['cpu_usage_percent']}%, Memory: {perf['memory_usage_percent']}%)"
            ]
            
            # Add AAL2 status if available
            if redis['available'] and redis.get('active_aal2_sessions') is not None:
                context_lines.append(f"- **Security**: AAL2 available ({redis['active_aal2_sessions']} active sessions)")
            elif redis['available']:
                context_lines.append("- **Security**: AAL2 system operational")
            
            return '\n'.join(context_lines) + '\n'
            
        except Exception as e:
            logger.warning(f"Error formatting context for prompt: {e}")
            return f"## Current System Context:\n- **Date/Time**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Status**: System context partially available\n"


# Global service instance
system_context_service = SystemContextService()


# Convenience functions for easy import
async def get_enhanced_system_context() -> Dict[str, Any]:
    """Get enhanced system context"""
    return await system_context_service.get_enhanced_system_context()


def format_context_for_prompt(context: Optional[Dict[str, Any]] = None) -> str:
    """Format context for AI prompt injection"""
    if context is None:
        # Get sync context for immediate use
        try:
            context = asyncio.get_event_loop().run_until_complete(get_enhanced_system_context())
        except:
            context = {'datetime': {'utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}}
    
    return system_context_service.format_context_for_prompt(context)


if __name__ == "__main__":
    # Test the service
    async def test_context_service():
        print("Testing System Context Service...")
        
        context = await get_enhanced_system_context()
        print("\nRaw context:")
        import json
        print(json.dumps(context, indent=2, default=str))
        
        print("\nFormatted for prompt:")
        print(format_context_for_prompt(context))
    
    asyncio.run(test_context_service())