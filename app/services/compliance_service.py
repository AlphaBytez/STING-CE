#!/usr/bin/env python3
"""
Compliance Service
Manages compliance profiles, custom rules, and PII handling policies
Designed to integrate with future agent service for verification
"""

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import logging
from datetime import datetime, timedelta

from app.models.compliance_models import (
    ComplianceProfile, CustomRule, ProfilePatternMapping, 
    ComplianceEvent, ProfileTemplate,
    ComplianceFramework, SensitivityLevel, ActionType, RiskLevel
)
from app.services.hive_scrambler import HiveScrambler, PIIType
from app.extensions import db

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service for managing compliance profiles and PII detection policies
    """
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or db.session
        self.hive_scrambler = HiveScrambler()
    
    # ==================== Profile Management ====================
    
    def create_profile(self, profile_data: Dict[str, Any]) -> ComplianceProfile:
        """Create a new compliance profile"""
        try:
            profile = ComplianceProfile(
                name=profile_data['name'],
                description=profile_data.get('description', ''),
                framework=ComplianceFramework(profile_data['framework']),
                industry=profile_data.get('industry', ''),
                sensitivity_level=SensitivityLevel(profile_data.get('sensitivity_level', 'moderate')),
                confidence_threshold=profile_data.get('confidence_threshold', 0.85),
                default_action=ActionType(profile_data.get('default_action', 'mask')),
                auto_quarantine=profile_data.get('auto_quarantine', False),
                notify_on_detection=profile_data.get('notify_on_detection', True),
                require_approval=profile_data.get('require_approval', False),
                log_retention_days=profile_data.get('log_retention_days', 365),
                audit_trail_enabled=profile_data.get('audit_trail_enabled', True),
                scan_file_types=profile_data.get('scan_file_types', ['pdf', 'docx', 'txt', 'xlsx']),
                exclude_system_files=profile_data.get('exclude_system_files', True),
                scan_depth=profile_data.get('scan_depth', 'normal'),
                jurisdictions=profile_data.get('jurisdictions', []),
                data_residency=profile_data.get('data_residency', ''),
                agent_verification_enabled=profile_data.get('agent_verification_enabled', False),
                agent_escalation_threshold=profile_data.get('agent_escalation_threshold', 0.7),
                created_by=profile_data.get('created_by', 'system')
            )
            
            self.db.add(profile)
            self.db.commit()
            
            # Add default pattern mappings based on framework
            self._add_default_patterns(profile)
            
            logger.info(f"Created compliance profile: {profile.name} ({profile.id})")
            return profile
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating compliance profile: {str(e)}")
            raise
    
    def get_profile(self, profile_id: str) -> Optional[ComplianceProfile]:
        """Get compliance profile by ID"""
        return self.db.query(ComplianceProfile).filter(
            ComplianceProfile.id == profile_id,
            ComplianceProfile.is_active == True
        ).first()
    
    def list_profiles(self, framework: str = None, industry: str = None) -> List[ComplianceProfile]:
        """List compliance profiles with optional filtering"""
        query = self.db.query(ComplianceProfile).filter(ComplianceProfile.is_active == True)
        
        if framework:
            query = query.filter(ComplianceProfile.framework == framework)
        if industry:
            query = query.filter(ComplianceProfile.industry == industry)
        
        return query.order_by(ComplianceProfile.created_at.desc()).all()
    
    def update_profile(self, profile_id: str, updates: Dict[str, Any]) -> ComplianceProfile:
        """Update compliance profile settings"""
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile not found: {profile_id}")
        
        try:
            for key, value in updates.items():
                if hasattr(profile, key):
                    # Handle enum conversions
                    if key == 'framework' and isinstance(value, str):
                        value = ComplianceFramework(value)
                    elif key == 'sensitivity_level' and isinstance(value, str):
                        value = SensitivityLevel(value)
                    elif key == 'default_action' and isinstance(value, str):
                        value = ActionType(value)
                    
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated compliance profile: {profile.name}")
            return profile
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating compliance profile: {str(e)}")
            raise
    
    # ==================== Custom Rules Management ====================
    
    def create_custom_rule(self, rule_data: Dict[str, Any]) -> CustomRule:
        """Create a new custom detection rule"""
        try:
            rule = CustomRule(
                profile_id=rule_data['profile_id'],
                name=rule_data['name'],
                description=rule_data.get('description', ''),
                based_on_pattern=rule_data['based_on_pattern'],
                conditions=rule_data.get('conditions', []),
                primary_action=ActionType(rule_data['primary_action']),
                secondary_action=ActionType(rule_data['secondary_action']) if rule_data.get('secondary_action') else None,
                escalation_action=ActionType(rule_data['escalation_action']) if rule_data.get('escalation_action') else None,
                risk_level_override=RiskLevel(rule_data['risk_level_override']) if rule_data.get('risk_level_override') else None,
                confidence_override=rule_data.get('confidence_override'),
                exceptions=rule_data.get('exceptions', []),
                agent_review_required=rule_data.get('agent_review_required', False),
                agent_confidence_threshold=rule_data.get('agent_confidence_threshold', 0.8)
            )
            
            self.db.add(rule)
            self.db.commit()
            
            logger.info(f"Created custom rule: {rule.name} for profile {rule.profile_id}")
            return rule
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating custom rule: {str(e)}")
            raise
    
    def get_rules_for_profile(self, profile_id: str) -> List[CustomRule]:
        """Get all custom rules for a profile"""
        return self.db.query(CustomRule).filter(
            CustomRule.profile_id == profile_id,
            CustomRule.is_active == True
        ).order_by(CustomRule.created_at.desc()).all()
    
    def test_custom_rule(self, rule_id: str, test_text: str) -> Dict[str, Any]:
        """Test a custom rule against sample text"""
        rule = self.db.query(CustomRule).filter(CustomRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")
        
        # Use hive scrambler to test the base pattern
        base_pattern_results = self.hive_scrambler.detect_pii(test_text)
        
        # Filter results for the specific pattern this rule is based on
        base_matches = [
            result for result in base_pattern_results 
            if result.pii_type.value == rule.based_on_pattern
        ]
        
        # Apply custom rule conditions
        filtered_matches = self._apply_rule_conditions(base_matches, rule.conditions, test_text)
        
        return {
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "base_pattern": rule.based_on_pattern,
            "base_matches": len(base_matches),
            "filtered_matches": len(filtered_matches),
            "matches": [
                {
                    "text": match.text,
                    "start": match.start_position,
                    "end": match.end_position,
                    "confidence": match.confidence,
                    "risk_level": rule.risk_level_override or match.risk_level,
                    "action": rule.primary_action.value
                }
                for match in filtered_matches
            ]
        }
    
    # ==================== Pattern Management ====================
    
    def get_available_patterns(self) -> List[Dict[str, Any]]:
        """Get all available PII patterns from HiveScrambler"""
        patterns = []
        for pii_type in PIIType:
            patterns.append({
                "name": pii_type.value,
                "display_name": pii_type.value.replace('_', ' ').title(),
                "description": f"Detects {pii_type.value.replace('_', ' ')} patterns",
                "compliance_frameworks": self._get_frameworks_for_pattern(pii_type)
            })
        return patterns
    
    def configure_pattern_for_profile(self, profile_id: str, pattern_name: str, config: Dict[str, Any]) -> ProfilePatternMapping:
        """Configure a specific pattern for a compliance profile"""
        try:
            # Check if mapping already exists
            existing = self.db.query(ProfilePatternMapping).filter(
                ProfilePatternMapping.profile_id == profile_id,
                ProfilePatternMapping.pattern_name == pattern_name
            ).first()
            
            if existing:
                # Update existing mapping
                for key, value in config.items():
                    if hasattr(existing, key):
                        if key.endswith('_override') and isinstance(value, str):
                            # Handle enum conversions for overrides
                            if 'action' in key:
                                value = ActionType(value)
                            elif 'risk_level' in key:
                                value = RiskLevel(value)
                        setattr(existing, key, value)
                
                existing.updated_at = datetime.utcnow()
                mapping = existing
            else:
                # Create new mapping
                mapping = ProfilePatternMapping(
                    profile_id=profile_id,
                    pattern_name=pattern_name,
                    is_enabled=config.get('is_enabled', True),
                    action_override=ActionType(config['action_override']) if config.get('action_override') else None,
                    risk_level_override=RiskLevel(config['risk_level_override']) if config.get('risk_level_override') else None,
                    confidence_threshold_override=config.get('confidence_threshold_override'),
                    context_keywords=config.get('context_keywords', []),
                    exclusion_patterns=config.get('exclusion_patterns', [])
                )
                self.db.add(mapping)
            
            self.db.commit()
            return mapping
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error configuring pattern {pattern_name} for profile {profile_id}: {str(e)}")
            raise
    
    # ==================== Template Management ====================
    
    def create_profile_template(self, template_data: Dict[str, Any]) -> ProfileTemplate:
        """Create a reusable profile template"""
        try:
            template = ProfileTemplate(
                name=template_data['name'],
                description=template_data.get('description', ''),
                industry=template_data['industry'],
                framework=ComplianceFramework(template_data['framework']),
                template_config=template_data['template_config'],
                default_patterns=template_data.get('default_patterns', []),
                recommended_rules=template_data.get('recommended_rules', []),
                created_by=template_data.get('created_by', 'system')
            )
            
            self.db.add(template)
            self.db.commit()
            
            logger.info(f"Created profile template: {template.name}")
            return template
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating profile template: {str(e)}")
            raise
    
    def list_templates(self, industry: str = None, framework: str = None) -> List[ProfileTemplate]:
        """List available profile templates"""
        query = self.db.query(ProfileTemplate).filter(ProfileTemplate.is_active == True)
        
        if industry:
            query = query.filter(ProfileTemplate.industry == industry)
        if framework:
            query = query.filter(ProfileTemplate.framework == framework)
        
        return query.order_by(ProfileTemplate.usage_count.desc()).all()
    
    def create_profile_from_template(self, template_id: str, profile_name: str, customizations: Dict[str, Any] = None) -> ComplianceProfile:
        """Create a compliance profile from a template"""
        template = self.db.query(ProfileTemplate).filter(ProfileTemplate.id == template_id).first()
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Merge template config with customizations
        profile_config = template.template_config.copy()
        if customizations:
            profile_config.update(customizations)
        
        profile_config['name'] = profile_name
        profile_config['framework'] = template.framework.value
        profile_config['industry'] = template.industry
        
        # Create profile
        profile = self.create_profile(profile_config)
        
        # Update template usage statistics
        template.usage_count += 1
        template.last_used = datetime.utcnow()
        self.db.commit()
        
        return profile
    
    # ==================== Event Logging ====================
    
    def log_compliance_event(self, event_data: Dict[str, Any]) -> ComplianceEvent:
        """Log a compliance event for audit trail"""
        try:
            event = ComplianceEvent(
                profile_id=event_data.get('profile_id'),
                event_type=event_data['event_type'],
                pii_type=event_data.get('pii_type'),
                rule_id=event_data.get('rule_id'),
                content_snippet=event_data.get('content_snippet'),
                detection_confidence=event_data.get('detection_confidence'),
                detection_method=event_data.get('detection_method'),
                action_taken=ActionType(event_data['action_taken']) if event_data.get('action_taken') else None,
                action_successful=event_data.get('action_successful', True),
                action_details=event_data.get('action_details'),
                source_file=event_data.get('source_file'),
                source_location=event_data.get('source_location'),
                user_id=event_data.get('user_id'),
                user_role=event_data.get('user_role')
            )
            
            self.db.add(event)
            self.db.commit()
            
            return event
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging compliance event: {str(e)}")
            raise
    
    def get_compliance_events(self, profile_id: str = None, days: int = 30) -> List[ComplianceEvent]:
        """Get compliance events for monitoring"""
        query = self.db.query(ComplianceEvent)
        
        if profile_id:
            query = query.filter(ComplianceEvent.profile_id == profile_id)
        
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(ComplianceEvent.timestamp >= since)
        
        return query.order_by(ComplianceEvent.timestamp.desc()).all()
    
    # ==================== Agent Service Integration (Future) ====================
    
    def prepare_for_agent_review(self, event_id: str) -> Dict[str, Any]:
        """Prepare compliance event data for agent service review"""
        event = self.db.query(ComplianceEvent).filter(ComplianceEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Event not found: {event_id}")
        
        # Prepare structured data for agent analysis
        return {
            "event_id": str(event.id),
            "event_type": event.event_type,
            "pii_type": event.pii_type,
            "detection_confidence": event.detection_confidence,
            "action_taken": event.action_taken.value if event.action_taken else None,
            "context": {
                "source_file": event.source_file,
                "user_role": event.user_role,
                "profile_framework": event.profile.framework.value if event.profile else None
            },
            "requires_review": event.detection_confidence < 0.8 or event.action_taken == ActionType.FLAG,
            "compliance_rules": self._get_applicable_rules(event)
        }
    
    # ==================== Private Helper Methods ====================
    
    def _add_default_patterns(self, profile: ComplianceProfile):
        """Add default pattern mappings based on compliance framework"""
        framework_patterns = {
            ComplianceFramework.HIPAA: [
                'medical_record_number', 'health_insurance_id', 'patient_id', 
                'medication_name', 'diagnosis', 'social_security_number'
            ],
            ComplianceFramework.PCI_DSS: [
                'credit_card', 'bank_account', 'routing_number'
            ],
            ComplianceFramework.GDPR: [
                'social_security_number', 'email_address', 'phone_number', 
                'person_name', 'date_of_birth', 'physical_address'
            ],
            ComplianceFramework.ATTORNEY_CLIENT: [
                'case_number', 'bar_number', 'court_docket', 'settlement_amount',
                'contract_id', 'witness_name', 'judge_name'
            ]
        }
        
        default_patterns = framework_patterns.get(profile.framework, [])
        
        for pattern_name in default_patterns:
            mapping = ProfilePatternMapping(
                profile_id=profile.id,
                pattern_name=pattern_name,
                is_enabled=True
            )
            self.db.add(mapping)
        
        self.db.commit()
    
    def _get_frameworks_for_pattern(self, pii_type: PIIType) -> List[str]:
        """Get applicable compliance frameworks for a PII type"""
        # This would use the logic from HiveScrambler._get_compliance_frameworks
        return self.hive_scrambler._get_compliance_frameworks(pii_type, "")
    
    def _apply_rule_conditions(self, matches: List, conditions: List[Dict], text: str) -> List:
        """Apply custom rule conditions to filter matches"""
        # Implementation for applying complex rule conditions
        # This would evaluate each condition in the conditions array
        filtered_matches = matches
        
        for condition in conditions:
            condition_type = condition.get('type')
            
            if condition_type == 'context_keywords':
                keywords = condition.get('keywords', [])
                min_matches = condition.get('min_matches', 1)
                # Filter matches that don't have enough context keyword matches
                # Implementation would check surrounding text for keywords
                pass
            
            elif condition_type == 'file_path':
                # Would be applied at the file level, not individual matches
                pass
            
            elif condition_type == 'confidence_threshold':
                threshold = condition.get('threshold', 0.5)
                filtered_matches = [m for m in filtered_matches if m.confidence >= threshold]
        
        return filtered_matches
    
    def _get_applicable_rules(self, event: ComplianceEvent) -> List[Dict]:
        """Get rules applicable to a compliance event"""
        if not event.profile_id:
            return []
        
        rules = self.get_rules_for_profile(event.profile_id)
        applicable = []
        
        for rule in rules:
            if rule.based_on_pattern == event.pii_type:
                applicable.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "primary_action": rule.primary_action.value,
                    "requires_agent_review": rule.agent_review_required
                })
        
        return applicable