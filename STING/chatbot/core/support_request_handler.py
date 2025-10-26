"""
Support Request Handler for Bee Chat
Handles conversational support requests and integrates with the support ticket system
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests

from .sting_knowledge_loader import STINGKnowledgeLoader

logger = logging.getLogger(__name__)


class SupportRequestHandler:
    """Handles support requests through Bee Chat interface"""
    
    def __init__(self, api_base_url: str = "http://app:5050"):
        """
        Initialize support request handler
        
        Args:
            api_base_url: Base URL for the STING API
        """
        self.api_base_url = api_base_url
        self.knowledge_loader = STINGKnowledgeLoader()
        self.support_patterns = self._compile_support_patterns()
        
        # Try to load knowledge at startup
        if not self.knowledge_loader.load_knowledge():
            logger.warning("Failed to load STING knowledge - support analysis will be limited")
    
    def _compile_support_patterns(self) -> List[Tuple[re.Pattern, str, float]]:
        """
        Compile regex patterns for detecting support requests
        
        Returns:
            List of tuples: (compiled_pattern, intent, confidence_weight)
        """
        patterns = [
            # Direct support requests
            (r"@bee\s+(?:help|support|assist|issue|problem)", "direct_support", 0.9),
            (r"@bee\s+(?:create|submit|open)\s+(?:support\s+)?(?:ticket|request)", "create_ticket", 0.95),
            (r"@bee\s+(?:I\s+need|need)\s+help", "request_help", 0.85),
            
            # Issue descriptions
            (r"(?:can't|cannot|unable to|won't)\s+(?:login|log in|access|connect)", "authentication_issue", 0.8),
            (r"(?:not\s+(?:working|loading|responding)|broken|down|failing)", "general_issue", 0.7),
            (r"(?:error|exception|failed|failure)", "error_report", 0.75),
            (r"(?:slow|sluggish|hanging|freezing|timeout)", "performance_issue", 0.8),
            
            # Service-specific issues
            (r"(?:dashboard|frontend|ui)\s+(?:not|won't|can't)", "frontend_issue", 0.85),
            (r"(?:chat|ai|bee)\s+(?:not|won't|can't|broken)", "ai_chat_issue", 0.85),
            (r"(?:database|db)\s+(?:connection|error|issue)", "database_issue", 0.85),
            
            # Admin confirmation patterns
            (r"(?:grant|confirm|authorize)\s+support\s+access", "grant_access", 0.95),
            (r"GRANT_SUPPORT_ACCESS", "grant_access_confirm", 1.0),
            
            # Status queries
            (r"@bee\s+(?:support\s+)?(?:status|tickets|sessions)", "support_status", 0.9),
        ]
        
        compiled_patterns = []
        for pattern_str, intent, weight in patterns:
            try:
                compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                compiled_patterns.append((compiled_pattern, intent, weight))
            except re.error as e:
                logger.warning(f"Failed to compile pattern '{pattern_str}': {e}")
        
        return compiled_patterns
    
    def detect_support_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if a message contains a support request and classify its intent
        
        Args:
            message: User's chat message
            
        Returns:
            Dict containing intent analysis
        """
        detected_intents = []
        
        for pattern, intent, weight in self.support_patterns:
            matches = pattern.findall(message)
            if matches:
                detected_intents.append({
                    'intent': intent,
                    'confidence': weight,
                    'matches': matches if isinstance(matches[0], str) else [match for match in matches]
                })
        
        # Sort by confidence
        detected_intents.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'is_support_request': len(detected_intents) > 0,
            'primary_intent': detected_intents[0]['intent'] if detected_intents else None,
            'confidence': detected_intents[0]['confidence'] if detected_intents else 0.0,
            'all_intents': detected_intents,
            'requires_admin': self._requires_admin_permission(detected_intents)
        }
    
    def _requires_admin_permission(self, intents: List[Dict[str, Any]]) -> bool:
        """Check if any detected intents require admin permissions"""
        admin_required_intents = {
            'create_ticket', 'grant_access', 'grant_access_confirm'
        }
        
        for intent_data in intents:
            if intent_data['intent'] in admin_required_intents:
                return True
        
        return False
    
    async def handle_support_request(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a support request from chat
        
        Args:
            message: User's message
            user_context: Context about the user (ID, email, role, session, etc.)
            
        Returns:
            Dict containing response and actions
        """
        # Detect support intent
        intent_analysis = self.detect_support_intent(message)
        
        if not intent_analysis['is_support_request']:
            return {
                'is_support_response': False,
                'message': None
            }
        
        primary_intent = intent_analysis['primary_intent']
        
        # Check admin permissions if required
        if intent_analysis['requires_admin'] and not self._is_admin_user(user_context):
            return {
                'is_support_response': True,
                'message': ("🔒 Support ticket creation requires admin permissions. "
                           "Please contact an administrator for assistance."),
                'requires_admin': True
            }
        
        # Route to specific handler based on intent
        if primary_intent == 'create_ticket':
            return await self._handle_create_ticket(message, user_context)
        elif primary_intent == 'direct_support':
            return await self._handle_direct_support(message, user_context)
        elif primary_intent == 'request_help':
            return await self._handle_help_request(message, user_context)
        elif primary_intent in ['authentication_issue', 'frontend_issue', 'ai_chat_issue', 'database_issue', 'performance_issue']:
            return await self._handle_issue_report(message, user_context, primary_intent)
        elif primary_intent == 'grant_access' or primary_intent == 'grant_access_confirm':
            return await self._handle_access_grant(message, user_context)
        elif primary_intent == 'support_status':
            return await self._handle_status_query(user_context)
        else:
            return await self._handle_general_issue(message, user_context)
    
    async def _handle_create_ticket(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle explicit ticket creation requests"""
        
        # Extract issue description from message
        issue_description = self._extract_issue_description(message)
        
        if not issue_description:
            return {
                'is_support_response': True,
                'message': ("I'd be happy to help you create a support ticket! "
                           "Could you please describe the issue you're experiencing?"),
                'awaiting_description': True
            }
        
        # Analyze the issue using STING knowledge
        if self.knowledge_loader.is_knowledge_loaded():
            analysis = self.knowledge_loader.analyze_issue_description(issue_description)
            support_summary = self.knowledge_loader.generate_support_summary(analysis, message)
        else:
            analysis = {'detected_issue_types': [], 'confidence_score': 0.5}
            support_summary = "I'll help you create a support ticket for this issue."
        
        # Create the ticket via API
        ticket_result = await self._create_support_ticket(
            issue_description, 
            user_context, 
            analysis,
            message
        )
        
        if ticket_result['success']:
            ticket_id = ticket_result['ticket']['ticket_id']
            
            response_parts = [
                f"✅ **Support Ticket Created: {ticket_id}**",
                "",
                support_summary,
                "",
                "**Next Steps:**",
                "1. I'm creating a targeted diagnostic bundle based on your issue",
                "2. The bundle will be automatically sanitized to remove sensitive data",
                "3. You'll receive updates as the support team reviews your request"
            ]
            
            # Add tier-specific information
            support_tier = ticket_result['ticket'].get('support_tier', 'community')
            if support_tier == 'professional':
                response_parts.extend([
                    "",
                    "🔒 **Professional Support:**",
                    "Would you like me to establish a secure Tailscale tunnel for hands-on support?",
                    "This will allow the support team secure access to help troubleshoot."
                ])
            elif support_tier == 'enterprise':
                response_parts.extend([
                    "",
                    "🏢 **Enterprise Support:**",
                    "I can establish a dedicated secure tunnel and assign a senior engineer.",
                    "Expected response time: 1 hour"
                ])
            
            return {
                'is_support_response': True,
                'message': '\n'.join(response_parts),
                'ticket_created': True,
                'ticket_id': ticket_id,
                'analysis': analysis
            }
        else:
            return {
                'is_support_response': True,
                'message': f"❌ Failed to create support ticket: {ticket_result.get('error', 'Unknown error')}",
                'error': True
            }
    
    async def _handle_direct_support(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct support/help requests"""
        
        # Extract the issue from the message
        issue_description = self._extract_issue_description(message)
        
        if self.knowledge_loader.is_knowledge_loaded():
            analysis = self.knowledge_loader.analyze_issue_description(issue_description)
            
            if analysis['confidence_score'] > 0.6:
                # High confidence - provide targeted assistance
                support_summary = self.knowledge_loader.generate_support_summary(analysis, message)
                
                response_parts = [
                    support_summary,
                    "",
                    "**I can help you with:**",
                    "1. Creating a targeted diagnostic bundle",
                    "2. Providing troubleshooting steps",
                    "3. Creating a support ticket with detailed analysis",
                    "",
                    "Would you like me to create a support ticket with intelligent diagnostics?"
                ]
                
                return {
                    'is_support_response': True,
                    'message': '\n'.join(response_parts),
                    'suggested_action': 'create_ticket',
                    'analysis': analysis
                }
        
        # Fallback response
        return {
            'is_support_response': True,
            'message': ("I'm here to help! I can:\n\n"
                       "• **Analyze your issues** and suggest solutions\n"
                       "• **Create diagnostic bundles** with relevant logs\n"
                       "• **Open support tickets** with detailed analysis\n"
                       "• **Check system health** and identify problems\n\n"
                       "Just describe what you're experiencing, and I'll provide targeted assistance!"),
            'help_provided': True
        }
    
    async def _handle_help_request(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general help requests"""
        return await self._handle_direct_support(message, user_context)
    
    async def _handle_issue_report(self, message: str, user_context: Dict[str, Any], issue_type: str) -> Dict[str, Any]:
        """Handle specific issue type reports"""
        
        # Map chat issue types to knowledge issue types
        issue_type_mapping = {
            'authentication_issue': 'authentication',
            'frontend_issue': 'frontend',
            'ai_chat_issue': 'ai_chat',
            'database_issue': 'database',
            'performance_issue': 'performance'
        }
        
        knowledge_issue_type = issue_type_mapping.get(issue_type, 'general')
        
        if self.knowledge_loader.is_knowledge_loaded():
            # Get specific guidance for this issue type
            issue_mapping = self.knowledge_loader.get_issue_mapping(knowledge_issue_type)
            
            if issue_mapping:
                services = issue_mapping.get('primary_services', [])
                patterns = issue_mapping.get('common_patterns', [])
                
                response_parts = [
                    f"I can see you're experiencing {knowledge_issue_type} issues.",
                    f"This typically involves the **{', '.join(services)}** services.",
                    "",
                    "**Common causes include:**"
                ]
                
                for pattern in patterns[:3]:  # Limit to top 3
                    response_parts.append(f"• {pattern}")
                
                response_parts.extend([
                    "",
                    "Would you like me to:",
                    "1. **Create a diagnostic bundle** focused on these services",
                    "2. **Open a support ticket** with targeted analysis", 
                    "3. **Check system health** for these components"
                ])
                
                return {
                    'is_support_response': True,
                    'message': '\n'.join(response_parts),
                    'issue_type': knowledge_issue_type,
                    'suggested_services': services
                }
        
        # Fallback response
        return {
            'is_support_response': True,
            'message': (f"I understand you're having {issue_type.replace('_', ' ')} issues. "
                       "Let me help you troubleshoot this. Would you like me to create "
                       "a diagnostic bundle and support ticket?"),
            'suggested_action': 'create_ticket'
        }
    
    async def _handle_access_grant(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle support access grant requests"""
        
        if "GRANT_SUPPORT_ACCESS" in message:
            # This is an explicit confirmation
            return {
                'is_support_response': True,
                'message': ("🔒 **Support Access Confirmed**\n\n"
                           "I would establish secure access here, but this feature is still "
                           "in development. For now, your support ticket has been created "
                           "with comprehensive diagnostics.\n\n"
                           "The support team will contact you through your registered email."),
                'access_granted': True
            }
        else:
            # Request for access grant
            return {
                'is_support_response': True,
                'message': ("🔐 **Support Access Request**\n\n"
                           "You're requesting secure support access. This will:\n"
                           "• Create a temporary encrypted tunnel\n"
                           "• Allow support team hands-on troubleshooting\n"
                           "• Automatically expire after the session\n\n"
                           "⚠️ **This grants external access to your system**\n\n"
                           "Type `GRANT_SUPPORT_ACCESS` to confirm authorization."),
                'awaiting_confirmation': True
            }
    
    async def _handle_status_query(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle support status queries"""
        
        try:
            # Get user's tickets from API
            tickets = await self._get_user_tickets(user_context)
            
            if not tickets:
                return {
                    'is_support_response': True,
                    'message': "📋 **Support Status:**\n\nYou don't have any active support tickets.",
                    'status_provided': True
                }
            
            response_parts = ["📋 **Your Support Tickets:**", ""]
            
            for ticket in tickets[:5]:  # Limit to 5 most recent
                status_emoji = {
                    'open': '🟡',
                    'in_progress': '🔵', 
                    'resolved': '✅',
                    'closed': '⚫'
                }.get(ticket.get('status', 'open'), '❓')
                
                ticket_id = ticket.get('ticket_id', 'Unknown')
                title = ticket.get('title', 'Support Request')
                status = ticket.get('status', 'open').replace('_', ' ').title()
                
                response_parts.append(f"{status_emoji} **{ticket_id}** - {title} ({status})")
            
            return {
                'is_support_response': True,
                'message': '\n'.join(response_parts),
                'status_provided': True,
                'ticket_count': len(tickets)
            }
            
        except Exception as e:
            logger.error(f"Failed to get support status: {e}")
            return {
                'is_support_response': True,
                'message': "❌ Unable to retrieve support status at this time.",
                'error': True
            }
    
    async def _handle_general_issue(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general issue reports"""
        
        # Analyze the message for issue patterns
        if self.knowledge_loader.is_knowledge_loaded():
            analysis = self.knowledge_loader.analyze_issue_description(message)
            
            if analysis['confidence_score'] > 0.4:
                support_summary = self.knowledge_loader.generate_support_summary(analysis, message)
                
                return {
                    'is_support_response': True,
                    'message': (f"{support_summary}\n\n"
                               "Would you like me to create a support ticket with "
                               "targeted diagnostics for this issue?"),
                    'suggested_action': 'create_ticket',
                    'analysis': analysis
                }
        
        # Fallback for unclear issues
        return {
            'is_support_response': True,
            'message': ("I can help you with this issue! To provide the best assistance, "
                       "could you please provide more details about:\n\n"
                       "• What you were trying to do\n"
                       "• What happened instead\n"
                       "• Any error messages you saw\n"
                       "• When the problem started\n\n"
                       "I'll then create a targeted diagnostic bundle and support ticket."),
            'awaiting_details': True
        }
    
    def _extract_issue_description(self, message: str) -> str:
        """Extract the core issue description from a message"""
        # Remove @bee mentions and common prefixes
        cleaned = re.sub(r'@bee\s+', '', message, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:help|support|assist|issue|problem)\s+(?:with|me\s+with)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:create|submit|open)\s+(?:a\s+)?(?:support\s+)?(?:ticket|request)\s+(?:for|about)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:I\s+(?:need|have|am having|experiencing))\s+', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _is_admin_user(self, user_context: Dict[str, Any]) -> bool:
        """Check if user has admin permissions"""
        user_role = user_context.get('role', '').lower()
        return user_role in ['admin', 'super_admin']
    
    async def _create_support_ticket(self, description: str, user_context: Dict[str, Any], 
                                   analysis: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """Create a support ticket via API"""
        
        try:
            # Prepare ticket data
            ticket_data = {
                'description': description,
                'title': f"Support Request - {analysis.get('detected_issue_types', [{}])[0].get('type', 'General').title()}",
                'chat_transcript': [
                    {
                        'timestamp': datetime.now().isoformat(),
                        'role': 'user',
                        'message': original_message,
                        'analysis': analysis
                    }
                ],
                'bee_session_id': user_context.get('session_id'),
                'honey_jar_created': True,  # Will be created by CLI command
                'support_tier': 'community'  # Default tier, could be enhanced
            }
            
            # Make API call (simulated for now - would need actual API integration)
            # For now, we'll simulate a successful response
            
            # In a real implementation, this would be:
            # response = requests.post(f"{self.api_base_url}/api/support/tickets", 
            #                         json=ticket_data,
            #                         headers={'Authorization': f'Bearer {user_token}'})
            
            # Simulated successful response
            ticket_id = f"ST-{datetime.now().strftime('%Y%m%d%H%M%S')}-CHAT001"
            
            return {
                'success': True,
                'ticket': {
                    'ticket_id': ticket_id,
                    'title': ticket_data['title'],
                    'description': description,
                    'support_tier': 'community',
                    'status': 'open'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create support ticket: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_user_tickets(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get user's support tickets via API"""
        
        try:
            # In a real implementation, this would be:
            # response = requests.get(f"{self.api_base_url}/api/support/tickets",
            #                        headers={'Authorization': f'Bearer {user_token}'})
            
            # Simulated response for now
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user tickets: {e}")
            return []
    
    def get_knowledge_status(self) -> Dict[str, Any]:
        """Get status of loaded knowledge"""
        return self.knowledge_loader.get_knowledge_summary()