#!/bin/bash
# Domain management functions for STING local domain system

# Define log_message if not already defined
if ! declare -f log_message >/dev/null 2>&1; then
    log_message() {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    }
fi

# Define STING_INSTALL_DIR if not set
if [[ -z "$STING_INSTALL_DIR" ]]; then
    STING_INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
fi

# Get unique machine identifier (8 chars)
get_machine_id() {
    local machine_id=""
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Use hardware UUID
        machine_id=$(ioreg -d2 -c IOPlatformExpertDevice | awk -F\" '/IOPlatformUUID/{print $4}' | tr '[:upper:]' '[:lower:]' | cut -c1-8)
        if [[ -n "$machine_id" ]]; then
            echo "mac-${machine_id}"
            return 0
        fi
    elif [[ -f /etc/machine-id ]]; then
        # Linux: Use machine-id
        machine_id=$(cat /etc/machine-id | cut -c1-8)
        if [[ -n "$machine_id" ]]; then
            echo "linux-${machine_id}"
            return 0
        fi
    fi
    
    # Fallback: Use hostname + MAC address
    local hostname_part=$(hostname -s | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g' | cut -c1-4)
    local mac_part=$(ifconfig 2>/dev/null | grep -o -E '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}' | head -1 | tr -d ':' | cut -c1-4)
    
    if [[ -n "$hostname_part" && -n "$mac_part" ]]; then
        echo "${hostname_part}-${mac_part}"
    else
        # Last resort: Random ID
        echo "sting-$(openssl rand -hex 4)"
    fi
}

# Generate STING local domain
generate_sting_domain() {
    local custom_prefix="$1"
    
    # Use .hive instead of .local to avoid macOS Bonjour conflicts
    # .hive is not a registered TLD and fits the bee theme
    local tld="hive"
    
    if [[ -n "$custom_prefix" ]]; then
        # Validate custom prefix (alphanumeric and hyphens only)
        if [[ "$custom_prefix" =~ ^[a-z0-9-]+$ ]]; then
            echo "${custom_prefix}.sting.${tld}"
        else
            echo "Error: Invalid domain prefix. Use only lowercase letters, numbers, and hyphens." >&2
            return 1
        fi
    else
        # Generate from machine ID
        local machine_id=$(get_machine_id)
        echo "${machine_id}.sting.${tld}"
    fi
}

# Check if mDNS is available
check_mdns_support() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS has built-in mDNS support
        command -v dns-sd >/dev/null 2>&1
        return $?
    else
        # Linux: Check for Avahi
        command -v avahi-publish >/dev/null 2>&1
        return $?
    fi
}

# Register mDNS service
register_mdns_service() {
    local domain="$1"
    local port="${2:-8443}"
    local service_name="STING CE"
    
    # Extract hostname from domain (supports both .local and .hive)
    local hostname="${domain%.sting.*}"
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Use dns-sd
        # Register both the hostname and the service
        dns-sd -R "$service_name" _https._tcp local $port "path=/" "domain=$domain" &
        local dns_pid=$!
        
        # Also register the hostname
        dns-sd -P "$hostname" _https._tcp local $port "$domain" 127.0.0.1 &
        local host_pid=$!
        
        # Store PIDs for cleanup
        echo "$dns_pid" > "${STING_INSTALL_DIR}/.mdns_service.pid"
        echo "$host_pid" >> "${STING_INSTALL_DIR}/.mdns_service.pid"
        
        log_message "mDNS service registered for $domain (PIDs: $dns_pid, $host_pid)"
        return 0
    else
        # Linux: Use Avahi if available
        if command -v avahi-publish >/dev/null 2>&1; then
            avahi-publish -s "$hostname" _https._tcp $port "domain=$domain" &
            local avahi_pid=$!
            echo "$avahi_pid" > "${STING_INSTALL_DIR}/.mdns_service.pid"
            log_message "Avahi service registered for $domain (PID: $avahi_pid)"
            return 0
        else
            log_message "mDNS not available on this system"
            return 1
        fi
    fi
}

# Stop mDNS service
stop_mdns_service() {
    if [[ -f "${STING_INSTALL_DIR}/.mdns_service.pid" ]]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                log_message "Stopped mDNS service (PID: $pid)"
            fi
        done < "${STING_INSTALL_DIR}/.mdns_service.pid"
        rm -f "${STING_INSTALL_DIR}/.mdns_service.pid"
    fi
}

# Update hosts file (fallback when mDNS not available)
update_hosts_file() {
    local domain="$1"
    local action="${2:-add}"  # add or remove
    
    if [[ "$action" == "add" ]]; then
        # Check if entry already exists
        if ! grep -q "$domain" /etc/hosts 2>/dev/null; then
            echo "127.0.0.1    $domain" | sudo tee -a /etc/hosts >/dev/null
            log_message "Added $domain to /etc/hosts"
        fi
    elif [[ "$action" == "remove" ]]; then
        sudo sed -i.bak "/$domain/d" /etc/hosts 2>/dev/null
        log_message "Removed $domain from /etc/hosts"
    fi
}

# Get current STING domain
get_current_domain() {
    if [[ -f "${STING_INSTALL_DIR}/.sting_domain" ]]; then
        cat "${STING_INSTALL_DIR}/.sting_domain"
    else
        echo "localhost"
    fi
}

# Save STING domain
save_domain() {
    local domain="$1"
    echo "$domain" > "${STING_INSTALL_DIR}/.sting_domain"
    log_message "Saved domain: $domain"
}

# Update configuration files with new domain
update_domain_config() {
    local new_domain="$1"
    local old_domain="${2:-localhost}"
    
    log_message "Updating configuration from $old_domain to $new_domain"
    
    # Update config.yml
    if [[ -f "${STING_INSTALL_DIR}/conf/config.yml" ]]; then
        sed -i.bak "s/${old_domain}/${new_domain}/g" "${STING_INSTALL_DIR}/conf/config.yml"
    fi
    
    # Update Kratos configuration
    if [[ -f "${STING_INSTALL_DIR}/conf/kratos/kratos.yml" ]]; then
        sed -i.bak "s/id: ${old_domain}/id: ${new_domain}/g" "${STING_INSTALL_DIR}/conf/kratos/kratos.yml"
        sed -i.bak "s/domain: ${old_domain}/domain: ${new_domain}/g" "${STING_INSTALL_DIR}/conf/kratos/kratos.yml"
    fi
    
    # Save domain for future reference
    save_domain "$new_domain"
    
    log_message "Configuration updated for domain: $new_domain"
}

# Display domain info
show_domain_info() {
    local domain=$(get_current_domain)
    local mdns_available=$(check_mdns_support && echo "Yes" || echo "No")
    
    echo ""
    echo "🌐 STING Local Domain Configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Current domain: $domain"
    echo "mDNS available: $mdns_available"
    echo ""
    echo "Access URLs:"
    echo "  Frontend: https://${domain}:8443"
    echo "  API: https://${domain}:5050"
    echo "  Kratos: https://${domain}:4433"
    echo ""
    
    if [[ "$mdns_available" == "Yes" ]]; then
        echo "✅ mDNS is available - domain will be accessible from other devices on your network"
    else
        echo "⚠️  mDNS not available - domain only accessible from this machine"
        echo "   To access from other devices, add to their /etc/hosts:"
        echo "   $(hostname -I | awk '{print $1}')    $domain"
    fi
    echo ""
}

# Export functions for use in other scripts
export -f get_machine_id
export -f generate_sting_domain
export -f check_mdns_support
export -f register_mdns_service
export -f stop_mdns_service
export -f update_hosts_file
export -f get_current_domain
export -f save_domain
export -f update_domain_config
export -f show_domain_info