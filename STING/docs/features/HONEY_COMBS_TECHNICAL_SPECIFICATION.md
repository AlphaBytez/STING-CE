# Honey Combs Technical Specification

## Executive Summary

Honey Combs are reusable data source configuration templates that enable rapid and secure connectivity to various data sources within the STING ecosystem. They serve as the blueprint for Worker Bees to collect data, either continuously feeding Honey Jars with live data or generating new Honey Jars through snapshots and dumps.

## Core Concept

### 🏗️ What are Honey Combs?

Honey Combs are pre-configured connection templates that define:
- **Connection parameters** for specific data source types
- **Security configurations** including authentication methods
- **Data extraction patterns** and query templates
- **Scrubbing rules** for privacy compliance
- **Output specifications** for Honey Jar generation

Think of them as the hexagonal cells in a beehive that bees use to produce honey - they provide the structure and specifications for data collection and processing.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Source   │     │   Honey Comb    │     │   Worker Bee    │
│  (Database/API) │────▶│  (Configuration)│────▶│   (Connector)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┴───────────────────────────┐
                              │                                                       │
                              ▼                                                       ▼
                    ┌─────────────────┐                                    ┌─────────────────┐
                    │ Scrubbing Engine│                                    │  Honey Jar      │
                    │ (Optional PII   │                                    │ (Live Feed)     │
                    │  Removal)       │                                    └─────────────────┘
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Honey Jar     │
                    │ (Generated)     │
                    └─────────────────┘
```

## Honey Comb Types

### 1. Database Combs 🗄️

Pre-configured templates for common database systems:

```yaml
postgresql_comb:
  type: "database"
  subtype: "postgresql"
  connection:
    host: "${COMB_DB_HOST}"
    port: 5432
    ssl_mode: "require"
    connection_pool:
      min: 2
      max: 10
  extraction_modes:
    - full_dump: "Generate complete Honey Jar snapshot"
    - incremental: "Continuous CDC feed to existing Honey Jar"
    - query_based: "Custom SQL extraction"
  scrubbing:
    enabled: true
    profiles:
      - pii_removal: "Remove personal identifiable information"
      - tokenization: "Replace sensitive data with tokens"
      - redaction: "Mask specified columns"
```

Supported databases:
- PostgreSQL
- MySQL/MariaDB
- MongoDB
- Oracle
- SQL Server
- Snowflake
- BigQuery
- DynamoDB

### 2. API Combs 🌐

Templates for API integrations:

```yaml
rest_api_comb:
  type: "api"
  subtype: "rest"
  connection:
    base_url: "${COMB_API_URL}"
    auth_type: "oauth2"
    rate_limit:
      requests_per_minute: 60
      retry_strategy: "exponential_backoff"
  extraction_modes:
    - paginated_sync: "Fetch all pages and create Honey Jar"
    - webhook_listener: "Real-time data feed"
    - scheduled_polling: "Periodic data collection"
  data_format: "json"
  scrubbing:
    enabled: true
    json_paths:
      - "$.users[*].email"
      - "$.users[*].phone"
```

Supported API types:
- REST
- GraphQL
- SOAP
- gRPC
- WebSocket

### 3. File System Combs 📁

Templates for file-based data sources:

```yaml
s3_comb:
  type: "file_system"
  subtype: "s3"
  connection:
    bucket: "${COMB_S3_BUCKET}"
    region: "${COMB_S3_REGION}"
    auth_type: "iam_role"
  extraction_modes:
    - bucket_snapshot: "Create Honey Jar from entire bucket"
    - file_monitor: "Watch for new files and stream to Honey Jar"
    - pattern_match: "Extract files matching patterns"
  file_processing:
    formats: ["csv", "json", "parquet", "excel"]
    compression: ["gzip", "zip", "brotli"]
  scrubbing:
    enabled: true
    file_handlers:
      csv: "column_based_scrubbing"
      json: "path_based_scrubbing"
```

Supported file systems:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage
- FTP/SFTP
- Local file system
- SharePoint
- Google Drive
- Dropbox

### 4. Stream Combs 🌊

Templates for real-time data streams:

```yaml
kafka_comb:
  type: "stream"
  subtype: "kafka"
  connection:
    brokers: "${COMB_KAFKA_BROKERS}"
    security_protocol: "SASL_SSL"
    consumer_group: "sting_worker_bees"
  extraction_modes:
    - continuous_stream: "Feed Honey Jar in real-time"
    - time_window_snapshot: "Create Honey Jar from time range"
    - topic_dump: "Export entire topic to Honey Jar"
  processing:
    batch_size: 1000
    commit_interval: "5s"
  scrubbing:
    enabled: true
    stream_processor: "inline_scrubbing"
```

Supported streaming platforms:
- Apache Kafka
- RabbitMQ
- AWS Kinesis
- Google Pub/Sub
- Redis Streams
- MQTT

## Data Scrubbing Engine

### Privacy-First Architecture

The scrubbing engine operates at the data ingestion layer, ensuring sensitive information is handled according to compliance requirements:

```python
class ScrubberEngine:
    """Core scrubbing engine for Honey Comb data processing"""
    
    def __init__(self, scrubbing_profile: Dict[str, Any]):
        self.profile = scrubbing_profile
        self.pii_detector = PIIDetector()
        self.tokenizer = DataTokenizer()
        self.audit_logger = AuditLogger()
    
    async def scrub_data(self, data: Any, data_type: str) -> Any:
        """Apply scrubbing rules based on profile"""
        if not self.profile.get('enabled', False):
            return data
            
        # Detect PII
        pii_locations = await self.pii_detector.scan(data, data_type)
        
        # Apply scrubbing strategy
        scrubbed_data = await self._apply_scrubbing(data, pii_locations)
        
        # Log scrubbing actions for compliance
        await self.audit_logger.log_scrubbing_action(
            original_hash=hashlib.sha256(str(data).encode()).hexdigest(),
            scrubbed_fields=pii_locations,
            strategy=self.profile['strategy']
        )
        
        return scrubbed_data
```

### Scrubbing Strategies

1. **PII Removal**: Complete removal of personal information
2. **Tokenization**: Replace sensitive data with reversible tokens
3. **Redaction**: Mask data while preserving format (e.g., ***-**-1234)
4. **Generalization**: Replace specific values with categories
5. **Encryption**: Encrypt sensitive fields at rest

### Compliance Profiles

Pre-configured profiles for common regulations:
- **GDPR**: EU data protection
- **CCPA**: California privacy rights
- **HIPAA**: Healthcare information
- **PCI-DSS**: Payment card data
- **SOC2**: Security and availability

## Honey Jar Generation Modes

### 1. Continuous Flow Mode 🔄

Worker Bees use Honey Combs to maintain live connections:

```python
async def continuous_flow(comb: HoneyComb, honey_jar: HoneyJar):
    """Continuously feed data into existing Honey Jar"""
    worker_bee = WorkerBee(comb.configuration)
    
    async for batch in worker_bee.collect_nectar_stream():
        # Apply scrubbing if configured
        if comb.scrubbing_enabled:
            batch = await scrubber.scrub_data(batch, comb.data_type)
        
        # Store in Honey Jar
        await honey_jar.add_honey(batch)
        
        # Update metrics
        await worker_bee.report_collection_metrics(len(batch))
```

### 2. Snapshot Generation Mode 📸

Create new Honey Jars from data source snapshots:

```python
async def generate_honey_jar(comb: HoneyComb, source_filter: Optional[Dict] = None):
    """Generate new Honey Jar from data source"""
    worker_bee = WorkerBee(comb.configuration)
    
    # Collect all data based on filter
    raw_data = await worker_bee.collect_nectar_batch(source_filter)
    
    # Apply scrubbing
    if comb.scrubbing_enabled:
        processed_data = await scrubber.scrub_data(raw_data, comb.data_type)
    else:
        processed_data = raw_data
    
    # Create new Honey Jar
    honey_jar = HoneyJar.create(
        name=f"{comb.name}_snapshot_{datetime.now().isoformat()}",
        description=f"Generated from {comb.name}",
        data=processed_data,
        metadata={
            'source_comb': comb.id,
            'generation_time': datetime.now(),
            'scrubbing_applied': comb.scrubbing_enabled
        }
    )
    
    return honey_jar
```

## Configuration Schema

### Honey Comb Definition

```yaml
honey_comb:
  id: "uuid"
  name: "Production Database Comb"
  description: "PostgreSQL production database with PII scrubbing"
  type: "database"
  subtype: "postgresql"
  
  connection:
    # Connection details (encrypted in Vault)
    vault_path: "/honey_combs/prod_db"
    
  extraction:
    default_mode: "incremental"
    available_modes:
      - full_dump
      - incremental
      - query_based
    
  scrubbing:
    enabled: true
    profile: "gdpr_compliant"
    custom_rules:
      - field: "users.email"
        action: "tokenize"
      - field: "users.ssn"
        action: "remove"
      - pattern: "credit_card_*"
        action: "redact"
    
  scheduling:
    continuous_flow:
      enabled: true
      interval: "5m"
    snapshot_generation:
      enabled: true
      cron: "0 2 * * *"  # Daily at 2 AM
    
  access_control:
    required_permissions:
      - "comb:read:prod_db"
      - "honey_jar:create"
    data_classification: "confidential"
```

## Security Considerations

### 1. Credential Management
- All credentials stored in HashiCorp Vault
- Worker Bees retrieve credentials at runtime
- No credentials stored in Comb configurations

### 2. Access Control
- Role-based access to Honey Combs
- Audit logging for all data access
- Encryption in transit and at rest

### 3. Data Sovereignty
- Combs can enforce data residency requirements
- Regional scrubbing rules
- Compliance tracking

## Integration with Existing Architecture

### Worker Bee Enhancement

Worker Bees will be enhanced to:
1. Accept Honey Comb configurations
2. Apply scrubbing rules during collection
3. Support both streaming and batch modes
4. Report collection metrics

### UI Integration

Within the Honey Jar interface:
1. **"Quick Connect" button**: Browse Comb library
2. **Comb Selection Modal**: Choose and configure Combs
3. **Scrubbing Options**: Toggle and configure privacy settings
4. **Generation Wizard**: Create new Honey Jars from Combs

## Implementation Phases

### Phase 1: Core Infrastructure
- Honey Comb configuration schema
- Basic Worker Bee integration
- Database Combs (PostgreSQL, MySQL)

### Phase 2: Scrubbing Engine
- PII detection algorithms
- Scrubbing strategies implementation
- Compliance profiles

### Phase 3: Extended Connectors
- API Combs
- File System Combs
- Stream Combs

### Phase 4: UI Integration
- Comb library browser
- Configuration wizard
- Monitoring dashboard

## Success Metrics

1. **Time to Connect**: Reduce from hours to minutes
2. **Data Privacy**: 100% PII detection accuracy
3. **Reusability**: 80% of connections use existing Combs
4. **Compliance**: Automated compliance reporting

## Conclusion

Honey Combs represent a paradigm shift in how organizations connect to and manage their data sources. By providing reusable, secure, and privacy-compliant templates, they enable rapid data integration while maintaining the highest standards of security and governance.