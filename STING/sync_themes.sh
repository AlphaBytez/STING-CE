#!/bin/bash

echo "Syncing theme files from src/theme to public/theme..."

# Create public/theme directory if it doesn't exist
mkdir -p frontend/public/theme

# Copy all theme CSS files from src to public
cp frontend/src/theme/*.css frontend/public/theme/ 2>/dev/null || true

echo "✅ Theme files synced!"
echo ""
echo "Files in public/theme:"
ls -la frontend/public/theme/
echo ""
echo "Now run: ./manage_sting.sh update frontend --sync-only"
echo "Or for full rebuild: ./manage_sting.sh update frontend --force"