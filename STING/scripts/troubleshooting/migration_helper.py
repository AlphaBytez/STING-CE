#!/usr/bin/env python3
"""
STING Migration Helper

Handles migration scenarios where:
- Users exist from previous installations
- No super admin exists (e.g., after restore from backup)
- Passkey data may or may not be preserved
- Manual intervention is needed for super admin assignment

Usage:
    python migration_helper.py [command] [options]

Commands:
    analyze         Analyze current user situation
    enable-migration Enable migration mode for automatic promotion
    promote-user    Manually promote a specific user to super admin
    list-candidates List potential super admin candidates
    backup-check    Check what data needs to be backed up
"""

import os
import sys
import argparse
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
NC = '\033[0m'

def log(message):
    print(f"{GREEN}[MIGRATION]{NC} {message}")

def warning(message):
    print(f"{YELLOW}[WARNING]{NC} {message}")

def error(message):
    print(f"{RED}[ERROR]{NC} {message}")

def info(message):
    print(f"{BLUE}[INFO]{NC} {message}")

def analyze_system():
    """Analyze current user and admin situation"""
    try:
        from app import create_app
        from app.models.user_models import User, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            # Get user counts
            total_users = User.query.count()
            super_admins = User.query.filter_by(is_super_admin=True).count()
            admins = User.query.filter_by(is_admin=True).count()
            regular_users = total_users - admins - super_admins
            
            log("System Analysis Results")
            print("=" * 50)
            print(f"Total Users: {total_users}")
            print(f"Super Admins: {super_admins}")
            print(f"Admins: {admins}")
            print(f"Regular Users: {regular_users}")
            print()
            
            # Check for migration scenarios
            if total_users > 0 and super_admins == 0:
                warning("🚨 MIGRATION SCENARIO DETECTED")
                warning("Users exist but no super admin found!")
                print()
                
                # Show oldest user
                oldest_user = User.query.order_by(User.created_at.asc()).first()
                print(f"Oldest User: {oldest_user.email} (created: {oldest_user.created_at})")
                
                # Show existing admins
                existing_admins = User.query.filter_by(is_admin=True).all()
                if existing_admins:
                    print("\nExisting Admins:")
                    for admin in existing_admins:
                        print(f"  - {admin.email} (created: {admin.created_at})")
                
                # Show candidates
                candidates = SystemSetting.get('super_admin_candidates', [])
                if candidates:
                    print("\nPotential Super Admin Candidates:")
                    for candidate in candidates:
                        print(f"  - {candidate.get('email')} (logged: {candidate.get('candidate_timestamp')})")
                
                print("\nRecommendations:")
                print("1. Run 'python migration_helper.py enable-migration' to enable auto-promotion")
                print("2. Or manually promote a user with 'python migration_helper.py promote-user --email user@example.com'")
                
            elif super_admins > 0:
                info("✅ System has super admin(s) - no migration needed")
                super_admin_users = User.query.filter_by(is_super_admin=True).all()
                for su in super_admin_users:
                    print(f"Super Admin: {su.email}")
            
            else:
                info("Fresh system - first user will become super admin automatically")
            
            # Check system settings
            print("\nSystem Settings:")
            first_admin_created = SystemSetting.get('first_super_admin_created', False)
            print(f"First Super Admin Created: {first_admin_created}")
            
            scenario = SystemSetting.get('super_admin_creation_scenario', 'Not set')
            print(f"Creation Scenario: {scenario}")
            
            migration_mode = SystemSetting.get('migration_super_admin_mode', False)
            print(f"Migration Mode: {migration_mode}")
            
            return True
            
    except Exception as e:
        error(f"Error analyzing system: {e}")
        return False

def enable_migration_mode():
    """Enable migration mode for automatic super admin promotion"""
    try:
        from app import create_app
        from app.models.user_models import SystemSetting
        from app.database import db
        
        app = create_app()
        
        with app.app_context():
            # Enable migration mode
            SystemSetting.set(
                'migration_super_admin_mode',
                True,
                'Migration mode enabled - allows automatic super admin promotion',
                f'migration_enabled_{datetime.utcnow().isoformat()}'
            )
            
            db.session.commit()
            
            log("✅ Migration mode enabled")
            log("Next admin user to log in will be promoted to super admin")
            warning("Remember to disable migration mode after promotion!")
            
            return True
            
    except Exception as e:
        error(f"Error enabling migration mode: {e}")
        return False

def promote_user_manually(email):
    """Manually promote a specific user to super admin"""
    try:
        from app import create_app
        from app.models.user_models import User, SystemSetting
        from app.database import db
        
        app = create_app()
        
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            
            if not user:
                error(f"User {email} not found")
                return False
            
            if user.is_super_admin:
                warning(f"User {email} is already a super admin")
                return True
            
            # Check if any super admin exists
            existing_super_admin = User.query.filter_by(is_super_admin=True).first()
            
            if existing_super_admin:
                warning("A super admin already exists:")
                warning(f"Existing: {existing_super_admin.email}")
                response = input("Continue with promotion anyway? (yes/no): ")
                if response.lower() != 'yes':
                    info("Promotion cancelled")
                    return False
            
            # Promote the user
            user._setup_as_first_super_admin("MANUAL_PROMOTION")
            
            log(f"✅ Successfully promoted {email} to super admin")
            log("User will be required to change password on next login")
            
            # Disable migration mode if it was enabled
            SystemSetting.set(
                'migration_super_admin_mode',
                False,
                'Migration mode disabled after manual promotion',
                f'migration_disabled_{datetime.utcnow().isoformat()}'
            )
            
            return True
            
    except Exception as e:
        error(f"Error promoting user: {e}")
        return False

def list_candidates():
    """List potential super admin candidates"""
    try:
        from app import create_app
        from app.models.user_models import User, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            candidates = SystemSetting.get('super_admin_candidates', [])
            
            if not candidates:
                info("No super admin candidates logged")
                info("Users will be logged as candidates when they attempt login")
                return True
            
            log("Super Admin Candidates:")
            print("=" * 60)
            
            for candidate in candidates:
                user = User.query.get(candidate.get('user_id'))
                if user:
                    print(f"Email: {candidate.get('email')}")
                    print(f"  User ID: {candidate.get('user_id')}")
                    print(f"  Created: {candidate.get('created_at')}")
                    print(f"  Is Admin: {candidate.get('is_admin')}")
                    print(f"  Candidate Since: {candidate.get('candidate_timestamp')}")
                    print(f"  Current Status: {'Active' if user.status.value == 'active' else user.status.value}")
                    print()
            
            print("To promote a candidate:")
            print("python migration_helper.py promote-user --email <email>")
            
            return True
            
    except Exception as e:
        error(f"Error listing candidates: {e}")
        return False

def backup_check():
    """Check what data needs to be backed up for proper migration"""
    log("STING Backup Requirements")
    print("=" * 50)
    
    print("CRITICAL DATA TO BACKUP:")
    print()
    print("1. 📄 Database (PostgreSQL)")
    print("   - User accounts and roles")
    print("   - System settings")
    print("   - Session data")
    print("   - Emergency recovery codes (encrypted)")
    print()
    print("2. 🔐 Kratos Data")
    print("   - Identity database")
    print("   - Passkey/WebAuthn credentials")
    print("   - Password hashes")
    print("   - Identity schemas")
    print()
    print("3. ⚙️  Configuration Files")
    print("   - conf/config.yml")
    print("   - env/*.env files")
    print("   - Kratos configuration")
    print()
    print("4. 🔒 Vault Data (if using)")
    print("   - Vault tokens and policies")
    print("   - Encrypted secrets")
    print()
    print("5. 📊 Application Data")
    print("   - LLM model configurations")
    print("   - User-generated content")
    print("   - Chat histories")
    print()
    
    warning("MIGRATION CONSIDERATIONS:")
    print("• Passkey data is stored in Kratos - ensure Kratos DB is backed up")
    print("• Recovery codes are encrypted in user table")
    print("• First login after restore will trigger super admin promotion logic")
    print("• Test restore process in staging environment first")
    print()
    
    info("BACKUP SCRIPT LOCATIONS:")
    print("• Database: pg_dump or docker volume backup")
    print("• Kratos: Back up kratos container volume")
    print("• Config: Copy entire conf/ and env/ directories")
    print()

def main():
    parser = argparse.ArgumentParser(
        description='STING Migration Helper',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('command', choices=['analyze', 'enable-migration', 'promote-user', 'list-candidates', 'backup-check'],
                       help='Command to execute')
    parser.add_argument('--email', help='Email address for promote-user command')
    
    args = parser.parse_args()
    
    print("🔄 STING Migration Helper")
    print("=" * 40)
    print()
    
    if args.command == 'analyze':
        success = analyze_system()
    elif args.command == 'enable-migration':
        success = enable_migration_mode()
    elif args.command == 'promote-user':
        if not args.email:
            error("--email required for promote-user command")
            return 1
        success = promote_user_manually(args.email)
    elif args.command == 'list-candidates':
        success = list_candidates()
    elif args.command == 'backup-check':
        backup_check()
        success = True
    else:
        error(f"Unknown command: {args.command}")
        return 1
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())