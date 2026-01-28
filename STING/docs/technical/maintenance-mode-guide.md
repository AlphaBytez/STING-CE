# Maintenance Mode Guide

## Overview

STING includes a comprehensive Maintenance Window System that allows administrators to gracefully take the platform offline for updates, migrations, or scheduled maintenance. The system provides:

- **Full-page maintenance screen** for unauthenticated users
- **CLI commands** for quick enable/disable via terminal
- **Admin UI panel** for scheduled maintenance with custom messages
- **Redis-backed state** for distributed deployments
- **Automatic recovery** when maintenance ends

---

## Quick Reference

### CLI Commands

```bash
# Enable maintenance mode immediately
sudo msting maintenance on

# Enable with custom message
sudo msting maintenance on --message "Upgrading database. Back in 30 minutes."

# Enable with scheduled end time
sudo msting maintenance on --end "2026-01-21 15:00:00"

# Disable maintenance mode
sudo msting maintenance off

# Check current status
sudo msting maintenance status
```

### API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/system/maintenance/status` | GET | Public | Check maintenance status |
| `/api/admin/maintenance/enable` | POST | Admin | Enable maintenance mode |
| `/api/admin/maintenance/disable` | POST | Admin | Disable maintenance mode |
| `/api/admin/maintenance/schedule` | POST | Admin | Schedule maintenance window |

---

## Detailed Usage

### Enabling Maintenance Mode

#### Via CLI (Recommended for Operations)

```bash
# Basic enable - uses default message
sudo msting maintenance on

# With custom message
sudo msting maintenance on --message "System update in progress. Expected completion: 3:00 PM EST"

# With scheduled end time (ISO format or natural language)
sudo msting maintenance on --end "2026-01-21T15:00:00Z"
sudo msting maintenance on --end "in 2 hours"

# Combine both
sudo msting maintenance on \
  --message "Database migration in progress" \
  --end "2026-01-21 16:00:00"
```

#### Via Admin Panel

1. Navigate to **Admin Panel** → **System Management** → **Maintenance**
2. Click **Enable Maintenance Mode**
3. (Optional) Set custom message and end time
4. Click **Confirm**

#### Via API

```bash
# Enable with defaults
curl -X POST https://localhost/api/admin/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION" \
  -d '{}'

# Enable with options
curl -X POST https://localhost/api/admin/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION" \
  -d '{
    "message": "Scheduled maintenance in progress",
    "end_time": "2026-01-21T15:00:00Z",
    "initiated_by": "admin@example.com"
  }'
```

### Disabling Maintenance Mode

```bash
# Via CLI
sudo msting maintenance off

# Via API
curl -X POST https://localhost/api/admin/maintenance/disable \
  -H "Cookie: ory_kratos_session=YOUR_SESSION"
```

### Checking Status

```bash
# Via CLI
sudo msting maintenance status

# Via API (no auth required)
curl -s https://localhost/api/system/maintenance/status | jq .
```

**Example response:**
```json
{
  "maintenance_mode": true,
  "status": "maintenance",
  "message": "System update in progress",
  "end_time": "2026-01-21T15:00:00Z",
  "started_at": "2026-01-21T14:00:00Z",
  "initiated_by": "admin@example.com"
}
```

---

## Best Practices

### Before Enabling Maintenance

1. **Notify users in advance** - Use the scheduled maintenance banner feature
2. **Complete pending operations** - Check for running reports, active chats
3. **Create a backup** - `sudo msting backup create`
4. **Document the reason** - Use meaningful maintenance messages

### During Maintenance

1. **Monitor logs** - `sudo msting logs --follow`
2. **Test changes** - Verify updates work before disabling maintenance
3. **Update status** - Keep the maintenance message current if delays occur

### After Maintenance

1. **Verify services** - `sudo msting status`
2. **Check health endpoints** - Ensure all services are healthy
3. **Test critical paths** - Login, chat, API responses
4. **Clear caches if needed** - `sudo msting cache clear`

---

## Scheduling Maintenance Windows

### Pre-Announced Maintenance

Schedule maintenance in advance to show users a warning banner:

```bash
# Schedule maintenance for tomorrow at 2 AM
curl -X POST https://localhost/api/admin/maintenance/schedule \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION" \
  -d '{
    "scheduled_start": "2026-01-22T02:00:00Z",
    "scheduled_end": "2026-01-22T04:00:00Z",
    "message": "Scheduled database maintenance"
  }'
```

Users will see a dismissable banner warning them about upcoming maintenance within 24 hours of the scheduled start time.

### Automatic Maintenance End

When an `end_time` is specified:
- The maintenance page shows a countdown timer
- When the time is reached, the system automatically checks if maintenance should end
- Admins can still manually end maintenance early

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ MaintenanceGate  │──│ MaintenancePage / Login Routes   │ │
│  └────────┬─────────┘  └──────────────────────────────────┘ │
│           │                                                  │
│           ▼ Checks /api/system/maintenance/status            │
├─────────────────────────────────────────────────────────────┤
│                        Backend                               │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Maintenance      │  │ System Routes                     │ │
│  │ Middleware       │──│ /api/system/maintenance/*         │ │
│  └────────┬─────────┘  └──────────────────────────────────┘ │
│           │                                                  │
│           ▼ 5-second cached state                            │
├─────────────────────────────────────────────────────────────┤
│                        Redis                                 │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Key: sting:maintenance:state                             ││
│  │ Value: {"enabled": true, "message": "...", ...}          ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### State Storage

Maintenance state is stored in Redis at key `sting:maintenance:state`:

```json
{
  "enabled": true,
  "message": "System maintenance in progress",
  "end_time": "2026-01-21T15:00:00Z",
  "started_at": "2026-01-21T14:00:00Z",
  "initiated_by": "admin@example.com"
}
```

### Frontend Behavior

1. **MaintenanceGate** component wraps all routes
2. On load, checks `/api/system/maintenance/status`
3. If `maintenance_mode: true`, renders `MaintenancePage` instead of normal routes
4. Re-checks every 30 seconds for status changes
5. When maintenance ends, automatically redirects to home

### Backend Behavior

1. **Middleware** checks maintenance state on protected API routes
2. Public routes (status endpoint, health checks) are always accessible
3. Admin routes bypass maintenance check (admins can still access during maintenance)
4. Returns HTTP 503 with `MAINTENANCE_MODE` code for blocked requests

---

## Troubleshooting

### Maintenance Mode Won't Enable

```bash
# Check Redis connectivity
sudo docker exec sting-ce-redis redis-cli ping

# Check maintenance state directly
sudo docker exec sting-ce-redis redis-cli GET "sting:maintenance:state"

# View backend logs
sudo msting logs app | grep -i maintenance
```

### Users Still Accessing During Maintenance

1. **Cache issue** - Clear browser cache or wait 30 seconds for frontend refresh
2. **CDN caching** - If using a CDN, purge the cache
3. **Direct API access** - Some API routes may still be accessible by design

### Maintenance Mode Stuck

```bash
# Force disable via Redis
sudo docker exec sting-ce-redis redis-cli DEL "sting:maintenance:state"

# Or via CLI
sudo msting maintenance off --force

# Restart frontend to clear cached state
sudo msting restart frontend
```

### Frontend Not Showing Maintenance Page

```bash
# Check API response
curl -s https://localhost/api/system/maintenance/status | jq .

# Verify frontend has latest code
sudo msting update frontend

# Check frontend logs
sudo msting logs frontend
```

---

## Integration with CI/CD

### Pre-Deployment Maintenance

```yaml
# Example GitHub Actions workflow
jobs:
  deploy:
    steps:
      - name: Enable Maintenance Mode
        run: |
          ssh production "sudo msting maintenance on --message 'Deploying v${{ github.ref_name }}'"
      
      - name: Deploy Application
        run: |
          ssh production "cd /opt/sting-ce && git pull && sudo msting update"
      
      - name: Verify Health
        run: |
          ssh production "sudo msting status"
      
      - name: Disable Maintenance Mode
        run: |
          ssh production "sudo msting maintenance off"
```

### Automated Maintenance Windows

```bash
# Cron job for weekly maintenance (Sundays at 2 AM)
0 2 * * 0 /usr/local/bin/msting maintenance on --message "Weekly maintenance" --end "$(date -d '+2 hours' --iso-8601=seconds)" && /usr/local/bin/msting upgrade && /usr/local/bin/msting maintenance off
```

---

## Related Documentation

- [System Architecture](../architecture/system-architecture.md)
- [Admin Panel Guide](./admin-feature-implementation-guide.md)
- [Upgrade Guide](../../UPGRADE.md)
- [CLI Reference](../../README.md#command-line-interface)

---

*Last Updated: January 2026*
