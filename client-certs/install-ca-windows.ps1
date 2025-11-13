# STING-CE CA Certificate Installer for Windows
# Run this script as Administrator

param(
    [string]$CAFile = "sting-ca.pem",
    [string]$Domain = "captain-den.local",
    [string]$VMIP = "192.168.68.78"
)

Write-Host "🔐 STING-CE Certificate Authority Installer for Windows" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ Error: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if CA file exists
if (-not (Test-Path $CAFile)) {
    Write-Host "❌ Error: $CAFile not found" -ForegroundColor Red
    Write-Host "Please run this script from the directory containing the CA certificate" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Install CA certificate
Write-Host "📋 Installing CA certificate..." -ForegroundColor Yellow
try {
    Import-Certificate -FilePath $CAFile -CertStoreLocation Cert:\LocalMachine\Root
    Write-Host "✅ CA certificate installed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error installing certificate: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Add domain to hosts file if needed
Write-Host ""
Write-Host "🌐 Setting up domain resolution..." -ForegroundColor Yellow
$hostsFile = "$env:SystemRoot\System32\drivers\etc\hosts"
$hostsContent = Get-Content $hostsFile -ErrorAction SilentlyContinue
if ($hostsContent -notmatch $Domain) {
    Write-Host "Adding $Domain to hosts file..." -ForegroundColor Yellow
    Add-Content -Path $hostsFile -Value "$VMIP $Domain"
    Write-Host "✅ Domain added to hosts file" -ForegroundColor Green
} else {
    Write-Host "✅ Domain already in hosts file" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 Installation complete!" -ForegroundColor Green
Write-Host "You can now access STING securely at: https://$Domain:8443" -ForegroundColor Cyan
Write-Host "⚠️  Please restart your browser to load the new certificate" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
