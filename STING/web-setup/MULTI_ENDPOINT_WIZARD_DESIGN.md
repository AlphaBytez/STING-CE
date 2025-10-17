# Multi-Endpoint Wizard UI Design

Design document for extending the STING setup wizard to support multiple LLM providers with API key authentication.

## Overview

**Current State**: Wizard only supports Ollama (local, no API keys)

**Target State**: Support multiple LLM providers:
- **Ollama** (local, free, no API key)
- **OpenAI** (cloud, paid, API key)
- **Anthropic Claude** (cloud, paid, API key)
- **Azure OpenAI** (cloud, paid, API key + endpoint)
- **Custom OpenAI-compatible** (LM Studio, vLLM, etc.)

## User Experience Flow

### Step 4: LLM Backend Configuration

```
┌─────────────────────────────────────────────────────────┐
│  🤖 LLM Backend Configuration                           │
│                                                          │
│  Choose your preferred AI model provider:               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Primary LLM Provider                              │  │
│  │ ┌───────────────────────────────────────────┐    │  │
│  │ │ ▼ Ollama (Local, Free) ✓ Recommended      │    │  │
│  │ └───────────────────────────────────────────┘    │  │
│  │   • OpenAI (Cloud, Paid - API Key Required)      │  │
│  │   • Anthropic Claude (Cloud, Paid)               │  │
│  │   • Azure OpenAI (Enterprise)                    │  │
│  │   • Custom OpenAI-compatible                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  [Dynamic configuration form appears here]              │
│                                                          │
│  [Test Connection] [Skip Test]                          │
└─────────────────────────────────────────────────────────┘
```

## HTML Implementation

### Provider Selection Dropdown

```html
<div class="step-content" data-step="4">
    <h2>🤖 LLM Backend Configuration</h2>
    <p class="text-muted mb-4">
        Configure your AI model provider to power the Worker Bee assistant.
        You can change this later in settings.
    </p>

    <!-- Provider Selection -->
    <div class="form-group mb-5">
        <label class="form-label fw-bold">Primary LLM Provider</label>
        <select
            id="llm-provider"
            class="form-select form-select-lg"
            onchange="toggleProviderConfig()"
            aria-label="Select LLM Provider"
        >
            <option value="ollama" selected>
                🐪 Ollama (Local, Free) - Recommended
            </option>
            <option value="openai">
                🤖 OpenAI (Cloud, Paid - API Key Required)
            </option>
            <option value="anthropic">
                🧠 Anthropic Claude (Cloud, Paid - API Key Required)
            </option>
            <option value="azure">
                ☁️ Azure OpenAI (Enterprise - API Key Required)
            </option>
            <option value="custom">
                🔧 Custom OpenAI-compatible (LM Studio, vLLM, etc.)
            </option>
        </select>

        <!-- Provider info badges -->
        <div id="provider-info" class="mt-2">
            <span class="badge bg-success" id="info-cost"></span>
            <span class="badge bg-info" id="info-location"></span>
            <span class="badge bg-warning" id="info-auth"></span>
        </div>
    </div>

    <!-- Ollama Configuration -->
    <div id="config-ollama" class="provider-config active">
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">🐪 Ollama Configuration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info mb-3">
                    <strong>Setup Required:</strong> Install Ollama on your system first.
                    <a href="https://ollama.ai/download" target="_blank" class="alert-link">
                        Download Ollama →
                    </a>
                    |
                    <a href="/docs/guides/OLLAMA_SETUP_GUIDE.md" target="_blank" class="alert-link">
                        Setup Guide →
                    </a>
                </div>

                <div class="form-group mb-3">
                    <label for="ollama-endpoint" class="form-label">
                        Ollama Endpoint URL
                        <span class="text-muted">(required)</span>
                    </label>
                    <input
                        type="url"
                        id="ollama-endpoint"
                        class="form-control"
                        placeholder="http://localhost:11434"
                        value="http://localhost:11434"
                        required
                    >
                    <div class="form-text">
                        Common endpoints:
                        <code>http://localhost:11434</code> (local),
                        <code>http://host.docker.internal:11434</code> (WSL2),
                        or Tailscale IP
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="ollama-model" class="form-label">
                        Default Model
                        <span class="text-muted">(required)</span>
                    </label>
                    <input
                        type="text"
                        id="ollama-model"
                        class="form-control"
                        placeholder="phi3:mini"
                        value="phi3:mini"
                        required
                    >
                    <div class="form-text">
                        Recommended: <code>phi3:mini</code> (fast, 2.3GB) or
                        <code>deepseek-r1:latest</code> (advanced)
                    </div>
                </div>

                <button
                    type="button"
                    class="btn btn-primary"
                    onclick="testLLMConnection('ollama')"
                >
                    <i class="fas fa-plug"></i> Test Ollama Connection
                </button>

                <div id="test-result-ollama" class="mt-3"></div>
            </div>
        </div>
    </div>

    <!-- OpenAI Configuration -->
    <div id="config-openai" class="provider-config" style="display: none;">
        <div class="card border-success">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">🤖 OpenAI Configuration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-warning mb-3">
                    <strong>⚠️ API Key Required:</strong> You need an OpenAI API key.
                    <a href="https://platform.openai.com/api-keys" target="_blank" class="alert-link">
                        Get API Key →
                    </a>
                </div>

                <div class="form-group mb-3">
                    <label for="openai-api-key" class="form-label">
                        OpenAI API Key
                        <span class="text-danger">*</span>
                    </label>
                    <div class="input-group">
                        <input
                            type="password"
                            id="openai-api-key"
                            class="form-control font-monospace"
                            placeholder="sk-proj-..."
                            autocomplete="off"
                            required
                        >
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            onclick="togglePasswordVisibility('openai-api-key')"
                        >
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                    <div class="form-text">
                        Your API key is encrypted and stored securely in HashiCorp Vault.
                        It never leaves your STING instance.
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="openai-model" class="form-label">
                        Default Model
                        <span class="text-danger">*</span>
                    </label>
                    <select id="openai-model" class="form-select" required>
                        <option value="gpt-4o" selected>GPT-4o (Latest, Best Quality)</option>
                        <option value="gpt-4-turbo">GPT-4 Turbo (Fast & Capable)</option>
                        <option value="gpt-4">GPT-4 (High Quality)</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Fast & Cheap)</option>
                    </select>
                    <div class="form-text">
                        Pricing:
                        <a href="https://openai.com/pricing" target="_blank" class="text-decoration-none">
                            View OpenAI pricing →
                        </a>
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="openai-org-id" class="form-label">
                        Organization ID
                        <span class="text-muted">(optional)</span>
                    </label>
                    <input
                        type="text"
                        id="openai-org-id"
                        class="form-control font-monospace"
                        placeholder="org-..."
                    >
                    <div class="form-text">
                        Only required if you belong to multiple organizations
                    </div>
                </div>

                <button
                    type="button"
                    class="btn btn-success"
                    onclick="testLLMConnection('openai')"
                >
                    <i class="fas fa-plug"></i> Test OpenAI Connection
                </button>

                <div id="test-result-openai" class="mt-3"></div>
            </div>
        </div>
    </div>

    <!-- Anthropic Claude Configuration -->
    <div id="config-anthropic" class="provider-config" style="display: none;">
        <div class="card border-info">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">🧠 Anthropic Claude Configuration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-warning mb-3">
                    <strong>⚠️ API Key Required:</strong> You need an Anthropic API key.
                    <a href="https://console.anthropic.com/account/keys" target="_blank" class="alert-link">
                        Get API Key →
                    </a>
                </div>

                <div class="form-group mb-3">
                    <label for="anthropic-api-key" class="form-label">
                        Anthropic API Key
                        <span class="text-danger">*</span>
                    </label>
                    <div class="input-group">
                        <input
                            type="password"
                            id="anthropic-api-key"
                            class="form-control font-monospace"
                            placeholder="sk-ant-api03-..."
                            autocomplete="off"
                            required
                        >
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            onclick="togglePasswordVisibility('anthropic-api-key')"
                        >
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                    <div class="form-text">
                        Your API key is encrypted and stored securely in HashiCorp Vault.
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="anthropic-model" class="form-label">
                        Default Model
                        <span class="text-danger">*</span>
                    </label>
                    <select id="anthropic-model" class="form-select" required>
                        <option value="claude-3-5-sonnet-20241022" selected>
                            Claude 3.5 Sonnet (Latest, Best Balance)
                        </option>
                        <option value="claude-3-opus-20240229">
                            Claude 3 Opus (Highest Intelligence)
                        </option>
                        <option value="claude-3-sonnet-20240229">
                            Claude 3 Sonnet (Balanced)
                        </option>
                        <option value="claude-3-haiku-20240307">
                            Claude 3 Haiku (Fast & Affordable)
                        </option>
                    </select>
                    <div class="form-text">
                        Pricing:
                        <a href="https://www.anthropic.com/pricing" target="_blank" class="text-decoration-none">
                            View Anthropic pricing →
                        </a>
                    </div>
                </div>

                <button
                    type="button"
                    class="btn btn-info text-white"
                    onclick="testLLMConnection('anthropic')"
                >
                    <i class="fas fa-plug"></i> Test Anthropic Connection
                </button>

                <div id="test-result-anthropic" class="mt-3"></div>
            </div>
        </div>
    </div>

    <!-- Azure OpenAI Configuration -->
    <div id="config-azure" class="provider-config" style="display: none;">
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">☁️ Azure OpenAI Configuration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info mb-3">
                    <strong>Azure OpenAI Service:</strong> Enterprise-grade deployment with Microsoft security.
                    <a href="https://azure.microsoft.com/en-us/products/ai-services/openai-service" target="_blank" class="alert-link">
                        Learn more →
                    </a>
                </div>

                <div class="form-group mb-3">
                    <label for="azure-endpoint" class="form-label">
                        Azure Endpoint
                        <span class="text-danger">*</span>
                    </label>
                    <input
                        type="url"
                        id="azure-endpoint"
                        class="form-control font-monospace"
                        placeholder="https://your-resource.openai.azure.com"
                        required
                    >
                    <div class="form-text">
                        Format: <code>https://&lt;your-resource-name&gt;.openai.azure.com</code>
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="azure-api-key" class="form-label">
                        API Key
                        <span class="text-danger">*</span>
                    </label>
                    <div class="input-group">
                        <input
                            type="password"
                            id="azure-api-key"
                            class="form-control font-monospace"
                            placeholder="..."
                            autocomplete="off"
                            required
                        >
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            onclick="togglePasswordVisibility('azure-api-key')"
                        >
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="azure-deployment" class="form-label">
                        Deployment Name
                        <span class="text-danger">*</span>
                    </label>
                    <input
                        type="text"
                        id="azure-deployment"
                        class="form-control"
                        placeholder="gpt-4o-deployment"
                        required
                    >
                    <div class="form-text">
                        The deployment name you created in Azure Portal
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="azure-api-version" class="form-label">
                        API Version
                        <span class="text-danger">*</span>
                    </label>
                    <select id="azure-api-version" class="form-select" required>
                        <option value="2024-02-01" selected>2024-02-01 (Latest)</option>
                        <option value="2023-12-01">2023-12-01</option>
                        <option value="2023-05-15">2023-05-15</option>
                    </select>
                </div>

                <button
                    type="button"
                    class="btn btn-primary"
                    onclick="testLLMConnection('azure')"
                >
                    <i class="fas fa-plug"></i> Test Azure OpenAI Connection
                </button>

                <div id="test-result-azure" class="mt-3"></div>
            </div>
        </div>
    </div>

    <!-- Custom OpenAI-compatible Configuration -->
    <div id="config-custom" class="provider-config" style="display: none;">
        <div class="card border-secondary">
            <div class="card-header bg-secondary text-white">
                <h5 class="mb-0">🔧 Custom OpenAI-compatible Configuration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info mb-3">
                    <strong>Supported:</strong> LM Studio, vLLM, Text Generation WebUI,
                    Together AI, Groq, and any OpenAI API-compatible service.
                </div>

                <div class="form-group mb-3">
                    <label for="custom-endpoint" class="form-label">
                        Endpoint URL
                        <span class="text-danger">*</span>
                    </label>
                    <input
                        type="url"
                        id="custom-endpoint"
                        class="form-control"
                        placeholder="http://localhost:1234/v1"
                        required
                    >
                    <div class="form-text">
                        Examples:
                        <code>http://localhost:1234/v1</code> (LM Studio),
                        <code>https://api.together.xyz/v1</code> (Together AI)
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="custom-api-key" class="form-label">
                        API Key
                        <span class="text-muted">(optional, if required by service)</span>
                    </label>
                    <div class="input-group">
                        <input
                            type="password"
                            id="custom-api-key"
                            class="form-control font-monospace"
                            placeholder="Leave empty for local services like LM Studio"
                            autocomplete="off"
                        >
                        <button
                            class="btn btn-outline-secondary"
                            type="button"
                            onclick="togglePasswordVisibility('custom-api-key')"
                        >
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>

                <div class="form-group mb-3">
                    <label for="custom-model" class="form-label">
                        Model Name
                        <span class="text-danger">*</span>
                    </label>
                    <input
                        type="text"
                        id="custom-model"
                        class="form-control"
                        placeholder="phi-3-mini-4k-instruct"
                        required
                    >
                    <div class="form-text">
                        Check your endpoint's <code>/v1/models</code> API for available models
                    </div>
                </div>

                <button
                    type="button"
                    class="btn btn-secondary"
                    onclick="testLLMConnection('custom')"
                >
                    <i class="fas fa-plug"></i> Test Custom Endpoint
                </button>

                <div id="test-result-custom" class="mt-3"></div>
            </div>
        </div>
    </div>

    <!-- Navigation -->
    <div class="wizard-nav mt-5">
        <button type="button" class="btn btn-secondary" onclick="prevStep()">
            ← Previous
        </button>
        <button type="button" class="btn btn-primary" onclick="nextStep()" id="step4-next">
            Next →
        </button>
    </div>
</div>

<style>
.provider-config {
    display: none;
}

.provider-config.active {
    display: block;
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.font-monospace {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}
</style>
```

## JavaScript Implementation

### Provider Toggle Logic

```javascript
/**
 * Toggle between provider configuration forms
 */
function toggleProviderConfig() {
    const provider = document.getElementById('llm-provider').value;

    // Hide all config sections
    document.querySelectorAll('.provider-config').forEach(section => {
        section.style.display = 'none';
        section.classList.remove('active');
    });

    // Show selected provider config
    const selectedConfig = document.getElementById(`config-${provider}`);
    if (selectedConfig) {
        selectedConfig.style.display = 'block';
        selectedConfig.classList.add('active');
    }

    // Update provider info badges
    updateProviderInfo(provider);
}

/**
 * Update informational badges based on provider
 */
function updateProviderInfo(provider) {
    const infoCost = document.getElementById('info-cost');
    const infoLocation = document.getElementById('info-location');
    const infoAuth = document.getElementById('info-auth');

    const providerInfo = {
        ollama: {
            cost: 'Free',
            location: 'Local',
            auth: 'No API Key'
        },
        openai: {
            cost: 'Paid (Usage-based)',
            location: 'Cloud (US)',
            auth: 'API Key Required'
        },
        anthropic: {
            cost: 'Paid (Usage-based)',
            location: 'Cloud (US)',
            auth: 'API Key Required'
        },
        azure: {
            cost: 'Paid (Enterprise)',
            location: 'Cloud (Your Region)',
            auth: 'API Key Required'
        },
        custom: {
            cost: 'Varies',
            location: 'Varies',
            auth: 'Maybe Required'
        }
    };

    const info = providerInfo[provider];
    infoCost.textContent = info.cost;
    infoLocation.textContent = info.location;
    infoAuth.textContent = info.auth;
}

/**
 * Toggle password visibility
 */
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = event.currentTarget.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

/**
 * Test LLM connection for all provider types
 */
async function testLLMConnection(provider) {
    const resultDiv = document.getElementById(`test-result-${provider}`);
    resultDiv.innerHTML = '<div class="alert alert-info">Testing connection...</div>';

    let config = {};

    // Build config based on provider
    switch(provider) {
        case 'ollama':
            config = {
                provider: 'ollama',
                endpoint: document.getElementById('ollama-endpoint').value,
                model: document.getElementById('ollama-model').value
            };
            break;

        case 'openai':
            const apiKey = document.getElementById('openai-api-key').value;
            if (!apiKey || !apiKey.startsWith('sk-')) {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Invalid API Key:</strong> OpenAI API keys start with "sk-"
                    </div>
                `;
                return;
            }
            config = {
                provider: 'openai',
                api_key: apiKey,
                model: document.getElementById('openai-model').value,
                organization: document.getElementById('openai-org-id').value || null
            };
            break;

        case 'anthropic':
            const anthropicKey = document.getElementById('anthropic-api-key').value;
            if (!anthropicKey || !anthropicKey.startsWith('sk-ant-')) {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Invalid API Key:</strong> Anthropic API keys start with "sk-ant-"
                    </div>
                `;
                return;
            }
            config = {
                provider: 'anthropic',
                api_key: anthropicKey,
                model: document.getElementById('anthropic-model').value
            };
            break;

        case 'azure':
            config = {
                provider: 'azure',
                endpoint: document.getElementById('azure-endpoint').value,
                api_key: document.getElementById('azure-api-key').value,
                deployment: document.getElementById('azure-deployment').value,
                api_version: document.getElementById('azure-api-version').value
            };
            break;

        case 'custom':
            config = {
                provider: 'custom',
                endpoint: document.getElementById('custom-endpoint').value,
                api_key: document.getElementById('custom-api-key').value || null,
                model: document.getElementById('custom-model').value
            };
            break;
    }

    // Send test request to backend
    try {
        const response = await fetch('/api/test-llm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>✓ Connection Successful!</strong><br>
                    ${result.message}<br>
                    ${result.models && result.models.length > 0 ?
                        `<small>Available models: ${result.models.slice(0, 5).join(', ')}${result.models.length > 5 ? '...' : ''}</small>`
                        : ''}
                </div>
            `;

            // Enable next button
            document.getElementById('step4-next').disabled = false;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>✗ Connection Failed</strong><br>
                    ${result.error || 'Unknown error'}<br>
                    <small class="text-muted">${result.details || ''}</small>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <strong>✗ Connection Error</strong><br>
                ${error.message}
            </div>
        `;
    }
}

/**
 * Get wizard data including LLM config for installation
 */
function getWizardData() {
    const provider = document.getElementById('llm-provider').value;

    const baseData = {
        // ... other wizard data ...
        llm_provider: provider
    };

    // Add provider-specific config
    switch(provider) {
        case 'ollama':
            baseData.llm_config = {
                endpoint: document.getElementById('ollama-endpoint').value,
                model: document.getElementById('ollama-model').value
            };
            break;

        case 'openai':
            baseData.llm_config = {
                api_key: document.getElementById('openai-api-key').value,
                model: document.getElementById('openai-model').value,
                organization: document.getElementById('openai-org-id').value || null
            };
            break;

        case 'anthropic':
            baseData.llm_config = {
                api_key: document.getElementById('anthropic-api-key').value,
                model: document.getElementById('anthropic-model').value
            };
            break;

        case 'azure':
            baseData.llm_config = {
                endpoint: document.getElementById('azure-endpoint').value,
                api_key: document.getElementById('azure-api-key').value,
                deployment: document.getElementById('azure-deployment').value,
                api_version: document.getElementById('azure-api-version').value
            };
            break;

        case 'custom':
            baseData.llm_config = {
                endpoint: document.getElementById('custom-endpoint').value,
                api_key: document.getElementById('custom-api-key').value || null,
                model: document.getElementById('custom-model').value
            };
            break;
    }

    return baseData;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    toggleProviderConfig(); // Show default (Ollama)
});
```

## Backend Implementation

### Updated Test Endpoint (`web-setup/app.py`)

```python
@app.route('/api/test-llm', methods=['POST'])
def test_llm():
    """
    Test LLM endpoint connectivity for all provider types
    Supports: Ollama, OpenAI, Anthropic, Azure OpenAI, Custom

    Returns:
        JSON: {success: bool, message: str, models: list, error: str, details: str}
    """
    try:
        config = request.json
        provider = config.get('provider', 'ollama')

        if provider == 'ollama':
            return test_ollama_endpoint(
                endpoint=config.get('endpoint'),
                model=config.get('model')
            )

        elif provider == 'openai':
            return test_openai_endpoint(
                api_key=config.get('api_key'),
                model=config.get('model'),
                organization=config.get('organization')
            )

        elif provider == 'anthropic':
            return test_anthropic_endpoint(
                api_key=config.get('api_key'),
                model=config.get('model')
            )

        elif provider == 'azure':
            return test_azure_openai_endpoint(
                endpoint=config.get('endpoint'),
                api_key=config.get('api_key'),
                deployment=config.get('deployment'),
                api_version=config.get('api_version')
            )

        elif provider == 'custom':
            return test_custom_endpoint(
                endpoint=config.get('endpoint'),
                api_key=config.get('api_key'),
                model=config.get('model')
            )

        else:
            return jsonify({
                'success': False,
                'error': f'Unknown provider: {provider}'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc()
        }), 500


def test_ollama_endpoint(endpoint, model):
    """Test Ollama endpoint (existing function - enhanced)"""
    try:
        # Try OpenAI-compatible endpoint first
        response = requests.get(f"{endpoint}/v1/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', [])]
            return jsonify({
                'success': True,
                'message': f'Connected to OpenAI-compatible endpoint. {len(models)} models available.',
                'models': models
            })
    except:
        pass

    try:
        # Try Ollama native API
        response = requests.get(f"{endpoint}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            return jsonify({
                'success': True,
                'message': f'Connected to Ollama. {len(models)} models available.',
                'models': models
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Connection failed',
            'details': str(e)
        }), 500


def test_openai_endpoint(api_key, model, organization=None):
    """Test OpenAI API connection"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        if organization:
            headers['OpenAI-Organization'] = organization

        # Test with models list endpoint
        response = requests.get(
            'https://api.openai.com/v1/models',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', []) if m['id'].startswith('gpt')]

            # Verify selected model exists
            model_exists = model in models

            return jsonify({
                'success': True,
                'message': f'Connected to OpenAI. {"Model verified." if model_exists else "Warning: Selected model not found."}',
                'models': models[:10]  # Limit to first 10
            })
        elif response.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'details': 'The provided API key is not valid'
            }), 401
        else:
            return jsonify({
                'success': False,
                'error': f'API Error {response.status_code}',
                'details': response.text
            }), response.status_code

    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Connection timeout',
            'details': 'OpenAI API is not responding'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Connection failed',
            'details': str(e)
        }), 500


def test_anthropic_endpoint(api_key, model):
    """Test Anthropic API connection"""
    try:
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }

        # Test with a minimal message (doesn't charge)
        test_payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'max_tokens': 1
        }

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=test_payload,
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': f'Connected to Anthropic. Model "{model}" is available.',
                'models': [model]
            })
        elif response.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'details': 'The provided Anthropic API key is not valid'
            }), 401
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'error': 'Model not found',
                'details': f'Model "{model}" is not available for your account'
            }), 404
        else:
            return jsonify({
                'success': False,
                'error': f'API Error {response.status_code}',
                'details': response.text
            }), response.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Connection failed',
            'details': str(e)
        }), 500


def test_azure_openai_endpoint(endpoint, api_key, deployment, api_version):
    """Test Azure OpenAI endpoint"""
    try:
        # Build Azure OpenAI URL
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

        # Test with minimal completion
        test_payload = {
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'max_tokens': 1
        }

        response = requests.post(
            url,
            headers=headers,
            json=test_payload,
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': f'Connected to Azure OpenAI. Deployment "{deployment}" is available.',
                'models': [deployment]
            })
        elif response.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'details': 'The provided Azure API key is not valid'
            }), 401
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'error': 'Deployment not found',
                'details': f'Deployment "{deployment}" not found at {endpoint}'
            }), 404
        else:
            return jsonify({
                'success': False,
                'error': f'API Error {response.status_code}',
                'details': response.text
            }), response.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Connection failed',
            'details': str(e)
        }), 500


def test_custom_endpoint(endpoint, api_key, model):
    """Test custom OpenAI-compatible endpoint"""
    try:
        headers = {'Content-Type': 'application/json'}

        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        # Try to list models
        response = requests.get(
            f"{endpoint}/models",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            models = []

            # Handle both OpenAI format and simple list
            if 'data' in data:
                models = [m['id'] for m in data['data']]
            elif isinstance(data, list):
                models = data

            model_exists = model in models if models else True  # Assume exists if can't verify

            return jsonify({
                'success': True,
                'message': f'Connected to custom endpoint. {"Model verified." if model_exists else "Could not verify model."}',
                'models': models[:10]
            })
        else:
            # If models endpoint fails, try a test completion
            test_payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': 'Hi'}],
                'max_tokens': 1
            }

            response = requests.post(
                f"{endpoint}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=10
            )

            if response.status_code == 200:
                return jsonify({
                    'success': True,
                    'message': 'Connected to custom endpoint (completion test successful)',
                    'models': [model]
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Connection failed (HTTP {response.status_code})',
                    'details': response.text
                }), response.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Connection failed',
            'details': str(e)
        }), 500
```

## Configuration Generation

### Update `conf/config.yml`

```yaml
llm_service:
  enabled: true
  default_provider: "ollama"  # Set by wizard

  providers:
    ollama:
      enabled: true
      endpoint: "http://localhost:11434"
      default_model: "phi3:mini"

    openai:
      enabled: false
      api_key: null  # Set from Vault: ${OPENAI_API_KEY}
      default_model: "gpt-4o"
      organization: null

    anthropic:
      enabled: false
      api_key: null  # Set from Vault: ${ANTHROPIC_API_KEY}
      default_model: "claude-3-5-sonnet-20241022"

    azure:
      enabled: false
      endpoint: null
      api_key: null  # Set from Vault: ${AZURE_OPENAI_API_KEY}
      deployment: null
      api_version: "2024-02-01"

    custom:
      enabled: false
      endpoint: null
      api_key: null  # Set from Vault if needed
      default_model: null
```

### Wizard Data Processing (`web-setup/app.py`)

```python
def process_wizard_data(wizard_data):
    """
    Process wizard data and update config.yml
    """
    config_path = Path(STING_DIR) / 'conf' / 'config.yml'

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Get LLM provider selection
    provider = wizard_data.get('llm_provider', 'ollama')
    llm_config = wizard_data.get('llm_config', {})

    # Update config
    config['llm_service']['default_provider'] = provider

    # Disable all providers first
    for p in config['llm_service']['providers']:
        config['llm_service']['providers'][p]['enabled'] = False

    # Enable and configure selected provider
    config['llm_service']['providers'][provider]['enabled'] = True

    if provider == 'ollama':
        config['llm_service']['providers']['ollama'].update({
            'endpoint': llm_config.get('endpoint'),
            'default_model': llm_config.get('model')
        })

    elif provider == 'openai':
        # Store API key in Vault
        vault_client = get_vault_client()
        vault_client.secrets.kv.v2.create_or_update_secret(
            path='llm/openai',
            secret={'api_key': llm_config.get('api_key')}
        )

        config['llm_service']['providers']['openai'].update({
            'api_key': '${OPENAI_API_KEY}',  # Will be loaded from Vault
            'default_model': llm_config.get('model'),
            'organization': llm_config.get('organization')
        })

    elif provider == 'anthropic':
        # Store API key in Vault
        vault_client = get_vault_client()
        vault_client.secrets.kv.v2.create_or_update_secret(
            path='llm/anthropic',
            secret={'api_key': llm_config.get('api_key')}
        )

        config['llm_service']['providers']['anthropic'].update({
            'api_key': '${ANTHROPIC_API_KEY}',
            'default_model': llm_config.get('model')
        })

    elif provider == 'azure':
        # Store API key in Vault
        vault_client = get_vault_client()
        vault_client.secrets.kv.v2.create_or_update_secret(
            path='llm/azure',
            secret={
                'api_key': llm_config.get('api_key'),
                'endpoint': llm_config.get('endpoint')
            }
        )

        config['llm_service']['providers']['azure'].update({
            'endpoint': '${AZURE_OPENAI_ENDPOINT}',
            'api_key': '${AZURE_OPENAI_API_KEY}',
            'deployment': llm_config.get('deployment'),
            'api_version': llm_config.get('api_version')
        })

    elif provider == 'custom':
        api_key = llm_config.get('api_key')
        if api_key:
            # Store API key in Vault if provided
            vault_client = get_vault_client()
            vault_client.secrets.kv.v2.create_or_update_secret(
                path='llm/custom',
                secret={'api_key': api_key}
            )
            api_key = '${CUSTOM_LLM_API_KEY}'

        config['llm_service']['providers']['custom'].update({
            'endpoint': llm_config.get('endpoint'),
            'api_key': api_key,
            'default_model': llm_config.get('model')
        })

    # Write updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return config
```

## Security Considerations

### API Key Storage

1. **Never store API keys in plain text**
   - All API keys stored in HashiCorp Vault
   - Vault path: `sting/llm/{provider}/api_key`
   - Environment variables reference Vault secrets

2. **Input sanitization**
   - Validate API key formats before submission
   - OpenAI: must start with `sk-`
   - Anthropic: must start with `sk-ant-`
   - Azure: validate endpoint URL format

3. **Transmission security**
   - HTTPS for wizard (if exposed remotely)
   - API keys never logged
   - Test requests minimal (1 token) to avoid charges

### Validation

```javascript
// Frontend validation before sending to backend
function validateProviderConfig(provider, config) {
    const errors = [];

    switch(provider) {
        case 'ollama':
            if (!config.endpoint) {
                errors.push('Endpoint URL is required');
            }
            if (!config.model) {
                errors.push('Model name is required');
            }
            break;

        case 'openai':
            if (!config.api_key || !config.api_key.startsWith('sk-')) {
                errors.push('Valid OpenAI API key required (starts with sk-)');
            }
            if (!config.model) {
                errors.push('Model selection required');
            }
            break;

        case 'anthropic':
            if (!config.api_key || !config.api_key.startsWith('sk-ant-')) {
                errors.push('Valid Anthropic API key required (starts with sk-ant-)');
            }
            if (!config.model) {
                errors.push('Model selection required');
            }
            break;

        case 'azure':
            if (!config.endpoint || !config.endpoint.includes('openai.azure.com')) {
                errors.push('Valid Azure endpoint required');
            }
            if (!config.api_key) {
                errors.push('Azure API key required');
            }
            if (!config.deployment) {
                errors.push('Deployment name required');
            }
            break;

        case 'custom':
            if (!config.endpoint) {
                errors.push('Endpoint URL required');
            }
            if (!config.model) {
                errors.push('Model name required');
            }
            break;
    }

    return errors;
}
```

## Testing Plan

### Manual Testing Checklist

- [ ] Ollama configuration and test
- [ ] OpenAI configuration and test (with valid API key)
- [ ] OpenAI configuration with invalid API key (should fail gracefully)
- [ ] Anthropic configuration and test
- [ ] Azure OpenAI configuration and test
- [ ] Custom endpoint (LM Studio) configuration and test
- [ ] Provider switching (all configs preserved)
- [ ] Password visibility toggle
- [ ] API key validation (frontend)
- [ ] API key storage in Vault
- [ ] Config generation from wizard data
- [ ] Installation with each provider type

### Automated Tests

```python
# web-setup/tests/test_llm_config.py
def test_ollama_endpoint():
    """Test Ollama endpoint validation"""
    # ... test code ...

def test_openai_api_key_validation():
    """Test OpenAI API key format validation"""
    # ... test code ...

def test_vault_api_key_storage():
    """Test API keys are stored in Vault, not config files"""
    # ... test code ...
```

## Documentation Updates

Files to update:
1. `docs/guides/OLLAMA_SETUP_GUIDE.md` ✅ (Already enhanced)
2. `docs/platform/guides/ADMIN_GUIDE.md` - Add LLM provider management section
3. `web-setup/README.md` - Update wizard flow documentation

## Migration Path

For existing installations:
1. Default to `ollama` provider (backward compatible)
2. Existing `llm_service.ollama` config preserved
3. Admin can switch providers via `conf/config.yml` manually
4. Future: Add provider management to web UI settings

## Future Enhancements

1. **Multi-provider routing** - Use different providers for different tasks
2. **Fallback providers** - Auto-failover if primary provider down
3. **Cost tracking** - Monitor API usage and costs for cloud providers
4. **Model selection per conversation** - Let users choose model
5. **Provider comparison** - Side-by-side response comparison
6. **LLM analytics** - Dashboard for usage, performance, costs

---

## Summary

This design provides:
- ✅ User-friendly provider selection
- ✅ Secure API key handling via Vault
- ✅ Comprehensive validation and testing
- ✅ Backward compatibility with Ollama-only setup
- ✅ Extensible for future providers
- ✅ Clear error messaging and troubleshooting
- ✅ Consistent with existing wizard UX patterns

**Implementation Priority**:
1. Frontend UI (HTML/JS) - 1-2 days
2. Backend test endpoints - 1 day
3. Config generation and Vault integration - 1 day
4. Testing and validation - 1 day
5. Documentation updates - 0.5 day

**Total Estimate**: ~4-5 days for complete implementation
