#!/bin/bash
# 99-cleanup.sh - Cleanup and minimize image size
set -e

echo "=== STING-CE OVA Build: Cleanup ==="

# Clean apt cache
echo "Cleaning apt cache..."
apt-get autoremove -y
apt-get clean
rm -rf /var/lib/apt/lists/*

# Clean temp files
echo "Cleaning temporary files..."
rm -rf /tmp/*
rm -rf /var/tmp/*

# Clean logs (but keep structure)
echo "Cleaning old logs..."
find /var/log -type f -name "*.log" -delete 2>/dev/null || true
find /var/log -type f -name "*.gz" -delete 2>/dev/null || true
journalctl --vacuum-time=1d 2>/dev/null || true

# Clear bash history
echo "Clearing bash history..."
unset HISTFILE
rm -f /root/.bash_history
rm -f /home/*/.bash_history 2>/dev/null || true

# Clear SSH host keys (will be regenerated on first boot)
echo "Clearing SSH host keys..."
rm -f /etc/ssh/ssh_host_*

# Create script to regenerate SSH keys on first boot
cat > /etc/rc.local << 'EOF'
#!/bin/bash
# Regenerate SSH host keys if missing
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    dpkg-reconfigure openssh-server
fi
exit 0
EOF
chmod +x /etc/rc.local

# Remove machine-id (will be regenerated)
echo "Clearing machine-id..."
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id

# Clear cloud-init state so it runs fresh
echo "Resetting cloud-init..."
cloud-init clean --logs 2>/dev/null || true
rm -rf /var/lib/cloud/instances/*

# Zero out free space to help compression (optional, takes time)
echo "Zeroing free space for better compression..."
dd if=/dev/zero of=/EMPTY bs=1M 2>/dev/null || true
rm -f /EMPTY

# Sync filesystem
sync

echo "=== Cleanup complete ==="
echo ""
echo "Image is ready for export."
echo "Estimated compressed size: ~1.5-2GB"
