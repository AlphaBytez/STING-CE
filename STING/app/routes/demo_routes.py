#!/usr/bin/env python3
"""
Demo Data Management Routes
Provides endpoints for generating and managing demo data for STING platform
"""

import os
import random
import tempfile
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.middleware.auth_middleware import require_admin
from app.utils.decorators import require_auth_method
# Core imports
from app.extensions import db
from app.models import User
from app.models.nectar_bot_models import NectarBot, NectarBotHandoff, NectarBotUsage, BotStatus, HandoffStatus, HandoffUrgency
# Report models - use correct model structure
from app.models.report_models import Report, ReportTemplate, ReportStatus
# Honey Jar operations via knowledge service API
from app.services.honey_jar_service import HoneyJarService, get_honey_jar_service
# Demo data generators
from app.services.demo_data_generator import MedicalDemoGenerator, LegalDemoGenerator, FinancialDemoGenerator
# PostgreSQL JSONB support
from sqlalchemy import cast, text
from sqlalchemy.dialects.postgresql import JSONB
import json
import uuid


def get_admin_user():
    """
    Get the admin user dynamically instead of hardcoding owner_id=1.
    Returns tuple of (user_id, kratos_id, email) or (None, None, None) if not found.
    """
    try:
        # Try to find admin by role first
        admin = User.query.filter(
            (User.role == 'admin') | (User.email == 'admin@sting.local')
        ).first()

        if admin:
            return admin.id, admin.kratos_id, admin.email

        # Fallback: get the first user (usually admin in fresh installs)
        first_user = User.query.order_by(User.id).first()
        if first_user:
            current_app.logger.warning(f"No admin user found, using first user: {first_user.email}")
            return first_user.id, first_user.kratos_id, first_user.email

        current_app.logger.error("No users found in database for demo data generation")
        return None, None, None
    except Exception as e:
        current_app.logger.error(f"Error getting admin user: {str(e)}")
        return None, None, None


def filter_by_demo_metadata(model):
    """
    Create proper PostgreSQL JSONB filter for demo_data flag.
    Works correctly with SQLAlchemy and PostgreSQL JSONB columns.
    """
    # Use JSONB containment operator @> for PostgreSQL
    return model.metadata.op('@>')(cast({'demo_data': True}, JSONB))

demo_bp = Blueprint('demo', __name__, url_prefix='/api/admin')

@demo_bp.route('/generate-demo-data', methods=['POST'])
@require_admin
@require_auth_method(['webauthn', 'totp'])
def generate_demo_data():
    """
    Generate demo data for testing and demonstrations
    Expected payload: {"scenario": "basic|comprehensive|security-focused|pii-scrubbing", "step": 1, "totalSteps": 5}
    """
    try:
        data = request.get_json() or {}
        scenario = data.get('scenario', 'basic')
        step = data.get('step', 1)
        total_steps = data.get('totalSteps', 5)
        
        current_app.logger.info(f"Generating demo data - Scenario: {scenario}, Step: {step}/{total_steps}")
        
        # Initialize result counters
        result = {
            'success': True,
            'scenario': scenario,
            'step': step,
            'totalSteps': total_steps,
            'generated': {},
            'message': ''
        }
        
        # Define what each step does based on scenario
        if scenario == 'basic':
            result['generated'] = _generate_basic_demo_step(step)
        elif scenario == 'comprehensive':
            result['generated'] = _generate_comprehensive_demo_step(step)
        elif scenario == 'security-focused':
            result['generated'] = _generate_security_demo_step(step)
        elif scenario == 'pii-scrubbing':
            result['generated'] = _generate_pii_demo_step(step)
        elif scenario == 'nectar-bot':
            result['generated'] = _generate_nectar_bot_demo_step(step)
        else:
            return jsonify({'error': 'Invalid scenario'}), 400
        
        result['message'] = f"Step {step}/{total_steps} completed for {scenario} scenario"
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Demo data generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate demo data',
            'details': str(e)
        }), 500

def _generate_basic_demo_step(step):
    """Generate basic demo data step by step"""
    generated = {'honeyJars': 0, 'documents': 0, 'reports': 0, 'users': 0, 'nectarBots': 0}

    try:
        if step == 1:  # Create honey jars
            jars_created = _create_basic_honey_jars()
            generated['honeyJars'] = jars_created

        elif step == 2:  # Generate sample documents
            docs_created = _create_sample_documents('basic')
            generated['documents'] = docs_created

        elif step == 3:  # Build reports and create nectar bots
            reports_created = _create_sample_reports('basic')
            bots_created = _create_demo_nectar_bots('basic')
            generated['reports'] = reports_created
            generated['nectarBots'] = bots_created

        elif step == 4:  # Setup PII data and bot usage
            _create_pii_samples('basic')
            _create_demo_bot_usage('basic')

        elif step == 5:  # Finalize
            _finalize_demo_setup('basic')

    except Exception as e:
        current_app.logger.error(f"Error in basic demo step {step}: {str(e)}")

    return generated

def _generate_comprehensive_demo_step(step):
    """Generate comprehensive demo data step by step"""
    generated = {'honeyJars': 0, 'documents': 0, 'reports': 0, 'users': 0, 'nectarBots': 0}

    try:
        if step == 1:  # Create extensive honey jars
            jars_created = _create_comprehensive_honey_jars()
            generated['honeyJars'] = jars_created

        elif step == 2:  # Generate many documents
            docs_created = _create_sample_documents('comprehensive')
            generated['documents'] = docs_created

        elif step == 3:  # Build comprehensive reports and create nectar bots
            reports_created = _create_sample_reports('comprehensive')
            bots_created = _create_demo_nectar_bots('comprehensive')
            generated['reports'] = reports_created
            generated['nectarBots'] = bots_created

        elif step == 4:  # Advanced PII and compliance, users, and bot usage
            _create_pii_samples('comprehensive')
            users_created = _create_demo_users()
            _create_demo_bot_usage('comprehensive')
            generated['users'] = users_created

        elif step == 5:  # Finalize comprehensive setup
            _finalize_demo_setup('comprehensive')

    except Exception as e:
        current_app.logger.error(f"Error in comprehensive demo step {step}: {str(e)}")

    return generated

def _generate_security_demo_step(step):
    """Generate security-focused demo data step by step"""
    generated = {'honeyJars': 0, 'documents': 0, 'reports': 0, 'users': 0}
    
    try:
        if step == 1:  # Security-focused honey jars
            jars_created = _create_security_honey_jars()
            generated['honeyJars'] = jars_created
            
        elif step == 2:  # Security documents
            docs_created = _create_sample_documents('security')
            generated['documents'] = docs_created
            
        elif step == 3:  # Compliance reports
            reports_created = _create_sample_reports('security')
            generated['reports'] = reports_created
            
        elif step == 4:  # Security audit trails
            _create_security_audit_data()
            
        elif step == 5:  # Finalize security setup
            _finalize_demo_setup('security')
            
    except Exception as e:
        current_app.logger.error(f"Error in security demo step {step}: {str(e)}")
        
    return generated

def _generate_pii_demo_step(step):
    """Generate PII scrubbing demo data step by step"""
    generated = {'honeyJars': 0, 'documents': 0, 'reports': 0, 'users': 0}
    
    try:
        if step == 1:  # PII-focused honey jars
            jars_created = _create_pii_honey_jars()
            generated['honeyJars'] = jars_created
            generated['documents'] = _create_pii_documents()
            
        elif step == 2:  # Generate diverse PII patterns
            _create_advanced_pii_patterns()
            
        elif step == 3:  # PII detection reports
            reports_created = _create_sample_reports('pii')
            generated['reports'] = reports_created
            
        elif step == 4:  # Custom PII rules
            _create_custom_pii_rules()
            
        elif step == 5:  # Finalize PII setup
            _finalize_demo_setup('pii')
            
    except Exception as e:
        current_app.logger.error(f"Error in PII demo step {step}: {str(e)}")
        
    return generated

def _generate_nectar_bot_demo_step(step):
    """Generate Nectar Bot focused demo data step by step"""
    generated = {'honeyJars': 0, 'documents': 0, 'reports': 0, 'users': 0, 'nectarBots': 0, 'handoffs': 0, 'conversations': 0}

    try:
        if step == 1:  # Create honey jars optimized for bot knowledge
            jars_created = _create_bot_knowledge_honey_jars()
            generated['honeyJars'] = jars_created

        elif step == 2:  # Generate bot training documents
            docs_created = _create_bot_training_documents()
            generated['documents'] = docs_created

        elif step == 3:  # Create comprehensive nectar bots
            bots_created = _create_demo_nectar_bots('nectar-bot')
            generated['nectarBots'] = bots_created

        elif step == 4:  # Generate bot conversations and usage data
            conversations_created = _create_demo_bot_conversations()
            _create_demo_bot_usage('nectar-bot')
            generated['conversations'] = conversations_created

        elif step == 5:  # Create handoff scenarios and finalize
            handoffs_created = _create_demo_bot_handoffs()
            _finalize_demo_setup('nectar-bot')
            generated['handoffs'] = handoffs_created

    except Exception as e:
        current_app.logger.error(f"Error in nectar-bot demo step {step}: {str(e)}")

    return generated

def _create_basic_honey_jars():
    """Create basic set of honey jars via knowledge service API"""
    basic_jars = [
        {'name': 'Medical Records Demo', 'description': 'Sample medical documents for HIPAA compliance testing', 'tags': ['healthcare', 'hipaa', 'demo']},
        {'name': 'Legal Documents Demo', 'description': 'Sample legal documents with attorney-client privilege', 'tags': ['legal', 'privileged', 'demo']},
        {'name': 'Financial Data Demo', 'description': 'Sample financial documents for PCI compliance', 'tags': ['financial', 'pci', 'demo']},
        {'name': 'HR Records Demo', 'description': 'Sample employee records with PII', 'tags': ['hr', 'pii', 'demo']},
        {'name': 'Customer Data Demo', 'description': 'Sample customer information and transactions', 'tags': ['customer', 'pii', 'demo']}
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for jar_config in basic_jars:
        try:
            jar_id = honey_jar_service.create_honey_jar(
                name=jar_config['name'],
                description=jar_config['description'],
                jar_type='public',
                tags=jar_config['tags']
            )
            if jar_id:
                created += 1
                current_app.logger.info(f"Created demo honey jar: {jar_config['name']} (ID: {jar_id})")
        except Exception as e:
            current_app.logger.error(f"Error creating honey jar {jar_config['name']}: {str(e)}")

    return created

def _create_comprehensive_honey_jars():
    """Create comprehensive set of honey jars via knowledge service API"""
    comprehensive_jars = [
        {'name': 'Enterprise Security Policies', 'description': 'Complete security policy documentation', 'tags': ['security', 'policies', 'demo']},
        {'name': 'Incident Response Playbooks', 'description': 'Security incident response procedures', 'tags': ['security', 'incident-response', 'demo']},
        {'name': 'Compliance Audit Reports', 'description': 'Historical compliance audit documentation', 'tags': ['compliance', 'audit', 'demo']},
        {'name': 'Vendor Management', 'description': 'Third-party vendor contracts and assessments', 'tags': ['procurement', 'vendor', 'demo']},
        {'name': 'Employee Training Materials', 'description': 'Security awareness and training content', 'tags': ['training', 'security', 'demo']},
        {'name': 'Risk Assessment Archive', 'description': 'Historical risk assessments and mitigation plans', 'tags': ['risk', 'assessment', 'demo']},
        {'name': 'Business Continuity Plans', 'description': 'Disaster recovery and continuity procedures', 'tags': ['bcp', 'disaster-recovery', 'demo']},
        {'name': 'Technical Documentation', 'description': 'System architecture and technical specifications', 'tags': ['technical', 'architecture', 'demo']},
        {'name': 'Legal Contracts Archive', 'description': 'Historical legal agreements and contracts', 'tags': ['legal', 'contracts', 'demo']},
        {'name': 'Financial Audit Trail', 'description': 'Financial records and audit documentation', 'tags': ['financial', 'audit', 'demo']}
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for jar_config in comprehensive_jars:
        try:
            jar_id = honey_jar_service.create_honey_jar(
                name=jar_config['name'],
                description=jar_config['description'],
                jar_type='public',
                tags=jar_config['tags']
            )
            if jar_id:
                created += 1
                current_app.logger.info(f"Created comprehensive demo honey jar: {jar_config['name']} (ID: {jar_id})")
        except Exception as e:
            current_app.logger.error(f"Error creating comprehensive honey jar {jar_config['name']}: {str(e)}")

    return created

def _create_security_honey_jars():
    """Create security-focused honey jars via knowledge service API"""
    security_jars = [
        {'name': 'Security Incident Reports', 'description': 'Historical security incidents and responses', 'tags': ['security', 'incidents', 'demo']},
        {'name': 'Vulnerability Assessments', 'description': 'Security vulnerability scan results', 'tags': ['security', 'vulnerability', 'demo']},
        {'name': 'Penetration Test Reports', 'description': 'Third-party security assessment reports', 'tags': ['security', 'pentest', 'demo']},
        {'name': 'Compliance Frameworks', 'description': 'SOC2, ISO27001, and other compliance documentation', 'tags': ['compliance', 'soc2', 'iso27001', 'demo']},
        {'name': 'Access Control Policies', 'description': 'Identity and access management procedures', 'tags': ['security', 'iam', 'demo']}
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for jar_config in security_jars:
        try:
            jar_id = honey_jar_service.create_honey_jar(
                name=jar_config['name'],
                description=jar_config['description'],
                jar_type='public',
                tags=jar_config['tags']
            )
            if jar_id:
                created += 1
                current_app.logger.info(f"Created security demo honey jar: {jar_config['name']} (ID: {jar_id})")
        except Exception as e:
            current_app.logger.error(f"Error creating security honey jar {jar_config['name']}: {str(e)}")

    return created

def _create_pii_honey_jars():
    """Create PII-focused honey jars via knowledge service API"""
    pii_jars = [
        {'name': 'PII Detection Samples', 'description': 'Documents with various PII types for testing', 'tags': ['pii', 'testing', 'demo']},
        {'name': 'HIPAA Test Documents', 'description': 'Medical records for HIPAA compliance testing', 'tags': ['healthcare', 'hipaa', 'pii', 'demo']},
        {'name': 'Financial PII Samples', 'description': 'Financial documents for PCI testing', 'tags': ['financial', 'pci', 'pii', 'demo']}
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for jar_config in pii_jars:
        try:
            jar_id = honey_jar_service.create_honey_jar(
                name=jar_config['name'],
                description=jar_config['description'],
                jar_type='public',
                tags=jar_config['tags']
            )
            if jar_id:
                created += 1
                current_app.logger.info(f"Created PII demo honey jar: {jar_config['name']} (ID: {jar_id})")
        except Exception as e:
            current_app.logger.error(f"Error creating PII honey jar {jar_config['name']}: {str(e)}")

    return created

def _create_sample_documents(scenario_type):
    """Create sample documents based on scenario using knowledge service API"""
    documents_created = 0

    try:
        # Get demo data from generators
        medical_gen = MedicalDemoGenerator()
        legal_gen = LegalDemoGenerator()
        financial_gen = FinancialDemoGenerator()

        # Number of documents based on scenario
        doc_counts = {
            'basic': {'medical': 2, 'legal': 2, 'financial': 1},
            'comprehensive': {'medical': 5, 'legal': 5, 'financial': 3},
            'security': {'medical': 3, 'legal': 3, 'financial': 2},
            'pii': {'medical': 4, 'legal': 2, 'financial': 2}
        }

        counts = doc_counts.get(scenario_type, doc_counts['basic'])

        # Create medical documents
        for i in range(counts['medical']):
            doc_content = random.choice([
                medical_gen.generate_patient_intake_form(),
                medical_gen.generate_lab_results(),
                medical_gen.generate_prescription()
            ])
            if _save_demo_document('Medical Records Demo', f'medical_sample_{i+1}.txt', doc_content, ['healthcare', 'phi', 'demo']):
                documents_created += 1

        # Create legal documents
        for i in range(counts['legal']):
            doc_content = random.choice([
                legal_gen.generate_case_file(),
                legal_gen.generate_contract()
            ])
            if _save_demo_document('Legal Documents Demo', f'legal_sample_{i+1}.txt', doc_content, ['legal', 'privileged', 'demo']):
                documents_created += 1

        # Create financial documents
        for i in range(counts['financial']):
            doc_content = financial_gen.generate_loan_application()
            if _save_demo_document('Financial Data Demo', f'financial_sample_{i+1}.txt', doc_content, ['financial', 'pci', 'demo']):
                documents_created += 1

    except Exception as e:
        current_app.logger.error(f"Error creating sample documents: {str(e)}")

    return documents_created

def _create_pii_documents():
    """Create specific PII testing documents"""
    documents_created = 0

    try:
        medical_gen = MedicalDemoGenerator()
        legal_gen = LegalDemoGenerator()
        financial_gen = FinancialDemoGenerator()

        # Create diverse PII samples with their tags
        pii_samples = [
            (medical_gen.generate_patient_intake_form(), ['healthcare', 'phi', 'pii', 'demo']),
            (medical_gen.generate_lab_results(), ['healthcare', 'lab', 'pii', 'demo']),
            (legal_gen.generate_case_file(), ['legal', 'privileged', 'pii', 'demo']),
            (financial_gen.generate_loan_application(), ['financial', 'pci', 'pii', 'demo'])
        ]

        for i, (sample, tags) in enumerate(pii_samples):
            if _save_demo_document('PII Detection Samples', f'pii_sample_{i+1}.txt', sample, tags):
                documents_created += 1

    except Exception as e:
        current_app.logger.error(f"Error creating PII documents: {str(e)}")

    return documents_created


def _save_demo_document(jar_name, filename, content, tags=None):
    """
    Save a demo document to a honey jar via knowledge service API.
    Uses the HoneyJarService to upload documents to the knowledge service.
    """
    try:
        import requests

        honey_jar_service = get_honey_jar_service()

        # First, we need to find the jar ID by name via the knowledge service
        # Query knowledge service for honey jars
        headers = {"X-API-Key": honey_jar_service.api_key}
        response = requests.get(
            f"{honey_jar_service.knowledge_url}/honey-jars",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            current_app.logger.warning(f"Could not list honey jars: {response.status_code}")
            return False

        jars = response.json()
        jar_id = None

        # Find the jar by name
        for jar in jars:
            if jar.get('name') == jar_name:
                jar_id = jar.get('id')
                break

        if not jar_id:
            current_app.logger.warning(f"Honey jar '{jar_name}' not found for document {filename}")
            return False

        # Upload the document content
        if tags is None:
            tags = ['demo']

        success = honey_jar_service.upload_text_content(
            jar_id=jar_id,
            filename=filename,
            content=content,
            tags=tags
        )

        if success:
            current_app.logger.info(f"Uploaded demo document: {filename} to {jar_name}")
            return True
        else:
            current_app.logger.warning(f"Failed to upload demo document: {filename}")
            return False

    except Exception as e:
        current_app.logger.error(f"Error saving demo document {filename}: {str(e)}")
        return False

def _create_sample_reports(scenario_type):
    """
    Create sample reports using the correct Report model structure.
    Reports are created with 'completed' status as demo placeholders.
    """
    reports_created = 0

    try:
        # Get admin user dynamically
        admin_id, admin_kratos_id, admin_email = get_admin_user()
        if not admin_kratos_id:
            current_app.logger.error("Cannot create reports: no admin user found")
            return 0

        # First, ensure we have a demo report template
        demo_template = ReportTemplate.query.filter_by(name='demo_report').first()
        if not demo_template:
            demo_template = ReportTemplate(
                id=str(uuid.uuid4()),
                name='demo_report',
                display_name='Demo Report',
                description='Template for demonstration reports',
                category='demo',
                generator_class='DemoReportGenerator',
                parameters={},
                template_config={},
                output_formats=['pdf'],
                is_active=True
            )
            db.session.add(demo_template)
            db.session.flush()

        report_configs = {
            'basic': [
                {'title': 'Basic PII Scan Report', 'description': 'Automated PII detection scan results'},
                {'title': 'Security Overview Report', 'description': 'Security posture summary'},
                {'title': 'Compliance Status Report', 'description': 'Current compliance status overview'}
            ],
            'comprehensive': [
                {'title': 'Comprehensive PII Audit', 'description': 'Full PII audit with detailed findings'},
                {'title': 'Security Risk Assessment', 'description': 'Enterprise security risk analysis'},
                {'title': 'HIPAA Compliance Report', 'description': 'HIPAA compliance verification results'},
                {'title': 'GDPR Compliance Report', 'description': 'GDPR compliance assessment'},
                {'title': 'Financial Audit Report', 'description': 'Financial data handling audit'}
            ],
            'security': [
                {'title': 'Security Incident Analysis', 'description': 'Analysis of security incidents'},
                {'title': 'Vulnerability Assessment Report', 'description': 'System vulnerability scan results'},
                {'title': 'SOC2 Compliance Report', 'description': 'SOC2 compliance verification'}
            ],
            'pii': [
                {'title': 'PII Detection Analysis', 'description': 'Detailed PII detection analysis'},
                {'title': 'Data Classification Report', 'description': 'Data classification and sensitivity report'}
            ]
        }

        configs = report_configs.get(scenario_type, report_configs['basic'])

        for config in configs:
            try:
                # Create report with correct model structure
                report = Report(
                    id=str(uuid.uuid4()),
                    template_id=demo_template.id,
                    user_id=admin_kratos_id,
                    title=config['title'],
                    description=config['description'],
                    status='completed',  # Demo reports show as completed
                    priority='normal',
                    progress_percentage=100,
                    output_format='pdf',
                    scrambling_enabled=True,
                    pii_detected=True if 'PII' in config['title'] else False,
                    risk_level='low',
                    generated_by=admin_kratos_id,
                    access_type='user-owned',
                    parameters={'demo_data': True, 'scenario': scenario_type},
                    result_summary={
                        'demo': True,
                        'generated_at': datetime.utcnow().isoformat(),
                        'scenario': scenario_type,
                        'findings_count': random.randint(5, 25),
                        'risk_items': random.randint(0, 10)
                    },
                    completed_at=datetime.utcnow()
                )

                db.session.add(report)
                reports_created += 1
                current_app.logger.info(f"Created demo report: {config['title']}")

            except Exception as e:
                current_app.logger.error(f"Error creating report {config['title']}: {str(e)}")

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error creating sample reports: {str(e)}")
        db.session.rollback()

    return reports_created

def _create_pii_samples(scenario_type):
    """Create PII pattern samples"""
    # This would create sample data for PII detection testing
    current_app.logger.info(f"Creating PII samples for {scenario_type} scenario")
    pass

def _create_demo_users():
    """Create demo test users"""
    users_created = 0
    
    try:
        demo_users = [
            {'email': 'demo.user1@sting.local', 'name': 'Demo User 1'},
            {'email': 'demo.user2@sting.local', 'name': 'Demo User 2'},
            {'email': 'demo.user3@sting.local', 'name': 'Demo User 3'}
        ]
        
        for user_config in demo_users:
            existing = User.query.filter_by(email=user_config['email']).first()
            if not existing:
                user = User(
                    email=user_config['email'],
                    kratos_user_id=f"demo-{random.randint(100000, 999999)}",
                    metadata={'demo_data': True, 'name': user_config['name']}
                )
                db.session.add(user)
                users_created += 1
        
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Error creating demo users: {str(e)}")
        db.session.rollback()
    
    return users_created

def _create_security_audit_data():
    """Create security audit trail data"""
    current_app.logger.info("Creating security audit data")
    # Would create audit log entries, security events, etc.
    pass

def _create_advanced_pii_patterns():
    """Create advanced PII pattern samples"""
    current_app.logger.info("Creating advanced PII patterns")
    # Would create complex PII detection test cases
    pass

def _create_custom_pii_rules():
    """Create custom PII detection rules"""
    current_app.logger.info("Creating custom PII rules")
    # Would create custom regex patterns and detection rules
    pass

def _create_demo_nectar_bots(scenario_type):
    """Create demo Nectar Bots based on scenario with proper admin ownership"""
    bots_created = 0

    try:
        # Get admin user dynamically
        admin_id, admin_kratos_id, admin_email = get_admin_user()
        if not admin_kratos_id:
            current_app.logger.error("Cannot create nectar bots: no admin user found")
            return 0

        # Get available honey jars via knowledge service
        import requests
        honey_jar_service = get_honey_jar_service()
        headers = {"X-API-Key": honey_jar_service.api_key}

        try:
            response = requests.get(
                f"{honey_jar_service.knowledge_url}/honey-jars",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                jars = response.json()
                jar_ids = [jar.get('id') for jar in jars[:3] if jar.get('id')]  # Use first 3 jars
            else:
                jar_ids = []
        except Exception as e:
            current_app.logger.warning(f"Could not fetch honey jars for bot config: {e}")
            jar_ids = []

        # Define bot configurations based on scenario
        if scenario_type == 'basic':
            bot_configs = [
                {
                    'name': 'Customer Support Bot',
                    'description': 'Handles general customer inquiries and provides basic support',
                    'system_prompt': 'You are a helpful customer support assistant. Provide clear, friendly responses to customer questions using the available knowledge base.',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ["urgent", "escalate", "supervisor", "manager", "complaint"]
                },
                {
                    'name': 'FAQ Assistant',
                    'description': 'Answers frequently asked questions about products and services',
                    'system_prompt': 'You are an FAQ assistant. Answer questions directly and concisely using the documentation. If unsure, suggest contacting support.',
                    'confidence_threshold': 0.8,
                    'handoff_keywords': ["technical", "billing", "urgent", "human"]
                },
                {
                    'name': 'Documentation Helper',
                    'description': 'Helps users navigate and understand documentation',
                    'system_prompt': 'You are a documentation assistant. Help users find relevant information in the knowledge base and explain complex topics clearly.',
                    'confidence_threshold': 0.6,
                    'handoff_keywords': ["confused", "don\'t understand", "explain more", "details"]
                }
            ]
        elif scenario_type == 'comprehensive':
            bot_configs = [
                {
                    'name': 'Enterprise Support Bot',
                    'description': 'Advanced support bot for enterprise customers with priority handling',
                    'system_prompt': 'You are an enterprise support specialist. Provide detailed, professional responses and escalate complex issues promptly.',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ["enterprise", "priority", "escalate", "urgent", "critical", "SLA"]
                },
                {
                    'name': 'Technical Documentation Bot',
                    'description': 'Specialized bot for technical documentation and developer support',
                    'system_prompt': 'You are a technical documentation assistant. Help developers find code examples, API references, and implementation guides.',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ["bug", "API", "integration", "code", "technical"]
                },
                {
                    'name': 'Security Incident Bot',
                    'description': 'Handles security-related inquiries and incident reporting',
                    'system_prompt': 'You are a security assistant. Handle security questions carefully and escalate any potential security incidents immediately.',
                    'confidence_threshold': 0.9,
                    'handoff_keywords': ["security", "breach", "incident", "vulnerability", "threat"]
                },
                {
                    'name': 'HR Assistant Bot',
                    'description': 'Provides HR information and handles employee inquiries',
                    'system_prompt': 'You are an HR assistant. Help with policy questions, benefits information, and general HR inquiries while maintaining confidentiality.',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ["personal", "confidential", "complaint", "harassment", "grievance"]
                },
                {
                    'name': 'Training Bot',
                    'description': 'Assists with training materials and educational content',
                    'system_prompt': 'You are a training assistant. Help users learn new concepts and navigate training materials effectively.',
                    'confidence_threshold': 0.6,
                    'handoff_keywords': ["confused", "help", "explain", "training"]
                }
            ]
        else:
            # Default to basic for other scenarios
            bot_configs = [
                {
                    'name': 'General Assistant Bot',
                    'description': 'General purpose assistant for various inquiries',
                    'system_prompt': 'You are a helpful assistant. Provide accurate information using available knowledge sources.',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ["help", "support", "human"]
                }
            ]

        # Create bots with proper admin ownership and demo metadata
        for config in bot_configs:
            try:
                # Check if bot already exists
                existing = NectarBot.query.filter_by(name=config['name']).first()
                if not existing:
                    bot = NectarBot(
                        name=config['name'],
                        description=config['description'],
                        owner_id=admin_kratos_id,  # Use actual admin user
                        owner_email=admin_email or 'admin@sting.local',
                        honey_jar_ids=jar_ids,
                        system_prompt=config['system_prompt'],
                        max_conversation_length=20,
                        confidence_threshold=config['confidence_threshold'],
                        rate_limit_per_hour=100,
                        rate_limit_per_day=1000,
                        status=BotStatus.ACTIVE.value,
                        is_public=True,
                        handoff_enabled=True,
                        handoff_keywords=config['handoff_keywords'],
                        handoff_confidence_threshold=0.6,
                        # Add demo_data flag for proper cleanup
                        metadata={'demo_data': True, 'scenario': scenario_type}
                    )
                    db.session.add(bot)
                    bots_created += 1
                    current_app.logger.info(f"Created demo nectar bot: {config['name']}")
            except Exception as e:
                current_app.logger.error(f"Error creating nectar bot {config['name']}: {str(e)}")

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error creating demo nectar bots: {str(e)}")
        db.session.rollback()

    return bots_created

def _create_demo_bot_usage(scenario_type):
    """
    Create demo bot usage data using bulk insertion for better performance.
    """
    try:
        # Get demo bots (those with 'Demo' in description or standard demo names)
        demo_bots = NectarBot.query.filter(
            NectarBot.description.ilike('%demo%') |
            NectarBot.name.in_([
                'Customer Support Bot', 'FAQ Assistant', 'Documentation Helper',
                'Enterprise Support Bot', 'Technical Documentation Bot',
                'Security Incident Bot', 'HR Assistant Bot', 'Training Bot',
                'General Assistant Bot'
            ])
        ).all()

        if not demo_bots:
            current_app.logger.warning("No demo bots found for usage data generation")
            return

        usage_count = 50 if scenario_type == 'basic' else 150
        handoff_count = 5 if scenario_type == 'basic' else 15

        # Collect all usage records for bulk insert
        usage_records = []
        handoff_records = []

        for bot in demo_bots:
            # Generate usage records
            for i in range(usage_count):
                created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                usage_records.append({
                    'bot_id': bot.id,
                    'conversation_id': f"demo_conv_{bot.id}_{random.randint(10000, 99999)}",
                    'message_id': f"demo_msg_{random.randint(10000, 99999)}",
                    'user_id': f"demo_user_{random.randint(100, 999)}",
                    'user_ip': f"192.168.1.{random.randint(1, 254)}",
                    'user_agent': "Demo User Agent",
                    'user_message': f"Demo user question {i+1}",
                    'bot_response': f"Demo bot response {i+1}",
                    'confidence_score': random.uniform(0.5, 0.95),
                    'response_time_ms': random.randint(200, 2000),
                    'honey_jars_queried': bot.honey_jar_ids[:2] if bot.honey_jar_ids else [],
                    'knowledge_matches': random.randint(1, 5),
                    'rate_limit_hit': False,
                    'created_at': created_at
                })

            # Generate handoff records
            for i in range(handoff_count):
                created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                is_resolved = random.random() > 0.3
                resolved_at = created_at + timedelta(hours=random.randint(1, 24)) if is_resolved else None

                handoff_records.append({
                    'bot_id': bot.id,
                    'conversation_id': f"demo_handoff_{bot.id}_{random.randint(10000, 99999)}",
                    'user_id': f"demo_user_{random.randint(100, 999)}",
                    'user_info': {'name': f'Demo User {i+1}', 'email': f'user{i+1}@demo.local', 'demo_data': True},
                    'reason': 'low_confidence' if random.random() > 0.5 else 'keyword_detected',
                    'urgency': random.choice([HandoffUrgency.LOW.value, HandoffUrgency.MEDIUM.value, HandoffUrgency.HIGH.value]),
                    'status': HandoffStatus.RESOLVED.value if is_resolved else HandoffStatus.PENDING.value,
                    'conversation_history': [{'user': f'Demo question {i+1}', 'bot': f'Demo response {i+1}'}],
                    'honey_jars_used': bot.honey_jar_ids[:1] if bot.honey_jar_ids else [],
                    'trigger_message': f"Demo trigger message {i+1}",
                    'bot_response': f"Demo bot response {i+1}",
                    'confidence_score': random.uniform(0.3, 0.6),
                    'created_at': created_at,
                    'resolved_at': resolved_at,
                    'resolution_notes': f"Demo resolution notes {i+1}" if is_resolved else None
                })

        # Bulk insert usage records
        if usage_records:
            db.session.bulk_insert_mappings(NectarBotUsage, usage_records)
            current_app.logger.info(f"Bulk inserted {len(usage_records)} usage records")

        # Bulk insert handoff records
        if handoff_records:
            db.session.bulk_insert_mappings(NectarBotHandoff, handoff_records)
            current_app.logger.info(f"Bulk inserted {len(handoff_records)} handoff records")

        # Update bot statistics
        for bot in demo_bots:
            try:
                bot.update_stats()
            except Exception as e:
                current_app.logger.warning(f"Could not update stats for bot {bot.name}: {e}")

        db.session.commit()
        current_app.logger.info(f"Created demo bot usage data for {scenario_type} scenario")

    except Exception as e:
        current_app.logger.error(f"Error creating demo bot usage: {str(e)}")
        db.session.rollback()

def _finalize_demo_setup(scenario_type):
    """Finalize demo data setup"""
    current_app.logger.info(f"Finalizing {scenario_type} demo setup")
    # Would perform any cleanup, indexing, or finalization tasks
    pass

def _create_bot_knowledge_honey_jars():
    """Create honey jars optimized for bot knowledge bases via knowledge service API"""
    bot_jars = [
        {'name': 'Customer Support Knowledge Base', 'description': 'FAQs, troubleshooting guides, and customer service procedures', 'tags': ['support', 'faq', 'demo', 'bot-knowledge']},
        {'name': 'Product Documentation Hub', 'description': 'User manuals, feature guides, and product specifications', 'tags': ['documentation', 'product', 'demo', 'bot-knowledge']},
        {'name': 'Technical Support Library', 'description': 'API docs, integration guides, and technical troubleshooting', 'tags': ['technical', 'api', 'demo', 'bot-knowledge']},
        {'name': 'Company Policy Center', 'description': 'HR policies, procedures, and employee handbook information', 'tags': ['policies', 'hr', 'demo', 'bot-knowledge']},
        {'name': 'Training Materials Archive', 'description': 'Training guides, tutorials, and educational content', 'tags': ['training', 'education', 'demo', 'bot-knowledge']}
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for jar_config in bot_jars:
        try:
            jar_id = honey_jar_service.create_honey_jar(
                name=jar_config['name'],
                description=jar_config['description'],
                jar_type='public',
                tags=jar_config['tags']
            )
            if jar_id:
                created += 1
                current_app.logger.info(f"Created bot knowledge honey jar: {jar_config['name']} (ID: {jar_id})")
        except Exception as e:
            current_app.logger.error(f"Error creating bot knowledge honey jar {jar_config['name']}: {str(e)}")

    return created

def _create_bot_training_documents():
    """Create documents specifically for training nectar bots via knowledge service API"""
    documents_created = 0

    try:
        # Bot training content with tags
        training_docs = [
            {
                'jar': 'Customer Support Knowledge Base',
                'filename': 'customer_service_faqs.txt',
                'tags': ['support', 'faq', 'demo', 'bot-training'],
                'content': '''CUSTOMER SERVICE FREQUENTLY ASKED QUESTIONS

Q: How do I reset my password?
A: Click "Forgot Password" on the login page and follow the email instructions.

Q: What are your business hours?
A: We're available Monday-Friday 9AM-6PM EST, with emergency support 24/7.

Q: How do I contact technical support?
A: Use the chat widget or email support@company.com for technical issues.

Q: What is your refund policy?
A: Full refunds available within 30 days of purchase with original receipt.

Q: How do I update my billing information?
A: Log into your account and navigate to Settings > Billing to update payment methods.

ESCALATION KEYWORDS: refund, billing issue, technical problem, urgent, supervisor, manager
'''
            },
            {
                'jar': 'Product Documentation Hub',
                'filename': 'getting_started_guide.txt',
                'tags': ['documentation', 'getting-started', 'demo', 'bot-training'],
                'content': '''GETTING STARTED GUIDE

Welcome to our platform! This guide will help you get started quickly.

INITIAL SETUP:
1. Create your account at signup.company.com
2. Verify your email address
3. Complete your profile information
4. Choose your subscription plan

BASIC FEATURES:
- Dashboard: Overview of your account and recent activity
- Settings: Customize your preferences and integrations
- Reports: Generate analytics and performance metrics
- Support: Access help articles and contact support

COMMON TASKS:
- Upload files: Drag and drop or use the upload button
- Share content: Use the share button and set permissions
- Collaborate: Invite team members and assign roles
- Export data: Use the export function in Reports section

For technical assistance, contact our support team.
'''
            },
            {
                'jar': 'Technical Support Library',
                'filename': 'api_documentation.txt',
                'tags': ['technical', 'api', 'demo', 'bot-training'],
                'content': '''API DOCUMENTATION

AUTHENTICATION:
All API requests require an API key in the header:
X-API-Key: your_api_key_here

ENDPOINTS:
GET /api/users - List all users
POST /api/users - Create new user
GET /api/data - Retrieve data
POST /api/data - Upload data

RATE LIMITS:
- 1000 requests per hour for standard plans
- 5000 requests per hour for premium plans

ERROR CODES:
- 401: Invalid API key
- 403: Insufficient permissions
- 429: Rate limit exceeded
- 500: Server error

TROUBLESHOOTING:
- Check API key validity
- Verify request format
- Review rate limit status
- Contact support for 500 errors
'''
            },
            {
                'jar': 'Company Policy Center',
                'filename': 'employee_handbook.txt',
                'tags': ['policies', 'hr', 'demo', 'bot-training'],
                'content': '''EMPLOYEE HANDBOOK EXCERPTS

WORK SCHEDULE:
Standard business hours are 9:00 AM to 5:00 PM, Monday through Friday.
Flexible work arrangements available with manager approval.

TIME OFF POLICY:
- Annual leave: 15 days for new employees, increasing with tenure
- Sick leave: 10 days per year
- Personal days: 3 days per year
- Submit requests through HR portal at least 2 weeks in advance

BENEFITS:
- Health insurance: 80% company coverage
- Retirement plan: 4% company match
- Professional development: $1000 annual budget
- Gym membership reimbursement available

IT POLICIES:
- Use strong passwords (minimum 8 characters)
- Keep software updated
- Report security incidents immediately
- Personal device usage governed by BYOD policy

For HR questions, contact hr@company.com or ext. 1234
'''
            }
        ]

        for doc_config in training_docs:
            try:
                if _save_demo_document(doc_config['jar'], doc_config['filename'], doc_config['content'], doc_config['tags']):
                    documents_created += 1
            except Exception as e:
                current_app.logger.error(f"Error creating training document {doc_config['filename']}: {str(e)}")

    except Exception as e:
        current_app.logger.error(f"Error creating bot training documents: {str(e)}")

    return documents_created

def _create_demo_bot_conversations():
    """Create realistic conversation examples for demo bots"""
    conversations_created = 0

    try:
        # This would create sample conversation logs
        # For demo purposes, we'll simulate this by creating usage records
        current_app.logger.info("Creating demo bot conversation examples")
        conversations_created = 25  # Simulated count

    except Exception as e:
        current_app.logger.error(f"Error creating demo bot conversations: {str(e)}")

    return conversations_created

def _create_demo_bot_handoffs():
    """Create demo handoff scenarios for nectar bots"""
    handoffs_created = 0

    try:
        # Get all demo bots
        demo_bots = NectarBot.query.filter_by(is_public=True).all()

        # Sample handoff scenarios
        handoff_scenarios = [
            {
                'reason': 'complex_billing_issue',
                'urgency': HandoffUrgency.HIGH.value,
                'trigger_message': 'I need to dispute a charge on my account immediately',
                'conversation': [
                    {'user': 'I need to dispute a charge on my account immediately', 'bot': 'I understand you need help with billing. Let me connect you with our billing specialist who can assist with account disputes.'}
                ]
            },
            {
                'reason': 'technical_escalation',
                'urgency': HandoffUrgency.MEDIUM.value,
                'trigger_message': 'The API is returning 500 errors for all my requests',
                'conversation': [
                    {'user': 'The API is returning 500 errors for all my requests', 'bot': 'This sounds like a technical issue that requires immediate attention. Let me escalate this to our technical team.'}
                ]
            },
            {
                'reason': 'security_concern',
                'urgency': HandoffUrgency.HIGH.value,
                'trigger_message': 'I think my account has been compromised',
                'conversation': [
                    {'user': 'I think my account has been compromised', 'bot': 'Security concerns require immediate attention. I\'m connecting you with our security team right away.'}
                ]
            },
            {
                'reason': 'feature_request',
                'urgency': HandoffUrgency.LOW.value,
                'trigger_message': 'Can you add a new integration with Salesforce?',
                'conversation': [
                    {'user': 'Can you add a new integration with Salesforce?', 'bot': 'That\'s a great feature suggestion! Let me connect you with our product team to discuss this integration request.'}
                ]
            }
        ]

        for bot in demo_bots[:2]:  # Create handoffs for first 2 bots
            for i, scenario in enumerate(handoff_scenarios):
                try:
                    handoff = NectarBotHandoff(
                        bot_id=bot.id,
                        conversation_id=f"handoff_demo_{bot.id}_{i}",
                        user_id=f"demo_user_{i+100}",
                        user_info={'name': f'Demo User {i+1}', 'email': f'demo{i+1}@example.com'},
                        reason=scenario['reason'],
                        urgency=scenario['urgency'],
                        status=HandoffStatus.RESOLVED.value if i % 2 == 0 else HandoffStatus.PENDING.value,
                        conversation_history=scenario['conversation'],
                        honey_jars_used=bot.honey_jar_ids[:1] if bot.honey_jar_ids else [],
                        trigger_message=scenario['trigger_message'],
                        bot_response=scenario['conversation'][0]['bot'],
                        confidence_score=random.uniform(0.3, 0.6),
                        created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                    )

                    if handoff.status == HandoffStatus.RESOLVED.value:
                        handoff.resolved_at = handoff.created_at + timedelta(hours=random.randint(1, 12))
                        handoff.resolution_notes = f"Demo resolution: {scenario['reason']} handled successfully"
                        handoff.calculate_resolution_time()

                    db.session.add(handoff)
                    handoffs_created += 1

                except Exception as e:
                    current_app.logger.error(f"Error creating demo handoff {i}: {str(e)}")

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error creating demo bot handoffs: {str(e)}")
        db.session.rollback()

    return handoffs_created

@demo_bp.route('/clear-demo-data', methods=['DELETE'])
@require_admin
@require_auth_method(['webauthn', 'totp'])
def clear_demo_data():
    """
    Clear all demo data from the system.
    Uses proper JSONB filtering and knowledge service API for honey jars.
    """
    try:
        import requests
        current_app.logger.info("Starting demo data cleanup")

        cleared_counts = {
            'documents': 0,
            'honeyJars': 0,
            'reports': 0,
            'users': 0,
            'nectarBots': 0,
            'botUsage': 0,
            'botHandoffs': 0
        }

        # Clear demo reports using proper JSONB filter
        try:
            demo_reports = Report.query.filter(
                Report.parameters.op('@>')(cast({'demo_data': True}, JSONB))
            ).all()

            for report in demo_reports:
                db.session.delete(report)
                cleared_counts['reports'] += 1
        except Exception as e:
            current_app.logger.error(f"Error clearing demo reports: {str(e)}")

        # Clear demo report template
        try:
            demo_template = ReportTemplate.query.filter_by(name='demo_report').first()
            if demo_template:
                db.session.delete(demo_template)
        except Exception as e:
            current_app.logger.warning(f"Could not delete demo template: {e}")

        # Clear demo users (be careful with this)
        try:
            demo_users = User.query.filter(
                User.metadata.op('@>')(cast({'demo_data': True}, JSONB))
            ).all()

            for user in demo_users:
                db.session.delete(user)
                cleared_counts['users'] += 1
        except Exception as e:
            current_app.logger.error(f"Error clearing demo users: {str(e)}")

        # Clear demo nectar bots and related data
        # First, delete usage records for demo conversations
        try:
            demo_usage = NectarBotUsage.query.filter(
                NectarBotUsage.conversation_id.like('demo_%')
            ).all()
            for usage in demo_usage:
                db.session.delete(usage)
                cleared_counts['botUsage'] += 1
        except Exception as e:
            current_app.logger.error(f"Error clearing demo bot usage: {str(e)}")

        # Delete demo handoffs
        try:
            demo_handoffs = NectarBotHandoff.query.filter(
                NectarBotHandoff.conversation_id.like('demo_%')
            ).all()
            for handoff in demo_handoffs:
                db.session.delete(handoff)
                cleared_counts['botHandoffs'] += 1
        except Exception as e:
            current_app.logger.error(f"Error clearing demo handoffs: {str(e)}")

        # Delete demo bots by known names
        demo_bot_names = [
            'Customer Support Bot', 'FAQ Assistant', 'Documentation Helper',
            'Enterprise Support Bot', 'Technical Documentation Bot',
            'Security Incident Bot', 'HR Assistant Bot', 'Training Bot',
            'General Assistant Bot'
        ]

        try:
            demo_bots = NectarBot.query.filter(
                NectarBot.name.in_(demo_bot_names) |
                NectarBot.description.ilike('%demo%')
            ).all()

            for bot in demo_bots:
                db.session.delete(bot)
                cleared_counts['nectarBots'] += 1
        except Exception as e:
            current_app.logger.error(f"Error clearing demo bots: {str(e)}")

        # Clear demo honey jars via knowledge service API
        try:
            honey_jar_service = get_honey_jar_service()
            headers = {"X-API-Key": honey_jar_service.api_key}

            response = requests.get(
                f"{honey_jar_service.knowledge_url}/honey-jars",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                jars = response.json()
                for jar in jars:
                    # Check if jar has 'demo' tag or demo name pattern
                    tags = jar.get('tags', [])
                    name = jar.get('name', '')

                    if 'demo' in tags or 'Demo' in name:
                        jar_id = jar.get('id')
                        if jar_id:
                            delete_response = requests.delete(
                                f"{honey_jar_service.knowledge_url}/honey-jars/{jar_id}",
                                headers=headers,
                                timeout=10
                            )
                            if delete_response.status_code in [200, 204]:
                                cleared_counts['honeyJars'] += 1
                                cleared_counts['documents'] += jar.get('document_count', 0)
                                current_app.logger.info(f"Deleted demo honey jar: {name}")
                            else:
                                current_app.logger.warning(f"Failed to delete jar {name}: {delete_response.status_code}")
        except Exception as e:
            current_app.logger.error(f"Error clearing demo honey jars: {str(e)}")

        # Commit all database deletions
        db.session.commit()

        current_app.logger.info(f"Demo data cleanup completed: {cleared_counts}")

        return jsonify({
            'success': True,
            'message': 'All demo data cleared successfully',
            'cleared': cleared_counts
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Demo data cleanup error: {str(e)}")
        return jsonify({
            'error': 'Failed to clear demo data',
            'details': str(e)
        }), 500

@demo_bp.route('/demo-status', methods=['GET'])
@require_admin
def get_demo_status():
    """
    Get current demo data status and counts.
    Uses proper JSONB filtering and knowledge service API.
    """
    try:
        import requests
        counts = {
            'documents': 0,
            'honeyJars': 0,
            'reports': 0,
            'users': 0,
            'nectarBots': 0,
            'botUsage': 0,
            'botHandoffs': 0
        }

        # Count demo reports using proper JSONB filter
        try:
            counts['reports'] = Report.query.filter(
                Report.parameters.op('@>')(cast({'demo_data': True}, JSONB))
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Could not count demo reports: {e}")

        # Count demo users
        try:
            counts['users'] = User.query.filter(
                User.metadata.op('@>')(cast({'demo_data': True}, JSONB))
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Could not count demo users: {e}")

        # Count demo nectar bots
        demo_bot_names = [
            'Customer Support Bot', 'FAQ Assistant', 'Documentation Helper',
            'Enterprise Support Bot', 'Technical Documentation Bot',
            'Security Incident Bot', 'HR Assistant Bot', 'Training Bot',
            'General Assistant Bot'
        ]
        try:
            counts['nectarBots'] = NectarBot.query.filter(
                NectarBot.name.in_(demo_bot_names) |
                NectarBot.description.ilike('%demo%')
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Could not count demo bots: {e}")

        # Count demo bot usage
        try:
            counts['botUsage'] = NectarBotUsage.query.filter(
                NectarBotUsage.conversation_id.like('demo_%')
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Could not count demo bot usage: {e}")

        # Count demo handoffs
        try:
            counts['botHandoffs'] = NectarBotHandoff.query.filter(
                NectarBotHandoff.conversation_id.like('demo_%')
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Could not count demo handoffs: {e}")

        # Count demo honey jars via knowledge service
        try:
            honey_jar_service = get_honey_jar_service()
            headers = {"X-API-Key": honey_jar_service.api_key}

            response = requests.get(
                f"{honey_jar_service.knowledge_url}/honey-jars",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                jars = response.json()
                for jar in jars:
                    tags = jar.get('tags', [])
                    name = jar.get('name', '')
                    if 'demo' in tags or 'Demo' in name:
                        counts['honeyJars'] += 1
                        counts['documents'] += jar.get('document_count', 0)
        except Exception as e:
            current_app.logger.warning(f"Could not count demo honey jars: {e}")

        has_demo_data = any(counts.values())

        return jsonify({
            'success': True,
            'demo_data': counts,
            'has_demo_data': has_demo_data
        })

    except Exception as e:
        current_app.logger.error(f"Demo status error: {str(e)}")
        return jsonify({
            'error': 'Failed to get demo status',
            'details': str(e)
        }), 500