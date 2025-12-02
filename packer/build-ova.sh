#!/bin/bash
# build-ova.sh - End-to-end OVA build script for STING-CE
# Creates a VirtualBox/VMware compatible OVA from scratch
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output/qemu"
VERSION="${VERSION:-1.0.0}"
OVA_NAME="sting-ce-quickstart-${VERSION}"

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
IMAGES_TARBALL="${SCRIPT_DIR}/sting-ce-images.tar.gz"

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

    log "Saving Docker images to tarball..."

    # Get list of images (include installation profile for utils)
    IMAGES=$(docker compose --profile installation config --images 2>/dev/null | sort -u)

    log "Images to save:"
    echo "$IMAGES" | head -10
    [ $(echo "$IMAGES" | wc -l) -gt 10 ] && echo "  ... and more"

    # Save all images (compressed)
    docker save $IMAGES | gzip > "$IMAGES_TARBALL"

    local tarball_size=$(du -h "$IMAGES_TARBALL" | cut -f1)
    log "Images saved to $IMAGES_TARBALL ($tarball_size)"

    cd "$SCRIPT_DIR"
}

# Check prerequisites
check_prerequisites() {
    header "Checking Prerequisites"

    local missing=()

    if ! command -v packer &> /dev/null; then
        missing+=("packer")
    fi

    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    if ! command -v qemu-system-x86_64 &> /dev/null; then
        missing+=("qemu-system-x86_64 (qemu-kvm package)")
    fi

    if ! command -v qemu-img &> /dev/null; then
        missing+=("qemu-img")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing required tools: ${missing[*]}\nInstall with: sudo apt install packer qemu-kvm qemu-utils"
    fi

    # Check KVM availability
    if [ ! -e /dev/kvm ]; then
        warn "/dev/kvm not found - build will be SLOW without hardware acceleration"
        echo "  To enable KVM: sudo modprobe kvm_intel (or kvm_amd)"
        read -p "Continue without KVM? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
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
    packer build -force -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl

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
    # SATA controller hierarchy.

    # Create a Python script to fix the OVF (more reliable than sed for XML)
    python3 << 'PYTHON_SCRIPT'
import xml.etree.ElementTree as ET
import sys

ovf_file = sys.argv[1] if len(sys.argv) > 1 else None
if not ovf_file:
    print("Usage: fix_ovf.py <ovf_file>")
    sys.exit(1)

# Parse OVF
tree = ET.parse(ovf_file)
root = tree.getroot()

# Define namespaces
ns = {
    'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
    'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
    'vssd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData',
    'vbox': 'http://www.virtualbox.org/ovf/machine'
}

# Register namespaces to preserve them in output
for prefix, uri in ns.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace('', ns['ovf'])

# Find VirtualHardwareSection
vhs = root.find('.//ovf:VirtualHardwareSection', ns)
if vhs is None:
    print("ERROR: VirtualHardwareSection not found")
    sys.exit(1)

# Check if SATA controller already exists
sata_exists = False
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    res_subtype = item.find('rasd:ResourceSubType', ns)
    if res_type is not None and res_type.text == '20':  # Storage controller
        if res_subtype is not None and 'AHCI' in res_subtype.text:
            sata_exists = True
            print("SATA controller already exists, skipping...")
            break

if not sata_exists:
    print("Adding SATA controller...")

    # Find the position to insert (after existing controllers, before disk)
    insert_pos = 0
    for i, item in enumerate(vhs.findall('ovf:Item', ns)):
        res_type = item.find('rasd:ResourceType', ns)
        if res_type is not None:
            # Insert after CPU (3), Memory (4), IDE (5) but before disk (17)
            if res_type.text in ['3', '4', '5', '6']:
                insert_pos = i + 1

    # Create SATA Controller item
    sata_item = ET.SubElement(vhs, '{http://schemas.dmtf.org/ovf/envelope/1}Item')

    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Address').text = '0'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Description').text = 'SATA Controller'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ElementName').text = 'SATA Controller'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}InstanceID').text = '3'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ResourceSubType').text = 'AHCI'
    ET.SubElement(sata_item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}ResourceType').text = '20'

# Fix Hard Disk item - add Parent reference and update InstanceID
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    if res_type is not None and res_type.text == '17':  # Hard Disk
        print("Fixing Hard Disk item...")

        # Update InstanceID to 4 (after SATA controller which is 3)
        instance_id = item.find('rasd:InstanceID', ns)
        if instance_id is not None:
            instance_id.text = '4'

        # Add Parent reference to SATA controller (InstanceID 3)
        parent = item.find('rasd:Parent', ns)
        if parent is None:
            parent = ET.SubElement(item, '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}Parent')
        parent.text = '3'

# Fix Network Adapter InstanceID (should be 5 now)
for item in vhs.findall('ovf:Item', ns):
    res_type = item.find('rasd:ResourceType', ns)
    if res_type is not None and res_type.text == '10':  # Network Adapter
        print("Fixing Network Adapter InstanceID...")
        instance_id = item.find('rasd:InstanceID', ns)
        if instance_id is not None and instance_id.text == '3':
            instance_id.text = '5'

# Write fixed OVF
tree.write(ovf_file, xml_declaration=True, encoding='UTF-8')
print(f"OVF fixed successfully: {ovf_file}")
PYTHON_SCRIPT

    # Run the Python fix
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
    echo "  1. Check prerequisites (packer, qemu, kvm, docker)"
    echo "  2. Pre-build Docker images on host (fast network)"
    echo "  3. Build VM using Packer (~15-30 minutes)"
    echo "  4. Fix OVF for VirtualBox compatibility"
    echo "  5. Package as OVA with checksum"
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
                OVA_NAME="sting-ce-quickstart-${VERSION}"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build     Skip Packer build (use existing output)"
                echo "  --skip-prebuild  Skip Docker image pre-build (use existing tarball)"
                echo "  --version VER    Set version string (default: 1.0.0)"
                echo "  --help           Show this help"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    check_prerequisites

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
