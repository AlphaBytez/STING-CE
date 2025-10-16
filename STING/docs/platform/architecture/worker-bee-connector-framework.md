# Worker Bee Connector Framework - Technical Specification

## Overview

Worker Bees are specialized data connectors that securely bridge STING's Honey Jars with external data sources. Building on STING's existing Worker Bee concept for distributed processing, these connectors extend the metaphor to data collection and integration.

## Architecture

### Worker Bee Types

```yaml
worker_bee_types:
  data_collectors:
    description: "Gather data from external sources"
    examples:
      - database_worker_bee
      - file_system_worker_bee
      - api_worker_bee
      - stream_worker_bee
  
  processors:
    description: "Transform and enrich data"
    examples:
      - etl_worker_bee
      - validation_worker_bee
      - encryption_worker_bee
  
  pollinators:
    description: "Sync data between systems"
    examples:
      - replication_worker_bee
      - cdc_worker_bee
      - backup_worker_bee
```

### Core Worker Bee Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

class WorkerBee(ABC):
    """Base class for all Worker Bee connectors"""
    
    def __init__(self, hive_config: Dict[str, Any]):
        self.hive_config = hive_config
        self.bee_id = self._generate_bee_id()
        self.flight_log = []  # Audit trail
        self.nectar_collected = 0  # Data volume metrics
        self.status = "idle"
        
    @abstractmethod
    async def collect_nectar(self, source: str, query: Optional[Dict] = None) -> Dict[str, Any]:
        """Collect data from external source"""
        pass
    
    @abstractmethod
    async def validate_flight_path(self) -> bool:
        """Validate connection and permissions"""
        pass
    
    @abstractmethod
    def get_pollen_schema(self) -> Dict[str, Any]:
        """Return data schema/metadata"""
        pass
    
    async def return_to_hive(self, nectar: Dict[str, Any]) -> str:
        """Store collected data in Honey Jar"""
        honey_jar_id = await self._store_in_honey_jar(nectar)
        self._log_flight(honey_jar_id, len(nectar))
        return honey_jar_id
    
    def dance_instructions(self) -> Dict[str, Any]:
        """Return connection configuration for other bees"""
        return {
            "bee_type": self.__class__.__name__,
            "flight_pattern": self._get_flight_pattern(),
            "nectar_sources": self._get_available_sources()
        }
```

### Database Worker Bee Implementation

```python
class PostgreSQLWorkerBee(WorkerBee):
    """Worker Bee for PostgreSQL data collection"""
    
    def __init__(self, hive_config: Dict[str, Any]):
        super().__init__(hive_config)
        self.connection_pool = None
        self.max_flight_duration = 300  # 5 minute timeout
        
    async def collect_nectar(self, source: str, query: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute query and return results"""
        self.status = "collecting"
        
        try:
            # Validate query against security policies
            if not self._validate_query_safety(query):
                raise SecurityViolation("Query contains forbidden operations")
            
            # Apply row-level security filters
            secured_query = self._apply_hive_security(query)
            
            # Execute query with timeout
            async with self._get_connection() as conn:
                results = await asyncio.wait_for(
                    conn.fetch(secured_query['sql'], *secured_query.get('params', [])),
                    timeout=self.max_flight_duration
                )
            
            # Transform to nectar format
            nectar = {
                "source": source,
                "timestamp": datetime.utcnow().isoformat(),
                "row_count": len(results),
                "data": [dict(row) for row in results],
                "pollen": self._extract_metadata(results)
            }
            
            self.nectar_collected += len(results)
            return nectar
            
        finally:
            self.status = "idle"
    
    async def validate_flight_path(self) -> bool:
        """Test database connection"""
        try:
            async with self._get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            self._log_error(f"Flight path validation failed: {e}")
            return False
    
    def get_pollen_schema(self) -> Dict[str, Any]:
        """Return database schema information"""
        # Implementation for schema introspection
        pass
```

### Identity Provider Integration

```python
class IdentityHive:
    """Manages identity provider integrations for Worker Bees"""
    
    def __init__(self):
        self.providers = {}
        self.passkey_manager = PasskeyManager()
        
    def register_provider(self, provider_type: str, config: Dict[str, Any]):
        """Register an identity provider"""
        if provider_type == "active_directory":
            provider = ActiveDirectoryProvider(config)
        elif provider_type == "okta":
            provider = OktaProvider(config)
        elif provider_type == "azure_ad":
            provider = AzureADProvider(config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        self.providers[provider_type] = provider
    
    async def authenticate_bee(self, bee_id: str, credentials: Dict) -> Dict[str, Any]:
        """Authenticate a Worker Bee using configured IdP"""
        # Try passkey first
        if passkey := credentials.get('passkey'):
            return await self.passkey_manager.verify_passkey(passkey)
        
        # Fall back to IdP
        provider = self.providers.get(credentials['provider'])
        if not provider:
            raise AuthenticationError("No suitable identity provider")
        
        return await provider.authenticate(credentials)
    
    def get_bee_permissions(self, bee_identity: Dict) -> List[str]:
        """Get permissions for authenticated bee"""
        # Map IdP groups to STING permissions
        permissions = []
        for group in bee_identity.get('groups', []):
            permissions.extend(self._map_group_to_permissions(group))
        return permissions
```

### Connection Pool Management

```python
class HiveConnectionPool:
    """Manages connections for all Worker Bees in a Hive"""
    
    def __init__(self, max_connections: int = 100):
        self.pools = {}  # Connection pools by source
        self.max_connections = max_connections
        self.metrics = ConnectionMetrics()
        
    async def get_connection(self, source_id: str, bee_type: str) -> Any:
        """Get a connection from the pool"""
        pool_key = f"{source_id}:{bee_type}"
        
        if pool_key not in self.pools:
            self.pools[pool_key] = await self._create_pool(source_id, bee_type)
        
        conn = await self.pools[pool_key].acquire()
        self.metrics.record_checkout(pool_key)
        return conn
    
    async def return_connection(self, conn: Any, source_id: str, bee_type: str):
        """Return a connection to the pool"""
        pool_key = f"{source_id}:{bee_type}"
        await self.pools[pool_key].release(conn)
        self.metrics.record_checkin(pool_key)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get status of all connection pools"""
        return {
            pool_key: {
                "size": pool.size,
                "available": pool.freesize,
                "in_use": pool.size - pool.freesize,
                "metrics": self.metrics.get_pool_metrics(pool_key)
            }
            for pool_key, pool in self.pools.items()
        }
```

### Security Framework

```python
class WorkerBeeSecurity:
    """Security controls for Worker Bee operations"""
    
    def __init__(self, vault_client: VaultClient):
        self.vault = vault_client
        self.policy_engine = PolicyEngine()
        self.audit_logger = AuditLogger()
        
    async def get_credentials(self, source_id: str, bee_id: str) -> Dict[str, Any]:
        """Retrieve credentials for a data source"""
        # Check bee permissions
        if not await self._check_bee_authorization(bee_id, source_id):
            raise AuthorizationError(f"Bee {bee_id} not authorized for {source_id}")
        
        # Get credentials from Vault
        creds = await self.vault.get_secret(f"data-sources/{source_id}")
        
        # Log access
        self.audit_logger.log_credential_access(bee_id, source_id)
        
        # Return time-limited credentials
        return self._create_temporary_credentials(creds)
    
    def validate_query(self, query: str, bee_permissions: List[str]) -> bool:
        """Validate query against security policies"""
        # Check for forbidden operations
        forbidden_ops = ['DROP', 'TRUNCATE', 'DELETE', 'UPDATE']
        if not self._has_write_permission(bee_permissions):
            for op in forbidden_ops:
                if op in query.upper():
                    return False
        
        # Check data access policies
        return self.policy_engine.evaluate_query(query, bee_permissions)
    
    def apply_row_level_security(self, query: str, bee_identity: Dict) -> str:
        """Apply RLS filters based on bee identity"""
        # Add WHERE clauses based on bee's data access rights
        rls_filters = self._get_rls_filters(bee_identity)
        return self._inject_filters(query, rls_filters)
```

## Configuration Examples

### Basic Database Connection

```yaml
# hive-config.yml
worker_bees:
  - id: "sales-db-bee"
    type: "postgresql"
    source:
      host: "sales-db.internal"
      port: 5432
      database: "sales_data"
      ssl_mode: "require"
    permissions:
      - "read:sales_data"
      - "read:customer_data"
    security:
      row_level_security: true
      max_rows: 10000
      timeout: 300
```

### Enterprise IdP Integration

```yaml
# identity-config.yml
identity_hive:
  primary_provider: "azure_ad"
  providers:
    azure_ad:
      tenant_id: "your-tenant-id"
      client_id: "your-client-id"
      authority: "https://login.microsoftonline.com"
      scopes:
        - "User.Read"
        - "Group.Read.All"
    
  passkey_config:
    enabled: true
    attestation: "direct"
    user_verification: "required"
    backup_eligible: true
    
  group_mappings:
    "SalesTeam": ["read:sales_data", "write:reports"]
    "Analytics": ["read:all_data", "create:honey_jars"]
    "Admins": ["admin:all"]
```

### Connection Pool Configuration

```yaml
# connection-pool.yml
hive_connection_pool:
  global_settings:
    max_total_connections: 200
    connection_timeout: 30
    idle_timeout: 600
    
  per_source_limits:
    production_db:
      max_connections: 50
      min_connections: 5
    analytics_db:
      max_connections: 20
      min_connections: 2
    
  health_checks:
    interval: 60
    timeout: 5
    failure_threshold: 3
```

## Deployment Architecture

```yaml
production_deployment:
  worker_bee_cluster:
    replicas: 3
    resources:
      cpu: "2"
      memory: "4Gi"
    
  connection_gateway:
    type: "pgbouncer"  # For PostgreSQL
    config:
      pool_mode: "transaction"
      max_client_conn: 1000
      default_pool_size: 25
    
  security_layer:
    vault:
      enabled: true
      auto_unseal: true
    
    network_policies:
      ingress:
        - from: "honey-jar-namespace"
          ports: ["5432", "3306", "27017"]
      egress:
        - to: "data-source-cidrs"
          ports: ["443", "5432", "3306"]
```

## Monitoring and Observability

```python
class WorkerBeeMetrics:
    """Metrics collection for Worker Bee operations"""
    
    def __init__(self):
        self.prometheus_registry = CollectorRegistry()
        self._setup_metrics()
        
    def _setup_metrics(self):
        self.nectar_collected = Counter(
            'worker_bee_nectar_collected_total',
            'Total amount of data collected',
            ['bee_type', 'source']
        )
        
        self.flight_duration = Histogram(
            'worker_bee_flight_duration_seconds',
            'Time spent collecting data',
            ['bee_type', 'source']
        )
        
        self.active_bees = Gauge(
            'worker_bee_active_count',
            'Number of active Worker Bees',
            ['bee_type']
        )
        
        self.error_count = Counter(
            'worker_bee_errors_total',
            'Total number of errors',
            ['bee_type', 'error_type']
        )
```

## Honey Comb Integration

Worker Bees seamlessly integrate with Honey Combs to enable rapid data connectivity. Honey Combs provide the configuration templates that Worker Bees use to establish connections and collect data.

### Worker Bee + Honey Comb Workflow

```python
class HoneyCombAwareWorkerBee(WorkerBee):
    """Enhanced Worker Bee that uses Honey Comb configurations"""
    
    def __init__(self, honey_comb: Dict[str, Any]):
        super().__init__(honey_comb.get('hive_config', {}))
        self.comb = honey_comb
        self.scrubber = self._init_scrubber()
        
    async def collect_from_comb(self, mode: str = 'continuous') -> Union[AsyncIterator, HoneyJar]:
        """Collect data using Honey Comb configuration"""
        if mode == 'continuous':
            return self._continuous_collection()
        elif mode == 'snapshot':
            return await self._generate_honey_jar()
        else:
            raise ValueError(f"Unknown collection mode: {mode}")
    
    async def _continuous_collection(self) -> AsyncIterator[Dict[str, Any]]:
        """Stream data continuously to existing Honey Jar"""
        connection_params = await self._get_connection_params()
        
        async with self._connect(connection_params) as conn:
            query = self.comb['extraction']['query_template']
            
            async for batch in self._stream_query(conn, query):
                # Apply scrubbing if configured
                if self.comb['scrubbing']['enabled']:
                    batch = await self.scrubber.process(batch)
                
                yield batch
    
    async def _generate_honey_jar(self) -> HoneyJar:
        """Create new Honey Jar from data snapshot"""
        connection_params = await self._get_connection_params()
        
        async with self._connect(connection_params) as conn:
            # Collect all data
            data = await self._execute_snapshot_query(conn)
            
            # Apply scrubbing
            if self.comb['scrubbing']['enabled']:
                data = await self.scrubber.process(data)
            
            # Create new Honey Jar
            return HoneyJar.create(
                name=f"{self.comb['name']}_snapshot_{datetime.now().isoformat()}",
                data=data,
                metadata={
                    'source_comb': self.comb['id'],
                    'scrubbing_applied': self.comb['scrubbing']['enabled']
                }
            )
```

### Honey Comb Configuration Loading

```python
class CombLibrary:
    """Manages Honey Comb templates and configurations"""
    
    def __init__(self):
        self.system_combs = self._load_system_combs()
        self.custom_combs = {}
        
    def get_comb(self, comb_id: str) -> Dict[str, Any]:
        """Retrieve a Honey Comb configuration"""
        if comb_id in self.system_combs:
            return self.system_combs[comb_id]
        return self.custom_combs.get(comb_id)
    
    def create_worker_bee(self, comb_id: str) -> WorkerBee:
        """Create appropriate Worker Bee for the Comb type"""
        comb = self.get_comb(comb_id)
        
        bee_mapping = {
            'postgresql': PostgreSQLWorkerBee,
            'mysql': MySQLWorkerBee,
            'mongodb': MongoDBWorkerBee,
            'rest': RESTAPIWorkerBee,
            's3': S3WorkerBee,
            'kafka': KafkaWorkerBee
        }
        
        bee_class = bee_mapping.get(comb['subtype'])
        if not bee_class:
            raise ValueError(f"No Worker Bee available for {comb['subtype']}")
            
        return bee_class(comb)
```

### Scrubbing Integration

```python
class DataScrubber:
    """Handles PII removal and data masking for Honey Combs"""
    
    def __init__(self, scrubbing_config: Dict[str, Any]):
        self.config = scrubbing_config
        self.profile = self._load_profile(scrubbing_config.get('profile_id'))
        
    async def process(self, data: Any) -> Any:
        """Apply scrubbing rules to data"""
        if isinstance(data, pd.DataFrame):
            return await self._scrub_dataframe(data)
        elif isinstance(data, dict):
            return await self._scrub_dict(data)
        elif isinstance(data, list):
            return await self._scrub_list(data)
        else:
            return data
    
    async def _scrub_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply scrubbing to pandas DataFrame"""
        for rule in self.config.get('custom_rules', []):
            if 'field' in rule:
                if rule['field'] in df.columns:
                    df[rule['field']] = self._apply_action(
                        df[rule['field']], 
                        rule['action']
                    )
        return df
```

## Next Steps

1. **Implement Core Framework**
   - Base WorkerBee class
   - PostgreSQL and MySQL connectors
   - Basic security controls

2. **Identity Provider Integration**
   - SAML/OIDC support
   - Passkey enhancement
   - Group mapping system

3. **Production Hardening**
   - Connection pool optimization
   - Circuit breaker patterns
   - Comprehensive monitoring

4. **Extended Connectors**
   - NoSQL databases (MongoDB, DynamoDB)
   - Cloud storage (S3, Azure Blob)
   - SaaS APIs (Salesforce, ServiceNow)

---

*This framework provides the technical foundation for Worker Bee data connectors while maintaining consistency with STING's existing architecture and bee metaphors.*