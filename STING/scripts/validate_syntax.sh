#!/bin/bash
# validate_syntax.sh - Validate bash script syntax across the STING codebase
# Usage: ./scripts/validate_syntax.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STING_DIR="$(dirname "$SCRIPT_DIR")"

echo "Validating bash script syntax..."
echo "================================"
echo ""

ERRORS=0
CHECKED=0

# Function to check a single script
check_script() {
    local script="$1"
    local relative_path="${script#$STING_DIR/}"

    CHECKED=$((CHECKED + 1))

    # Run bash syntax check
    if error_output=$(bash -n "$script" 2>&1); then
        echo "[+] $relative_path"
        return 0
    else
        echo "[-] $relative_path"
        echo "   Error: $error_output"
        echo ""
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Check main scripts
echo "Checking main scripts..."
for script in "$STING_DIR"/*.sh; do
    [ -f "$script" ] && check_script "$script"
done
echo ""

# Check lib scripts
echo "Checking library scripts..."
for script in "$STING_DIR/lib"/*.sh; do
    [ -f "$script" ] && check_script "$script"
done
echo ""

# Check setup scripts
echo "Checking setup scripts..."
for script in "$STING_DIR/scripts/setup"/*.sh; do
    [ -f "$script" ] && check_script "$script"
done
echo ""

# Summary
echo "================================"
echo "Validation complete!"
echo ""
echo "Scripts checked: $CHECKED"
if [ $ERRORS -eq 0 ]; then
    echo "[+] All scripts passed syntax validation!"
    exit 0
else
    echo "[-] $ERRORS script(s) have syntax errors"
    exit 1
fi
