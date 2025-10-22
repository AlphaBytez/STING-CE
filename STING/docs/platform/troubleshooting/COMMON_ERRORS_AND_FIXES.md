# Common Errors and Fixes for STING-CE

## 1. "No honey jars available" in Bee Chat (Fixed January 2025)

### Symptom
- Bee Chat shows "No honey jars available" message
- Message persists after logout/login
- Honey Jar page works fine and shows available honey jars

### Root Cause
- Chatbot was calling wrong API endpoint: `/bee/context/public` instead of `/bee/context`
- Knowledge service connectivity issues between chatbot and knowledge service
- Session/authentication issues after service restarts

### Fix Applied (v2025.1)
```bash
# The fix is already applied in the latest version
# If you're still seeing this issue, restart the chatbot:
./manage_sting.sh restart chatbot
```

### Technical Details
- **Fixed endpoint**: Chatbot now calls correct `/bee/context` endpoint
- **Enhanced error logging**: Specific error messages help identify the root cause
- **Better error handling**: Structured responses with status indicators
- **Session persistence**: Improved session management across service restarts

### Prevention
- Keep services updated: `./manage_sting.sh update chatbot`
- Monitor chatbot logs: `docker logs sting-ce-chatbot`
- If issue persists, check knowledge service health: `./manage_sting.sh status`

## 2. Zombie LLM Process Problem

### Symptom
- After reinstall, LLM service shows wrong model or old uptime
- `curl http://localhost:8086/health` shows uptime of hours/days
- Model changes don't take effect

### Root Cause
- Native LLM service process not killed during uninstall
- PID file persists across reinstalls
- Process continues running with old configuration

### Fix
```bash
# Find the process
lsof -i :8086

# Kill it (replace PID with actual process ID)
kill -9 PID

# Remove PID files
rm -f ~/.sting-ce/run/llm-gateway.pid
rm -f /opt/sting-ce/run/llm-gateway.pid

# Restart service
./sting-llm start
```

### Prevention
- Always run `./manage_sting.sh uninstall` before reinstalling
- The updated installer now kills processes automatically

## 2. Repo ID vs Local Path Error

### Symptom
```
{"detail":"Text generation failed: Repo id must be in the form 'repo_name' or 'namespace/repo_name': '/path/to/model'. Use `repo_type` argument if needed."}
```

### Root Cause
- Task routing configured to use non-existent model (e.g., phi3)
- Model path being interpreted as HuggingFace repo ID
- Path doesn't exist or isn't accessible
- Wrong model being loaded due to config

### Fix
```bash
# 1. Check task routing configuration
grep -A 5 "chat:" ~/Documents/GitHub/STING-CE/STING/conf/config.yml

# 2. Fix config to use available models
# Edit config.yml to set tinyllama as primary for chat

# 3. Force load correct model
curl -X POST http://localhost:8086/models/tinyllama/load

# 4. Or specify model explicitly
curl -X POST http://localhost:8086/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "model": "tinyllama", "max_length": 50}'

# 5. Restart service to reload config
./sting-llm restart
```

## 3. Missing Python Dependencies

### Symptom
- `ModuleNotFoundError: No module named 'torch'`
- `ModuleNotFoundError: No module named 'fastapi'`

### Root Cause
- Virtual environment missing dependencies
- Incomplete installation

### Fix
```bash
cd /path/to/STING-CE/STING
source .venv/bin/activate
pip install -r llm_service/requirements.txt
pip install -r llm_service/requirements.common.txt
pip install -r llm_service/requirements.gateway.txt
```

## 4. Docker Compose Shows No Services

### Symptom
- `docker compose ps` shows empty
- But `docker ps` shows containers running

### Root Cause
- Running command from wrong directory
- Docker Compose project name mismatch

### Fix
```bash
# Run from installation directory
cd ~/.sting-ce
docker compose ps

# Or specify compose file
cd /path/to/STING-CE/STING
docker compose -f docker-compose.yml -f docker-compose.mac.yml ps
```

## 5. Alpine Container as LLM Gateway

### Symptom
- `docker ps` shows alpine:latest as llm-gateway
- Port forwarding not working

### Root Cause
- macOS uses stub container to forward to native service
- Native service not running

### Fix
```bash
# Start native service first
./sting-llm start

# Verify it's running
curl http://localhost:8086/health

# Restart docker services
docker compose restart llm-gateway
```

## Quick Diagnostic Commands

```bash
# Check all services
docker ps | grep sting
./sting-llm status
curl http://localhost:8086/health
curl http://localhost:8081/health

# Check logs
docker compose logs --tail=50
tail -50 ~/.sting-ce/logs/llm-gateway.log

# Clean restart
./manage_sting.sh stop
pkill -f "python.*server.py"
./manage_sting.sh start
```