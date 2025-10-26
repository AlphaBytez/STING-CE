# Grafana Observability Integration

## Overview

STING-CE includes a comprehensive observability stack built on Grafana, Loki, and Promtail that provides real-time monitoring, log aggregation, and system analytics. The integration is designed to work seamlessly within the Beeacon observability framework.

## Architecture

### Components

- **Grafana 11.0.0**: Main dashboard and visualization platform
- **Loki 3.0.0**: Log aggregation and querying engine  
- **Promtail**: Log collection and forwarding agent
- **Log Forwarder**: Custom container log streaming service

### Network Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   STING App     │───▶│   Promtail      │───▶│     Loki        │
│   (Logs)        │    │  (Collector)    │    │ (Aggregation)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────────────────────────────┘
│  Log Forwarder  │    │
│ (Docker Logs)   │────┘    ┌─────────────────┐
└─────────────────┘          │    Grafana      │
                             │  (Dashboards)   │
┌─────────────────┐         └─────────────────┘
│  End User       │                  │
│  Dashboard      │◀─────────────────┘
└─────────────────┘
```

## Configuration

### Environment Variables

The observability stack is configured through `/env/observability.env`:

```bash
# Grafana Configuration
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=secure_password_here
GF_SECURITY_SECRET_KEY=grafana_secret_key_here
GF_SECURITY_ALLOW_EMBEDDING=true
GF_SECURITY_X_FRAME_OPTIONS=SAMEORIGIN

# Anonymous access for embedded dashboards
GF_AUTH_ANONYMOUS_ENABLED=true
GF_AUTH_ANONYMOUS_ORG_NAME=Main Org.
GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer

# Privacy settings
GF_ANALYTICS_REPORTING_ENABLED=false
GF_ANALYTICS_CHECK_FOR_UPDATES=false
GF_SNAPSHOTS_EXTERNAL_ENABLED=false
```

### Docker Compose Services

```yaml
grafana:
  container_name: sting-ce-grafana
  image: grafana/grafana:11.0.0
  ports:
    - "3001:3000"  # Avoid conflict with frontend
  volumes:
    - ./observability/grafana/config/grafana.ini:/etc/grafana/grafana.ini:ro
    - ./observability/grafana/provisioning:/etc/grafana/provisioning:ro
  networks:
    - sting_local

loki:
  container_name: sting-ce-loki  
  image: grafana/loki:3.0.0
  ports:
    - "3100:3100"
  volumes:
    - ./observability/loki/config/loki.yml:/etc/loki/loki.yml:ro
```

## Dashboard Integration

### Frontend Components

The main dashboard integration is handled by `/frontend/src/components/dashboard/EmbeddedGrafanaDashboard.jsx`:

```javascript
const EmbeddedGrafanaDashboard = ({ 
  dashboardId, 
  title, 
  timeRange = "5m",
  autoRefresh = "10s" 
}) => {
  const grafanaBaseUrl = "http://localhost:3001";
  
  // Workaround for X-Frame-Options restrictions
  const handleOpenDashboard = () => {
    window.open(`${grafanaBaseUrl}/d/${dashboardId}`, '_blank');
  };
  
  return (
    <div className="dashboard-widget">
      <button 
        onClick={handleOpenDashboard}
        className="interactive-dashboard-button"
      >
        Open {title} Dashboard
      </button>
    </div>
  );
};
```

### Available Dashboards

1. **System Overview** (`dashboard-id: system-overview`)
   - Service health status
   - Resource utilization
   - Active connections

2. **Log Analytics** (`dashboard-id: log-analytics`)  
   - Error rate trends
   - Log volume by service
   - Alert notifications

3. **Performance Metrics** (`dashboard-id: performance`)
   - Response times
   - Queue depths  
   - Memory/CPU usage

## X-Frame-Options Workaround

### The Problem

Grafana 11.0.0 introduced stricter Content Security Policy (CSP) and X-Frame-Options headers that prevent iframe embedding, even with `allow_embedding = true` configured.

### The Solution

Instead of broken iframe embedding, STING-CE uses interactive buttons that open dashboards in new tabs:

```javascript
// Instead of:
<iframe src={grafanaUrl} /> // ❌ Blocked by CSP

// We use:
<button onClick={() => window.open(grafanaUrl, '_blank')}>
  Open Dashboard
</button> // ✅ Works with security restrictions
```

### Configuration Attempts Made

We attempted several configuration approaches that did NOT work:

```ini
# grafana.ini - These settings were tried but ineffective
[security]
allow_embedding = true
cookie_samesite = none  
cookie_secure = false

[auth.anonymous]
enabled = true
org_role = Viewer
```

The issue persists due to Grafana's enhanced security model in version 11.0.0.

## Service Management

### Starting Observability Stack

```bash
# Start with specific profile
./manage_sting.sh start --profile observability

# Or start individual services
docker compose up -d grafana loki promtail
```

### Health Checks

```bash
# Check Grafana health
curl -f http://localhost:3001/api/health

# Check Loki health  
wget --no-verbose --tries=1 --spider http://localhost:3100/ready

# Check service logs
./manage_sting.sh logs grafana
./manage_sting.sh logs loki
./manage_sting.sh logs promtail
```

## Troubleshooting

### Dashboard Not Loading

**Symptoms:**
- Grafana service is healthy but dashboards show errors
- "Failed to fetch" errors in browser console

**Solution:**
```bash
# 1. Check Grafana container logs
./manage_sting.sh logs grafana

# 2. Verify configuration
docker exec sting-ce-grafana cat /etc/grafana/grafana.ini

# 3. Restart observability services
docker compose restart grafana loki
```

### Log Aggregation Issues

**Symptoms:**
- No logs appearing in Grafana dashboards
- Promtail showing connection errors

**Solution:**
```bash
# 1. Check Promtail configuration
./manage_sting.sh logs promtail

# 2. Verify Loki connectivity
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="promtail"}' \
  --data-urlencode 'limit=5'

# 3. Check log file permissions
docker exec sting-ce-promtail ls -la /var/log/sting/
```

### Embedding Security Errors

**Symptoms:**
- "Refused to display in a frame because it set 'X-Frame-Options' to 'DENY'"
- CSP violations in browser console

**Solution:**
This is expected behavior with Grafana 11.0.0. Use the button-based navigation instead of iframe embedding:

```javascript
// Use this pattern instead of iframes
const openDashboard = () => {
  window.open(`${grafanaBaseUrl}/d/${dashboardId}`, '_blank');
};
```

## Performance Considerations

### Resource Usage

```yaml
grafana:
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
      reservations:
        memory: 128M

loki:
  deploy:
    resources:
      limits:
        memory: 512M  
        cpus: '0.5'
      reservations:
        memory: 128M
```

### Log Retention

Loki is configured for 30-day log retention by default:

```yaml
# loki.yml
limits_config:
  retention_period: 720h  # 30 days
  
compactor:
  retention_enabled: true
  retention_delete_delay: 2h
```

## Security

### Access Control

- **Anonymous Read Access**: Enabled for embedded dashboards
- **Admin Access**: Protected by username/password stored in Vault
- **Network Isolation**: Services communicate on internal `sting_local` network

### Data Privacy

- Analytics and telemetry disabled
- External snapshots disabled  
- No data sent to Grafana Labs

## Integration with STING Components

### Beeacon Page

The observability integration is surfaced through the Beeacon page at `/dashboard/beeacon`:

- Real-time system status
- Interactive dashboard links
- Log search interface
- Alert management

### Alert Configuration

Alerts can be configured through Grafana's alerting system:

1. Navigate to http://localhost:3001/alerting
2. Create alert rules based on log patterns
3. Configure notification channels (email, Slack, etc.)
4. Test alert delivery

## Future Enhancements

### Planned Features

1. **Custom Metrics API**: Direct metrics extraction without Grafana UI
2. **Embedded Charts**: SVG-based chart generation for iframe-free embedding  
3. **Alert Integration**: Native STING alert management
4. **Mobile Dashboard**: Responsive observability interface

### API Integration

Future versions will include direct metric APIs:

```javascript
// Planned API endpoints
GET /api/metrics/system-health
GET /api/metrics/logs/search?query=error
GET /api/metrics/alerts/active
```

This will enable fully embedded observability without X-Frame-Options limitations.

---

**Note**: This integration provides production-ready observability for STING-CE deployments. The button-based dashboard navigation is a temporary workaround for Grafana 11.0.0 security restrictions and will be enhanced with direct API integration in future releases.