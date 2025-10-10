#!/usr/bin/env python3
"""
Minimal Report Worker for STING-CE
A lightweight worker that delegates all processing to the app service via API calls.
This eliminates code duplication and version coordination issues.
"""

import os
import sys
import logging
import asyncio
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from datetime import datetime
import uuid
import urllib3
import ssl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def configure_ssl_verification():
    """Configure SSL verification for HTTPS requests"""
    cert_path = '/app/certs/server.crt'

    # Always disable SSL warnings for internal microservice communication
    # Since we're in a controlled environment with self-signed certificates
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()

    if os.path.exists(cert_path):
        logger.info(f"Found shared SSL certificate at {cert_path}, but using verify=False for internal communication")
    else:
        logger.info("No SSL certificate found, using verify=False for internal communication")

    return session

class MinimalReportWorker:
    """Lightweight worker that processes jobs via app service APIs"""

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"minimal-worker-{uuid.uuid4().hex[:8]}"
        self.app_base_url = os.environ.get('APP_SERVICE_URL', 'http://app:5050')
        self.is_running = False

        # Configure SSL session
        self.session = configure_ssl_verification()

        # Internal API endpoints
        self.next_job_url = f"{self.app_base_url}/api/reports/internal/next-job"
        self.process_job_url = f"{self.app_base_url}/api/reports/internal/process-job"

        logger.info(f"Minimal report worker {self.worker_id} initialized")
        logger.info(f"App service URL: {self.app_base_url}")
        logger.info(f"SSL session configured: {type(self.session).__name__}")

    async def start(self):
        """Start the worker loop"""
        self.is_running = True
        logger.info(f"Minimal worker {self.worker_id} started")

        while self.is_running:
            try:
                # Get next job from app service
                job = self._get_next_job()

                if job:
                    logger.info(f"Processing job: {job['report_id']}")
                    success = self._process_job(job)

                    if success:
                        logger.info(f"Successfully processed job: {job['report_id']}")
                    else:
                        logger.error(f"Failed to process job: {job['report_id']}")
                else:
                    # No jobs available, wait before checking again
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping minimal worker {self.worker_id}")
        self.is_running = False

    def _get_next_job(self) -> dict:
        """Get next job from app service"""
        try:
            response = self.session.get(
                self.next_job_url,
                params={'worker_id': self.worker_id},
                timeout=30,
                verify=False  # Skip SSL verification for internal services
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('job'):
                    return data['data']['job']

            return None

        except Exception as e:
            logger.error(f"Error getting next job: {e}")
            return None

    def _process_job(self, job: dict) -> bool:
        """Process job via app service API"""
        try:
            response = self.session.post(
                self.process_job_url,
                json=job,
                timeout=300,  # 5 minutes for processing
                verify=False  # Skip SSL verification for internal services
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            else:
                logger.error(f"Process job API returned {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error processing job via API: {e}")
            return False

    def health_check(self) -> bool:
        """Check if the worker is healthy"""
        try:
            # Check if app service is reachable
            response = self.session.get(f"{self.app_base_url}/api/reports/health", timeout=10, verify=False)
            return response.status_code == 200
        except:
            return False

def simple_health_check() -> bool:
    """Lightweight health check for Docker health check - doesn't create full worker instance"""
    import os
    import requests
    import urllib3

    # Disable SSL warnings for health check
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        app_url = os.environ.get('APP_SERVICE_URL', 'https://app:5050')
        # Use main app health endpoint which is more reliable than reports-specific endpoint
        response = requests.get(f"{app_url}/health", timeout=5, verify=False)
        return response.status_code == 200
    except:
        return False

def health_check_main():
    """Entry point for health check - returns proper exit code"""
    import sys
    if simple_health_check():
        sys.exit(0)
    else:
        sys.exit(1)

# Main entry point
async def main():
    """Main entry point for the minimal worker"""
    worker = MinimalReportWorker()

    try:
        # Start the worker
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await worker.stop()
    except Exception as e:
        logger.error(f"Minimal worker crashed: {e}")
        raise

if __name__ == '__main__':
    # Run the minimal worker
    asyncio.run(main())