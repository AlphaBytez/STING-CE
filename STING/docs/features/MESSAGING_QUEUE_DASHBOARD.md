# Messaging Queue Dashboard

## Overview

The STING-CE Messaging Queue system provides robust inter-service communication, background job processing, and real-time messaging capabilities. Built on Redis and PostgreSQL, it offers reliable message delivery, queue management, and comprehensive monitoring through an integrated dashboard.

## Architecture

### Queue System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Producers     │───▶│   Redis Queue   │───▶│   Workers       │
│ (App, Chatbot,  │    │   (Fast Queue)  │    │ (Processors)    │
│  Knowledge)     │    └─────────────────┘    └─────────────────┘
└─────────────────┘             │                       │
                                 ▼                       ▼
                    ┌─────────────────────────────────────────────┐
                    │           PostgreSQL                        │
                    │        (Persistent Storage)                 │
                    │ ┌─────────────┐ ┌─────────────────────────┐ │
                    │ │   Messages  │ │    Queue Metadata       │ │
                    │ │   History   │ │   (Stats, Status)       │ │
                    │ └─────────────┘ └─────────────────────────┘ │
                    └─────────────────────────────────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │    Dashboard    │
                            │   (Monitoring)  │
                            └─────────────────┘
```

### Key Components

1. **Redis Queue**: High-performance in-memory queue for active jobs
2. **PostgreSQL Storage**: Persistent storage for message history and metadata
3. **Worker Processes**: Background job processors
4. **Message Router**: Intelligent message routing and delivery
5. **Dashboard Interface**: Real-time queue monitoring and management
6. **Messaging Service**: Standalone service for queue management

## Service Configuration

### Messaging Service

The messaging service is defined in `docker-compose.yml`:

```yaml
messaging:
  container_name: sting-ce-messaging
  build:
    context: ./messaging_service
    dockerfile: Dockerfile
  environment:
    - MESSAGING_ENCRYPTION_ENABLED=true
    - MESSAGING_QUEUE_ENABLED=true
    - MESSAGING_NOTIFICATIONS_ENABLED=true
    - MESSAGING_STORAGE_BACKEND=postgresql
    - DATABASE_URL=postgresql://app_user:app_secure_password_change_me@db:5432/sting_messaging
    - REDIS_URL=redis://redis:6379
    - MAX_MESSAGE_SIZE=1048576  # 1MB
    - MESSAGE_RETENTION_DAYS=30
  volumes:
    - messaging_data:/app/data
    - ./messaging_service:/app
  ports:
    - 8889:8889
  networks:
    sting_local:
      aliases:
        - messaging
  depends_on:
    db:
      condition: service_healthy
```

### Queue Types

The system supports multiple queue types for different use cases:

```python
# Queue configuration
QUEUE_TYPES = {
    'default': {
        'priority': 100,
        'max_retries': 3,
        'retry_delay': 60,  # seconds
        'max_workers': 5
    },
    'reports': {
        'priority': 200,
        'max_retries': 2,
        'retry_delay': 120,
        'max_workers': 3,
        'timeout': 1800  # 30 minutes
    },
    'notifications': {
        'priority': 300,
        'max_retries': 5,
        'retry_delay': 30,
        'max_workers': 10,
        'timeout': 60
    },
    'background': {
        'priority': 50,
        'max_retries': 2,
        'retry_delay': 300,
        'max_workers': 2,
        'timeout': 3600  # 1 hour
    }
}
```

## Message Structure

### Message Format

All messages follow a standardized format:

```json
{
  "id": "msg-uuid-1234567890",
  "queue": "reports",
  "type": "report_generation",
  "payload": {
    "user_id": "user-uuid",
    "template_id": "template-uuid",
    "parameters": {
      "format": "pdf",
      "include_charts": true
    }
  },
  "metadata": {
    "created_at": "2024-08-22T10:30:45.123Z",
    "scheduled_for": "2024-08-22T10:30:45.123Z",
    "priority": 200,
    "max_retries": 3,
    "current_retry": 0,
    "timeout": 1800,
    "source": "app",
    "correlation_id": "req-uuid"
  },
  "status": "pending",
  "worker_id": null,
  "started_at": null,
  "completed_at": null,
  "error": null,
  "result": null
}
```

### Queue States

Messages progress through defined states:

- **pending**: Newly created, waiting for worker
- **queued**: In Redis queue, ready for processing
- **processing**: Currently being processed by worker
- **completed**: Successfully processed
- **failed**: Processing failed (with retry logic)
- **cancelled**: Manually cancelled
- **expired**: Timed out during processing

## Dashboard Interface

### Queue Monitoring Dashboard

The messaging dashboard provides comprehensive queue monitoring:

```javascript
// React component for queue monitoring
const MessagingQueueDashboard = () => {
  const [queueStats, setQueueStats] = useState({});
  const [activeJobs, setActiveJobs] = useState([]);
  const [failedJobs, setFailedJobs] = useState([]);
  const [workerStatus, setWorkerStatus] = useState({});
  
  // Real-time updates via WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8889/queue/status');
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      switch(update.type) {
        case 'queue_stats':
          setQueueStats(update.data);
          break;
        case 'job_update':
          updateJobStatus(update.data);
          break;
        case 'worker_status':
          setWorkerStatus(update.data);
          break;
      }
    };
    
    return () => ws.close();
  }, []);
  
  return (
    <div className="messaging-dashboard">
      <QueueStatistics stats={queueStats} />
      <ActiveJobsList jobs={activeJobs} />
      <FailedJobsList jobs={failedJobs} />
      <WorkerStatusPanel workers={workerStatus} />
    </div>
  );
};
```

### Key Dashboard Metrics

1. **Queue Depth**: Number of pending jobs per queue
2. **Processing Rate**: Jobs processed per minute/hour
3. **Success Rate**: Percentage of successful job completions
4. **Average Processing Time**: Mean time for job completion
5. **Worker Utilization**: Active workers vs available capacity
6. **Error Rate**: Failed jobs and common error patterns
7. **Queue Throughput**: Messages/second processed

### Dashboard Widgets

#### Queue Statistics Widget
```javascript
const QueueStatistics = ({ stats }) => (
  <div className="queue-stats-grid">
    {Object.entries(stats.queues || {}).map(([queueName, queueData]) => (
      <div key={queueName} className="queue-stat-card">
        <h3>{queueName}</h3>
        <div className="metrics">
          <div className="metric">
            <label>Pending</label>
            <span className="value">{queueData.pending}</span>
          </div>
          <div className="metric">
            <label>Processing</label>
            <span className="value">{queueData.processing}</span>
          </div>
          <div className="metric">
            <label>Completed Today</label>
            <span className="value">{queueData.completed_today}</span>
          </div>
          <div className="metric">
            <label>Success Rate</label>
            <span className="value">{queueData.success_rate}%</span>
          </div>
        </div>
        <div className="queue-actions">
          <button onClick={() => pauseQueue(queueName)}>
            {queueData.paused ? 'Resume' : 'Pause'}
          </button>
          <button onClick={() => drainQueue(queueName)}>
            Drain Queue
          </button>
        </div>
      </div>
    ))}
  </div>
);
```

#### Active Jobs Monitor
```javascript
const ActiveJobsList = ({ jobs }) => (
  <div className="active-jobs-panel">
    <h3>Active Jobs ({jobs.length})</h3>
    <div className="jobs-table">
      {jobs.map(job => (
        <div key={job.id} className="job-row">
          <div className="job-info">
            <span className="job-type">{job.type}</span>
            <span className="job-id">{job.id.slice(0, 8)}</span>
          </div>
          <div className="job-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${job.progress || 0}%` }}
              />
            </div>
            <span className="progress-text">
              {job.progress || 0}%
            </span>
          </div>
          <div className="job-timing">
            <span>Started: {formatTime(job.started_at)}</span>
            <span>Duration: {formatDuration(job.started_at)}</span>
          </div>
          <div className="job-actions">
            <button onClick={() => cancelJob(job.id)}>Cancel</button>
          </div>
        </div>
      ))}
    </div>
  </div>
);
```

## API Endpoints

### Queue Management API

```python
# Core queue management endpoints
@messaging_bp.route('/queue/<queue_name>/stats', methods=['GET'])
def get_queue_stats(queue_name):
    """Get statistics for a specific queue"""
    stats = queue_manager.get_queue_stats(queue_name)
    return jsonify({
        'queue': queue_name,
        'stats': stats,
        'timestamp': datetime.utcnow().isoformat()
    })

@messaging_bp.route('/queue/<queue_name>/jobs', methods=['GET'])
def list_queue_jobs(queue_name):
    """List jobs in a specific queue"""
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))
    
    jobs = queue_manager.list_jobs(queue_name, status=status, limit=limit)
    return jsonify({
        'queue': queue_name,
        'jobs': jobs,
        'count': len(jobs)
    })

@messaging_bp.route('/job/<job_id>', methods=['GET'])
def get_job_details(job_id):
    """Get detailed information about a specific job"""
    job = queue_manager.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({'job': job})

@messaging_bp.route('/job/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a specific job"""
    result = queue_manager.cancel_job(job_id)
    if result:
        return jsonify({'message': 'Job cancelled successfully'})
    else:
        return jsonify({'error': 'Failed to cancel job'}), 400

@messaging_bp.route('/queue/<queue_name>/pause', methods=['POST'])
def pause_queue(queue_name):
    """Pause processing for a queue"""
    queue_manager.pause_queue(queue_name)
    return jsonify({'message': f'Queue {queue_name} paused'})

@messaging_bp.route('/queue/<queue_name>/resume', methods=['POST'])  
def resume_queue(queue_name):
    """Resume processing for a queue"""
    queue_manager.resume_queue(queue_name)
    return jsonify({'message': f'Queue {queue_name} resumed'})
```

### Real-time Updates

WebSocket endpoint for real-time queue monitoring:

```python
@messaging_bp.route('/queue/status')
def queue_status_websocket():
    """WebSocket endpoint for real-time queue updates"""
    def event_stream():
        while True:
            # Get current queue status
            stats = queue_manager.get_all_queue_stats()
            
            yield f"data: {json.dumps({
                'type': 'queue_stats',
                'data': stats,
                'timestamp': datetime.utcnow().isoformat()
            })}\n\n"
            
            time.sleep(5)  # Update every 5 seconds
    
    return Response(event_stream(), mimetype='text/plain')
```

## Worker Management

### Worker Configuration

Workers are configured per queue type:

```python
class QueueWorker:
    def __init__(self, queue_name, worker_id=None):
        self.queue_name = queue_name
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.redis_client = redis.from_url(REDIS_URL)
        self.db_session = get_db_session()
        self.is_running = False
        self.current_job = None
        
    async def start(self):
        """Start worker process"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} started for queue {self.queue_name}")
        
        while self.is_running:
            try:
                # Get next job from queue
                job_data = self.redis_client.blpop(
                    f"queue:{self.queue_name}", 
                    timeout=30
                )
                
                if job_data:
                    job_json = job_data[1]
                    job = json.loads(job_json)
                    
                    await self.process_job(job)
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(10)
    
    async def process_job(self, job):
        """Process a single job"""
        job_id = job['id']
        self.current_job = job
        
        try:
            # Update job status to processing
            self.update_job_status(job_id, 'processing', {
                'worker_id': self.worker_id,
                'started_at': datetime.utcnow().isoformat()
            })
            
            # Process based on job type
            processor = self.get_job_processor(job['type'])
            result = await processor.process(job)
            
            # Mark job as completed
            self.update_job_status(job_id, 'completed', {
                'completed_at': datetime.utcnow().isoformat(),
                'result': result
            })
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            # Handle job failure with retry logic
            retry_count = job['metadata'].get('current_retry', 0)
            max_retries = job['metadata'].get('max_retries', 3)
            
            if retry_count < max_retries:
                # Retry job
                job['metadata']['current_retry'] = retry_count + 1
                retry_delay = job['metadata'].get('retry_delay', 60)
                
                # Schedule retry
                self.schedule_retry(job, retry_delay)
                
                self.update_job_status(job_id, 'pending', {
                    'error': str(e),
                    'retry_scheduled': True
                })
            else:
                # Mark as failed
                self.update_job_status(job_id, 'failed', {
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                })
            
            logger.error(f"Job {job_id} failed: {e}")
        
        finally:
            self.current_job = None
```

### Worker Scaling

Dynamic worker scaling based on queue depth:

```python
class WorkerManager:
    def __init__(self):
        self.workers = {}
        self.scaling_config = {
            'reports': {'min': 2, 'max': 5, 'scale_threshold': 10},
            'notifications': {'min': 5, 'max': 15, 'scale_threshold': 50},
            'background': {'min': 1, 'max': 3, 'scale_threshold': 5}
        }
    
    def auto_scale_workers(self):
        """Automatically scale workers based on queue depth"""
        for queue_name, config in self.scaling_config.items():
            queue_depth = self.get_queue_depth(queue_name)
            current_workers = len(self.workers.get(queue_name, []))
            
            if queue_depth > config['scale_threshold']:
                # Scale up
                if current_workers < config['max']:
                    self.start_worker(queue_name)
            elif queue_depth == 0:
                # Scale down  
                if current_workers > config['min']:
                    self.stop_worker(queue_name)
    
    def start_worker(self, queue_name):
        """Start a new worker for the specified queue"""
        worker = QueueWorker(queue_name)
        
        if queue_name not in self.workers:
            self.workers[queue_name] = []
        
        self.workers[queue_name].append(worker)
        
        # Start worker in background
        asyncio.create_task(worker.start())
        
        logger.info(f"Started new worker for queue {queue_name}")
    
    def stop_worker(self, queue_name):
        """Stop a worker for the specified queue"""
        if queue_name in self.workers and self.workers[queue_name]:
            worker = self.workers[queue_name].pop()
            worker.stop()
            logger.info(f"Stopped worker for queue {queue_name}")
```

## Monitoring and Alerting

### Health Checks

```python
@messaging_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check for messaging system"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    try:
        # Check Redis connectivity
        redis_client.ping()
        health_status['components']['redis'] = {'status': 'healthy'}
    except Exception as e:
        health_status['components']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    try:
        # Check PostgreSQL connectivity
        with get_db_session() as session:
            session.execute(text('SELECT 1'))
        health_status['components']['database'] = {'status': 'healthy'}
    except Exception as e:
        health_status['components']['database'] = {
            'status': 'unhealthy', 
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check worker status
    worker_stats = worker_manager.get_worker_stats()
    health_status['components']['workers'] = {
        'status': 'healthy' if worker_stats['active'] > 0 else 'warning',
        'active_workers': worker_stats['active'],
        'total_workers': worker_stats['total']
    }
    
    # Check queue depths
    queue_stats = queue_manager.get_all_queue_stats()
    health_status['components']['queues'] = queue_stats
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code
```

### Performance Metrics

```python
class MessagingMetrics:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def record_job_completion(self, queue_name, duration, success=True):
        """Record job completion metrics"""
        timestamp = int(time.time())
        hour_key = f"metrics:hourly:{timestamp // 3600}"
        day_key = f"metrics:daily:{timestamp // 86400}"
        
        # Increment counters
        self.redis.hincrby(hour_key, f"{queue_name}:completed", 1)
        self.redis.hincrby(day_key, f"{queue_name}:completed", 1)
        
        if success:
            self.redis.hincrby(hour_key, f"{queue_name}:success", 1)
            self.redis.hincrby(day_key, f"{queue_name}:success", 1)
        else:
            self.redis.hincrby(hour_key, f"{queue_name}:failed", 1)
            self.redis.hincrby(day_key, f"{queue_name}:failed", 1)
        
        # Record duration
        self.redis.lpush(f"durations:{queue_name}", duration)
        self.redis.ltrim(f"durations:{queue_name}", 0, 999)  # Keep last 1000
        
        # Set expiration
        self.redis.expire(hour_key, 86400 * 7)  # 7 days
        self.redis.expire(day_key, 86400 * 30)  # 30 days
    
    def get_throughput_metrics(self, queue_name, timeframe='hour'):
        """Get throughput metrics for a queue"""
        timestamp = int(time.time())
        
        if timeframe == 'hour':
            key = f"metrics:hourly:{timestamp // 3600}"
        else:
            key = f"metrics:daily:{timestamp // 86400}"
        
        completed = int(self.redis.hget(key, f"{queue_name}:completed") or 0)
        success = int(self.redis.hget(key, f"{queue_name}:success") or 0)
        failed = int(self.redis.hget(key, f"{queue_name}:failed") or 0)
        
        return {
            'completed': completed,
            'success': success,
            'failed': failed,
            'success_rate': (success / completed * 100) if completed > 0 else 0
        }
```

## Troubleshooting

### Common Issues

#### Jobs Stuck in Queue

**Symptoms:**
- Jobs remain in "pending" status
- No workers processing jobs

**Diagnosis:**
```bash
# Check worker processes
./manage_sting.sh logs messaging

# Check Redis queue length
redis-cli LLEN queue:reports

# Check worker status
curl http://localhost:8889/workers/status
```

**Solutions:**
```bash
# Restart messaging service
./manage_sting.sh restart messaging

# Manually start worker
curl -X POST http://localhost:8889/workers/start \
  -H "Content-Type: application/json" \
  -d '{"queue": "reports"}'

# Clear stuck jobs (if safe)
curl -X POST http://localhost:8889/queue/reports/drain
```

#### High Memory Usage

**Symptoms:**
- Redis consuming excessive memory
- Messaging service OOM errors

**Solutions:**
```bash
# Check queue depths
redis-cli INFO memory

# Check large queues
redis-cli EVAL "
for i, key in ipairs(redis.call('keys', 'queue:*')) do
    local len = redis.call('llen', key)
    if len > 1000 then
        print(key .. ': ' .. len)
    end
end
" 0

# Increase worker count for backed up queues
curl -X POST http://localhost:8889/workers/scale \
  -H "Content-Type: application/json" \
  -d '{"queue": "reports", "workers": 5}'
```

#### Message Loss

**Symptoms:**
- Jobs disappearing from queue
- No completion records

**Solutions:**
```bash
# Check PostgreSQL job history
psql -h localhost -p 5433 -U app_user -d sting_messaging \
  -c "SELECT * FROM job_history WHERE status = 'lost' ORDER BY created_at DESC LIMIT 10;"

# Enable job persistence
curl -X PUT http://localhost:8889/config \
  -H "Content-Type: application/json" \
  -d '{"job_persistence": true, "backup_to_db": true}'
```

## Security Considerations

### Message Encryption

All messages can be encrypted at rest:

```python
from cryptography.fernet import Fernet

class EncryptedMessageQueue:
    def __init__(self, encryption_key):
        self.fernet = Fernet(encryption_key)
    
    def encrypt_message(self, message):
        """Encrypt message payload"""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        encrypted = self.fernet.encrypt(message.encode())
        return encrypted.decode()
    
    def decrypt_message(self, encrypted_message):
        """Decrypt message payload"""
        decrypted = self.fernet.decrypt(encrypted_message.encode())
        return json.loads(decrypted.decode())
```

### Access Control

- **API Authentication**: All queue management APIs require valid session
- **Worker Isolation**: Workers run in isolated processes
- **Network Security**: Internal communication on `sting_local` network only
- **Message Validation**: All messages validated before processing

## Future Enhancements

### Planned Features

1. **Dead Letter Queues**: Automatic handling of persistently failing messages
2. **Message Routing**: Advanced routing based on content and metadata  
3. **Batch Processing**: Efficient processing of message batches
4. **Priority Queues**: Enhanced priority-based message ordering
5. **Cross-Service Messaging**: Direct service-to-service communication

### Integration Roadmap

- **Kubernetes Support**: Native Kubernetes job scheduling
- **Cloud Queues**: Integration with AWS SQS, Google Pub/Sub
- **Monitoring Integration**: Enhanced Grafana dashboards and alerting
- **Machine Learning**: Predictive scaling and anomaly detection

---

**Note**: The Messaging Queue Dashboard provides comprehensive queue management and monitoring for STING-CE's distributed processing needs. It ensures reliable message delivery, efficient resource utilization, and provides detailed insights into system performance.