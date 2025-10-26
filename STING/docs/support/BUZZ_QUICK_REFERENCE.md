# 🐝 Buzz Commands - Quick Reference

## Basic Commands
```bash
# Create a diagnostic bundle (honey jar)
./manage_sting.sh buzz collect

# List existing bundles
./manage_sting.sh buzz list

# Show hive status
./manage_sting.sh buzz hive-status

# Clean old bundles
./manage_sting.sh buzz clean
```

## Advanced Collection
```bash
# Last 48 hours with ticket reference
./manage_sting.sh buzz collect --hours 48 --ticket SUPPORT-123

# Focus on authentication issues
./manage_sting.sh buzz collect --auth-focus --include-startup

# Focus on LLM performance
./manage_sting.sh buzz collect --llm-focus --performance

# Custom time range
./manage_sting.sh buzz collect --from "2024-01-01 10:00" --to "2024-01-01 15:00"
```

## Maintenance
```bash
# Test data sanitization
./manage_sting.sh buzz filter-test

# Clean bundles older than 7 days
./manage_sting.sh buzz clean --older-than 7d

# Check available space
ls -lah ${INSTALL_DIR}/support_bundles/
```

## Bundle Contents
✅ **Included**: Service logs, container status, system metrics, sanitized configs  
❌ **Filtered**: Passwords, API keys, tokens, email addresses, phone numbers

## Quick Troubleshooting
- **Service won't start**: `./manage_sting.sh buzz collect --include-startup`
- **Auth problems**: `./manage_sting.sh buzz collect --auth-focus`  
- **Performance issues**: `./manage_sting.sh buzz collect --performance --llm-focus`
- **Before major changes**: `./manage_sting.sh buzz collect --baseline`

## Bundle Location
📁 Default: `${INSTALL_DIR}/support_bundles/`  
🕐 Auto-cleanup: 30 days  
🔒 Privacy: Automatically sanitized