#!/usr/bin/env python3
"""
Hive Manager - Honey Jar Administration and Management
Handles creation, permissions, and lifecycle of knowledge bases
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import os

logger = logging.getLogger(__name__)

class HiveManager:
    """Manages Honey Jar knowledge bases and their permissions"""
    
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = data_dir
        self.honey_jars_file = os.path.join(data_dir, "honey_jars.json")
        self.permissions_file = os.path.join(data_dir, "permissions.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize with default data if files don't exist
        self._initialize_data()
    
    def _initialize_data(self):
        """Initialize default Honey Pots and permissions if files don't exist"""
        if not os.path.exists(self.honey_jars_file):
            default_honey_jars = [
                {
                    "id": "sting-platform-docs",
                    "name": "STING Platform Knowledge",
                    "description": "Core documentation and API references for STING platform",
                    "owner": "admin@sting.local",
                    "type": "public",
                    "status": "active",
                    "tags": ["documentation", "api", "platform"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "document_count": 42,
                    "embedding_count": 1250,
                    "permissions": {
                        "public_read": True,
                        "public_write": False,
                        "admin_only": False
                    },
                    "config": {
                        "chunk_size": 1000,
                        "overlap": 200,
                        "embedding_model": "all-MiniLM-L6-v2"
                    }
                },
                {
                    "id": "customer-support-faq",
                    "name": "Customer Support FAQ",
                    "description": "Frequently asked questions and troubleshooting guides",
                    "owner": "support@sting.local",
                    "type": "private",
                    "status": "active",
                    "tags": ["faq", "support", "troubleshooting"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "document_count": 18,
                    "embedding_count": 890,
                    "permissions": {
                        "public_read": False,
                        "public_write": False,
                        "admin_only": False,
                        "allowed_roles": ["support", "admin"]
                    },
                    "config": {
                        "chunk_size": 800,
                        "overlap": 150,
                        "embedding_model": "all-MiniLM-L6-v2"
                    }
                },
                {
                    "id": "marketing-materials",
                    "name": "Marketing Materials",
                    "description": "Product brochures, case studies, and marketing content",
                    "owner": "marketing@sting.local",
                    "type": "private",
                    "status": "draft",
                    "tags": ["marketing", "content", "brochures"],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "document_count": 25,
                    "embedding_count": 650,
                    "permissions": {
                        "public_read": False,
                        "public_write": False,
                        "admin_only": False,
                        "allowed_users": ["marketing@sting.local", "admin@sting.local"]
                    },
                    "config": {
                        "chunk_size": 1200,
                        "overlap": 250,
                        "embedding_model": "all-MiniLM-L6-v2"
                    }
                }
            ]
            
            with open(self.honey_jars_file, 'w') as f:
                json.dump(default_honey_jars, f, indent=2)
        
        if not os.path.exists(self.permissions_file):
            default_permissions = {
                "roles": {
                    "admin": {
                        "can_create": True,
                        "can_delete": True,
                        "can_edit_all": True,
                        "can_read_all": True
                    },
                    "support": {
                        "can_create": True,
                        "can_delete": False,
                        "can_edit_own": True,
                        "can_read_support": True
                    },
                    "user": {
                        "can_create": False,
                        "can_delete": False,
                        "can_edit_own": False,
                        "can_read_public": True
                    }
                },
                "default_permissions": {
                    "new_honey_jar": {
                        "type": "private",
                        "public_read": False,
                        "public_write": False
                    }
                }
            }
            
            with open(self.permissions_file, 'w') as f:
                json.dump(default_permissions, f, indent=2)
    
    async def create_honey_jar(
        self,
        name: str,
        description: str,
        owner: str,
        tags: List[str] = None,
        type: str = "private",
        permissions: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new Honey Jar knowledge base"""
        try:
            honey_jar_id = str(uuid.uuid4())
            
            honey_jar = {
                "id": honey_jar_id,
                "name": name,
                "description": description,
                "owner": owner,
                "type": type,
                "status": "active",
                "tags": tags or [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "document_count": 0,
                "embedding_count": 0,
                "permissions": permissions or {
                    "public_read": type == "public",
                    "public_write": False,
                    "admin_only": False
                },
                "config": {
                    "chunk_size": 1000,
                    "overlap": 200,
                    "embedding_model": "all-MiniLM-L6-v2"
                }
            }
            
            # Load existing honey pots
            honey_jars = self._load_honey_jars()
            honey_jars.append(honey_jar)
            
            # Save updated list
            with open(self.honey_jars_file, 'w') as f:
                json.dump(honey_jars, f, indent=2)
            
            logger.info(f"Created Honey Jar: {name} ({honey_jar_id})")
            return honey_jar
            
        except Exception as e:
            logger.error(f"Failed to create Honey Jar: {e}")
            raise
    
    async def get_honey_jar(self, honey_jar_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific Honey Jar by ID"""
        try:
            honey_jars = self._load_honey_jars()
            
            for honey_jar in honey_jars:
                if honey_jar["id"] == honey_jar_id:
                    return honey_jar
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Honey Jar {honey_jar_id}: {e}")
            raise
    
    async def list_honey_jars(self) -> List[Dict[str, Any]]:
        """List all Honey Pots"""
        try:
            return self._load_honey_jars()
        except Exception as e:
            logger.error(f"Failed to list Honey Pots: {e}")
            return []
    
    async def list_user_honey_jars(
        self,
        user: Dict[str, Any],
        type_filter: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List Honey Pots accessible to a specific user"""
        try:
            all_honey_jars = self._load_honey_jars()
            accessible_honey_jars = []
            
            for honey_jar in all_honey_jars:
                # Check if user has access
                if await self._user_can_access(user, honey_jar):
                    # Apply filters
                    if type_filter and honey_jar["type"] != type_filter:
                        continue
                    if tag_filter and tag_filter not in honey_jar["tags"]:
                        continue
                    
                    accessible_honey_jars.append(honey_jar)
            
            logger.info(f"User {user.get('email', 'unknown')} has access to {len(accessible_honey_jars)} Honey Pots")
            return accessible_honey_jars
            
        except Exception as e:
            logger.error(f"Failed to list user Honey Pots: {e}")
            return []
    
    async def update_honey_jar(
        self,
        honey_jar_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a Honey Jar's metadata"""
        try:
            honey_jars = self._load_honey_jars()
            
            for i, honey_jar in enumerate(honey_jars):
                if honey_jar["id"] == honey_jar_id:
                    # Apply updates
                    honey_jar.update(updates)
                    honey_jar["updated_at"] = datetime.utcnow().isoformat()
                    honey_jars[i] = honey_jar
                    
                    # Save changes
                    with open(self.honey_jars_file, 'w') as f:
                        json.dump(honey_jars, f, indent=2)
                    
                    logger.info(f"Updated Honey Jar: {honey_jar_id}")
                    return honey_jar
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update Honey Jar {honey_jar_id}: {e}")
            raise
    
    async def delete_honey_jar(self, honey_jar_id: str) -> bool:
        """Delete a Honey Jar"""
        try:
            honey_jars = self._load_honey_jars()
            
            for i, honey_jar in enumerate(honey_jars):
                if honey_jar["id"] == honey_jar_id:
                    del honey_jars[i]
                    
                    # Save changes
                    with open(self.honey_jars_file, 'w') as f:
                        json.dump(honey_jars, f, indent=2)
                    
                    logger.info(f"Deleted Honey Jar: {honey_jar_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete Honey Jar {honey_jar_id}: {e}")
            raise
    
    async def update_honey_jar_stats(self, honey_jar_id: str) -> None:
        """Update document and embedding counts for a Honey Jar"""
        try:
            # This would normally query the honeycomb manager for actual counts
            # For now, just increment the counts
            honey_jar = await self.get_honey_jar(honey_jar_id)
            if honey_jar:
                updates = {
                    "document_count": honey_jar.get("document_count", 0) + 1,
                    "embedding_count": honey_jar.get("embedding_count", 0) + 5  # Estimate
                }
                await self.update_honey_jar(honey_jar_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update stats for Honey Jar {honey_jar_id}: {e}")
    
    async def get_honey_jar_permissions(self, honey_jar_id: str) -> Dict[str, Any]:
        """Get permissions for a specific Honey Jar"""
        try:
            honey_jar = await self.get_honey_jar(honey_jar_id)
            if honey_jar:
                return honey_jar.get("permissions", {})
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get permissions for Honey Jar {honey_jar_id}: {e}")
            return {}
    
    async def set_honey_jar_permissions(
        self,
        honey_jar_id: str,
        permissions: Dict[str, Any]
    ) -> bool:
        """Set permissions for a specific Honey Jar"""
        try:
            updates = {"permissions": permissions}
            result = await self.update_honey_jar(honey_jar_id, updates)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to set permissions for Honey Jar {honey_jar_id}: {e}")
            return False
    
    def _load_honey_jars(self) -> List[Dict[str, Any]]:
        """Load Honey Pots from storage"""
        try:
            with open(self.honey_jars_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Failed to load Honey Pots: {e}")
            return []
    
    def _load_permissions(self) -> Dict[str, Any]:
        """Load permissions configuration from storage"""
        try:
            with open(self.permissions_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")
            return {}
    
    async def _user_can_access(self, user: Dict[str, Any], honey_jar: Dict[str, Any]) -> bool:
        """Check if user can access a specific Honey Jar"""
        try:
            permissions = honey_jar.get("permissions", {})
            user_email = user.get("email", "")
            user_role = user.get("role", "user")
            
            # Public read access
            if permissions.get("public_read", False):
                return True
            
            # Owner access
            if honey_jar.get("owner") == user_email:
                return True
            
            # Admin access
            if user_role == "admin":
                return True
            
            # Role-based access
            allowed_roles = permissions.get("allowed_roles", [])
            if user_role in allowed_roles:
                return True
            
            # User-specific access
            allowed_users = permissions.get("allowed_users", [])
            if user_email in allowed_users:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check user access: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall Hive statistics"""
        try:
            honey_jars = self._load_honey_jars()
            
            stats = {
                "total_honey_jars": len(honey_jars),
                "active_honey_jars": len([hp for hp in honey_jars if hp.get("status") == "active"]),
                "public_honey_jars": len([hp for hp in honey_jars if hp.get("type") == "public"]),
                "private_honey_jars": len([hp for hp in honey_jars if hp.get("type") == "private"]),
                "total_documents": sum(hp.get("document_count", 0) for hp in honey_jars),
                "total_embeddings": sum(hp.get("embedding_count", 0) for hp in honey_jars),
                "most_popular_tags": self._get_popular_tags(honey_jars),
                "last_updated": max((hp.get("updated_at", "") for hp in honey_jars), default="")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _get_popular_tags(self, honey_jars: List[Dict[str, Any]]) -> List[str]:
        """Get most popular tags across all Honey Pots"""
        tag_counts = {}
        
        for honey_jar in honey_jars:
            for tag in honey_jar.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count and return top 5
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, count in sorted_tags[:5]]