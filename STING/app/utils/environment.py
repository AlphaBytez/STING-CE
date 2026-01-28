"""
Environment detection utilities for STING
Detects WSL2, VM, Docker, and other deployment environments
"""

import os
import platform
import logging

logger = logging.getLogger(__name__)

def is_wsl2():
    """
    Detect if running in WSL2 environment
    """
    try:
        # Check for WSL-specific environment variables
        if 'WSL_DISTRO_NAME' in os.environ or 'WSL_INTEROP' in os.environ:
            return True
        
        # Check /proc/version for WSL indicators
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                if 'microsoft' in version_info or 'wsl' in version_info:
                    return True
        
        # Check for WSL-specific file
        if os.path.exists('/proc/sys/fs/binfmt_misc/WSLInterop'):
            return True
            
    except Exception as e:
        logger.debug(f"Error checking for WSL2: {e}")
    
    return False

def is_docker():
    """
    Detect if running inside a Docker container
    """
    try:
        # Check for .dockerenv file
        if os.path.exists('/.dockerenv'):
            return True
        
        # Check cgroup for docker
        if os.path.exists('/proc/self/cgroup'):
            with open('/proc/self/cgroup', 'r') as f:
                for line in f:
                    if 'docker' in line or 'kubepods' in line:
                        return True
    except Exception as e:
        logger.debug(f"Error checking for Docker: {e}")
    
    return False

def is_vm():
    """
    Detect if running in a virtual machine
    """
    try:
        # Check for common VM indicators
        system = platform.system().lower()
        
        if system == 'linux':
            # Check DMI information for VM vendors
            dmi_files = [
                '/sys/class/dmi/id/sys_vendor',
                '/sys/class/dmi/id/product_name',
                '/sys/class/dmi/id/board_vendor'
            ]
            
            vm_indicators = [
                'vmware', 'virtualbox', 'kvm', 'qemu', 
                'xen', 'hyper-v', 'parallels', 'virtual'
            ]
            
            for dmi_file in dmi_files:
                if os.path.exists(dmi_file):
                    try:
                        with open(dmi_file, 'r') as f:
                            content = f.read().lower()
                            for indicator in vm_indicators:
                                if indicator in content:
                                    return True
                    except:
                        pass
            
            # Check CPU info
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                    if 'hypervisor' in cpuinfo:
                        return True
        
    except Exception as e:
        logger.debug(f"Error checking for VM: {e}")
    
    return False

def get_environment():
    """
    Get the current deployment environment
    Returns: 'wsl2', 'docker', 'vm', 'native'
    """
    if is_docker():
        # Docker takes precedence as we're always in Docker
        # But check if Docker is running in WSL2
        if is_wsl2():
            return 'docker-wsl2'
        return 'docker'
    elif is_wsl2():
        return 'wsl2'
    elif is_vm():
        return 'vm'
    else:
        return 'native'

def get_optimal_cookie_config():
    """
    Get optimal cookie configuration based on environment
    """
    env = get_environment()
    
    # Default configuration
    config = {
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        # CRITICAL FIX: Don't set domain to work with proxy scenarios and external IPs
        # Note: Flask doesn't like None for domain, so we omit it entirely
    }
    
    # Adjust for specific environments
    if env in ['wsl2', 'docker-wsl2', 'vm', 'docker']:
        # More permissive settings for NAT/proxy environments
        config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-origin
        # Don't set domain for permissive behavior
        logger.info(f"Using Docker/VM/WSL2 cookie configuration (SameSite=None, no domain) for environment: {env}")
    else:
        # Native environment can use stricter settings
        config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        # Don't set domain for proxy compatibility
        logger.info(f"Using native cookie configuration (SameSite=Lax, no domain) for environment: {env}")
    
    return config

def log_environment_info():
    """
    Log detailed environment information for debugging
    """
    env = get_environment()
    logger.info(f"Deployment environment detected: {env}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python version: {platform.python_version()}")
    
    # Log specific environment details
    if env == 'wsl2' or env == 'docker-wsl2':
        logger.info("WSL2 environment detected - using compatibility mode")
        if 'WSL_DISTRO_NAME' in os.environ:
            logger.info(f"WSL Distribution: {os.environ.get('WSL_DISTRO_NAME')}")
    elif env == 'vm':
        logger.info("Virtual machine environment detected")
    elif env == 'docker':
        logger.info("Docker container environment detected")
        if os.path.exists('/proc/1/cgroup'):
            try:
                with open('/proc/1/cgroup', 'r') as f:
                    cgroup_info = f.read()
                    if 'docker' in cgroup_info:
                        # Extract container ID
                        for line in cgroup_info.split('\n'):
                            if 'docker' in line:
                                parts = line.split('/')
                                if len(parts) > 2:
                                    container_id = parts[-1][:12]
                                    logger.info(f"Container ID: {container_id}")
                                    break
            except:
                pass
    else:
        logger.info("Native environment detected")

def get_system_timezone():
    """
    Get system timezone with fallback to UTC
    
    Priority:
    1. TZ environment variable (for VM deployments)
    2. System timezone detection
    3. UTC fallback
    
    Returns:
        str: Timezone identifier (e.g., 'UTC', 'America/New_York', 'Europe/London')
    """
    # First priority: TZ environment variable
    tz = os.getenv('TZ')
    if tz:
        try:
            # Validate timezone string
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo
            
            # Test if timezone is valid
            ZoneInfo(tz)
            logger.info(f"Using TZ environment variable timezone: {tz}")
            return tz
        except ImportError:
            logger.warning("zoneinfo not available (Python < 3.9), using TZ variable as-is")
            return tz
        except Exception as e:
            logger.warning(f"Invalid TZ environment variable '{tz}': {e}")
    
    # Second priority: System timezone detection
    try:
        import tzlocal
        system_tz = str(tzlocal.get_localzone())
        logger.info(f"Detected system timezone: {system_tz}")
        return system_tz
    except ImportError:
        logger.info("tzlocal package not available for timezone detection")
    except Exception as e:
        logger.warning(f"Failed to detect system timezone: {e}")
    
    # Fallback to UTC
    logger.info("Using UTC timezone (fallback)")
    return 'UTC'


def get_datetime_context():
    """
    Get comprehensive datetime context for system awareness
    
    Returns:
        Dict with current time in multiple formats and timezone info
    """
    from datetime import datetime, timezone
    
    system_tz = get_system_timezone()
    now_utc = datetime.now(timezone.utc)
    
    try:
        from zoneinfo import ZoneInfo
        tz_info = ZoneInfo(system_tz)
        now_local = now_utc.astimezone(tz_info)
        
        return {
            'utc': {
                'iso': now_utc.isoformat(),
                'human': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'timestamp': now_utc.timestamp()
            },
            'local': {
                'iso': now_local.isoformat(), 
                'human': now_local.strftime(f'%Y-%m-%d %H:%M:%S {system_tz}'),
                'timezone': system_tz,
                'offset': now_local.strftime('%z')
            },
            'timezone': system_tz,
            'is_utc': system_tz == 'UTC'
        }
    except ImportError:
        # Fallback for systems without zoneinfo
        return {
            'utc': {
                'iso': now_utc.isoformat(),
                'human': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'timestamp': now_utc.timestamp()
            },
            'local': {
                'iso': now_utc.isoformat(),
                'human': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'timezone': system_tz,
                'offset': '+0000'
            },
            'timezone': system_tz,
            'is_utc': True
        }


def get_database_url():
    """
    Get database URL from environment or return default
    """
    return os.getenv('DATABASE_URL', 'postgresql://app_user:app_secure_password_change_me@db:5432/sting_app?sslmode=disable')