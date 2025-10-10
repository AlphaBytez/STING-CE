#!/bin/bash
# fix_python_dependencies.sh - Fix missing Python dependencies issue

echo "🔧 STING Python Dependencies Fix"
echo "================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📍 Working directory: $SCRIPT_DIR"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "🐳 Starting dev container..."
docker compose up -d dev

echo ""
echo "⏳ Waiting for container to be ready..."
sleep 5

echo ""
echo "📦 Installing Python dependencies..."

# Install both sets of requirements
echo "  Installing conf/requirements.in..."
if docker compose exec -T dev pip install -r /app/conf/requirements.in; then
    echo "  ✅ conf/requirements.in installed successfully"
else
    echo "  ⚠️  conf/requirements.in installation had issues"
fi

echo ""
echo "  Installing app/requirements.txt..."
if docker compose exec -T dev pip install -r /app/app/requirements.txt; then
    echo "  ✅ app/requirements.txt installed successfully"
else
    echo "  ⚠️  app/requirements.txt installation had issues"
fi

echo ""
echo "🧪 Testing critical imports..."

# Test critical imports
test_imports=(
    "flask_cors"
    "app.services.user_service"
    "app.models.user_models"
    "sqlalchemy"
    "cryptography"
    "requests"
)

failed_imports=()

for import_name in "${test_imports[@]}"; do
    if docker compose exec -T dev python3 -c "import $import_name" 2>/dev/null; then
        echo "  ✅ $import_name"
    else
        echo "  ❌ $import_name"
        failed_imports+=("$import_name")
    fi
done

echo ""

if [ ${#failed_imports[@]} -eq 0 ]; then
    echo "🎉 All dependencies are working correctly!"
    echo ""
    echo "You can now run:"
    echo "  ./manage_sting.sh start"
    echo ""
else
    echo "⚠️  Some imports are still failing: ${failed_imports[*]}"
    echo ""
    echo "Try rebuilding the containers:"
    echo "  docker compose down"
    echo "  docker compose build --no-cache dev"
    echo "  docker compose up -d dev"
    echo ""
fi

echo "🔧 Fix complete!"