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
