#!/usr/bin/env bash
# Optimize Docker build speeds using BuildKit cache mounts
# This dramatically speeds up pip installs by caching downloaded packages
#
# Why this works:
# - BuildKit cache persists pip downloads across builds
# - No external mirrors needed (works on all networks)
# - Standard Docker best practice
# - 10-50x faster on slow network connections

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  Docker Build Speed Optimization"
echo "=========================================="
echo ""
echo "This will add BuildKit cache mounts to all Dockerfiles"
echo "to dramatically speed up pip installs."
echo ""

cd "$STING_ROOT"

# Backup timestamp
BACKUP_SUFFIX="backup_$(date +%Y%m%d_%H%M%S)"

# Counter for changes
OPTIMIZED_COUNT=0

# Find all Dockerfiles with pip install commands
echo "🔍 Scanning Dockerfiles for pip install commands..."
echo ""

DOCKERFILES=$(find . -type f \( -name "Dockerfile*" \) -not -path "*/\.*" -not -name "*.backup*" 2>/dev/null)

for dockerfile in $DOCKERFILES; do
    # Check if this Dockerfile has pip install
    if grep -q "pip install" "$dockerfile" 2>/dev/null; then
        echo "📝 Processing: $dockerfile"

        # Check if already optimized
        if grep -q "mount=type=cache.*pip" "$dockerfile" 2>/dev/null; then
            echo "   ✅ Already optimized - skipping"
            continue
        fi

        # Backup original
        cp "$dockerfile" "${dockerfile}.${BACKUP_SUFFIX}"

        # Create optimized version using awk for precise control
        awk '
        /^RUN.*pip install/ {
            # Check if this is a multi-line RUN with backslash continuation
            if (/\\$/) {
                # Multi-line pip install - add cache mount before the line
                print "RUN --mount=type=cache,target=/root/.cache/pip \\"
                sub(/^RUN /, "    ")
                print
            } else {
                # Single line pip install
                sub(/^RUN /, "RUN --mount=type=cache,target=/root/.cache/pip ")
                print
            }
            next
        }
        # Print all other lines unchanged
        { print }
        ' "${dockerfile}.${BACKUP_SUFFIX}" > "$dockerfile"

        echo "   ✅ Optimized!"
        ((OPTIMIZED_COUNT++))
    fi
done

echo ""
echo "=========================================="
echo "  ✅ Optimization Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Optimized $OPTIMIZED_COUNT Dockerfile(s)"
echo "  • Backups saved with suffix: .$BACKUP_SUFFIX"
echo ""
echo "BuildKit cache mount benefits:"
echo "  📦 Persistent pip cache across builds"
echo "  🚀 10-50x faster pip installs on slow networks"
echo "  💾 Automatic cache management"
echo "  🌍 Works on all networks (no external mirrors)"
echo ""
echo "Next steps:"
echo "  1. Test a build: docker compose build [service]"
echo "  2. On slow networks, first builds cache packages"
echo "  3. Subsequent builds reuse cache (near-instant!)"
echo ""
echo "To enable BuildKit (if not already):"
echo "  export DOCKER_BUILDKIT=1"
echo "  export COMPOSE_DOCKER_CLI_BUILD=1"
echo ""
echo "To clean up backups:"
echo "  find . -name \"*.${BACKUP_SUFFIX}\" -delete"
echo ""
