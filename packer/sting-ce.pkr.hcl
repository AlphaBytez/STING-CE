# STING-CE Packer Template
# Builds a "Quick Start" OVA with Ubuntu 24.04, Docker, and STING pre-staged
#
# Usage:
#   packer init sting-ce.pkr.hcl
#   packer build -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl
#
# Outputs:
#   - VirtualBox OVA (for VMware/VirtualBox import)
#   - AWS AMI (optional, if AWS credentials configured)

packer {
  required_plugins {
    virtualbox = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/virtualbox"
    }
    amazon = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "sting_version" {
  type        = string
  description = "STING-CE version tag"
  default     = "1.0.0"
}

variable "ubuntu_version" {
  type        = string
  description = "Ubuntu version"
  default     = "24.04"
}

variable "iso_url" {
  type        = string
  description = "Ubuntu Server ISO URL"
  default     = "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-live-server-amd64.iso"
}

variable "iso_checksum" {
  type        = string
  description = "Ubuntu ISO SHA256 checksum"
  default     = "sha256:e240e4b801f7bb68c20d1356b60571d2d7d4e1e1c3c2e9d4a2a3b5c8d9e0f1a2"  # Update with actual checksum
}

variable "vm_name" {
  type        = string
  description = "VM name"
  default     = "sting-ce-quickstart"
}

variable "disk_size" {
  type        = number
  description = "Disk size in MB"
  default     = 40960  # 40GB
}

variable "memory" {
  type        = number
  description = "RAM in MB"
  default     = 8192  # 8GB (matches STING minimum requirements)
}

variable "cpus" {
  type        = number
  description = "Number of CPUs"
  default     = 4  # 4 cores (matches STING minimum requirements)
}

variable "ssh_username" {
  type        = string
  description = "SSH username for provisioning"
  default     = "sting"
}

variable "ssh_password" {
  type        = string
  description = "SSH password for provisioning (will be disabled after build)"
  default     = "sting-install"
  sensitive   = true
}

variable "headless" {
  type        = bool
  description = "Run build headless (no GUI)"
  default     = true
}

variable "sting_repo" {
  type        = string
  description = "STING-CE Git repository URL"
  default     = "https://github.com/AlphaBytez/STING-CE-Public.git"
}

variable "output_directory" {
  type        = string
  description = "Output directory for built images"
  default     = "output"
}

# =============================================================================
# Locals
# =============================================================================

locals {
  build_timestamp = formatdate("YYYYMMDD-hhmmss", timestamp())
  vm_description  = "STING-CE Quick Start v${var.sting_version} - Pre-configured Ubuntu with Docker and STING installer ready. Boot and access the web installer at https://<VM_IP>:5000"
}

# =============================================================================
# Source: VirtualBox ISO Builder
# =============================================================================

source "virtualbox-iso" "sting-ce" {
  vm_name              = "${var.vm_name}-${var.sting_version}"
  guest_os_type        = "Ubuntu_64"
  headless             = var.headless

  # ISO configuration
  iso_url              = var.iso_url
  iso_checksum         = var.iso_checksum

  # VM resources
  disk_size            = var.disk_size
  memory               = var.memory
  cpus                 = var.cpus

  # Network
  http_directory       = "http"

  # Boot command for Ubuntu autoinstall
  boot_wait            = "5s"
  boot_command         = [
    "<esc><wait>",
    "e<wait>",
    "<down><down><down><end>",
    " autoinstall ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
    "<f10>"
  ]

  # SSH configuration
  ssh_username         = var.ssh_username
  ssh_password         = var.ssh_password
  ssh_timeout          = "30m"
  ssh_handshake_attempts = 100

  # Shutdown
  shutdown_command     = "echo '${var.ssh_password}' | sudo -S shutdown -P now"

  # Output
  output_directory     = "${var.output_directory}/virtualbox"
  output_filename      = "${var.vm_name}-${var.sting_version}"
  format               = "ova"

  # VirtualBox settings
  vboxmanage = [
    ["modifyvm", "{{.Name}}", "--nat-localhostreachable1", "on"],
    ["modifyvm", "{{.Name}}", "--audio", "none"],
    ["modifyvm", "{{.Name}}", "--usb", "off"],
    ["modifyvm", "{{.Name}}", "--vrde", "off"],
    ["modifyvm", "{{.Name}}", "--graphicscontroller", "vmsvga"],
    ["modifyvm", "{{.Name}}", "--vram", "16"],
    ["modifyvm", "{{.Name}}", "--description", "${local.vm_description}"]
  ]

  # Guest additions (for shared folders, better integration)
  guest_additions_mode = "upload"
}

# =============================================================================
# Source: AWS AMI Builder (optional)
# =============================================================================

source "amazon-ebs" "sting-ce" {
  ami_name        = "sting-ce-quickstart-${var.sting_version}-${local.build_timestamp}"
  ami_description = local.vm_description
  instance_type   = "t3.medium"
  region          = "us-east-1"

  source_ami_filter {
    filters = {
      name                = "ubuntu/images/*ubuntu-noble-24.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    owners      = ["099720109477"]  # Canonical
    most_recent = true
  }

  ssh_username = "ubuntu"

  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 40
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name        = "STING-CE Quick Start"
    Version     = var.sting_version
    BuildTime   = local.build_timestamp
    Application = "STING-CE"
  }

  # Skip AMI build if no AWS credentials
  skip_create_ami = true  # Set to false when AWS is configured
}

# =============================================================================
# Build Definition
# =============================================================================

build {
  name = "sting-ce-quickstart"

  sources = [
    "source.virtualbox-iso.sting-ce",
    # "source.amazon-ebs.sting-ce",  # Uncomment when AWS configured
  ]

  # ==========================================================================
  # Provisioning Steps
  # ==========================================================================

  # Wait for cloud-init to complete
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait || true",
      "echo 'Cloud-init complete.'"
    ]
  }

  # Base system setup
  provisioner "shell" {
    script = "scripts/01-base-setup.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S bash '{{.Path}}'"
  }

  # Install Docker
  provisioner "shell" {
    script = "scripts/02-install-docker.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S bash '{{.Path}}'"
    environment_vars = [
      "STING_USER=${var.ssh_username}"
    ]
  }

  # Clone STING repository
  provisioner "shell" {
    script = "scripts/03-clone-sting.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S -E bash '{{.Path}}'"
    environment_vars = [
      "STING_REPO=${var.sting_repo}",
      "STING_VERSION=${var.sting_version}",
      "STING_USER=${var.ssh_username}"
    ]
  }

  # Copy first-boot service files
  provisioner "file" {
    source      = "files/sting-first-boot.service"
    destination = "/tmp/sting-first-boot.service"
  }

  provisioner "file" {
    source      = "files/sting-first-boot.sh"
    destination = "/tmp/sting-first-boot.sh"
  }

  # Install first-boot service
  provisioner "shell" {
    script = "scripts/04-setup-first-boot.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S bash '{{.Path}}'"
  }

  # Cleanup and minimize image size
  provisioner "shell" {
    script = "scripts/99-cleanup.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S bash '{{.Path}}'"
  }

  # ==========================================================================
  # Post-Processors
  # ==========================================================================

  post-processor "checksum" {
    checksum_types = ["sha256"]
    output         = "${var.output_directory}/{{.BuildName}}-${var.sting_version}.{{.ChecksumType}}"
  }

  post-processor "manifest" {
    output     = "${var.output_directory}/manifest.json"
    strip_path = true
  }
}
