#!/usr/bin/env python3
"""
Comprehensive Mailpit Validation Script for STING-CE

This script validates mailpit is properly configured for the auth flow:
1. Container is running and healthy
2. Port mappings are correct (8025:8025 not 8025:8026)
3. SMTP port 1025 accepts connections
4. Web UI port 8025 is accessible
5. End-to-end: SMTP can send and mailpit receives emails

Critical for passwordless auth, magic links, and email verification codes.
"""

import sys
import time
import smtplib
import socket
import subprocess
import json
from email.message import EmailMessage
from typing import Tuple, Optional

# Configuration
SMTP_HOST = "localhost"
SMTP_PORT = 1025
WEB_UI_HOST = "localhost"
WEB_UI_PORT = 8025
CONTAINER_NAME = "sting-ce-mailpit"
TEST_EMAIL = "healthcheck@sting.local"

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def log_info(msg: str):
    print(f"{BLUE}[INFO]{NC} {msg}")


def log_success(msg: str):
    print(f"{GREEN}[✓]{NC} {msg}")


def log_warning(msg: str):
    print(f"{YELLOW}[⚠]{NC} {msg}")


def log_error(msg: str):
    print(f"{RED}[✗]{NC} {msg}")


def check_container_status() -> Tuple[bool, str]:
    """Check if mailpit container is running and healthy"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Docker command failed"

        output = result.stdout.strip()
        if not output:
            return False, f"Container {CONTAINER_NAME} not found"

        if "Up" not in output:
            return False, f"Container is not running: {output}"

        if "healthy" not in output.lower():
            return False, f"Container is not healthy: {output}"

        return True, output

    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_port_mapping() -> Tuple[bool, str]:
    """Verify correct port mapping (8025:8025 not 8025:8026)"""
    try:
        result = subprocess.run(
            ["docker", "inspect", CONTAINER_NAME, "--format", "{{json .HostConfig.PortBindings}}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Failed to inspect container"

        port_bindings = json.loads(result.stdout)

        # Check SMTP port (1025)
        smtp_mapping = port_bindings.get("1025/tcp", [])
        if not smtp_mapping or smtp_mapping[0].get("HostPort") != "1025":
            return False, "SMTP port 1025 not correctly mapped"

        # Check Web UI port - should be 8025/tcp -> 8025 (NOT 8026/tcp)
        # The key "8025/tcp" means the container exposes 8025
        web_ui_mapping = port_bindings.get("8025/tcp", [])
        if not web_ui_mapping:
            # Check if it's incorrectly mapped from 8026
            wrong_mapping = port_bindings.get("8026/tcp", [])
            if wrong_mapping:
                return False, f"❌ INCORRECT PORT MAPPING: Container port 8026 mapped (should be 8025). Mailpit listens on 8025, not 8026!"
            return False, "Web UI port not mapped"

        if web_ui_mapping[0].get("HostPort") != str(WEB_UI_PORT):
            return False, f"Web UI host port incorrect: {web_ui_mapping[0].get('HostPort')} (expected {WEB_UI_PORT})"

        return True, f"Ports correctly mapped: 1025→1025, 8025→8025"

    except json.JSONDecodeError:
        return False, "Failed to parse port bindings"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_smtp_port() -> Tuple[bool, str]:
    """Check if SMTP port accepts connections"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((SMTP_HOST, SMTP_PORT))
        sock.close()

        if result == 0:
            return True, f"SMTP port {SMTP_PORT} is accepting connections"
        else:
            return False, f"SMTP port {SMTP_PORT} is not accepting connections"

    except Exception as e:
        return False, f"Error checking SMTP port: {str(e)}"


def check_web_ui_port() -> Tuple[bool, str]:
    """Check if Web UI port is accessible"""
    try:
        import urllib.request

        url = f"http://{WEB_UI_HOST}:{WEB_UI_PORT}/api/v1/info"
        req = urllib.request.Request(url, method='GET')

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                version = data.get('Version', 'unknown')
                msg_count = data.get('Messages', 0)
                return True, f"Web UI accessible (v{version}, {msg_count} messages)"
            else:
                return False, f"Web UI returned status {response.status}"

    except Exception as e:
        return False, f"Error accessing Web UI: {str(e)}"


def test_email_delivery() -> Tuple[bool, str]:
    """End-to-end test: Send email via SMTP and verify mailpit receives it"""
    try:
        # Get initial message count
        import urllib.request
        url = f"http://{WEB_UI_HOST}:{WEB_UI_PORT}/api/v1/messages"

        with urllib.request.urlopen(url, timeout=5) as response:
            initial_data = json.loads(response.read())
            initial_count = initial_data.get('total', 0)

        # Send test email
        msg = EmailMessage()
        msg['Subject'] = f'Mailpit Health Check - {int(time.time())}'
        msg['From'] = 'healthcheck@sting.local'
        msg['To'] = TEST_EMAIL
        msg.set_content('This is an automated health check email from STING mailpit validation.')

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.send_message(msg)

        # Wait for email to be processed
        time.sleep(2)

        # Check if email was received
        with urllib.request.urlopen(url, timeout=5) as response:
            final_data = json.loads(response.read())
            final_count = final_data.get('total', 0)

        new_emails = final_count - initial_count

        if new_emails > 0:
            return True, f"Email delivery working (sent 1, received {new_emails})"
        else:
            return False, "Email was sent but not received by mailpit"

    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Error during email test: {str(e)}"


def run_validation(quick: bool = False) -> int:
    """
    Run all validation checks

    Args:
        quick: If True, skip the email delivery test

    Returns:
        0 if all checks pass, 1 if any check fails
    """
    print("=" * 70)
    print(f"{BLUE}STING Mailpit Validation{NC}")
    print("=" * 70)
    print()

    checks = [
        ("Container Status", check_container_status),
        ("Port Mapping", check_port_mapping),
        ("SMTP Port (1025)", check_smtp_port),
        ("Web UI Port (8025)", check_web_ui_port),
    ]

    if not quick:
        checks.append(("Email Delivery (End-to-End)", test_email_delivery))

    all_passed = True

    for check_name, check_func in checks:
        log_info(f"Checking: {check_name}...")
        passed, message = check_func()

        if passed:
            log_success(f"{check_name}: {message}")
        else:
            log_error(f"{check_name}: {message}")
            all_passed = False

        print()

    print("=" * 70)
    if all_passed:
        log_success("All mailpit validation checks passed!")
        print()
        log_info(f"Mailpit Web UI: http://localhost:{WEB_UI_PORT}")
        log_info(f"Auth emails will be delivered successfully")
        print("=" * 70)
        return 0
    else:
        log_error("Some mailpit validation checks failed!")
        print()
        log_warning("Troubleshooting steps:")
        print(f"  1. Check container: docker logs {CONTAINER_NAME}")
        print(f"  2. Verify port mapping: docker port {CONTAINER_NAME}")
        print(f"  3. Run mailpit cleanup: /opt/sting-ce/lib/mailpit_lifecycle.sh restart")
        print(f"  4. Check docker-compose.yml for correct port mapping (8025:8025 not 8025:8026)")
        print("=" * 70)
        return 1


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate mailpit configuration for STING auth flow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full validation (including email delivery test)
  %(prog)s

  # Quick validation (skip email test, for healthcheck use)
  %(prog)s --quick

  # Use in healthcheck
  docker exec sting-ce-mailpit python3 /path/to/validate_mailpit.py --quick
        """
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Skip email delivery test (faster, for healthchecks)'
    )

    args = parser.parse_args()

    try:
        return run_validation(quick=args.quick)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
