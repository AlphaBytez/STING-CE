#!/usr/bin/env python3
"""
Background Tasks for Knowledge Service

Celery-based background processing for document ingestion,
embedding generation, and other async operations.
"""

import os
import logging
from celery import Celery
from typing import Dict, List, Any
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Create Celery app
celery_app = Celery(
    'knowledge_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['knowledge_service.background_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@celery_app.task(bind=True, name='process_document')
def process_document_task(self, honey_jar_id: str, document_id: str, file_path: str, metadata: Dict[str, Any] = None):
    """
    Background task to process uploaded documents
    """
    try:
        logger.info(f"Starting document processing for {document_id} in honey pot {honey_jar_id}")
        
        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={'stage': 'text_extraction', 'progress': 10}
        )
        
        # Import here to avoid circular imports
        from knowledge_service.core.nectar_processor import NectarProcessor
        from knowledge_service.core.honeycomb_manager import HoneycombManager
        
        processor = NectarProcessor()
        honeycomb = HoneycombManager()
        
        # Extract text from document
        self.update_state(
            state='PROGRESS', 
            meta={'stage': 'text_extraction', 'progress': 30}
        )
        
        extracted_data = processor.extract_text(file_path)
        
        if not extracted_data or not extracted_data.get('text'):
            raise ValueError("Failed to extract text from document")
        
        # Generate embeddings
        self.update_state(
            state='PROGRESS',
            meta={'stage': 'embedding_generation', 'progress': 60}
        )
        
        embeddings = processor.generate_embeddings(
            extracted_data['text'], 
            metadata or {}
        )
        
        # Store in vector database
        self.update_state(
            state='PROGRESS',
            meta={'stage': 'vector_storage', 'progress': 80}
        )
        
        result = honeycomb.store_embeddings(
            honey_jar_id=honey_jar_id,
            document_id=document_id,
            embeddings=embeddings,
            metadata={
                **(metadata or {}),
                'processed_at': datetime.utcnow().isoformat(),
                'file_path': file_path,
                'extraction_method': extracted_data.get('method', 'unknown')
            }
        )
        
        # Final completion
        self.update_state(
            state='SUCCESS',
            meta={
                'stage': 'completed',
                'progress': 100,
                'embeddings_count': len(embeddings),
                'chunks_processed': result.get('chunks_processed', 0),
                'completed_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Successfully processed document {document_id}")
        return {
            'status': 'success',
            'document_id': document_id,
            'honey_jar_id': honey_jar_id,
            'embeddings_count': len(embeddings),
            'processing_time': self.request.time_start
        }
        
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
        )
        raise


@celery_app.task(bind=True, name='bulk_process_documents')
def bulk_process_documents_task(self, honey_jar_id: str, document_specs: List[Dict[str, Any]]):
    """
    Background task to process multiple documents in batch
    """
    try:
        logger.info(f"Starting bulk processing of {len(document_specs)} documents for honey pot {honey_jar_id}")
        
        total_docs = len(document_specs)
        processed_docs = []
        failed_docs = []
        
        for i, doc_spec in enumerate(document_specs):
            try:
                # Update overall progress
                progress = int((i / total_docs) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': f'processing_document_{i+1}',
                        'progress': progress,
                        'current_document': doc_spec.get('filename', f'doc_{i+1}'),
                        'completed': i,
                        'total': total_docs
                    }
                )
                
                # Process individual document
                result = process_document_task.delay(
                    honey_jar_id=honey_jar_id,
                    document_id=doc_spec['document_id'],
                    file_path=doc_spec['file_path'],
                    metadata=doc_spec.get('metadata', {})
                )
                
                # Wait for completion with timeout
                doc_result = result.get(timeout=600)  # 10 minute timeout per doc
                processed_docs.append(doc_result)
                
            except Exception as e:
                logger.error(f"Failed to process document {doc_spec.get('document_id', 'unknown')}: {str(e)}")
                failed_docs.append({
                    'document_id': doc_spec.get('document_id'),
                    'error': str(e)
                })
        
        # Final completion
        self.update_state(
            state='SUCCESS',
            meta={
                'stage': 'completed',
                'progress': 100,
                'processed_count': len(processed_docs),
                'failed_count': len(failed_docs),
                'completed_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Bulk processing completed: {len(processed_docs)} successful, {len(failed_docs)} failed")
        return {
            'status': 'success',
            'honey_jar_id': honey_jar_id,
            'processed_documents': processed_docs,
            'failed_documents': failed_docs,
            'total_processed': len(processed_docs),
            'total_failed': len(failed_docs)
        }
        
    except Exception as e:
        logger.error(f"Bulk processing failed for honey pot {honey_jar_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
        )
        raise


@celery_app.task(bind=True, name='rebuild_honey_jar_index')
def rebuild_honey_jar_index_task(self, honey_jar_id: str):
    """
    Background task to rebuild vector index for a honey pot
    """
    try:
        logger.info(f"Starting index rebuild for honey pot {honey_jar_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'stage': 'index_rebuild', 'progress': 20}
        )
        
        from knowledge_service.core.honeycomb_manager import HoneycombManager
        
        honeycomb = HoneycombManager()
        
        # Rebuild index
        result = honeycomb.rebuild_index(honey_jar_id)
        
        self.update_state(
            state='SUCCESS',
            meta={
                'stage': 'completed',
                'progress': 100,
                'documents_reindexed': result.get('documents_count', 0),
                'completed_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Successfully rebuilt index for honey pot {honey_jar_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to rebuild index for honey pot {honey_jar_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
        )
        raise


# Health check for Celery workers
@celery_app.task(name='health_check')
def health_check_task():
    """Simple health check task"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'worker_id': os.getenv('HOSTNAME', 'unknown')
    }


# Task status helper functions
def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a background task"""
    result = celery_app.AsyncResult(task_id)
    
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.successful() else None,
        'info': result.info,
        'traceback': result.traceback if result.failed() else None
    }


def cancel_task(task_id: str) -> bool:
    """Cancel a background task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception:
        return False


# Periodic tasks (if needed)
# from celery.schedules import crontab
# 
# celery_app.conf.beat_schedule = {
#     'cleanup-old-tasks': {
#         'task': 'cleanup_old_tasks',
#         'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
#     },
# }


if __name__ == '__main__':
    # For running Celery worker
    celery_app.start()