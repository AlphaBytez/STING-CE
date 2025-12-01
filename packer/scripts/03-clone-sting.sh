#!/bin/bash
# 03-clone-sting.sh - Clone STING-CE repository
set -e

echo "=== STING-CE OVA Build: Clone Repository ==="

# Variables from Packer
STING_REPO="${STING_REPO:-https://github.com/AlphaBytez/STING-CE-Public.git}"
STING_VERSION="${STING_VERSION:-main}"
STING_USER="${STING_USER:-sting}"
STING_SOURCE_DIR="/opt/sting-ce-source"

# Create source directory
echo "Creating STING source directory..."
mkdir -p "${STING_SOURCE_DIR}"

# Clone repository
echo "Cloning STING-CE repository..."
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
else
    echo "Version file not found, using git info:"
    cd "${STING_SOURCE_DIR}" && git describe --tags --always 2>/dev/null || echo "unknown"
fi

echo ""
echo "=== Repository clone complete ==="
