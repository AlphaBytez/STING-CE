#!/usr/bin/env python3
"""
PII Configuration API Routes
Provides endpoints for managing PII detection patterns and configuration
"""

from flask import Blueprint, request, jsonify, current_app, g
import logging
import json
import re
from typing import Dict, List, Any
from datetime import datetime
from functools import wraps

from app.services.hive_scrambler import HiveScrambler, PIIType, ComplianceFramework, DetectionMode
from app.utils.decorators import require_auth

pii_bp = Blueprint('pii', __name__)
logger = logging.getLogger(__name__)

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not g.user.is_admin and not g.user.is_super_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@pii_bp.route('/patterns', methods=['GET'])
@require_auth
def get_pii_patterns():
    """Get all available PII detection patterns"""
    try:
        # Initialize scrambler to get patterns
        scrambler = HiveScrambler()
        
        patterns = []
        
        # Convert built-in patterns to frontend format
        for pii_type, pattern_obj in scrambler.patterns.items():
            # Map PII type to category and framework
            category, framework, severity, description = _get_pattern_metadata(pii_type)
            
            patterns.append({
                'id': pii_type.value,
                'name': _get_pattern_display_name(pii_type),
                'pattern': pattern_obj.pattern,
                'description': description,
                'category': category,
                'framework': framework,
                'severity': severity,
                'confidence': _get_pattern_confidence(pii_type),
                'enabled': True,
                'custom': False,
                'detection_count': 0,  # Would come from audit service in production
                'last_detected': None,
                'examples': _get_pattern_examples(pii_type),
                'compliance_frameworks': _get_compliance_frameworks(pii_type)
            })
        
        # Add medical patterns
        for pii_type, pattern_obj in scrambler.medical_patterns.items():
            category, framework, severity, description = _get_pattern_metadata(pii_type)
            
            patterns.append({
                'id': pii_type.value,
                'name': _get_pattern_display_name(pii_type),
                'pattern': pattern_obj.pattern,
                'description': description,
                'category': 'medical',
                'framework': 'hipaa',
                'severity': severity,
                'confidence': _get_pattern_confidence(pii_type),
                'enabled': True,
                'custom': False,
                'detection_count': 0,
                'last_detected': None,
                'examples': _get_pattern_examples(pii_type),
                'compliance_frameworks': ['HIPAA']
            })
        
        # Add legal patterns
        for pii_type, pattern_obj in scrambler.legal_patterns.items():
            category, framework, severity, description = _get_pattern_metadata(pii_type)
            
            patterns.append({
                'id': pii_type.value,
                'name': _get_pattern_display_name(pii_type),
                'pattern': pattern_obj.pattern,
                'description': description,
                'category': 'legal',
                'framework': 'legal',
                'severity': severity,
                'confidence': _get_pattern_confidence(pii_type),
                'enabled': True,
                'custom': False,
                'detection_count': 0,
                'last_detected': None,
                'examples': _get_pattern_examples(pii_type),
                'compliance_frameworks': ['Attorney-Client']
            })
        
        return jsonify({
            'patterns': patterns,
            'total_count': len(patterns)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving PII patterns: {str(e)}")
        return jsonify({'error': 'Failed to retrieve PII patterns'}), 500

@pii_bp.route('/frameworks', methods=['GET'])
@require_auth
def get_compliance_frameworks():
    """Get all available compliance frameworks"""
    try:
        frameworks = [
            {
                'id': 'hipaa',
                'name': 'HIPAA',
                'description': 'Health Insurance Portability and Accountability Act',
                'categories': ['medical', 'personal'],
                'mandatory_patterns': ['medical_record_number', 'patient_id', 'social_security_number'],
                'risk_threshold': 'medium',
                'retention_days': 2555,  # 7 years
                'encryption_required': True,
                'active': True
            },
            {
                'id': 'gdpr',
                'name': 'GDPR',
                'description': 'General Data Protection Regulation',
                'categories': ['personal', 'contact'],
                'mandatory_patterns': ['email_address', 'phone_number', 'person_name'],
                'risk_threshold': 'low',
                'retention_days': 1095,  # 3 years
                'encryption_required': True,
                'active': True
            },
            {
                'id': 'pci_dss',
                'name': 'PCI DSS',
                'description': 'Payment Card Industry Data Security Standard',
                'categories': ['financial'],
                'mandatory_patterns': ['credit_card', 'bank_account'],
                'risk_threshold': 'critical',
                'retention_days': 365,  # 1 year
                'encryption_required': True,
                'active': True
            },
            {
                'id': 'legal',
                'name': 'Attorney-Client',
                'description': 'Attorney-Client Privilege Protection',
                'categories': ['legal'],
                'mandatory_patterns': ['case_number', 'bar_number', 'settlement_amount'],
                'risk_threshold': 'medium',
                'retention_days': 3650,  # 10 years
                'encryption_required': True,
                'active': True
            }
        ]
        
        return jsonify({
            'frameworks': frameworks,
            'total_count': len(frameworks)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving compliance frameworks: {str(e)}")
        return jsonify({'error': 'Failed to retrieve compliance frameworks'}), 500

@pii_bp.route('/test', methods=['POST'])
@require_auth
def test_pattern():
    """Test a regex pattern against sample text"""
    try:
        data = request.get_json()
        pattern_str = data.get('pattern')
        test_text = data.get('text', '')
        
        if not pattern_str:
            return jsonify({'error': 'Pattern is required'}), 400
        
        # Compile and test the pattern
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = []
            
            for match in pattern.finditer(test_text):
                matches.append({
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'context': test_text[max(0, match.start() - 20):match.end() + 20]
                })
            
            return jsonify({
                'matches': matches,
                'count': len(matches),
                'pattern_valid': True
            })
            
        except re.error as e:
            return jsonify({
                'matches': [],
                'count': 0,
                'pattern_valid': False,
                'error': f'Invalid regex pattern: {str(e)}'
            })
        
    except Exception as e:
        logger.error(f"Error testing pattern: {str(e)}")
        return jsonify({'error': 'Failed to test pattern'}), 500

@pii_bp.route('/import', methods=['POST'])
@require_admin
def import_patterns():
    """Import PII patterns from JSON file"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate import data structure
        if isinstance(data, dict) and 'patterns' in data:
            patterns_data = data['patterns']
        elif isinstance(data, list):
            patterns_data = data
        else:
            return jsonify({'error': 'Invalid data format. Expected patterns array or config object with patterns.'}), 400
        
        imported_count = 0
        errors = []
        
        for pattern_data in patterns_data:
            try:
                # Validate required fields
                required_fields = ['name', 'pattern', 'description', 'category', 'framework', 'severity']
                missing_fields = [field for field in required_fields if field not in pattern_data]
                
                if missing_fields:
                    errors.append(f"Pattern '{pattern_data.get('name', 'unknown')}' missing fields: {', '.join(missing_fields)}")
                    continue
                
                # Validate regex pattern
                try:
                    re.compile(pattern_data['pattern'])
                except re.error as e:
                    errors.append(f"Pattern '{pattern_data['name']}' has invalid regex: {str(e)}")
                    continue
                
                # Validate category and framework values
                valid_categories = ['personal', 'medical', 'legal', 'financial', 'contact']
                valid_frameworks = ['hipaa', 'gdpr', 'pci_dss', 'legal', 'custom']
                valid_severities = ['critical', 'high', 'medium', 'low']
                
                if pattern_data['category'] not in valid_categories:
                    errors.append(f"Pattern '{pattern_data['name']}' has invalid category: {pattern_data['category']}")
                    continue
                
                if pattern_data['framework'] not in valid_frameworks:
                    errors.append(f"Pattern '{pattern_data['name']}' has invalid framework: {pattern_data['framework']}")
                    continue
                
                if pattern_data['severity'] not in valid_severities:
                    errors.append(f"Pattern '{pattern_data['name']}' has invalid severity: {pattern_data['severity']}")
                    continue
                
                # Validate confidence score
                confidence = pattern_data.get('confidence', 0.90)
                if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                    errors.append(f"Pattern '{pattern_data['name']}' has invalid confidence score: {confidence}")
                    continue
                
                # TODO: Save to database or configuration storage
                # For now, just count as imported
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error processing pattern '{pattern_data.get('name', 'unknown')}': {str(e)}")
                continue
        
        return jsonify({
            'imported_count': imported_count,
            'total_patterns': len(patterns_data),
            'errors': errors,
            'success': imported_count > 0
        })
        
    except Exception as e:
        logger.error(f"Error importing patterns: {str(e)}")
        return jsonify({'error': 'Failed to import patterns'}), 500

@pii_bp.route('/profile/<profile_id>/settings', methods=['GET'])
@require_auth
def get_profile_settings(profile_id):
    """Get PII profile configuration settings"""
    try:
        # Default settings structure for now - would come from database in production
        default_settings = {
            'profile': {
                'id': profile_id,
                'name': _get_profile_name(profile_id),
                'description': _get_profile_description(profile_id),
                'active': True,
                'priority': 'medium'
            },
            'sensitivity': {
                'detection_threshold': 0.75,
                'confidence_threshold': 0.85,
                'pattern_matching_mode': 'balanced',
                'context_analysis_enabled': True,
                'false_positive_reduction': True,
                'minimum_match_length': 3
            },
            'actions': {
                'immediate_actions': {
                    'quarantine_data': True,
                    'notify_admin': True,
                    'block_processing': False,
                    'create_audit_log': True
                },
                'automated_workflows': {
                    'data_classification': True,
                    'encryption_trigger': True,
                    'access_restriction': False,
                    'compliance_tagging': True
                },
                'escalation_rules': {
                    'high_risk_escalation': True,
                    'multiple_detections_escalation': True,
                    'escalation_threshold': 5,
                    'escalation_timeframe': 3600
                }
            },
            'retention': {
                'data_retention_enabled': True,
                'retention_period_days': _get_default_retention_days(profile_id),
                'automatic_deletion': False,
                'archive_before_deletion': True,
                'retention_exceptions': [],
                'purge_logs_after_days': 365,
                'compliance_hold_enabled': False
            },
            'notifications': {
                'email_alerts': {
                    'enabled': True,
                    'recipients': [],
                    'alert_frequency': 'immediate',
                    'include_context': False,
                    'severity_threshold': 'medium'
                },
                'dashboard_alerts': {
                    'enabled': True,
                    'show_statistics': True,
                    'show_trends': True,
                    'alert_persistence_days': 30
                },
                'audit_notifications': {
                    'enabled': True,
                    'include_remediation_actions': True,
                    'notify_on_pattern_updates': True
                }
            },
            'advanced': {
                'machine_learning_enhancement': False,
                'pattern_learning_enabled': False,
                'contextual_analysis_depth': 'medium',
                'cross_document_correlation': False,
                'api_integration_enabled': False,
                'custom_preprocessing_rules': [],
                'performance_optimization': 'balanced'
            }
        }
        
        return jsonify({'settings': default_settings})
        
    except Exception as e:
        logger.error(f"Error retrieving profile settings: {str(e)}")
        return jsonify({'error': 'Failed to retrieve profile settings'}), 500

@pii_bp.route('/profile/<profile_id>/settings', methods=['PUT'])
@require_admin
def update_profile_settings(profile_id):
    """Update PII profile configuration settings"""
    try:
        settings_data = request.get_json()
        
        if not settings_data:
            return jsonify({'error': 'No settings data provided'}), 400
        
        # Validate settings structure
        validation_errors = _validate_profile_settings(settings_data)
        if validation_errors:
            return jsonify({'error': 'Invalid settings', 'validation_errors': validation_errors}), 400
        
        # TODO: Save settings to database/configuration storage
        # For now, just log the settings
        logger.info(f"Updated settings for profile {profile_id}: {settings_data}")
        
        return jsonify({
            'success': True,
            'message': 'Profile settings updated successfully',
            'profile_id': profile_id
        })
        
    except Exception as e:
        logger.error(f"Error updating profile settings: {str(e)}")
        return jsonify({'error': 'Failed to update profile settings'}), 500

@pii_bp.route('/profile/<profile_id>/test', methods=['POST'])
@require_auth
def test_profile_configuration(profile_id):
    """Test PII profile configuration and provide performance estimates"""
    try:
        settings_data = request.get_json()
        
        if not settings_data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Simulate configuration testing and analysis
        test_results = _analyze_profile_configuration(settings_data)
        
        return jsonify(test_results)
        
    except Exception as e:
        logger.error(f"Error testing profile configuration: {str(e)}")
        return jsonify({'error': 'Failed to test configuration'}), 500

@pii_bp.route('/export', methods=['GET'])
@require_auth
def export_patterns():
    """Export current PII configuration"""
    try:
        # Get current patterns (this would come from database in production)
        response = get_pii_patterns()
        patterns_data = response[0].get_json()
        
        if not patterns_data:
            return jsonify({'error': 'Failed to retrieve patterns for export'}), 500
        
        export_data = {
            'version': '1.0',
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'patterns': patterns_data['patterns'],
            'compliance_profiles': [],  # Would come from get_compliance_frameworks()
            'custom_rules': []
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        logger.error(f"Error exporting patterns: {str(e)}")
        return jsonify({'error': 'Failed to export patterns'}), 500

def _get_pattern_metadata(pii_type: PIIType) -> tuple:
    """Get metadata for a PII type"""
    metadata_map = {
        # Personal
        PIIType.SSN: ('personal', 'hipaa', 'critical', 'US Social Security Number'),
        PIIType.DRIVERS_LICENSE: ('personal', 'gdpr', 'high', "Driver's License Number"),
        PIIType.PASSPORT: ('personal', 'gdpr', 'high', 'Passport Number'),
        PIIType.NAME: ('personal', 'gdpr', 'medium', 'Person Name'),
        PIIType.DATE_OF_BIRTH: ('personal', 'hipaa', 'high', 'Date of Birth'),
        
        # Financial
        PIIType.CREDIT_CARD: ('financial', 'pci_dss', 'critical', 'Credit Card Number'),
        PIIType.BANK_ACCOUNT: ('financial', 'pci_dss', 'critical', 'Bank Account Number'),
        PIIType.ROUTING_NUMBER: ('financial', 'pci_dss', 'high', 'Bank Routing Number'),
        
        # Contact
        PIIType.EMAIL: ('contact', 'gdpr', 'medium', 'Email Address'),
        PIIType.PHONE: ('contact', 'gdpr', 'medium', 'Phone Number'),
        PIIType.ADDRESS: ('contact', 'gdpr', 'medium', 'Physical Address'),
        
        # Medical
        PIIType.MEDICAL_RECORD: ('medical', 'hipaa', 'high', 'Medical Record Number'),
        PIIType.PATIENT_ID: ('medical', 'hipaa', 'high', 'Patient ID'),
        PIIType.HEALTH_INSURANCE: ('medical', 'hipaa', 'high', 'Health Insurance ID'),
        PIIType.DEA_NUMBER: ('medical', 'hipaa', 'high', 'DEA Number'),
        PIIType.NPI_NUMBER: ('medical', 'hipaa', 'medium', 'NPI Number'),
        PIIType.MEDICARE_ID: ('medical', 'hipaa', 'high', 'Medicare ID'),
        PIIType.MEDICAID_ID: ('medical', 'hipaa', 'high', 'Medicaid ID'),
        
        # Legal
        PIIType.CASE_NUMBER: ('legal', 'legal', 'high', 'Legal Case Number'),
        PIIType.BAR_NUMBER: ('legal', 'legal', 'medium', 'Attorney Bar Number'),
        PIIType.SETTLEMENT_AMOUNT: ('legal', 'legal', 'high', 'Settlement Amount'),
        PIIType.CLIENT_MATTER_ID: ('legal', 'legal', 'high', 'Client Matter ID'),
        PIIType.TRUST_ACCOUNT: ('legal', 'legal', 'critical', 'Trust Account'),
        
        # Digital
        PIIType.IP_ADDRESS: ('personal', 'gdpr', 'low', 'IP Address'),
        PIIType.API_KEY: ('personal', 'custom', 'critical', 'API Key'),
        PIIType.USERNAME: ('personal', 'gdpr', 'low', 'Username'),
    }
    
    return metadata_map.get(pii_type, ('personal', 'custom', 'medium', pii_type.value.replace('_', ' ').title()))

def _get_pattern_display_name(pii_type: PIIType) -> str:
    """Get display name for PII type"""
    name_map = {
        PIIType.SSN: 'Social Security Number',
        PIIType.CREDIT_CARD: 'Credit Card Number',
        PIIType.EMAIL: 'Email Address',
        PIIType.PHONE: 'Phone Number',
        PIIType.IP_ADDRESS: 'IP Address',
        PIIType.API_KEY: 'API Key',
        PIIType.NAME: 'Person Name',
        PIIType.DATE_OF_BIRTH: 'Date of Birth',
        PIIType.MEDICAL_RECORD: 'Medical Record Number',
        PIIType.PATIENT_ID: 'Patient ID',
        PIIType.CASE_NUMBER: 'Case Number',
        PIIType.BAR_NUMBER: 'Bar Number',
        PIIType.SETTLEMENT_AMOUNT: 'Settlement Amount'
    }
    
    return name_map.get(pii_type, pii_type.value.replace('_', ' ').title())

def _get_pattern_confidence(pii_type: PIIType) -> float:
    """Get confidence score for PII type"""
    confidence_map = {
        PIIType.SSN: 0.95,
        PIIType.CREDIT_CARD: 0.98,
        PIIType.EMAIL: 0.90,
        PIIType.PHONE: 0.85,
        PIIType.IP_ADDRESS: 0.95,
        PIIType.API_KEY: 0.92,
        PIIType.MEDICAL_RECORD: 0.90,
        PIIType.CASE_NUMBER: 0.88,
        PIIType.SETTLEMENT_AMOUNT: 0.82
    }
    
    return confidence_map.get(pii_type, 0.85)

def _get_pattern_examples(pii_type: PIIType) -> List[str]:
    """Get example matches for PII type"""
    examples_map = {
        PIIType.SSN: ['123-45-6789', '987-65-4321'],
        PIIType.CREDIT_CARD: ['4111111111111111', '5555555555554444'],
        PIIType.EMAIL: ['user@example.com', 'admin@company.org'],
        PIIType.PHONE: ['(555) 123-4567', '+1-555-123-4567'],
        PIIType.IP_ADDRESS: ['192.168.1.1', '10.0.0.1'],
        PIIType.MEDICAL_RECORD: ['MRN: A123456', 'Medical Record: B789012'],
        PIIType.CASE_NUMBER: ['Case No: 2024-CV-12345', '2024/CR/98765'],
        PIIType.BAR_NUMBER: ['Bar No: 123456', 'Bar Number: 789012'],
        PIIType.SETTLEMENT_AMOUNT: ['settlement: $50,000', 'damages: $125,000']
    }
    
    return examples_map.get(pii_type, [])

def _get_compliance_frameworks(pii_type: PIIType) -> List[str]:
    """Get compliance frameworks for PII type"""
    framework_map = {
        PIIType.SSN: ['HIPAA', 'GDPR'],
        PIIType.CREDIT_CARD: ['PCI DSS'],
        PIIType.EMAIL: ['GDPR', 'CCPA'],
        PIIType.PHONE: ['GDPR', 'HIPAA'],
        PIIType.MEDICAL_RECORD: ['HIPAA'],
        PIIType.PATIENT_ID: ['HIPAA'],
        PIIType.CASE_NUMBER: ['Attorney-Client'],
        PIIType.BAR_NUMBER: ['Attorney-Client'],
        PIIType.SETTLEMENT_AMOUNT: ['Attorney-Client']
    }
    
    return framework_map.get(pii_type, ['Custom'])

def _get_profile_name(profile_id: str) -> str:
    """Get profile display name"""
    profile_names = {
        'hipaa': 'HIPAA Compliance Profile',
        'gdpr': 'GDPR Compliance Profile', 
        'pci_dss': 'PCI DSS Compliance Profile',
        'legal': 'Attorney-Client Privilege Profile'
    }
    return profile_names.get(profile_id, f'Profile {profile_id}')

def _get_profile_description(profile_id: str) -> str:
    """Get profile description"""
    descriptions = {
        'hipaa': 'Health Insurance Portability and Accountability Act compliance settings for healthcare data protection',
        'gdpr': 'General Data Protection Regulation compliance settings for personal data privacy', 
        'pci_dss': 'Payment Card Industry Data Security Standard compliance for financial data',
        'legal': 'Attorney-client privilege and legal professional compliance settings'
    }
    return descriptions.get(profile_id, f'Custom compliance profile settings for {profile_id}')

def _get_default_retention_days(profile_id: str) -> int:
    """Get default retention period for profile"""
    retention_defaults = {
        'hipaa': 2555,    # 7 years
        'gdpr': 1095,     # 3 years
        'pci_dss': 365,   # 1 year
        'legal': 3650     # 10 years
    }
    return retention_defaults.get(profile_id, 2555)

def _validate_profile_settings(settings: dict) -> list:
    """Validate profile settings structure and values"""
    errors = []
    
    try:
        # Validate profile section
        if 'profile' not in settings:
            errors.append("Missing 'profile' section")
        elif not settings['profile'].get('name'):
            errors.append("Profile name is required")
        
        # Validate sensitivity section
        if 'sensitivity' in settings:
            sensitivity = settings['sensitivity']
            if not (0.1 <= sensitivity.get('detection_threshold', 0) <= 1.0):
                errors.append("Detection threshold must be between 0.1 and 1.0")
            if not (0.1 <= sensitivity.get('confidence_threshold', 0) <= 1.0):
                errors.append("Confidence threshold must be between 0.1 and 1.0")
        
        # Validate retention section
        if 'retention' in settings:
            retention = settings['retention']
            if retention.get('data_retention_enabled') and retention.get('retention_period_days', 0) < 1:
                errors.append("Retention period must be at least 1 day when retention is enabled")
        
        # Validate notifications section
        if 'notifications' in settings:
            notifications = settings['notifications']
            email_alerts = notifications.get('email_alerts', {})
            if email_alerts.get('enabled') and not email_alerts.get('recipients'):
                errors.append("Email recipients required when email alerts are enabled")
        
    except Exception as e:
        errors.append(f"Settings validation error: {str(e)}")
    
    return errors

def _analyze_profile_configuration(settings: dict) -> dict:
    """Analyze profile configuration and provide performance/compliance estimates"""
    try:
        # Simulate analysis based on settings
        performance_score = 85
        accuracy_estimate = 90
        resource_usage = "Medium"
        compliance_status = "Compliant"
        recommendations = []
        
        # Adjust estimates based on settings
        sensitivity = settings.get('sensitivity', {})
        actions = settings.get('actions', {})
        advanced = settings.get('advanced', {})
        
        # Performance adjustments
        if sensitivity.get('pattern_matching_mode') == 'strict':
            accuracy_estimate += 5
            performance_score -= 10
        elif sensitivity.get('pattern_matching_mode') == 'permissive':
            accuracy_estimate -= 5
            performance_score += 10
        
        if advanced.get('machine_learning_enhancement'):
            accuracy_estimate += 10
            performance_score -= 15
            resource_usage = "High"
            recommendations.append("ML enhancement will improve accuracy but requires more CPU resources")
        
        if advanced.get('cross_document_correlation'):
            accuracy_estimate += 5
            performance_score -= 20
            resource_usage = "High" if resource_usage != "High" else "Very High"
            recommendations.append("Cross-document correlation significantly increases processing time")
        
        # Action complexity adjustments
        immediate_actions_count = sum(1 for v in actions.get('immediate_actions', {}).values() if v)
        if immediate_actions_count > 3:
            performance_score -= 5
            recommendations.append("Consider reducing immediate actions to improve processing speed")
        
        # Context analysis adjustments
        context_depth = advanced.get('contextual_analysis_depth', 'medium')
        if context_depth == 'deep':
            accuracy_estimate += 8
            performance_score -= 25
            recommendations.append("Deep contextual analysis provides best accuracy but slowest performance")
        elif context_depth == 'shallow':
            accuracy_estimate -= 5
            performance_score += 15
        
        # Performance optimization adjustments
        perf_mode = advanced.get('performance_optimization', 'balanced')
        if perf_mode == 'speed':
            performance_score += 20
            accuracy_estimate -= 5
        elif perf_mode == 'accuracy':
            performance_score -= 15
            accuracy_estimate += 8
        
        # Compliance validation
        retention = settings.get('retention', {})
        if not retention.get('data_retention_enabled'):
            compliance_status = "Warning: Data retention disabled"
            recommendations.append("Enable data retention for full compliance")
        
        notifications = settings.get('notifications', {})
        if not notifications.get('audit_notifications', {}).get('enabled'):
            compliance_status = "Warning: Audit notifications disabled"
            recommendations.append("Enable audit notifications for compliance tracking")
        
        # Ensure realistic bounds
        performance_score = max(10, min(100, performance_score))
        accuracy_estimate = max(50, min(99, accuracy_estimate))
        
        return {
            'performance_score': performance_score,
            'accuracy_estimate': accuracy_estimate,
            'resource_usage': resource_usage,
            'compliance_status': compliance_status,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error analyzing configuration: {str(e)}")
        return {
            'performance_score': 75,
            'accuracy_estimate': 85,
            'resource_usage': 'Medium',
            'compliance_status': 'Analysis Error',
            'recommendations': ['Configuration analysis failed - using default estimates'],
            'analysis_timestamp': datetime.utcnow().isoformat() + 'Z'
        }