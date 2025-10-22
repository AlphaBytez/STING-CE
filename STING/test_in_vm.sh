#!/bin/bash

#################################################
# STING-CE VM Testing Script
# Prepares and tests installation in clean VM
#################################################

set -e

echo "STING-CE VM Test Preparation"
echo "============================"
echo ""
echo "This script helps test STING-CE in a clean Ubuntu VM"
echo ""

# Check system requirements
echo "Checking system..."
echo "- OS: $(lsb_release -d | cut -f2)"
echo "- RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "- Disk: $(df -h / | awk 'NR==2 {print $4}' ) available"
echo "- Docker: $(docker --version 2>/dev/null || echo 'Not installed')"
echo ""

# Install dependencies if needed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Install it? (y/n)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        echo "Docker installed. Please logout and login again."
        exit 0
    fi
fi

# Test installation
echo "Ready to test STING-CE installation."
echo ""
echo "Steps:"
echo "1. Run: ./install_sting.sh"
echo "2. Follow the setup wizard"
echo "3. Access https://localhost:8443"
echo ""
echo "Press any key to start installation..."
read -n 1

# Run installer
./install_sting.sh
