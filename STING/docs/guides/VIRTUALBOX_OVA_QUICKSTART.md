# VirtualBox OVA Quick Start Guide

This guide covers importing and configuring the STING-CE Quick Start OVA in VirtualBox.

## Importing the OVA

### MAC Address Policy

During import, VirtualBox shows a "MAC Address Policy" dropdown. The default is **"Include only NAT network adapter MAC addresses"**.

**Recommended setting**: Keep the default or select **"Generate new MAC addresses for all network adapters"** to avoid MAC address conflicts if running multiple instances.

### Import Steps

1. **File** → **Import Appliance**
2. Select the `.ova` file
3. Review settings (can be adjusted after import)
4. Click **Import**

## Required Post-Import Settings

After import, you **must** adjust these settings before starting the VM:

### 1. Storage - Enable Host I/O Cache

**Critical for performance**. Without this, disk operations are extremely slow and health checks may timeout.

1. Select the VM → **Settings** → **Storage**
2. Click on the **SATA Controller** (not the disk)
3. Check **"Use Host I/O Cache"**
4. Click **OK**

### 2. Network - Switch to Bridged Adapter

For network accessibility from your host and other machines:

1. Select the VM → **Settings** → **Network**
2. **Attached to**: Change from "NAT" to **"Bridged Adapter"**
3. **Name**: Select your active network interface
4. **Advanced** → **Adapter Type**: Change to **"Paravirtualized Network (virtio-net)"** for better performance
5. Click **OK**

### 3. Memory (RAM)

The OVA defaults to 8 GB RAM. For better performance:

1. Select the VM → **Settings** → **System** → **Motherboard**
2. **Base Memory**: 8192 MB minimum, **16384 MB recommended**
3. Click **OK**

### 4. Processors

The OVA defaults to 4 CPUs, which should be sufficient. Adjust if needed:

1. Select the VM → **Settings** → **System** → **Processor**
2. **Processors**: 4 minimum, more if available
3. Click **OK**

## First Boot

1. Start the VM
2. Login with:
   - **Username**: `sting`
   - **Password**: `sting-install`
3. The installation wizard will start automatically on first boot
4. Follow the on-screen prompts to complete setup

## Accessing STING-CE

After installation completes:

- **Web Interface**: `https://<vm-hostname>.local:8443`
- The VM uses Avahi/mDNS for `.local` hostname resolution
- Install the CA certificate on your client machine for trusted HTTPS

## Troubleshooting

### VM Starts But Services Fail Health Checks

1. Ensure **Host I/O Cache** is enabled (see above)
2. Check that the VM has sufficient RAM (8 GB minimum)
3. Wait for Docker services to fully start (can take 2-3 minutes)

### Cannot Access Web Interface

1. Verify network is set to **Bridged Adapter**
2. Check the VM has an IP address: `ip addr show`
3. Ensure mDNS is working: `hostname` should show the local hostname
4. Try accessing via IP address instead of hostname

### Slow Performance

1. Enable **Host I/O Cache** on the SATA controller
2. Switch network to **Paravirtualized (virtio-net)**
3. Increase RAM to 16 GB if available
4. Ensure VirtualBox Guest Additions are installed (included in OVA)

---
*Last Updated: December 2025*
