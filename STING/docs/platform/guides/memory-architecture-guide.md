# STING Memory Architecture Guide

## Overview

This guide outlines a comprehensive memory architecture for STING that enables persistent, cross-model memory sharing and long-term learning capabilities.

## Memory Hierarchy

### 1. Working Memory (Session-based)
- **Purpose**: Immediate conversation context
- **Scope**: Current session only
- **Storage**: In-memory (Redis)
- **TTL**: 30 minutes of inactivity
- **Size**: 4-8k tokens

### 2. Short-term Memory (Conversation-based)
- **Purpose**: Recent conversation history
- **Scope**: Last 7 days of conversations
- **Storage**: PostgreSQL + Redis cache
- **TTL**: 7 days rolling window
- **Size**: Up to 100 messages per conversation

### 3. Long-term Memory (User/System-based)
- **Purpose**: Persistent knowledge and preferences
- **Scope**: Permanent storage
- **Storage**: PostgreSQL with vector embeddings
- **TTL**: No expiration (with archival)
- **Size**: Unlimited (with intelligent summarization)

### 4. Shared Knowledge Base
- **Purpose**: Cross-model shared knowledge
- **Scope**: System-wide
- **Storage**: PostgreSQL + Vector DB (pgvector)
- **TTL**: Version controlled
- **Size**: Grows with learning

## Architecture Components

### 1. Unified Memory Service

```python
# /memory_service/unified_memory.py
class UnifiedMemoryService:
    """
    Central memory coordination service that manages all memory tiers
    and provides a unified API for all AI models and services.
    """
    
    def __init__(self):
        self.working_memory = WorkingMemoryManager()  # Redis
        self.short_term = ShortTermMemoryManager()    # PostgreSQL + Redis
        self.long_term = LongTermMemoryManager()      # PostgreSQL + Vectors
        self.knowledge = SharedKnowledgeManager()      # Knowledge Graph
```

### 2. Database Schema

```sql
-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app_users(id),
    model_type VARCHAR(50),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    summary TEXT,
    embedding vector(768)  -- For semantic search
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    embedding vector(768)
);

-- Memory entries
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app_users(id),
    memory_type VARCHAR(50),  -- 'fact', 'preference', 'interaction', 'learned'
    content TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    embedding vector(768),
    expires_at TIMESTAMP  -- Optional expiration
);

-- Knowledge graph nodes
CREATE TABLE knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50),  -- 'entity', 'concept', 'fact'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    properties JSONB,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge graph edges
CREATE TABLE knowledge_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES knowledge_nodes(id),
    target_id UUID REFERENCES knowledge_nodes(id),
    relationship_type VARCHAR(50),
    strength FLOAT DEFAULT 1.0,
    properties JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_memory_entries_user_id ON memory_entries(user_id);
CREATE INDEX idx_memory_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_embedding ON knowledge_nodes USING ivfflat (embedding vector_cosine_ops);
```

### 3. Memory Management Strategies

#### A. Memory Formation
```python
def form_memory(interaction, context):
    """
    Converts interactions into different types of memories
    """
    # Extract entities and facts
    entities = extract_entities(interaction)
    facts = extract_facts(interaction)
    
    # Determine importance
    importance = calculate_importance(interaction, context)
    
    # Create embeddings for semantic search
    embedding = generate_embedding(interaction)
    
    # Store in appropriate memory tier
    if importance > 0.8:
        store_long_term_memory(facts, entities, embedding)
    elif importance > 0.5:
        store_short_term_memory(interaction, embedding)
    
    # Update knowledge graph
    update_knowledge_graph(entities, facts)
```

#### B. Memory Retrieval
```python
def retrieve_relevant_memories(query, context, limit=10):
    """
    Retrieves most relevant memories using hybrid search
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)
    
    # Semantic search
    semantic_results = vector_search(query_embedding, limit * 2)
    
    # Keyword search
    keyword_results = keyword_search(extract_keywords(query), limit * 2)
    
    # Knowledge graph traversal
    graph_results = knowledge_graph_search(query, context)
    
    # Combine and rank results
    combined = combine_search_results(
        semantic_results, 
        keyword_results, 
        graph_results
    )
    
    # Apply recency and importance weighting
    ranked = rank_by_relevance(combined, context)
    
    return ranked[:limit]
```

#### C. Memory Consolidation
```python
def consolidate_memories():
    """
    Periodic process to consolidate and summarize memories
    """
    # Identify related memories
    memory_clusters = cluster_similar_memories()
    
    for cluster in memory_clusters:
        # Generate summary
        summary = summarize_cluster(cluster)
        
        # Create consolidated memory
        consolidated = create_consolidated_memory(summary, cluster)
        
        # Archive original memories
        archive_memories(cluster)
        
        # Update knowledge graph
        update_knowledge_from_consolidation(consolidated)
```

### 4. Cross-Model Memory Sharing

#### A. Memory API
```python
class MemoryAPI:
    """
    RESTful API for memory access across all services
    """
    
    @app.post("/memory/store")
    async def store_memory(memory: MemoryEntry, auth: Auth):
        """Store a new memory entry"""
        
    @app.get("/memory/retrieve")
    async def retrieve_memories(query: str, context: dict, auth: Auth):
        """Retrieve relevant memories"""
        
    @app.post("/memory/update")
    async def update_memory(memory_id: str, updates: dict, auth: Auth):
        """Update existing memory"""
        
    @app.get("/knowledge/query")
    async def query_knowledge(query: str, depth: int = 2):
        """Query the knowledge graph"""
```

#### B. Model Integration
```python
# In each AI model service
class ModelWithMemory:
    def __init__(self):
        self.memory_client = MemoryClient()
        
    async def process_with_memory(self, input_text, context):
        # Retrieve relevant memories
        memories = await self.memory_client.retrieve(
            query=input_text,
            context=context
        )
        
        # Enhance prompt with memories
        enhanced_prompt = self.build_prompt_with_memories(
            input_text, 
            memories
        )
        
        # Process with model
        response = await self.model.generate(enhanced_prompt)
        
        # Store new memories from interaction
        await self.memory_client.store_interaction(
            input=input_text,
            output=response,
            context=context
        )
        
        return response
```

### 5. Privacy and Security

#### A. Memory Encryption
- All memory entries encrypted at rest
- User-specific encryption keys
- Separate encryption for shared knowledge

#### B. Access Control
- User memories isolated by user_id
- Role-based access to shared knowledge
- Audit logging for all memory operations

#### C. Memory Deletion
- User right to be forgotten
- Cascade deletion of related memories
- Scheduled cleanup of expired memories

### 6. Implementation Phases

#### Phase 1: Database Schema and Basic Storage
1. Create database migrations
2. Implement basic CRUD operations
3. Add PostgreSQL storage to existing managers

#### Phase 2: Vector Embeddings and Search
1. Set up pgvector extension
2. Implement embedding generation
3. Add semantic search capabilities

#### Phase 3: Knowledge Graph
1. Implement knowledge node/edge storage
2. Add graph traversal algorithms
3. Create knowledge extraction pipeline

#### Phase 4: Memory Service
1. Build unified memory service
2. Create REST API
3. Integrate with existing services

#### Phase 5: Advanced Features
1. Memory consolidation
2. Importance decay algorithms
3. Cross-model learning

## Configuration

```yaml
# memory_config.yml
memory:
  working:
    backend: redis
    ttl_minutes: 30
    max_size_mb: 100
  
  short_term:
    backend: postgresql
    cache: redis
    retention_days: 7
    max_messages_per_conversation: 100
  
  long_term:
    backend: postgresql
    vector_dim: 768
    importance_threshold: 0.7
    consolidation_interval_hours: 24
  
  knowledge:
    backend: postgresql
    max_graph_depth: 5
    similarity_threshold: 0.8
  
  embeddings:
    model: "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: 32
    cache_embeddings: true
```

## Benefits

1. **Persistent Context**: Conversations and learning persist across restarts
2. **Cross-Model Intelligence**: All models share common knowledge
3. **Personalization**: System learns user preferences over time
4. **Efficient Retrieval**: Hybrid search ensures relevant memory access
5. **Scalability**: Tiered architecture handles growth
6. **Privacy-Preserving**: User data isolation and encryption

## Next Steps

1. Review and approve architecture
2. Create detailed implementation plan
3. Set up development environment
4. Begin Phase 1 implementation