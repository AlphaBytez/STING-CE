import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class Tool:
    """Base class for Bee tools"""
    
    def __init__(self, name: str, description: str, required_role: str = "end_user"):
        self.name = name
        self.description = description
        self.required_role = required_role
        self.enabled = True
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the tool with given input"""
        raise NotImplementedError("Tool must implement execute method")
    
    def can_access(self, user_role: str) -> bool:
        """Check if user role can access this tool"""
        role_hierarchy = {
            "end_user": 0,
            "support": 1,
            "admin": 2
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(self.required_role, 0)
        
        return user_level >= required_level

class SearchTool(Tool):
    """Tool for searching documents and data"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="Search through documents, databases, and knowledge base",
            required_role="end_user"
        )
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute search"""
        try:
            # This is a placeholder - integrate with actual search service
            results = []
            
            # Simulate search based on input
            if "sales" in input_data.lower():
                results = [
                    {"title": "Q4 Sales Report", "snippet": "Sales increased by 15% in Q4...", "relevance": 0.95},
                    {"title": "Sales Dashboard Guide", "snippet": "How to use the sales dashboard...", "relevance": 0.85}
                ]
            elif "inventory" in input_data.lower():
                results = [
                    {"title": "Current Inventory Status", "snippet": "Total inventory value: $1.2M...", "relevance": 0.92},
                    {"title": "Inventory Management Best Practices", "snippet": "Tips for optimizing inventory...", "relevance": 0.78}
                ]
            
            return {
                "name": self.name,
                "status": "success",
                "query": input_data,
                "result_count": len(results),
                "results": results,
                "summary": f"Found {len(results)} results for '{input_data}'",
                "context": {
                    "search_performed": True,
                    "search_query": input_data
                }
            }
            
        except Exception as e:
            logger.error(f"Search tool error: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "summary": "Search failed"
            }

class AnalyticsTool(Tool):
    """Tool for generating analytics and reports"""
    
    def __init__(self):
        super().__init__(
            name="analytics",
            description="Generate analytics reports and data visualizations",
            required_role="end_user"
        )
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute analytics"""
        try:
            # Parse analytics request
            report_type = "summary"
            
            if "detailed" in input_data.lower():
                report_type = "detailed"
            elif "sales" in input_data.lower():
                report_type = "sales"
            elif "inventory" in input_data.lower():
                report_type = "inventory"
            
            # Generate mock analytics
            analytics_data = {
                "summary": {
                    "total_revenue": "$2.5M",
                    "growth_rate": "+15%",
                    "active_customers": 1250,
                    "top_products": ["Product A", "Product B", "Product C"]
                },
                "sales": {
                    "daily_average": "$85K",
                    "monthly_total": "$2.5M",
                    "conversion_rate": "3.2%",
                    "average_order_value": "$125"
                },
                "inventory": {
                    "total_value": "$1.2M",
                    "turnover_rate": "4.5",
                    "low_stock_items": 23,
                    "overstocked_items": 8
                }
            }
            
            report_data = analytics_data.get(report_type, analytics_data["summary"])
            
            return {
                "name": self.name,
                "status": "success",
                "report_type": report_type,
                "data": report_data,
                "summary": f"Generated {report_type} analytics report",
                "context": {
                    "analytics_generated": True,
                    "report_type": report_type
                }
            }
            
        except Exception as e:
            logger.error(f"Analytics tool error: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "summary": "Analytics generation failed"
            }

class DatabaseQueryTool(Tool):
    """Tool for querying databases (admin/support only)"""
    
    def __init__(self):
        super().__init__(
            name="database_query",
            description="Query databases directly for advanced data retrieval",
            required_role="support"
        )
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute database query"""
        try:
            # Safety check - prevent dangerous queries
            dangerous_keywords = ["drop", "delete", "truncate", "update", "insert"]
            query_lower = input_data.lower()
            
            for keyword in dangerous_keywords:
                if keyword in query_lower:
                    return {
                        "name": self.name,
                        "status": "error",
                        "error": f"Query contains restricted keyword: {keyword}",
                        "summary": "Query rejected for safety"
                    }
            
            # This is a placeholder - integrate with actual database
            # In production, use parameterized queries and proper access control
            
            mock_results = [
                {"id": 1, "name": "Sample Record", "value": 100},
                {"id": 2, "name": "Another Record", "value": 200}
            ]
            
            return {
                "name": self.name,
                "status": "success",
                "query": input_data,
                "row_count": len(mock_results),
                "results": mock_results,
                "summary": f"Query returned {len(mock_results)} rows",
                "context": {
                    "database_queried": True,
                    "query_type": "select"
                }
            }
            
        except Exception as e:
            logger.error(f"Database query tool error: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "summary": "Database query failed"
            }

class NotificationTool(Tool):
    """Tool for sending notifications"""
    
    def __init__(self):
        super().__init__(
            name="notify",
            description="Send notifications via email, SMS, or in-app messaging",
            required_role="support"
        )
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Send notification"""
        try:
            # Parse notification request
            # Expected format: "notify user@example.com: Your order is ready"
            
            parts = input_data.split(":", 1)
            if len(parts) != 2:
                return {
                    "name": self.name,
                    "status": "error",
                    "error": "Invalid format. Use: notify recipient: message",
                    "summary": "Notification failed"
                }
            
            recipient = parts[0].replace("notify", "").strip()
            message = parts[1].strip()
            
            # This is a placeholder - integrate with messaging service
            notification_id = f"notif_{datetime.now().timestamp()}"
            
            return {
                "name": self.name,
                "status": "success",
                "notification_id": notification_id,
                "recipient": recipient,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "summary": f"Notification sent to {recipient}",
                "context": {
                    "notification_sent": True,
                    "recipient": recipient
                }
            }
            
        except Exception as e:
            logger.error(f"Notification tool error: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "summary": "Notification failed"
            }

class SystemConfigTool(Tool):
    """Tool for system configuration (admin only)"""
    
    def __init__(self):
        super().__init__(
            name="system_config",
            description="View and modify system configuration",
            required_role="admin"
        )
    
    async def execute(self, input_data: str, context: Dict[str, Any], user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute system configuration"""
        try:
            # Parse config request
            if input_data.startswith("get "):
                config_key = input_data[4:].strip()
                # Placeholder for getting config
                return {
                    "name": self.name,
                    "status": "success",
                    "action": "get",
                    "key": config_key,
                    "value": "placeholder_value",
                    "summary": f"Retrieved config: {config_key}",
                    "context": {
                        "config_accessed": True,
                        "action": "get"
                    }
                }
            elif input_data.startswith("set "):
                # Parse set command
                parts = input_data[4:].split("=", 1)
                if len(parts) != 2:
                    return {
                        "name": self.name,
                        "status": "error",
                        "error": "Invalid format. Use: set key=value",
                        "summary": "Configuration update failed"
                    }
                
                config_key = parts[0].strip()
                config_value = parts[1].strip()
                
                return {
                    "name": self.name,
                    "status": "success",
                    "action": "set",
                    "key": config_key,
                    "value": config_value,
                    "summary": f"Updated config: {config_key}",
                    "context": {
                        "config_modified": True,
                        "action": "set"
                    }
                }
            else:
                return {
                    "name": self.name,
                    "status": "error",
                    "error": "Invalid command. Use: get <key> or set <key>=<value>",
                    "summary": "Invalid configuration command"
                }
                
        except Exception as e:
            logger.error(f"System config tool error: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "summary": "System configuration failed"
            }

class ToolManager:
    """Manages available tools for Bee"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = {}
        
        # Register default tools
        self._register_default_tools()
        
        # Load enabled tools from config
        self.enabled_tools = set(config.get('enabled_tools', [
            'search', 'analytics', 'database_query', 'notify', 'system_config'
        ]))
    
    def _register_default_tools(self):
        """Register all default tools"""
        default_tools = [
            SearchTool(),
            AnalyticsTool(),
            DatabaseQueryTool(),
            NotificationTool(),
            SystemConfigTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def is_tool_available(self, tool_name: str, user_role: str = "end_user") -> bool:
        """Check if a tool is available for the user"""
        if tool_name not in self.tools:
            return False
        
        if tool_name not in self.enabled_tools:
            return False
        
        tool = self.tools[tool_name]
        return tool.can_access(user_role)
    
    def get_available_tools(self, user_role: str = "end_user") -> List[Dict[str, str]]:
        """Get list of available tools for user role"""
        available = []
        
        for tool_name, tool in self.tools.items():
            if tool_name in self.enabled_tools and tool.can_access(user_role):
                available.append({
                    "name": tool.name,
                    "description": tool.description,
                    "required_role": tool.required_role
                })
        
        return available
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools (admin view)"""
        all_tools = []
        
        for tool_name, tool in self.tools.items():
            all_tools.append({
                "name": tool.name,
                "description": tool.description,
                "required_role": tool.required_role,
                "enabled": tool_name in self.enabled_tools
            })
        
        return all_tools
    
    async def execute_tool(
        self,
        tool_name: str,
        input_data: str,
        context: Dict[str, Any],
        user_info: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Execute a tool"""
        if tool_name not in self.tools:
            logger.error(f"Tool not found: {tool_name}")
            return None
        
        if tool_name not in self.enabled_tools:
            logger.error(f"Tool not enabled: {tool_name}")
            return None
        
        tool = self.tools[tool_name]
        
        # Check user access
        user_role = user_info.get('role', 'end_user') if user_info else 'end_user'
        if not tool.can_access(user_role):
            logger.warning(f"User {user_role} cannot access tool {tool_name}")
            return {
                "name": tool_name,
                "status": "error",
                "error": "Insufficient permissions",
                "summary": f"Access denied to {tool_name}"
            }
        
        try:
            # Execute tool
            result = await tool.execute(input_data, context, user_info)
            
            # Add execution metadata
            result['executed_at'] = datetime.now().isoformat()
            result['executed_by'] = user_info.get('id', 'unknown') if user_info else 'unknown'
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {str(e)}")
            return {
                "name": tool_name,
                "status": "error",
                "error": str(e),
                "summary": f"Tool {tool_name} failed to execute"
            }
    
    def update_enabled_tools(self, tool_names: List[str]):
        """Update list of enabled tools"""
        self.enabled_tools = set(tool_names)
        logger.info(f"Updated enabled tools: {tool_names}")
    
    def is_healthy(self) -> bool:
        """Health check for tool manager"""
        try:
            # Check if we have tools registered
            return len(self.tools) > 0
        except:
            return False