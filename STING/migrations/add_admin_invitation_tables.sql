-- Migration: Add admin invitation tables
-- Description: Creates tables for secure admin-to-admin invitation system
-- Date: 2025-09-04

-- Create admin_invitations table
CREATE TABLE IF NOT EXISTS admin_invitations (
    id VARCHAR(36) PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    invited_email VARCHAR(255) NOT NULL,
    invited_by_email VARCHAR(255) NOT NULL,
    invited_by_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    used_at TIMESTAMP NULL,
    used_by_identity VARCHAR(36) NULL,
    invitation_reason TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    metadata TEXT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_admin_invitations_token ON admin_invitations(token);
CREATE INDEX IF NOT EXISTS idx_admin_invitations_email ON admin_invitations(invited_email);
CREATE INDEX IF NOT EXISTS idx_admin_invitations_expires ON admin_invitations(expires_at);
CREATE INDEX IF NOT EXISTS idx_admin_invitations_used ON admin_invitations(used);

-- Create admin_invitation_audit table
CREATE TABLE IF NOT EXISTS admin_invitation_audit (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    invitation_id VARCHAR(36) NULL,
    invitation_token VARCHAR(64) NULL,
    actor_email VARCHAR(255) NULL,
    actor_identity_id VARCHAR(36) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    details TEXT NULL,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT NULL
);

-- Create indexes for audit table
CREATE INDEX IF NOT EXISTS idx_invitation_audit_timestamp ON admin_invitation_audit(timestamp);
CREATE INDEX IF NOT EXISTS idx_invitation_audit_event ON admin_invitation_audit(event_type);
CREATE INDEX IF NOT EXISTS idx_invitation_audit_invitation ON admin_invitation_audit(invitation_id);
CREATE INDEX IF NOT EXISTS idx_invitation_audit_actor ON admin_invitation_audit(actor_email);

-- Add comment to tables
COMMENT ON TABLE admin_invitations IS 'Stores admin invitation tokens for secure admin creation';
COMMENT ON TABLE admin_invitation_audit IS 'Audit log for all admin invitation activities';

-- Grant necessary permissions (adjust based on your database user setup)
-- GRANT SELECT, INSERT, UPDATE ON admin_invitations TO sting_app;
-- GRANT SELECT, INSERT ON admin_invitation_audit TO sting_app;