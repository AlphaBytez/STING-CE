# 🐝 Worker Bees Architecture

## Overview

Worker Bees are the backbone of STING's external data source integration system. They provide a scalable, secure framework for connecting to external data sources, processing data, and feeding it into the Honey Reserve and knowledge base ecosystem.

## Core Concepts

### Worker Bee Types

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Worker   │    │   API Worker    │    │ Stream Worker   │
│                 │    │                 │    │                 │
│ • Local Files   │    │ • REST APIs     │    │ • Real-time     │
│ • FTP/SFTP      │    │ • GraphQL       │    │ • Event streams │
│ • Network Drives│    │ • Webhooks      │    │ • Message Queue │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                         ┌─────────────────┐
                         │  Nectar System  │
                         │   (Processor)   │
                         └─────────────────┘
                                  │
                         ┌─────────────────┐
                         │  Honey Reserve  │
                         │ & Knowledge DB  │
                         └─────────────────┘
```

### Worker Bee Lifecycle

1. **Registration**: Worker Bee registers with the Hive Manager
2. **Configuration**: Data source credentials and connection parameters
3. **Scheduling**: Define sync frequency and data collection rules
4. **Execution**: Worker Bee runs data collection tasks
5. **Processing**: Nectar System processes collected data
6. **Storage**: Data stored in Honey Reserve or Knowledge Base
7. **Monitoring**: Health checks and performance metrics

## Architecture Components

### 1. Hive Manager (Central Orchestrator)

```python
class HiveManager:
    """Central orchestrator for all Worker Bees"""
    
    def register_worker(self, worker_type: str, config: Dict) -> str:
        """Register a new Worker Bee"""
        
    def schedule_job(self, worker_id: str, schedule: str) -> str:
        """Schedule a data collection job"""
        
    def monitor_workers(self) -> List[WorkerStatus]:
        """Monitor health and status of all workers"""
        
    def distribute_load(self):
        """Balance workload across available workers"""
```

### 2. Base Worker Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator
import asyncio

class BaseWorker(ABC):
    """Abstract base class for all Worker Bees"""
    
    def __init__(self, worker_id: str, config: Dict[str, Any]):
        self.worker_id = worker_id
        self.config = config
        self.status = "idle"
        self.last_heartbeat = datetime.now()
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def collect_data(self) -> AsyncIterator[Dict]:
        """Collect data from source"""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Test connection health"""
        pass
    
    async def heartbeat(self):
        """Send heartbeat to Hive Manager"""
        self.last_heartbeat = datetime.now()
        await self.hive_manager.update_worker_status(
            self.worker_id, self.status
        )
    
    async def run_job(self, job_config: Dict) -> JobResult:
        """Execute a data collection job"""
        try:
            self.status = "running"
            await self.heartbeat()
            
            async for data_chunk in self.collect_data():
                await self.send_to_nectar_system(data_chunk)
            
            self.status = "completed"
            return JobResult(success=True, records_processed=count)
            
        except Exception as e:
            self.status = "failed"
            logger.error(f"Worker {self.worker_id} failed: {e}")
            return JobResult(success=False, error=str(e))
        finally:
            await self.heartbeat()
```

### 3. File Worker Implementation

```python
class FileWorker(BaseWorker):
    """Worker Bee for file-based data sources"""
    
    async def connect(self) -> bool:
        """Connect to file system or network drive"""
        connection_type = self.config.get('type', 'local')
        
        if connection_type == 'sftp':
            return await self._connect_sftp()
        elif connection_type == 's3':
            return await self._connect_s3()
        elif connection_type == 'google_drive':
            return await self._connect_google_drive()
        else:
            return await self._connect_local()
    
    async def collect_data(self) -> AsyncIterator[Dict]:
        """Collect files from configured source"""
        source_path = self.config['source_path']
        file_patterns = self.config.get('patterns', ['*'])
        
        for pattern in file_patterns:
            async for file_path in self._scan_files(source_path, pattern):
                file_data = await self._read_file(file_path)
                yield {
                    'type': 'file',
                    'source': file_path,
                    'content': file_data,
                    'metadata': await self._get_file_metadata(file_path),
                    'collected_at': datetime.now().isoformat()
                }
```

### 4. API Worker Implementation

```python
class APIWorker(BaseWorker):
    """Worker Bee for API-based data sources"""
    
    async def connect(self) -> bool:
        """Test API connection and authentication"""
        test_endpoint = self.config['endpoints']['health']
        headers = self._build_auth_headers()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(test_endpoint, headers=headers) as response:
                return response.status == 200
    
    async def collect_data(self) -> AsyncIterator[Dict]:
        """Collect data from API endpoints"""
        endpoints = self.config['endpoints']['data']
        
        for endpoint in endpoints:
            async for page_data in self._paginate_api(endpoint):
                for record in page_data:
                    yield {
                        'type': 'api_record',
                        'source': endpoint,
                        'data': record,
                        'collected_at': datetime.now().isoformat()
                    }
```

### 5. Stream Worker Implementation

```python
class StreamWorker(BaseWorker):
    """Worker Bee for real-time data streams"""
    
    async def connect(self) -> bool:
        """Connect to streaming data source"""
        stream_type = self.config['type']
        
        if stream_type == 'kafka':
            return await self._connect_kafka()
        elif stream_type == 'websocket':
            return await self._connect_websocket()
        elif stream_type == 'rabbitmq':
            return await self._connect_rabbitmq()
    
    async def collect_data(self) -> AsyncIterator[Dict]:
        """Stream data continuously"""
        # This runs indefinitely for streaming sources
        async for message in self._stream_messages():
            yield {
                'type': 'stream_message',
                'source': self.config['source'],
                'data': message,
                'timestamp': datetime.now().isoformat()
            }
```

## Nectar System Integration

### Data Processing Pipeline

```python
class NectarProcessor:
    """Processes data collected by Worker Bees"""
    
    async def process_data_chunk(self, data: Dict) -> ProcessedData:
        """Process raw data from Worker Bees"""
        
        # 1. Data validation
        await self._validate_data(data)
        
        # 2. Format detection and conversion
        processed = await self._convert_format(data)
        
        # 3. Content extraction (text, metadata, etc.)
        content = await self._extract_content(processed)
        
        # 4. PII scrubbing and compliance
        sanitized = await self._apply_scrubbing_rules(content)
        
        # 5. Chunking for knowledge base
        chunks = await self._chunk_content(sanitized)
        
        # 6. Generate embeddings
        embeddings = await self._generate_embeddings(chunks)
        
        return ProcessedData(
            content=sanitized,
            chunks=chunks,
            embeddings=embeddings,
            metadata=data['metadata']
        )
```

## Security and Compliance

### Authentication Methods

```python
class WorkerAuthentication:
    """Handle authentication for different data sources"""
    
    def __init__(self, vault_client):
        self.vault = vault_client
    
    async def get_credentials(self, worker_id: str, source_type: str) -> Dict:
        """Retrieve encrypted credentials from Vault"""
        credential_path = f"worker-bees/{worker_id}/{source_type}"
        return await self.vault.read(credential_path)
    
    async def oauth2_flow(self, config: Dict) -> str:
        """Handle OAuth2 authentication flow"""
        # Implementation for OAuth2 token exchange
        pass
    
    async def api_key_auth(self, config: Dict) -> Dict:
        """Handle API key authentication"""
        # Implementation for API key management
        pass
```

### Data Scrubbing Rules

```yaml
# scrubbing_rules.yml
scrubbing_profiles:
  gdpr_compliant:
    pii_detection:
      - email_addresses
      - phone_numbers
      - credit_cards
      - social_security_numbers
    actions:
      email_addresses: hash_with_salt
      phone_numbers: remove
      credit_cards: remove
      social_security_numbers: remove
  
  financial_data:
    sensitive_patterns:
      - account_numbers
      - routing_numbers
      - transaction_ids
    actions:
      account_numbers: mask_partial
      routing_numbers: remove
      transaction_ids: hash_with_salt
```

## Configuration Schema

### Worker Bee Configuration

```yaml
# worker_bee_config.yml
worker_bees:
  google_drive_sync:
    type: file_worker
    enabled: true
    schedule: "0 */6 * * *"  # Every 6 hours
    config:
      type: google_drive
      auth:
        method: oauth2
        client_id: "{{ vault.google.client_id }}"
        client_secret: "{{ vault.google.client_secret }}"
      source_path: "/company_docs"
      patterns: ["*.pdf", "*.docx", "*.md"]
      recursive: true
    processing:
      scrubbing_profile: gdpr_compliant
      auto_categorize: true
      target_honey_jar: "company_knowledge"
  
  sales_api_sync:
    type: api_worker
    enabled: true
    schedule: "0 0 * * *"  # Daily at midnight
    config:
      base_url: "https://api.salesforce.com"
      auth:
        method: oauth2
        client_id: "{{ vault.salesforce.client_id }}"
      endpoints:
        health: "/services/data/v58.0/"
        data: 
          - "/services/data/v58.0/sobjects/Account"
          - "/services/data/v58.0/sobjects/Opportunity"
    processing:
      scrubbing_profile: financial_data
      target_honey_jar: "sales_data"
```

## Monitoring and Metrics

### Worker Bee Dashboard

```python
class WorkerBeeMetrics:
    """Collect and expose Worker Bee metrics"""
    
    def __init__(self):
        self.metrics = {
            'workers_active': Counter(),
            'jobs_completed': Counter(),
            'jobs_failed': Counter(),
            'data_processed_bytes': Counter(),
            'processing_time': Histogram(),
            'worker_health': Gauge()
        }
    
    async def collect_metrics(self) -> Dict:
        """Collect current metrics"""
        return {
            'active_workers': await self._count_active_workers(),
            'jobs_in_queue': await self._count_queued_jobs(),
            'avg_processing_time': await self._avg_processing_time(),
            'success_rate': await self._calculate_success_rate(),
            'data_sources_connected': await self._count_connected_sources()
        }
```

### Health Monitoring

```python
class WorkerHealthMonitor:
    """Monitor Worker Bee health and performance"""
    
    async def check_worker_health(self, worker_id: str) -> HealthStatus:
        """Check individual worker health"""
        worker = await self.get_worker(worker_id)
        
        checks = [
            await self._check_heartbeat(worker),
            await self._check_connection(worker),
            await self._check_resource_usage(worker),
            await self._check_error_rate(worker)
        ]
        
        return HealthStatus(
            overall=all(checks),
            details=checks,
            last_checked=datetime.now()
        )
```

## Deployment and Scaling

### Container Configuration

```dockerfile
# Dockerfile.worker-bee
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY worker_bees/ ./worker_bees/
COPY nectar_system/ ./nectar_system/

ENV WORKER_TYPE=file_worker
ENV WORKER_ID=""
ENV HIVE_MANAGER_URL=""

CMD ["python", "-m", "worker_bees.main"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-bee-file
spec:
  replicas: 3
  selector:
    matchLabels:
      app: worker-bee
      type: file
  template:
    metadata:
      labels:
        app: worker-bee
        type: file
    spec:
      containers:
      - name: worker-bee
        image: sting/worker-bee:latest
        env:
        - name: WORKER_TYPE
          value: "file_worker"
        - name: HIVE_MANAGER_URL
          value: "http://hive-manager:8080"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Future Enhancements

### Planned Features

1. **ML-Powered Data Classification**
   - Automatic categorization of collected data
   - Smart routing to appropriate honey jars
   - Content quality scoring

2. **Real-time Analytics**
   - Live data flow monitoring
   - Performance optimization suggestions
   - Predictive scaling

3. **Advanced Scheduling**
   - Event-driven data collection
   - Dependency-based job orchestration
   - Smart retry mechanisms

4. **Multi-cloud Support**
   - Cross-cloud data synchronization
   - Cloud-agnostic deployment
   - Disaster recovery across clouds

---

*Worker Bees enable STING to seamlessly integrate with your existing data ecosystem, providing a unified knowledge platform.*