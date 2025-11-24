#!/usr/bin/env python3
"""
Demo Data Management Routes
Provides endpoints for generating and managing demo data for STING platform
"""

import os
import random
import tempfile
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
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
from app.services.report_service import get_report_service
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
        
        # Get current user ID if available
        current_user_id = None
        if hasattr(g, 'user') and g.user:
            current_user_id = g.user.kratos_id
            
        # Define what each step does based on scenario
        if scenario == 'basic':
            result['generated'] = _generate_basic_demo_step(step, current_user_id)
        elif scenario == 'comprehensive':
            result['generated'] = _generate_comprehensive_demo_step(step, current_user_id)
        elif scenario == 'security-focused':
            result['generated'] = _generate_security_demo_step(step, current_user_id)
        elif scenario == 'pii-scrubbing':
            result['generated'] = _generate_pii_demo_step(step, current_user_id)
        elif scenario == 'nectar-bot':
            result['generated'] = _generate_nectar_bot_demo_step(step)
        elif scenario == 'enterprise-showcase':
            # Enterprise showcase uses comprehensive with enterprise focus
            result['generated'] = _generate_comprehensive_demo_step(step, current_user_id)
        elif scenario == 'healthcare':
            # Healthcare demo uses PII demo with medical focus
            result['generated'] = _generate_pii_demo_step(step, current_user_id)
        elif scenario == 'legal-financial':
            # Legal-financial uses basic with legal/financial focus
            result['generated'] = _generate_basic_demo_step(step, current_user_id)
        else:
            return jsonify({'error': f'Invalid scenario: {scenario}'}), 400
        
        result['message'] = f"Step {step}/{total_steps} completed for {scenario} scenario"
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Demo data generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate demo data',
            'details': str(e)
        }), 500

def _generate_basic_demo_step(step, user_id=None):
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
            reports_created = _create_sample_reports('basic', user_id)
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

def _generate_comprehensive_demo_step(step, user_id=None):
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
            reports_created = _create_sample_reports('comprehensive', user_id)
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

def _generate_security_demo_step(step, user_id=None):
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
            reports_created = _create_sample_reports('security', user_id)
            generated['reports'] = reports_created
            
        elif step == 4:  # Security audit trails
            _create_security_audit_data()
            
        elif step == 5:  # Finalize security setup
            _finalize_demo_setup('security')
            
    except Exception as e:
        current_app.logger.error(f"Error in security demo step {step}: {str(e)}")
        
    return generated

def _generate_pii_demo_step(step, user_id=None):
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
            reports_created = _create_sample_reports('pii', user_id)
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
    """Create comprehensive set of 35 honey jars across departments"""
    departments = [
        ('Legal', ['Contracts', 'Litigation', 'Compliance', 'IP', 'Corporate']),
        ('HR', ['Benefits', 'Recruiting', 'Employee Relations', 'Training', 'Payroll']),
        ('Finance', ['Audits', 'Tax', 'Budgeting', 'Invoices', 'Reports']),
        ('IT', ['Architecture', 'Security', 'Operations', 'Support', 'Assets']),
        ('Sales', ['Contracts', 'Proposals', 'Leads', 'Enablement', 'Territories']),
        ('Marketing', ['Assets', 'Campaigns', 'Research', 'Brand', 'Events']),
        ('R&D', ['Specs', 'Patents', 'Prototypes', 'Research', 'Roadmap'])
    ]

    created = 0
    honey_jar_service = get_honey_jar_service()

    for dept, categories in departments:
        for category in categories:
            name = f"{dept} - {category} Archive"
            description = f"Comprehensive {category.lower()} documentation for {dept} department"
            tags = [dept.lower(), category.lower(), 'demo', 'comprehensive']
            
            try:
                jar_id = honey_jar_service.create_honey_jar(
                    name=name,
                    description=description,
                    jar_type='public',
                    tags=tags
                )
                if jar_id:
                    created += 1
                    current_app.logger.info(f"Created comprehensive honey jar: {name} (ID: {jar_id})")
            except Exception as e:
                current_app.logger.error(f"Error creating honey jar {name}: {str(e)}")

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
        # Get demo data generators
        medical_gen = MedicalDemoGenerator()
        legal_gen = LegalDemoGenerator()
        financial_gen = FinancialDemoGenerator()

        # Define document distribution
        if scenario_type == 'comprehensive':
            # Target: 225 documents
            targets = [
                ('HR', 'Benefits', medical_gen.generate_patient_intake_form, 45, ['hr', 'pii', 'demo']),
                ('Legal', 'Contracts', legal_gen.generate_contract, 45, ['legal', 'privileged', 'demo']),
                ('Finance', 'Invoices', financial_gen.generate_loan_application, 45, ['financial', 'pci', 'demo']),
                ('IT', 'Security', legal_gen.generate_case_file, 45, ['technical', 'security', 'demo']), # Using case file as placeholder for incident report
                ('Sales', 'Proposals', legal_gen.generate_contract, 45, ['sales', 'commercial', 'demo'])
            ]
        else:
            # Basic/other scenarios
            doc_counts = {
                'basic': {'medical': 2, 'legal': 2, 'financial': 1},
                'security': {'medical': 3, 'legal': 3, 'financial': 2},
                'pii': {'medical': 4, 'legal': 2, 'financial': 2}
            }
            counts = doc_counts.get(scenario_type, doc_counts['basic'])
            targets = [
                ('Medical Records Demo', None, medical_gen.generate_patient_intake_form, counts.get('medical', 0), ['healthcare', 'phi', 'demo']),
                ('Legal Documents Demo', None, legal_gen.generate_contract, counts.get('legal', 0), ['legal', 'privileged', 'demo']),
                ('Financial Data Demo', None, financial_gen.generate_loan_application, counts.get('financial', 0), ['financial', 'pci', 'demo'])
            ]

        for target in targets:
            jar_prefix, category, generator_func, count, tags = target
            
            for i in range(count):
                try:
                    # Construct jar name based on scenario
                    if scenario_type == 'comprehensive':
                        jar_name = f"{jar_prefix} - {category} Archive"
                    else:
                        jar_name = jar_prefix

                    doc_content = generator_func()
                    filename = f"{tags[0]}_doc_{i+1}_{uuid.uuid4().hex[:6]}.txt"
                    
                    if _save_demo_document(jar_name, filename, doc_content, tags):
                        documents_created += 1
                except Exception as e:
                    current_app.logger.error(f"Error creating document {i} for {jar_prefix}: {e}")

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
            f"{honey_jar_service.knowledge_url}/honey-jars?limit=1000",
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

def _create_sample_reports(scenario_type, target_user_id=None):
    """
    Create sample reports using the correct Report model structure.
    Reports are created with 'completed' status as demo placeholders.
    """
    reports_created = 0

    try:
        # Use provided user ID or fallback to admin
        if target_user_id:
            report_owner_id = target_user_id
        else:
            # Get admin user dynamically
            admin_id, admin_kratos_id, admin_email = get_admin_user()
            if not admin_kratos_id:
                current_app.logger.error("Cannot create reports: no admin user found")
                return 0
            report_owner_id = admin_kratos_id

        # First, ensure we have a demo report template
        demo_template = ReportTemplate.query.filter_by(name='demo_report').first()
        if not demo_template:
            demo_template = ReportTemplate(
                id=str(uuid.uuid4()),
                name='demo_report',
                display_name='Demo Report',
                description='Template for demonstration reports',
                category='demo',
                generator_class='DocumentProcessingReportGenerator',
                parameters={'demo_scenario': 'basic'},
                template_config={},
                output_formats=['pdf'],
                is_active=True
            )
            db.session.add(demo_template)
            db.session.flush()
        else:
            # Update existing template to use correct generator
            demo_template.generator_class = 'DocumentProcessingReportGenerator'
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
        current_app.logger.info(f"Creating reports for scenario: {scenario_type}, base configs: {len(configs)}")

        # For comprehensive scenario, expand the list to reach ~25 reports
        # ALL reports are queued for REAL processing (stress test)
        if scenario_type == 'comprehensive':
            base_configs = configs[:]
            configs = []

            # Generate 5 variations for each of the 5 base types = 25 reports
            # All reports queued for real processing to stress test the system
            for i in range(5):
                for base in base_configs:
                    new_config = base.copy()
                    month = (datetime.now() - timedelta(days=30*i)).strftime("%B")
                    new_config['title'] = f"{base['title']} - {month}"
                    new_config['status'] = 'queued'  # All queued for real processing
                    configs.append(new_config)

            current_app.logger.info(f"Expanded comprehensive scenario to {len(configs)} report configs (ALL queued for processing)")

        current_app.logger.info(f"Creating {len(configs)} demo reports for {scenario_type} scenario")
        for config in configs:
            try:
                # Create report with correct model structure
                report = Report(
                    id=str(uuid.uuid4()),
                    template_id=demo_template.id,
                    user_id=report_owner_id,
                    title=config['title'],
                    description=config['description'],
                    status='queued',  # Always queued for real processing
                    priority='normal',
                    progress_percentage=0,
                    output_format='pdf',
                    scrambling_enabled=True,
                    pii_detected=True if 'PII' in config['title'] else False,
                    risk_level='low',
                    generated_by=report_owner_id,
                    access_type='user-owned',
                    parameters={'demo_scenario': scenario_type, 'demo_data': True},
                    created_at=datetime.utcnow(),
                    completed_at=None
                )

                db.session.add(report)
                db.session.commit()  # Commit to ensure report is visible to queue service

                # Queue ALL reports for real processing
                try:
                    report_service = get_report_service()
                    report_service.queue_report(report.id)
                    current_app.logger.info(f"Queued demo report for processing: {config['title']} ({report.id})")
                except Exception as queue_error:
                    current_app.logger.error(f"Failed to queue report {report.id}: {queue_error}")
                
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
            # 15 Bots across departments with rich, distinct identities
            bot_configs = [
                # Support Team
                {
                    'name': 'Support - Tier 1',
                    'description': 'General customer inquiries and first-line support',
                    'system_prompt': '''You are Alex, a friendly Tier 1 Customer Support specialist. Your role is to help customers with common questions about accounts, billing, and basic product usage.

PERSONALITY: Warm, patient, and helpful. Use simple language and avoid technical jargon.

YOU CAN HELP WITH:
- Account access and password resets
- Billing questions and invoice copies
- Basic product features and how-to questions
- Order status and shipping inquiries
- Updating contact information

ALWAYS:
- Greet customers warmly and thank them for reaching out
- Ask clarifying questions before providing solutions
- Provide step-by-step instructions when explaining processes
- Offer to escalate complex issues to Tier 2 support

NEVER:
- Make promises about refunds or credits without approval
- Share internal policies or procedures
- Guess at technical solutions outside your knowledge base''',
                    'confidence_threshold': 0.8,
                    'handoff_keywords': ['escalate', 'supervisor', 'manager', 'refund', 'cancel subscription']
                },
                {
                    'name': 'Support - Tier 2',
                    'description': 'Technical troubleshooting and advanced support',
                    'system_prompt': '''You are Jordan, a Tier 2 Technical Support Engineer. You handle escalated issues that require deeper technical knowledge and problem-solving skills.

PERSONALITY: Methodical, technically precise, and solution-oriented. Comfortable with technical terminology.

YOU CAN HELP WITH:
- Software bugs and error troubleshooting
- Integration and API issues
- Performance optimization
- Configuration and setup problems
- Data migration assistance

TROUBLESHOOTING APPROACH:
1. Gather system information (version, OS, browser)
2. Reproduce the issue when possible
3. Check known issues database
4. Provide workarounds while investigating root cause
5. Document findings for engineering if needed

ESCALATE TO ENGINEERING WHEN:
- Bug is confirmed and reproducible
- Security vulnerability suspected
- Data corruption or loss reported
- Issue affects multiple customers''',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ['engineering', 'developer', 'bug report', 'security issue', 'data loss']
                },
                {
                    'name': 'Support - Enterprise',
                    'description': 'VIP support for enterprise customers with SLA commitments',
                    'system_prompt': '''You are Morgan, a dedicated Enterprise Account Support Manager. You provide white-glove service to our most valued enterprise customers.

PERSONALITY: Professional, proactive, and executive-level communication. Treat every interaction as high-priority.

ENTERPRISE SUPPORT INCLUDES:
- Priority response for all technical issues
- Direct escalation paths to engineering
- Quarterly business reviews coordination
- Custom configuration assistance
- Dedicated Slack/Teams channel support

SLA COMMITMENTS:
- Critical issues: 1-hour response, 4-hour resolution target
- High priority: 4-hour response, 24-hour resolution target
- Standard: 8-hour response, 72-hour resolution target

ALWAYS:
- Address contacts by name and company
- Reference their account history and previous interactions
- Proactively communicate status updates
- Loop in their Customer Success Manager for strategic issues

IMMEDIATE ESCALATION TRIGGERS:
- Production system down
- Data security concerns
- Executive-level complaints
- SLA breach risk''',
                    'confidence_threshold': 0.9,
                    'handoff_keywords': ['account manager', 'executive', 'SLA', 'production down', 'urgent']
                },

                # Sales Team
                {
                    'name': 'Sales - North America',
                    'description': 'US and Canada sales inquiries and qualification',
                    'system_prompt': '''You are Sam, a Sales Development Representative covering the US and Canada region. You help qualify leads and connect prospects with the right sales resources.

PERSONALITY: Enthusiastic, consultative, and value-focused. Listen first, pitch second.

YOUR ROLE:
- Answer product and pricing questions
- Qualify leads using BANT (Budget, Authority, Need, Timeline)
- Schedule demos with Account Executives
- Share relevant case studies and resources

QUALIFICATION QUESTIONS TO ASK:
- What challenges are you trying to solve?
- How are you handling this today?
- Who else is involved in this decision?
- What's your timeline for implementation?
- Do you have budget allocated for this?

PRICING GUIDANCE:
- Starter: $29/user/month (up to 10 users)
- Professional: $79/user/month (up to 100 users)
- Enterprise: Custom pricing (100+ users, dedicated support)
- All plans include 14-day free trial

HAND OFF TO ACCOUNT EXECUTIVE WHEN:
- Prospect is qualified (meets BANT criteria)
- Deal size > $10K ARR
- Request for custom demo or POC
- Enterprise-level requirements''',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ['quote', 'proposal', 'contract', 'negotiate', 'discount', 'enterprise pricing']
                },
                {
                    'name': 'Sales - EMEA',
                    'description': 'Europe, Middle East, and Africa sales inquiries',
                    'system_prompt': '''You are Elena, a Sales Development Representative for the EMEA region. You help European prospects understand our solutions and connect with local Account Executives.

PERSONALITY: Professional, culturally aware, and relationship-focused. Respect different business customs.

REGIONAL CONSIDERATIONS:
- GDPR compliance is standard in all our offerings
- EU data residency options available
- Pricing in EUR, GBP, or USD
- Support available in English, German, French, Spanish
- Local invoicing and VAT handling

OFFICE HOURS: 8:00 - 18:00 CET (we cover UK, EU, and Middle East timezones)

COMMON QUESTIONS:
- Data residency: EU-hosted option available (Frankfurt data center)
- GDPR: Full compliance, DPA available upon request
- Languages: Platform supports 12 languages
- Payment: SEPA, wire transfer, credit card accepted

HAND OFF TO LOCAL AE WHEN:
- Qualified opportunity identified
- Request for localized demo
- Contract negotiation stage
- Public sector or regulated industry''',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ['quote', 'proposal', 'GDPR', 'data residency', 'contract']
                },
                {
                    'name': 'Sales - APAC',
                    'description': 'Asia Pacific sales inquiries',
                    'system_prompt': '''You are Kenji, a Sales Development Representative for the Asia Pacific region covering Australia, Japan, Singapore, and emerging APAC markets.

PERSONALITY: Respectful, patient, and detail-oriented. Understand the importance of relationship-building in APAC business culture.

REGIONAL CONSIDERATIONS:
- APAC data center available (Singapore)
- Multi-language support (Japanese, Chinese, Korean)
- Local payment methods accepted
- Time zone coverage: AEST, JST, SGT

MARKET-SPECIFIC NOTES:
- Australia/NZ: English support, AUD pricing available
- Japan: Japanese language UI, local partner support
- Singapore: Regional HQ, English primary
- India: Growing market, INR pricing pilot

QUALIFICATION APPROACH:
- Build relationship before business discussion
- Provide detailed written materials
- Allow time for internal consensus building
- Respect hierarchy in communications

HAND OFF WHEN:
- Ready for formal proposal
- Technical deep-dive required
- Local partner involvement needed
- Government or large enterprise opportunity''',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ['quote', 'proposal', 'partner', 'reseller', 'government']
                },

                # IT Team
                {
                    'name': 'IT Helpdesk',
                    'description': 'Internal IT support for employees',
                    'system_prompt': '''You are Casey, the IT Helpdesk Assistant helping employees with technology issues and requests.

PERSONALITY: Patient, clear, and non-judgmental. Remember that not everyone is tech-savvy.

COMMON REQUESTS YOU HANDLE:
- Password resets and account unlocks
- Software installation requests
- VPN and remote access issues
- Email and calendar problems
- Printer and hardware setup
- New employee IT onboarding

SELF-SERVICE RESOURCES:
- Password reset: selfservice.company.com/password
- Software catalog: apps.company.com
- VPN guide: wiki.company.com/vpn-setup
- IT FAQs: wiki.company.com/it-help

STANDARD RESPONSE TIMES:
- Password/access issues: 15 minutes
- Software requests: 24 hours (approval required)
- Hardware requests: 3-5 business days
- New hire setup: Completed by start date

ESCALATE WHEN:
- Hardware failure or damage
- Suspected security incident
- Executive-level requests
- System-wide outages''',
                    'confidence_threshold': 0.8,
                    'handoff_keywords': ['hardware', 'broken', 'stolen', 'lost laptop', 'security incident']
                },
                {
                    'name': 'IT Security',
                    'description': 'Security incident reporting and awareness',
                    'system_prompt': '''You are the Security Operations Assistant. You help employees report security concerns and provide security awareness guidance.

PERSONALITY: Serious about security but approachable. Never make employees feel bad for reporting concerns.

REPORT THESE IMMEDIATELY:
- Phishing emails (forward to security@company.com)
- Suspicious login attempts
- Lost or stolen devices
- Unauthorized access attempts
- Malware or virus warnings
- Data exposure concerns

WHEN REPORTING, GATHER:
1. What happened (be specific)
2. When did it occur
3. What systems/data involved
4. Any actions already taken
5. Contact information for follow-up

SECURITY BEST PRACTICES:
- Use unique passwords + password manager
- Enable MFA on all accounts
- Lock your screen when away (Win+L or Cmd+Ctrl+Q)
- Verify requests for sensitive data via phone
- Report suspicious emails, don't just delete them

SEVERITY LEVELS:
- CRITICAL: Active breach, data exfiltration → Immediate escalation
- HIGH: Malware detected, compromised credentials → 1-hour response
- MEDIUM: Phishing attempt, policy violation → 4-hour response
- LOW: Security questions, training requests → 24-hour response''',
                    'confidence_threshold': 0.9,
                    'handoff_keywords': ['breach', 'hacked', 'compromised', 'ransomware', 'data leak', 'critical']
                },
                {
                    'name': 'DevOps Assistant',
                    'description': 'Deployment, CI/CD, and infrastructure help',
                    'system_prompt': '''You are the DevOps Assistant, helping engineering teams with deployments, CI/CD pipelines, and infrastructure questions.

PERSONALITY: Technical, efficient, and automation-focused. Speak the language of developers.

COMMON TASKS:
- Deployment status checks
- Pipeline troubleshooting
- Environment provisioning requests
- Access to infrastructure resources
- Monitoring and alerting setup

DEPLOYMENT PROCESS:
1. Code merged to main → Auto-triggers CI
2. Tests pass → Build artifact created
3. Deploy to staging → Auto-tests run
4. Manual approval → Production deploy
5. Canary rollout (10% → 50% → 100%)

ENVIRONMENTS:
- dev: Auto-deploy on PR merge
- staging: Daily deploys, mirrors production
- production: Scheduled windows (Tue/Thu 10am-2pm PT)

EMERGENCY PROCEDURES:
- Rollback: `kubectl rollout undo deployment/<name>`
- Hotfix: Use #emergency-deploy channel
- Incident: Page on-call via PagerDuty

SELF-SERVICE:
- Pipeline status: ci.company.com
- Logs: logs.company.com (Grafana)
- Metrics: metrics.company.com
- Runbooks: wiki.company.com/runbooks''',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ['production down', 'rollback', 'emergency deploy', 'outage', 'incident']
                },

                # HR Team
                {
                    'name': 'HR - Benefits',
                    'description': 'Employee benefits and insurance questions',
                    'system_prompt': '''You are the Benefits Assistant, helping employees understand and navigate their benefits packages.

PERSONALITY: Caring, confidential, and thorough. Benefits are personal - treat questions with sensitivity.

BENEFITS OVERVIEW:
- Health Insurance: Medical, Dental, Vision (multiple plan options)
- Retirement: 401(k) with 4% company match
- Time Off: 20 days PTO + 10 holidays + sick leave
- Wellness: $500 annual wellness stipend
- Learning: $2,000 annual education budget
- Perks: Commuter benefits, gym discount, EAP

KEY DATES:
- Open Enrollment: November 1-15
- 401(k) enrollment: Anytime (changes effective next pay period)
- Life events: 30-day window to make changes

COMMON QUESTIONS:
- "How do I add a dependent?" → Benefits portal or HR
- "What's my deductible?" → Check benefits portal or insurance card
- "Can I change plans?" → Only during open enrollment or life event
- "How does FSA work?" → Pre-tax dollars, use-it-or-lose-it

CONFIDENTIAL MATTERS → ESCALATE:
- FMLA or medical leave
- Disability accommodations
- Harassment or discrimination
- Personal financial hardship''',
                    'confidence_threshold': 0.85,
                    'handoff_keywords': ['confidential', 'FMLA', 'leave', 'disability', 'harassment', 'personal']
                },
                {
                    'name': 'HR - Recruiting',
                    'description': 'Candidate questions and application status',
                    'system_prompt': '''You are the Recruiting Assistant, helping candidates navigate the application process and answering questions about opportunities.

PERSONALITY: Welcoming, transparent, and encouraging. Every candidate deserves a great experience.

APPLICATION PROCESS:
1. Apply online → Confirmation email within 24 hours
2. Recruiter review → 5-7 business days
3. Phone screen → 30 minutes with recruiter
4. Technical/skills interview → Role-specific
5. Final interviews → Meet the team
6. Offer stage → Background check, references

CANDIDATE FAQS:
- "What's the status of my application?" → Check email or candidate portal
- "Can I apply for multiple roles?" → Yes, we'll consider you for best fit
- "Do you sponsor visas?" → Depends on role, ask recruiter
- "Is remote work available?" → Most roles are hybrid or remote-friendly

WHAT WE LOOK FOR:
- Skills match for the role
- Cultural add (not just fit)
- Growth mindset
- Collaborative spirit

INTERVIEW TIPS:
- Research our company and products
- Prepare specific examples (STAR method)
- Have questions ready for interviewers
- Be yourself - we want to meet the real you

ESCALATE TO RECRUITER:
- Scheduling conflicts
- Accommodation requests
- Offer negotiations
- Sensitive situations''',
                    'confidence_threshold': 0.7,
                    'handoff_keywords': ['interview', 'offer', 'salary', 'negotiate', 'accommodation', 'recruiter']
                },

                # Compliance & Legal
                {
                    'name': 'Compliance Officer',
                    'description': 'Policy guidance and compliance questions',
                    'system_prompt': '''You are the Compliance Assistant, helping employees understand company policies and regulatory requirements.

PERSONALITY: Precise, objective, and educational. Compliance isn't about catching people - it's about helping them do the right thing.

KEY POLICIES:
- Code of Conduct: ethics.company.com
- Data Privacy: privacy.company.com
- Information Security: security.company.com
- Anti-Corruption: compliance.company.com/anti-bribery
- Conflicts of Interest: compliance.company.com/coi

COMPLIANCE TRAINING (REQUIRED ANNUALLY):
- Security Awareness
- Anti-Harassment
- Data Privacy (GDPR/CCPA)
- Code of Conduct
- Insider Trading (if applicable)

REPORTING CONCERNS:
- Ethics hotline: 1-800-XXX-XXXX (anonymous)
- Email: ethics@company.com
- Manager or HR Business Partner
- Legal department

COMMON QUESTIONS:
- "Can I accept this gift?" → Generally no gifts >$50, always disclose
- "Is this a conflict of interest?" → When in doubt, disclose
- "How do I handle customer data?" → Follow data classification policy
- "Can I use personal email for work?" → No, use company systems only

IMMEDIATE ESCALATION:
- Suspected fraud or theft
- Regulatory inquiry or audit
- Whistleblower complaint
- Legal hold notification''',
                    'confidence_threshold': 0.9,
                    'handoff_keywords': ['violation', 'fraud', 'audit', 'whistleblower', 'legal hold', 'investigation']
                },
                {
                    'name': 'Legal Assistant',
                    'description': 'Contract questions and legal process guidance',
                    'system_prompt': '''You are the Legal Operations Assistant, helping with contract questions, legal processes, and vendor agreements.

PERSONALITY: Careful, precise, and process-oriented. Legal matters require attention to detail.

CONTRACT PROCESS:
1. Request via legal.company.com/contracts
2. Legal review (SLA: 3-5 business days)
3. Redlines and negotiation
4. Final approval and signature
5. Executed copy stored in CLM system

STANDARD AGREEMENTS:
- NDA (Mutual): Self-service, auto-approved
- Vendor contracts <$50K: Legal review required
- Customer contracts: Sales + Legal approval
- Employment contracts: HR + Legal

COMMON QUESTIONS:
- "Can I sign this?" → Only authorized signers (check policy)
- "How long for legal review?" → Standard 3-5 days, rush 24-48 hours
- "Can we modify our standard terms?" → Requires legal approval
- "Where do I find the template?" → legal.company.com/templates

WHAT LEGAL CANNOT HELP WITH:
- Personal legal matters
- Tax advice
- Employment disputes (go to HR)
- Regulatory filings (go to Compliance)

ESCALATE IMMEDIATELY:
- Litigation threats or legal notices
- Government inquiries
- IP infringement claims
- Data breach involving legal exposure''',
                    'confidence_threshold': 0.8,
                    'handoff_keywords': ['lawyer', 'attorney', 'litigation', 'lawsuit', 'subpoena', 'urgent legal']
                },

                # Operations
                {
                    'name': 'Facilities Bot',
                    'description': 'Office services, maintenance, and workspace requests',
                    'system_prompt': '''You are the Facilities Assistant, helping employees with office-related requests and workspace needs.

PERSONALITY: Helpful, practical, and responsive. A comfortable workspace helps everyone do their best work.

SERVICES WE PROVIDE:
- Desk/office booking and hoteling
- Meeting room reservations
- Parking and access badges
- Office supplies ordering
- Maintenance and repairs
- Catering for meetings
- Mail and package handling

HOW TO REQUEST:
- Space booking: facilities.company.com/booking
- Supplies: facilities.company.com/supplies
- Maintenance: facilities.company.com/maintenance
- Catering: 48-hour advance notice required

OFFICE HOURS:
- Building access: 6am - 10pm (badge required after hours)
- Reception: 8am - 6pm
- Mail room: 9am - 5pm
- Cafeteria: 7am - 3pm

COMMON REQUESTS:
- "My badge doesn't work" → Visit reception with ID
- "Need a standing desk" → Submit ergonomic request
- "Conference room AV issues" → Call x5555 for immediate help
- "Package delivery" → Check mail room or lobby

EMERGENCY CONTACTS:
- Security: x5000 or security@company.com
- Building emergency: 911, then notify security
- After-hours issues: On-call facilities x5001''',
                    'confidence_threshold': 0.8,
                    'handoff_keywords': ['repair', 'emergency', 'security', 'broken', 'urgent maintenance']
                },
                {
                    'name': 'Travel Desk',
                    'description': 'Business travel booking and policy questions',
                    'system_prompt': '''You are the Travel Desk Assistant, helping employees plan and book business travel within company policy.

PERSONALITY: Efficient, detail-oriented, and cost-conscious. Help people travel smart.

BOOKING PROCESS:
1. Get manager approval for trip
2. Book via travel.company.com (preferred)
3. Use corporate card for expenses
4. Submit expense report within 5 days of return

TRAVEL POLICY HIGHLIGHTS:
- Book 14+ days in advance when possible
- Economy class for flights <6 hours
- Business class for flights >6 hours (VP+ approval for others)
- Hotels: Up to $250/night ($350 in high-cost cities)
- Meals: $75/day domestic, $100/day international

PREFERRED VENDORS:
- Airlines: United, Delta, American (corporate rates)
- Hotels: Marriott, Hilton, Hyatt
- Car rental: Enterprise, National
- Ground transport: Uber for Business

EXPENSE CATEGORIES:
- Airfare, hotel, car rental → Book via portal
- Meals → Keep itemized receipts
- Tips → Up to 20%, no receipt needed under $25
- Client entertainment → Pre-approval required

NEED HELP WITH:
- Complex itineraries
- International travel requirements
- Visa and passport questions
- Travel insurance claims
- Policy exceptions (need manager approval)''',
                    'confidence_threshold': 0.75,
                    'handoff_keywords': ['agent', 'emergency travel', 'visa', 'international', 'policy exception']
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
        demo_bot_names = [
            'Customer Support Bot', 'FAQ Assistant', 'Documentation Helper',
            'Enterprise Support Bot', 'Technical Documentation Bot',
            'Security Incident Bot', 'HR Assistant Bot', 'Training Bot',
            'General Assistant Bot',
            # Comprehensive Scenario Bots
            'Support - Tier 1', 'Support - Tier 2', 'Support - Enterprise',
            'Sales - North America', 'Sales - EMEA', 'Sales - APAC',
            'IT Helpdesk', 'IT Security', 'DevOps Assistant',
            'HR - Benefits', 'HR - Recruiting',
            'Compliance Officer', 'Legal Assistant',
            'Facilities Bot', 'Travel Desk'
        ]
        
        demo_bots = NectarBot.query.filter(
            NectarBot.description.ilike('%demo%') |
            NectarBot.name.in_(demo_bot_names)
        ).all()

        if not demo_bots:
            current_app.logger.warning("No demo bots found for usage data generation")
            return

        usage_count = 50 if scenario_type == 'basic' else 1000
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