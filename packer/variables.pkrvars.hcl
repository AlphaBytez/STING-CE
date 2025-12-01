# STING-CE Packer Variables
# Copy this file and customize for your build

# STING Version (should match git tag)
sting_version = "1.0.0"

# Ubuntu 24.04.1 LTS Server ISO
ubuntu_version = "24.04"
iso_url        = "https://releases.ubuntu.com/24.04.1/ubuntu-24.04.1-live-server-amd64.iso"
iso_checksum   = "sha256:d6dab0c3a657988501b4bd76f1297c053df710e06e0c3aece60dead24f270b4d"

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
