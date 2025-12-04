#!/bin/bash
# build-ova.sh - End-to-end OVA build script for STING-CE
# Creates a VirtualBox/VMware/UTM compatible OVA from scratch
# Supports both amd64 (x86_64) and arm64 (Apple Silicon) architectures
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output/qemu"
VERSION="${VERSION:-1.0.0}"
ARCH="${ARCH:-amd64}"  # Default to amd64, can be arm64 for Apple Silicon
OVA_NAME="sting-ce-quickstart-${VERSION}-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

STING_DIR="$(dirname "$SCRIPT_DIR")/STING"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
IMAGES_TARBALL="${SCRIPT_DIR}/sting-ce-images.tar.gz"
SOURCE_TARBALL="${SCRIPT_DIR}/sting-ce-source.tar.gz"

# Pre-build Docker images on host (fast network)
prebuild_docker_images() {
    header "Pre-building Docker Images on Host"

    log "This builds images on the host (fast network) to avoid VM timeouts"

    cd "$STING_DIR"

    # Set required environment variables
    export INSTALL_DIR="$STING_DIR"
    export STING_VERSION="latest"
    export HOSTNAME="localhost"

    # Create .env file for docker compose
    cat > .env << EOF
INSTALL_DIR=$INSTALL_DIR
STING_VERSION=$STING_VERSION
HOSTNAME=$HOSTNAME
EOF

    log "Building all Docker images (this may take 20-30 minutes)..."

    # Build all services including utils (installation profile) - continue on failure (some may be pre-built images)
    docker compose --profile installation build --parallel 2>&1 || warn "Some builds failed (may be pre-built images)"

    log "Pulling external images (mailpit, etc.)..."
    # Pull external images that aren't built (mailpit, postgres, redis, etc.)
    # Include dev profile for mailpit (needed for OVA evaluation)
    docker compose --profile installation --profile dev pull --ignore-buildable 2>&1 || warn "Some pulls failed"

    log "Saving Docker images to tarball..."

    # Get list of images (include installation and dev profiles for utils + mailpit)
    IMAGES=$(docker compose --profile installation --profile dev config --images 2>/dev/null | sort -u)

    log "Images to save:"
    echo "$IMAGES" | head -10
    [ $(echo "$IMAGES" | wc -l) -gt 10 ] && echo "  ... and more"

    # Save all images (compressed)
    docker save $IMAGES | gzip > "$IMAGES_TARBALL"

    local tarball_size=$(du -h "$IMAGES_TARBALL" | cut -f1)
    log "Images saved to $IMAGES_TARBALL ($tarball_size)"

    cd "$SCRIPT_DIR"
}

# Create source tarball from local repo (for dev builds)
create_source_tarball() {
    header "Creating Local Source Tarball"

    log "Creating tarball from local repository..."
    log "Source: ${REPO_DIR}"

    cd "$REPO_DIR"

    # Create tarball excluding dev/build artifacts and secrets
    # Exclude .git entirely (saves ~3GB, not needed in OVA)
    # Note: Uses BSD tar syntax for macOS compatibility (-s for transform)
    tar -czf "$SOURCE_TARBALL" \
        --exclude='.git' \
        --exclude='packer/output' \
        --exclude='packer/*.tar.gz' \
        --exclude='packer/*.log' \
        --exclude='STING/frontend/node_modules' \
        --exclude='STING/frontend/dist' \
        --exclude='STING/frontend/build' \
        --exclude='STING/env' \
        --exclude='STING/conf/config.yml' \
        --exclude='*.ova' \
        --exclude='*.vmdk' \
        --exclude='*.qcow2' \
        -s ',^,STING-CE/,' \
        .

    if [ -f "$SOURCE_TARBALL" ]; then
        local tarball_size=$(du -h "$SOURCE_TARBALL" | cut -f1)
        log "Source tarball created: $SOURCE_TARBALL ($tarball_size)"
    else
        error "Failed to create source tarball"
    fi

    cd "$SCRIPT_DIR"
}

# Check prerequisites
check_prerequisites() {
    header "Checking Prerequisites"

    local missing=()
    local os_type=$(uname -s)

    if ! command -v packer &> /dev/null; then
        missing+=("packer")
    fi

    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    if ! command -v qemu-img &> /dev/null; then
        missing+=("qemu-img")
    fi

    # Check for architecture-appropriate QEMU
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v qemu-system-aarch64 &> /dev/null; then
            missing+=("qemu-system-aarch64")
        fi
    else
        if ! command -v qemu-system-x86_64 &> /dev/null; then
            missing+=("qemu-system-x86_64 (qemu-kvm package)")
        fi
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        if [ "$os_type" = "Darwin" ]; then
            error "Missing required tools: ${missing[*]}\nInstall with: brew install packer qemu docker"
        else
            error "Missing required tools: ${missing[*]}\nInstall with: sudo apt install packer qemu-kvm qemu-utils"
        fi
    fi

    # Check hardware acceleration availability
    if [ "$os_type" = "Darwin" ]; then
        # macOS uses HVF (Hypervisor Framework)
        if [ "$ARCH" = "arm64" ]; then
            log "Using HVF (Hypervisor Framework) for ARM64 on macOS"
        else
            warn "Building amd64 on macOS ARM will use emulation (slow)"
        fi
    else
        # Linux uses KVM
        if [ ! -e /dev/kvm ]; then
            warn "/dev/kvm not found - build will be SLOW without hardware acceleration"
            echo "  To enable KVM: sudo modprobe kvm_intel (or kvm_amd)"
            read -p "Continue without KVM? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi

    log "All prerequisites satisfied"
}

# Run Packer build
run_packer_build() {
    header "Building VM with Packer"

    cd "${SCRIPT_DIR}"

    # Check for variables file
    if [ ! -f "variables.pkrvars.hcl" ]; then
        error "variables.pkrvars.hcl not found. Copy from variables.pkrvars.hcl.example and configure."
    fi

    log "Starting Packer build (this takes 15-30 minutes)..."
    log "Output directory: ${OUTPUT_DIR}"

    # Run packer with force to overwrite existing
    # ARM64 UEFI firmware is handled automatically by packer via efi_* options
    log "Building for architecture: ${ARCH}"
    packer build -force -var-file=variables.pkrvars.hcl -var "arch=${ARCH}" sting-ce.pkr.hcl

    log "Packer build complete"
}

# Fix OVF for VirtualBox compatibility
fix_ovf_for_virtualbox() {
    header "Fixing OVF for VirtualBox Compatibility"

    local ovf_file="${OUTPUT_DIR}/${OVA_NAME}.ovf"

    if [ ! -f "$ovf_file" ]; then
        error "OVF file not found: $ovf_file"
    fi

    log "Backing up original OVF..."
    cp "$ovf_file" "${ovf_file}.backup"

    log "Applying VirtualBox compatibility fixes..."

    # The issue: Packer's QEMU post-processor creates an OVF where the disk item
    # references a parent that doesn't exist. VirtualBox requires a proper
    # SATA controller hierarchy. We also add VirtualBox-specific settings
    # to enable Host I/O Cache for better disk performance.

    # Run Python script to fix the OVF
    python3 -c "
import xml.etree.ElementTree as ET
import sys

ovf_file = '${ovf_file}'

# Parse OVF
tree = ET.parse(ovf_file)
root = tree.getroot()

# Define namespaces
ns = {
    'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
    'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
    'vssd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData',
}

# Register namespaces
for prefix, uri in ns.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace('', ns['ovf'])

# Find VirtualHardwareSection
vhs = root.find('.//ovf:VirtualHardwareSection', ns)
if vhs is None:
    print('ERROR: VirtualHardwareSection not found')
    sys.exit(1)

# Check if SATA controller already exists
sata_exists = False
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    res_subtype = item.find('rasd:ResourceSubType', ns)
    if res_type is not None and res_type.text == '20':
        if res_subtype is not None and 'AHCI' in res_subtype.text:
            sata_exists = True
            print('SATA controller already exists')
            break

if not sata_exists:
    print('Adding SATA controller...')
    sata_item = ET.Element('{http://schemas.dmtf.org/ovf/envelope/1}Item')
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Address').text = '0'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Description').text = 'SATA Controller'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ElementName').text = 'SATA Controller'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}InstanceID').text = '3'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ResourceSubType').text = 'AHCI'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ResourceType').text = '20'

    # Insert after system items
    items = list(vhs)
    insert_idx = 0
    for i, item in enumerate(items):
        if item.tag.endswith('Item'):
            insert_idx = i + 1
            res_type = item.find('rasd:ResourceType', ns)
            if res_type is not None and res_type.text == '17':
                insert_idx = i
                break
    vhs.insert(insert_idx, sata_item)

# Fix Hard Disk - add Parent and update InstanceID
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    if res_type is not None and res_type.text == '17':
        print('Fixing Hard Disk item...')
        instance_id = item.find('rasd:InstanceID', ns)
        if instance_id is not None:
            instance_id.text = '4'
        parent = item.find('rasd:Parent', ns)
        if parent is None:
            parent = ET.SubElement(item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Parent')
        parent.text = '3'

# Fix Network Adapter InstanceID
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    if res_type is not None and res_type.text == '10':
        instance_id = item.find('rasd:InstanceID', ns)
        if instance_id is not None and instance_id.text in ['3', '4']:
            print('Fixing Network Adapter InstanceID...')
            instance_id.text = '5'

# Note: VirtualBox-specific extensions (vbox:Machine) were removed as they
# cause import errors. Users must manually enable Host I/O Cache in VirtualBox:
# Settings → Storage → SATA Controller → Use Host I/O Cache
# This is documented in the VirtualBox OVA guide.

tree.write(ovf_file, xml_declaration=True, encoding='UTF-8')
print('OVF fixed successfully')
"

    log "OVF fix complete"
}

# Create OVA package
create_ova_package() {
    header "Creating OVA Package"

    cd "${OUTPUT_DIR}"

    local ovf_file="${OVA_NAME}.ovf"
    local vmdk_file="${OVA_NAME}.vmdk"
    local ova_file="${OVA_NAME}.ova"

    # Verify required files exist
    if [ ! -f "$ovf_file" ]; then
        error "OVF file not found: $ovf_file"
    fi

    if [ ! -f "$vmdk_file" ]; then
        error "VMDK file not found: $vmdk_file"
    fi

    # Remove existing OVA
    if [ -f "$ova_file" ]; then
        log "Removing existing OVA..."
        rm -f "$ova_file"
    fi

    # Create OVA (tar archive with specific file order)
    # OVF must be first in the archive
    log "Creating OVA archive..."
    tar -cvf "$ova_file" "$ovf_file" "$vmdk_file"

    # Generate SHA256 checksum
    log "Generating SHA256 checksum..."
    sha256sum "$ova_file" > "${ova_file}.sha256"

    local ova_size=$(du -h "$ova_file" | cut -f1)

    log "OVA created successfully!"
    echo ""
    echo -e "${GREEN}  File: ${OUTPUT_DIR}/${ova_file}${NC}"
    echo -e "${GREEN}  Size: ${ova_size}${NC}"
    echo -e "${GREEN}  SHA256: $(cat ${ova_file}.sha256 | cut -d' ' -f1)${NC}"
}

# Cleanup old builds
cleanup_old_builds() {
    header "Cleaning Up"

    cd "${OUTPUT_DIR}" 2>/dev/null || return

    # Remove backup files
    rm -f *.backup 2>/dev/null || true

    log "Cleanup complete"
}

# Print final summary
print_summary() {
    header "Build Complete!"

    local ova_file="${OUTPUT_DIR}/${OVA_NAME}.ova"
    local ova_size=$(du -h "$ova_file" 2>/dev/null | cut -f1 || echo "N/A")

    echo "OVA file ready for distribution:"
    echo ""
    echo -e "  ${GREEN}Location:${NC} ${ova_file}"
    echo -e "  ${GREEN}Size:${NC}     ${ova_size}"
    echo ""
    echo "Next steps:"
    echo "  1. Test the OVA by importing into VirtualBox/VMware"
    echo "  2. Upload to Backblaze B2 for distribution"
    echo "  3. Configure Cloudflare CDN (optional)"
    echo ""
    echo "To upload to Backblaze B2:"
    echo "  b2 upload-file <bucket-name> ${ova_file} ${OVA_NAME}.ova"
    echo ""
}

# Main execution
main() {
    header "STING-CE OVA Builder v${VERSION}"

    echo "This script will:"
    echo "  1. Check prerequisites (packer, qemu, kvm/hvf, docker)"
    echo "  2. Create source tarball from local repo (includes uncommitted changes)"
    echo "  3. Pre-build Docker images on host (fast network)"
    echo "  4. Build VM using Packer (~15-30 minutes)"
    echo "  5. Fix OVF for VirtualBox/UTM compatibility"
    echo "  6. Package as OVA with checksum"
    echo ""

    # Parse arguments
    SKIP_BUILD=false
    SKIP_PREBUILD=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-prebuild)
                SKIP_PREBUILD=true
                shift
                ;;
            --version)
                shift
                VERSION="$1"
                OVA_NAME="sting-ce-quickstart-${VERSION}-${ARCH}"
                shift
                ;;
            --arch)
                shift
                ARCH="$1"
                if [[ "$ARCH" != "amd64" && "$ARCH" != "arm64" ]]; then
                    error "Invalid architecture: $ARCH (must be amd64 or arm64)"
                fi
                OVA_NAME="sting-ce-quickstart-${VERSION}-${ARCH}"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --arch ARCH      Target architecture: amd64 (default) or arm64"
                echo "  --skip-build     Skip Packer build (use existing output)"
                echo "  --skip-prebuild  Skip Docker image pre-build (use existing tarball)"
                echo "  --version VER    Set version string (default: 1.0.0)"
                echo "  --help           Show this help"
                echo ""
                echo "Examples:"
                echo "  $0                          # Build amd64 OVA (default)"
                echo "  $0 --arch arm64             # Build arm64 OVA for Apple Silicon"
                echo "  $0 --arch arm64 --version 1.1.0  # ARM64 with custom version"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Display build configuration
    log "Target architecture: ${ARCH}"
    log "Output: ${OVA_NAME}.ova"
    echo ""

    check_prerequisites

    # Always create fresh source tarball from local repo
    create_source_tarball

    # Pre-build Docker images on host (unless skipped or tarball exists)
    if [ "$SKIP_PREBUILD" = false ]; then
        if [ -f "$IMAGES_TARBALL" ]; then
            local existing_size
            existing_size=$(du -h "$IMAGES_TARBALL" | cut -f1)
            log "Using existing images tarball: $IMAGES_TARBALL ($existing_size)"
            log "Use --skip-prebuild=false to force rebuild"
        else
            prebuild_docker_images
        fi
    else
        log "Skipping Docker pre-build (--skip-prebuild specified)"
    fi

    if [ "$SKIP_BUILD" = false ]; then
        run_packer_build
    else
        log "Skipping Packer build (--skip-build specified)"
    fi

    fix_ovf_for_virtualbox
    create_ova_package
    cleanup_old_builds
    print_summary
}

# Run main
main "$@"
