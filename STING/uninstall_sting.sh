#!/bin/bash
#
# STING-CE Quick Uninstaller
# One-line uninstall: curl -fsSL https://raw.githubusercontent.com/sting-ce/sting-ce/main/STING/uninstall_sting.sh | bash
#
# Options:
#   --purge       Remove all data, volumes, and backups
#   --yes         Skip confirmation prompts
#   --llm         Also remove downloaded LLM models

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
PURGE_FLAG=""
YES_FLAG=""
LLM_FLAG=""

for arg in "$@"; do
    case "$arg" in
        --purge) PURGE_FLAG="--purge" ;;
        --yes) YES_FLAG="--yes" ;;
        --llm) LLM_FLAG="--llm" ;;
    esac
done

# Default installation directory
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           STING-CE Quick Uninstaller                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if STING is installed
if [ ! -d "$INSTALL_DIR" ] && ! command -v msting &>/dev/null; then
    echo -e "${YELLOW}⚠️  STING-CE doesn't appear to be installed${NC}"
    echo ""
    echo "Checked:"
    echo "  - Installation directory: $INSTALL_DIR"
    echo "  - msting command in PATH"
    echo ""
    read -p "Continue with Docker cleanup anyway? [y/N]: " continue_cleanup
    case "$continue_cleanup" in
        [Yy]*) echo "Proceeding with cleanup..." ;;
        *) echo "Uninstall cancelled."; exit 0 ;;
    esac
fi

# Show what will be removed
echo -e "${YELLOW}This will remove:${NC}"
echo "  ✗ All STING-CE Docker containers and images"
echo "  ✗ Installation directory: $INSTALL_DIR"
echo "  ✗ System msting command"

if [ -n "$PURGE_FLAG" ]; then
    echo "  ✗ All Docker volumes (database, vault data, etc.)"
    echo "  ✗ All backups"
fi

if [ -n "$LLM_FLAG" ]; then
    echo "  ✗ Downloaded LLM models"
fi

echo ""
echo -e "${GREEN}This will preserve:${NC}"
[ -z "$PURGE_FLAG" ] && echo "  ✓ Backups in ${INSTALL_DIR}/backups (if they exist)"
[ -z "$LLM_FLAG" ] && echo "  ✓ Downloaded LLM models (use --llm to remove)"
echo ""

# Confirmation (unless --yes flag)
if [ -z "$YES_FLAG" ]; then
    echo -e "${RED}⚠️  This action cannot be undone!${NC}"
    echo ""

    # Retry loop for confirmation (up to 3 attempts)
    attempts=0
    max_attempts=3
    confirmed=false

    while [ $attempts -lt $max_attempts ] && [ "$confirmed" = "false" ]; do
        read -p "Are you sure you want to uninstall STING-CE? (yes/no): " confirm

        # Normalize input: trim whitespace, lowercase, remove extra characters
        confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z]//g')

        case "$confirm" in
            yes|y)
                echo "Proceeding with uninstall..."
                confirmed=true
                ;;
            no|n)
                echo "Uninstall cancelled."
                exit 0
                ;;
            *)
                attempts=$((attempts + 1))
                if [ $attempts -lt $max_attempts ]; then
                    echo "❌ Invalid input. Please type 'yes' or 'no' (attempt $attempts/$max_attempts)"
                    echo ""
                else
                    echo "❌ Too many invalid attempts. Uninstall cancelled."
                    exit 0
                fi
                ;;
        esac
    done
fi

echo ""
echo "Starting uninstall process..."
echo ""

# Check if manage_sting.sh exists and use it for proper uninstall
if [ -f "$INSTALL_DIR/manage_sting.sh" ]; then
    echo "Using STING's built-in uninstaller..."
    cd "$INSTALL_DIR" || exit 1

    # Build uninstall command
    UNINSTALL_CMD="./manage_sting.sh uninstall"
    [ -n "$PURGE_FLAG" ] && UNINSTALL_CMD="$UNINSTALL_CMD --purge"
    [ -n "$LLM_FLAG" ] && UNINSTALL_CMD="$UNINSTALL_CMD --llm"
    UNINSTALL_CMD="$UNINSTALL_CMD --force"  # Skip confirmation since we already asked

    if $UNINSTALL_CMD; then
        echo ""
        echo -e "${GREEN}✅ STING-CE uninstalled successfully${NC}"
    else
        echo ""
        echo -e "${RED}❌ Uninstall encountered errors${NC}"
        exit 1
    fi
else
    # Fallback: Manual cleanup if manage_sting.sh doesn't exist
    echo "⚠️  STING installation incomplete or corrupted"
    echo "Performing manual cleanup..."
    echo ""

    # Stop and remove all STING containers
    echo "Stopping STING containers..."
    docker ps -a --format "{{.Names}}" 2>/dev/null | grep -iE "sting" | xargs -r docker stop 2>/dev/null || true
    docker ps -a --format "{{.Names}}" 2>/dev/null | grep -iE "sting" | xargs -r docker rm -f 2>/dev/null || true

    # Remove STING images
    echo "Removing STING images..."
    docker images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -iE "sting" | xargs -r docker rmi -f 2>/dev/null || true

    # Remove volumes if --purge
    if [ -n "$PURGE_FLAG" ]; then
        echo "Removing STING volumes..."
        docker volume ls --format "{{.Name}}" 2>/dev/null | grep -iE "sting" | xargs -r docker volume rm -f 2>/dev/null || true
    fi

    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        echo "Removing installation directory..."

        # Preserve backups unless --purge
        if [ -z "$PURGE_FLAG" ] && [ -d "$INSTALL_DIR/backups" ]; then
            BACKUP_TEMP="/tmp/sting_backups_$(date +%s)"
            mv "$INSTALL_DIR/backups" "$BACKUP_TEMP" 2>/dev/null || true
            echo "  ✓ Backups preserved at: $BACKUP_TEMP"
        fi

        sudo rm -rf "$INSTALL_DIR" 2>/dev/null || rm -rf "$INSTALL_DIR" 2>/dev/null || true
    fi

    # Remove msting command
    if [ -L /usr/local/bin/msting ]; then
        echo "Removing msting command..."
        sudo rm -f /usr/local/bin/msting 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}✅ Manual cleanup completed${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Uninstall Complete                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "STING-CE has been removed from your system."
echo ""

if [ -z "$PURGE_FLAG" ]; then
    echo "Note: Docker volumes were preserved. To remove all data, run:"
    echo "  docker volume ls | grep sting | awk '{print \$2}' | xargs docker volume rm"
    echo ""
fi

echo "To reinstall STING-CE, run:"
echo "  curl -fsSL https://raw.githubusercontent.com/sting-ce/sting-ce/main/STING/install_sting.sh | bash"
echo ""
