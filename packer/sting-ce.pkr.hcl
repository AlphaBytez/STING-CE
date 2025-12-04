# STING-CE Packer Template
# Builds a "Quick Start" OVA with Ubuntu 24.04, Docker, and STING pre-staged
#
# Usage:
#   packer init sting-ce.pkr.hcl
#   packer build -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl
#
# Outputs:
#   - QEMU qcow2 image (converted to OVA for VMware/VirtualBox import)
#   - AWS AMI (optional, if AWS credentials configured)

packer {
  required_plugins {
    qemu = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/qemu"
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

variable "arch" {
  type        = string
  description = "Target architecture: amd64 or arm64"
  default     = "amd64"
  validation {
    condition     = contains(["amd64", "arm64"], var.arch)
    error_message = "Architecture must be 'amd64' or 'arm64'."
  }
}

variable "iso_url" {
  type        = string
  description = "Ubuntu Server ISO URL (auto-set based on arch if not specified)"
  default     = ""  # Will be computed in locals
}

variable "iso_checksum" {
  type        = string
  description = "Ubuntu ISO SHA256 checksum (auto-set based on arch if not specified)"
  default     = ""  # Will be computed in locals
}

variable "vm_name" {
  type        = string
  description = "VM name"
  default     = "sting-ce-quickstart"
}

variable "disk_size" {
  type        = string
  description = "Disk size (e.g., 40G)"
  default     = "40G"
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
  default     = "https://github.com/AlphaBytez/STING-CE.git"
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
  vm_description  = "STING-CE Quick Start v${var.sting_version} (${var.arch}) - Pre-configured Ubuntu with Docker and STING installer ready. Boot and access the web installer at https://<VM_IP>:5000"

  # Architecture-specific ISO URLs and checksums (Ubuntu 24.04.3 LTS)
  iso_urls = {
    amd64 = "https://releases.ubuntu.com/24.04/ubuntu-24.04.3-live-server-amd64.iso"
    arm64 = "https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04.3-live-server-arm64.iso"
  }

  iso_checksums = {
    amd64 = "sha256:c3514bf0056180d09376462a7a1b4f213c1d6e8ea67fae5c25099c6fd3d8274b"
    arm64 = "sha256:2ee2163c9b901ff5926400e80759088ff3b879982a3956c02100495b489fd555"
  }

  # Use provided values or auto-detect from arch
  effective_iso_url      = var.iso_url != "" ? var.iso_url : local.iso_urls[var.arch]
  effective_iso_checksum = var.iso_checksum != "" ? var.iso_checksum : local.iso_checksums[var.arch]

  # Architecture-specific QEMU settings
  qemu_binary = var.arch == "arm64" ? "qemu-system-aarch64" : "qemu-system-x86_64"
  qemu_machine = var.arch == "arm64" ? "virt,highmem=on" : "q35"
  qemu_accelerator = var.arch == "arm64" ? "hvf" : "kvm"  # hvf for macOS ARM, kvm for Linux x86

  # ARM64 requires UEFI firmware (homebrew location on macOS)
  efi_firmware = "/opt/homebrew/share/qemu/edk2-aarch64-code.fd"

  # Output filename includes architecture
  output_name = "${var.vm_name}-${var.sting_version}-${var.arch}"
}

# =============================================================================
# Source: QEMU Builder (works without hardware virtualization)
# =============================================================================

source "qemu" "sting-ce" {
  vm_name          = local.output_name
  headless         = var.headless

  # ISO configuration (auto-detected based on arch)
  iso_url          = local.effective_iso_url
  iso_checksum     = local.effective_iso_checksum

  # VM resources
  disk_size        = var.disk_size
  memory           = var.memory
  cpus             = var.cpus

  # Architecture-specific QEMU settings
  qemu_binary      = local.qemu_binary
  machine_type     = local.qemu_machine
  accelerator      = local.qemu_accelerator

  # ARM64-specific: UEFI firmware and CPU settings
  # Only apply these for ARM64 builds on macOS
  qemuargs = var.arch == "arm64" ? [
    ["-cpu", "host"],
    ["-bios", local.efi_firmware],
    ["-device", "virtio-gpu-pci"],
    ["-device", "usb-ehci"],
    ["-device", "usb-kbd"],
    ["-device", "usb-mouse"]
  ] : []

  # Disk settings
  format           = "qcow2"
  disk_interface   = "virtio"
  net_device       = "virtio-net"

  # Network - HTTP server for autoinstall
  http_directory   = "http"

  # SSH port forwarding (QEMU user-mode networking)
  host_port_min    = 2222
  host_port_max    = 2229

  # Boot command for Ubuntu 24.04 autoinstall (GRUB menu)
  boot_wait        = "10s"
  boot_command     = [
    "e<wait3>",
    "<down><down><down><end>",
    " autoinstall ds=nocloud-net\\;s=http://{{.HTTPIP}}:{{.HTTPPort}}/",
    "<f10>"
  ]

  # SSH configuration
  ssh_username     = var.ssh_username
  ssh_password     = var.ssh_password
  ssh_timeout      = "60m"
  ssh_handshake_attempts = 200
  ssh_wait_timeout = "60m"

  # Shutdown
  shutdown_command = "echo '${var.ssh_password}' | sudo -S shutdown -P now"

  # Output
  output_directory = "${var.output_directory}/qemu"
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
    "source.qemu.sting-ce",
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

  # Copy Docker veth fix files (VirtualBox workaround)
  provisioner "file" {
    source      = "files/docker-veth-fix.sh"
    destination = "/tmp/docker-veth-fix.sh"
  }

  provisioner "file" {
    source      = "files/docker-veth-fix.service"
    destination = "/tmp/docker-veth-fix.service"
  }

  provisioner "file" {
    source      = "files/docker-veth-fix.timer"
    destination = "/tmp/docker-veth-fix.timer"
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

  # Copy local source tarball (created by build-ova.sh from local repo)
  # This allows testing with uncommitted changes without pushing to GitHub
  provisioner "file" {
    source      = "sting-ce-source.tar.gz"
    destination = "/tmp/sting-ce-source.tar.gz"
    generated   = true  # Skip if file doesn't exist (fallback to git clone)
  }

  # Install STING source (extracts from tarball or clones from git as fallback)
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

  # Copy pre-built Docker images tarball (if it exists)
  # This is created by build-ova.sh on the host for faster VM builds
  provisioner "file" {
    source      = "sting-ce-images.tar.gz"
    destination = "/tmp/sting-ce-images.tar.gz"
    generated   = true  # Skip if file doesn't exist
  }

  # Load pre-built Docker images (significantly reduces first-boot install time)
  # Uses pre-built images from tarball instead of building in VM (avoids slow network)
  provisioner "shell" {
    script = "scripts/05-prebuild-containers.sh"
    execute_command = "echo '${var.ssh_password}' | sudo -S bash '{{.Path}}'"
    timeout = "90m"
  }

  # Pre-build wizard Python venv (avoids pip install on first boot)
  # This ensures the wizard can start immediately without network access
  provisioner "shell" {
    script = "scripts/06-prebuild-wizard.sh"
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

  # Convert QEMU qcow2 to OVA format
  post-processor "shell-local" {
    inline = [
      "echo 'Converting qcow2 to OVA format...'",
      "echo 'Architecture: ${var.arch}'",
      "cd ${var.output_directory}/qemu",
      "qemu-img convert -f qcow2 -O vmdk ${var.vm_name}-${var.sting_version}-${var.arch} ${var.vm_name}-${var.sting_version}-${var.arch}.vmdk",
      "echo 'Creating OVF descriptor...'",
      "cat > ${var.vm_name}-${var.sting_version}-${var.arch}.ovf << 'OVFEOF'",
      "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
      "<Envelope xmlns=\"http://schemas.dmtf.org/ovf/envelope/1\" xmlns:ovf=\"http://schemas.dmtf.org/ovf/envelope/1\" xmlns:rasd=\"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData\" xmlns:vssd=\"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
      "  <References>",
      "    <File ovf:href=\"${var.vm_name}-${var.sting_version}-${var.arch}.vmdk\" ovf:id=\"file1\"/>",
      "  </References>",
      "  <DiskSection>",
      "    <Info>Virtual disk information</Info>",
      "    <Disk ovf:capacity=\"42949672960\" ovf:diskId=\"vmdisk1\" ovf:fileRef=\"file1\" ovf:format=\"http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized\"/>",
      "  </DiskSection>",
      "  <NetworkSection>",
      "    <Info>The list of logical networks</Info>",
      "    <Network ovf:name=\"NAT\">",
      "      <Description>NAT network</Description>",
      "    </Network>",
      "  </NetworkSection>",
      "  <VirtualSystem ovf:id=\"${var.vm_name}-${var.arch}\">",
      "    <Info>STING-CE Quick Start VM (${var.arch})</Info>",
      "    <Name>${var.vm_name}-${var.sting_version}-${var.arch}</Name>",
      "    <OperatingSystemSection ovf:id=\"96\">",
      "      <Info>Ubuntu 64-bit</Info>",
      "    </OperatingSystemSection>",
      "    <VirtualHardwareSection>",
      "      <Info>Virtual hardware requirements</Info>",
      "      <System>",
      "        <vssd:ElementName>Virtual Hardware Family</vssd:ElementName>",
      "        <vssd:InstanceID>0</vssd:InstanceID>",
      "        <vssd:VirtualSystemType>vmx-14</vssd:VirtualSystemType>",
      "      </System>",
      "      <Item>",
      "        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>",
      "        <rasd:Description>Number of Virtual CPUs</rasd:Description>",
      "        <rasd:ElementName>4 virtual CPU(s)</rasd:ElementName>",
      "        <rasd:InstanceID>1</rasd:InstanceID>",
      "        <rasd:ResourceType>3</rasd:ResourceType>",
      "        <rasd:VirtualQuantity>4</rasd:VirtualQuantity>",
      "      </Item>",
      "      <Item>",
      "        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>",
      "        <rasd:Description>Memory Size</rasd:Description>",
      "        <rasd:ElementName>8192MB of memory</rasd:ElementName>",
      "        <rasd:InstanceID>2</rasd:InstanceID>",
      "        <rasd:ResourceType>4</rasd:ResourceType>",
      "        <rasd:VirtualQuantity>8192</rasd:VirtualQuantity>",
      "      </Item>",
      "      <Item>",
      "        <rasd:Address>0</rasd:Address>",
      "        <rasd:Description>SATA Controller</rasd:Description>",
      "        <rasd:ElementName>SATA Controller</rasd:ElementName>",
      "        <rasd:InstanceID>3</rasd:InstanceID>",
      "        <rasd:ResourceSubType>AHCI</rasd:ResourceSubType>",
      "        <rasd:ResourceType>20</rasd:ResourceType>",
      "      </Item>",
      "      <Item>",
      "        <rasd:AddressOnParent>0</rasd:AddressOnParent>",
      "        <rasd:ElementName>Hard Disk 1</rasd:ElementName>",
      "        <rasd:HostResource>ovf:/disk/vmdisk1</rasd:HostResource>",
      "        <rasd:InstanceID>4</rasd:InstanceID>",
      "        <rasd:Parent>3</rasd:Parent>",
      "        <rasd:ResourceType>17</rasd:ResourceType>",
      "      </Item>",
      "      <Item>",
      "        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>",
      "        <rasd:Connection>NAT</rasd:Connection>",
      "        <rasd:ElementName>Ethernet adapter on NAT</rasd:ElementName>",
      "        <rasd:InstanceID>5</rasd:InstanceID>",
      "        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>",
      "        <rasd:ResourceType>10</rasd:ResourceType>",
      "      </Item>",
      "    </VirtualHardwareSection>",
      "  </VirtualSystem>",
      "</Envelope>",
      "OVFEOF",
      "echo 'Creating OVA archive...'",
      "tar -cvf ${var.vm_name}-${var.sting_version}-${var.arch}.ova ${var.vm_name}-${var.sting_version}-${var.arch}.ovf ${var.vm_name}-${var.sting_version}-${var.arch}.vmdk",
      "echo 'OVA created successfully!'",
      "ls -lh ${var.vm_name}-${var.sting_version}-${var.arch}.ova"
    ]
  }

  post-processor "checksum" {
    checksum_types = ["sha256"]
    output         = "${var.output_directory}/{{.BuildName}}-${var.sting_version}-${var.arch}.{{.ChecksumType}}"
  }

  post-processor "manifest" {
    output     = "${var.output_directory}/manifest.json"
    strip_path = true
  }
}
