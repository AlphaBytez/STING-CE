"""
Profile Manager - Core business logic for profile management.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.file_service import ProfileFileService
from database import get_db_session
from models.profile_models import UserProfile, ProfileExtension, create_profile_tables
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ProfileManager:
    """Manages user profiles and related operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize profile manager with configuration."""
        self.config = config
        self.file_service = ProfileFileService()
        
        # Initialize database tables
        try:
            self._init_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def _init_database(self):
        """Initialize profile database tables."""
        try:
            with get_db_session() as session:
                # Create tables if they don't exist
                create_profile_tables(session.bind)
                logger.info("Profile database tables initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile data dictionary or None
        """
        try:
            with get_db_session() as session:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if not profile:
                    return None
                
                # Get profile picture URL if exists
                profile_data = profile.to_dict()
                
                # Add profile picture URL
                if profile.profile_picture_file_id:
                    profile_data['profile_picture_url'] = f"/api/files/{profile.profile_picture_file_id}"
                
                return profile_data
                
        except Exception as e:
            logger.error(f"Error getting profile for user {user_id}: {e}")
            return None
    
    def create_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user profile.
        
        Args:
            user_id: User ID
            profile_data: Profile data
            
        Returns:
            Result dictionary
        """
        try:
            with get_db_session() as session:
                # Check if profile already exists
                existing = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if existing:
                    return {
                        'success': False,
                        'error': 'Profile already exists'
                    }
                
                # Create new profile
                profile = UserProfile(
                    user_id=user_id,
                    display_name=profile_data.get('display_name'),
                    first_name=profile_data.get('first_name'),
                    last_name=profile_data.get('last_name'),
                    bio=profile_data.get('bio'),
                    location=profile_data.get('location'),
                    website=profile_data.get('website'),
                    phone=profile_data.get('phone'),
                    timezone=profile_data.get('timezone'),
                    language=profile_data.get('language', 'en'),
                    preferences=profile_data.get('preferences', {}),
                    privacy_settings=profile_data.get('privacy_settings', {})
                )
                
                session.add(profile)
                session.commit()
                
                logger.info(f"Created profile for user {user_id}")
                
                return {
                    'success': True,
                    'profile_id': str(profile.id),
                    'profile': profile.to_dict()
                }
                
        except Exception as e:
            logger.error(f"Error creating profile for user {user_id}: {e}")
            return {
                'success': False,
                'error': f'Failed to create profile: {str(e)}'
            }
    
    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            profile_data: Updated profile data
            
        Returns:
            Result dictionary
        """
        try:
            with get_db_session() as session:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if not profile:
                    # Create profile if it doesn't exist
                    return self.create_profile(user_id, profile_data)
                
                # Update fields
                updatable_fields = [
                    'display_name', 'first_name', 'last_name', 'bio',
                    'location', 'website', 'phone', 'timezone', 'language'
                ]
                
                for field in updatable_fields:
                    if field in profile_data:
                        setattr(profile, field, profile_data[field])
                
                # Update preferences and privacy settings
                if 'preferences' in profile_data:
                    profile.preferences = {
                        **(profile.preferences or {}),
                        **profile_data['preferences']
                    }
                
                if 'privacy_settings' in profile_data:
                    profile.privacy_settings = {
                        **(profile.privacy_settings or {}),
                        **profile_data['privacy_settings']
                    }
                
                profile.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"Updated profile for user {user_id}")
                
                return {
                    'success': True,
                    'profile': profile.to_dict()
                }
                
        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return {
                'success': False,
                'error': f'Failed to update profile: {str(e)}'
            }
    
    def upload_profile_picture(self, user_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload profile picture.
        
        Args:
            user_id: User ID
            file_data: Image file data
            filename: Original filename
            
        Returns:
            Result dictionary
        """
        try:
            # Upload file using file service
            upload_result = self.file_service.upload_profile_picture(file_data, filename, user_id)
            
            if not upload_result['success']:
                return upload_result
            
            # Update profile with file ID
            with get_db_session() as session:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if not profile:
                    # Create profile if it doesn't exist
                    profile = UserProfile(user_id=user_id)
                    session.add(profile)
                
                # Remove old profile picture if exists
                if profile.profile_picture_file_id:
                    old_file_id = profile.profile_picture_file_id
                    # Delete old file (async operation)
                    try:
                        self.file_service.file_service.delete_file(old_file_id, user_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete old profile picture {old_file_id}: {e}")
                
                profile.profile_picture_file_id = upload_result['file_id']
                profile.updated_at = datetime.utcnow()
                session.commit()
                
                return {
                    'success': True,
                    'file_id': upload_result['file_id'],
                    'profile_picture_url': f"/api/files/{upload_result['file_id']}"
                }
                
        except Exception as e:
            logger.error(f"Error uploading profile picture for user {user_id}: {e}")
            return {
                'success': False,
                'error': f'Failed to upload profile picture: {str(e)}'
            }
    
    def get_profile_picture(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's profile picture.
        
        Args:
            user_id: User ID
            
        Returns:
            File data dictionary or None
        """
        try:
            with get_db_session() as session:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if not profile or not profile.profile_picture_file_id:
                    return None
                
                # Get file from file service
                return self.file_service.file_service.download_file(
                    profile.profile_picture_file_id, user_id
                )
                
        except Exception as e:
            logger.error(f"Error getting profile picture for user {user_id}: {e}")
            return None
    
    def delete_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Soft delete user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            Result dictionary
        """
        try:
            with get_db_session() as session:
                profile = session.query(UserProfile).filter(
                    UserProfile.user_id == user_id,
                    UserProfile.deleted_at.is_(None)
                ).first()
                
                if not profile:
                    return {
                        'success': False,
                        'error': 'Profile not found'
                    }
                
                # Soft delete
                profile.deleted_at = datetime.utcnow()
                session.commit()
                
                # Delete profile picture if exists
                if profile.profile_picture_file_id:
                    try:
                        self.file_service.file_service.delete_file(
                            profile.profile_picture_file_id, user_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete profile picture: {e}")
                
                logger.info(f"Deleted profile for user {user_id}")
                
                return {
                    'success': True,
                    'message': 'Profile deleted successfully'
                }
                
        except Exception as e:
            logger.error(f"Error deleting profile for user {user_id}: {e}")
            return {
                'success': False,
                'error': f'Failed to delete profile: {str(e)}'
            }
    
    def search_profiles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search profiles by display name or name.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of profile dictionaries
        """
        try:
            with get_db_session() as session:
                profiles = session.query(UserProfile).filter(
                    UserProfile.deleted_at.is_(None)
                ).filter(
                    UserProfile.display_name.ilike(f'%{query}%') |
                    UserProfile.first_name.ilike(f'%{query}%') |
                    UserProfile.last_name.ilike(f'%{query}%')
                ).limit(limit).all()
                
                return [profile.to_dict(include_private=False) for profile in profiles]
                
        except Exception as e:
            logger.error(f"Error searching profiles: {e}")
            return []
    
    def health_check(self) -> bool:
        """
        Check service health.
        
        Returns:
            True if healthy
        """
        try:
            with get_db_session() as session:
                # Simple query to test database connectivity
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False