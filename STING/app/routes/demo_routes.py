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
# Simplified imports for working demo routes
from app.extensions import db
from app.models import User
from app.models.nectar_bot_models import NectarBot, NectarBotHandoff, NectarBotUsage, BotStatus, HandoffStatus, HandoffUrgency
# Note: These model imports will need to be added if they don't exist
# from app.models.honey_jar_models import HoneyJar
# from app.models.document_models import Document
# from app.models.report_models import Report
# from app.models.honey_reserve import HoneyReserve
# from app.models.demo_generators import MedicalDemoGenerator, LegalDemoGenerator, FinancialDemoGenerator
import json
import uuid

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
    """Create basic set of honey jars"""
    basic_jars = [
        {'name': 'Medical Records Demo', 'description': 'Sample medical documents for HIPAA compliance testing', 'category': 'Healthcare'},
        {'name': 'Legal Documents Demo', 'description': 'Sample legal documents with attorney-client privilege', 'category': 'Legal'},
        {'name': 'Financial Data Demo', 'description': 'Sample financial documents for PCI compliance', 'category': 'Financial'},
        {'name': 'HR Records Demo', 'description': 'Sample employee records with PII', 'category': 'Human Resources'},
        {'name': 'Customer Data Demo', 'description': 'Sample customer information and transactions', 'category': 'Customer Service'}
    ]
    
    created = 0
    for jar_config in basic_jars:
        try:
            # Check if jar already exists
            existing = HoneyJar.query.filter_by(name=jar_config['name']).first()
            if not existing:
                jar = HoneyJar(
                    name=jar_config['name'],
                    description=jar_config['description'],
                    owner_id=1,  # Admin user
                    is_public=True,
                    metadata={'category': jar_config['category'], 'demo_data': True}
                )
                db.session.add(jar)
                created += 1
        except Exception as e:
            current_app.logger.error(f"Error creating honey jar {jar_config['name']}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing honey jars: {str(e)}")
        
    return created

def _create_comprehensive_honey_jars():
    """Create comprehensive set of honey jars"""
    comprehensive_jars = [
        {'name': 'Enterprise Security Policies', 'description': 'Complete security policy documentation', 'category': 'Security'},
        {'name': 'Incident Response Playbooks', 'description': 'Security incident response procedures', 'category': 'Security'},
        {'name': 'Compliance Audit Reports', 'description': 'Historical compliance audit documentation', 'category': 'Compliance'},
        {'name': 'Vendor Management', 'description': 'Third-party vendor contracts and assessments', 'category': 'Procurement'},
        {'name': 'Employee Training Materials', 'description': 'Security awareness and training content', 'category': 'Training'},
        {'name': 'Risk Assessment Archive', 'description': 'Historical risk assessments and mitigation plans', 'category': 'Risk Management'},
        {'name': 'Business Continuity Plans', 'description': 'Disaster recovery and continuity procedures', 'category': 'Business Continuity'},
        {'name': 'Technical Documentation', 'description': 'System architecture and technical specifications', 'category': 'Technical'},
        {'name': 'Legal Contracts Archive', 'description': 'Historical legal agreements and contracts', 'category': 'Legal'},
        {'name': 'Financial Audit Trail', 'description': 'Financial records and audit documentation', 'category': 'Financial'}
    ]
    
    created = 0
    for jar_config in comprehensive_jars:
        try:
            existing = HoneyJar.query.filter_by(name=jar_config['name']).first()
            if not existing:
                jar = HoneyJar(
                    name=jar_config['name'],
                    description=jar_config['description'],
                    owner_id=1,
                    is_public=True,
                    metadata={'category': jar_config['category'], 'demo_data': True, 'scenario': 'comprehensive'}
                )
                db.session.add(jar)
                created += 1
        except Exception as e:
            current_app.logger.error(f"Error creating comprehensive honey jar {jar_config['name']}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing comprehensive honey jars: {str(e)}")
        
    return created

def _create_security_honey_jars():
    """Create security-focused honey jars"""
    security_jars = [
        {'name': 'Security Incident Reports', 'description': 'Historical security incidents and responses', 'category': 'Security'},
        {'name': 'Vulnerability Assessments', 'description': 'Security vulnerability scan results', 'category': 'Security'},
        {'name': 'Penetration Test Reports', 'description': 'Third-party security assessment reports', 'category': 'Security'},
        {'name': 'Compliance Frameworks', 'description': 'SOC2, ISO27001, and other compliance documentation', 'category': 'Compliance'},
        {'name': 'Access Control Policies', 'description': 'Identity and access management procedures', 'category': 'Security'}
    ]
    
    created = 0
    for jar_config in security_jars:
        try:
            existing = HoneyJar.query.filter_by(name=jar_config['name']).first()
            if not existing:
                jar = HoneyJar(
                    name=jar_config['name'],
                    description=jar_config['description'],
                    owner_id=1,
                    is_public=True,
                    metadata={'category': jar_config['category'], 'demo_data': True, 'scenario': 'security'}
                )
                db.session.add(jar)
                created += 1
        except Exception as e:
            current_app.logger.error(f"Error creating security honey jar {jar_config['name']}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing security honey jars: {str(e)}")
        
    return created

def _create_pii_honey_jars():
    """Create PII-focused honey jars"""
    pii_jars = [
        {'name': 'PII Detection Samples', 'description': 'Documents with various PII types for testing', 'category': 'PII Testing'},
        {'name': 'HIPAA Test Documents', 'description': 'Medical records for HIPAA compliance testing', 'category': 'Healthcare'},
        {'name': 'Financial PII Samples', 'description': 'Financial documents for PCI testing', 'category': 'Financial'}
    ]
    
    created = 0
    for jar_config in pii_jars:
        try:
            existing = HoneyJar.query.filter_by(name=jar_config['name']).first()
            if not existing:
                jar = HoneyJar(
                    name=jar_config['name'],
                    description=jar_config['description'],
                    owner_id=1,
                    is_public=True,
                    metadata={'category': jar_config['category'], 'demo_data': True, 'scenario': 'pii'}
                )
                db.session.add(jar)
                created += 1
        except Exception as e:
            current_app.logger.error(f"Error creating PII honey jar {jar_config['name']}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing PII honey jars: {str(e)}")
        
    return created

def _create_sample_documents(scenario_type):
    """Create sample documents based on scenario"""
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
            _save_demo_document('Medical Records Demo', f'medical_sample_{i+1}.txt', doc_content)
            documents_created += 1
        
        # Create legal documents
        for i in range(counts['legal']):
            doc_content = random.choice([
                legal_gen.generate_case_file(),
                legal_gen.generate_contract()
            ])
            _save_demo_document('Legal Documents Demo', f'legal_sample_{i+1}.txt', doc_content)
            documents_created += 1
        
        # Create financial documents
        for i in range(counts['financial']):
            doc_content = financial_gen.generate_loan_application()
            _save_demo_document('Financial Data Demo', f'financial_sample_{i+1}.txt', doc_content)
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
        
        # Create diverse PII samples
        pii_samples = [
            medical_gen.generate_patient_intake_form(),
            medical_gen.generate_lab_results(),
            legal_gen.generate_case_file(),
            financial_gen.generate_loan_application()
        ]
        
        for i, sample in enumerate(pii_samples):
            _save_demo_document('PII Detection Samples', f'pii_sample_{i+1}.txt', sample)
            documents_created += 1
            
    except Exception as e:
        current_app.logger.error(f"Error creating PII documents: {str(e)}")
    
    return documents_created

def _save_demo_document(jar_name, filename, content):
    """Save a demo document to a honey jar"""
    try:
        # Find the honey jar
        jar = HoneyJar.query.filter_by(name=jar_name).first()
        if not jar:
            current_app.logger.warning(f"Honey jar '{jar_name}' not found for document {filename}")
            return False
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Use HoneyReserve to store the document
            honey_reserve = HoneyReserve()
            file_id = honey_reserve.store_file(
                user_id=1,  # Admin user
                file_path=temp_file_path,
                filename=filename,
                metadata={'demo_data': True, 'jar_id': jar.id}
            )
            
            # Add document record
            document = Document(
                filename=filename,
                honey_jar_id=jar.id,
                uploader_id=1,
                file_path=f"honey_reserve/{file_id}",
                file_size=len(content),
                mime_type='text/plain',
                status='approved',  # Auto-approve demo documents
                metadata={'demo_data': True, 'file_id': file_id}
            )
            
            db.session.add(document)
            db.session.commit()
            
            return True
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        current_app.logger.error(f"Error saving demo document {filename}: {str(e)}")
        return False

def _create_sample_reports(scenario_type):
    """Create sample reports"""
    reports_created = 0
    
    try:
        report_configs = {
            'basic': [
                {'name': 'Basic PII Scan Report', 'type': 'pii_scan'},
                {'name': 'Security Overview Report', 'type': 'security_overview'},
                {'name': 'Compliance Status Report', 'type': 'compliance_status'}
            ],
            'comprehensive': [
                {'name': 'Comprehensive PII Audit', 'type': 'pii_audit'},
                {'name': 'Security Risk Assessment', 'type': 'security_assessment'},
                {'name': 'HIPAA Compliance Report', 'type': 'hipaa_compliance'},
                {'name': 'GDPR Compliance Report', 'type': 'gdpr_compliance'},
                {'name': 'Financial Audit Report', 'type': 'financial_audit'}
            ],
            'security': [
                {'name': 'Security Incident Analysis', 'type': 'incident_analysis'},
                {'name': 'Vulnerability Assessment Report', 'type': 'vulnerability_assessment'},
                {'name': 'SOC2 Compliance Report', 'type': 'soc2_compliance'}
            ],
            'pii': [
                {'name': 'PII Detection Analysis', 'type': 'pii_detection'},
                {'name': 'Data Classification Report', 'type': 'data_classification'}
            ]
        }
        
        configs = report_configs.get(scenario_type, report_configs['basic'])
        
        for config in configs:
            try:
                # Attempt to create actual report file (simulation)
                file_creation_successful = False
                failure_reason = None

                try:
                    # Simulate file creation process
                    # In real implementation, this would create actual PDF/Excel files
                    # For demo, we'll simulate failure based on the config
                    if config.get('simulate_failure', True):  # Most demos fail file creation
                        failure_reason = "DEMO DATA - FILE CREATION FAILED"
                        file_creation_successful = False
                    else:
                        file_creation_successful = True
                except Exception as file_error:
                    failure_reason = f"File creation error: {str(file_error)}"
                    file_creation_successful = False

                # Set status based on actual file creation success
                report_status = 'completed' if file_creation_successful else 'failed'
                report_description = config.get('description', '')

                # Add failure reason to description if needed
                if not file_creation_successful and failure_reason:
                    report_description = f"{report_description} [{failure_reason}]"

                report = Report(
                    name=config['name'],
                    report_type=config['type'],
                    generated_by=1,  # Admin user
                    status=report_status,  # Now reflects actual success/failure
                    metadata={'demo_data': True, 'scenario': scenario_type, 'file_creation_attempted': True, 'file_creation_successful': file_creation_successful},
                    results={'demo': True, 'generated_at': datetime.utcnow().isoformat(), 'file_creation_successful': file_creation_successful}
                )
                
                db.session.add(report)
                reports_created += 1
                
            except Exception as e:
                current_app.logger.error(f"Error creating report {config['name']}: {str(e)}")
        
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
    """Create demo Nectar Bots based on scenario"""
    bots_created = 0

    try:
        # Get available honey jars for bot configuration
        honey_jars = HoneyJar.query.filter_by(is_public=True).all()
        jar_ids = [str(jar.id) for jar in honey_jars[:3]]  # Use first 3 jars

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

        # Create bots
        for config in bot_configs:
            try:
                # Check if bot already exists
                existing = NectarBot.query.filter_by(name=config['name']).first()
                if not existing:
                    bot = NectarBot(
                        name=config['name'],
                        description=config['description'],
                        owner_id=str(uuid.uuid4()),  # Use admin user ID in real implementation
                        owner_email='admin@sting.local',
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
                        handoff_confidence_threshold=0.6
                    )
                    db.session.add(bot)
                    bots_created += 1
            except Exception as e:
                current_app.logger.error(f"Error creating nectar bot {config['name']}: {str(e)}")

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error creating demo nectar bots: {str(e)}")
        db.session.rollback()

    return bots_created

def _create_demo_bot_usage(scenario_type):
    """Create demo bot usage data"""
    try:
        # Get all demo bots
        demo_bots = NectarBot.query.filter_by(is_public=True).all()

        for bot in demo_bots:
            # Create usage records for the past 30 days
            from datetime import datetime, timedelta

            usage_count = 50 if scenario_type == 'basic' else 150
            handoff_count = 5 if scenario_type == 'basic' else 15

            # Create usage records
            for i in range(usage_count):
                usage = NectarBotUsage(
                    bot_id=bot.id,
                    conversation_id=f"conv_{random.randint(10000, 99999)}",
                    message_id=f"msg_{random.randint(10000, 99999)}",
                    user_id=f"user_{random.randint(100, 999)}",
                    user_ip=f"192.168.1.{random.randint(1, 254)}",
                    user_agent="Demo User Agent",
                    user_message=f"Demo user question {i+1}",
                    bot_response=f"Demo bot response {i+1}",
                    confidence_score=random.uniform(0.5, 0.95),
                    response_time_ms=random.randint(200, 2000),
                    honey_jars_queried=bot.honey_jar_ids[:2],
                    knowledge_matches=random.randint(1, 5),
                    rate_limit_hit=False,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(usage)

            # Create handoff records
            for i in range(handoff_count):
                handoff = NectarBotHandoff(
                    bot_id=bot.id,
                    conversation_id=f"conv_{random.randint(10000, 99999)}",
                    user_id=f"user_{random.randint(100, 999)}",
                    user_info={'name': f'Demo User {i+1}', 'email': f'user{i+1}@demo.local'},
                    reason='low_confidence' if random.random() > 0.5 else 'keyword_detected',
                    urgency=random.choice([HandoffUrgency.LOW.value, HandoffUrgency.MEDIUM.value, HandoffUrgency.HIGH.value]),
                    status=HandoffStatus.RESOLVED.value if random.random() > 0.3 else HandoffStatus.PENDING.value,
                    conversation_history=[
                        {'user': f'Demo question {i+1}', 'bot': f'Demo response {i+1}'}
                    ],
                    honey_jars_used=bot.honey_jar_ids[:1],
                    trigger_message=f"Demo trigger message {i+1}",
                    bot_response=f"Demo bot response {i+1}",
                    confidence_score=random.uniform(0.3, 0.6),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )

                if handoff.status == HandoffStatus.RESOLVED.value:
                    handoff.resolved_at = handoff.created_at + timedelta(hours=random.randint(1, 24))
                    handoff.resolution_notes = f"Demo resolution notes {i+1}"
                    handoff.calculate_resolution_time()

                db.session.add(handoff)

            # Update bot statistics
            bot.update_stats()

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
    """Create honey jars optimized for bot knowledge bases"""
    bot_jars = [
        {'name': 'Customer Support Knowledge Base', 'description': 'FAQs, troubleshooting guides, and customer service procedures', 'category': 'Support'},
        {'name': 'Product Documentation Hub', 'description': 'User manuals, feature guides, and product specifications', 'category': 'Documentation'},
        {'name': 'Technical Support Library', 'description': 'API docs, integration guides, and technical troubleshooting', 'category': 'Technical'},
        {'name': 'Company Policy Center', 'description': 'HR policies, procedures, and employee handbook information', 'category': 'Policies'},
        {'name': 'Training Materials Archive', 'description': 'Training guides, tutorials, and educational content', 'category': 'Training'}
    ]

    created = 0
    for jar_config in bot_jars:
        try:
            existing = HoneyJar.query.filter_by(name=jar_config['name']).first()
            if not existing:
                jar = HoneyJar(
                    name=jar_config['name'],
                    description=jar_config['description'],
                    owner_id=1,
                    is_public=True,
                    metadata={'category': jar_config['category'], 'demo_data': True, 'scenario': 'nectar-bot', 'optimized_for_bots': True}
                )
                db.session.add(jar)
                created += 1
        except Exception as e:
            current_app.logger.error(f"Error creating bot knowledge honey jar {jar_config['name']}: {str(e)}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing bot knowledge honey jars: {str(e)}")

    return created

def _create_bot_training_documents():
    """Create documents specifically for training nectar bots"""
    documents_created = 0

    try:
        # Bot training content
        training_docs = [
            {
                'jar': 'Customer Support Knowledge Base',
                'filename': 'customer_service_faqs.txt',
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
                _save_demo_document(doc_config['jar'], doc_config['filename'], doc_config['content'])
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
    Clear all demo data from the system
    """
    try:
        current_app.logger.info("Starting demo data cleanup")
        
        # Clear demo documents
        demo_documents = Document.query.filter(
            Document.metadata.contains({'demo_data': True})
        ).all()
        
        for doc in demo_documents:
            try:
                # Remove from Honey Reserve if applicable
                if 'file_id' in doc.metadata:
                    honey_reserve = HoneyReserve()
                    honey_reserve.delete_file(doc.metadata['file_id'])
                
                db.session.delete(doc)
            except Exception as e:
                current_app.logger.error(f"Error deleting demo document {doc.id}: {str(e)}")
        
        # Clear demo honey jars
        demo_jars = HoneyJar.query.filter(
            HoneyJar.metadata.contains({'demo_data': True})
        ).all()
        
        for jar in demo_jars:
            db.session.delete(jar)
        
        # Clear demo reports
        demo_reports = Report.query.filter(
            Report.metadata.contains({'demo_data': True})
        ).all()
        
        for report in demo_reports:
            db.session.delete(report)
        
        # Clear demo users (be careful with this)
        demo_users = User.query.filter(
            User.metadata.contains({'demo_data': True})
        ).all()

        for user in demo_users:
            db.session.delete(user)

        # Clear demo nectar bots (this will cascade to handoffs and usage)
        demo_bots = NectarBot.query.filter_by(is_public=True).all()
        demo_bot_count = 0

        for bot in demo_bots:
            # Only delete if it looks like demo data (check name patterns)
            if any(keyword in bot.name for keyword in ['Demo', 'Customer Support Bot', 'FAQ Assistant', 'Documentation Helper', 'Enterprise Support Bot', 'Technical Documentation Bot', 'Security Incident Bot', 'HR Assistant Bot', 'Training Bot', 'General Assistant Bot']):
                db.session.delete(bot)
                demo_bot_count += 1

        # Commit all deletions
        db.session.commit()
        
        current_app.logger.info("Demo data cleanup completed successfully")
        
        return jsonify({
            'success': True,
            'message': 'All demo data cleared successfully',
            'cleared': {
                'documents': len(demo_documents),
                'honeyJars': len(demo_jars),
                'reports': len(demo_reports),
                'users': len(demo_users),
                'nectarBots': demo_bot_count
            }
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
    Get current demo data status and counts
    """
    try:
        # Count demo data
        demo_documents = Document.query.filter(
            Document.metadata.contains({'demo_data': True})
        ).count()
        
        demo_jars = HoneyJar.query.filter(
            HoneyJar.metadata.contains({'demo_data': True})
        ).count()
        
        demo_reports = Report.query.filter(
            Report.metadata.contains({'demo_data': True})
        ).count()
        
        demo_users = User.query.filter(
            User.metadata.contains({'demo_data': True})
        ).count()

        # Count demo nectar bots (approximate by checking public bots with common demo names)
        demo_bots_count = NectarBot.query.filter_by(is_public=True).filter(
            NectarBot.name.contains('Bot') |
            NectarBot.name.contains('Assistant') |
            NectarBot.name.contains('Support')
        ).count()

        return jsonify({
            'success': True,
            'demo_data': {
                'documents': demo_documents,
                'honeyJars': demo_jars,
                'reports': demo_reports,
                'users': demo_users,
                'nectarBots': demo_bots_count
            },
            'has_demo_data': any([demo_documents, demo_jars, demo_reports, demo_users, demo_bots_count])
        })
        
    except Exception as e:
        current_app.logger.error(f"Demo status error: {str(e)}")
        return jsonify({
            'error': 'Failed to get demo status',
            'details': str(e)
        }), 500