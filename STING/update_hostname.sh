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

# 3. Export for config generation
export STING_HOSTNAME="$STING_HOSTNAME"
echo ""
echo -e "${GREEN}✅ Configuration files updated${NC}"

# 4. Restart Kratos if Docker is running
if docker ps -q -f name=sting-ce-kratos >/dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}🔄 Restarting Kratos service...${NC}"

    if docker compose -f "$INSTALL_DIR/docker-compose.yml" restart kratos >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Kratos restarted${NC}"

        # Wait for healthy
        echo -n "   Waiting for Kratos to be healthy..."
        sleep 5

        if docker ps | grep sting-ce-kratos | grep -q healthy; then
            echo -e " ${GREEN}✓${NC}"
        else
            echo -e " ${YELLOW}⚠ (check status manually)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Could not restart Kratos (Docker may not be running)${NC}"
    fi
fi

echo ""
show_hostname_instructions "$STING_HOSTNAME"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Hostname configuration complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Access STING at: ${GREEN}https://$STING_HOSTNAME:8443${NC}"
echo ""
