#!/bin/bash

# Clean up old planning and temporary documents from root directory
# These have been superseded by proper documentation in docs/

echo "Cleaning up old planning documents from root directory..."

# Create archive directory if needed for any important docs
mkdir -p archive/old-planning-docs

# List of documents to remove (outdated planning/temp docs)
DOCS_TO_REMOVE=(
    # Planning documents that are outdated or moved to docs/
    "CHATBOT_TIMEOUT_FIXES.md"
    "FIX_LLM_START_ORDER.md" 
    "LOGIN_PAGE_V2_UPDATE.md"
    "LOGIN_PAGE_SUMMARY.md"
    "OLLAMA_MIGRATION_PROGRESS.md"
    "PASSKEY_IMPLEMENTATION_REPORT.md"
    "PUBLIC_RELEASE_CLEANUP_PLAN.md"
    "REPORT_GENERATION_FRAMEWORK.md"
    "REPORT_GENERATION_MVP_SPEC.md"
    "SETTINGS_THEME_AUDIT.md"
    "STING_UI_IMPROVEMENTS_PLAN.md"
    "bee-reports-status.md"
    
    # Technical implementation details that belong in docs/
    "DOCKER_NPM_SOLUTIONS.md"
    "INSTALLATION_FUNCTIONS_EXTRACTED.md"
    "MODULE_DEPENDENCIES.md"
    "REINSTALL_OPTIMIZATION_GUIDE.md"
    "VENV_EXCLUSION_SUMMARY.md"
)

# Archive these docs (in case we need to reference them)
echo "Archiving old planning documents..."
for doc in "${DOCS_TO_REMOVE[@]}"; do
    if [ -f "$doc" ]; then
        echo "Archiving $doc"
        mv "$doc" archive/old-planning-docs/
    fi
done

# Move test_auth_flow.md to docs/ (it's a useful testing guide)
if [ -f "test_auth_flow.md" ]; then
    echo "Moving test_auth_flow.md to docs/ (useful testing guide)"
    mv "test_auth_flow.md" "docs/AUTH_FLOW_TESTING_GUIDE.md"
fi

# Keep these important docs in root:
echo ""
echo "Keeping these important docs in root:"
echo "- README.md (main project readme)"
echo "- CLAUDE.md (backwards compatibility reference)"
echo "- CREDITS.md (attribution)"
echo "- AGENTS.md (agent framework)"
echo "- AI_ASSISTANT.md (assistant features)"
echo ""
echo "All other documentation is properly organized in docs/"
echo ""
echo "Done! Old planning docs archived to archive/old-planning-docs/"
echo "test_auth_flow.md moved to docs/AUTH_FLOW_TESTING_GUIDE.md"