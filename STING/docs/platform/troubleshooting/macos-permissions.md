# macOS Permission Issues with STING

## Common Permission Problems

On macOS, you may encounter permission issues after installation or updates, particularly:

```bash
/usr/local/bin/msting: line 13: /Users/captain-wolf/.sting-ce/manage_sting.sh: Permission denied
/usr/local/bin/msting: line 13: exec: /Users/captain-wolf/.sting-ce/manage_sting.sh: cannot execute: Undefined error: 0
```

## Quick Fix

We've provided a script to fix these permission issues:

```bash
# From the STING project directory
./fix_permissions.sh
```

## Manual Fix

If you prefer to fix permissions manually:

```bash
# Fix manage_sting.sh
chmod +x ~/.sting-ce/manage_sting.sh

# Fix all shell scripts in the installation
find ~/.sting-ce -name "*.sh" -type f -exec chmod +x {} \;

# Fix msting command (if needed)
sudo chmod +x /usr/local/bin/msting
```

## Why This Happens

1. **File System Differences**: macOS uses different file systems (APFS, HFS+) that may handle permissions differently than Linux
2. **Copy Operations**: When files are copied during installation, execute permissions may not be preserved
3. **Security Features**: macOS security features may strip execute permissions from downloaded files

## Prevention

The installation script has been updated to better handle permissions on macOS. To ensure this doesn't happen:

1. Always run the official installation script:
   ```bash
   ./install_sting.sh install
   ```

2. After updates, verify permissions:
   ```bash
   ls -la ~/.sting-ce/manage_sting.sh
   # Should show 'x' permissions: -rwxr-xr-x
   ```

## During Installation

The installer now runs these commands automatically:
- Sets execute permissions on all .sh files
- Specifically verifies manage_sting.sh is executable
- Sets proper ownership for the installation directory

## Troubleshooting

If you continue to have permission issues:

1. Check file ownership:
   ```bash
   ls -la ~/.sting-ce/manage_sting.sh
   # Should be owned by your user, not root
   ```

2. If owned by root, fix it:
   ```bash
   sudo chown -R $USER:$(id -gn) ~/.sting-ce
   ```

3. Verify the msting command works:
   ```bash
   which msting
   msting --version
   ```

## Note for Developers

When developing or testing STING, always ensure shell scripts have execute permissions in the source repository:

```bash
# Before committing
find . -name "*.sh" -type f -exec chmod +x {} \;
git add -u
git commit -m "Fix: Ensure shell scripts have execute permissions"
```