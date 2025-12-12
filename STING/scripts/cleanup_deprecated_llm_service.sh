#!/usr/bin/env bash
# Cleanup deprecated llm_service directory and references
# This removes the old custom PyTorch LLM inference code that has been
# replaced by the modern provider-agnostic external-ai gateway
#
# The external-ai service supports:
# - Local: Ollama, LM Studio, LocalAI
# - Cloud: OpenAI, Anthropic, Azure OpenAI
# - Any OpenAI-compatible endpoint

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  Deprecated LLM Service Cleanup"
echo "=========================================="
echo ""
echo "This will remove the archived llm_service directory and references."
echo "Your modern LLM gateway (external-ai) will continue working unchanged."
echo ""

cd "$STING_ROOT"

# Safety check
if [ ! -d "llm_service" ]; then
    echo "[+] llm_service directory already removed - nothing to do!"
    exit 0
fi

echo " Found deprecated llm_service directory"
echo ""
echo "Changes to be made:"
echo "  1. Remove docker-compose volume mounts (2 lines)"
echo "  2. Delete obsolete chatbot/server.py (not executed)"
echo "  3. Archive llm_service directory"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🧹 Starting cleanup..."
echo ""

# 1. Backup docker-compose.yml
echo "[1/4] Backing up docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup_$(date +%Y%m%d_%H%M%S)
echo "[+] Backup created"

# 2. Remove llm_service volume mounts from docker-compose.yml
echo "[2/4] Removing deprecated volume mounts from docker-compose.yml..."
if grep -q "llm_service/chat" docker-compose.yml 2>/dev/null; then
    sed -i.bak '/llm_service\/chat/d' docker-compose.yml
    sed -i.bak '/llm_service\/filtering/d' docker-compose.yml
    rm -f docker-compose.yml.bak
    echo "[+] Removed 2 volume mount lines"
else
    echo "[*]  No volume mounts found (already cleaned)"
fi

# 3. Remove obsolete chatbot/server.py (not executed by entrypoint)
echo "[3/4] Removing obsolete chatbot/server.py..."
if [ -f "chatbot/server.py" ]; then
    mv chatbot/server.py "chatbot/server.py.deprecated_$(date +%Y%m%d)"
    echo "[+] Moved to chatbot/server.py.deprecated_$(date +%Y%m%d)"
else
    echo "[*]  chatbot/server.py already removed"
fi

# 4. Archive llm_service directory
echo "[4/4] Archiving llm_service directory..."
ARCHIVE_NAME="llm_service.ARCHIVED_$(date +%Y%m%d)"
mv llm_service "$ARCHIVE_NAME"
echo "[+] Archived to $ARCHIVE_NAME/"
echo ""

echo " Checking for remaining references..."
if grep -r "from llm_service\|import llm_service" . \
    --exclude-dir="$ARCHIVE_NAME" \
    --exclude-dir=".git" \
    --exclude="*.backup_*" \
    --include="*.py" 2>/dev/null | grep -v "^Binary"; then

    echo ""
    echo "[!]  Found references above - please review manually"
else
    echo "[+] No active code references found"
fi

echo ""
echo "=========================================="
echo "  [+] Cleanup Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Archived: $ARCHIVE_NAME/"
echo "  • Removed: 2 docker-compose volume mounts"
echo "  • Removed: chatbot/server.py (obsolete)"
echo ""
echo "Your modern LLM architecture remains unchanged:"
echo "  Bee → external-ai gateway → Your LLM provider"
echo "  (Ollama, OpenAI, Anthropic, Azure, etc.)"
echo ""
echo "To permanently delete archived directory:"
echo "  rm -rf $ARCHIVE_NAME/"
echo ""
