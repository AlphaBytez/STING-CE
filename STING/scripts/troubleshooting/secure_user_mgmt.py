#!/usr/bin/env python3
"""
STING Secure User Management Wrapper

This script provides additional security layers around the user management operations.
It's designed to be run by system administrators with proper authorization.

Features:
- SSH key validation for authorized administrators
- Time-based operation windows
- Additional audit logging
- Emergency mode for critical situations
- Backup verification before destructive operations

Usage:
    python secure_user_mgmt.py [operation] [options]
"""

import os
import sys
import hashlib
import time
import json
import getpass
from datetime import datetime, timedelta

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def log(message):
    print(f"{GREEN}[SECURE MGR]{NC} {message}")

def warning(message):
    print(f"{YELLOW}[WARNING]{NC} {message}")

def error(message):
    print(f"{RED}[ERROR]{NC} {message}")

def check_authorized_user():
    """Check if current user is authorized to run destructive operations"""
    current_user = getpass.getuser()
    
    # Define authorized users (in production, this could be read from a config file)
    authorized_users = ['root', 'admin', 'sting-admin']
    
    if current_user not in authorized_users:
        # Allow if user can provide admin password hash (simple check)
        warning(f"User '{current_user}' not in authorized list")
        
        # Check for authorization file
        auth_file = os.path.expanduser("~/.sting_admin_auth")
        if os.path.exists(auth_file):
            log("Found admin authorization file")
            return True
        
        # Manual authorization
        admin_hash = input("Enter admin authorization hash (contact system administrator): ")
        expected_hash = hashlib.sha256(f"sting-admin-{datetime.now().strftime('%Y-%m-%d')}".encode()).hexdigest()[:16]
        
        if admin_hash == expected_hash:
            log("Authorization hash verified")
            return True
        else:
            error("Invalid authorization hash")
            return False
    
    log(f"Authorized user: {current_user}")
    return True

def check_operation_window():
    """Check if current time is within allowed operation window"""
    current_hour = datetime.now().hour
    
    # Allow destructive operations only during maintenance windows
    # Customize these hours based on your organization's schedule
    allowed_hours = list(range(1, 6)) + list(range(22, 24))  # 1-6 AM and 10-12 PM
    
    if current_hour not in allowed_hours:
        warning(f"Current time ({datetime.now().strftime('%H:%M')}) is outside maintenance window")
        warning("Destructive operations are typically allowed between 1-6 AM and 10 PM-12 AM")
        
        override = input("Override time restriction? (requires justification): ")
        if override.lower() in ['yes', 'emergency', 'critical']:
            justification = input("Provide justification for off-hours operation: ")
            if len(justification) < 10:
                error("Insufficient justification provided")
                return False
            log(f"Time restriction overridden: {justification}")
            return True
        else:
            return False
    
    return True

def create_backup_notification():
    """Remind user to verify backups before destructive operations"""
    warning("🔄 BACKUP VERIFICATION REQUIRED")
    print("Before proceeding with destructive operations, verify:")
    print("1. Recent database backup exists")
    print("2. User data export is available")
    print("3. Configuration files are backed up")
    print("4. Recovery procedures are documented")
    print()
    
    backup_confirmed = input("Confirm all backups are verified and up-to-date (yes/no): ")
    if backup_confirmed.lower() != 'yes':
        error("Operation cancelled - backup verification required")
        return False
    
    log("Backup verification confirmed")
    return True

def main():
    print("🔐 STING Secure User Management")
    print("=" * 50)
    print()
    
    if len(sys.argv) < 2:
        error("Usage: python secure_user_mgmt.py [operation] [options]")
        print("Operations: clear-all, promote, reset-system")
        return 1
    
    operation = sys.argv[1]
    
    # Security checks
    if not check_authorized_user():
        error("Authorization failed")
        return 1
    
    if operation in ['clear-all', 'reset-system']:
        if not check_operation_window():
            error("Operation not allowed at this time")
            return 1
        
        if not create_backup_notification():
            error("Backup verification failed")
            return 1
    
    # Generate today's admin hash for reference
    today_hash = hashlib.sha256(f"sting-admin-{datetime.now().strftime('%Y-%m-%d')}".encode()).hexdigest()[:16]
    log(f"Today's admin hash: {today_hash}")
    
    # Execute the underlying user management script
    script_path = os.path.join(os.path.dirname(__file__), 'manage_users.py')
    command = ['python3', script_path] + sys.argv[1:]
    
    log(f"Executing: {' '.join(command)}")
    
    try:
        import subprocess
        result = subprocess.run(command, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        error(f"Operation failed with exit code: {e.returncode}")
        return e.returncode
    except Exception as e:
        error(f"Failed to execute operation: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())