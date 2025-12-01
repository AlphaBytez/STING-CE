# STING-CE Packer Variables
# Copy this file and customize for your build

# STING Version (should match git tag)
sting_version = "1.0.0"

# Ubuntu 24.04.3 LTS Server ISO (latest point release)
ubuntu_version = "24.04"
iso_url        = "https://releases.ubuntu.com/24.04/ubuntu-24.04.3-live-server-amd64.iso"
iso_checksum   = "sha256:c3514bf0056180d09376462a7a1b4f213c1d6e8ea67fae5c25099c6fd3d8274b"

# VM Configuration (aligned with docs minimum requirements)
vm_name   = "sting-ce-quickstart"
disk_size = 40960  # 40GB - enough for Docker images
memory    = 8192   # 8GB RAM (STING minimum requirement)
cpus      = 4      # 4 cores (STING minimum requirement)

# Build user (will be the default login)
ssh_username = "sting"
ssh_password = "sting-install"  # Changed on first boot

# Build settings
headless = true  # Set to false to see VM console during build

# Repository
sting_repo = "https://github.com/AlphaBytez/STING-CE-Public.git"

# Output
output_directory = "output"
