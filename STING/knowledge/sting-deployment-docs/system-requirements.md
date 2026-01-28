# STING Hardware & System Requirements

## Minimum System Requirements

### Hardware Specifications
- **Memory**: 16GB RAM minimum
- **CPU**: 8+ cores (Apple M1/M2/M3 or Intel/AMD)
- **Storage**: 50GB free disk space (SSD recommended)
- **Network**: Internet connection for initial setup

### Operating System Support
- **macOS**: 11+ (Apple Silicon recommended)
- **Linux**: Ubuntu 20.04+ or CentOS 8+
- **Docker**: Docker Desktop 4.0+ with Docker Compose

## Recommended Configurations

### Small Deployment (1-5 users, <1000 documents)
- **Memory**: 16GB RAM
- **Storage**: 100GB SSD
- **Network**: 100 Mbps connection
- **Estimated Resource Usage**: 75% of available RAM

### Medium Deployment (5-20 users, 1000-10000 documents) 
- **Memory**: 32GB RAM
- **Storage**: 250GB SSD
- **Network**: 1 Gbps connection
- **Additional**: Dedicated ChromaDB instance

### Large Deployment (20+ users, 10000+ documents)
- **Memory**: 64GB+ RAM
- **Storage**: 500GB+ SSD (NVMe preferred)
- **Network**: 10 Gbps connection
- **Additional**: Redis cluster, separate knowledge workers

## Resource Allocation Guidelines

### Docker Container Limits (Optimized for 16GB)
- **Knowledge Service**: 3GB memory, 1.5 CPU
- **ChromaDB**: 2GB memory, 1.0 CPU  
- **App Container**: 1GB memory, 1.0 CPU
- **Database**: 1GB memory, 1.0 CPU
- **Frontend**: 512MB memory, 0.5 CPU

### Memory Usage Breakdown
- **System Reserved**: 4GB (OS and other processes)
- **STING Services**: 12GB (optimized allocation)
- **Total Utilization**: 75% of 16GB minimum requirement

## Performance Considerations

### ChromaDB Optimization
- Uses `all-MiniLM-L6-v2` model (90MB, 384 dimensions)
- Efficient for semantic search with minimal memory overhead
- Scales well with document volume up to 100k documents

### Knowledge Processing
- **Document Chunking**: 1000-1500 characters with overlap
- **Background Processing**: Queue-based for large uploads
- **Incremental Updates**: Only process changed documents

## Monitoring & Alerts

### Resource Monitoring
- Container memory usage should not exceed 85% of limits
- CPU utilization should average <70% during normal operation  
- Disk usage for knowledge storage grows ~1MB per document

### Performance Metrics
- **Search Response Time**: <2 seconds for most queries
- **Document Upload**: <30 seconds per 10MB file
- **Bee Response Time**: <5 seconds with knowledge context