#!/bin/bash
# Script to clean up backup files and organize helper scripts

set -e

# Create a directory structure inside troubleshooting for organizing the scripts
mkdir -p troubleshooting/chatbot_fixes
mkdir -p troubleshooting/db_fixes
mkdir -p troubleshooting/port_fixes
mkdir -p troubleshooting/model_fixes

# Move fix scripts to appropriate directories
echo "Moving helper scripts to troubleshooting directory..."

# LLM-related fixes
mv -v fix-llm-final.sh troubleshooting/chatbot_fixes/
mv -v fix-llm-gateway.sh troubleshooting/chatbot_fixes/
mv -v fix-llm-service.sh troubleshooting/chatbot_fixes/
mv -v fix-model-path.sh troubleshooting/model_fixes/

# Database fixes
mv -v fix-db-healthcheck.sh troubleshooting/db_fixes/

# Port fixes
mv -v update-ports.sh troubleshooting/port_fixes/

# Comprehensive fixes
mv -v fix-all-services.sh troubleshooting/

# Move documentation file
mv -v CHATBOT_FIX_GUIDE.md troubleshooting/chatbot_fixes/

# Copy needed helper scripts
cp -v llm_service/server.py.final troubleshooting/chatbot_fixes/
cp -v chatbot/simple_server.py troubleshooting/chatbot_fixes/

# Create a summary file
cat > troubleshooting/FIXES_SUMMARY.md << 'EOF'
# STING Fixes Summary

This directory contains scripts to fix various issues with the STING platform:

## Applied Fixes

1. **Database Fixes**
   - Fixed PostgreSQL healthcheck to properly use the "postgres" user
   - Located in `db_fixes/fix-db-healthcheck.sh`

2. **Port Conflict Fixes**
   - Updated all service ports to avoid conflicts
   - Located in `port_fixes/update-ports.sh`

3. **LLM and Chatbot Fixes**
   - Fixed model loading issues with updated BitsAndBytesConfig
   - Added proper chat templates for Llama-3
   - Fixed Dockerfile to use latest dependency versions
   - Located in `chatbot_fixes/fix-llm-service.sh` and `chatbot_fixes/fix-llm-final.sh`

4. **Model Path Fixes**
   - Fixed path to use correct model directory (llm_models vs llm-models)
   - Located in `model_fixes/fix-model-path.sh`

5. **Comprehensive Fix**
   - Combined all fixes in a single orderly script
   - Located in `fix-all-services.sh`

## Usage

Run the appropriate script based on the issue you're experiencing:

- For database issues: `./troubleshooting/db_fixes/fix-db-healthcheck.sh`
- For port conflicts: `./troubleshooting/port_fixes/update-ports.sh`
- For model path issues: `./troubleshooting/model_fixes/fix-model-path.sh`
- For LLM/chatbot issues: `./troubleshooting/chatbot_fixes/fix-llm-final.sh`
- For all issues: `./troubleshooting/fix-all-services.sh`

## Backup Files

During the troubleshooting process, several backup files were created with .bak extensions.
These can be safely removed if the fixes are working properly.
EOF

# Clean up backup files
echo "Cleaning up backup files..."

# Remove .bak files generated during our session
rm -v docker-compose.yml.bak.dbfix docker-compose.yml.bak.dbfix2 2>/dev/null || true
rm -v llm_service/server.py.bak.* llm_service/Dockerfile.gateway.bak.* 2>/dev/null || true
rm -v docker-compose.yml.bak[0-9] 2>/dev/null || true
rm -v docker-compose.yml.bak.2025* 2>/dev/null || true
rm -v env/*.bak.modelpath 2>/dev/null || true
rm -v conf/config.yml.bak.modelpath 2>/dev/null || true

echo "Cleanup complete!"
echo "All fix scripts have been organized into the troubleshooting directory."
echo "See troubleshooting/FIXES_SUMMARY.md for details."