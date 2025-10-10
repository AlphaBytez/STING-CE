#!/bin/bash
# Script to fix venv exclusion in all rsync commands

# Find all rsync commands and add venv exclusion if missing
fix_rsync_venv_exclusion() {
    local file="$1"
    
    # Backup the original file
    cp "$file" "$file.bak.venv"
    
    # Find all lines with rsync that don't already exclude venv
    grep -n "rsync.*-av" "$file" | while IFS=: read -r line_num line_content; do
        # Check if this rsync command already has venv exclusion
        if ! echo "$line_content" | grep -q "exclude.*venv"; then
            # Check if it's a multi-line rsync (has trailing \)
            if echo "$line_content" | grep -q '\\$'; then
                echo "Line $line_num: Multi-line rsync found, venv exclusion might be on next lines"
            else
                # Single line rsync without venv exclusion
                echo "Line $line_num needs venv exclusion: $line_content"
                
                # Add --exclude='venv' to the rsync command
                # This is tricky because we need to insert it before the source/dest args
                # For now, just report it
            fi
        fi
    done
}

# Create a pattern file for rsync exclusions
create_rsync_exclude_file() {
    cat > /tmp/rsync_excludes.txt << 'EOF'
# Virtual environments
venv
**/venv
venv/
**/venv/
.venv
**/.venv
virtualenv
**/virtualenv

# Python artifacts
__pycache__
**/__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.egg-info
**/*.egg-info
build/
dist/
.pytest_cache
.coverage
.tox

# Node modules
node_modules
**/node_modules

# Git
.git
.gitignore

# Logs
*.log
logs/

# OS files
.DS_Store
Thumbs.db

# IDE files
.idea
.vscode
*.swp
*.swo

# Build artifacts
build
dist

# Model files (large)
models/
llm_models/
llm-models/
*.bin
*.safetensors
EOF
}

# Function to properly exclude venv in rsync
safe_rsync() {
    local src="$1"
    local dest="$2"
    shift 2
    local extra_args="$@"
    
    # Create exclude file
    create_rsync_exclude_file
    
    # Run rsync with exclude file
    rsync -av \
        --exclude-from=/tmp/rsync_excludes.txt \
        $extra_args \
        "$src" "$dest"
    
    local result=$?
    
    # Clean up
    rm -f /tmp/rsync_excludes.txt
    
    return $result
}

# Show current rsync commands that might need fixing
echo "Checking manage_sting.sh for rsync commands..."
echo "================================================"
fix_rsync_venv_exclusion "manage_sting.sh"

echo ""
echo "Recommended fix:"
echo "================"
echo "Replace all rsync commands with the safe_rsync function above, or"
echo "ensure every rsync command includes these exclusions:"
echo ""
echo "  --exclude='venv' \\"
echo "  --exclude='**/venv' \\"
echo "  --exclude='venv/' \\"
echo "  --exclude='**/venv/' \\"
echo "  --exclude='.venv' \\"
echo "  --exclude='**/.venv' \\"
echo ""
echo "Example:"
echo "  rsync -av --exclude='venv' --exclude='**/venv' --exclude='venv/' \\"
echo "            --exclude='**/venv/' --exclude='.venv' --exclude='**/.venv' \\"
echo "            \"\$source/\" \"\$dest/\""