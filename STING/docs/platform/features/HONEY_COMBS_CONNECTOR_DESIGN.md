# Honey Combs Connector Design

## Executive Summary

This document provides the detailed implementation design for Honey Combs - the data source configuration templates that enable rapid, secure connectivity within STING. It covers the technical architecture, UI/UX integration, and implementation roadmap.

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           STING Frontend                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ Honey Jar View  │  │ Comb Library UI  │  │ Connection Wizard  │    │
│  └────────┬────────┘  └────────┬─────────┘  └─────────┬──────────┘    │
└───────────┼───────────────────┼──────────────────────┼────────────────┘
            │                   │                        │
            ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Honey Comb Service API                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ Comb Manager    │  │ Template Engine   │  │ Execution Engine   │    │
│  └────────┬────────┘  └────────┬─────────┘  └─────────┬──────────┘    │
└───────────┼───────────────────┼──────────────────────┼────────────────┘
            │                   │                        │
            ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Worker Bee Framework                            │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ DB Worker Bees  │  │ API Worker Bees  │  │ Stream Worker Bees │    │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
            │                   │                        │
            ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Scrubbing & Security Layer                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│  │ PII Detector    │  │ Data Tokenizer   │  │ Audit Logger       │    │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Database Honey Combs

### PostgreSQL Comb

```python
class PostgreSQLHoneyComb:
    """PostgreSQL database connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "database",
        "subtype": "postgresql",
        "display_name": "PostgreSQL Database",
        "icon": "database",
        "connection_params": {
            "host": {"required": True, "type": "string"},
            "port": {"required": True, "type": "int", "default": 5432},
            "database": {"required": True, "type": "string"},
            "username": {"required": True, "type": "string", "vault": True},
            "password": {"required": True, "type": "password", "vault": True},
            "ssl_mode": {"required": False, "type": "enum", 
                        "values": ["disable", "require", "verify-ca", "verify-full"],
                        "default": "require"}
        },
        "extraction_options": {
            "table_selection": {
                "type": "multi_select",
                "discover_endpoint": "/discover/tables"
            },
            "query_mode": {
                "type": "enum",
                "values": ["full_table", "custom_query", "incremental"],
                "default": "full_table"
            },
            "custom_query": {
                "type": "sql_editor",
                "when": {"query_mode": "custom_query"}
            },
            "incremental_column": {
                "type": "column_select",
                "when": {"query_mode": "incremental"}
            }
        },
        "scrubbing_options": {
            "auto_detect_pii": {"type": "boolean", "default": True},
            "column_rules": {
                "type": "mapping",
                "key": "column_name",
                "value": {
                    "action": ["keep", "remove", "hash", "mask", "tokenize"],
                    "pattern": "regex"
                }
            }
        }
    }
    
    async def test_connection(self, config: Dict) -> Tuple[bool, str]:
        """Test database connectivity"""
        try:
            conn = await asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password'],
                ssl=config.get('ssl_mode', 'require')
            )
            await conn.fetchval('SELECT 1')
            await conn.close()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
    
    async def discover_schema(self, config: Dict) -> Dict[str, List[str]]:
        """Discover database schema"""
        conn = await self._get_connection(config)
        
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        
        schema = {}
        for table in tables:
            schema_name = table['table_schema']
            table_name = table['table_name']
            
            # Get columns for each table
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
            """, schema_name, table_name)
            
            schema[f"{schema_name}.{table_name}"] = [
                {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES'
                }
                for col in columns
            ]
        
        await conn.close()
        return schema
```

### MongoDB Comb

```python
class MongoDBHoneyComb:
    """MongoDB connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "database",
        "subtype": "mongodb",
        "display_name": "MongoDB",
        "icon": "document_database",
        "connection_params": {
            "connection_string": {
                "required": True, 
                "type": "string",
                "placeholder": "mongodb://username:password@host:port/database",
                "vault": True
            },
            "tls": {"required": False, "type": "boolean", "default": True},
            "auth_mechanism": {
                "required": False,
                "type": "enum",
                "values": ["SCRAM-SHA-256", "SCRAM-SHA-1", "MONGODB-X509"],
                "default": "SCRAM-SHA-256"
            }
        },
        "extraction_options": {
            "collection_selection": {
                "type": "multi_select",
                "discover_endpoint": "/discover/collections"
            },
            "query_filter": {
                "type": "json_editor",
                "placeholder": '{"status": "active"}'
            },
            "projection": {
                "type": "json_editor",
                "placeholder": '{"_id": 0, "name": 1, "email": 1}'
            }
        }
    }
```

## API Honey Combs

### REST API Comb

```python
class RESTAPIHoneyComb:
    """REST API connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "api",
        "subtype": "rest",
        "display_name": "REST API",
        "icon": "api",
        "connection_params": {
            "base_url": {"required": True, "type": "url"},
            "auth_type": {
                "required": True,
                "type": "enum",
                "values": ["none", "api_key", "bearer", "oauth2", "basic"],
                "default": "none"
            },
            "api_key": {
                "required": False,
                "type": "string",
                "vault": True,
                "when": {"auth_type": "api_key"}
            },
            "api_key_header": {
                "required": False,
                "type": "string",
                "default": "X-API-Key",
                "when": {"auth_type": "api_key"}
            },
            "bearer_token": {
                "required": False,
                "type": "string",
                "vault": True,
                "when": {"auth_type": "bearer"}
            }
        },
        "extraction_options": {
            "endpoints": {
                "type": "endpoint_builder",
                "allow_multiple": True
            },
            "pagination": {
                "type": "object",
                "fields": {
                    "type": ["none", "offset", "cursor", "page"],
                    "page_size": {"type": "int", "default": 100},
                    "max_pages": {"type": "int", "default": 1000}
                }
            },
            "rate_limiting": {
                "type": "object",
                "fields": {
                    "requests_per_minute": {"type": "int", "default": 60},
                    "retry_strategy": ["exponential", "linear", "none"]
                }
            }
        }
    }
```

### GraphQL Comb

```python
class GraphQLHoneyComb:
    """GraphQL API connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "api",
        "subtype": "graphql",
        "display_name": "GraphQL API",
        "icon": "graphql",
        "connection_params": {
            "endpoint": {"required": True, "type": "url"},
            "headers": {
                "type": "key_value_pairs",
                "vault_values": True
            }
        },
        "extraction_options": {
            "query": {
                "type": "graphql_editor",
                "schema_introspection": True
            },
            "variables": {
                "type": "json_editor"
            }
        }
    }
```

## File System Honey Combs

### S3 Comb

```python
class S3HoneyComb:
    """AWS S3 connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "file_system",
        "subtype": "s3",
        "display_name": "Amazon S3",
        "icon": "s3",
        "connection_params": {
            "bucket": {"required": True, "type": "string"},
            "region": {"required": True, "type": "aws_region"},
            "access_key_id": {"required": True, "type": "string", "vault": True},
            "secret_access_key": {"required": True, "type": "password", "vault": True},
            "endpoint_url": {"required": False, "type": "url"}
        },
        "extraction_options": {
            "prefix": {"type": "string", "placeholder": "data/2024/"},
            "file_patterns": {
                "type": "multi_pattern",
                "examples": ["*.csv", "*.json", "*.parquet"]
            },
            "recursive": {"type": "boolean", "default": True}
        }
    }
```

## Stream Honey Combs

### Kafka Comb

```python
class KafkaHoneyComb:
    """Apache Kafka connector configuration"""
    
    DEFAULT_CONFIG = {
        "type": "stream",
        "subtype": "kafka",
        "display_name": "Apache Kafka",
        "icon": "kafka",
        "connection_params": {
            "bootstrap_servers": {
                "required": True,
                "type": "string",
                "placeholder": "broker1:9092,broker2:9092"
            },
            "security_protocol": {
                "required": True,
                "type": "enum",
                "values": ["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"],
                "default": "PLAINTEXT"
            },
            "sasl_mechanism": {
                "required": False,
                "type": "enum",
                "values": ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"],
                "when": {"security_protocol": ["SASL_PLAINTEXT", "SASL_SSL"]}
            }
        },
        "extraction_options": {
            "topics": {
                "type": "multi_select",
                "discover_endpoint": "/discover/topics"
            },
            "consumer_group": {
                "type": "string",
                "default": "sting_worker_bee"
            },
            "start_from": {
                "type": "enum",
                "values": ["latest", "earliest", "timestamp"],
                "default": "latest"
            }
        }
    }
```

## Scrubbing Engine Design

### PII Detection Pipeline

```python
class PIIDetector:
    """Detect personally identifiable information in data"""
    
    def __init__(self):
        self.detectors = {
            'email': EmailDetector(),
            'phone': PhoneDetector(),
            'ssn': SSNDetector(),
            'credit_card': CreditCardDetector(),
            'address': AddressDetector(),
            'name': NameDetector(),
            'date_of_birth': DOBDetector()
        }
        
    async def scan_dataframe(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Scan DataFrame for PII"""
        pii_columns = defaultdict(list)
        
        for column in df.columns:
            sample_data = df[column].dropna().head(1000)
            
            for pii_type, detector in self.detectors.items():
                if detector.check_column(sample_data):
                    pii_columns[pii_type].append(column)
        
        return dict(pii_columns)
    
    async def scan_json(self, data: Dict, path: str = "") -> List[Dict]:
        """Scan JSON structure for PII"""
        pii_locations = []
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                pii_locations.extend(
                    await self.scan_json(value, current_path)
                )
            elif isinstance(value, list) and value:
                if isinstance(value[0], dict):
                    for i, item in enumerate(value[:10]):  # Sample first 10
                        pii_locations.extend(
                            await self.scan_json(item, f"{current_path}[{i}]")
                        )
                else:
                    # Check list of primitives
                    for pii_type, detector in self.detectors.items():
                        if detector.check_values(value[:100]):  # Sample
                            pii_locations.append({
                                'path': current_path,
                                'type': pii_type,
                                'confidence': detector.confidence
                            })
            else:
                # Check primitive value
                for pii_type, detector in self.detectors.items():
                    if detector.check_value(str(value)):
                        pii_locations.append({
                            'path': current_path,
                            'type': pii_type,
                            'confidence': detector.confidence
                        })
        
        return pii_locations
```

### Scrubbing Actions

```python
class ScrubberActions:
    """Available scrubbing actions for PII"""
    
    @staticmethod
    def remove(value: Any) -> None:
        """Remove the value entirely"""
        return None
    
    @staticmethod
    def hash(value: str, salt: str = "") -> str:
        """One-way hash the value"""
        return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()[:16]
    
    @staticmethod
    def mask(value: str, visible_chars: int = 4) -> str:
        """Mask all but last N characters"""
        if len(value) <= visible_chars:
            return "*" * len(value)
        return "*" * (len(value) - visible_chars) + value[-visible_chars:]
    
    @staticmethod
    def tokenize(value: str, token_vault: TokenVault) -> str:
        """Replace with reversible token"""
        return token_vault.tokenize(value)
    
    @staticmethod
    def generalize(value: Any, level: str = "medium") -> Any:
        """Generalize to less specific value"""
        if isinstance(value, datetime):
            if level == "low":
                return value.strftime("%Y-%m-%d")
            elif level == "medium":
                return value.strftime("%Y-%m")
            else:
                return value.year
        elif isinstance(value, (int, float)):
            if level == "low":
                return round(value, -1)
            elif level == "medium":
                return round(value, -2)
            else:
                return round(value, -3)
        else:
            return "<REDACTED>"
```

## UI/UX Integration

### Honey Jar Interface Enhancement

Within the existing Honey Jar management interface, add:

1. **Quick Connect Button**
   - Located in the header of the Honey Jar list view
   - Opens the Comb Library modal
   - Shows "Connect Data Source" with a honeycomb icon

2. **Comb Library Modal**
   ```typescript
   interface CombLibraryModalProps {
     onSelectComb: (combId: string) => void;
     currentHoneyJar?: HoneyJar;
   }
   
   const CombLibraryModal: React.FC<CombLibraryModalProps> = ({ onSelectComb, currentHoneyJar }) => {
     const [selectedCategory, setSelectedCategory] = useState<string>('all');
     const [searchQuery, setSearchQuery] = useState<string>('');
     
     return (
       <Modal title="Choose a Honey Comb" size="large">
         <div className="comb-library">
           <CategoryFilter 
             categories={['all', 'database', 'api', 'file_system', 'stream']}
             selected={selectedCategory}
             onChange={setSelectedCategory}
           />
           
           <SearchBar 
             placeholder="Search combs..."
             value={searchQuery}
             onChange={setSearchQuery}
           />
           
           <CombGrid>
             {filteredCombs.map(comb => (
               <CombCard
                 key={comb.id}
                 comb={comb}
                 onClick={() => onSelectComb(comb.id)}
               />
             ))}
           </CombGrid>
         </div>
       </Modal>
     );
   };
   ```

3. **Connection Wizard**
   - Step 1: Connection parameters
   - Step 2: Data selection (tables, endpoints, etc.)
   - Step 3: Scrubbing configuration
   - Step 4: Output options (continuous vs snapshot)
   - Step 5: Test & Deploy

4. **Active Connections View**
   - Shows live Worker Bees using Honey Combs
   - Real-time metrics (records/sec, last sync, errors)
   - Pause/Resume/Stop controls
   - Edit configuration option

### Visual Design

```css
/* Honey Comb Card */
.comb-card {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: 2px solid #d4a017;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.comb-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(212, 160, 23, 0.3);
}

.comb-card::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: repeating-linear-gradient(
    60deg,
    transparent,
    transparent 10px,
    rgba(255, 255, 255, 0.1) 10px,
    rgba(255, 255, 255, 0.1) 20px
  );
  transform: rotate(30deg);
  pointer-events: none;
}

/* Connection Status Indicator */
.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.connection-status.active {
  background: #d4f4dd;
  color: #2e7d32;
}

.connection-status.error {
  background: #ffebee;
  color: #d32f2f;
}

.connection-status .pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}
```

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Implement Honey Comb data model
- [ ] Create base CombManager service
- [ ] Build PostgreSQL and MySQL combs
- [ ] Basic UI for comb selection

### Phase 2: Scrubbing Engine (Weeks 3-4)
- [ ] Implement PII detection algorithms
- [ ] Create scrubbing action library
- [ ] Build compliance profiles (GDPR, CCPA)
- [ ] Add scrubbing configuration UI

### Phase 3: Extended Connectors (Weeks 5-6)
- [ ] Implement REST API comb
- [ ] Add S3 file system comb
- [ ] Create Kafka stream comb
- [ ] Build discovery endpoints

### Phase 4: Production Features (Weeks 7-8)
- [ ] Add connection pooling
- [ ] Implement retry logic
- [ ] Create monitoring dashboard
- [ ] Add audit logging

### Phase 5: Enterprise Features (Weeks 9-10)
- [ ] Multi-tenant isolation
- [ ] Advanced scheduling
- [ ] Custom comb templates
- [ ] Marketplace integration

## Security Considerations

### Credential Management
```python
class CombCredentialManager:
    """Secure credential management for Honey Combs"""
    
    def __init__(self, vault_client: VaultClient):
        self.vault = vault_client
        self.encryption_key = self._get_or_create_key()
    
    async def store_credentials(self, comb_id: str, credentials: Dict) -> str:
        """Store credentials securely in Vault"""
        path = f"honey_combs/{comb_id}/credentials"
        
        # Encrypt sensitive fields
        encrypted = {}
        for key, value in credentials.items():
            if self._is_sensitive(key):
                encrypted[key] = self._encrypt(value)
            else:
                encrypted[key] = value
        
        # Store in Vault
        await self.vault.write(path, encrypted)
        return path
    
    async def retrieve_credentials(self, comb_id: str) -> Dict:
        """Retrieve and decrypt credentials"""
        path = f"honey_combs/{comb_id}/credentials"
        encrypted = await self.vault.read(path)
        
        # Decrypt sensitive fields
        decrypted = {}
        for key, value in encrypted.items():
            if self._is_sensitive(key):
                decrypted[key] = self._decrypt(value)
            else:
                decrypted[key] = value
        
        return decrypted
```

### Access Control
```python
class CombAccessControl:
    """RBAC for Honey Combs"""
    
    PERMISSIONS = {
        'comb:view': 'View comb configurations',
        'comb:create': 'Create new combs',
        'comb:edit': 'Edit existing combs',
        'comb:delete': 'Delete combs',
        'comb:execute': 'Run data extraction',
        'comb:manage_credentials': 'Manage comb credentials'
    }
    
    async def check_permission(self, user: User, comb: HoneyComb, 
                              action: str) -> bool:
        """Check if user has permission for action"""
        # System combs - read-only for non-admins
        if comb.is_system and action in ['edit', 'delete']:
            return user.role == 'admin'
        
        # Check ownership
        if comb.owner_id == user.id:
            return True
        
        # Check explicit permissions
        return await self.has_permission(user, f"comb:{action}")
```

## Monitoring and Observability

### Metrics Collection
```python
class CombMetrics:
    """Prometheus metrics for Honey Combs"""
    
    def __init__(self):
        self.extraction_duration = Histogram(
            'honey_comb_extraction_duration_seconds',
            'Time spent extracting data',
            ['comb_type', 'mode']
        )
        
        self.records_processed = Counter(
            'honey_comb_records_processed_total',
            'Total records processed',
            ['comb_type', 'honey_jar_id']
        )
        
        self.scrubbing_actions = Counter(
            'honey_comb_scrubbing_actions_total',
            'Scrubbing actions performed',
            ['action_type', 'pii_type']
        )
        
        self.active_connections = Gauge(
            'honey_comb_active_connections',
            'Number of active connections',
            ['comb_type']
        )
```

## Testing Strategy

### Unit Tests
- Comb configuration validation
- Scrubbing engine accuracy
- Connection parameter encryption

### Integration Tests
- End-to-end data extraction
- Scrubbing compliance verification
- Error handling and retry logic

### Performance Tests
- Large dataset handling
- Concurrent connection limits
- Memory usage optimization

## Conclusion

Honey Combs represent a significant advancement in STING's data connectivity capabilities. By providing reusable, secure templates with built-in privacy compliance, they enable organizations to rapidly integrate diverse data sources while maintaining the highest standards of security and governance.

The phased implementation approach ensures that core functionality is delivered quickly while allowing for iterative improvements based on user feedback and real-world usage patterns.