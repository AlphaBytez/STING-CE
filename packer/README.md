# STING-CE Packer Build

This directory contains [HashiCorp Packer](https://www.packer.io/) templates to build STING-CE VM images.

## Quick Start OVA

The Quick Start OVA is a pre-configured Ubuntu VM with:
- Ubuntu 24.04 LTS
- Docker and Docker Compose pre-installed
- Base Docker images pre-pulled (postgres, redis, nginx)
- STING-CE source code cloned
- First-boot auto-installer

**User Experience:**
1. Download OVA (~1.5-2 GB compressed)
2. Import into VMware or VirtualBox
3. Boot VM
4. Installer launches automatically
5. Access web wizard, configure STING
6. ~15-20 minutes to fully running

## Building the OVA

### Prerequisites

1. Install [Packer](https://developer.hashicorp.com/packer/downloads) (1.9+)
2. Install [VirtualBox](https://www.virtualbox.org/) (for VirtualBox builds)

### Build Commands

```bash
# Initialize Packer plugins
packer init sting-ce.pkr.hcl

# Validate the template
packer validate -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl

# Build the OVA (takes 20-30 minutes)
packer build -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl

# Build with visible VM console (for debugging)
packer build -var-file=variables.pkrvars.hcl -var="headless=false" sting-ce.pkr.hcl
```

### Build Output

After successful build:
```
output/
├── virtualbox/
│   └── sting-ce-quickstart-1.0.0.ova
├── sting-ce-quickstart-1.0.0.sha256
└── manifest.json
```

## Directory Structure

```
packer/
├── sting-ce.pkr.hcl         # Main Packer template
├── variables.pkrvars.hcl     # Build variables
├── README.md                 # This file
├── http/                     # Ubuntu autoinstall configs
│   ├── user-data             # Cloud-init autoinstall
│   └── meta-data             # Cloud-init metadata
├── scripts/                  # Provisioning scripts
│   ├── 01-base-setup.sh      # OS updates, packages
│   ├── 02-install-docker.sh  # Docker installation
│   ├── 03-clone-sting.sh     # Clone STING repo
│   ├── 04-setup-first-boot.sh # First-boot service
│   └── 99-cleanup.sh         # Minimize image size
└── files/                    # Files to copy into VM
    ├── sting-first-boot.service  # Systemd service
    └── sting-first-boot.sh       # First-boot script
```

## Customization

### Variables

Edit `variables.pkrvars.hcl` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `sting_version` | `1.0.0` | STING version tag |
| `disk_size` | `40960` | Disk size in MB (40GB) |
| `memory` | `4096` | RAM in MB (4GB) |
| `cpus` | `2` | Number of CPUs |
| `ssh_username` | `sting` | Default user |
| `headless` | `true` | Run build without GUI |

### Building for AWS

Uncomment the AWS source in `sting-ce.pkr.hcl` and configure:

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Build AMI
packer build -only=amazon-ebs.sting-ce -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl
```

## First Boot Experience

When the VM boots for the first time:

1. Auto-login as `sting` user
2. STING installer launches automatically
3. Web wizard available at `http://VM_IP:5000`
4. User completes configuration
5. STING services start
6. Access STING at `https://VM_IP:8443`

## Troubleshooting

### Build fails at ISO download
Update `iso_url` and `iso_checksum` in `variables.pkrvars.hcl` with current Ubuntu ISO.

### SSH connection timeout
- Increase `ssh_timeout` in template
- Check VirtualBox network settings
- Try with `headless=false` to see console

### VM doesn't boot after build
- Verify VirtualBox Guest Additions installed
- Check VM has enough RAM (4GB minimum)
- Try importing OVA fresh

## Contributing

To improve the build:
1. Test changes locally with `packer build`
2. Verify first-boot experience in fresh VM
3. Submit PR with changes

## License

Same as STING-CE main project.
