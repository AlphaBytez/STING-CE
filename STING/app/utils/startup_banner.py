"""
Startup Banner - Displays important information on STING startup
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def display_startup_banner():
    """Display startup banner with important information"""
    
    # Display passwordless startup banner
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           🐝 STING CE - RUNNING 🐝                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🔐 PASSWORDLESS AUTHENTICATION ENABLED                                      ║
║  ─────────────────────────────────────                                      ║
║  • Login with your email to receive a magic link                            ║
║  • Dev environment: Check Mailpit at http://localhost:8026 for magic links  ║
║                                                                              ║
║  👤 ADMIN ACCOUNT SETUP                                                      ║
║  ─────────────────────────                                                  ║
║  • Create admin: ./manage_sting.sh create admin <your-email>                 ║
║  • Then login with that email address                                       ║
║                                                                              ║
║  🔗 Access STING at: https://localhost:8443                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    logger.info(banner)
    print(banner)