"""
Initialize Default Report Templates for STING-CE
Creates standard report templates that demonstrate the reporting system capabilities.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.report_models import ReportTemplate
from app.database import get_db_session

logger = logging.getLogger(__name__)

def create_default_templates(session=None):
    """Create default report templates"""
    
    templates = [
        {
            'name': 'honey_jar_summary',
            'display_name': 'Honey Jar Summary Report',
            'description': 'Comprehensive overview of honey jar usage, document access patterns, and user engagement metrics.',
            'category': 'analytics',
            'template_config': {
                'data_sources': ['honey_jars', 'document_access', 'user_activity'],
                'queries': {
                    'honey_jar_stats': 'SELECT COUNT(*) as total_jars, AVG(document_count) as avg_docs FROM honey_jars WHERE active = true',
                    'access_patterns': 'SELECT jar_id, COUNT(*) as access_count FROM document_access WHERE created_at >= :start_date GROUP BY jar_id',
                    'user_engagement': 'SELECT user_id, COUNT(DISTINCT jar_id) as jars_accessed FROM document_access WHERE created_at >= :start_date GROUP BY user_id'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '30_days_ago', 'help': 'Report period start date'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Report period end date (defaults to today)'},
                    {'name': 'department_filter', 'type': 'multiselect', 'required': False, 'options': ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Legal', 'Operations'], 'help': 'Filter by organizational departments'},
                    {'name': 'access_level_threshold', 'type': 'select', 'required': False, 'options': ['Public', 'Internal', 'Confidential', 'Restricted'], 'default': 'Internal', 'help': 'Minimum access level to include in analysis'},
                    {'name': 'data_classification', 'type': 'multiselect', 'required': False, 'options': ['General Business', 'Financial', 'Customer Data', 'Technical', 'Legal', 'HR'], 'help': 'Include specific data classifications'},
                    {'name': 'include_trends', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include month-over-month trend analysis'},
                    {'name': 'benchmark_comparison', 'type': 'boolean', 'required': False, 'default': False, 'help': 'Compare against industry benchmarks'}
                ],
                'visualizations': [
                    {'type': 'bar_chart', 'title': 'Documents per Honey Jar', 'data_key': 'honey_jar_stats'},
                    {'type': 'pie_chart', 'title': 'Access Distribution', 'data_key': 'access_patterns'},
                    {'type': 'table', 'title': 'User Engagement Summary', 'data_key': 'user_engagement'}
                ]
            },
            'output_formats': ['pdf', 'xlsx', 'csv'],
            'estimated_time_minutes': 3,
            'requires_scrambling': True,
            'scrambling_profile': 'gdpr_compliant',
            'security_level': 'standard'
        },
        
        {
            'name': 'user_activity_audit',
            'display_name': 'User Activity Audit Report',
            'description': 'Detailed audit trail of user activities, login patterns, and access control events for security compliance.',
            'category': 'security',
            'template_config': {
                'data_sources': ['user_sessions', 'authentication_events', 'access_logs'],
                'queries': {
                    'login_summary': 'SELECT DATE(created_at) as date, COUNT(*) as login_count FROM user_sessions WHERE created_at >= :start_date GROUP BY DATE(created_at)',
                    'failed_attempts': 'SELECT user_id, COUNT(*) as failed_count FROM authentication_events WHERE status = "failed" AND created_at >= :start_date GROUP BY user_id',
                    'access_events': 'SELECT action, resource_type, COUNT(*) as event_count FROM access_logs WHERE created_at >= :start_date GROUP BY action, resource_type'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '7_days_ago', 'help': 'Audit period start date'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Audit period end date'},
                    {'name': 'compliance_framework', 'type': 'select', 'required': False, 'options': ['SOX', 'HIPAA', 'GDPR', 'SOC2', 'ISO27001', 'PCI-DSS'], 'default': 'SOC2', 'help': 'Compliance framework for audit requirements'},
                    {'name': 'risk_threshold', 'type': 'select', 'required': False, 'options': ['Low', 'Medium', 'High', 'Critical'], 'default': 'Medium', 'help': 'Minimum risk level to flag in report'},
                    {'name': 'alert_severity', 'type': 'multiselect', 'required': False, 'options': ['Info', 'Warning', 'Critical', 'Emergency'], 'default': ['Warning', 'Critical'], 'help': 'Security alert severities to include'},
                    {'name': 'geographic_scope', 'type': 'multiselect', 'required': False, 'options': ['US', 'EU', 'APAC', 'LATAM', 'Global'], 'default': ['US'], 'help': 'Geographic regions to include in analysis'},
                    {'name': 'include_privileged_access', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include privileged access monitoring'},
                    {'name': 'anomaly_detection', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Run ML-based anomaly detection'},
                    {'name': 'executive_summary', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include executive summary section'}
                ],
                'visualizations': [
                    {'type': 'line_chart', 'title': 'Daily Login Activity', 'data_key': 'login_summary'},
                    {'type': 'table', 'title': 'Failed Login Attempts', 'data_key': 'failed_attempts'},
                    {'type': 'heatmap', 'title': 'Access Event Distribution', 'data_key': 'access_events'}
                ]
            },
            'output_formats': ['pdf', 'xlsx'],
            'estimated_time_minutes': 5,
            'requires_scrambling': True,
            'scrambling_profile': 'security_audit',
            'security_level': 'high',
            'required_role': 'admin'
        },
        
        {
            'name': 'document_processing_report',
            'display_name': 'Document Processing Performance',
            'description': 'Analysis of document upload, processing times, and system performance metrics.',
            'category': 'performance',
            'template_config': {
                'data_sources': ['file_uploads', 'processing_logs', 'system_metrics'],
                'queries': {
                    'upload_stats': 'SELECT DATE(created_at) as date, COUNT(*) as upload_count, AVG(file_size) as avg_size FROM file_uploads WHERE created_at >= :start_date GROUP BY DATE(created_at)',
                    'processing_times': 'SELECT file_type, AVG(processing_time_seconds) as avg_processing_time FROM processing_logs WHERE created_at >= :start_date GROUP BY file_type',
                    'error_analysis': 'SELECT error_type, COUNT(*) as error_count FROM processing_logs WHERE status = "error" AND created_at >= :start_date GROUP BY error_type'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '14_days_ago', 'help': 'Performance analysis period start'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Performance analysis period end'},
                    {'name': 'sla_threshold_seconds', 'type': 'number', 'required': False, 'default': 300, 'help': 'SLA threshold in seconds for processing time'},
                    {'name': 'system_components', 'type': 'multiselect', 'required': False, 'options': ['Upload Service', 'Text Extraction', 'Vector Processing', 'Search Index', 'Encryption', 'Storage'], 'help': 'System components to analyze'},
                    {'name': 'file_size_categories', 'type': 'multiselect', 'required': False, 'options': ['Small (<1MB)', 'Medium (1-10MB)', 'Large (10-50MB)', 'Very Large (>50MB)'], 'default': ['Small (<1MB)', 'Medium (1-10MB)', 'Large (10-50MB)'], 'help': 'File size categories for analysis'},
                    {'name': 'performance_baseline', 'type': 'select', 'required': False, 'options': ['Last Week', 'Last Month', 'Last Quarter', 'Custom'], 'default': 'Last Month', 'help': 'Baseline period for performance comparison'},
                    {'name': 'include_capacity_planning', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include capacity planning recommendations'},
                    {'name': 'bottleneck_analysis', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Run automated bottleneck detection'},
                    {'name': 'cost_analysis', 'type': 'boolean', 'required': False, 'default': False, 'help': 'Include cost per transaction analysis'}
                ],
                'visualizations': [
                    {'type': 'line_chart', 'title': 'Daily Upload Volume', 'data_key': 'upload_stats'},
                    {'type': 'bar_chart', 'title': 'Processing Times by Type', 'data_key': 'processing_times'},
                    {'type': 'table', 'title': 'Error Analysis', 'data_key': 'error_analysis'}
                ]
            },
            'output_formats': ['pdf', 'xlsx', 'csv'],
            'estimated_time_minutes': 4,
            'requires_scrambling': False,
            'security_level': 'standard',
            'required_role': 'admin'
        },
        
        {
            'name': 'bee_chat_analytics',
            'display_name': 'Bee Chat Usage Analytics',
            'description': 'Insights into chatbot usage patterns, popular queries, and response effectiveness.',
            'category': 'analytics',
            'template_config': {
                'data_sources': ['chat_sessions', 'chat_messages', 'user_feedback'],
                'queries': {
                    'usage_trends': 'SELECT DATE(created_at) as date, COUNT(DISTINCT session_id) as sessions, COUNT(*) as messages FROM chat_messages WHERE created_at >= :start_date GROUP BY DATE(created_at)',
                    'popular_topics': 'SELECT extracted_topic, COUNT(*) as frequency FROM chat_messages WHERE created_at >= :start_date AND extracted_topic IS NOT NULL GROUP BY extracted_topic ORDER BY frequency DESC LIMIT 20',
                    'response_quality': 'SELECT rating, COUNT(*) as count FROM user_feedback WHERE created_at >= :start_date GROUP BY rating'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '30_days_ago', 'help': 'Analysis period start date'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Analysis period end date'},
                    {'name': 'topic_categories', 'type': 'multiselect', 'required': False, 'options': ['Technical Support', 'Product Questions', 'Account Management', 'Billing', 'Feature Requests', 'Bug Reports', 'General Inquiry'], 'help': 'Topic categories to analyze'},
                    {'name': 'sentiment_analysis', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include sentiment analysis of conversations'},
                    {'name': 'user_engagement_scoring', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Calculate user engagement scores'},
                    {'name': 'escalation_patterns', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Analyze escalation to human agents'},
                    {'name': 'session_duration_threshold', 'type': 'number', 'required': False, 'default': 300, 'help': 'Session duration threshold in seconds for engagement analysis'},
                    {'name': 'response_time_sla', 'type': 'number', 'required': False, 'default': 5, 'help': 'Response time SLA in seconds'},
                    {'name': 'include_multilingual', 'type': 'boolean', 'required': False, 'default': False, 'help': 'Include multi-language usage patterns'}
                ],
                'visualizations': [
                    {'type': 'line_chart', 'title': 'Chat Usage Trends', 'data_key': 'usage_trends'},
                    {'type': 'word_cloud', 'title': 'Popular Topics', 'data_key': 'popular_topics'},
                    {'type': 'pie_chart', 'title': 'Response Quality Distribution', 'data_key': 'response_quality'}
                ]
            },
            'output_formats': ['pdf', 'xlsx'],
            'estimated_time_minutes': 6,
            'requires_scrambling': True,
            'scrambling_profile': 'chat_analytics',
            'security_level': 'standard'
        },
        
        {
            'name': 'encryption_status_report',
            'display_name': 'Data Encryption Status Report',
            'description': 'Comprehensive overview of data encryption coverage, key management, and security compliance.',
            'category': 'security',
            'template_config': {
                'data_sources': ['file_assets', 'encryption_logs', 'key_rotations'],
                'queries': {
                    'encryption_coverage': 'SELECT file_type, COUNT(*) as total_files, SUM(CASE WHEN encrypted = true THEN 1 ELSE 0 END) as encrypted_files FROM file_assets GROUP BY file_type',
                    'key_rotation_history': 'SELECT DATE(rotated_at) as date, COUNT(*) as rotations FROM key_rotations WHERE rotated_at >= :start_date GROUP BY DATE(rotated_at)',
                    'encryption_failures': 'SELECT error_type, COUNT(*) as failure_count FROM encryption_logs WHERE status = "failed" AND created_at >= :start_date GROUP BY error_type'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '90_days_ago', 'help': 'Encryption analysis period start'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Encryption analysis period end'},
                    {'name': 'compliance_standards', 'type': 'multiselect', 'required': False, 'options': ['FIPS 140-2', 'AES-256', 'RSA-2048', 'NIST SP 800-53', 'Common Criteria'], 'default': ['AES-256'], 'help': 'Encryption standards to validate against'},
                    {'name': 'encryption_algorithms', 'type': 'multiselect', 'required': False, 'options': ['AES-256-GCM', 'AES-256-CBC', 'ChaCha20-Poly1305', 'RSA-OAEP', 'ECC-P256'], 'help': 'Specific algorithms to analyze'},
                    {'name': 'key_rotation_schedule', 'type': 'select', 'required': False, 'options': ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Annually'], 'default': 'Monthly', 'help': 'Expected key rotation frequency'},
                    {'name': 'alert_on_weak_keys', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Flag cryptographically weak keys'},
                    {'name': 'include_hsm_keys', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include Hardware Security Module keys'},
                    {'name': 'quantum_readiness_check', 'type': 'boolean', 'required': False, 'default': False, 'help': 'Assess quantum computing resistance'}
                ],
                'visualizations': [
                    {'type': 'stacked_bar_chart', 'title': 'Encryption Coverage by File Type', 'data_key': 'encryption_coverage'},
                    {'type': 'line_chart', 'title': 'Key Rotation Activity', 'data_key': 'key_rotation_history'},
                    {'type': 'table', 'title': 'Encryption Failures', 'data_key': 'encryption_failures'}
                ]
            },
            'output_formats': ['pdf', 'xlsx'],
            'estimated_time_minutes': 4,
            'requires_scrambling': False,
            'security_level': 'high',
            'required_role': 'admin'
        },
        
        {
            'name': 'storage_utilization_report',
            'display_name': 'Honey Reserve Storage Report',
            'description': 'Analysis of storage usage patterns, quota utilization, and cleanup recommendations.',
            'category': 'storage',
            'template_config': {
                'data_sources': ['file_assets', 'storage_quotas', 'cleanup_logs'],
                'queries': {
                    'quota_utilization': 'SELECT user_id, used_bytes, quota_bytes, (used_bytes::float / quota_bytes * 100) as utilization_percent FROM storage_quotas WHERE active = true',
                    'storage_by_type': 'SELECT file_type, COUNT(*) as file_count, SUM(file_size) as total_bytes FROM file_assets WHERE deleted_at IS NULL GROUP BY file_type',
                    'cleanup_activity': 'SELECT DATE(cleaned_at) as date, files_cleaned, bytes_freed FROM cleanup_logs WHERE cleaned_at >= :start_date'
                },
                'parameters': [
                    {'name': 'start_date', 'type': 'date', 'required': True, 'default': '30_days_ago', 'help': 'Storage analysis period start'},
                    {'name': 'end_date', 'type': 'date', 'required': False, 'default': 'today', 'help': 'Storage analysis period end'},
                    {'name': 'quota_threshold', 'type': 'number', 'required': False, 'default': 80, 'help': 'Alert threshold for quota utilization (%)'},
                    {'name': 'cost_per_gb', 'type': 'number', 'required': False, 'default': 0.15, 'help': 'Cost per GB for financial analysis'},
                    {'name': 'retention_policies', 'type': 'multiselect', 'required': False, 'options': ['7 Days', '30 Days', '90 Days', '1 Year', '7 Years', 'Indefinite'], 'help': 'Retention policies to analyze'},
                    {'name': 'cleanup_recommendations', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Generate automated cleanup recommendations'},
                    {'name': 'growth_projections', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include 6-month growth projections'},
                    {'name': 'tier_analysis', 'type': 'boolean', 'required': False, 'default': False, 'help': 'Analyze hot/warm/cold storage tiers'},
                    {'name': 'compliance_aging', 'type': 'boolean', 'required': False, 'default': True, 'help': 'Include compliance-based aging analysis'}
                ],
                'visualizations': [
                    {'type': 'histogram', 'title': 'Storage Quota Utilization', 'data_key': 'quota_utilization'},
                    {'type': 'pie_chart', 'title': 'Storage by File Type', 'data_key': 'storage_by_type'},
                    {'type': 'area_chart', 'title': 'Cleanup Activity', 'data_key': 'cleanup_activity'}
                ]
            },
            'output_formats': ['pdf', 'xlsx', 'csv'],
            'estimated_time_minutes': 3,
            'requires_scrambling': True,
            'scrambling_profile': 'gdpr_compliant',
            'security_level': 'standard'
        }
    ]
    
    try:
        if session is None:
            with get_db_session() as session:
                return _create_templates_with_session(session, templates)
        else:
            return _create_templates_with_session(session, templates)
            
    except Exception as e:
        logger.error(f"Error creating default templates: {e}")
        raise

def _create_templates_with_session(session, templates):
    """Internal function to create templates with given session"""
    created_count = 0
    
    for template_data in templates:
        # Check if template already exists
        existing = session.query(ReportTemplate).filter(
            ReportTemplate.name == template_data['name']
        ).first()
        
        if existing:
            logger.info(f"Template '{template_data['name']}' already exists, skipping")
            continue
        
        # Map template names to generator classes
        generator_map = {
            'honey_jar_summary': 'HoneyJarSummaryGenerator',
            'user_activity_audit': 'UserActivityAuditGenerator',
            'document_processing_report': 'DocumentProcessingReportGenerator',
            'bee_chat_analytics': 'BeeChatAnalyticsGenerator',
            'encryption_status_report': 'EncryptionStatusReportGenerator',
            'storage_utilization_report': 'StorageUtilizationReportGenerator'
        }
        
        # Create new template
        template = ReportTemplate(
            name=template_data['name'],
            display_name=template_data['display_name'],
            description=template_data['description'],
            category=template_data['category'],
            generator_class=generator_map.get(template_data['name'], 'BaseReportGenerator'),
            parameters=template_data['template_config'].get('parameters', []),
            template_config=template_data['template_config'],
            output_formats=template_data['output_formats'],
            estimated_time_minutes=template_data['estimated_time_minutes'],
            requires_scrambling=template_data['requires_scrambling'],
            scrambling_profile=template_data.get('scrambling_profile'),
            security_level=template_data['security_level'],
            required_role=template_data.get('required_role', 'user'),
            created_by='system',
            is_active=True
        )
        
        session.add(template)
        created_count += 1
        
        logger.info(f"Created template: {template_data['display_name']}")
    
    session.commit()
    
    logger.info(f"Successfully created {created_count} report templates")
    return created_count

def main():
    """Main function to initialize templates"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        count = create_default_templates()
        print(f"✅ Successfully initialized {count} default report templates")
        
    except Exception as e:
        print(f"❌ Failed to initialize templates: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())