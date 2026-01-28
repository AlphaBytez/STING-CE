"""
Admin State Persistence - Database-backed admin initialization tracking
This ensures admin state survives container rebuilds and file system resets
"""

import logging
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()

class AdminState(Base):
    """Persistent tracking of admin initialization and password status"""
    __tablename__ = 'admin_state'
    
    id = Column(String(50), primary_key=True, default='default_admin')
    kratos_identity_id = Column(String(100), nullable=True)
    initialized_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    initial_password_changed = Column(Boolean, default=False)
    recovery_info = Column(Text, nullable=True)  # JSON for recovery data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_or_create_admin_state(db_session):
    """Get or create the admin state record"""
    try:
        admin_state = db_session.query(AdminState).filter_by(id='default_admin').first()
        if not admin_state:
            admin_state = AdminState(id='default_admin')
            db_session.add(admin_state)
            db_session.commit()
            logger.info("Created new admin state record in database")
        return admin_state
    except Exception as e:
        logger.error(f"Error getting admin state: {e}")
        return None

def mark_admin_initialized_db(db_session, kratos_identity_id):
    """Mark admin as initialized in database"""
    try:
        admin_state = get_or_create_admin_state(db_session)
        if admin_state:
            admin_state.kratos_identity_id = kratos_identity_id
            admin_state.initialized_at = datetime.utcnow()
            admin_state.updated_at = datetime.utcnow()
            db_session.commit()
            logger.info(f"Marked admin as initialized in database with ID: {kratos_identity_id}")
            return True
    except Exception as e:
        logger.error(f"Error marking admin initialized in DB: {e}")
    return False

def mark_password_changed_db(db_session):
    """Mark admin password as changed in database"""
    try:
        admin_state = get_or_create_admin_state(db_session)
        if admin_state:
            admin_state.password_changed_at = datetime.utcnow()
            admin_state.initial_password_changed = True
            admin_state.updated_at = datetime.utcnow()
            db_session.commit()
            logger.info("Marked admin password as changed in database")
            return True
    except Exception as e:
        logger.error(f"Error marking password changed in DB: {e}")
    return False

def is_admin_initialized_db(db_session):
    """Check if admin is initialized according to database"""
    try:
        admin_state = db_session.query(AdminState).filter_by(id='default_admin').first()
        if admin_state and admin_state.initialized_at:
            return True
    except Exception as e:
        logger.error(f"Error checking admin initialized status in DB: {e}")
    return False

def is_password_changed_db(db_session):
    """Check if initial password has been changed according to database"""
    try:
        admin_state = db_session.query(AdminState).filter_by(id='default_admin').first()
        if admin_state:
            return admin_state.initial_password_changed
    except Exception as e:
        logger.error(f"Error checking password changed status in DB: {e}")
    return False

def get_admin_kratos_id_db(db_session):
    """Get the Kratos identity ID from database"""
    try:
        admin_state = db_session.query(AdminState).filter_by(id='default_admin').first()
        if admin_state:
            return admin_state.kratos_identity_id
    except Exception as e:
        logger.error(f"Error getting admin Kratos ID from DB: {e}")
    return None