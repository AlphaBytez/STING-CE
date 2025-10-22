#!/bin/bash
# Deep cleanup - removes all remaining deprecated items

echo "🧹 Deep Cleanup..."
cd "$(dirname "$0")/.."

# Remove frontend archives
echo "- Removing frontend archive directories..."
rm -rf frontend/src/archive
rm -rf frontend/src/auth/archive
rm -rf frontend/src/components/auth/archive

# Remove test files with SuperTokens
echo "- Removing SuperTokens test files..."
rm -f app/test_auth_setup.py

# Clean SuperTokens from config.yml
echo "- Cleaning config.yml..."
if [ -f "conf/config.yml" ]; then
    sed -i '/supertokens:/,+10d' conf/config.yml
fi

# Clean SuperTokens from entrypoint.sh
echo "- Cleaning entrypoint scripts..."
if [ -f "app/entrypoint.sh" ]; then
    sed -i '/supertokens/d' app/entrypoint.sh
    sed -i '/Supertokens/d' app/entrypoint.sh
fi

# Remove commented SuperTokens code from __init__.py (already commented, just remove)
if [ -f "app/__init__.py" ]; then
    sed -i '/# from supertokens/d' app/__init__.py
    sed -i '/# .*supertokens/d' app/__init__.py
fi

# Remove any remaining .bak files
find . -name "*.bak*" -delete 2>/dev/null

echo "✅ Deep cleanup complete!"
echo ""
echo "Verification:"
echo "- Archive dirs: $(find . -type d -name "archive" 2>/dev/null | wc -l)"
echo "- SuperTokens refs: $(grep -r "supertokens" . 2>/dev/null | grep -v ".git" | wc -l)"
