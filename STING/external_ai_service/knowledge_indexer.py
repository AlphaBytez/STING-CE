#!/usr/bin/env python3
"""
ChromaDB Knowledge Indexer for Bee
Indexes brain knowledge and documentation for fast semantic search
"""

import os
import logging
import asyncio
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class KnowledgeIndexer:
    """Manages ChromaDB indexing for Bee's knowledge base"""

    def __init__(
        self,
        chroma_host: str = "chroma",
        chroma_port: int = 8000,
        collection_name: str = "bee_knowledge"
    ):
        """Initialize ChromaDB client"""
        try:
            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=Settings(anonymized_telemetry=False)
            )
            # Test connection
            self.client.heartbeat()
            logger.info(f"✅ Connected to ChromaDB at {chroma_host}:{chroma_port}")
            self.enabled = True
        except Exception as e:
            logger.error(f"❌ Failed to connect to ChromaDB: {e}")
            logger.warning("Semantic search will not be available")
            self.client = None
            self.enabled = False

        self.collection_name = collection_name
        self.collection = None

    def _get_or_create_collection(self) -> Optional[Any]:
        """Get or create ChromaDB collection"""
        if not self.enabled:
            return None

        try:
            # Try to get existing collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"📚 Loaded existing collection: {self.collection_name}")
            except Exception:
                # Create new collection
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Bee's brain knowledge and documentation"}
                )
                logger.info(f"📚 Created new collection: {self.collection_name}")

            return self.collection

        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            return None

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better semantic search"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Find chunk boundaries (try to break at sentence/paragraph)
            end = start + chunk_size

            if end < len(text):
                # Try to find a good break point (period, newline, etc.)
                break_chars = ['\n\n', '\n', '. ', '! ', '? ']
                best_break = end

                for break_char in break_chars:
                    last_break = text.rfind(break_char, start, end)
                    if last_break != -1:
                        best_break = last_break + len(break_char)
                        break

                end = best_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap, ensuring forward progress
            if end < len(text):
                # Use overlap but ensure we move forward
                new_start = end - overlap
                start = max(new_start, start + 1)  # Always move forward by at least 1
            else:
                start = end  # At end of text, exit loop

        return chunks

    def _generate_id(self, text: str, prefix: str = "", section_idx: int = 0, chunk_idx: int = 0) -> str:
        """Generate unique ID for a document - includes section and chunk indices for uniqueness"""
        hash_obj = hashlib.md5(text.encode())
        return f"{prefix}_s{section_idx}_c{chunk_idx}_{hash_obj.hexdigest()[:8]}"

    def index_brain_knowledge(self, brain_text: str) -> bool:
        """Index Bee's brain knowledge into ChromaDB"""
        if not self.enabled:
            return False

        try:
            collection = self._get_or_create_collection()
            if not collection:
                return False

            logger.info(f"Indexing brain knowledge ({len(brain_text)} chars)...")

            # Split brain into sections by headers
            logger.info("Splitting brain into sections...")
            sections = []
            current_section = []
            current_header = "Introduction"

            for line in brain_text.split('\n'):
                if line.startswith('#'):
                    # Save previous section
                    if current_section:
                        section_text = '\n'.join(current_section).strip()
                        if section_text:
                            sections.append({
                                'header': current_header,
                                'content': section_text
                            })

                    # Start new section
                    current_header = line.strip('# ').strip()
                    current_section = []
                else:
                    current_section.append(line)

            # Save last section
            if current_section:
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    sections.append({
                        'header': current_header,
                        'content': section_text
                    })

            logger.info(f"Found {len(sections)} sections, chunking...")

            # Chunk each section and index
            documents = []
            metadatas = []
            ids = []

            logger.info(f"Processing {len(sections)} sections into chunks...")
            for idx, section in enumerate(sections):
                # Log progress every 20 sections, plus extra for final sections
                if idx % 20 == 0 or idx >= 140:
                    logger.info(f"  Processing section {idx+1}/{len(sections)}: {section['header'][:50]}...")

                # Chunk large sections
                try:
                    chunks = self._chunk_text(section['content'], chunk_size=800, overlap=150)
                    if idx >= 140:
                        logger.info(f"    → Section {idx+1} produced {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error chunking section {idx+1} '{section['header']}': {e}")
                    continue

                for i, chunk in enumerate(chunks):
                    try:
                        doc_id = self._generate_id(chunk, f"brain", section_idx=idx, chunk_idx=i)
                        documents.append(chunk)
                        metadatas.append({
                            'source': 'bee_brain',
                            'section': section['header'],
                            'chunk': i,
                            'type': 'knowledge'
                        })
                        ids.append(doc_id)
                    except Exception as e:
                        logger.error(f"Error processing chunk {i} of section {idx+1}: {e}")
                        continue

            logger.info(f"✓ Prepared {len(documents)} document chunks for indexing")

            # Add to ChromaDB in batches to avoid hanging on large additions
            batch_size = 10  # Process 10 chunks at a time
            total = len(documents)
            logger.info(f"Adding {total} chunks in batches of {batch_size}...")

            for i in range(0, total, batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]

                try:
                    collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    logger.info(f"  ✓ Batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}: {len(batch_docs)} chunks added")
                except Exception as e:
                    logger.error(f"  ✗ Batch {i//batch_size + 1} failed: {e}")
                    # Continue with next batch even if one fails
                    continue

            logger.info(f"✅ Indexed {len(documents)} brain knowledge chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to index brain knowledge: {e}")
            return False

    def index_documentation(self, docs_path: Path) -> bool:
        """Index documentation files into ChromaDB"""
        if not self.enabled:
            return False

        try:
            collection = self._get_or_create_collection()
            if not collection:
                return False

            logger.info(f"Indexing documentation from {docs_path}...")

            # Priority documentation files
            priority_docs = [
                "README.md",
                "ARCHITECTURE.md",
                "DATA_PROTECTION_ARCHITECTURE.md",
                "WORKER_BEE_CONNECTOR_FRAMEWORK.md",
                "REPORT_GENERATION_FRAMEWORK.md",
                "AI_ASSISTANT.md"
            ]

            documents = []
            metadatas = []
            ids = []

            # Index priority docs from root
            root_path = docs_path.parent
            for doc_name in priority_docs:
                doc_path = root_path / doc_name
                if doc_path.exists():
                    logger.info(f"  Indexing priority doc: {doc_name}")
                    content = doc_path.read_text(encoding='utf-8')

                    # Chunk the document
                    chunks = self._chunk_text(content, chunk_size=1000, overlap=200)

                    for i, chunk in enumerate(chunks):
                        doc_id = self._generate_id(chunk, f"doc_{doc_name}")
                        documents.append(chunk)
                        metadatas.append({
                            'source': doc_name,
                            'path': str(doc_path.relative_to(root_path)),
                            'chunk': i,
                            'type': 'documentation',
                            'priority': True
                        })
                        ids.append(doc_id)

            # Index docs from docs/ directory
            if docs_path.exists():
                for md_file in docs_path.rglob("*.md"):
                    relative_path = str(md_file.relative_to(root_path))

                    # Skip if already indexed as priority
                    if md_file.name in priority_docs:
                        continue

                    content = md_file.read_text(encoding='utf-8')

                    # Chunk the document
                    chunks = self._chunk_text(content, chunk_size=1000, overlap=200)

                    for i, chunk in enumerate(chunks):
                        doc_id = self._generate_id(chunk, f"doc_{md_file.name}")
                        documents.append(chunk)
                        metadatas.append({
                            'source': md_file.name,
                            'path': relative_path,
                            'chunk': i,
                            'type': 'documentation',
                            'priority': False
                        })
                        ids.append(doc_id)

            # Add to ChromaDB in batches
            if documents:
                batch_size = 10  # Process 10 chunks at a time
                total = len(documents)
                logger.info(f"Adding {total} documentation chunks in batches of {batch_size}...")

                for i in range(0, total, batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_metas = metadatas[i:i+batch_size]
                    batch_ids = ids[i:i+batch_size]

                    try:
                        collection.add(
                            documents=batch_docs,
                            metadatas=batch_metas,
                            ids=batch_ids
                        )
                        logger.info(f"  ✓ Batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}: {len(batch_docs)} chunks added")
                    except Exception as e:
                        logger.error(f"  ✗ Batch {i//batch_size + 1} failed: {e}")
                        continue

                logger.info(f"✅ Indexed {len(documents)} documentation chunks")
                return True
            else:
                logger.warning("No documentation files found to index")
                return False

        except Exception as e:
            logger.error(f"Failed to index documentation: {e}")
            return False

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search indexed knowledge using semantic search"""
        if not self.enabled:
            return []

        try:
            if not self.collection:
                self.collection = self._get_or_create_collection()
                if not self.collection:
                    return []

            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_metadata
            )

            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0

                    formatted_results.append({
                        'content': doc,
                        'metadata': metadata,
                        'score': 1.0 - distance,  # Convert distance to similarity score
                        'source': metadata.get('source', 'unknown')
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self.enabled:
            return {"enabled": False}

        try:
            if not self.collection:
                self.collection = self._get_or_create_collection()
                if not self.collection:
                    return {"enabled": True, "error": "No collection"}

            count = self.collection.count()

            return {
                "enabled": True,
                "collection_name": self.collection_name,
                "document_count": count,
                "status": "healthy"
            }

        except Exception as e:
            return {
                "enabled": True,
                "error": str(e),
                "status": "unhealthy"
            }

    def clear_collection(self) -> bool:
        """Clear all documents from collection (useful for re-indexing)"""
        if not self.enabled:
            return False

        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None
            logger.info(f"🗑️  Cleared collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False


# Global instance
_knowledge_indexer = None
_auto_index_task = None

def get_knowledge_indexer() -> KnowledgeIndexer:
    """Get or create global knowledge indexer instance"""
    global _knowledge_indexer
    if _knowledge_indexer is None:
        _knowledge_indexer = KnowledgeIndexer()
    return _knowledge_indexer


class BrainAutoIndexer:
    """
    Automatically indexes Bee Brain files when they change.
    Uses hash-based change detection to avoid unnecessary re-indexing.
    """

    def __init__(
        self,
        brain_dir: str = "/app",
        brain_pattern: str = "bee_brain*.md",
        check_interval: int = 60  # Check every 60 seconds
    ):
        self.brain_dir = Path(brain_dir)
        self.brain_pattern = brain_pattern
        self.check_interval = check_interval
        self.indexed_hashes: Dict[str, str] = {}  # filename -> content hash
        self.indexer = get_knowledge_indexer()
        self._running = False
        self._last_index_time = 0
        self._debounce_seconds = 5  # Wait 5 seconds after change before indexing

    def _compute_file_hash(self, filepath: Path) -> str:
        """Compute SHA256 hash of file content"""
        try:
            content = filepath.read_text(encoding='utf-8')
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash {filepath}: {e}")
            return ""

    def _get_brain_files(self) -> List[Path]:
        """Find all brain files matching pattern"""
        try:
            import glob
            pattern = str(self.brain_dir / self.brain_pattern)
            files = [Path(f) for f in glob.glob(pattern)]
            return sorted(files)
        except Exception as e:
            logger.error(f"Failed to find brain files: {e}")
            return []

    def check_and_index(self) -> Dict[str, Any]:
        """
        Check for brain file changes and re-index if needed.
        Returns status dict.
        """
        import time

        if not self.indexer.enabled:
            return {"status": "disabled", "message": "ChromaDB not available"}

        brain_files = self._get_brain_files()
        if not brain_files:
            return {"status": "no_files", "message": "No brain files found"}

        changes_detected = []
        current_hashes = {}

        for brain_file in brain_files:
            file_hash = self._compute_file_hash(brain_file)
            current_hashes[brain_file.name] = file_hash

            # Check if this file is new or changed
            if brain_file.name not in self.indexed_hashes:
                changes_detected.append({"file": brain_file.name, "reason": "new"})
            elif self.indexed_hashes[brain_file.name] != file_hash:
                changes_detected.append({"file": brain_file.name, "reason": "modified"})

        if not changes_detected:
            return {"status": "current", "message": "Brain index is up to date", "files": list(current_hashes.keys())}

        # Debounce - wait a bit in case more changes are coming
        time_since_last = time.time() - self._last_index_time
        if time_since_last < self._debounce_seconds:
            return {"status": "debouncing", "message": f"Waiting for changes to settle ({self._debounce_seconds - time_since_last:.1f}s)"}

        logger.info(f"🔄 Brain changes detected: {changes_detected}")

        # Re-index all brain files
        try:
            # Clear old index first
            logger.info("🗑️ Clearing old brain index...")
            self.indexer.clear_collection()

            # Index all brain files
            total_indexed = 0
            for brain_file in brain_files:
                logger.info(f"📚 Indexing {brain_file.name}...")
                try:
                    content = brain_file.read_text(encoding='utf-8')
                    if self.indexer.index_brain_knowledge(content):
                        total_indexed += 1
                        self.indexed_hashes[brain_file.name] = current_hashes[brain_file.name]
                except Exception as e:
                    logger.error(f"Failed to index {brain_file.name}: {e}")

            self._last_index_time = time.time()

            return {
                "status": "reindexed",
                "message": f"Re-indexed {total_indexed} brain files",
                "changes": changes_detected,
                "files_indexed": total_indexed
            }

        except Exception as e:
            logger.error(f"Auto-indexing failed: {e}")
            return {"status": "error", "message": str(e)}

    async def start_background_watcher(self):
        """Start background task to watch for brain file changes"""
        import asyncio

        if self._running:
            logger.warning("Auto-indexer already running")
            return

        self._running = True
        logger.info(f"🔍 Starting brain auto-indexer (checking every {self.check_interval}s)")

        # Initial index check
        result = self.check_and_index()
        logger.info(f"Initial brain index check: {result.get('status')} - {result.get('message')}")

        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                result = self.check_and_index()
                if result.get('status') == 'reindexed':
                    logger.info(f"🔄 Brain auto-reindex: {result.get('message')}")
            except asyncio.CancelledError:
                logger.info("Brain auto-indexer stopped")
                break
            except Exception as e:
                logger.error(f"Auto-indexer error: {e}")
                await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the background watcher"""
        self._running = False


# Global auto-indexer instance
_brain_auto_indexer: Optional[BrainAutoIndexer] = None

def get_brain_auto_indexer() -> BrainAutoIndexer:
    """Get or create global brain auto-indexer instance"""
    global _brain_auto_indexer
    if _brain_auto_indexer is None:
        _brain_auto_indexer = BrainAutoIndexer()
    return _brain_auto_indexer


async def start_auto_indexer():
    """Start the brain auto-indexer background task"""
    global _auto_index_task
    auto_indexer = get_brain_auto_indexer()
    _auto_index_task = asyncio.create_task(auto_indexer.start_background_watcher())
    return _auto_index_task


# Test the knowledge indexer
if __name__ == "__main__":
    import asyncio

    async def test_knowledge_indexer():
        indexer = KnowledgeIndexer()

        # Test stats
        print("\n=== ChromaDB Stats ===")
        stats = indexer.get_stats()
        print(f"Enabled: {stats.get('enabled')}")
        print(f"Documents: {stats.get('document_count', 0)}")

        # Test indexing brain knowledge
        print("\n=== Indexing Test Brain ===")
        test_brain = """
# Authentication System
STING uses Ory Kratos for authentication with support for passkeys and TOTP.

# Honey Jars
Honey Jars are secure document repositories with encryption and access controls.

# Security Features
- AAL2 authentication for sensitive operations
- PII detection and scrambling
- End-to-end encryption
"""
        indexer.index_brain_knowledge(test_brain)

        # Test search
        print("\n=== Search Test ===")
        results = indexer.search("How does authentication work?", n_results=3)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.3f}")
            print(f"   Source: {result['source']}")
            print(f"   Content: {result['content'][:100]}...")

        # Test stats after indexing
        print("\n=== Stats After Indexing ===")
        stats = indexer.get_stats()
        print(f"Documents: {stats.get('document_count', 0)}")

    asyncio.run(test_knowledge_indexer())
