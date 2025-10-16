# LLM Model Loading Progress Tracking

This document describes the enhanced progress tracking system for LLM model loading operations in STING.

## Overview

The progress tracking system provides real-time feedback during long-running model loading operations, addressing the issue where large models (like Llama-3 8B) could take 5-15 minutes to download and load.

## Features

### 🎯 **Core Features**
- **Async model loading** - Non-blocking operations with progress tracking
- **Real-time progress updates** - Visual progress bar with percentage
- **Terminal output** - Optional live terminal view of loading process
- **Status indicators** - Clear visual feedback for different loading stages
- **Error handling** - Graceful error reporting with retry options

### 📊 **Progress Stages**
1. **Initializing** (0-5%) - Starting the loading process
2. **Downloading** (10-60%) - Downloading model files from HuggingFace
3. **Loading** (60-85%) - Loading model into memory
4. **Finalizing** (85-95%) - Final setup and verification
5. **Completed** (100%) - Model ready for use

## API Endpoints

### Start Model Loading
```http
POST /api/llm/load
Content-Type: application/json

{
  "model_name": "phi3"
}
```

**Response (202 Accepted):**
```json
{
  "operation_id": "uuid-string",
  "message": "Model loading started for phi3",
  "status": "started"
}
```

### Get Progress
```http
GET /api/llm/progress/{operation_id}
```

**Response:**
```json
{
  "status": "downloading",
  "progress": 45,
  "message": "Downloading model files...",
  "logs": [
    "Starting model download...",
    "Fetching model weights (1/3)...",
    "Progress: 45% complete"
  ],
  "created_at": "2025-06-25T10:30:00Z",
  "updated_at": "2025-06-25T10:31:15Z"
}
```

### Get All Operations
```http
GET /api/llm/progress
```

### Clear Progress Data
```http
DELETE /api/llm/progress/{operation_id}
```

## UI Components

### BeeSettings Enhanced Features

#### Progress Modal
- **Automatic display** when model loading starts
- **Progress bar** with animated stripes
- **Status indicators** with icons and colors
- **Terminal toggle** for detailed output
- **Action buttons** (Done, Close, Retry)

#### Terminal Output Component
- **Live terminal view** with scroll to bottom
- **Copy to clipboard** functionality
- **Download logs** as text file
- **Syntax highlighting** for better readability

#### Progress Bar Component
- **Animated progress** with smooth transitions
- **Status-based colors** (blue for downloading, purple for loading, green for complete)
- **Stripe animation** for active operations
- **Error state handling**

## Model Loading Times

| Model | Size | Expected Time | Progress Tracking |
|-------|------|---------------|-------------------|
| TinyLlama | ~1.1GB | 1-2 minutes | ✅ Full tracking |
| Phi-3 | ~7GB | 3-6 minutes | ✅ Full tracking |
| Llama-3 8B | ~8GB+ | 5-10 minutes | ✅ Full tracking |
| Large models | 15GB+ | 10-20 minutes | ✅ Full tracking |

## Usage Example

### Frontend Usage
```javascript
// Start model loading
const response = await fetch('/api/llm/load', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ model_name: 'phi3' })
});

const { operation_id } = await response.json();

// Poll for progress
const pollProgress = setInterval(async () => {
  const progressResponse = await fetch(`/api/llm/progress/${operation_id}`);
  const progress = await progressResponse.json();
  
  // Update UI with progress
  updateProgressBar(progress.progress);
  updateStatusMessage(progress.message);
  
  if (progress.status === 'completed') {
    clearInterval(pollProgress);
    showSuccessMessage();
  }
}, 1000);
```

## Error Handling

### Common Error Scenarios
1. **Model not found** - Invalid model name
2. **Download failure** - Network issues or HuggingFace errors
3. **Memory issues** - Insufficient RAM for model
4. **Service unavailable** - LLM service not running

### Error Response Format
```json
{
  "status": "error",
  "progress": 35,
  "message": "Failed to download model: Network timeout",
  "logs": [
    "Starting download...",
    "Connection timeout after 30 seconds",
    "Retrying download...",
    "Error: Unable to connect to HuggingFace Hub"
  ]
}
```

## Performance Considerations

### Backend
- **Threaded execution** - Model loading runs in separate threads
- **Memory management** - Progress data cleanup after completion
- **Resource limits** - Configurable timeouts and retry logic

### Frontend
- **Polling interval** - 1-second updates for responsive feedback
- **Modal overlay** - Prevents user interaction during loading
- **Auto-cleanup** - Progress data cleared after completion

## Configuration

### Environment Variables
```bash
# LLM service configuration
NATIVE_LLM_URL=http://localhost:8086
STING_LLM_SCRIPT=./sting-llm

# Progress tracking
PROGRESS_CLEANUP_INTERVAL=300  # seconds
MAX_PROGRESS_ENTRIES=100       # per operation
```

### Model Loading Timeouts
- **Small models** (< 2GB): 5 minutes
- **Medium models** (2-8GB): 15 minutes  
- **Large models** (> 8GB): 30 minutes

## Future Enhancements

### Planned Features
- **WebSocket streaming** for real-time updates
- **Download resumption** for interrupted transfers
- **Bandwidth throttling** options
- **Multi-model loading** queue management
- **Progress persistence** across service restarts

### Integration Ideas
- **Notification system** for completion alerts
- **Progress history** and analytics
- **Resource monitoring** during loading
- **Model preloading** scheduler

## Troubleshooting

### Common Issues

#### Progress Not Updating
- Check if LLM service is running: `./sting-llm status`
- Verify operation ID is valid
- Check browser console for polling errors

#### Terminal Not Showing Output
- Ensure `sting-llm` script has proper output formatting
- Check if logs are being captured correctly
- Verify process stdout redirection

#### Model Loading Hangs
- Check available disk space
- Verify network connectivity to HuggingFace
- Monitor system memory usage
- Check for model-specific requirements

## Related Documentation

- [LLM Service Management](./LLM_SERVICE_MANAGEMENT.md)
- [Debugging Guide](./DEBUGGING.md)
- [Service Health Monitoring](./SERVICE_HEALTH_MONITORING.md)
- [BeeSettings Component Documentation](../frontend/src/components/settings/README.md)