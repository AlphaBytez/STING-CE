# STING Update Best Practices

## Quick Reference

### When to use each update command:

1. **`./manage_sting.sh update [service]`**
   - Updates a specific service's Docker image and code
   - Does NOT sync scripts or configuration files
   - Use for: Quick service-specific code updates

2. **`./manage_sting.sh sync-config`** ⭐
   - Syncs ALL configuration files and scripts
   - Does NOT rebuild Docker images
   - Use for: After changing scripts, config files, or docker-compose files
   - **Always run this if you've modified anything in `/scripts`**

3. **`./manage_sting.sh update [service] && ./manage_sting.sh sync-config`**
   - Full update: rebuilds service AND syncs all configs/scripts
   - Use for: Comprehensive updates when you've changed both code and scripts

## Common Scenarios

### Scenario 1: Updated Python scripts (like password reset)
```bash
./manage_sting.sh sync-config
```

### Scenario 2: Changed backend API code
```bash
./manage_sting.sh update app
```

### Scenario 3: Modified frontend React components
```bash
./manage_sting.sh update frontend
```

### Scenario 4: Changed both code and scripts
```bash
./manage_sting.sh update app frontend
./manage_sting.sh sync-config
```

### Scenario 5: Modified docker-compose.yml
```bash
./manage_sting.sh sync-config
./manage_sting.sh restart  # To apply compose changes
```

## What Gets Synced by sync-config

- `/scripts/*` - All Python and shell scripts
- `/conf/*` - Configuration files
- `/lib/*` - Shell library modules
- `docker-compose*.yml` - All compose files
- `manage_sting.sh` - Main management script
- `.env.example` - Environment template

## Pro Tips

1. **After major updates**, always run:
   ```bash
   ./manage_sting.sh sync-config
   ```

2. **Check what changed** before updating:
   ```bash
   git status
   # If you see changes in /scripts or /conf, use sync-config
   ```

3. **For production**, create an update script:
   ```bash
   #!/bin/bash
   ./manage_sting.sh update app frontend
   ./manage_sting.sh sync-config
   ./manage_sting.sh restart
   ```

## Troubleshooting

### "Script not found" or "Old behavior persists"
- You probably need to run `sync-config`
- Scripts in `~/.sting-ce/scripts/` might be outdated

### "Configuration not applying"
- Run `sync-config` then restart affected services
- Check that files were actually copied to `~/.sting-ce/`

### "Password or security settings reverting"
- Critical sign that scripts weren't synced
- Run `sync-config` immediately