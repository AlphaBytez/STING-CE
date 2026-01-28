# STING-CE Packer Variables
# Copy this file and customize for your build

# STING Version (should match git tag)
sting_version = "1.0.0"

# Ubuntu 24.04 LTS Server
# NOTE: Do NOT set iso_url/iso_checksum here - they are auto-selected based on --arch
# The build script passes -var "arch=arm64" or "arch=amd64" which selects the right ISO
ubuntu_version = "24.04"
# iso_url and iso_checksum are dynamically set in sting-ce.pkr.hcl based on arch variable

# VM Configuration (aligned with docs minimum requirements)
vm_name   = "sting-ce-quickstart"
disk_size = "40G"  # 40GB - enough for Docker images
memory    = 8192   # 8GB RAM (STING minimum requirement)
cpus      = 4      # 4 cores (STING minimum requirement)

# Build user (will be the default login)
ssh_username = "sting"
ssh_password = "sting-install"  # Changed on first boot

# Build settings
headless = true  # Set to false to see VM console during build

# Repository
sting_repo = "https://github.com/AlphaBytez/STING-CE.git"

# Output
output_directory = "output"
