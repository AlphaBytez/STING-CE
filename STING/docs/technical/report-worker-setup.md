# Report Worker Setup Guide

## Overview

The Report Worker is a background service that processes report generation jobs from the queue. It connects to the Redis queue, fetches pending report jobs, generates the reports using the configured templates, and saves the results.

## Service Configuration

### Docker Compose Service Definition

Add the following service definition to your `docker-compose.yml`:

```yaml
  report-worker:
    container_name: sting-ce-report-worker
    build:
      context: .
      dockerfile: report_worker/Dockerfile
    env_file:
      - ${INSTALL_DIR}/env/app.env
      - ${INSTALL_DIR}/env/db.env
    environment:
      - WORKER_ID=report-worker-1
      - REDIS_URL=redis://redis:6379/0
      - REPORT_QUEUE_NAME=sting:reports
      - REPORT_MAX_PROCESSING_TIME=1800
      - REPORT_MAX_RETRIES=3
    volumes:
      - ./conf:/app/conf:ro
      - report_worker_logs:/var/log/report-worker
    networks:
      sting_local:
        aliases:
          - report-worker
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy
      app:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
    restart: unless-stopped
    profiles:
      - full
      - report-system
```

### Volume Definition

Add the report worker logs volume:

```yaml
volumes:
  report_worker_logs:
    driver: local
```

## Running the Report Worker

### Starting the Service

```bash
# Start the report worker
docker compose --profile report-system up -d report-worker

# Check worker status
docker compose ps report-worker

# View worker logs
docker compose logs -f report-worker
```

### Scaling Workers

You can run multiple workers for increased throughput:

```bash
# Scale to 3 workers
docker compose up -d --scale report-worker=3
```

## Manual Testing

### Running the Worker Locally

For development and testing, you can run the worker locally:

```bash
# From the project root
cd /path/to/sting
python scripts/run_report_worker.py
```

### Environment Variables

Set these environment variables for local testing:

```bash
export DATABASE_URL="postgresql://postgres:password@localhost:5433/sting_app"
export REDIS_URL="redis://localhost:6379/0"
export REPORT_QUEUE_NAME="sting:reports"
export WORKER_ID="local-worker"
```

## Report Generation Flow

1. **User requests report** via the frontend
2. **API creates report record** in database with status `pending`
3. **Report service queues job** in Redis with priority
4. **Worker picks up job** from queue
5. **Worker processes report**:
   - Loads template configuration
   - Collects data from database
   - Applies PII scrubbing if enabled
   - Generates output file (PDF/Excel/CSV)
   - Uploads to file storage
6. **Worker updates report status** to `completed`
7. **User downloads report** via API

## Monitoring

### Queue Status

Check the report queue status:

```bash
# Using Redis CLI
docker exec -it sting-ce-redis redis-cli
> ZCARD sting:reports
> HLEN sting:reports:processing
> HLEN sting:reports:failed
```

### Worker Health

Monitor worker health and performance:

```bash
# Check worker container health
docker inspect sting-ce-report-worker | jq '.[0].State.Health'

# View worker metrics
docker stats sting-ce-report-worker
```

## Troubleshooting

### Common Issues

1. **Worker not picking up jobs**
   - Check Redis connectivity
   - Verify queue name matches configuration
   - Check worker logs for errors

2. **Reports failing**
   - Check database connectivity
   - Verify file service is accessible
   - Check for PII scrubbing errors
   - Review worker logs for stack traces

3. **Memory issues**
   - Adjust memory limits in docker-compose
   - Monitor large report generation
   - Consider pagination for large datasets

### Debug Mode

Enable debug logging:

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

## Adding New Report Templates

1. **Create generator class** in `app/workers/report_generators.py`
2. **Register in worker** mapping in `report_worker.py`
3. **Add template** via `init_report_templates.py`
4. **Test generation** with sample data

Example generator:

```python
class CustomReportGenerator(BaseReportGenerator):
    async def collect_data(self) -> Dict[str, Any]:
        # Implement data collection
        pass
    
    async def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implement data processing
        pass
```

## Performance Tuning

### Redis Configuration

Optimize Redis for job queue performance:

```yaml
redis:
  command: >
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save ""
```

### Worker Configuration

Adjust worker parameters:

- `REPORT_MAX_PROCESSING_TIME`: Maximum time for a single report (default: 1800s)
- `REPORT_MAX_RETRIES`: Retry attempts for failed reports (default: 3)
- Worker count: Scale based on CPU cores and report volume

### Database Optimization

- Add indexes for frequently queried fields
- Use query optimization for large datasets
- Consider materialized views for complex reports