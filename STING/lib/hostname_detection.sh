#!/bin/bash
# Hostname Detection for STING Installation
# Provides smart defaults for WebAuthn/Passkey compatibility

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
detect_system_hostname() {
    local hostname=""

    # Try to get FQDN first
    hostname=$(hostname -f 2>/dev/null)

    # If FQDN failed or returned localhost, try short hostname
    if [ -z "$hostname" ] || [ "$hostname" = "localhost" ] || [ "$hostname" = "localhost.localdomain" ]; then
        hostname=$(hostname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')
    fi

    # Return empty if still localhost
    if [ "$hostname" = "localhost" ]; then
        hostname=""
    fi

    echo "$hostname"
}

# Main function to determine STING hostname
# Returns the best hostname for WebAuthn/Passkey compatibility
get_sting_hostname() {
    local detected_hostname=""
    local default_hostname="sting.local"
    local interactive="${1:-true}"  # Default to interactive mode

    # 1. Check for explicit environment variable override
    if [ -n "$STING_HOSTNAME" ]; then
        echo "$STING_HOSTNAME"
        return 0
    fi

    # 2. Detect system hostname
    detected_hostname=$(detect_system_hostname)

    # 3. Validate detected hostname
    if [ -n "$detected_hostname" ]; then
        # Check if it's an IP address (not valid for WebAuthn)
        if is_ip_address "$detected_hostname"; then
            detected_hostname=""  # Clear it
        fi
    fi

    # 4. Interactive mode - ask user
    if [ "$interactive" = "true" ]; then
        echo "" >&2
        echo "🌐 Hostname Configuration for STING" >&2
        echo "===================================" >&2
        echo "" >&2
        echo "STING needs a hostname (not an IP) for passkey/hardware key support." >&2
        echo "" >&2

        if [ -n "$detected_hostname" ]; then
            echo "Detected hostname: $detected_hostname" >&2
        else
            echo "No hostname detected (or system uses localhost)" >&2
        fi

        echo "" >&2
        echo "Options:" >&2
        echo "  1) localhost         - Only works on this machine (no remote access)" >&2

        if [ -n "$detected_hostname" ]; then
            echo "  2) $detected_hostname  - Detected system hostname (recommended if valid)" >&2
            echo "  3) sting.local       - Generic local domain (recommended for VMs)" >&2
            echo "  4) Custom            - Enter your own" >&2
        else
            echo "  2) sting.local       - Generic local domain (recommended)" >&2
            echo "  3) Custom            - Enter your own" >&2
        fi

        echo "" >&2

        # Determine default option
        local default_option=""
        if [ -n "$detected_hostname" ]; then
            default_option="2"
            read -p "Select option [1-4] (default: 2 - $detected_hostname): " choice >&2
        else
            default_option="2"
            read -p "Select option [1-3] (default: 2 - sting.local): " choice >&2
        fi

        choice="${choice:-$default_option}"

        case "$choice" in
            1)
                echo "localhost"
                ;;
            2)
                if [ -n "$detected_hostname" ]; then
                    echo "$detected_hostname"
                else
                    echo "$default_hostname"
                fi
                ;;
            3)
                if [ -n "$detected_hostname" ]; then
                    echo "$default_hostname"
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
                # Invalid choice - use detected or default
                if [ -n "$detected_hostname" ]; then
                    echo "$detected_hostname"
                else
                    echo "$default_hostname"
                fi
                ;;
        esac
    else
        # Non-interactive mode
        # Prefer: detected hostname > sting.local > localhost
        if [ -n "$detected_hostname" ]; then
            echo "$detected_hostname"
        else
            echo "$default_hostname"
        fi
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

# Export function for use in other scripts
export -f get_sting_hostname
export -f detect_system_hostname
export -f is_ip_address
export -f show_hostname_instructions
