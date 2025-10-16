#!/bin/bash

echo "Clearing frontend cache and rebuilding..."

# Clear node_modules cache
echo "1. Clearing npm cache..."
cd frontend
npm cache clean --force

# Remove build directory
echo "2. Removing build directory..."
rm -rf build/

# Remove any .cache directories
echo "3. Removing cache directories..."
find . -type d -name ".cache" -exec rm -rf {} + 2>/dev/null || true

# Clear browser cache hint
echo "4. Browser cache:"
echo "   Please clear your browser cache (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows/Linux)"

echo ""
echo "Cache cleared! Now run:"
echo "  ./manage_sting.sh update frontend --force"
echo ""
echo "Or for faster development updates:"
echo "  ./manage_sting.sh update frontend --sync-only"