# app/models/recovery_code_models.py
"""
Recovery codes for account recovery when primary authentication methods are unavailable.
These codes provide a backup way to authenticate for users who lose access to their passkeys or TOTP.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import db
import secrets
import hashlib
import logging

logger = logging.getLogger(__name__)

class RecoveryCode(db.Model):
    """
    Recovery codes for backup authentication.

    These are one-time use codes that can be used when users lose access to their
    primary authentication methods (passkey, TOTP). Each user can have up to 10
    recovery codes at a time.
    """
    __tablename__ = 'recovery_codes'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)  # Kratos user ID
    user_email = Column(String(255), nullable=False, index=True)  # For audit purposes

    # Hashed code (never store plaintext)
    code_hash = Column(String(255), nullable=False, unique=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    # Usage tracking
    used_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    used_user_agent = Column(Text, nullable=True)

    # Security
    expires_at = Column(DateTime, nullable=False)  # Recovery codes expire after 1 year

    def __init__(self, user_id, user_email, code, expires_in_days=365):
        """Initialize recovery code with hashed storage"""
        self.user_id = user_id
        self.user_email = user_email
        self.code_hash = self._hash_code(code)
        self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    @staticmethod
    def _hash_code(code):
        """Hash a recovery code for secure storage"""
        # Use SHA-256 with salt for secure hashing
        salt = "sting_recovery_codes_salt_2024"  # Application-specific salt
        return hashlib.sha256(f"{salt}{code}".encode()).hexdigest()

    def verify_code(self, code):
        """Verify if the provided code matches this recovery code"""
        if self.is_used:
            return False
        if self.is_expired():
            return False

        return self.code_hash == self._hash_code(code)

    def mark_as_used(self, ip_address=None, user_agent=None):
        """Mark this recovery code as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_ip = ip_address
        self.used_user_agent = user_agent

        logger.info(f"Recovery code used by user {self.user_email} from IP {ip_address}")

    def is_expired(self):
        """Check if this recovery code has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """Check if this recovery code is still valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()

    @classmethod
    def generate_codes_for_user(cls, user_id, user_email, count=10):
        """
        Generate a set of recovery codes for a user.

        Returns:
            tuple: (list of RecoveryCode objects, list of plaintext codes)
        """
        # Remove any existing valid codes first
        cls.query.filter_by(user_id=user_id, is_used=False).delete()

        codes = []
        plaintext_codes = []

        for _ in range(count):
            # Generate cryptographically secure random code
            # Format: XXXX-XXXX-XXXX (12 characters, easy to type)
            code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"

            recovery_code = cls(user_id=user_id, user_email=user_email, code=code)
            codes.append(recovery_code)
            plaintext_codes.append(code)

        # Add to database
        for code in codes:
            db.session.add(code)

        logger.info(f"Generated {count} recovery codes for user {user_email}")
        return codes, plaintext_codes

    @classmethod
    def verify_user_code(cls, user_id, code, ip_address=None, user_agent=None):
        """
        Verify a recovery code for a user and mark it as used.

        Returns:
            bool: True if code is valid and successfully used, False otherwise
        """
        # Find matching code for this user
        recovery_code = cls.query.filter_by(
            user_id=user_id,
            is_used=False
        ).filter(
            cls.expires_at > datetime.utcnow()
        ).all()

        for code_obj in recovery_code:
            if code_obj.verify_code(code):
                code_obj.mark_as_used(ip_address, user_agent)
                db.session.commit()
                return True

        return False

    @classmethod
    def get_user_codes_status(cls, user_id):
        """
        Get status of recovery codes for a user.

        Returns:
            dict: Status information about user's recovery codes
        """
        total_codes = cls.query.filter_by(user_id=user_id).count()
        used_codes = cls.query.filter_by(user_id=user_id, is_used=True).count()
        valid_codes = cls.query.filter_by(user_id=user_id, is_used=False).filter(
            cls.expires_at > datetime.utcnow()
        ).count()
        expired_codes = cls.query.filter_by(user_id=user_id, is_used=False).filter(
            cls.expires_at <= datetime.utcnow()
        ).count()

        return {
            'total_codes': total_codes,
            'used_codes': used_codes,
            'valid_codes': valid_codes,
            'expired_codes': expired_codes,
            'has_codes': valid_codes > 0
        }

    @classmethod
    def cleanup_expired_codes(cls):
        """Remove expired recovery codes (cleanup utility)"""
        expired_count = cls.query.filter(cls.expires_at <= datetime.utcnow()).delete()
        db.session.commit()

        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired recovery codes")

        return expired_count

    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        result = {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired(),
            'is_valid': self.is_valid()
        }

        if include_sensitive:
            result.update({
                'used_ip': self.used_ip,
                'used_user_agent': self.used_user_agent
            })

        return result

    def __repr__(self):
        return f'<RecoveryCode {self.id} for user {self.user_email} (used: {self.is_used})>'