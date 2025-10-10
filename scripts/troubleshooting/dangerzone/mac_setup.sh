#!/bin/bash
# Mac Development Environment Setup for STING

# Use user's home directory for development
export INSTALL_DIR="$HOME/.sting-ce"
export DEV_LOGS_DIR="$HOME/.sting-ce/logs"

# Create user-space directories
mkdir -p $INSTALL_DIR
mkdir -p $DEV_LOGS_DIR
mkdir -p $INSTALL_DIR/conf/vault
mkdir -p $INSTALL_DIR/data/postgres

# Make management script executable
chmod +x manage_sting.sh

# Set environment variables for development
echo "export INSTALL_DIR=$INSTALL_DIR" >> ~/.zshrc
echo "export STING_LOGS_DIR=$DEV_LOGS_DIR" >> ~/.zshrc
