#!/usr/bin/env python3
"""
PII Audit Service
Handles PII detection audit logging, serialization, and retention management
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

from app import db
from app.models.pii_audit_models import (
    PIIDetectionRecord, PIIRetentionPolicy, PIIAuditLog, 
    PIIDeletionRequest, PIIComplianceReport,
    calculate_expiration_date, get_retention_policy
)
from app.services.hive_scrambler import PIIDetection
from config_loader import ConfigLoader

# Setup logging
logger = logging.getLogger(__name__)

class PIIAuditService:
    """
    Service for managing PII audit logging, serialization, and compliance retention
    """
    
    def __init__(self):
        self.config = ConfigLoader()
        self.pii_config = self.config.get_section('pii_detection', {})
        self.audit_config = self.pii_config.get('audit_logging', {})
        self.retention_config = self.pii_config.get('retention', {})
        
        # Initialize audit logging
        self.audit_enabled = self.audit_config.get('enabled', True)
        self.include_original_values = self.audit_config.get('include_original_values', False)
        
        logger.info(f"PIIAuditService initialized - audit_enabled: {self.audit_enabled}")
    
    def record_pii_detection(self, 
                           detection: PIIDetection, 
                           user_id: str,
                           document_id: str = None,
                           honey_jar_id: str = None,
                           detection_mode: str = "general") -> PIIDetectionRecord:
        """
        Record a PII detection event in the audit system
        """
        if not self.audit_enabled:
            return None
            
        try:
            # Generate unique detection ID
            detection_id = f"pii_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(detection.original_value) % 10000:04d}"
            
            # Calculate retention expiration
            compliance_frameworks = [fw.value for fw in (detection.compliance_frameworks or [])]
            expires_at = calculate_expiration_date(
                compliance_frameworks, 
                detection.pii_type.value, 
                datetime.utcnow()
            )
            
            # Create audit record (without storing actual PII values for security)
            record = PIIDetectionRecord(
                detection_id=detection_id,
                document_id=document_id,
                honey_jar_id=honey_jar_id,
                user_id=user_id,
                pii_type=detection.pii_type.value,
                risk_level=detection.risk_level,
                confidence_score=int(detection.confidence * 100),
                start_position=detection.start_position,
                end_position=detection.end_position,
                context_hash=self._hash_value(detection.context) if detection.context else None,
                value_hash=self._hash_value(detection.original_value),
                compliance_frameworks=compliance_frameworks,
                detection_mode=detection_mode,
                expires_at=expires_at
            )
            
            db.session.add(record)
            db.session.commit()
            
            # Log the detection event
            self._log_audit_event(
                event_type="pii_detection",
                event_description=f"PII detected: {detection.pii_type.value}",
                detection_record_id=record.id,
                user_id=user_id,
                event_data={
                    "pii_type": detection.pii_type.value,
                    "risk_level": detection.risk_level,
                    "confidence": detection.confidence,
                    "compliance_frameworks": compliance_frameworks,
                    "detection_mode": detection_mode
                },
                compliance_impact=self._assess_compliance_impact(detection)
            )
            
            # Check if high-risk notification needed
            if detection.risk_level == "high":
                self._handle_high_risk_detection(record, detection)
            
            logger.info(f"Recorded PII detection: {detection_id}")
            return record
            
        except SQLAlchemyError as e:
            logger.error(f"Database error recording PII detection: {e}")
            db.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error recording PII detection: {e}")
            raise
    
    def batch_record_detections(self, 
                              detections: List[PIIDetection],
                              user_id: str,
                              document_id: str = None,
                              honey_jar_id: str = None,
                              detection_mode: str = "general") -> List[PIIDetectionRecord]:
        """
        Efficiently record multiple PII detections in batch
        """
        if not self.audit_enabled or not detections:
            return []
        
        try:
            records = []
            audit_events = []
            
            for detection in detections:
                # Generate unique detection ID
                detection_id = f"pii_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(detection.original_value) % 10000:04d}"
                
                # Calculate retention expiration
                compliance_frameworks = [fw.value for fw in (detection.compliance_frameworks or [])]
                expires_at = calculate_expiration_date(
                    compliance_frameworks, 
                    detection.pii_type.value, 
                    datetime.utcnow()
                )
                
                # Create record
                record = PIIDetectionRecord(
                    detection_id=detection_id,
                    document_id=document_id,
                    honey_jar_id=honey_jar_id,
                    user_id=user_id,
                    pii_type=detection.pii_type.value,
                    risk_level=detection.risk_level,
                    confidence_score=int(detection.confidence * 100),
                    start_position=detection.start_position,
                    end_position=detection.end_position,
                    context_hash=self._hash_value(detection.context) if detection.context else None,
                    value_hash=self._hash_value(detection.original_value),
                    compliance_frameworks=compliance_frameworks,
                    detection_mode=detection_mode,
                    expires_at=expires_at
                )
                
                records.append(record)
                
                # Prepare audit event
                audit_events.append({
                    "detection": detection,
                    "record": record,
                    "compliance_impact": self._assess_compliance_impact(detection)
                })
            
            # Bulk insert records
            db.session.bulk_save_objects(records)
            db.session.commit()
            
            # Log audit events
            for event in audit_events:
                self._log_audit_event(
                    event_type="pii_detection_batch",
                    event_description=f"Batch PII detection: {event['detection'].pii_type.value}",
                    detection_record_id=event['record'].id,
                    user_id=user_id,
                    event_data={
                        "pii_type": event['detection'].pii_type.value,
                        "risk_level": event['detection'].risk_level,
                        "batch_size": len(detections)
                    },
                    compliance_impact=event['compliance_impact']
                )
            
            logger.info(f"Batch recorded {len(records)} PII detections")
            return records
            
        except Exception as e:
            logger.error(f"Error in batch recording PII detections: {e}")
            db.session.rollback()
            raise
    
    def process_deletion_request(self, 
                               requester_email: str,
                               request_type: str = "gdpr_erasure",
                               user_id: str = None,
                               reason: str = None) -> PIIDeletionRequest:
        """
        Process a PII deletion request (GDPR/CCPA compliance)
        """
        try:
            # Calculate deadline based on request type
            deadline_days = 30 if request_type == "gdpr_erasure" else 45  # CCPA allows longer
            deadline_at = datetime.utcnow() + timedelta(days=deadline_days)
            
            # Create deletion request
            request = PIIDeletionRequest(
                request_type=request_type,
                requester_email=requester_email,
                user_id=user_id,
                reason=reason,
                scope="all_data",  # Default to all data
                deadline_at=deadline_at,
                status="pending"
            )
            
            db.session.add(request)
            db.session.commit()
            
            # Log the request
            self._log_audit_event(
                event_type="deletion_request",
                event_description=f"PII deletion request: {request_type}",
                user_id=user_id,
                event_data={
                    "request_type": request_type,
                    "requester_email": requester_email,
                    "deadline": deadline_at.isoformat()
                },
                compliance_impact="high"
            )
            
            logger.info(f"Created deletion request: {request.id}")
            return request
            
        except Exception as e:
            logger.error(f"Error processing deletion request: {e}")
            db.session.rollback()
            raise
    
    def execute_retention_cleanup(self) -> Dict[str, int]:
        """
        Execute retention policy cleanup - delete expired PII records
        """
        try:
            now = datetime.utcnow()
            
            # Find expired records
            expired_records = PIIDetectionRecord.query.filter(
                and_(
                    PIIDetectionRecord.expires_at <= now,
                    PIIDetectionRecord.deleted_at.is_(None)
                )
            ).all()
            
            deleted_count = 0
            framework_counts = {}
            
            for record in expired_records:
                # Check if grace period applies
                policy = get_retention_policy(
                    record.compliance_frameworks[0] if record.compliance_frameworks else "gdpr",
                    record.pii_type
                )
                
                grace_period_days = policy.grace_period_days if policy else 30
                grace_deadline = record.expires_at + timedelta(days=grace_period_days)
                
                if now >= grace_deadline:
                    # Soft delete the record
                    record.deleted_at = now
                    deleted_count += 1
                    
                    # Track by framework
                    for framework in (record.compliance_frameworks or ["unknown"]):
                        framework_counts[framework] = framework_counts.get(framework, 0) + 1
                    
                    # Log deletion
                    self._log_audit_event(
                        event_type="retention_deletion",
                        event_description=f"Retention policy deletion: {record.pii_type}",
                        detection_record_id=record.id,
                        event_data={
                            "pii_type": record.pii_type,
                            "expired_at": record.expires_at.isoformat(),
                            "grace_period_days": grace_period_days,
                            "compliance_frameworks": record.compliance_frameworks
                        },
                        compliance_impact="low"
                    )
            
            if deleted_count > 0:
                db.session.commit()
                logger.info(f"Retention cleanup: deleted {deleted_count} expired PII records")
            
            return {
                "total_deleted": deleted_count,
                "by_framework": framework_counts
            }
            
        except Exception as e:
            logger.error(f"Error in retention cleanup: {e}")
            db.session.rollback()
            raise
    
    def generate_compliance_report(self, 
                                 compliance_framework: str,
                                 start_date: datetime,
                                 end_date: datetime,
                                 generated_by: str) -> PIIComplianceReport:
        """
        Generate a compliance report for audit purposes
        """
        try:
            # Gather statistics
            detections_query = PIIDetectionRecord.query.filter(
                and_(
                    PIIDetectionRecord.detected_at >= start_date,
                    PIIDetectionRecord.detected_at <= end_date,
                    PIIDetectionRecord.compliance_frameworks.contains([compliance_framework])
                )
            )
            
            total_detections = detections_query.count()
            high_risk_detections = detections_query.filter(
                PIIDetectionRecord.risk_level == "high"
            ).count()
            
            # Deletion statistics
            deletions_query = PIIAuditLog.query.filter(
                and_(
                    PIIAuditLog.event_type == "retention_deletion",
                    PIIAuditLog.event_timestamp >= start_date,
                    PIIAuditLog.event_timestamp <= end_date
                )
            )
            
            records_deleted = deletions_query.count()
            
            # Deletion requests
            deletion_requests = PIIDeletionRequest.query.filter(
                and_(
                    PIIDeletionRequest.requested_at >= start_date,
                    PIIDeletionRequest.requested_at <= end_date,
                    PIIDeletionRequest.status == "completed"
                )
            ).count()
            
            # Detailed statistics
            statistics = {
                "by_pii_type": self._get_detection_stats_by_type(compliance_framework, start_date, end_date),
                "by_risk_level": self._get_detection_stats_by_risk(compliance_framework, start_date, end_date),
                "by_detection_mode": self._get_detection_stats_by_mode(compliance_framework, start_date, end_date)
            }
            
            # Create report
            report = PIIComplianceReport(
                report_type="ad_hoc",
                compliance_framework=compliance_framework,
                reporting_period_start=start_date,
                reporting_period_end=end_date,
                total_detections=total_detections,
                high_risk_detections=high_risk_detections,
                records_deleted=records_deleted,
                deletion_requests_processed=deletion_requests,
                statistics=statistics,
                generated_by=generated_by
            )
            
            db.session.add(report)
            db.session.commit()
            
            logger.info(f"Generated compliance report: {report.id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            db.session.rollback()
            raise
    
    def get_user_pii_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary of PII detections for a specific user (for privacy requests)
        """
        try:
            records = PIIDetectionRecord.query.filter(
                and_(
                    PIIDetectionRecord.user_id == user_id,
                    PIIDetectionRecord.deleted_at.is_(None)
                )
            ).all()
            
            summary = {
                "total_records": len(records),
                "by_pii_type": {},
                "by_compliance_framework": {},
                "oldest_record": None,
                "newest_record": None,
                "high_risk_count": 0
            }
            
            if records:
                # Calculate statistics
                for record in records:
                    # By PII type
                    pii_type = record.pii_type
                    summary["by_pii_type"][pii_type] = summary["by_pii_type"].get(pii_type, 0) + 1
                    
                    # By compliance framework
                    for framework in (record.compliance_frameworks or []):
                        summary["by_compliance_framework"][framework] = summary["by_compliance_framework"].get(framework, 0) + 1
                    
                    # Risk level
                    if record.risk_level == "high":
                        summary["high_risk_count"] += 1
                
                # Date range
                dates = [r.detected_at for r in records]
                summary["oldest_record"] = min(dates).isoformat()
                summary["newest_record"] = max(dates).isoformat()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting user PII summary: {e}")
            raise
    
    # Private helper methods
    
    def _hash_value(self, value: str) -> str:
        """Create SHA-256 hash of a value for audit purposes"""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()
    
    def _assess_compliance_impact(self, detection: PIIDetection) -> str:
        """Assess the compliance impact of a PII detection"""
        if detection.risk_level == "high":
            return "high"
        elif detection.compliance_frameworks and len(detection.compliance_frameworks) > 1:
            return "medium"
        else:
            return "low"
    
    def _handle_high_risk_detection(self, record: PIIDetectionRecord, detection: PIIDetection):
        """Handle high-risk PII detection notifications"""
        risk_config = self.pii_config.get('risk_management', {})
        notifications_enabled = risk_config.get('high_risk_notifications', {}).get('enabled', False)
        
        if notifications_enabled:
            # Mark for notification (actual notification would be handled by separate service)
            record.notified = True
            logger.warning(f"High-risk PII detected: {detection.pii_type.value} in document {record.document_id}")
    
    def _log_audit_event(self, 
                        event_type: str,
                        event_description: str,
                        detection_record_id: str = None,
                        user_id: str = None,
                        event_data: Dict = None,
                        compliance_impact: str = "low"):
        """Log an audit event"""
        try:
            audit_log = PIIAuditLog(
                event_type=event_type,
                event_description=event_description,
                detection_record_id=detection_record_id,
                user_id=user_id,
                system_component="pii_audit_service",
                event_data=event_data,
                compliance_impact=compliance_impact
            )
            
            db.session.add(audit_log)
            # Note: commit is handled by calling method
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    def _get_detection_stats_by_type(self, framework: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get detection statistics by PII type"""
        # Implementation would use database aggregation
        return {}
    
    def _get_detection_stats_by_risk(self, framework: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get detection statistics by risk level"""
        # Implementation would use database aggregation
        return {}
    
    def _get_detection_stats_by_mode(self, framework: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get detection statistics by detection mode"""
        # Implementation would use database aggregation
        return {}

# Singleton instance for application use
pii_audit_service = PIIAuditService()