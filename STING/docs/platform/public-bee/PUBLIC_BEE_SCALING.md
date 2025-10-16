# Public Bee Scaling Guide

**Scaling AI-as-a-Service for High Volume & Enterprise Deployment**

## Overview

This guide covers scaling the Public Bee service from development/demo usage to production-ready, high-volume deployment. Whether you're serving hundreds or millions of conversations, this guide provides the architecture patterns and configurations needed.

## Scaling Tiers

### 🐝 Small Hive (1-100 conversations/day)
- **Use Case**: Small businesses, demos, proof of concepts
- **Architecture**: Single container, default configuration
- **Resources**: 512MB RAM, 0.5 CPU cores
- **Storage**: Local filesystem for logs
- **Suitable for**: Testing, small customer support teams

### 🐝🐝 Medium Hive (100-10,000 conversations/day)  
- **Use Case**: Growing businesses, departmental deployment
- **Architecture**: Dedicated service containers, Redis caching
- **Resources**: 2GB RAM, 2 CPU cores
- **Storage**: Persistent volumes, log aggregation
- **Features**: Analytics, multiple bots, API rate limiting

### 🐝🐝🐝 Large Hive (10,000+ conversations/day)
- **Use Case**: Enterprise deployment, multi-tenant SaaS
- **Architecture**: Microservices, load balancing, auto-scaling
- **Resources**: Horizontal scaling, managed databases
- **Storage**: Cloud storage, CDN, distributed caching
- **Features**: Advanced analytics, white-labeling, SLA monitoring

## Architecture Patterns

### Single Instance (Small Hive)

```
┌─────────────┐
│   Frontend  │
├─────────────┤
│ Public Bee  │
│   Service   │
├─────────────┤
│  Knowledge  │
│   Service   │ 
├─────────────┤
│ PostgreSQL  │
└─────────────┘
```

**Configuration:**
```yaml
public_bee:
  enabled: true
  port: 8092
  workers: 2
  rate_limit: 100  # requests per hour
  
resources:
  memory: 512M
  cpu: 0.5
```

### Load Balanced (Medium Hive)

```
┌─────────────┐
│ Load        │
│ Balancer    │
└─────┬───────┘
      │
   ┌──▼──┐  ┌──────┐  ┌──────┐
   │ PB1 │  │ PB2  │  │ PB3  │
   └─────┘  └─────┘   └─────┘
      │        │         │
   ┌──▼────────▼─────────▼──┐
   │      Redis Cache      │
   └───────────┬───────────┘
               │
   ┌───────────▼───────────┐
   │    PostgreSQL HA      │
   └───────────────────────┘
```

**Configuration:**
```yaml
public_bee:
  enabled: true
  replicas: 3
  port: 8092
  workers: 4
  rate_limit: 1000
  
redis:
  enabled: true
  cluster_mode: false
  memory: 1GB
  
postgres:
  enabled: true
  replicas: 2  # Primary + replica
  memory: 4GB
```

### Microservices (Large Hive)

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│   API       │   │   Chat       │   │  Analytics  │
│  Gateway    │◄──│   Service    │◄──│   Service   │
└─────┬───────┘   └──────┬───────┘   └─────────────┘
      │                  │
   ┌──▼──────────────────▼──┐
   │   Message Queue      │
   │   (Redis/RabbitMQ)   │
   └─────────┬──────────────┘
             │
   ┌─────────▼──────────┐
   │   Knowledge        │
   │   Processing       │
   │   Workers          │
   └────────┬───────────┘
            │
   ┌────────▼────────┐
   │   Vector DB     │
   │   (Chroma)      │
   └─────────────────┘
```

## LangChain Integration

### Enable LangChain Service

For advanced conversation management and memory:

```yaml
# conf/config.yml
langchain_service:
  enabled: true
  port: 8093
  model_provider: "ollama"
  memory_type: "buffer"
  
public_bee:
  integrations:
    use_langchain: true
    langchain_url: "http://langchain:8093"
```

### LangChain Features
- **Conversation Memory**: Persistent context across messages
- **Chain Management**: Complex multi-step reasoning
- **Agent Capabilities**: Tool usage and function calling
- **Vector Store**: Efficient semantic search
- **Prompt Templates**: Consistent response formatting

### Docker Compose Addition

```yaml
langchain-service:
  container_name: sting-ce-langchain
  build:
    context: ./langchain_service
    dockerfile: Dockerfile
  environment:
    - LANGCHAIN_PORT=8093
    - MODEL_PROVIDER=ollama
    - OLLAMA_URL=http://external-ai:8091
    - CHROMA_URL=http://chroma:8000
  ports:
    - "8093:8093"
  networks:
    sting_local:
      aliases:
        - langchain
  depends_on:
    external-ai:
      condition: service_healthy
    chroma:
      condition: service_healthy
```

## Performance Optimization

### Database Optimization

#### Connection Pooling
```python
# public_bee/models.py
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_timeout': 30,
    'pool_recycle': 3600
}
```

#### Indexing Strategy
```sql
-- Performance indexes for Public Bee
CREATE INDEX idx_public_bot_usage_timestamp ON public_bot_usage(timestamp);
CREATE INDEX idx_public_bots_status ON public_bots(status) WHERE status = 'active';
CREATE INDEX idx_conversations_bot_session ON conversations(bot_id, session_id);
```

### Caching Strategy

#### Redis Configuration
```yaml
redis:
  enabled: true
  memory: 2GB
  maxmemory_policy: allkeys-lru
  
public_bee:
  cache:
    enabled: true
    default_ttl: 3600  # 1 hour
    conversation_ttl: 86400  # 24 hours
    knowledge_ttl: 7200  # 2 hours
```

#### Cache Implementation
```python
# Cache frequently requested knowledge
@cache_result(ttl=7200)
def get_knowledge_context(query, honey_jar_ids):
    return knowledge_service.search(query, honey_jar_ids)

# Cache bot configurations
@cache_result(ttl=3600)
def get_bot_config(bot_id):
    return bot_manager.get_bot(bot_id)
```

### Response Time Optimization

#### Async Processing
```python
# public_bee/app.py
import asyncio
from fastapi import FastAPI
from asyncio import gather

async def process_message_async(message, bot_config):
    # Parallel processing of knowledge retrieval and AI inference
    knowledge_task = get_knowledge_context_async(message, bot_config.honey_jars)
    ai_task = generate_response_async(message, bot_config)
    
    knowledge, ai_response = await gather(knowledge_task, ai_task)
    return combine_response(knowledge, ai_response)
```

#### Streaming Responses
```javascript
// Frontend streaming implementation
const response = await fetch('/api/public/chat/bot-id/message', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: userInput, stream: true})
});

const reader = response.body.getReader();
let accumulated = '';

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  accumulated += new TextDecoder().decode(value);
  displayIncrementalResponse(accumulated);
}
```

## High Availability Setup

### Multi-Region Deployment

```yaml
# docker-compose.production.yml
services:
  public-bee-primary:
    image: sting/public-bee:latest
    environment:
      - REGION=us-east-1
      - DATABASE_URL=postgresql://primary.db.region1
    deploy:
      replicas: 3
      
  public-bee-secondary:
    image: sting/public-bee:latest
    environment:
      - REGION=us-west-2
      - DATABASE_URL=postgresql://replica.db.region2
    deploy:
      replicas: 2
```

### Health Monitoring

```yaml
# healthcheck configuration
healthcheck:
  test: |
    curl -f http://localhost:8092/health &&
    curl -f http://localhost:8092/api/public/health/deep
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Auto-Scaling Configuration

```yaml
# Kubernetes HPA example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: public-bee-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: public-bee
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Security at Scale

### API Rate Limiting

#### Advanced Rate Limiting
```python
# Multiple rate limiting tiers
RATE_LIMITS = {
    'basic': {'requests': 100, 'window': 3600, 'burst': 10},
    'pro': {'requests': 1000, 'window': 3600, 'burst': 50},
    'enterprise': {'requests': 10000, 'window': 3600, 'burst': 100}
}

# Distributed rate limiting with Redis
@rate_limit(key="api_key:{api_key}", limit="1000/hour")
async def chat_endpoint(request):
    pass
```

#### DDoS Protection
```nginx
# nginx.conf for Public Bee
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $http_x_api_key zone=apikey:10m rate=100r/s;
    
    server {
        location /api/public/ {
            limit_req zone=api burst=20 nodelay;
            limit_req zone=apikey burst=50 nodelay;
            proxy_pass http://public-bee-backend;
        }
    }
}
```

### Content Security

#### Advanced PII Detection
```python
# Enhanced PII filtering for scale
PII_CONFIG = {
    'profiles': {
        'strict': ['ssn', 'credit_card', 'email', 'phone', 'address'],
        'moderate': ['ssn', 'credit_card'],
        'minimal': ['credit_card']
    },
    'custom_patterns': {
        'employee_id': r'EMP\d{6}',
        'customer_id': r'CUST\d{8}'
    }
}
```

## Monitoring & Analytics

### Metrics Collection

#### Prometheus Metrics
```python
# public_bee/metrics.py
from prometheus_client import Counter, Histogram, Gauge

message_total = Counter('public_bee_messages_total', 'Total messages processed', ['bot_id', 'status'])
response_time = Histogram('public_bee_response_time_seconds', 'Response time', ['bot_id'])
active_sessions = Gauge('public_bee_active_sessions', 'Active sessions', ['bot_id'])

@metrics_middleware
async def process_message(message, bot_id):
    start_time = time.time()
    try:
        response = await generate_response(message, bot_id)
        message_total.labels(bot_id=bot_id, status='success').inc()
        return response
    except Exception as e:
        message_total.labels(bot_id=bot_id, status='error').inc()
        raise
    finally:
        response_time.labels(bot_id=bot_id).observe(time.time() - start_time)
```

#### Custom Analytics Dashboard
```yaml
# Grafana dashboard for Public Bee
grafana:
  dashboards:
    public_bee:
      panels:
        - messages_per_second
        - response_time_percentiles
        - active_bots_count
        - error_rate_by_bot
        - knowledge_source_usage
        - customer_satisfaction_scores
```

### Alerting

```yaml
# Alert rules
alerts:
  - name: high_error_rate
    condition: error_rate > 5%
    duration: 5m
    notification: slack_webhook
    
  - name: slow_responses
    condition: p95_response_time > 5s
    duration: 2m
    notification: pager_duty
    
  - name: high_memory_usage
    condition: memory_usage > 90%
    duration: 1m
    notification: email
```

## Cost Optimization

### Resource Management

#### Intelligent Scaling
```python
# Auto-scaling based on conversation patterns
SCALING_RULES = {
    'business_hours': {'min_replicas': 5, 'max_replicas': 20},
    'off_hours': {'min_replicas': 2, 'max_replicas': 10},
    'weekend': {'min_replicas': 1, 'max_replicas': 5}
}

def get_current_scaling_profile():
    now = datetime.now()
    if now.weekday() >= 5:  # Weekend
        return SCALING_RULES['weekend']
    elif 9 <= now.hour <= 17:  # Business hours
        return SCALING_RULES['business_hours']
    else:
        return SCALING_RULES['off_hours']
```

#### Storage Optimization
```python
# Intelligent conversation cleanup
CLEANUP_POLICY = {
    'inactive_sessions': {'delete_after': '7d'},
    'low_value_conversations': {'archive_after': '30d'},
    'analytics_data': {'aggregate_after': '90d'}
}
```

## Enterprise Features

### Multi-Tenancy

```python
# Tenant isolation
@require_tenant_access
async def get_bot_config(bot_id: str, tenant_id: str):
    return bot_manager.get_bot(bot_id, tenant_filter=tenant_id)

# Tenant-specific rate limits
@rate_limit(key="tenant:{tenant_id}", limit="tenant_limit")
async def chat_endpoint(tenant_id: str):
    pass
```

### White Labeling

```yaml
# Tenant-specific branding
tenants:
  acme_corp:
    branding:
      primary_color: "#ff6600"
      logo_url: "https://cdn.acme.com/logo.png"
      domain: "chat.acme.com"
    features:
      analytics: true
      custom_models: true
      
  beta_inc:
    branding:
      primary_color: "#0066cc"
      domain: "support.beta.com"
    features:
      analytics: false
      custom_models: false
```

### Enterprise SLA Monitoring

```python
# SLA tracking and enforcement
SLA_TARGETS = {
    'response_time': {'p95': 2.0, 'p99': 5.0},  # seconds
    'availability': {'uptime': 99.9},  # percentage
    'accuracy': {'satisfaction': 4.0}  # out of 5
}

@track_sla
async def process_enterprise_request(request):
    # Priority processing for enterprise customers
    pass
```

## Migration Strategies

### Zero-Downtime Deployment

```bash
# Blue-Green deployment script
#!/bin/bash

# Deploy new version to standby environment
docker-compose -f docker-compose.green.yml up -d public-bee

# Health check new deployment
wait_for_healthy "green-public-bee"

# Switch traffic
nginx_switch_upstream "green"

# Verify traffic switch
verify_traffic_routing

# Shutdown old version
docker-compose -f docker-compose.blue.yml down public-bee
```

### Data Migration

```python
# Conversation data migration
async def migrate_conversation_data():
    """Migrate conversations to new schema"""
    batch_size = 1000
    offset = 0
    
    while True:
        conversations = await get_conversations_batch(offset, batch_size)
        if not conversations:
            break
            
        migrated = [migrate_conversation_schema(c) for c in conversations]
        await save_migrated_conversations(migrated)
        
        offset += batch_size
        await asyncio.sleep(0.1)  # Rate limiting
```

## Troubleshooting at Scale

### Performance Issues

#### Identify Bottlenecks
```bash
# Database query analysis
psql -d sting_app -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"

# Memory usage per container
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Response time analysis
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8092/api/public/chat/bot/message"
```

#### Load Testing
```bash
# Artillery.js load test
artillery run --target https://sting.example.com:8092 load-test.yml

# load-test.yml
config:
  target: 'https://sting.example.com:8092'
  phases:
    - duration: 300
      arrivalRate: 10
      name: "Warm up"
    - duration: 600
      arrivalRate: 50
      name: "Peak load"
scenarios:
  - name: "Chat flow"
    requests:
      - post:
          url: "/api/public/chat/support-bot/message"
          headers:
            X-API-Key: "{{ $randomString() }}"
          json:
            message: "How do I install STING?"
            session_id: "load-test-{{ $randomString() }}"
```

### Common Issues & Solutions

#### High Memory Usage
- **Symptom**: OOM kills, slow responses
- **Solution**: Implement conversation cleanup, optimize caching
- **Prevention**: Set memory limits, monitor usage patterns

#### Database Connection Pool Exhaustion
- **Symptom**: Connection timeout errors
- **Solution**: Increase pool size, implement connection retry
- **Prevention**: Monitor active connections, use read replicas

#### Knowledge Service Latency
- **Symptom**: Slow knowledge retrieval
- **Solution**: Implement semantic caching, pre-compute embeddings
- **Prevention**: Optimize vector search indexes

## Success Metrics

### Technical Metrics
- **Response Time**: P95 < 2 seconds, P99 < 5 seconds
- **Throughput**: 10,000+ messages/minute
- **Availability**: 99.9% uptime
- **Error Rate**: < 0.1%

### Business Metrics
- **Customer Satisfaction**: > 4.0/5.0
- **Deflection Rate**: > 80% of queries resolved without human
- **Usage Growth**: Month-over-month conversation volume
- **Revenue Impact**: Cost savings vs. human support

---

**Ready to scale your Public Bee deployment?** Start with the tier that matches your current needs and follow this guide to grow your AI-as-a-Service platform! 🚀🐝