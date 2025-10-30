# WSL2 Network Blocker Diagnostic
# Run this in PowerShell as Administrator

Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   WSL2 Network Blocker Diagnostic         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Check 1: VPN Software
Write-Host "🔍 Checking for VPN software..." -ForegroundColor Yellow
$vpnProcesses = @(
    "openvpn", "cisco", "anyconnect", "nordvpn", "expressvpn", 
    "surfshark", "privatevpn", "protonvpn", "mullvad", "tailscale",
    "zerotier", "hamachi", "GlobalProtect"
)

$foundVpns = @()
foreach ($vpn in $vpnProcesses) {
    $process = Get-Process -Name "*$vpn*" -ErrorAction SilentlyContinue
    if ($process) {
        $foundVpns += $process.ProcessName
        Write-Host "  ⚠️  Found: $($process.ProcessName)" -ForegroundColor Red
    }
}

if ($foundVpns.Count -eq 0) {
    Write-Host "  ✓ No VPN processes detected" -ForegroundColor Green
} else {
    Write-Host "`n  💡 TIP: Try disabling VPN temporarily to test" -ForegroundColor Yellow
}

# Check 2: WSL Network Adapter
Write-Host "`n🔍 Checking WSL network adapter..." -ForegroundColor Yellow
$wslAdapter = Get-NetAdapter | Where-Object {$_.Name -like "*WSL*"}

if ($wslAdapter) {
    Write-Host "  ✓ Found: $($wslAdapter.Name)" -ForegroundColor Green
    Write-Host "    Status: $($wslAdapter.Status)" -ForegroundColor Cyan
    Write-Host "    Interface Description: $($wslAdapter.InterfaceDescription)" -ForegroundColor Cyan
    
    if ($wslAdapter.Status -ne "Up") {
        Write-Host "  ⚠️  Adapter is not UP!" -ForegroundColor Red
        Write-Host "    Try: Get-NetAdapter | Where-Object {`$_.Name -like '*WSL*'} | Restart-NetAdapter" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  No WSL adapter found!" -ForegroundColor Red
    Write-Host "    WSL network bridge is missing" -ForegroundColor Yellow
}

# Check 3: Windows Firewall
Write-Host "`n🔍 Checking Windows Firewall..." -ForegroundColor Yellow
$firewallProfiles = Get-NetFirewallProfile

foreach ($profile in $firewallProfiles) {
    $status = if ($profile.Enabled) { "ENABLED" } else { "DISABLED" }
    $color = if ($profile.Enabled) { "Red" } else { "Green" }
    Write-Host "  $($profile.Name): $status" -ForegroundColor $color
}

# Check 4: Hyper-V Status
Write-Host "`n🔍 Checking Hyper-V..." -ForegroundColor Yellow
$hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue

if ($hyperv -and $hyperv.State -eq "Enabled") {
    Write-Host "  ✓ Hyper-V is enabled" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Hyper-V might not be properly enabled" -ForegroundColor Red
}

# Check 5: WSL Status
Write-Host "`n🔍 Checking WSL status..." -ForegroundColor Yellow
try {
    $wslList = wsl --list --verbose
    Write-Host "  ✓ WSL is installed" -ForegroundColor Green
    Write-Host "`n  Distributions:" -ForegroundColor Cyan
    $wslList | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
} catch {
    Write-Host "  ⚠️  WSL command failed" -ForegroundColor Red
}

# Check 6: NAT Settings
Write-Host "`n🔍 Checking NAT configuration..." -ForegroundColor Yellow
$natNetworks = Get-NetNat -ErrorAction SilentlyContinue

if ($natNetworks) {
    Write-Host "  ✓ Found NAT networks:" -ForegroundColor Green
    foreach ($nat in $natNetworks) {
        Write-Host "    Name: $($nat.Name)" -ForegroundColor Cyan
        Write-Host "    Internal IP Prefix: $($nat.InternalIPInterfaceAddressPrefix)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  ⚠️  No NAT networks found (this might be OK)" -ForegroundColor Yellow
}

# Check 7: Third-party Security Software
Write-Host "`n🔍 Checking for security software..." -ForegroundColor Yellow
$securitySoftware = @(
    "MsMpEng",           # Windows Defender
    "avp",               # Kaspersky
    "avgui",             # AVG
    "avast",             # Avast
    "mcafee",            # McAfee
    "norton",            # Norton
    "bdagent",           # Bitdefender
    "eset",              # ESET
    "sophos"             # Sophos
)

$foundSecurity = @()
foreach ($sec in $securitySoftware) {
    $process = Get-Process -Name "*$sec*" -ErrorAction SilentlyContinue
    if ($process) {
        $foundSecurity += $process.ProcessName
        Write-Host "  ℹ️  Found: $($process.ProcessName)" -ForegroundColor Cyan
    }
}

if ($foundSecurity.Count -eq 0) {
    Write-Host "  ℹ️  No third-party security software detected" -ForegroundColor Cyan
}

# Recommendations
Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Recommendations                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan

if ($foundVpns.Count -gt 0) {
    Write-Host "1. ⚠️  DISABLE VPN temporarily and test WSL" -ForegroundColor Red
    Write-Host "   VPNs often block WSL2 traffic by default`n" -ForegroundColor Yellow
}

if ($wslAdapter -and $wslAdapter.Status -ne "Up") {
    Write-Host "2. ⚠️  RESTART WSL Network Adapter:" -ForegroundColor Red
    Write-Host "   wsl --shutdown" -ForegroundColor White
    Write-Host "   Get-NetAdapter | Where-Object {`$_.Name -like '*WSL*'} | Restart-NetAdapter`n" -ForegroundColor White
}

$enabledFirewalls = $firewallProfiles | Where-Object { $_.Enabled }
if ($enabledFirewalls) {
    Write-Host "3. 🔥 TEST: Temporarily disable Windows Firewall:" -ForegroundColor Yellow
    Write-Host "   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False" -ForegroundColor White
    Write-Host "   (Re-enable after testing: -Enabled True)`n" -ForegroundColor Gray
}

if (!$wslAdapter) {
    Write-Host "4. ⚠️  REBUILD WSL Network:" -ForegroundColor Red
    Write-Host "   wsl --shutdown" -ForegroundColor White
    Write-Host "   netsh winsock reset" -ForegroundColor White
    Write-Host "   netsh int ip reset all" -ForegroundColor White
    Write-Host "   Restart-Computer`n" -ForegroundColor White
}

Write-Host "`n💡 QUICK TEST STEPS:" -ForegroundColor Cyan
Write-Host "   1. Disconnect any VPN" -ForegroundColor White
Write-Host "   2. Run: wsl --shutdown" -ForegroundColor White
Write-Host "   3. Wait 10 seconds" -ForegroundColor White
Write-Host "   4. Run: wsl" -ForegroundColor White
Write-Host "   5. Test: ping 8.8.8.8" -ForegroundColor White
Write-Host ""
