#!/usr/bin/env python3
"""
Basket Storage Management Routes
Provides endpoints for user storage management, document organization, and cleanup operations
"""

import os
import shutil
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func, desc, and_, or_
from app.utils.decorators import require_auth
from app.models import db, User, HoneyJar, Document, File
from app.services.honey_reserve import HoneyReserve
from app.utils.file_utils import get_file_size, format_bytes

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
            Document.file_size,
            Document.created_at,
            Document.status,
            Document.honey_jar_id,
            HoneyJar.name.label('honey_jar_name'),
            HoneyJar.type.label('honey_jar_type')
        ).join(
            HoneyJar, Document.honey_jar_id == HoneyJar.id
        ).filter(
            and_(
                or_(Document.uploader_id == user_id, HoneyJar.owner_id == user_id),
                Document.status != 'deleted'
            )
        ).order_by(desc(Document.created_at)).all()

        # Get user's temporary files
        temp_files = db.session.query(File).filter(
            and_(
                File.uploader_id == user_id,
                File.is_temporary == True,
                File.created_at > datetime.utcnow() - timedelta(hours=48)
            )
        ).all()

        # Calculate storage breakdown
        documents_size = sum(doc.file_size or 0 for doc in user_documents)
        temp_files_size = sum(file.size or 0 for file in temp_files)
        total_used = documents_size + temp_files_size

        # Group documents by honey jar
        honey_jar_breakdown = {}
        for doc in user_documents:
            jar_id = doc.honey_jar_id
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
                'id': doc.id,
                'filename': doc.filename,
                'size': doc.file_size or 0,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'status': doc.status
            })
            honey_jar_breakdown[jar_id]['total_size'] += doc.file_size or 0
            honey_jar_breakdown[jar_id]['document_count'] += 1

        # Sort honey jars by size (largest first)
        sorted_honey_jars = sorted(
            honey_jar_breakdown.values(),
            key=lambda x: x['total_size'],
            reverse=True
        )

        # Find cleanup opportunities
        cleanup_opportunities = []
        
        # Old temporary files
        old_temp_files = db.session.query(File).filter(
            and_(
                File.uploader_id == user_id,
                File.is_temporary == True,
                File.created_at < datetime.utcnow() - timedelta(hours=24)
            )
        ).all()
        
        if old_temp_files:
            temp_cleanup_size = sum(file.size or 0 for file in old_temp_files)
            cleanup_opportunities.append({
                'type': 'temp_files',
                'description': f'Delete {len(old_temp_files)} old temporary files',
                'potential_savings': temp_cleanup_size,
                'count': len(old_temp_files)
            })

        # Large files that haven't been accessed recently
        large_files = [doc for doc in user_documents if (doc.file_size or 0) > 10 * 1024 * 1024]  # > 10MB
        if large_files:
            large_files_size = sum(doc.file_size or 0 for doc in large_files)
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
                'largest_file_size': max((doc.file_size or 0 for doc in user_documents), default=0),
                'oldest_document': min((doc.created_at for doc in user_documents if doc.created_at), default=datetime.utcnow()).isoformat()
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
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            query = db.session.query(File).filter(
                and_(
                    File.uploader_id == user_id,
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
                        # Delete from Honey Reserve storage
                        honey_reserve = HoneyReserve()
                        honey_reserve.delete_file(file.id)
                        
                        # Delete from database
                        db.session.delete(file)
                    
                    cleaned_files += 1
                    freed_space += file.size or 0
                    
                except Exception as e:
                    error_msg = f"Failed to delete temp file {file.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    errors.append(error_msg)
            
            if not dry_run and cleaned_files > 0:
                db.session.commit()

        elif cleanup_type == 'documents':
            # Clean up specific documents marked for deletion
            query = db.session.query(Document).filter(
                and_(
                    Document.uploader_id == user_id,
                    Document.status == 'deleted'
                )
            )
            
            if file_ids:
                query = query.filter(Document.id.in_(file_ids))
            
            deleted_docs = query.all()
            
            for doc in deleted_docs:
                try:
                    if not dry_run:
                        # Delete from storage if file_path exists
                        if doc.file_path:
                            honey_reserve = HoneyReserve()
                            # Extract file ID from path if needed
                            if 'honey_reserve/' in doc.file_path:
                                file_id = doc.file_path.split('honey_reserve/')[-1]
                                honey_reserve.delete_file(file_id)
                        
                        # Delete from database
                        db.session.delete(doc)
                    
                    cleaned_files += 1
                    freed_space += doc.file_size or 0
                    
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
            documents = db.session.query(Document).filter(
                and_(
                    Document.id.in_(file_ids),
                    Document.uploader_id == user_id
                )
            ).all()
            
            temp_files = db.session.query(File).filter(
                and_(
                    File.id.in_(file_ids),
                    File.uploader_id == user_id
                )
            ).all()
            
            # Process documents
            for doc in documents:
                try:
                    if not dry_run:
                        if doc.file_path:
                            honey_reserve = HoneyReserve()
                            if 'honey_reserve/' in doc.file_path:
                                file_id = doc.file_path.split('honey_reserve/')[-1]
                                honey_reserve.delete_file(file_id)
                        
                        db.session.delete(doc)
                    
                    cleaned_files += 1
                    freed_space += doc.file_size or 0
                    
                except Exception as e:
                    error_msg = f"Failed to delete document {doc.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Process temp files
            for file in temp_files:
                try:
                    if not dry_run:
                        honey_reserve = HoneyReserve()
                        honey_reserve.delete_file(file.id)
                        db.session.delete(file)
                    
                    cleaned_files += 1
                    freed_space += file.size or 0
                    
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

        # Verify user owns or has access to these documents
        documents = db.session.query(Document).filter(
            and_(
                Document.id.in_(document_ids),
                or_(
                    Document.uploader_id == user_id,
                    Document.honey_jar_id.in_(
                        db.session.query(HoneyJar.id).filter(HoneyJar.owner_id == user_id)
                    )
                )
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
                            HoneyJar.owner_id == user_id
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
            Document.file_size,
            Document.created_at,
            Document.status,
            Document.honey_jar_id,
            HoneyJar.name.label('honey_jar_name')
        ).join(
            HoneyJar, Document.honey_jar_id == HoneyJar.id
        ).filter(
            and_(
                or_(
                    Document.uploader_id == user_id,
                    HoneyJar.owner_id == user_id,
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
                search_conditions.append(Document.created_at >= start_date)
            if date_range.get('end'):
                end_date = datetime.fromisoformat(date_range['end'])
                search_conditions.append(Document.created_at <= end_date)

        # Size range filter
        if size_range:
            if size_range.get('min'):
                search_conditions.append(Document.file_size >= size_range['min'])
            if size_range.get('max'):
                search_conditions.append(Document.file_size <= size_range['max'])

        # Apply all conditions
        if search_conditions:
            search_query = base_query.filter(and_(*search_conditions))
        else:
            search_query = base_query

        # Execute search with limit
        results = search_query.order_by(desc(Document.created_at)).limit(limit).all()

        # Format results
        documents = []
        for result in results:
            documents.append({
                'id': result.id,
                'filename': result.filename,
                'size': result.file_size or 0,
                'size_formatted': format_bytes(result.file_size or 0),
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'status': result.status,
                'honey_jar_id': result.honey_jar_id,
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