#!/bin/bash
# STING Hostname Configuration Tool
# Updates hostname for WebAuthn/Passkey compatibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect install directory
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${HOME}/.sting-ce"
else
    INSTALL_DIR="/opt/sting-ce"
fi

# Override if running from a different location
if [ -f "$SCRIPT_DIR/kratos/kratos.yml.template" ]; then
    INSTALL_DIR="$SCRIPT_DIR"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  STING Hostname Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Source hostname detection library
if [ -f "$INSTALL_DIR/lib/hostname_detection.sh" ]; then
    source "$INSTALL_DIR/lib/hostname_detection.sh"
else
    echo -e "${RED}Error: hostname_detection.sh not found${NC}"
    exit 1
fi

# Get hostname (interactive mode)
STING_HOSTNAME=$(get_sting_hostname true)

if [ -z "$STING_HOSTNAME" ]; then
    echo -e "${RED}Error: No hostname provided${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Selected hostname: $STING_HOSTNAME${NC}"
echo ""

# Confirm with user
read -p "Proceed with this hostname? [Y/n]: " confirm
confirm="${confirm:-Y}"

if [[ ! "$confirm" =~ ^[Yy] ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}📝 Updating configuration files...${NC}"

# 1. Update Kratos config from template
if [ -f "$INSTALL_DIR/kratos/kratos.yml.template" ]; then
    echo "  • Generating kratos/kratos.yml"
    sed "s/__STING_HOSTNAME__/$STING_HOSTNAME/g" \
        "$INSTALL_DIR/kratos/kratos.yml.template" > \
        "$INSTALL_DIR/kratos/kratos.yml"
    echo -e "    ${GREEN}✓${NC} kratos.yml updated"
else
    echo -e "    ${YELLOW}⚠${NC} kratos.yml.template not found, skipping"
fi

# 2. Update frontend env.js files
for env_file in \
    "$INSTALL_DIR/frontend/public/env.js" \
    "$INSTALL_DIR/app/static/env.js"; do

    if [ -f "$env_file" ]; then
        echo "  • Updating $(basename $(dirname $env_file))/$(basename $env_file)"

        # Cross-platform sed -i (macOS requires '', Linux doesn't)
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS
            sed -i '' "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "$env_file"
            sed -i '' "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "$env_file"
            sed -i '' "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "$env_file"
        else
            # Linux
            sed -i "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "$env_file"
            sed -i "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "$env_file"
            sed -i "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "$env_file"
        fi

        echo -e "    ${GREEN}✓${NC} Updated"
    fi
done

# 3. Update .env file with new hostname for docker-compose persistence
if [ -f "$INSTALL_DIR/.env" ]; then
    echo "  • Updating .env file for docker-compose"

    # Remove existing HOSTNAME line
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        sed -i '' '/^HOSTNAME=/d' "$INSTALL_DIR/.env"
    else
        # Linux
        sed -i '/^HOSTNAME=/d' "$INSTALL_DIR/.env"
    fi

    # Append new HOSTNAME
    echo "HOSTNAME=$STING_HOSTNAME" >> "$INSTALL_DIR/.env"
    echo -e "    ${GREEN}✓${NC} .env file updated"
else
    echo -e "    ${YELLOW}⚠${NC} .env file not found, skipping"
fi

# 4. Export for config generation
export STING_HOSTNAME="$STING_HOSTNAME"
export HOSTNAME="$STING_HOSTNAME"  # Also export HOSTNAME for docker-compose
echo ""
echo -e "${GREEN}✅ Configuration files updated${NC}"

# 5. Update Docker environment and restart services if Docker is running
if docker ps -q -f name=sting-ce >/dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}🔄 Updating Docker services with new hostname...${NC}"

    # Set HOSTNAME environment variable for docker-compose
    export HOSTNAME="$STING_HOSTNAME"

    # Recreate containers with new hostname (this updates environment variables)
    echo "  • Recreating frontend with new hostname..."
    if docker compose -f "$INSTALL_DIR/docker-compose.yml" up -d --force-recreate --no-deps frontend >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} Frontend recreated"
    else
        echo -e "    ${YELLOW}⚠${NC} Could not recreate frontend"
    fi

    echo "  • Restarting Kratos..."
    if docker compose -f "$INSTALL_DIR/docker-compose.yml" restart kratos >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} Kratos restarted"
    else
        echo -e "    ${YELLOW}⚠${NC} Could not restart Kratos"
    fi

    echo "  • Restarting app service..."
    if docker compose -f "$INSTALL_DIR/docker-compose.yml" restart app >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} App restarted"
    else
        echo -e "    ${YELLOW}⚠${NC} Could not restart app"
    fi

    echo -e "${GREEN}✅ Docker services updated${NC}"

    # Wait for services to be healthy
    echo -n "   Waiting for services to be healthy..."
    sleep 8

    if docker ps | grep sting-ce-frontend | grep -q healthy && \
       docker ps | grep sting-ce-kratos | grep -q healthy; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${YELLOW}⚠ (some services may still be starting)${NC}"
    fi
fi

echo ""
show_hostname_instructions "$STING_HOSTNAME"

# 6. Offer to update /etc/hosts file for local DNS resolution
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Local DNS Configuration (Optional)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "For local development, you can add this hostname to /etc/hosts"
echo -e "so you can access STING at ${GREEN}https://$STING_HOSTNAME:8443${NC}"
echo ""

# Get primary IP address for hosts file entry
PRIMARY_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$PRIMARY_IP" ]; then
    PRIMARY_IP="127.0.0.1"
fi

echo -e "This will add the following entry to /etc/hosts:"
echo -e "  ${YELLOW}$PRIMARY_IP  $STING_HOSTNAME${NC}"
echo ""
echo -e "${YELLOW}⚠️  Note:${NC} This requires sudo privileges and only affects THIS machine."
echo -e "   Remote clients will still need to configure DNS separately."
echo ""

read -p "Update /etc/hosts on this machine? [y/N]: " update_hosts
if [[ "$update_hosts" =~ ^[Yy]$ ]]; then
    # Check if entry already exists
    if grep -q "^[^#]*[[:space:]]$STING_HOSTNAME" /etc/hosts 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}⚠️  Entry for $STING_HOSTNAME already exists in /etc/hosts${NC}"
        read -p "Replace existing entry? [y/N]: " replace_entry

        if [[ "$replace_entry" =~ ^[Yy]$ ]]; then
            # Remove old entries for this hostname
            if sudo sed -i.backup "/$STING_HOSTNAME/d" /etc/hosts 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Removed old entry"
            else
                echo -e "${RED}✗${NC} Failed to remove old entry"
            fi
        else
            echo "Skipping /etc/hosts update"
            update_hosts="n"
        fi
    fi

    if [[ "$update_hosts" =~ ^[Yy]$ ]]; then
        # Add new entry
        if echo "$PRIMARY_IP  $STING_HOSTNAME  # Added by STING update_hostname.sh" | sudo tee -a /etc/hosts >/dev/null 2>&1; then
            echo -e "${GREEN}✅ /etc/hosts updated successfully${NC}"
            echo ""
            echo "Testing DNS resolution..."
            if ping -c 1 -W 2 "$STING_HOSTNAME" >/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} $STING_HOSTNAME resolves to $PRIMARY_IP"
            else
                echo -e "${YELLOW}⚠${NC} Could not ping $STING_HOSTNAME (this may be normal if ping is blocked)"
            fi
        else
            echo -e "${RED}✗${NC} Failed to update /etc/hosts"
            echo "   You can manually add: $PRIMARY_IP  $STING_HOSTNAME"
        fi
    fi
else
    echo "Skipping /etc/hosts update"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Hostname configuration complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Access STING at: ${GREEN}https://$STING_HOSTNAME:8443${NC}"
echo ""
