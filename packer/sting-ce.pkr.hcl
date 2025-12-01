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
# Source: QEMU Builder (works without hardware virtualization)
# =============================================================================

source "qemu" "sting-ce" {
  vm_name          = "${var.vm_name}-${var.sting_version}"
  headless         = var.headless

  # ISO configuration
  iso_url          = var.iso_url
  iso_checksum     = var.iso_checksum

  # VM resources
  disk_size        = var.disk_size
  memory           = var.memory
  cpus             = var.cpus

  # Use software emulation (no KVM required) for CI environments
  accelerator      = "none"

  # Disk settings
  format           = "qcow2"
  disk_interface   = "virtio"
  net_device       = "virtio-net"

  # Network - HTTP server for autoinstall
  http_directory   = "http"

  # Boot command for Ubuntu autoinstall
  boot_wait        = "5s"
  boot_command     = [
    "<esc><esc><esc><esc>e<wait>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "<del><del><del><del><del><del><del><del>",
    "linux /casper/vmlinuz --- autoinstall ds=\"nocloud-net;s=http://{{.HTTPIP}}:{{.HTTPPort}}/\"<enter><wait>",
    "initrd /casper/initrd<enter><wait>",
    "boot<enter>"
  ]

  # SSH configuration
  ssh_username     = var.ssh_username
  ssh_password     = var.ssh_password
  ssh_timeout      = "45m"
  ssh_handshake_attempts = 100

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

  # Convert QEMU qcow2 to OVA format
  post-processor "shell-local" {
    inline = [
      "echo 'Converting qcow2 to OVA format...'",
      "cd ${var.output_directory}/qemu",
      "qemu-img convert -f qcow2 -O vmdk ${var.vm_name}-${var.sting_version} ${var.vm_name}-${var.sting_version}.vmdk",
      "echo 'Creating OVF descriptor...'",
      "cat > ${var.vm_name}-${var.sting_version}.ovf << 'OVFEOF'",
      "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
      "<Envelope xmlns=\"http://schemas.dmtf.org/ovf/envelope/1\" xmlns:ovf=\"http://schemas.dmtf.org/ovf/envelope/1\" xmlns:rasd=\"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData\" xmlns:vssd=\"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
      "  <References>",
      "    <File ovf:href=\"${var.vm_name}-${var.sting_version}.vmdk\" ovf:id=\"file1\"/>",
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
      "  <VirtualSystem ovf:id=\"${var.vm_name}\">",
      "    <Info>STING-CE Quick Start VM</Info>",
      "    <Name>${var.vm_name}-${var.sting_version}</Name>",
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
      "        <rasd:AddressOnParent>0</rasd:AddressOnParent>",
      "        <rasd:ElementName>Hard Disk 1</rasd:ElementName>",
      "        <rasd:HostResource>ovf:/disk/vmdisk1</rasd:HostResource>",
      "        <rasd:InstanceID>3</rasd:InstanceID>",
      "        <rasd:ResourceType>17</rasd:ResourceType>",
      "      </Item>",
      "      <Item>",
      "        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>",
      "        <rasd:Connection>NAT</rasd:Connection>",
      "        <rasd:ElementName>Ethernet adapter on NAT</rasd:ElementName>",
      "        <rasd:InstanceID>4</rasd:InstanceID>",
      "        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>",
      "        <rasd:ResourceType>10</rasd:ResourceType>",
      "      </Item>",
      "    </VirtualHardwareSection>",
      "  </VirtualSystem>",
      "</Envelope>",
      "OVFEOF",
      "echo 'Creating OVA archive...'",
      "tar -cvf ${var.vm_name}-${var.sting_version}.ova ${var.vm_name}-${var.sting_version}.ovf ${var.vm_name}-${var.sting_version}.vmdk",
      "echo 'OVA created successfully!'",
      "ls -lh ${var.vm_name}-${var.sting_version}.ova"
    ]
  }

  post-processor "checksum" {
    checksum_types = ["sha256"]
    output         = "${var.output_directory}/{{.BuildName}}-${var.sting_version}.{{.ChecksumType}}"
  }

  post-processor "manifest" {
    output     = "${var.output_directory}/manifest.json"
    strip_path = true
  }
}
