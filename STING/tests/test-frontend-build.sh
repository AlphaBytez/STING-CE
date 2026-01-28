#!/bin/bash
echo "🔄 Testing frontend build with 2FA enforcement..."

# Build the frontend
cd /mnt/c/Dev/STING-CE/STING/frontend
npm run build

if [ $? -eq 0 ]; then
  echo "✅ Frontend build successful!"
  echo "📦 Build created in frontend/build/"
else
  echo "❌ Frontend build failed!"
  exit 1
fi