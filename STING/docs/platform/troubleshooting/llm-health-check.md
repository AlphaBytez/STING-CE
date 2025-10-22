# LLM Health Check Instructions

The LLM services in STING can take some time to fully load the models and become operational. To ensure that your installation is working correctly, we've provided a health check script that will verify that all LLM services are properly running.

## When to Use This Script

Run this script:

1. After installation completes
2. If you experience issues with the LLM functionality
3. After upgrading or changing LLM models
4. If you want to verify that your Hugging Face token is working

## Usage

```bash
# Make the script executable (if not already)
chmod +x check_llm_health.sh

# Run the health check
./check_llm_health.sh
```

## What the Script Checks

The script performs several checks:

1. **Docker Status**: Verifies that Docker is running
2. **Container Status**: Checks if all LLM service containers are running
3. **Gateway Health**: Tests the LLM gateway health endpoint
4. **Model Loading**: Examines logs to see if models are loaded
5. **Model Testing**: Sends a simple prompt to each model to test functionality

## How to Interpret Results

The health check will display colored output:

- 🟢 **Green**: Component is healthy and working correctly
- 🟡 **Yellow**: Warning or component still initializing
- 🔴 **Red**: Error or component not functioning

## Troubleshooting

If issues are detected:

1. **Models Still Loading**: LLM models can take several minutes to load, especially on the first run
   ```bash
   # Check the logs of a specific model service
   docker logs $(docker ps | grep llama3-service | awk '{print $1}')
   ```

2. **Services Not Running**: Restart the services
   ```bash
   ./manage_sting.sh restart llama3-service phi3-service zephyr-service llm-gateway
   ```

3. **Gateway Connection Issues**: Check if the gateway is running on the expected port
   ```bash
   docker ps | grep llm-gateway
   ```

4. **Hugging Face Token Issues**: Verify your token is correctly set
   ```bash
   ./setup_hf_token.sh
   ```

## Wait Times

- **Initial Load**: 3-10 minutes depending on your hardware
- **Subsequent Starts**: 1-3 minutes

## Additional Information

The LLM services are designed to initialize in the background to prevent blocking the installation process. This means your STING installation may report as successful even if the models are still loading.

For large models (like Llama 3), initialization can take longer depending on your system's hardware resources. A machine with a GPU will load models faster than a CPU-only system.