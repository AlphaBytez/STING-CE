# STING-CE Migration Scripts

This directory contains version migration scripts that are automatically executed during upgrades.

## Naming Convention

Migration scripts should be named: `v{from_version}_to_v{to_version}.sh`

Examples:
- `v1.0.0_to_v1.1.0.sh`
- `v1.1.0_to_v1.2.0.sh`
- `v2.0.0_to_v2.1.0.sh`

## Migration Script Structure

Each migration script should:
1. Check prerequisites
2. Perform the migration
3. Validate the result
4. Exit with appropriate status code

## Example Migration Script

```bash
#!/bin/bash
# Migration from v1.0.0 to v1.1.0
set -e

MIGRATION_NAME="v1.0.0_to_v1.1.0"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo "Running migration: ${MIGRATION_NAME}"

# Step 1: Backup critical data
echo "Creating migration backup..."
mkdir -p "${INSTALL_DIR}/backups/migrations"
backup_file="${INSTALL_DIR}/backups/migrations/${MIGRATION_NAME}-$(date +%Y%m%d-%H%M%S).tar.gz"

# Backup configuration files
tar -czf "$backup_file" \
    -C "${INSTALL_DIR}" \
    conf/ \
    env/ \
    2>/dev/null || echo "Warning: Some files could not be backed up"

# Step 2: Perform migration tasks
echo "Performing migration tasks..."

# Example: Update configuration file
if [ -f "${INSTALL_DIR}/conf/config.yml" ]; then
    # Add new configuration key
    if ! grep -q "new_feature_enabled" "${INSTALL_DIR}/conf/config.yml"; then
        echo "  new_feature_enabled: true" >> "${INSTALL_DIR}/conf/config.yml"
        echo "✅ Updated config.yml"
    fi
fi

# Example: Run database migration
docker exec sting-ce-app flask db upgrade || {
    echo "❌ Database migration failed"
    exit 1
}

# Step 3: Validate migration
echo "Validating migration..."

# Check if new feature is accessible
if curl -f -s -o /dev/null http://localhost:5050/api/health; then
    echo "✅ Health check passed"
else
    echo "⚠️ Health check failed - but continuing"
fi

echo "✅ Migration ${MIGRATION_NAME} completed successfully"
exit 0
```

## Running Migrations

Migrations are automatically executed during the upgrade process via:
```bash
sudo msting upgrade
```

To manually run a specific migration:
```bash
sudo bash /opt/sting-ce/migrations/v1.0.0_to_v1.1.0.sh
```

## Best Practices

1. **Idempotent**: Migrations should be safe to run multiple times
2. **Backup**: Always backup data before making changes
3. **Validate**: Check prerequisites before making changes
4. **Rollback**: Provide rollback instructions in comments
5. **Logging**: Log all actions for debugging
6. **Error Handling**: Exit with non-zero status on failure

## Migration Checklist

Before creating a migration:
- [ ] Identify what changed between versions
- [ ] Document breaking changes
- [ ] Create backup strategy
- [ ] Test migration on clean install
- [ ] Test migration on existing install
- [ ] Document rollback procedure
- [ ] Add to CHANGELOG.md

## Troubleshooting

If a migration fails:
1. Check the migration logs
2. Restore from automatic backup if needed
3. Review the migration script for issues
4. Run the migration manually with debug output
5. Report issues on GitHub

## Migration History

Migrations are logged in: `/opt/sting-ce/.upgrade_history`
