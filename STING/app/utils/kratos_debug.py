"""
Debug utilities for Kratos connectivity
"""
import os
import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def test_kratos_connectivity():
    """Test connectivity to Kratos from within the container"""
    results = {}
    
    # Get configured URLs
    public_url = os.getenv('KRATOS_PUBLIC_URL', 'https://localhost:4433')
    admin_url = os.getenv('KRATOS_ADMIN_URL', 'http://kratos:4434')
    
    logger.info(f"Testing Kratos connectivity...")
    logger.info(f"KRATOS_PUBLIC_URL: {public_url}")
    logger.info(f"KRATOS_ADMIN_URL: {admin_url}")
    
    # Test public endpoint
    try:
        # Try with SSL verification disabled
        resp = requests.get(f"{public_url}/health/ready", verify=False, timeout=5)
        results['public_health'] = {
            'url': f"{public_url}/health/ready",
            'status': resp.status_code,
            'success': resp.status_code == 200,
            'response': resp.text if resp.status_code != 200 else 'OK'
        }
    except Exception as e:
        results['public_health'] = {
            'url': f"{public_url}/health/ready",
            'status': None,
            'success': False,
            'error': str(e)
        }
    
    # Test admin endpoint
    try:
        resp = requests.get(f"{admin_url}/admin/health/ready", verify=False, timeout=5)
        results['admin_health'] = {
            'url': f"{admin_url}/admin/health/ready",
            'status': resp.status_code,
            'success': resp.status_code == 200,
            'response': resp.text if resp.status_code != 200 else 'OK'
        }
    except Exception as e:
        results['admin_health'] = {
            'url': f"{admin_url}/admin/health/ready",
            'status': None,
            'success': False,
            'error': str(e)
        }
    
    # Try alternative URLs
    alternatives = [
        ('http://kratos:4433', 'Internal HTTP'),
        ('https://localhost:4433', 'Localhost HTTPS'),
        ('http://localhost:4433', 'Localhost HTTP'),
        ('https://sting-ce-kratos:4433', 'Container name HTTPS'),
        ('http://sting-ce-kratos:4433', 'Container name HTTP'),
    ]
    
    for url, desc in alternatives:
        try:
            resp = requests.get(f"{url}/health/ready", verify=False, timeout=2)
            results[f'alternative_{desc}'] = {
                'url': f"{url}/health/ready",
                'status': resp.status_code,
                'success': resp.status_code == 200
            }
        except Exception as e:
            results[f'alternative_{desc}'] = {
                'url': f"{url}/health/ready",
                'status': None,
                'success': False,
                'error': str(type(e).__name__)
            }
    
    return results

def test_session_validation(session_cookie: str):
    """Test session validation with detailed debugging"""
    public_url = os.getenv('KRATOS_PUBLIC_URL', 'https://localhost:4433')
    
    logger.info(f"Testing session validation...")
    logger.info(f"Session cookie: {session_cookie[:20]}...")
    
    # Try different approaches
    approaches = []
    
    # Approach 1: Standard cookie
    try:
        resp = requests.get(
            f"{public_url}/sessions/whoami",
            cookies={'ory_kratos_session': session_cookie},
            verify=False,
            timeout=5
        )
        approaches.append({
            'method': 'Standard cookie',
            'status': resp.status_code,
            'success': resp.status_code == 200,
            'response': resp.json() if resp.status_code == 200 else resp.text
        })
    except Exception as e:
        approaches.append({
            'method': 'Standard cookie',
            'error': str(e)
        })
    
    # Approach 2: Both cookie names
    try:
        resp = requests.get(
            f"{public_url}/sessions/whoami",
            cookies={
                'ory_kratos_session': session_cookie,
                'ory_kratos_session': session_cookie
            },
            verify=False,
            timeout=5
        )
        approaches.append({
            'method': 'Both cookie names',
            'status': resp.status_code,
            'success': resp.status_code == 200,
            'response': resp.json() if resp.status_code == 200 else resp.text
        })
    except Exception as e:
        approaches.append({
            'method': 'Both cookie names',
            'error': str(e)
        })
    
    # Approach 3: Cookie header
    try:
        resp = requests.get(
            f"{public_url}/sessions/whoami",
            headers={'Cookie': f'ory_kratos_session={session_cookie}'},
            verify=False,
            timeout=5
        )
        approaches.append({
            'method': 'Cookie header',
            'status': resp.status_code,
            'success': resp.status_code == 200,
            'response': resp.json() if resp.status_code == 200 else resp.text
        })
    except Exception as e:
        approaches.append({
            'method': 'Cookie header',
            'error': str(e)
        })
    
    return approaches