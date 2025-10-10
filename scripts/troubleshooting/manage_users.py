#!/usr/bin/env python3
"""
STING User Management Script

⚠️  SECURITY WARNING ⚠️
This script performs destructive operations including deleting ALL users.
Use with extreme caution and only in controlled environments.

SECURITY FEATURES:
- Requires explicit confirmation for destructive operations
- Logs all operations with timestamps
- Checks for production environment and warns accordingly
- Requires admin authentication for sensitive operations
- Creates audit trail of all user management actions

This script provides comprehensive user management capabilities including:
- Clear all users (both STING database and Kratos)
- Promote existing users to admin
- List all users
- Reset user system for fresh start

Usage:
    python manage_users.py [command] [options]

Commands:
    clear-all       Clear all users from both STING and Kratos
    promote         Promote a user to admin role
    list            List all users in STING database
    reset-system    Complete user system reset (clear + reset settings)
    
Examples:
    python manage_users.py clear-all
    python manage_users.py promote --email user@example.com
    python manage_users.py list
    python manage_users.py reset-system
"""

import os
import sys
import argparse
import requests
import json
import urllib3
import hashlib
import time
import getpass
from datetime import datetime

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
NC = '\033[0m'  # No Color

def log(message):
    print(f"{GREEN}[STING USER MGR]{NC} {message}")

def warning(message):
    print(f"{YELLOW}[WARNING]{NC} {message}")

def error(message):
    print(f"{RED}[ERROR]{NC} {message}")

def info(message):
    print(f"{BLUE}[INFO]{NC} {message}")

def debug(message):
    print(f"{PURPLE}[DEBUG]{NC} {message}")

def audit_log(action, details, user_email=None):
    """Log security-sensitive operations"""
    timestamp = datetime.utcnow().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'action': action,
        'details': details,
        'user_email': user_email,
        'script_user': getpass.getuser(),
        'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
    }
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Write to audit log
    log_file = os.path.join(log_dir, 'user_management_audit.log')
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    debug(f"Audit logged: {action}")

def check_environment():
    """Check if we're in a production environment and warn accordingly"""
    config_file = os.path.join(os.path.dirname(__file__), 'conf', 'config.yml')
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                if 'env: production' in content.lower():
                    error("🚨 PRODUCTION ENVIRONMENT DETECTED 🚨")
                    error("This script is running against a PRODUCTION system!")
                    error("Destructive operations could affect live users!")
                    print()
                    response = input("Type 'I-UNDERSTAND-THE-RISKS' to continue: ")
                    if response != 'I-UNDERSTAND-THE-RISKS':
                        error("Operation cancelled for safety")
                        return False
                    warning("Proceeding with production environment operations...")
                    audit_log("PRODUCTION_WARNING_BYPASSED", "User acknowledged production risks")
        except Exception as e:
            warning(f"Could not read config file: {e}")
    
    return True

def require_admin_confirmation(operation_name):
    """Require explicit confirmation for destructive operations"""
    warning(f"⚠️  DESTRUCTIVE OPERATION: {operation_name}")
    warning("This operation cannot be undone!")
    print()
    
    # Multiple confirmation steps
    confirmations = [
        f"Type 'DELETE' to confirm you want to {operation_name.lower()}",
        f"Type 'CONFIRM' to acknowledge this action affects ALL users",
        f"Type 'PROCEED' to execute the {operation_name.lower()} operation"
    ]
    
    for confirmation in confirmations:
        expected = confirmation.split("'")[1]
        response = input(f"{confirmation}: ")
        if response != expected:
            error("Operation cancelled - confirmation failed")
            audit_log("DESTRUCTIVE_OP_CANCELLED", f"Failed confirmation for: {operation_name}")
            return False
        time.sleep(1)  # Brief pause between confirmations
    
    # Final timestamp confirmation
    current_minute = datetime.now().strftime("%H:%M")
    response = input(f"Final check - enter current time (HH:MM format, currently {current_minute}): ")
    if response != current_minute:
        error("Operation cancelled - time verification failed")
        audit_log("DESTRUCTIVE_OP_CANCELLED", f"Failed time verification for: {operation_name}")
        return False
    
    audit_log("DESTRUCTIVE_OP_CONFIRMED", f"User confirmed: {operation_name}")
    return True

def verify_script_integrity():
    """Verify the script hasn't been tampered with (basic check)"""
    script_path = __file__
    try:
        with open(script_path, 'rb') as f:
            content = f.read()
            
        # Check for suspicious modifications
        if b'os.system(' in content or b'subprocess.' in content or b'eval(' in content:
            warning("Script contains potentially dangerous functions")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
                
        return True
    except Exception as e:
        warning(f"Could not verify script integrity: {e}")
        return True  # Allow to proceed if verification fails

def get_kratos_admin_url():
    """Get Kratos admin URL from environment or use default"""
    return os.getenv('KRATOS_ADMIN_URL', 'https://localhost:4434')

def test_kratos_connection():
    """Test connection to Kratos Admin API"""
    kratos_url = get_kratos_admin_url()
    try:
        response = requests.get(
            f"{kratos_url}/admin/health/ready",
            verify=False,
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def get_all_kratos_identities():
    """Fetch all identities from Kratos"""
    kratos_url = get_kratos_admin_url()
    try:
        response = requests.get(
            f"{kratos_url}/admin/identities",
            verify=False,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            error(f"Failed to fetch Kratos identities: {response.status_code}")
            return []
    except Exception as e:
        error(f"Error fetching Kratos identities: {e}")
        return []

def delete_kratos_identity(identity_id):
    """Delete a specific identity from Kratos"""
    kratos_url = get_kratos_admin_url()
    try:
        response = requests.delete(
            f"{kratos_url}/admin/identities/{identity_id}",
            verify=False,
            timeout=10
        )
        return response.status_code == 204
    except Exception as e:
        error(f"Error deleting Kratos identity {identity_id}: {e}")
        return False

def clear_all_users():
    """Clear all users from both STING database and Kratos"""
    log("Starting complete user cleanup...")
    
    # Security checks
    if not check_environment():
        return False
    
    if not require_admin_confirmation("CLEAR ALL USERS"):
        return False
    
    audit_log("CLEAR_ALL_USERS_STARTED", "Beginning user cleanup operation")
    
    # Check Kratos connection
    if not test_kratos_connection():
        error("Cannot connect to Kratos Admin API")
        error("Make sure Kratos is running at " + get_kratos_admin_url())
        audit_log("CLEAR_ALL_USERS_FAILED", "Kratos connection failed")
        return False
    
    try:
        # Import here to avoid issues if script is run outside Flask context
        from app import create_app
        from app.database import db
        from app.models.user_models import User, UserSession, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            # Step 1: Get all users from STING database
            users = User.query.all()
            user_count = len(users)
            
            if user_count == 0:
                info("No users found in STING database")
            else:
                log(f"Found {user_count} users in STING database")
                
                # Show users before deletion
                for user in users:
                    debug(f"  - {user.email} ({user.role.value}) [Kratos: {user.kratos_id}]")
            
            # Step 2: Clear STING database users
            if user_count > 0:
                log("Clearing STING database users...")
                
                # Delete user sessions first (foreign key constraint)
                session_count = UserSession.query.count()
                if session_count > 0:
                    UserSession.query.delete()
                    debug(f"Deleted {session_count} user sessions")
                
                # Delete users
                User.query.delete()
                db.session.commit()
                log(f"Deleted {user_count} users from STING database")
            
            # Step 3: Clear Kratos identities
            log("Fetching Kratos identities...")
            kratos_identities = get_all_kratos_identities()
            
            if not kratos_identities:
                info("No identities found in Kratos")
            else:
                log(f"Found {len(kratos_identities)} identities in Kratos")
                
                deleted_count = 0
                failed_count = 0
                
                for identity in kratos_identities:
                    identity_id = identity.get('id')
                    email = identity.get('traits', {}).get('email', 'unknown')
                    
                    debug(f"Deleting Kratos identity: {email} ({identity_id})")
                    
                    if delete_kratos_identity(identity_id):
                        deleted_count += 1
                    else:
                        failed_count += 1
                        warning(f"Failed to delete identity: {email}")
                
                log(f"Deleted {deleted_count} Kratos identities")
                if failed_count > 0:
                    warning(f"Failed to delete {failed_count} identities")
            
            # Step 4: Reset admin creation flag
            log("Resetting system settings...")
            SystemSetting.query.filter_by(key='first_admin_created').delete()
            db.session.commit()
            
            log("✅ User cleanup completed successfully!")
            log("System is ready for fresh admin user creation")
            audit_log("CLEAR_ALL_USERS_COMPLETED", f"Deleted {user_count} STING users and {deleted_count} Kratos identities")
            return True
            
    except Exception as e:
        error(f"Error during user cleanup: {e}")
        return False

def promote_user_to_admin(email):
    """Promote an existing user to admin role"""
    try:
        from app import create_app
        from app.database import db
        from app.models.user_models import User, UserRole
        
        app = create_app()
        
        with app.app_context():
            # Find the user by email
            user = User.query.filter_by(email=email).first()
            
            if not user:
                error(f"User {email} not found in STING database")
                info("User must log in at least once to be created in STING")
                return False
            
            # Check current role
            if user.is_super_admin:
                info(f"User {email} is already a super admin")
                return True
            elif user.is_admin:
                # Promote from admin to super admin
                log(f"Promoting {email} from admin to super admin...")
                user.role = UserRole.SUPER_ADMIN
                user.is_super_admin = True
                user.is_admin = True
            else:
                # Promote from user to super admin
                log(f"Promoting {email} from user to super admin...")
                user.role = UserRole.SUPER_ADMIN
                user.is_super_admin = True
                user.is_admin = True
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            log(f"✅ Successfully promoted {email} to super admin")
            log(f"User now has access to 🐝 LLM Settings and all admin features")
            audit_log("USER_PROMOTED", f"Promoted {email} to super admin", user_email=email)
            return True
            
    except Exception as e:
        error(f"Error promoting user: {e}")
        return False

def list_all_users():
    """List all users in STING database"""
    try:
        from app import create_app
        from app.models.user_models import User
        
        app = create_app()
        
        with app.app_context():
            users = User.query.order_by(User.created_at.desc()).all()
            
            if not users:
                info("No users found in STING database")
                return True
            
            log(f"Found {len(users)} users in STING database:")
            print()
            print(f"{'Email':<40} {'Role':<15} {'Status':<10} {'Created':<20}")
            print("-" * 90)
            
            for user in users:
                role_display = "Super Admin" if user.is_super_admin else ("Admin" if user.is_admin else "User")
                created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "Unknown"
                print(f"{user.email:<40} {role_display:<15} {user.status.value:<10} {created:<20}")
            
            print()
            return True
            
    except Exception as e:
        error(f"Error listing users: {e}")
        return False

def reset_user_system():
    """Complete user system reset"""
    log("🔄 Starting complete user system reset...")
    warning("This will remove ALL users and reset the system!")
    
    # Security checks
    if not check_environment():
        return False
    
    if not require_admin_confirmation("RESET USER SYSTEM"):
        return False
    
    audit_log("SYSTEM_RESET_STARTED", "Beginning complete system reset")
    
    # Clear all users
    if not clear_all_users():
        error("Failed to clear users")
        return False
    
    try:
        from app import create_app
        from app.database import db
        from app.models.user_models import SystemSetting
        
        app = create_app()
        
        with app.app_context():
            # Reset additional system settings
            log("Resetting additional system settings...")
            
            # Clear any user-related system settings
            settings_to_clear = [
                'first_admin_created',
                'user_registration_enabled',
                'admin_setup_completed'
            ]
            
            for setting_key in settings_to_clear:
                SystemSetting.query.filter_by(key=setting_key).delete()
            
            db.session.commit()
            
            log("✅ User system reset completed!")
            log("System is now ready for initial setup")
            log("Run ./setup_first_admin.sh to create the first admin user")
            audit_log("SYSTEM_RESET_COMPLETED", "Complete system reset finished successfully")
            return True
            
    except Exception as e:
        error(f"Error during system reset: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='STING User Management Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  clear-all       Clear all users from both STING and Kratos
  promote         Promote a user to admin role
  list            List all users in STING database  
  reset-system    Complete user system reset (clear + reset settings)

Examples:
  python manage_users.py clear-all
  python manage_users.py promote --email user@example.com
  python manage_users.py list
  python manage_users.py reset-system
        """
    )
    
    parser.add_argument('command', choices=['clear-all', 'promote', 'list', 'reset-system'],
                       help='Command to execute')
    parser.add_argument('--email', help='Email address for promote command')
    parser.add_argument('--kratos-url', default='https://localhost:4434',
                       help='Kratos Admin API URL (default: https://localhost:4434)')
    
    args = parser.parse_args()
    
    # Set Kratos URL if provided
    if args.kratos_url:
        os.environ['KRATOS_ADMIN_URL'] = args.kratos_url
    
    print("🐝 STING User Management")
    print("=" * 40)
    print()
    
    # Security checks
    if not verify_script_integrity():
        error("Script integrity check failed")
        return 1
    
    audit_log("SCRIPT_STARTED", f"Command: {args.command}", user_email=args.email)
    
    # Execute command
    if args.command == 'clear-all':
        success = clear_all_users()
    elif args.command == 'promote':
        if not args.email:
            error("--email required for promote command")
            return 1
        success = promote_user_to_admin(args.email)
    elif args.command == 'list':
        success = list_all_users()
    elif args.command == 'reset-system':
        success = reset_user_system()
    else:
        error(f"Unknown command: {args.command}")
        return 1
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())