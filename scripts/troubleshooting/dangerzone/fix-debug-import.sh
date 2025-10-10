#!/bin/bash
# Quick fix for the missing DebugPage import

echo "🔧 Fixing DebugPage import in AppRoutes.js..."

# Backup original file
cp frontend/src/AppRoutes.js frontend/src/AppRoutes.js.bak

# Add the missing import
sed -i '' '5i\
import DebugPage from '\''./components/auth/DebugPage'\'';
' frontend/src/AppRoutes.js

# Check if fix was applied
if grep -q "import DebugPage" frontend/src/AppRoutes.js; then
  echo "✅ Fix applied successfully!"
  echo "Original file backed up as: frontend/src/AppRoutes.js.bak"
else
  echo "❌ Fix could not be applied automatically."
  echo "Please manually add this line below the other imports in frontend/src/AppRoutes.js:"
  echo "import DebugPage from './components/auth/DebugPage';"
fi

echo -e "\n📋 Next steps:"
echo "1. Restart your frontend: ./manage_sting.sh restart frontend"
echo "2. Try accessing the debug page again: https://localhost:3000/debug"
echo "3. If issues persist, try running the complete fix script: ./fix-auth-debug.sh"