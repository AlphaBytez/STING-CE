#!/bin/bash

# WSL2 Mailpit SMTP Fix Script
# Detects WSL2 environment and updates Kratos SMTP config to use IP instead of hostname

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Checking for WSL2 environment...${NC}"

# Detect if running in WSL2
if grep -q "microsoft.*WSL2" /proc/version 2>/dev/null; then
    echo -e "${YELLOW}📍 WSL2 detected - applying Mailpit SMTP fix...${NC}"
    
    # Get Mailpit container IP
    MAILPIT_IP=$(docker inspect sting-ce-mailpit --format '{{range $k, $v := .NetworkSettings.Networks}}{{$v.IPAddress}}{{end}}' 2>/dev/null)
    
    if [ -z "$MAILPIT_IP" ]; then
        echo -e "${RED}❌ Could not find Mailpit container IP${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}📡 Found Mailpit IP: $MAILPIT_IP${NC}"
    
    # Update Kratos configuration
    KRATOS_CONFIG="/mnt/c/Dev/STING-CE/STING/kratos/kratos.yml"
    
    if [ -f "$KRATOS_CONFIG" ]; then
        # Backup original config
        cp "$KRATOS_CONFIG" "$KRATOS_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Replace hostname with IP
        sed -i "s|smtp://mailpit:1025|smtp://$MAILPIT_IP:1025|g" "$KRATOS_CONFIG"
        
        echo -e "${GREEN}✅ Updated Kratos SMTP config to use IP: $MAILPIT_IP${NC}"
        
        # Restart Kratos to apply changes
        echo -e "${YELLOW}🔄 Restarting Kratos...${NC}"
        docker restart sting-ce-kratos > /dev/null
        
        echo -e "${GREEN}✅ WSL2 Mailpit fix applied successfully${NC}"
    else
        echo -e "${RED}❌ Kratos config file not found at $KRATOS_CONFIG${NC}"
        exit 1
    fi
    
elif grep -q "Darwin" /proc/version 2>/dev/null || uname -s | grep -q "Darwin"; then
    echo -e "${GREEN}🍎 macOS detected - hostname resolution should work fine${NC}"
    echo -e "${GREEN}✅ No changes needed for macOS${NC}"
    
else
    echo -e "${GREEN}🐧 Standard Linux detected - hostname resolution should work fine${NC}"
    echo -e "${GREEN}✅ No changes needed for standard Linux${NC}"
fi

echo -e "${GREEN}🎯 Platform-specific SMTP configuration complete${NC}"