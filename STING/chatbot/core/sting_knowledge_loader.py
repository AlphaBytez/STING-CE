"""
STING Architecture Knowledge Loader for Bee
Loads system architecture knowledge to enable intelligent support assistance
"""

import yaml
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class STINGKnowledgeLoader:
    """Loads and manages STING system architecture knowledge for Bee"""
    
    def __init__(self, knowledge_file_path: Optional[str] = None):
        """
        Initialize the knowledge loader
        
        Args:
            knowledge_file_path: Path to the STING architecture knowledge file
        """
        if knowledge_file_path is None:
            # Default to the knowledge file in the chatbot directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            knowledge_file_path = os.path.join(base_dir, "knowledge", "sting_architecture.yml")
        
        self.knowledge_file_path = knowledge_file_path
        self.knowledge_data: Dict[str, Any] = {}
        self.loaded_at: Optional[datetime] = None
        
    def load_knowledge(self) -> bool:
        """
        Load STING architecture knowledge from YAML file
        
        Returns:
            bool: True if knowledge loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.knowledge_file_path):
                logger.warning(f"STING knowledge file not found: {self.knowledge_file_path}")
                return False
            
            with open(self.knowledge_file_path, 'r', encoding='utf-8') as f:
                self.knowledge_data = yaml.safe_load(f)
            
            self.loaded_at = datetime.now()
            logger.info(f"STING architecture knowledge loaded successfully from {self.knowledge_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load STING knowledge: {str(e)}")
            return False
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dict with service information or None if not found
        """
        services = self.knowledge_data.get('services', {})
        return services.get(service_name)
    
    def get_issue_mapping(self, issue_type: str) -> Optional[Dict[str, Any]]:
        """
        Get service mapping for a specific issue type
        
        Args:
            issue_type: Type of issue (e.g., 'authentication', 'frontend')
            
        Returns:
            Dict with issue mapping or None if not found
        """
        issue_mappings = self.knowledge_data.get('issue_mappings', {})
        return issue_mappings.get(issue_type)
    
    def analyze_issue_description(self, description: str) -> Dict[str, Any]:
        """
        Analyze an issue description and map it to services and diagnostics
        
        Args:
            description: User's description of the issue
            
        Returns:
            Dict containing analysis results
        """
        description_lower = description.lower()
        
        # Default analysis result
        analysis = {
            'detected_issue_types': [],
            'primary_services': [],
            'secondary_services': [],
            'diagnostic_flags': [],
            'log_sources': [],
            'confidence_score': 0.0,
            'suggested_actions': [],
            'troubleshooting_commands': []
        }
        
        issue_mappings = self.knowledge_data.get('issue_mappings', {})
        
        # Check each issue type for keyword matches
        for issue_type, mapping in issue_mappings.items():
            # Simple keyword matching (could be enhanced with NLP later)
            keywords = self._get_issue_keywords(issue_type)
            
            matches = sum(1 for keyword in keywords if keyword in description_lower)
            if matches > 0:
                confidence = min(matches / len(keywords), 1.0)
                
                analysis['detected_issue_types'].append({
                    'type': issue_type,
                    'confidence': confidence,
                    'matched_keywords': [kw for kw in keywords if kw in description_lower]
                })
                
                # Add services and diagnostics based on confidence
                if confidence > 0.3:  # Threshold for including suggestions
                    analysis['primary_services'].extend(mapping.get('primary_services', []))
                    analysis['secondary_services'].extend(mapping.get('secondary_services', []))
                    analysis['diagnostic_flags'].extend(mapping.get('diagnostic_flags', []))
                    analysis['log_sources'].extend(mapping.get('log_sources', []))
                    analysis['suggested_actions'].extend(mapping.get('common_patterns', []))
        
        # Remove duplicates and calculate overall confidence
        analysis['primary_services'] = list(set(analysis['primary_services']))
        analysis['secondary_services'] = list(set(analysis['secondary_services']))
        analysis['diagnostic_flags'] = list(set(analysis['diagnostic_flags']))
        analysis['log_sources'] = list(set(analysis['log_sources']))
        
        # Calculate overall confidence score
        if analysis['detected_issue_types']:
            analysis['confidence_score'] = max(item['confidence'] for item in analysis['detected_issue_types'])
        
        # Add troubleshooting commands
        analysis['troubleshooting_commands'] = self._get_troubleshooting_commands(analysis)
        
        return analysis
    
    def _get_issue_keywords(self, issue_type: str) -> List[str]:
        """Get keywords associated with an issue type"""
        keyword_mapping = {
            'authentication': ['login', 'auth', 'session', 'password', 'kratos', 'aal2', 'signin', 'logout'],
            'frontend': ['frontend', 'ui', 'dashboard', 'loading', 'react', 'build', 'page', 'display'],
            'api': ['api', 'backend', '500', 'error', 'flask', 'server', 'endpoint', 'request'],
            'ai_chat': ['bee', 'chat', 'ai', 'llm', 'model', 'ollama', 'chatbot', 'response'],
            'database': ['database', 'db', 'postgres', 'connection', 'sql', 'data', 'query'],
            'performance': ['slow', 'performance', 'memory', 'cpu', 'timeout', 'hang', 'freeze']
        }
        
        return keyword_mapping.get(issue_type, [])
    
    def _get_troubleshooting_commands(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate troubleshooting commands based on analysis"""
        commands = []
        
        # Service status check
        if analysis['primary_services']:
            commands.append("./manage_sting.sh status")
        
        # Service-specific log checks
        for service in analysis['primary_services'][:3]:  # Limit to top 3
            commands.append(f"./manage_sting.sh logs {service}")
        
        # Diagnostic honey jar creation
        if analysis['diagnostic_flags']:
            flags = ' '.join(analysis['diagnostic_flags'][:2])  # Limit to top 2 flags
            commands.append(f"./manage_sting.sh buzz collect {flags}")
        
        return commands
    
    def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get dependencies for a specific service"""
        service_info = self.get_service_info(service_name)
        if service_info:
            return service_info.get('dependencies', [])
        return []
    
    def get_all_services(self) -> List[str]:
        """Get list of all known services"""
        services = self.knowledge_data.get('services', {})
        return list(services.keys())
    
    def get_support_response_template(self, template_name: str, **kwargs) -> str:
        """
        Get a formatted response template for support scenarios
        
        Args:
            template_name: Name of the template
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted response string
        """
        templates = self.knowledge_data.get('bee_support_responses', {})
        template = templates.get(template_name)
        
        if not template:
            return f"I understand you're experiencing {kwargs.get('issue_type', 'an issue')}. Let me analyze this and help you."
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable {e} for template {template_name}")
            return template
    
    def generate_support_summary(self, analysis: Dict[str, Any], user_message: str) -> str:
        """
        Generate a conversational support summary based on analysis
        
        Args:
            analysis: Issue analysis results
            user_message: Original user message
            
        Returns:
            Formatted support response
        """
        if not analysis['detected_issue_types']:
            return ("I can help you troubleshoot this issue. Let me create a general diagnostic "
                   "bundle to gather information about your STING system.")
        
        # Get the highest confidence issue type
        primary_issue = max(analysis['detected_issue_types'], key=lambda x: x['confidence'])
        issue_type = primary_issue['type']
        confidence = primary_issue['confidence']
        
        # Generate response based on issue type
        if issue_type == 'authentication':
            response = ("I can see this appears to be an authentication issue. This typically involves "
                       f"the {', '.join(analysis['primary_services'])} services. ")
        elif issue_type == 'frontend':
            response = ("I understand you're having frontend/UI issues. This usually relates to "
                       f"the {', '.join(analysis['primary_services'])} services. ")
        elif issue_type == 'ai_chat':
            response = ("I notice this is about AI chat functionality. This involves "
                       f"the {', '.join(analysis['primary_services'])} services. ")
        elif issue_type == 'database':
            response = ("This appears to be a database-related issue. I'll focus on "
                       f"the {', '.join(analysis['primary_services'])} services. ")
        elif issue_type == 'performance':
            response = ("I can help with performance issues. This requires examining "
                       f"multiple services including {', '.join(analysis['primary_services'][:3])}. ")
        else:
            response = (f"I'll help you troubleshoot this {issue_type} issue. "
                       f"Let me examine the {', '.join(analysis['primary_services'])} services. ")
        
        # Add diagnostic information
        if analysis['diagnostic_flags']:
            flags_text = ', '.join(analysis['diagnostic_flags'])
            response += f"I'll create a targeted diagnostic bundle with these focuses: {flags_text}. "
        
        # Add confidence indicator
        if confidence > 0.8:
            response += "I'm quite confident about this analysis. "
        elif confidence > 0.5:
            response += "This analysis looks promising. "
        else:
            response += "Let me gather more information to better understand the issue. "
        
        return response
    
    def is_knowledge_loaded(self) -> bool:
        """Check if knowledge has been loaded successfully"""
        return bool(self.knowledge_data and self.loaded_at)
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of loaded knowledge"""
        if not self.is_knowledge_loaded():
            return {'status': 'not_loaded'}
        
        return {
            'status': 'loaded',
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'services_count': len(self.knowledge_data.get('services', {})),
            'issue_mappings_count': len(self.knowledge_data.get('issue_mappings', {})),
            'version': self.knowledge_data.get('metadata', {}).get('version', 'unknown')
        }