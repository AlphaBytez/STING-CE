"""
Temporary placeholder for honey jar models.
In the actual implementation, honey jars are managed by the knowledge service.
Report generators should use the knowledge service API instead of direct model access.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.sql import func
from app.database import db

class HoneyJar:
    """Placeholder - actual honey jars are in knowledge service"""
    pass

class HoneyJarDocument:
    """Placeholder - actual documents are in knowledge service"""
    pass