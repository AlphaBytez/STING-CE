# STING-CE Upgrade Guide

This guide explains how to upgrade STING-CE to the latest version.

## Quick Upgrade

For most users, upgrading is a single command:

```bash
sudo msting upgrade
```

This will:
1. Create an automatic backup
2. Pull the latest Docker images
3. Run any necessary migrations
4. Restart services
5. Verify health

## Version Management

### Check Current Version

```bash
msting version
```

Output:
```
╭──────────────────────────────────────────╮
│  STING-CE Version Information           │
╰──────────────────────────────────────────╯

  Current Version: v1.0.0
  Install Path:    /opt/STING-CE
```

### Check for Updates

```bash
msting version --check-updates
```

This queries GitHub for the latest release and compares it with your current version.

## Upgrade Options

### Upgrade to Latest Version

```bash
sudo msting upgrade
```

### Upgrade to Specific Version

```bash
sudo msting upgrade --version=1.2.0
```

### Skip Automatic Backup

```bash
sudo msting upgrade --no-backup
```

⚠️ **Not recommended** - Backups are your safety net!

### Check What Would Be Upgraded (Dry Run)

```bash
sudo msting upgrade --check-only
```

## How Upgrades Work

### Image-Based Upgrades (Default)

STING-CE uses versioned Docker images published to GitHub Container Registry:

1. **Check Current Version**: Read from `/opt/STING-CE/VERSION`
2. **Create Backup**: Backup configuration and environment files
3. **Pull Images**: Download new Docker images from GHCR
4. **Run Migrations**: Execute any version-specific migration scripts
5. **Update VERSION**: Write new version to VERSION file
6. **Restart Services**: Bring up containers with new images
7. **Health Check**: Verify services are running correctly
8. **Log History**: Record upgrade in `.upgrade_history`

### What Gets Backed Up

Before each upgrade, the following are backed up:

- `/opt/STING-CE/conf/` - Configuration files
- `/opt/STING-CE/env/` - Environment variables
- `/opt/STING-CE/VERSION` - Version file

Backups are stored in: `/opt/STING-CE/backups/pre-upgrade-YYYYMMDD-HHMMSS.tar.gz`

### What Gets Preserved

The upgrade process **preserves**:
- User data (database volumes)
- Uploaded files
- SSL certificates
- Custom configurations
- Docker volumes

### What Gets Updated

The upgrade process **updates**:
- Docker images (application code)
- Database schemas (via migrations)
- Default configurations (merged with your changes)

## Migration Scripts

Version-specific migrations are located in `/opt/STING-CE/migrations/`

### Viewing Migration History

```bash
cat /opt/STING-CE/.upgrade_history
```

Example output:
```
2024-01-15 10:30:45 - Upgraded from v1.0.0 to v1.1.0
2024-02-20 14:22:10 - Upgraded from v1.1.0 to v1.2.0
2024-03-10 09:15:30 - Upgraded from v1.2.0 to v1.3.0
```

### Manual Migration Execution

If needed, you can run migrations manually:

```bash
sudo bash /opt/STING-CE/migrations/v1.0.0_to_v1.1.0.sh
```

## Rollback

If an upgrade fails or causes issues, you can rollback:

### Restore from Backup

```bash
# Find your backup
ls -lh /opt/STING-CE/backups/

# Restore configuration
sudo tar -xzf /opt/STING-CE/backups/pre-upgrade-YYYYMMDD-HHMMSS.tar.gz -C /opt/STING-CE/

# Restart services
cd /opt/STING-CE && docker compose restart
```

### Rollback to Specific Version

```bash
# Stop services
cd /opt/STING-CE && docker compose down

# Set version to rollback to
export STING_VERSION=1.0.0
export STING_IMAGE_REGISTRY=ghcr.io/alphabytez

# Pull old images
docker compose pull

# Start with old version
docker compose up -d
```

## Upgrade Path

### Supported Upgrade Paths

- ✅ **Minor versions**: 1.0.x → 1.1.x (fully supported)
- ✅ **Patch versions**: 1.0.0 → 1.0.1 (fully supported)
- ⚠️ **Major versions**: 1.x → 2.x (check release notes for breaking changes)

### Skipping Versions

You can usually skip versions (e.g., 1.0.0 → 1.3.0), but:

1. Read release notes for all intermediate versions
2. Check for breaking changes
3. Test in a staging environment first
4. Backup before upgrading

### Breaking Changes

Major version upgrades may require manual intervention:

1. Review `CHANGELOG.md` for breaking changes
2. Update custom configurations
3. Test thoroughly after upgrade
4. Check logs for deprecation warnings

## Troubleshooting

### Upgrade Fails to Pull Images

**Problem**: Cannot pull images from GHCR

**Solution**:
```bash
# Check Docker credentials
docker login ghcr.io

# Manually pull images
export STING_VERSION=latest
docker compose pull
```

### Services Won't Start After Upgrade

**Problem**: Services stuck in restart loop

**Solution**:
```bash
# Check logs
docker compose logs app
docker compose logs frontend

# Restore from backup
sudo tar -xzf /opt/STING-CE/backups/pre-upgrade-*.tar.gz -C /opt/STING-CE/

# Restart
docker compose restart
```

### Database Migration Fails

**Problem**: Migration script exits with error

**Solution**:
```bash
# Check database logs
docker compose logs db

# Manually run migration
docker exec sting-ce-app flask db upgrade

# If stuck, consult migration logs
docker compose logs app | grep -i migration
```

### Version Mismatch

**Problem**: `msting version` shows wrong version

**Solution**:
```bash
# Check VERSION file
cat /opt/STING-CE/VERSION

# Check running image versions
docker images | grep sting-ce

# If mismatch, force pull
export STING_VERSION=1.2.0
cd /opt/STING-CE && docker compose pull
docker compose up -d
```

## Best Practices

### Before Upgrading

1. ✅ **Read Release Notes**: Check `CHANGELOG.md` and GitHub releases
2. ✅ **Backup Data**: Though automatic, manual backup is good practice
3. ✅ **Test Environment**: Upgrade staging/dev environment first
4. ✅ **Maintenance Window**: Schedule upgrades during low-traffic periods
5. ✅ **Check Disk Space**: Ensure sufficient space for new images

### During Upgrade

1. ⏱️ **Be Patient**: Large images may take time to download
2. 📊 **Monitor Logs**: Watch upgrade progress in another terminal
3. 🚫 **Don't Interrupt**: Let the upgrade complete fully

### After Upgrading

1. ✅ **Verify Version**: Run `msting version` to confirm
2. ✅ **Check Services**: Run `msting status` for health check
3. ✅ **Test Functionality**: Log in and verify core features
4. ✅ **Review Logs**: Check for errors or warnings
5. ✅ **Update Documentation**: Note any configuration changes

## Development Upgrades

For developers working from source:

### Pull Latest Code

```bash
cd /path/to/STING-CE
git pull origin main
```

### Rebuild Images

```bash
# Rebuild all images
msting update --no-cache

# Or rebuild specific service
docker compose build --no-cache app
docker compose up -d app
```

### Development vs Production

| Mode | Image Source | Update Method |
|------|-------------|---------------|
| **Production** | GHCR (pre-built) | `msting upgrade` |
| **Development** | Local build | `git pull + msting update` |

## Version Pinning

To pin to a specific version and prevent automatic upgrades:

### Set Version in Environment

```bash
# Edit docker-compose override
cat > /opt/STING-CE/docker-compose.override.yml << EOF
services:
  app:
    image: ghcr.io/alphabytez/STING-CE-app:1.0.0
  frontend:
    image: ghcr.io/alphabytez/STING-CE-frontend:1.0.0
EOF
```

### Update Later

```bash
# Remove override to use latest
rm /opt/STING-CE/docker-compose.override.yml

# Run upgrade
sudo msting upgrade
```

## FAQ

### Q: How often should I upgrade?

**A**: For security and stability, upgrade when:
- Security patches are released (immediately)
- New features you need are added
- Bug fixes for issues you're experiencing

### Q: Will upgrading cause downtime?

**A**: Yes, brief downtime (typically 2-5 minutes) occurs during:
- Container restart
- Database migrations
- Image pulling

Plan upgrades during maintenance windows.

### Q: Can I automate upgrades?

**A**: Not recommended for production. Always review release notes first. For testing environments:

```bash
# Add to crontab (weekly upgrade check)
0 2 * * 0 /usr/local/bin/msting upgrade --check-only
```

### Q: What if my custom changes get overwritten?

**A**: Customizations should be in:
- `/opt/STING-CE/conf/` (preserved)
- `/opt/STING-CE/env/` (preserved)
- `docker-compose.override.yml` (never touched)

Docker images contain default code only.

## Support

- 📖 Documentation: https://docs.sting.local
- 🐛 Issues: https://github.com/alphabytez/STING-CE/issues
- 💬 Discussions: https://github.com/alphabytez/STING-CE/discussions
- 📧 Email: support@sting.local

## Version History

Track your upgrade history:

```bash
cat /opt/STING-CE/.upgrade_history
```

## Related Documentation

- [Installation Guide](INSTALL.md)
- [Configuration Guide](CONFIGURATION.md)
- [Backup and Restore](BACKUP.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
