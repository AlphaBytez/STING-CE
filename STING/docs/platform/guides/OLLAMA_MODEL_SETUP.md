# Ollama Model Setup Guide

## Overview
STING uses Ollama for local AI capabilities, including the Bee chat assistant. This guide helps you set up the required models.

## Quick Start

### 1. Check if Ollama is running
```bash
ollama list
```

If you get an error, start Ollama:
```bash
ollama serve
```

### 2. Install recommended models

For general use (including Bee chat):
```bash
# Recommended - Latest Llama model with good performance
ollama pull llama3.3

# Alternative lightweight option
ollama pull phi3
```

For code-related tasks:
```bash
# Excellent for code analysis and generation
ollama pull deepseek-coder-v2
```

### 3. Verify installation
```bash
ollama list
```

You should see your installed models listed.

## Model Recommendations

| Model | Size | Use Case | Performance |
|-------|------|----------|-------------|
| llama3.3:latest | ~5GB | General chat, analysis | Excellent |
| phi3:mini | ~2GB | Lightweight chat | Good |
| deepseek-coder-v2:latest | ~16GB | Code tasks | Excellent for code |

## Troubleshooting

### "No models available" error in Bee chat
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Install a model: `ollama pull llama3.3`
3. Restart the external AI service: `./manage_sting.sh restart external-ai`

### Model downloading slowly
Models can be large. Consider:
- Using a faster internet connection
- Installing smaller models first (phi3:mini)
- Downloading during off-peak hours

### Bee chat shows "online" but doesn't respond
This usually means no models are installed. The service is running but has no AI model to use.

## Configuration

The default model is configured in `/conf/config.yml`:
```yaml
external_ai:
  providers:
    ollama:
      defaultModel: "llama3.3:latest"
```

After changing the configuration:
```bash
./manage_sting.sh restart external-ai
```

## Memory Considerations

- Ollama models are loaded into memory when used
- Ensure you have sufficient RAM (8GB+ recommended)
- Models are automatically unloaded when idle

## Next Steps

After installing models:
1. Test Bee chat in the STING UI
2. Check logs if issues persist: `docker logs sting-ce-external-ai`
3. Try different models to find the best fit for your use case