#!/bin/bash
# hutallation setup for STING

# Set up directories needed for installation
echo "Creating necessary directories..."
mkdir -p ~/.sting-ce
mkdir -p ~/.sting-ce/env
mkdir -p ~/.sting-ce/logs
mkdir -p ~/.sting-ce/conf

# Create a dummy HF token to prevent errors
echo "Creating dummy HF token file..."
echo "HF_TOKEN=dummy" > ~/.sting-ce/env/hf_token.env
chmod 600 ~/.sting-ce/env/hf_token.env

# Create .env file in project root
echo "Creating .env file in project root..."
echo "HF_TOKEN=dummy" > "$(dirname "$0")/.env"
chmod 600 "$(dirname "$0")/.env"

echo "Setup complete! You should now be able to run the installer."
echo "To set a real Hugging Face token later, use ./setup_hf_token.sh"