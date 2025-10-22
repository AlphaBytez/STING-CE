# STING Queuing Architecture & Memory Optimization

## 🚦 Current Memory Limits Applied

All services now have memory limits to prevent swap usage:

| Service | Memory Limit | CPU Limit | Purpose |
|---------|-------------|-----------|---------|
| **PostgreSQL** | 1GB | 1.0 | Database with optimized settings |
| **Redis** | 512MB | 0.5 | Caching & job queues |
| **Vault** | 512MB | 0.5 | Secrets management |
| **Kratos** | 512MB | 0.5 | Authentication |
| **App (Flask)** | 1GB | 1.0 | Backend API |
| **Frontend** | 1GB | 1.0 | React development server |
| **Messaging** | 1GB | 1.0 | Message queuing service |
| **Chatbot** | 3GB | 2.0 | phi3 model hosting |
| **LLM Gateway** | 6GB | 4.0 | Model management |
| **Knowledge** | 3GB | 2.0 | Vector database processing |
| **Chroma** | 2GB | 1.0 | Vector storage |

**Total Memory Budget: ~20GB** (vs unlimited before)

## 🔄 Current Queuing Infrastructure

### Already Implemented:
1. **Redis** - Job queue backend (optimized for LRU caching)
2. **Messaging Service** - Custom message processing
3. **PostgreSQL** - Message persistence and storage

### Redis Configuration:
```yaml
REDIS_MAXMEMORY: 512mb
REDIS_MAXMEMORY_POLICY: allkeys-lru
REDIS_SAVE: "900 1 300 10 60 10000"  # Optimized persistence
```

## 🚀 Recommended Queue Enhancements

### 1. Background Job Processing
Add Celery for distributed task processing:

```yaml
# Add to docker-compose.yml
celery-worker:
  build:
    context: .
    dockerfile: ./workers/Dockerfile.celery
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/1
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 256M
  depends_on:
    - redis
    - db
```

### 2. Queue Types Needed:

#### **High Priority Queues:**
- **Chat Processing** - Real-time user interactions
- **Model Loading** - phi3 initialization and warm-up
- **Knowledge Ingestion** - Document processing for Honey Pots

#### **Medium Priority Queues:**
- **Embedding Generation** - Vector creation for search
- **System Maintenance** - Cleanup and optimization tasks
- **Notification Dispatch** - User alerts and updates

#### **Low Priority Queues:**
- **Analytics Processing** - Usage statistics and reporting
- **Backup Operations** - Data persistence tasks
- **Audit Log Processing** - Security and compliance logging

### 3. Task Distribution Strategy:

```python
# Example queue configuration
CELERY_ROUTES = {
    'chat.process_message': {'queue': 'high_priority'},
    'knowledge.process_document': {'queue': 'medium_priority'},
    'analytics.generate_report': {'queue': 'low_priority'},
    'models.load_phi3': {'queue': 'high_priority'},
    'embeddings.generate_batch': {'queue': 'medium_priority'},
}
```

## 📊 Queue Monitoring & Management

### 1. Queue Health Monitoring:
```bash
# Redis queue monitoring
redis-cli info replication
redis-cli llen high_priority_queue
redis-cli llen medium_priority_queue
redis-cli llen low_priority_queue
```

### 2. Worker Scaling:
```yaml
# Scale workers based on queue depth
celery-worker:
  deploy:
    replicas: 3  # Start with 3 workers
    restart_policy:
      condition: on-failure
    update_config:
      parallelism: 1
      delay: 10s
```

### 3. Queue Persistence:
```yaml
# Redis persistence for job reliability
redis:
  environment:
    - REDIS_APPENDONLY=yes
    - REDIS_APPENDFSYNC=everysec
    - REDIS_AUTO_AOF_REWRITE_PERCENTAGE=100
```

## 🔧 Performance Optimizations

### Memory Management:
1. **Queue Size Limits** - Prevent memory exhaustion
2. **Job TTL** - Auto-expire old jobs
3. **Result Cleanup** - Remove completed job results
4. **Memory Monitoring** - Alert on high memory usage

### Redis Optimizations:
```bash
# Redis memory optimization commands
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET tcp-keepalive 60
CONFIG SET timeout 300
```

### PostgreSQL Queue Tables:
```sql
-- Efficient job queue table
CREATE TABLE job_queue (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_job_queue_status ON job_queue(status, priority);
CREATE INDEX idx_job_queue_created ON job_queue(created_at);
```

## 🎯 Next Steps for Queue Implementation

### Phase 1: Basic Queue Setup
1. Add Celery worker containers
2. Configure Redis for job persistence
3. Implement basic task routing

### Phase 2: Advanced Features
1. Dead letter queues for failed jobs
2. Job retry mechanisms with exponential backoff
3. Queue monitoring dashboard

### Phase 3: Enterprise Features
1. Multi-tenant queue isolation
2. Job scheduling and cron-like tasks
3. Queue metrics and alerting

## 🔍 Queue Use Cases for STING

### Immediate Needs:
- **Document Processing** - Honey Jar ingestion pipeline
- **Model Management** - phi3 loading and optimization
- **User Notifications** - Real-time alerts

### Future Scaling:
- **Multi-user Chat** - Concurrent Bee conversations
- **Batch Processing** - Large document collections
- **Enterprise Integration** - LDAP/SAML sync jobs

## 📈 Memory vs Performance Trade-offs

With the new memory limits:
- **Benefit**: No more 40GB swap usage
- **Trade-off**: May need smarter queue management
- **Solution**: Efficient job batching and prioritization

The queue system becomes more important with memory constraints since we need to:
1. Process jobs efficiently without memory spikes
2. Batch operations to reduce memory overhead
3. Clean up completed jobs promptly