#!/usr/bin/env python3
"""
Secure Bundle Download Server for STING Community Support
Provides time-limited, secure download links for diagnostic bundles
"""

import os
import hashlib
import secrets
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes

logger = logging.getLogger(__name__)


class SecureBundleServer:
    """Secure download server for diagnostic bundles"""
    
    def __init__(self, bundle_dir: str, port: int = 8071, host: str = "0.0.0.0"):
        """
        Initialize secure bundle server
        
        Args:
            bundle_dir: Directory containing diagnostic bundles
            port: Port to serve on (default 8071, avoiding conflicts)
            host: Host to bind to
        """
        self.bundle_dir = Path(bundle_dir)
        self.port = port
        self.host = host
        self.active_links: Dict[str, Dict] = {}
        self.cleanup_thread = None
        
        # Ensure bundle directory exists
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # Start cleanup thread
        self.start_cleanup_thread()
    
    def generate_secure_link(self, bundle_path: str, ticket_id: str, 
                           duration_hours: int = 48) -> Dict[str, str]:
        """
        Generate a secure, time-limited download link for a bundle
        
        Args:
            bundle_path: Path to the diagnostic bundle file
            ticket_id: Support ticket ID
            duration_hours: How long the link should be valid
            
        Returns:
            Dict with download_url, expires_at, and access_token
        """
        if not os.path.exists(bundle_path):
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")
        
        # Generate secure token
        access_token = secrets.token_urlsafe(32)
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        # Store link info
        link_info = {
            'ticket_id': ticket_id,
            'bundle_path': os.path.abspath(bundle_path),
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'duration_hours': duration_hours,
            'download_count': 0,
            'max_downloads': 10,  # Prevent abuse
            'bundle_size': os.path.getsize(bundle_path),
            'bundle_hash': self._calculate_file_hash(bundle_path)
        }
        
        self.active_links[access_token] = link_info
        
        # Generate download URL
        download_url = f"http://{self.host}:{self.port}/download/{access_token}"
        
        logger.info(f"Generated secure link for {ticket_id}: {access_token[:8]}... (expires: {expires_at})")
        
        return {
            'download_url': download_url,
            'access_token': access_token,
            'expires_at': expires_at.isoformat(),
            'ticket_id': ticket_id,
            'bundle_size': link_info['bundle_size'],
            'valid_for': f"{duration_hours} hours"
        }
    
    def validate_access_token(self, token: str) -> Optional[Dict]:
        """Validate access token and return link info if valid"""
        
        if token not in self.active_links:
            return None
        
        link_info = self.active_links[token]
        
        # Check expiration
        expires_at = datetime.fromisoformat(link_info['expires_at'])
        if datetime.now() > expires_at:
            logger.info(f"Access token expired: {token[:8]}...")
            del self.active_links[token]
            return None
        
        # Check download limit
        if link_info['download_count'] >= link_info['max_downloads']:
            logger.warning(f"Download limit exceeded for token: {token[:8]}...")
            return None
        
        return link_info
    
    def record_download(self, token: str) -> bool:
        """Record a download attempt"""
        if token in self.active_links:
            self.active_links[token]['download_count'] += 1
            self.active_links[token]['last_downloaded'] = datetime.now().isoformat()
            return True
        return False
    
    def cleanup_expired_links(self):
        """Remove expired download links"""
        now = datetime.now()
        expired_tokens = []
        
        for token, link_info in self.active_links.items():
            expires_at = datetime.fromisoformat(link_info['expires_at'])
            if now > expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            ticket_id = self.active_links[token]['ticket_id']
            logger.info(f"Cleaning up expired link for ticket {ticket_id}")
            del self.active_links[token]
        
        return len(expired_tokens)
    
    def start_cleanup_thread(self):
        """Start background thread for cleaning up expired links"""
        def cleanup_worker():
            while True:
                try:
                    cleaned = self.cleanup_expired_links()
                    if cleaned > 0:
                        logger.info(f"Cleaned up {cleaned} expired download links")
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
                    time.sleep(60)  # Retry in 1 minute on error
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info("Started cleanup thread for expired download links")
    
    def get_active_links_summary(self) -> Dict:
        """Get summary of active download links"""
        active_count = len(self.active_links)
        
        # Count by ticket
        tickets = set(link['ticket_id'] for link in self.active_links.values())
        
        # Calculate total downloads
        total_downloads = sum(link['download_count'] for link in self.active_links.values())
        
        return {
            'active_links': active_count,
            'active_tickets': len(tickets),
            'total_downloads': total_downloads,
            'server_port': self.port,
            'cleanup_thread_active': self.cleanup_thread.is_alive() if self.cleanup_thread else False
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for integrity verification"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class SecureDownloadHandler(BaseHTTPRequestHandler):
    """HTTP request handler for secure bundle downloads"""
    
    def __init__(self, request, client_address, server, bundle_server: SecureBundleServer):
        self.bundle_server = bundle_server
        super().__init__(request, client_address, server)
    
    def do_GET(self):
        """Handle GET requests for bundle downloads"""
        
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) >= 2 and path_parts[0] == 'download':
            # Download request: /download/{access_token}
            access_token = path_parts[1]
            self._handle_download(access_token)
            
        elif parsed_url.path == '/health':
            # Health check endpoint
            self._handle_health_check()
            
        elif parsed_url.path == '/status':
            # Status endpoint
            self._handle_status()
            
        else:
            # Invalid endpoint
            self._send_error(404, "Endpoint not found")
    
    def _handle_download(self, access_token: str):
        """Handle bundle download request"""
        
        # Validate token
        link_info = self.bundle_server.validate_access_token(access_token)
        
        if not link_info:
            self._send_error(403, "Invalid or expired access token")
            return
        
        bundle_path = link_info['bundle_path']
        
        # Verify file still exists
        if not os.path.exists(bundle_path):
            self._send_error(404, "Bundle file not found")
            return
        
        # Record download
        self.bundle_server.record_download(access_token)
        
        # Send file
        try:
            with open(bundle_path, 'rb') as f:
                file_size = os.path.getsize(bundle_path)
                
                # Send headers
                self.send_response(200)
                self.send_header('Content-Type', 'application/gzip')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Content-Disposition', 
                               f'attachment; filename="sting-bundle-{link_info["ticket_id"]}.tar.gz"')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                
                # Stream file content
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                
                logger.info(f"Bundle download completed: {link_info['ticket_id']} "
                           f"(download #{link_info['download_count']})")
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            self._send_error(500, "Download failed")
    
    def _handle_health_check(self):
        """Handle health check requests"""
        health_data = {
            'status': 'healthy',
            'service': 'secure_bundle_server',
            'timestamp': datetime.now().isoformat(),
            'active_links': len(self.bundle_server.active_links)
        }
        
        self._send_json_response(health_data)
    
    def _handle_status(self):
        """Handle status requests"""
        status_data = self.bundle_server.get_active_links_summary()
        status_data['timestamp'] = datetime.now().isoformat()
        
        self._send_json_response(status_data)
    
    def _send_json_response(self, data: Dict):
        """Send JSON response"""
        response_data = json.dumps(data, indent=2).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)
    
    def _send_error(self, code: int, message: str):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom log format"""
        logger.info(f"[{self.address_string()}] {format % args}")


def create_secure_bundle_link(bundle_path: str, ticket_id: str, duration_hours: int = 48) -> Dict:
    """
    Create a secure download link for a diagnostic bundle
    
    Args:
        bundle_path: Path to the bundle file
        ticket_id: Support ticket ID
        duration_hours: How long the link should be valid
        
    Returns:
        Dict with download information
    """
    
    # Initialize bundle server
    bundle_dir = os.path.dirname(bundle_path)
    server = SecureBundleServer(bundle_dir, port=8071)
    
    # Generate secure link
    link_info = server.generate_secure_link(bundle_path, ticket_id, duration_hours)
    
    return link_info


if __name__ == "__main__":
    # Example usage and testing
    import tempfile
    import argparse
    
    parser = argparse.ArgumentParser(description="STING Secure Bundle Download Server")
    parser.add_argument("--port", type=int, default=8071, help="Port to serve on")
    parser.add_argument("--bundle-dir", required=True, help="Directory containing bundles")
    parser.add_argument("--test", action="store_true", help="Run test mode")
    
    args = parser.parse_args()
    
    if args.test:
        # Test mode - create test bundle and link
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as f:
            f.write(b"Test diagnostic bundle content")
            test_bundle = f.name
        
        try:
            link_info = create_secure_bundle_link(test_bundle, "ST-TEST-001", 1)
            print(f"Test link created: {link_info['download_url']}")
            print(f"Expires: {link_info['expires_at']}")
            print(f"Valid for: {link_info['valid_for']}")
            
        finally:
            os.unlink(test_bundle)
    
    else:
        # Production mode - start server
        bundle_server = SecureBundleServer(args.bundle_dir, args.port)
        
        logger.info(f"Starting secure bundle server on {args.port}")
        logger.info(f"Bundle directory: {args.bundle_dir}")
        
        class SecureHTTPServer(HTTPServer):
            def __init__(self, server_address, RequestHandlerClass, bundle_server):
                self.bundle_server = bundle_server
                super().__init__(server_address, RequestHandlerClass)
        
        def handler_factory(bundle_server):
            def handler(request, client_address, server):
                return SecureDownloadHandler(request, client_address, server, bundle_server)
            return handler
        
        httpd = SecureHTTPServer(
            (args.host, args.port), 
            handler_factory(bundle_server),
            bundle_server
        )
        
        try:
            print(f"🔒 Secure Bundle Server running on http://{args.host}:{args.port}")
            print(f"📁 Bundle directory: {args.bundle_dir}")
            print(f"🏥 Health check: http://{args.host}:{args.port}/health")
            print(f"📊 Status: http://{args.host}:{args.port}/status")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down secure bundle server...")
            httpd.shutdown()