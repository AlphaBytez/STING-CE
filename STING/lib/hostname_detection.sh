#!/bin/bash
# Hostname Detection for STING Installation
# Provides smart defaults for WebAuthn/Passkey compatibility
#
# Prefers hostnames over IPs for WebAuthn consistency. IP is only used as fallback.

# Function to check if a string is an IP address
is_ip_address() {
    local value="$1"
    # Check if it matches IP pattern
    if [[ "$value" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 0  # Is an IP
    fi
    return 1  # Not an IP
}

# Function to detect system hostname
# Prefers hostnames over IPs for WebAuthn consistency
detect_system_hostname() {
    local hostname=""

    # Strategy 1: Try FQDN (if it's a proper domain, not localhost)
    hostname=$(hostname -f 2>/dev/null)
    if [ -n "$hostname" ] && [ "$hostname" != "localhost" ] && [ "$hostname" != "localhost.localdomain" ] && [[ "$hostname" =~ \. ]]; then
        # Valid FQDN (has dot and isn't localhost)
        echo "$hostname"
        return 0
    fi

    # Strategy 2: Try short hostname with .local appended (good for VMs)
    hostname=$(hostname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')
    if [ -n "$hostname" ] && [ "$hostname" != "localhost" ]; then
        # Append .local for mDNS/local network resolution
        echo "${hostname}.local"
        return 0
    fi

    # Strategy 3: Use primary IP address (fallback for when no hostname is available)
    local primary_ip=""

    # Linux: hostname -I
    if command -v hostname &>/dev/null && hostname -I &>/dev/null 2>&1; then
        primary_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    # macOS: ifconfig
    elif command -v ifconfig &>/dev/null; then
        primary_ip=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
    fi

    if [ -n "$primary_ip" ] && [[ ! "$primary_ip" =~ ^127\. ]]; then
        # Valid IP that's not loopback
        echo "$primary_ip"
        return 0
    fi

    # Fallback: Use sting.local
    echo "sting.local"
}

# Main function to determine STING hostname
# Returns the best hostname for WebAuthn/Passkey compatibility
get_sting_hostname() {
    local detected_hostname=""
    local default_hostname="sting.local"
    local interactive="${1:-true}"  # Default to interactive mode

    # 1. Check for explicit environment variable override
    # Use ${STING_HOSTNAME:-} to avoid unbound variable error with set -u
    if [ -n "${STING_HOSTNAME:-}" ]; then
        echo "$STING_HOSTNAME"
        return 0
    fi

    # 2. Detect system hostname
    detected_hostname=$(detect_system_hostname)

    # 3. Interactive mode - ask user
    if [ "$interactive" = "true" ]; then
        echo "" >&2
        echo "🌐 Hostname Configuration for STING" >&2
        echo "===================================" >&2
        echo "" >&2
        echo "STING needs a hostname or IP address for WebAuthn/passkey support." >&2
        echo "" >&2

        # Check if running in GitHub Codespaces
        if [ -n "${CODESPACES:-}" ] || [ -n "${CODESPACE_NAME:-}" ]; then
            echo "⚠️  GitHub Codespaces detected!" >&2
            echo "   .local domains won't work in Codespaces." >&2
            echo "   Use 'localhost' or forward ports and use the Codespaces URL." >&2
            echo "" >&2
        fi

        if [ -n "$detected_hostname" ]; then
            echo "Detected hostname: $detected_hostname" >&2
        else
            echo "No hostname detected (or system uses localhost)" >&2
        fi

        echo "" >&2
        echo "Options:" >&2
        echo "  1) sting.local       - Simple local domain (recommended for local VMs)" >&2
        echo "  2) localhost         - Only works on this machine (good for Codespaces)" >&2

        if [ -n "$detected_hostname" ]; then
            echo "  3) $detected_hostname  - Use detected system hostname" >&2
            echo "  4) Custom            - Enter your own" >&2
        else
            echo "  3) Custom            - Enter your own" >&2
        fi

        echo "" >&2

        # Default to sting.local (option 1)
        local default_option="1"
        if [ -n "$detected_hostname" ]; then
            read -p "Select option [1-4] (default: 1 - sting.local): " choice >&2
        else
            read -p "Select option [1-3] (default: 1 - sting.local): " choice >&2
        fi

        choice="${choice:-$default_option}"

        case "$choice" in
            1)
                echo "$default_hostname"
                ;;
            2)
                echo "localhost"
                ;;
            3)
                if [ -n "$detected_hostname" ]; then
                    echo "$detected_hostname"
                else
                    read -p "Enter custom hostname: " custom_hostname >&2
                    echo "${custom_hostname:-$default_hostname}"
                fi
                ;;
            4)
                read -p "Enter custom hostname: " custom_hostname >&2
                echo "${custom_hostname:-$default_hostname}"
                ;;
            *)
                # Invalid choice - use default (sting.local)
                echo "$default_hostname"
                ;;
        esac
    else
        # Non-interactive mode
        # Always prefer sting.local for consistency
        echo "$default_hostname"
    fi
}

# Function to display hostname setup instructions
show_hostname_instructions() {
    local hostname="$1"

    echo ""
    echo "📝 Hostname Setup Instructions"
    echo "=============================="
    echo ""

    if [ "$hostname" = "localhost" ]; then
        echo "✅ Using localhost - no additional setup needed"
        echo "⚠️  NOTE: Passkeys will only work on this machine"
        echo "   For multi-device access, consider using a custom hostname"
    else
        echo "✅ Using hostname: $hostname"
        echo ""
        echo "For remote access, add this to /etc/hosts on client machines:"
        echo ""
        echo "  <STING_SERVER_IP>  $hostname"
        echo ""
        echo "Example:"
        echo "  192.168.1.100  $hostname"
        echo ""
        echo "Then access STING at: https://$hostname:8443"
    fi

    echo ""
}

# Function to detect if running in WSL2
is_wsl2() {
    # Check for WSLInterop (definitive WSL2 marker)
    if [ -f /proc/sys/fs/binfmt_misc/WSLInterop ]; then
        return 0  # Is WSL2
    fi

    # Fallback: Check for "microsoft" in kernel version
    if grep -qi microsoft /proc/version 2>/dev/null; then
        return 0  # Is WSL2 (or WSL1)
    fi

    return 1  # Not WSL2
}

# Function to get Windows hosts file path from WSL2
get_windows_hosts_path() {
    # Standard Windows hosts file location (accessible from WSL2)
    local win_hosts="/mnt/c/Windows/System32/drivers/etc/hosts"

    if [ -f "$win_hosts" ]; then
        echo "$win_hosts"
        return 0
    fi

    # Try alternate drive letter
    win_hosts="/mnt/d/Windows/System32/drivers/etc/hosts"
    if [ -f "$win_hosts" ]; then
        echo "$win_hosts"
        return 0
    fi

    return 1  # Not found
}

# Function to update Windows hosts file from WSL2
update_windows_hosts() {
    local hostname="$1"
    local ip_address="$2"
    local windows_hosts=""

    if ! is_wsl2; then
        echo "Not running in WSL2 - skipping Windows hosts file update" >&2
        return 1
    fi

    windows_hosts=$(get_windows_hosts_path)
    if [ -z "$windows_hosts" ]; then
        echo "Could not locate Windows hosts file" >&2
        return 1
    fi

    echo "Updating Windows hosts file: $windows_hosts" >&2

    # Check if entry already exists
    if grep -q "[[:space:]]$hostname" "$windows_hosts" 2>/dev/null; then
        echo "  Entry for $hostname already exists in Windows hosts file" >&2

        # Try to remove old entry (may fail due to permissions)
        if sudo sed -i.backup "/$hostname/d" "$windows_hosts" 2>/dev/null; then
            echo "  ✓ Removed old entry" >&2
        else
            echo "  ⚠ Could not remove old entry (permission denied)" >&2
            echo "  Please manually edit: C:\\Windows\\System32\\drivers\\etc\\hosts" >&2
            echo "  Remove lines containing: $hostname" >&2
            return 1
        fi
    fi

    # Add new entry
    if echo "$ip_address  $hostname  # Added by STING installer" | sudo tee -a "$windows_hosts" >/dev/null 2>&1; then
        echo "  ✅ Windows hosts file updated successfully" >&2
        return 0
    else
        echo "  ⚠ Could not update Windows hosts file (permission denied)" >&2
        echo "" >&2
        echo "  📝 Manual step required:" >&2
        echo "  1. Open Notepad as Administrator (Windows)" >&2
        echo "  2. Open: C:\\Windows\\System32\\drivers\\etc\\hosts" >&2
        echo "  3. Add this line:" >&2
        echo "     $ip_address  $hostname" >&2
        echo "" >&2
        return 1
    fi
}

# Function to verify hostname resolves
verify_hostname_resolves() {
    local hostname="$1"

    # Skip verification for localhost (always works)
    if [ "$hostname" = "localhost" ]; then
        return 0
    fi

    # Skip verification for IP addresses (no DNS needed)
    if is_ip_address "$hostname"; then
        return 0
    fi

    echo "Testing hostname resolution for: $hostname" >&2

    # Try ping (may be blocked by firewall)
    if ping -c 1 -W 2 "$hostname" >/dev/null 2>&1; then
        echo "✅ Hostname resolves via ping" >&2
        return 0
    fi

    # Try getent hosts (DNS lookup)
    if command -v getent &>/dev/null; then
        if getent hosts "$hostname" >/dev/null 2>&1; then
            echo "✅ Hostname resolves via DNS" >&2
            return 0
        fi
    fi

    # Try nslookup
    if command -v nslookup &>/dev/null; then
        if nslookup "$hostname" >/dev/null 2>&1; then
            echo "✅ Hostname resolves via nslookup" >&2
            return 0
        fi
    fi

    # Check /etc/hosts manually
    if grep -q "[[:space:]]$hostname" /etc/hosts 2>/dev/null; then
        echo "✅ Hostname found in /etc/hosts" >&2
        return 0
    fi

    echo "⚠ Could not verify hostname resolution" >&2
    return 1
}

# Export function for use in other scripts
export -f get_sting_hostname
export -f detect_system_hostname
export -f is_ip_address
export -f show_hostname_instructions
export -f is_wsl2
export -f get_windows_hosts_path
export -f update_windows_hosts
export -f verify_hostname_resolves
