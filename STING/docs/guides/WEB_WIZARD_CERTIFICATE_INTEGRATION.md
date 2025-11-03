# Web Wizard Certificate Integration - Implementation Plan

## Overview

Integrate automated certificate generation and distribution into the STING-CE web setup wizard to prevent WebAuthn certificate errors before they occur.

## Integration Points

### 1. Web Wizard Flow Enhancement

**Current Flow:**
```
System Config → Email Config → LLM Config → Review → Install → Redirect
```

**Enhanced Flow:**
```
System Config → Email Config → LLM Config → Certificate Setup → Review → Install → Redirect
```

### 2. Client IP Detection

The web wizard already has the client IP available via Flask request context:

```python
# In web-setup/app.py
client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
client_ip = client_ip.split(',')[0] if client_ip else request.remote_addr
```

### 3. Certificate Generation Integration

**Option A: Direct Integration**
- Import certificate functions from manage_sting.sh into Python
- Generate certificates within the wizard process

**Option B: Subprocess Call (Recommended)**
- Use subprocess to call existing manage_sting.sh export-certs
- Leverage existing, tested certificate generation logic

### 4. Implementation Steps

#### Step 1: Add Certificate Step to Wizard

**File: `web-setup/app.py`**

Add new route for certificate generation:

```python
@app.route('/api/wizard/certificates', methods=['GET', 'POST'])
def handle_certificates():
    if request.method == 'GET':
        # Return current certificate status and client info
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Get current STING configuration
        state = load_setup_state()
        config_data = state.get('wizard_data', {})
        sting_hostname = config_data.get('system', {}).get('hostname', 'localhost')
        
        return jsonify({
            'client_ip': client_ip,
            'sting_hostname': sting_hostname,
            'certificate_needed': client_ip != sting_hostname,
            'platform_detected': detect_client_platform(request.headers.get('User-Agent', ''))
        })
    
    elif request.method == 'POST':
        # Generate certificate bundle
        return generate_certificate_bundle()

def generate_certificate_bundle():
    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Create temporary directory for certificate export
        cert_dir = os.path.join(SETUP_DIR, 'certificates', str(int(time.time())))
        os.makedirs(cert_dir, exist_ok=True)
        
        # Call manage_sting.sh export-certs
        sting_dir = os.path.dirname(STING_SOURCE)
        cmd = [os.path.join(sting_dir, 'manage_sting.sh'), 'export-certs', cert_dir]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=sting_dir)
        
        if result.returncode == 0:
            # Create downloadable zip file
            zip_path = create_certificate_zip(cert_dir)
            
            return jsonify({
                'success': True,
                'download_url': f'/api/wizard/certificates/download/{os.path.basename(zip_path)}',
                'client_ip': client_ip,
                'instructions_url': '/api/wizard/certificates/instructions'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Certificate generation failed: {result.stderr}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Certificate generation error: {str(e)}'
        }), 500

def detect_client_platform(user_agent):
    ua_lower = user_agent.lower()
    if 'windows' in ua_lower:
        return 'windows'
    elif 'mac' in ua_lower or 'darwin' in ua_lower:
        return 'macos'
    elif 'linux' in ua_lower:
        return 'linux'
    else:
        return 'unknown'
```

#### Step 2: Add Certificate Download Endpoints

```python
@app.route('/api/wizard/certificates/download/<filename>')
def download_certificate_bundle(filename):
    cert_dir = os.path.join(SETUP_DIR, 'certificates')
    return send_from_directory(cert_dir, filename, as_attachment=True)

@app.route('/api/wizard/certificates/instructions')
def certificate_instructions():
    return jsonify({
        'windows': {
            'title': 'Windows Installation',
            'steps': [
                'Download the certificate bundle',
                'Extract the ZIP file',
                'Right-click PowerShell and select "Run as Administrator"',
                'Navigate to the extracted folder',
                'Run: .\\install-ca-windows.ps1',
                'Follow the prompts to install the certificate'
            ]
        },
        'macos': {
            'title': 'macOS Installation', 
            'steps': [
                'Download the certificate bundle',
                'Extract the ZIP file',
                'Open Terminal',
                'Navigate to the extracted folder',
                'Run: ./install-ca-mac.sh',
                'Enter your password when prompted'
            ]
        },
        'linux': {
            'title': 'Linux Installation',
            'steps': [
                'Download the certificate bundle',
                'Extract the ZIP file', 
                'Open Terminal',
                'Navigate to the extracted folder',
                'Run: ./install-ca-linux.sh',
                'Enter sudo password when prompted'
            ]
        }
    })
```

#### Step 3: Frontend Certificate Step

**File: `web-setup/templates/wizard.html`**

Add certificate setup step to the wizard flow:

```javascript
// Add to steps array
{
    id: 'certificates',
    title: 'Certificate Setup',
    description: 'Install certificates for secure WebAuthn access'
}

// Add step handler
async function handleCertificateStep() {
    try {
        // Get certificate status
        const response = await fetch('/api/wizard/certificates');
        const data = await response.json();
        
        if (data.certificate_needed) {
            showCertificateInstallation(data);
        } else {
            showCertificateSkip(data);
        }
    } catch (error) {
        console.error('Certificate check failed:', error);
    }
}

function showCertificateInstallation(data) {
    const content = `
        <div class="certificate-setup">
            <h3>Certificate Installation Required</h3>
            <p>To ensure WebAuthn/passkey authentication works properly:</p>
            
            <div class="client-info">
                <p><strong>Your IP:</strong> ${data.client_ip}</p>
                <p><strong>STING Server:</strong> ${data.sting_hostname}</p>
                <p><strong>Platform:</strong> ${data.platform_detected}</p>
            </div>
            
            <button onclick="generateCertificates()" class="btn-primary">
                Generate Certificate Bundle
            </button>
            
            <div id="certificate-download" style="display:none;">
                <!-- Download links and instructions appear here -->
            </div>
            
            <div class="validation">
                <label>
                    <input type="checkbox" id="cert-installed"> 
                    I have installed the certificate on my machine
                </label>
            </div>
        </div>
    `;
    
    document.getElementById('step-certificates').innerHTML = content;
}

async function generateCertificates() {
    try {
        showLoader('Generating certificates...');
        
        const response = await fetch('/api/wizard/certificates', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showCertificateDownload(data);
        } else {
            showError('Certificate generation failed: ' + data.error);
        }
    } catch (error) {
        showError('Certificate generation error: ' + error.message);
    }
}
```

## Benefits of This Integration

### 1. Proactive Problem Solving
- **Prevents certificate errors** before they occur
- **Educates users** about the importance of certificates
- **Provides clear guidance** for certificate installation

### 2. Seamless User Experience  
- **No confusion at login** - certificates already installed
- **Platform-specific instructions** - users get relevant guidance
- **Automated generation** - no manual certificate management

### 3. Production Ready
- **Works in any deployment scenario** - VMs, containers, remote servers
- **Scales to multiple users** - each gets their own certificate bundle
- **Enterprise friendly** - certificates can be deployed via IT policies

### 4. Technical Robustness
- **Leverages existing code** - reuses proven certificate generation logic
- **Error handling** - graceful fallbacks if certificate generation fails
- **Optional installation** - users can skip if they understand the risks

## Implementation Timeline

**Phase 1 (Current Sprint):**
- [ ] Add certificate step to wizard flow
- [ ] Implement backend certificate generation endpoints
- [ ] Basic frontend certificate download UI

**Phase 2 (Next Sprint):**
- [ ] Enhanced UI with platform detection
- [ ] Comprehensive installation instructions
- [ ] Certificate validation and status checking

**Phase 3 (Future):**
- [ ] CLI wizard integration
- [ ] Automated certificate deployment options
- [ ] Enterprise certificate management features

## Risk Mitigation

**Risk:** Certificate generation fails during wizard
**Mitigation:** Graceful fallback - allow users to continue without certificates, provide manual instructions

**Risk:** User confusion about certificate installation
**Mitigation:** Clear, platform-specific instructions with screenshots

**Risk:** Increased wizard complexity
**Mitigation:** Make certificate step optional, provide skip option with clear warnings

---

This integration transforms certificate management from a post-installation problem into a proactive setup step, ensuring seamless WebAuthn authentication from day one.