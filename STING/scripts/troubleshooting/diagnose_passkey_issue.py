#!/usr/bin/env python3
"""
Diagnose passkey authentication issues across different machines
"""
import os
import sys
import socket
import subprocess

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Connect to an external server to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unable to determine"

def check_env_file():
    """Check current WebAuthn configuration"""
    env_file = "env/app.env"
    current_rp_id = None
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WEBAUTHN_RP_ID='):
                    current_rp_id = line.strip().split('=')[1]
                    break
    
    return current_rp_id

def main():
    print("=" * 60)
    print("STING Passkey Cross-Machine Diagnostic Tool")
    print("=" * 60)
    
    # Get system information
    hostname = socket.gethostname()
    local_ip = get_local_ip()
    current_rp_id = check_env_file()
    
    print(f"\nSystem Information:")
    print(f"  Hostname: {hostname}")
    print(f"  Local IP: {local_ip}")
    print(f"  Current WEBAUTHN_RP_ID: {current_rp_id or 'Not set (defaults to localhost)'}")
    
    print(f"\nAccess URLs based on current configuration:")
    rp_id = current_rp_id or 'localhost'
    print(f"  Current: https://{rp_id}:8443")
    
    if rp_id == 'localhost':
        print("\n⚠️  WARNING: Using 'localhost' as RP ID")
        print("  Passkeys created on this machine will ONLY work when accessing via 'localhost'")
        print("  They will NOT work when accessing from other machines or via IP address!")
    
    print(f"\nPossible alternative configurations:")
    print(f"  1. Local IP:     https://{local_ip}:8443")
    print(f"  2. Hostname:     https://{hostname}:8443")
    print(f"  3. Localhost:    https://localhost:8443")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    
    if current_rp_id == 'localhost':
        print("\n❌ Issue Found: RP ID is set to 'localhost'")
        print("   This limits passkey usage to localhost access only.")
        print("\n   To fix this issue:")
        print(f"   1. Edit env/app.env")
        print(f"   2. Change WEBAUTHN_RP_ID to one of:")
        print(f"      - {local_ip} (for local network access)")
        print(f"      - {hostname} (if using hostname)")
        print(f"      - A proper domain name (for production)")
        print(f"   3. Run: ./manage_sting.sh update app")
        print(f"   4. Re-register all passkeys (old ones will be invalid)")
    else:
        print(f"\n✓ RP ID is configured as: {current_rp_id}")
        print(f"  Ensure all machines access STING using: https://{current_rp_id}:8443")
        print(f"  Passkeys will only work with this exact domain/IP!")
    
    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS:")
    print("\n1. For development across multiple machines:")
    print(f"   - Set WEBAUTHN_RP_ID={local_ip} in env/app.env")
    print(f"   - Access from all machines using: https://{local_ip}:8443")
    print("\n2. For production:")
    print("   - Use a proper domain name (e.g., sting.yourdomain.com)")
    print("   - Set WEBAUTHN_RP_ID=sting.yourdomain.com")
    print("\n3. After changing RP ID:")
    print("   - Run: ./manage_sting.sh update app")
    print("   - Delete and re-register all passkeys")
    
    # Check if user wants to update
    if current_rp_id == 'localhost':
        print("\n" + "=" * 60)
        response = input(f"\nWould you like to update WEBAUTHN_RP_ID to {local_ip}? (y/n): ")
        if response.lower() == 'y':
            try:
                # Read current env file
                with open('env/app.env', 'r') as f:
                    lines = f.readlines()
                
                # Update or add WEBAUTHN_RP_ID
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith('WEBAUTHN_RP_ID='):
                        lines[i] = f'WEBAUTHN_RP_ID={local_ip}\n'
                        updated = True
                        break
                
                if not updated:
                    lines.append(f'\n# WebAuthn Configuration\n')
                    lines.append(f'WEBAUTHN_RP_ID={local_ip}\n')
                
                # Write back
                with open('env/app.env', 'w') as f:
                    f.writelines(lines)
                
                print(f"\n✅ Updated WEBAUTHN_RP_ID to {local_ip}")
                print("\nNext steps:")
                print("1. Run: ./manage_sting.sh update app")
                print("2. Clear browser data/cookies")
                print(f"3. Access STING using: https://{local_ip}:8443")
                print("4. Re-register your passkeys")
                
            except Exception as e:
                print(f"\n❌ Error updating configuration: {e}")

if __name__ == "__main__":
    main()