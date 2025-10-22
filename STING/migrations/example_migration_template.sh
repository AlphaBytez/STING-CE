#!/bin/bash
# Migration Template
# Copy this file and rename to: v{from}_to_v{to}.sh
# Example: v1.0.0_to_v1.1.0.sh

set -e  # Exit on error

# Configuration
MIGRATION_NAME="v1.0.0_to_v1.1.0"  # UPDATE THIS
FROM_VERSION="1.0.0"                # UPDATE THIS
TO_VERSION="1.1.0"                  # UPDATE THIS
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Main migration function
run_migration() {
    echo "========================================"
    echo "Migration: ${MIGRATION_NAME}"
    echo "From: v${FROM_VERSION}"
    echo "To:   v${TO_VERSION}"
    echo "========================================"
    echo ""

    # Step 1: Prerequisites check
    log_info "Checking prerequisites..."

    # Check if STING is installed
    if [ ! -d "${INSTALL_DIR}" ]; then
        log_error "STING installation directory not found: ${INSTALL_DIR}"
        exit 1
    fi

    # Check current version
    if [ -f "${INSTALL_DIR}/VERSION" ]; then
        current_version=$(cat "${INSTALL_DIR}/VERSION")
        log_info "Current version: v${current_version}"

        # Optionally enforce version check
        # if [ "$current_version" != "$FROM_VERSION" ]; then
        #     log_error "This migration requires version ${FROM_VERSION}, but found ${current_version}"
        #     exit 1
        # fi
    else
        log_warn "VERSION file not found, skipping version check"
    fi

    # Step 2: Backup
    log_info "Creating migration backup..."
    mkdir -p "${INSTALL_DIR}/backups/migrations"
    backup_file="${INSTALL_DIR}/backups/migrations/${MIGRATION_NAME}-$(date +%Y%m%d-%H%M%S).tar.gz"

    tar -czf "$backup_file" \
        -C "${INSTALL_DIR}" \
        conf/ \
        env/ \
        VERSION \
        2>/dev/null || log_warn "Warning: Some files could not be backed up"

    if [ -f "$backup_file" ]; then
        log_info "Backup created: $backup_file"
    else
        log_error "Backup failed"
        exit 1
    fi

    # Step 3: Perform migration tasks
    echo ""
    log_info "Performing migration tasks..."

    # --------------------------------------------------
    # ADD YOUR MIGRATION TASKS HERE
    # --------------------------------------------------

    # Example: Update configuration file
    # if [ -f "${INSTALL_DIR}/conf/config.yml" ]; then
    #     if ! grep -q "new_setting" "${INSTALL_DIR}/conf/config.yml"; then
    #         echo "  new_setting: true" >> "${INSTALL_DIR}/conf/config.yml"
    #         log_info "Updated config.yml with new_setting"
    #     fi
    # fi

    # Example: Run database migration
    # log_info "Running database migrations..."
    # docker exec sting-ce-app flask db upgrade || {
    #     log_error "Database migration failed"
    #     exit 1
    # }

    # Example: Update environment files
    # if [ -f "${INSTALL_DIR}/env/app.env" ]; then
    #     if ! grep -q "NEW_FEATURE_ENABLED" "${INSTALL_DIR}/env/app.env"; then
    #         echo "NEW_FEATURE_ENABLED=true" >> "${INSTALL_DIR}/env/app.env"
    #         log_info "Added NEW_FEATURE_ENABLED to app.env"
    #     fi
    # fi

    # Example: Clean up old files
    # if [ -f "${INSTALL_DIR}/old_deprecated_file.txt" ]; then
    #     rm -f "${INSTALL_DIR}/old_deprecated_file.txt"
    #     log_info "Removed deprecated file"
    # fi

    # --------------------------------------------------
    # END MIGRATION TASKS
    # --------------------------------------------------

    # Step 4: Validation
    echo ""
    log_info "Validating migration..."

    # Check if services are running
    if docker ps | grep -q "sting-ce-app"; then
        log_info "Core services are running"
    else
        log_warn "Core services not running - this may be expected"
    fi

    # Health check (if services are running)
    if curl -f -s -o /dev/null -k https://localhost:5050/api/health 2>/dev/null; then
        log_info "Health check passed"
    else
        log_warn "Health check failed or services not ready"
    fi

    # Step 5: Complete
    echo ""
    echo "========================================"
    log_info "Migration ${MIGRATION_NAME} completed successfully!"
    echo "========================================"
    echo ""
    echo "Rollback instructions (if needed):"
    echo "1. Restore from backup: tar -xzf $backup_file -C ${INSTALL_DIR}"
    echo "2. Restart services: cd ${INSTALL_DIR} && docker compose restart"
    echo ""

    return 0
}

# Error handler
handle_error() {
    log_error "Migration failed at line $1"
    log_error "Check logs and backup at: ${INSTALL_DIR}/backups/migrations/"
    exit 1
}

# Set error trap
trap 'handle_error $LINENO' ERR

# Run migration
run_migration

exit 0
