#!/usr/bin/env python3
"""
Basket Storage Management Routes
Provides endpoints for user storage management, document organization, and cleanup operations
"""

import os
import shutil
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func, desc, and_, or_, Column, String, Text, Integer, BigInteger, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.utils.decorators import require_auth
from app.extensions import db
from app.models import User
# Note: FileAsset used for temp files, HoneyReserve not implemented yet
try:
    from app.models.file_models import FileAsset as File
except ImportError:
    File = None  # File model may not exist

# Stub for format_bytes utility
def format_bytes(size):
    """Format bytes to human readable size"""
    if size == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


# Define models that map to existing database tables
class HoneyJar(db.Model):
    """SQLAlchemy model for honey_jars table"""
    __tablename__ = 'honey_jars'
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    status = Column(String(50), default='active')
    owner = Column(String(255), index=True)  # Maps to owner column in DB
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    tags = Column(JSONB, default=list)
    permissions = Column(JSONB, default=dict)
    document_count = Column(Integer, default=0)
    embedding_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)


class Document(db.Model):
    """SQLAlchemy model for documents table"""
    __tablename__ = 'documents'
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    size_bytes = Column(Integer, default=0)  # Maps to size_bytes in DB
    content_type = Column(String(255))
    honey_jar_id = Column(UUID(as_uuid=True), ForeignKey('honey_jars.id', ondelete='CASCADE'))
    status = Column(String(50), default='pending')
    file_path = Column(String(500))
    doc_metadata = Column(JSONB, default=dict)  # Maps to doc_metadata in DB
    tags = Column(JSONB, default=list)
    upload_date = Column(DateTime, default=datetime.utcnow)  # Maps to upload_date in DB
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding_count = Column(Integer, default=0)
    processing_time = Column(db.Float)
    error_message = Column(Text)

basket_bp = Blueprint('basket', __name__, url_prefix='/api/basket')

@basket_bp.route('/overview', methods=['GET'])
@require_auth
def get_basket_overview():
    """
    Get comprehensive storage overview for the current user
    Returns personalized storage breakdown, usage, and recommendations
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        current_app.logger.info(f"Basket overview request from user {user_id}")

        # Get user's storage quota (from metadata or default)
        user = User.query.get(user_id)
        user_quota = 1073741824  # Default 1GB
        if user and user.metadata and user.metadata.get('storage_quota'):
            user_quota = user.metadata['storage_quota']

        # Get user's documents across all honey jars
        user_documents = db.session.query(
            Document.id,
            Document.filename,
            Document.size_bytes,
            Document.upload_date,
            Document.status,
            Document.honey_jar_id,
            HoneyJar.name.label('honey_jar_name'),
            HoneyJar.type.label('honey_jar_type')
        ).join(
            HoneyJar, Document.honey_jar_id == HoneyJar.id
        ).filter(
            and_(
                HoneyJar.owner == str(user_id),
                Document.status != 'deleted'
            )
        ).order_by(desc(Document.upload_date)).all()

        # Get user's temporary files (skip if File model not available or incompatible)
        temp_files = []
        if File is not None:
            try:
                temp_files = db.session.query(File).filter(
                    and_(
                        File.uploader_id == str(user_id),
                        File.is_temporary == True,
                        File.created_at > datetime.utcnow() - timedelta(hours=48)
                    )
                ).all()
            except Exception as file_query_error:
                current_app.logger.warning(f"Could not query temp files (model may not be compatible): {file_query_error}")
                temp_files = []

        # Calculate storage breakdown
        documents_size = sum(doc.size_bytes or 0 for doc in user_documents)
        temp_files_size = sum(getattr(file, 'size', 0) or getattr(file, 'size_bytes', 0) or 0 for file in temp_files)
        total_used = documents_size + temp_files_size

        # Group documents by honey jar
        honey_jar_breakdown = {}
        for doc in user_documents:
            jar_id = str(doc.honey_jar_id)
            if jar_id not in honey_jar_breakdown:
                honey_jar_breakdown[jar_id] = {
                    'id': jar_id,
                    'name': doc.honey_jar_name,
                    'type': doc.honey_jar_type,
                    'documents': [],
                    'total_size': 0,
                    'document_count': 0
                }

            honey_jar_breakdown[jar_id]['documents'].append({
                'id': str(doc.id),
                'filename': doc.filename,
                'size': doc.size_bytes or 0,
                'created_at': doc.upload_date.isoformat() if doc.upload_date else None,
                'status': doc.status
            })
            honey_jar_breakdown[jar_id]['total_size'] += doc.size_bytes or 0
            honey_jar_breakdown[jar_id]['document_count'] += 1

        # Sort honey jars by size (largest first)
        sorted_honey_jars = sorted(
            honey_jar_breakdown.values(),
            key=lambda x: x['total_size'],
            reverse=True
        )

        # Find cleanup opportunities
        cleanup_opportunities = []

        # Old temporary files (skip if File model not available or incompatible)
        old_temp_files = []
        if File is not None:
            try:
                old_temp_files = db.session.query(File).filter(
                    and_(
                        File.uploader_id == str(user_id),
                        File.is_temporary == True,
                        File.created_at < datetime.utcnow() - timedelta(hours=24)
                    )
                ).all()
            except Exception as file_query_error:
                current_app.logger.warning(f"Could not query old temp files: {file_query_error}")
                old_temp_files = []

        if old_temp_files:
            temp_cleanup_size = sum(getattr(file, 'size', 0) or getattr(file, 'size_bytes', 0) or 0 for file in old_temp_files)
            cleanup_opportunities.append({
                'type': 'temp_files',
                'description': f'Delete {len(old_temp_files)} old temporary files',
                'potential_savings': temp_cleanup_size,
                'count': len(old_temp_files)
            })

        # Large files that haven't been accessed recently
        large_files = [doc for doc in user_documents if (doc.size_bytes or 0) > 10 * 1024 * 1024]  # > 10MB
        if large_files:
            large_files_size = sum(doc.size_bytes or 0 for doc in large_files)
            cleanup_opportunities.append({
                'type': 'large_files',
                'description': f'Review {len(large_files)} large files (>10MB)',
                'potential_savings': large_files_size,
                'count': len(large_files)
            })

        # Calculate usage percentage and status
        usage_percentage = (total_used / user_quota) * 100 if user_quota > 0 else 0
        storage_status = 'healthy'
        if usage_percentage > 90:
            storage_status = 'critical'
        elif usage_percentage > 75:
            storage_status = 'warning'

        # Generate storage recommendations
        recommendations = []
        if usage_percentage > 80:
            recommendations.append({
                'type': 'cleanup',
                'priority': 'high',
                'message': 'Consider cleaning up temporary files and large documents'
            })
        
        if len(sorted_honey_jars) > 5:
            recommendations.append({
                'type': 'organization',
                'priority': 'medium',
                'message': 'You have many honey jars. Consider consolidating related documents'
            })

        total_cleanup_potential = sum(op['potential_savings'] for op in cleanup_opportunities)

        response_data = {
            'user_id': user_id,
            'storage_quota': user_quota,
            'total_used': total_used,
            'usage_percentage': round(usage_percentage, 1),
            'storage_status': storage_status,
            'breakdown': {
                'documents': documents_size,
                'temp_files': temp_files_size,
                'other': 0  # Reserved for future file types
            },
            'honey_jars': sorted_honey_jars,
            'cleanup_opportunities': cleanup_opportunities,
            'total_cleanup_potential': total_cleanup_potential,
            'recommendations': recommendations,
            'statistics': {
                'total_documents': len(user_documents),
                'total_honey_jars': len(honey_jar_breakdown),
                'total_temp_files': len(temp_files),
                'largest_file_size': max((doc.size_bytes or 0 for doc in user_documents), default=0),
                'oldest_document': min((doc.upload_date for doc in user_documents if doc.upload_date), default=datetime.utcnow()).isoformat()
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Basket overview error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve basket overview',
            'details': str(e) if current_app.debug else 'Internal server error'
        }), 500

@basket_bp.route('/cleanup', methods=['POST'])
@require_auth
def perform_cleanup():
    """
    Perform storage cleanup operations for the current user
    Supports cleanup types: temp_files, large_files, old_documents
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        cleanup_type = data.get('type', 'temp_files')
        dry_run = data.get('dry_run', True)
        file_ids = data.get('file_ids', [])  # Specific files to clean up
        
        cleaned_files = 0
        freed_space = 0
        errors = []

        current_app.logger.info(f"Basket cleanup request: type={cleanup_type}, dry_run={dry_run}, user={user_id}")

        if cleanup_type == 'temp_files':
            # Clean up temporary files older than 24 hours
            if File is None:
                return jsonify({'error': 'Temp file cleanup not available (File model not loaded)'}), 400

            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                query = db.session.query(File).filter(
                    and_(
                        File.uploader_id == str(user_id),
                        File.is_temporary == True,
                        File.created_at < cutoff_time
                    )
                )

                if file_ids:
                    query = query.filter(File.id.in_(file_ids))

                temp_files = query.all()

                for file in temp_files:
                    try:
                        if not dry_run:
                            # Note: HoneyReserve storage not yet implemented
                            # Just delete from database for now
                            db.session.delete(file)

                        cleaned_files += 1
                        freed_space += getattr(file, 'size', 0) or getattr(file, 'size_bytes', 0) or 0

                    except Exception as e:
                        error_msg = f"Failed to delete temp file {file.id}: {str(e)}"
                        current_app.logger.error(error_msg)
                        errors.append(error_msg)

                if not dry_run and cleaned_files > 0:
                    db.session.commit()
            except Exception as file_cleanup_error:
                current_app.logger.warning(f"Temp file cleanup failed (model may not be compatible): {file_cleanup_error}")
                errors.append(f"Temp file cleanup unavailable: {str(file_cleanup_error)}")

        elif cleanup_type == 'documents':
            # Clean up specific documents marked for deletion (owned via honey jar)
            query = db.session.query(Document).join(
                HoneyJar, Document.honey_jar_id == HoneyJar.id
            ).filter(
                and_(
                    HoneyJar.owner == str(user_id),
                    Document.status == 'deleted'
                )
            )
            
            if file_ids:
                query = query.filter(Document.id.in_(file_ids))
            
            deleted_docs = query.all()
            
            for doc in deleted_docs:
                try:
                    if not dry_run:
                        # Note: HoneyReserve storage not yet implemented
                        # Just delete from database for now
                        db.session.delete(doc)
                    
                    cleaned_files += 1
                    freed_space += doc.size_bytes or 0
                    
                except Exception as e:
                    error_msg = f"Failed to delete document {doc.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    errors.append(error_msg)
            
            if not dry_run and cleaned_files > 0:
                db.session.commit()

        elif cleanup_type == 'selected_files':
            # Clean up specifically selected files
            if not file_ids:
                return jsonify({'error': 'No file IDs provided for cleanup'}), 400

            # Handle both Document and File model cleanup
            documents = db.session.query(Document).join(
                HoneyJar, Document.honey_jar_id == HoneyJar.id
            ).filter(
                and_(
                    Document.id.in_(file_ids),
                    HoneyJar.owner == str(user_id)
                )
            ).all()

            # Try to get temp files if File model is available
            temp_files = []
            if File is not None:
                try:
                    temp_files = db.session.query(File).filter(
                        and_(
                            File.id.in_(file_ids),
                            File.uploader_id == str(user_id)
                        )
                    ).all()
                except Exception as file_query_error:
                    current_app.logger.warning(f"Could not query temp files for cleanup: {file_query_error}")

            # Process documents
            for doc in documents:
                try:
                    if not dry_run:
                        # Note: HoneyReserve storage not yet implemented
                        db.session.delete(doc)

                    cleaned_files += 1
                    freed_space += doc.size_bytes or 0

                except Exception as e:
                    error_msg = f"Failed to delete document {doc.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    errors.append(error_msg)

            # Process temp files
            for file in temp_files:
                try:
                    if not dry_run:
                        # Note: HoneyReserve storage not yet implemented
                        db.session.delete(file)

                    cleaned_files += 1
                    freed_space += getattr(file, 'size', 0) or getattr(file, 'size_bytes', 0) or 0

                except Exception as e:
                    error_msg = f"Failed to delete file {file.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    errors.append(error_msg)

            if not dry_run and cleaned_files > 0:
                db.session.commit()

        current_app.logger.info(f"Basket cleanup ({'DRY RUN' if dry_run else 'EXECUTED'}): {cleaned_files} files, {freed_space} bytes freed")
        
        return jsonify({
            'success': True,
            'type': cleanup_type,
            'dry_run': dry_run,
            'cleaned_files': cleaned_files,
            'freed_space': freed_space,
            'freed_space_formatted': format_bytes(freed_space),
            'errors': errors,
            'message': f'{"Would clean" if dry_run else "Cleaned"} {cleaned_files} files, freeing {format_bytes(freed_space)}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Basket cleanup error: {str(e)}")
        return jsonify({
            'error': 'Cleanup operation failed',
            'details': str(e) if current_app.debug else 'Internal server error'
        }), 500

@basket_bp.route('/documents/bulk', methods=['POST'])
@require_auth
def bulk_document_operations():
    """
    Perform bulk operations on user documents
    Supports: move, delete, archive, restore operations
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        operation = data.get('operation')  # move, delete, archive, restore
        document_ids = data.get('document_ids', [])
        target_honey_jar_id = data.get('target_honey_jar_id')  # For move operation
        
        if not operation or not document_ids:
            return jsonify({'error': 'Missing operation or document_ids'}), 400

        current_app.logger.info(f"Bulk operation request: {operation} on {len(document_ids)} documents by user {user_id}")

        # Verify user owns or has access to these documents (via honey jar ownership)
        documents = db.session.query(Document).join(
            HoneyJar, Document.honey_jar_id == HoneyJar.id
        ).filter(
            and_(
                Document.id.in_(document_ids),
                HoneyJar.owner == str(user_id)
            )
        ).all()

        if len(documents) != len(document_ids):
            return jsonify({'error': 'Some documents not found or access denied'}), 403

        processed_count = 0
        errors = []

        for doc in documents:
            try:
                if operation == 'delete':
                    # Mark as deleted (soft delete)
                    doc.status = 'deleted'
                    doc.updated_at = datetime.utcnow()
                
                elif operation == 'archive':
                    doc.status = 'archived'
                    doc.updated_at = datetime.utcnow()
                
                elif operation == 'restore':
                    doc.status = 'active'
                    doc.updated_at = datetime.utcnow()
                
                elif operation == 'move':
                    if not target_honey_jar_id:
                        errors.append(f"No target honey jar specified for document {doc.id}")
                        continue
                    
                    # Verify target honey jar exists and user has access
                    target_jar = db.session.query(HoneyJar).filter(
                        and_(
                            HoneyJar.id == target_honey_jar_id,
                            HoneyJar.owner == str(user_id)
                        )
                    ).first()
                    
                    if not target_jar:
                        errors.append(f"Target honey jar not found or access denied for document {doc.id}")
                        continue
                    
                    doc.honey_jar_id = target_honey_jar_id
                    doc.updated_at = datetime.utcnow()
                
                else:
                    errors.append(f"Unknown operation: {operation}")
                    continue
                
                processed_count += 1
                
            except Exception as e:
                error_msg = f"Failed to {operation} document {doc.id}: {str(e)}"
                current_app.logger.error(error_msg)
                errors.append(error_msg)

        if processed_count > 0:
            db.session.commit()

        current_app.logger.info(f"Bulk {operation} completed: {processed_count} documents processed")
        
        return jsonify({
            'success': True,
            'operation': operation,
            'processed_count': processed_count,
            'total_requested': len(document_ids),
            'errors': errors,
            'message': f'Successfully {operation}d {processed_count} documents'
        })
        
    except Exception as e:
        current_app.logger.error(f"Bulk operation error: {str(e)}")
        return jsonify({
            'error': 'Bulk operation failed',
            'details': str(e) if current_app.debug else 'Internal server error'
        }), 500

@basket_bp.route('/search', methods=['POST'])
@require_auth
def search_user_documents():
    """
    Search through user's documents across all accessible honey jars
    Supports filename, content, and metadata search
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        query = data.get('query', '').strip()
        honey_jar_ids = data.get('honey_jar_ids', [])  # Filter by specific honey jars
        file_types = data.get('file_types', [])  # Filter by file extensions
        date_range = data.get('date_range')  # {'start': '2024-01-01', 'end': '2024-12-31'}
        size_range = data.get('size_range')  # {'min': 1024, 'max': 10485760}
        limit = min(data.get('limit', 50), 100)  # Max 100 results
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        current_app.logger.info(f"Basket search request: '{query}' by user {user_id}")

        # Base query for user's accessible documents
        base_query = db.session.query(
            Document.id,
            Document.filename,
            Document.size_bytes,
            Document.upload_date,
            Document.status,
            Document.honey_jar_id,
            HoneyJar.name.label('honey_jar_name')
        ).join(
            HoneyJar, Document.honey_jar_id == HoneyJar.id
        ).filter(
            and_(
                or_(
                    HoneyJar.owner == str(user_id),
                    HoneyJar.type == 'public'
                ),
                Document.status != 'deleted'
            )
        )

        # Apply search filters
        search_conditions = []
        
        # Text search in filename
        if query:
            search_conditions.append(Document.filename.ilike(f'%{query}%'))

        # Honey jar filter
        if honey_jar_ids:
            search_conditions.append(Document.honey_jar_id.in_(honey_jar_ids))

        # File type filter
        if file_types:
            type_conditions = []
            for file_type in file_types:
                type_conditions.append(Document.filename.ilike(f'%.{file_type}'))
            search_conditions.append(or_(*type_conditions))

        # Date range filter
        if date_range:
            if date_range.get('start'):
                start_date = datetime.fromisoformat(date_range['start'])
                search_conditions.append(Document.upload_date >= start_date)
            if date_range.get('end'):
                end_date = datetime.fromisoformat(date_range['end'])
                search_conditions.append(Document.upload_date <= end_date)

        # Size range filter
        if size_range:
            if size_range.get('min'):
                search_conditions.append(Document.size_bytes >= size_range['min'])
            if size_range.get('max'):
                search_conditions.append(Document.size_bytes <= size_range['max'])

        # Apply all conditions
        if search_conditions:
            search_query = base_query.filter(and_(*search_conditions))
        else:
            search_query = base_query

        # Execute search with limit
        results = search_query.order_by(desc(Document.upload_date)).limit(limit).all()

        # Format results
        documents = []
        for result in results:
            documents.append({
                'id': str(result.id),
                'filename': result.filename,
                'size': result.size_bytes or 0,
                'size_formatted': format_bytes(result.size_bytes or 0),
                'created_at': result.upload_date.isoformat() if result.upload_date else None,
                'status': result.status,
                'honey_jar_id': str(result.honey_jar_id),
                'honey_jar_name': result.honey_jar_name
            })

        return jsonify({
            'success': True,
            'query': query,
            'total_results': len(documents),
            'documents': documents,
            'filters_applied': {
                'honey_jar_ids': honey_jar_ids,
                'file_types': file_types,
                'date_range': date_range,
                'size_range': size_range
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Basket search error: {str(e)}")
        return jsonify({
            'error': 'Search operation failed',
            'details': str(e) if current_app.debug else 'Internal server error'
        }), 500


@basket_bp.route('/add-report', methods=['POST'])
@require_auth
def add_report_to_basket():
    """
    Add a generated report from Bee chat to the user's basket (private space)
    Creates a file entry that can be viewed in the Basket page
    """
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user else None

        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        filename = data.get('filename')
        content = data.get('content')
        content_type = data.get('content_type', 'text/markdown')
        metadata = data.get('metadata', {})

        if not filename or not content:
            return jsonify({'error': 'Filename and content are required'}), 400

        current_app.logger.info(f"Adding report to basket for user {user_id}: {filename}")

        # Get or create user's private "Reports" honey jar
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Find or create a "Bee Reports" honey jar for the user
        reports_jar = HoneyJar.query.filter(
            and_(
                HoneyJar.owner == str(user_id),
                HoneyJar.name == 'Bee Reports',
                HoneyJar.type == 'private'
            )
        ).first()

        if not reports_jar:
            # Create the reports honey jar
            reports_jar = HoneyJar(
                name='Bee Reports',
                description='Auto-generated reports from Bee chat conversations',
                type='private',
                owner=str(user_id),
                status='active',
                tags=['reports', 'bee-generated']
            )
            db.session.add(reports_jar)
            db.session.flush()  # Get the ID

        # Create a document entry for the report
        content_bytes = content.encode('utf-8')

        new_document = Document(
            filename=filename,
            size_bytes=len(content_bytes),
            content_type=content_type,
            honey_jar_id=reports_jar.id,
            status='active',
            doc_metadata={
                **metadata,
                'source': 'bee_chat_report',
                'added_to_basket': datetime.utcnow().isoformat(),
                'uploader_id': str(user_id)
            },
            tags=['report', 'bee-generated']
        )
        db.session.add(new_document)

        # Note: File content storage (HoneyReserve) not yet implemented
        # For now, the document entry is created without storing the actual content
        # This allows tracking reports in the basket even before full storage is available
        current_app.logger.info(f"Document entry created (content storage pending future implementation)")

        db.session.commit()

        current_app.logger.info(f"Report added to basket: {filename} (document {new_document.id})")

        return jsonify({
            'success': True,
            'message': f'Report "{filename}" added to your Bee Reports folder',
            'document_id': str(new_document.id),
            'honey_jar_id': str(reports_jar.id),
            'honey_jar_name': reports_jar.name,
            'file_size': len(content_bytes),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"Add report to basket error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Failed to add report to basket',
            'details': str(e) if current_app.debug else 'Internal server error'
        }), 500