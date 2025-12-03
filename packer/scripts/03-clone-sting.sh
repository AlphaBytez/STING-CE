#!/bin/bash
# 03-clone-sting.sh - Install STING-CE source from tarball or git clone
set -e

echo "=== STING-CE OVA Build: Install Source ==="

# Variables from Packer
STING_REPO="${STING_REPO:-https://github.com/AlphaBytez/STING-CE.git}"
STING_VERSION="${STING_VERSION:-main}"
STING_USER="${STING_USER:-sting}"
STING_SOURCE_DIR="/opt/sting-ce-source"
SOURCE_TARBALL="/tmp/sting-ce-source.tar.gz"

# Clean up existing directory if it exists (from autoinstall late-commands)
if [ -d "${STING_SOURCE_DIR}" ]; then
    echo "Removing existing directory ${STING_SOURCE_DIR}..."
    rm -rf "${STING_SOURCE_DIR}"
fi

# Create source directory
echo "Creating STING source directory..."
mkdir -p "${STING_SOURCE_DIR}"

# Check if source tarball exists (created by build-ova.sh from local repo)
if [ -f "$SOURCE_TARBALL" ]; then
    echo "Found local source tarball - extracting..."
    echo "  Source: ${SOURCE_TARBALL}"
    echo "  Destination: ${STING_SOURCE_DIR}"

    # Extract tarball (contains STING-CE/ prefix from --transform)
    cd /opt
    tar -xzf "$SOURCE_TARBALL"

    # Rename extracted directory
    if [ -d "/opt/STING-CE" ]; then
        mv /opt/STING-CE/* "${STING_SOURCE_DIR}/" 2>/dev/null || true
        mv /opt/STING-CE/.* "${STING_SOURCE_DIR}/" 2>/dev/null || true
        rmdir /opt/STING-CE 2>/dev/null || true
    fi

    # Clean up tarball
    rm -f "$SOURCE_TARBALL"

    echo "Local source extracted successfully"
else
    # Fallback to git clone
    echo "No local tarball found - cloning from git..."
    echo "  Repository: ${STING_REPO}"
    echo "  Version: ${STING_VERSION}"
    echo "  Destination: ${STING_SOURCE_DIR}"

    git clone "${STING_REPO}" "${STING_SOURCE_DIR}"

    # Checkout specific version if not main
    if [ "${STING_VERSION}" != "main" ] && [ "${STING_VERSION}" != "latest" ]; then
        echo "Checking out version ${STING_VERSION}..."
        cd "${STING_SOURCE_DIR}"
        git checkout "${STING_VERSION}" || git checkout "v${STING_VERSION}" || true
    fi
fi

# Set ownership
echo "Setting ownership to ${STING_USER}..."
chown -R "${STING_USER}:${STING_USER}" "${STING_SOURCE_DIR}"

# Make scripts executable
echo "Making scripts executable..."
chmod +x "${STING_SOURCE_DIR}/install_sting.sh" 2>/dev/null || true
chmod +x "${STING_SOURCE_DIR}/STING/install_sting.sh" 2>/dev/null || true
chmod +x "${STING_SOURCE_DIR}/STING/manage_sting.sh" 2>/dev/null || true

# Create symlink for easy access
echo "Creating symlinks..."
ln -sf "${STING_SOURCE_DIR}/STING/install_sting.sh" /usr/local/bin/sting-install 2>/dev/null || true

# Display version info
echo ""
echo "STING-CE source installed:"
if [ -f "${STING_SOURCE_DIR}/STING/VERSION" ]; then
    cat "${STING_SOURCE_DIR}/STING/VERSION"
elif [ -d "${STING_SOURCE_DIR}/.git" ]; then
    echo "Version from git:"
    cd "${STING_SOURCE_DIR}" && git describe --tags --always 2>/dev/null || echo "unknown"
else
    echo "Local development build (no version info)"
fi

echo ""
echo "=== Source installation complete ==="
