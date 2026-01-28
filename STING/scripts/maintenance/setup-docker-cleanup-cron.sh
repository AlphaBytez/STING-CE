#!/bin/bash

# Setup cron job for Docker cleanup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup-docker.sh"

# Add cron job to run cleanup daily at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * $CLEANUP_SCRIPT >> /tmp/docker-cleanup.log 2>&1") | crontab -

echo "[+] Docker cleanup cron job installed!"
echo "📅 Will run daily at 2 AM"
echo "📝 Logs will be written to /tmp/docker-cleanup.log"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove this cron job: crontab -e"