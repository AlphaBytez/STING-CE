#!/usr/bin/env python3
"""
STING Admin Status Checker

This script checks the admin status of users in the STING system.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def check_admin_status():
    """Check admin users in the system"""
    try:
        from app import create_app
        from app.models.user_models import User, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            print("🐝 STING Admin Status Check")
            print("=" * 30)
            
            # Check if first admin was created
            first_admin_created = SystemSetting.get('first_admin_created', False)
            print(f"First admin created: {'✅ Yes' if first_admin_created else '❌ No'}")
            
            # Get all admin users
            admin_users = User.query.filter(
                (User.is_admin == True) | (User.is_super_admin == True)
            ).all()
            
            print(f"Total admin users: {len(admin_users)}")
            print()
            
            if admin_users:
                print("Admin Users:")
                print("-" * 50)
                for user in admin_users:
                    role = "Super Admin" if user.is_super_admin else "Admin"
                    print(f"📧 {user.email}")
                    print(f"   Role: {role}")
                    print(f"   Created: {user.created_at}")
                    print(f"   Last Login: {user.last_login_at or 'Never'}")
                    print()
            else:
                print("❌ No admin users found!")
                print()
                print("Recommendations:")
                print("1. Run: ./setup_first_admin.sh")
                print("2. Or register the first user (auto-promoted)")
                print("3. Or run: python create_admin.py --email your@email.com --temp-password")
            
            # Check total users
            total_users = User.query.count()
            print(f"Total users in system: {total_users}")
            
            if total_users == 0:
                print()
                print("💡 No users found. First registered user will be auto-promoted to admin.")
            
            return len(admin_users) > 0
            
    except Exception as e:
        print(f"❌ Error checking admin status: {e}")
        return False

def main():
    """Main function"""
    has_admin = check_admin_status()
    return 0 if has_admin else 1

if __name__ == '__main__':
    sys.exit(main())