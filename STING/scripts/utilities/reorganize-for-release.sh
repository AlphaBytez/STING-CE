#!/bin/bash
# STING-CE Public Release Reorganization Script
# Moves files to archives according to PUBLIC_RELEASE_CLEANUP_PLAN.md

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🐝 STING-CE Public Release Reorganization"
echo "========================================"

# Create archive directories
ARCHIVE_BASE="../archives"
mkdir -p "$ARCHIVE_BASE"/{development,legacy,test,troubleshooting,logs,temp}

# Function to safely move files
move_to_archive() {
    local file=$1
    local category=$2
    local target_dir="$ARCHIVE_BASE/$category"
    
    if [ -e "$file" ]; then
        echo -e "${YELLOW}Moving${NC} $file → $target_dir/"
        mv "$file" "$target_dir/" 2>/dev/null || echo -e "${RED}Failed to move${NC} $file"
    fi
}

echo -e "\n${BLUE}1. Moving development and debug files...${NC}"
# Development files
for pattern in "*.log" "*.bak" "*.bak.*" "*output.txt" "debug.log" "bee.log" "bee_simple.log" "llm_native.log"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "logs"
    done
done

echo -e "\n${BLUE}2. Moving legacy management scripts...${NC}"
# Legacy scripts
for script in manage_sting_legacy.sh manage_sting_minimal.sh manage_sting_modular.sh manage_sting_new.sh manage_sting_simple.sh; do
    move_to_archive "$script" "legacy"
done

# Legacy refactor files
for pattern in "manage_sting_refactor_*.md" "refactor_*.json" "refactor_*.md" "LEGACY_REFACTOR_MAPPING.md"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "legacy"
    done
done

echo -e "\n${BLUE}3. Moving test scripts...${NC}"
# Test scripts
for pattern in "test-*.sh" "test_*.py" "test_*.json" "check-*.sh" "fix_*.sh" "fix_*.py"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "test"
    done
done

echo -e "\n${BLUE}4. Moving development utilities...${NC}"
# Development utilities
for file in code_dump.sh tree-data.txt function_mapping.csv main_function_content.txt; do
    move_to_archive "$file" "development"
done

# Function inventory files
for pattern in "*_function_inventory.md"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "development"
    done
done

echo -e "\n${BLUE}5. Moving troubleshooting directory...${NC}"
# Move entire troubleshooting directory
if [ -d "troubleshooting" ]; then
    echo -e "${YELLOW}Moving${NC} troubleshooting/ → $ARCHIVE_BASE/troubleshooting/"
    mv troubleshooting "$ARCHIVE_BASE/" 2>/dev/null || echo -e "${RED}Failed to move${NC} troubleshooting/"
fi

echo -e "\n${BLUE}6. Moving environment and build files...${NC}"
# Environment files (keeping .env.example if it exists)
for file in .env .env.bak .env.build .env.performance .pgpass realm-export.json; do
    move_to_archive "$file" "temp"
done

echo -e "\n${BLUE}7. Moving patch files...${NC}"
# Patch files
for pattern in "*.patch"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "development"
    done
done

echo -e "\n${BLUE}8. Moving old versions and backups...${NC}"
# Directories
for dir in old_versions backups logs; do
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}Moving${NC} $dir/ → $ARCHIVE_BASE/temp/"
        mv "$dir" "$ARCHIVE_BASE/temp/" 2>/dev/null || echo -e "${RED}Failed to move${NC} $dir/"
    fi
done

echo -e "\n${BLUE}9. Moving additional scripts to archives...${NC}"
# Scripts that should be in honey jars
for script in check_llm_health.sh check_admin.py check-installation-status.sh \
              download_optimized_models.sh download_small_models.sh setup-model-symlinks.sh \
              sting-model-manager.sh update_service.sh cleanup-fixes.sh stop-waiting.sh \
              mac_setup.sh quick-mac-setup.sh create-demo-user.sh create_admin.py; do
    move_to_archive "$script" "troubleshooting"
done

# Setup scripts
for pattern in "setup-*.sh"; do
    for file in $pattern; do
        [ -e "$file" ] && move_to_archive "$file" "troubleshooting"
    done
done

echo -e "\n${BLUE}10. Creating updated .gitignore...${NC}"
# Update .gitignore
cat >> .gitignore << 'EOF'

# === STING-CE Public Release Exclusions ===

# Logs
*.log
*.log.*
logs/

# Environment files
.env
.env.*
.pgpass

# Build artifacts
build/
dist/
*.egg-info/
.venv/
env/
node_modules/

# System files
.DS_Store
Thumbs.db

# Backup files
*.bak
*.bak.*
*output.txt

# Development files
old_versions/
backups/
refactor_*.json
refactor_*.md
test_*.json

# Temporary files
*.tmp
*.temp

# Archives (for development reference)
archives/
EOF

echo -e "\n${BLUE}11. Creating archive README...${NC}"
# Create README for archives
cat > "$ARCHIVE_BASE/README.md" << 'EOF'
# STING-CE Archives

This directory contains files that were moved during the public release preparation of STING-CE.

## Directory Structure

- **development/** - Development utilities, patches, and function mappings
- **legacy/** - Legacy management scripts and refactoring documentation
- **test/** - Test scripts and fixtures
- **troubleshooting/** - Diagnostic and fix scripts (to be integrated into Honey Jar system)
- **logs/** - Old log files
- **temp/** - Temporary files, environment configs, and old backups

## Important Notes

1. **Troubleshooting Scripts**: These are valuable diagnostic tools that will be integrated into the Honey Jar system for automated problem resolution.

2. **Legacy Scripts**: The various `manage_sting_*.sh` variants contain code that may be useful for reference but should not be used directly.

3. **Test Scripts**: These can be used to create a proper test suite in the future.

4. **Environment Files**: May contain sensitive information - do not commit to public repositories.

## Future Plans

- Troubleshooting scripts will be converted to Honey Jar diagnostic modules
- Test scripts will be organized into a proper test suite
- Legacy code will be reviewed for any useful patterns before permanent deletion
EOF

echo -e "\n${GREEN}✅ Reorganization complete!${NC}"
echo -e "\nSummary:"
echo "- Files moved to: $ARCHIVE_BASE/"
echo "- .gitignore updated with exclusions"
echo "- Archive README created"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Review the archives to ensure nothing critical was moved"
echo "2. Test that manage_sting.sh still works correctly"
echo "3. Commit the cleaned repository"
echo -e "\n🍯 STING-CE is ready for public release!"
EOF

chmod +x reorganize-for-release.sh