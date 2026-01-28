# Docker Resource Optimization for STING

## Resource Allocation Strategy

STING's Docker architecture is optimized for efficient resource utilization on systems meeting the 16GB minimum requirement.

### Current Optimized Allocations

```yaml
# Knowledge Service (Increased for better performance)
knowledge:
  limits: 3GB memory, 1.5 CPU
  reserved: 1GB memory

# ChromaDB (Vector operations need dedicated resources)  
chroma:
  limits: 2GB memory, 1.0 CPU
  reserved: 512MB memory

# Core Services
app: 1GB memory, 1.0 CPU
database: 1GB memory, 1.0 CPU
frontend: 512MB memory, 0.5 CPU

# Supporting Services  
vault: 512MB memory, 0.25 CPU
messaging: 256MB memory, 0.25 CPU
redis: 512MB memory, 0.5 CPU
```

### Memory Usage Distribution
- **Total Reserved**: ~4GB (25% of 16GB)
- **Total Limits**: ~12GB (75% of 16GB) 
- **System Buffer**: 4GB for OS and other processes

## Performance Optimizations

### Knowledge Service Enhancements
- **Increased Memory**: From 2GB to 3GB for better embedding caching
- **CPU Boost**: From 1.0 to 1.5 cores for parallel document processing
- **Background Processing**: Queue-based uploads prevent memory spikes

### ChromaDB Vector Database
- **Dedicated Resources**: 2GB ensures smooth vector operations
- **Embedding Model**: `all-MiniLM-L6-v2` chosen for efficiency
- **Index Optimization**: Automatic index building for sub-second search

### Container Health Monitoring
All services now have resource limits to prevent runaway processes:
- **Frontend**: Previously unlimited, now 512MB
- **Vault**: Previously unlimited, now 512MB  
- **Messaging**: Previously unlimited, now 256MB

## Scaling Recommendations

### When to Increase Resources

**Knowledge Service (3GB → 4GB)**
- Processing >1000 documents daily
- Multiple concurrent users uploading
- Complex document formats (large PDFs)

**ChromaDB (2GB → 3GB)** 
- Vector database >10,000 documents
- Frequent similarity searches
- Multiple knowledge bases active

**App Container (1GB → 2GB)**
- >20 concurrent users
- Heavy API usage patterns
- Multiple background jobs

### Horizontal Scaling Options

**Separate ChromaDB Instance**
```yaml
# For deployments >50k documents
chroma-production:
  image: chromadb/chroma:latest
  resources:
    limits: 8GB memory, 4.0 CPU
  volumes:
    - chroma-production:/chroma/chroma
```

**Knowledge Worker Scaling**
```yaml
# Separate knowledge processing workers
knowledge-worker-1:
  build: ./knowledge_service
  environment:
    - WORKER_MODE=true
    - WORKER_QUEUE=document_processing
```

## Troubleshooting Resource Issues

### Common Symptoms
- **Slow search responses**: Increase ChromaDB memory
- **Upload timeouts**: Increase knowledge service resources  
- **Container restarts**: Check memory limits vs usage
- **High swap usage**: Enable Docker resource limits

### Monitoring Commands
```bash
# Check container resource usage
docker stats --no-stream

# Monitor specific service
docker stats sting-ce-knowledge --no-stream

# Check memory pressure
docker exec sting-ce-knowledge cat /proc/meminfo

# View resource limits
docker inspect sting-ce-knowledge | grep -A 10 "Memory"
```

### Performance Tuning
```yaml
# Example production optimization
knowledge:
  deploy:
    resources:
      limits:
        memory: 4G        # Increased from 3G
        cpus: '2.0'       # Increased from 1.5
      reservations: 
        memory: 2G        # Increased from 1G
  environment:
    - WORKER_THREADS=4    # Parallel processing
    - CHUNK_BATCH_SIZE=50 # Optimize chunking
    - EMBEDDING_CACHE_SIZE=1000 # Cache embeddings
```

This optimized allocation ensures STING runs efficiently on minimum specification systems while providing clear upgrade paths for growth.