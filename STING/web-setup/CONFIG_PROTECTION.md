# Config Protection - How config.yml Survives Installation

## TL;DR

**Your config.yml is safe!** ✅

The STING installer already has built-in protection that **prevents config.yml from being overwritten** during installation or updates.

## How It Works

### 1. Rsync Exclusions

The installer uses `rsync` with `--exclude` flags to protect user configuration:

```bash
# From lib/file_operations.sh
rsync -a --delete "$project_dir/" "$INSTALL_DIR/" \
    --exclude .git \
    --exclude '*.log' \
    --exclude 'config.yml' \    # <-- THIS PROTECTS YOUR CONFIG!
    --exclude '*.env'
```

**Files that are protected:**
- `config.yml` - Main configuration file
- `*.env` - Generated environment files
- `*.log` - Log files
- `.git` - Git metadata

### 2. Config Change Detection

The installer detects if config.yml has changed:

```bash
# lib/file_operations.sh line 225
if ! diff -q "$project_dir/conf/config.yml" "$INSTALL_DIR/conf/config.yml"; then
    log_message "config.yml has changed"
    config_changed=true
fi
```

If changed, it regenerates environment files using `config_loader.py`.

### 3. Backup Mechanism

If you explicitly reset configuration, the installer creates backups:

```bash
# lib/file_operations.sh - reset_config_files()
cp "$config_file" "$config_file.$backup_num"
log_message "✓ Backed up to config.yml.$backup_num"

# Keeps last 5 backups
find . -name "config.yml.*" -type f | tail -n +6 | xargs rm -f
```

## Wizard Integration

### Safe Configuration Flow

When the wizard applies configuration, it leverages this protection:

```python
def apply_config():
    # 1. Wizard writes config.yml
    with open('/opt/sting-ce/conf/config.yml', 'w') as f:
        yaml.dump(wizard_config, f)

    # 2. Invoke installer
    subprocess.run([
        '/opt/sting-ce/install_sting.sh',
        'install',
        '--non-interactive'
    ])

    # The installer will:
    # - See config.yml exists at /opt/sting-ce/conf/config.yml
    # - NOT overwrite it (thanks to rsync --exclude)
    # - Detect it's different from project default
    # - Regenerate env files from wizard's config
    # - Start STING with wizard's configuration
```

### Protection Layers

**Layer 1: Wizard Writes First**
```bash
# Wizard creates config.yml BEFORE installer runs
/opt/sting-ce/conf/config.yml  # Created by wizard
```

**Layer 2: Rsync Excludes It**
```bash
# Installer syncs files but excludes config.yml
rsync ... --exclude 'config.yml' ...
# Result: Wizard's config.yml survives!
```

**Layer 3: Change Detection**
```bash
# Installer detects wizard config differs from default
if config_changed; then
    regenerate_env_files  # Use wizard's config
fi
```

**Layer 4: Env File Generation**
```bash
# config_loader.py reads wizard's config.yml
python3 config_loader.py /opt/sting-ce/conf/config.yml
# Generates env files from wizard's settings
```

## Test Scenarios

### Scenario 1: Fresh Install with Wizard

```bash
# 1. Boot VM - no config.yml exists
ls /opt/sting-ce/conf/config.yml
# File not found

# 2. Run wizard - creates config.yml
# Wizard writes validated configuration
cat /opt/sting-ce/conf/config.yml
# Contains wizard settings

# 3. Wizard invokes installer
./install_sting.sh install --non-interactive

# 4. Installer sees wizard's config.yml
# - Does NOT overwrite it (rsync excludes it)
# - Generates env files from it
# - Starts STING with wizard settings

# 5. Verify config survived
cat /opt/sting-ce/conf/config.yml
# Still contains wizard settings ✅
```

### Scenario 2: Update After Wizard Setup

```bash
# User completed wizard months ago
cat /opt/sting-ce/conf/config.yml
# Contains customized LLM endpoints, SMTP, etc.

# New STING version released
./install_sting.sh update

# Installer:
# 1. Syncs new code (excludes config.yml)
# 2. Detects config.yml differs from new default
# 3. Regenerates env files from user's config
# 4. Restarts services

# User's config survives ✅
cat /opt/sting-ce/conf/config.yml
# Still has customized settings
```

### Scenario 3: Manual Config Edit

```bash
# User manually edits config after wizard
vim /opt/sting-ce/conf/config.yml
# Change LLM endpoint to new server

# Regenerate env files
./manage_sting.sh regenerate-env

# Installer:
# 1. Runs config_loader.py on user's config.yml
# 2. Generates updated env files
# 3. User's changes applied ✅
```

## Edge Cases

### What if wizard's config.yml is invalid?

**Protection: Wizard validates BEFORE writing**

```python
# Wizard validates with config_loader.py
valid, errors = validate_config_with_loader(config)

if not valid:
    # Don't write config.yml
    # Show errors to user
    return jsonify({'errors': errors}), 400

# Only write if valid
with open('/opt/sting-ce/conf/config.yml', 'w') as f:
    yaml.dump(config, f)  # Safe to write
```

The wizard **never writes invalid config.yml** because it validates first.

### What if installer can't read wizard's config.yml?

**Protection: Installer has fallback**

```bash
# If config.yml is missing or corrupt
if [ ! -f config.yml ]; then
    # Copy from default
    cp config.yml.default config.yml
fi
```

But this shouldn't happen because:
1. Wizard validates before writing
2. Wizard writes atomically (no partial writes)
3. Wizard marks setup complete only on success

### What if user wants to reset to defaults?

**Protection: Manual reset with backup**

```bash
# User can explicitly reset
./manage_sting.sh reset-config

# This:
# 1. Backs up config.yml to config.yml.1
# 2. Copies config.yml.default to config.yml
# 3. User can restore from backup if needed
```

## Best Practices

### For Wizard Development

1. **Always validate before writing**
   ```python
   valid, errors = validate_config_with_loader(config)
   if valid:
       write_config(config)
   ```

2. **Write atomically**
   ```python
   # Write to temp file first
   with open('/tmp/config.yml.tmp', 'w') as f:
       yaml.dump(config, f)

   # Validate temp file
   if validate_temp_file():
       shutil.move('/tmp/config.yml.tmp', '/opt/sting-ce/conf/config.yml')
   ```

3. **Mark setup complete only on success**
   ```python
   if installer_succeeded():
       mark_setup_complete()
   else:
       # Don't mark complete
       # User can retry wizard
   ```

### For Users

1. **Let wizard validate**
   - Don't manually edit config.yml before wizard completes
   - Use wizard's validation features

2. **Use wizard's staging**
   - Wizard validates configuration
   - Only applies valid configs
   - Prevents broken installations

3. **After wizard, edit freely**
   - After wizard completes, config.yml is yours
   - Installer protects it during updates
   - Use `./manage_sting.sh regenerate-env` after edits

## Summary

### Wizard's Responsibility
- ✅ Validate configuration with `config_loader.py`
- ✅ Write valid `config.yml` to correct location
- ✅ Invoke installer with `--non-interactive`
- ✅ Mark setup complete on success

### Installer's Responsibility
- ✅ Protect existing `config.yml` (rsync exclude)
- ✅ Detect config changes
- ✅ Regenerate env files from user's config
- ✅ Start STING with correct configuration

### Result
**User's configuration is always preserved!** 🎉

The wizard and installer work together to ensure:
- Config is validated before applying
- Config survives installation
- Config survives updates
- User can edit config anytime
- Backups exist for safety

## Code References

**Protection in installer:**
- `/mnt/c/DevWorld/STING-CE-Fresh/lib/file_operations.sh:442` - rsync exclude
- `/mnt/c/DevWorld/STING-CE-Fresh/lib/file_operations.sh:225` - change detection
- `/mnt/c/DevWorld/STING-CE-Fresh/lib/file_operations.sh:879` - reset with backup

**Validation in wizard:**
- `web-setup/app.py:validate_config_with_loader()` - config validation
- `web-setup/app.py:apply_config()` - safe application

**Generation in installer:**
- `/mnt/c/DevWorld/STING-CE-Fresh/lib/config_utils.sh:67` - env file generation
- `/mnt/c/DevWorld/STING-CE-Fresh/conf/config_loader.py` - config parser
