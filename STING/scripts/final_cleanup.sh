#!/bin/bash

# Final cleanup before public release
# Removes remaining test/debug files from root

echo "🧹 Final Cleanup - Removing test/debug files..."

cd "$(dirname "$0")/.."

# Remove test files from root
rm -f create_test_*.py
rm -f debug_*.py
rm -f demo_*.py
rm -f queue_test_*.py
rm -f init_report_templates_manual.py

# Remove test artifacts
rm -f kratos_cookies*.txt
rm -f login_flow.txt
rm -f *_cookies.txt
rm -f final_test.pdf

# Remove temp/backup files
rm -f temp_*.sh
rm -f *.bak*
rm -f *.old

# Remove debug files
rm -f debug-*.html
rm -f check_aal2_state.js

# Remove old compose backups
rm -f docker-compose.*.bak*

# Keep test_in_vm.sh - it's useful for users

echo "✓ Cleanup complete!"
echo ""
echo "Remaining root scripts:"
ls -lh *.sh 2>/dev/null | grep -v test_in_vm | awk '{print "  " $9}'
