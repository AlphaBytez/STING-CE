-- Migration: Add missing tables for compliance, PII audit, and file management
-- Date: 2025-01-04
-- Description: Adds tables required by new models that weren't in the initial schema

-- Connect to sting_app database
\c sting_app;

-- =============================================
-- COMPLIANCE MANAGEMENT TABLES
-- =============================================

-- Compliance Profiles table
CREATE TABLE IF NOT EXISTS compliance_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    profile_type VARCHAR(100) NOT NULL, -- 'HIPAA', 'GDPR', 'CCPA', 'CUSTOM'
    enabled BOOLEAN DEFAULT TRUE,
    severity VARCHAR(50) DEFAULT 'medium',
    
    -- Configuration
    pattern_config JSONB DEFAULT '{}'::jsonb,
    rules JSONB DEFAULT '[]'::jsonb,
    exceptions JSONB DEFAULT '[]'::jsonb,
    
    -- Actions
    auto_redact BOOLEAN DEFAULT FALSE,
    auto_encrypt BOOLEAN DEFAULT FALSE,
    require_approval BOOLEAN DEFAULT FALSE,
    notification_settings JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- Custom Rules table
CREATE TABLE IF NOT EXISTS custom_rules (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES compliance_profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50), -- 'pattern', 'keyword', 'regex', 'ml_based'
    
    -- Rule definition
    pattern TEXT,
    keywords JSONB DEFAULT '[]'::jsonb,
    regex_pattern TEXT,
    ml_model_id VARCHAR(255),
    
    -- Matching configuration
    case_sensitive BOOLEAN DEFAULT FALSE,
    whole_words_only BOOLEAN DEFAULT FALSE,
    min_matches INTEGER DEFAULT 1,
    confidence_threshold DOUBLE PRECISION DEFAULT 0.8,
    
    -- Actions
    severity VARCHAR(50) DEFAULT 'medium',
    action VARCHAR(100) DEFAULT 'flag', -- 'flag', 'redact', 'encrypt', 'block'
    replacement_text TEXT,
    
    -- Metadata
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_rule_per_profile UNIQUE(profile_id, name)
);

-- Profile Pattern Mappings table
CREATE TABLE IF NOT EXISTS profile_pattern_mappings (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES compliance_profiles(id) ON DELETE CASCADE,
    pattern_id VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(100), -- 'ssn', 'credit_card', 'email', 'phone', 'custom'
    
    -- Mapping configuration
    enabled BOOLEAN DEFAULT TRUE,
    override_action VARCHAR(100), -- Override profile default action
    override_severity VARCHAR(50),
    custom_replacement TEXT,
    
    -- Statistics
    match_count INTEGER DEFAULT 0,
    last_matched TIMESTAMP WITHOUT TIME ZONE,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_pattern_per_profile UNIQUE(profile_id, pattern_id)
);

-- Compliance Events table
CREATE TABLE IF NOT EXISTS compliance_events (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES compliance_profiles(id),
    rule_id INTEGER REFERENCES custom_rules(id),
    
    -- Event details
    event_type VARCHAR(100) NOT NULL, -- 'detection', 'violation', 'remediation', 'exception'
    severity VARCHAR(50),
    
    -- Context
    source_type VARCHAR(100), -- 'document', 'api_call', 'database', 'message'
    source_id VARCHAR(255),
    user_id VARCHAR(255),
    
    -- Detection details
    matched_content TEXT,
    matched_pattern VARCHAR(255),
    confidence_score DOUBLE PRECISION,
    
    -- Action taken
    action_taken VARCHAR(100),
    remediation_status VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Profile Templates table
CREATE TABLE IF NOT EXISTS profile_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100), -- 'healthcare', 'finance', 'legal', 'general'
    
    -- Template definition
    base_profile_type VARCHAR(100),
    template_config JSONB NOT NULL,
    default_rules JSONB DEFAULT '[]'::jsonb,
    recommended_settings JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    description TEXT,
    version VARCHAR(50),
    is_certified BOOLEAN DEFAULT FALSE,
    certification_details JSONB,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- PII AUDIT TABLES
-- =============================================

-- PII Detection Records table
CREATE TABLE IF NOT EXISTS pii_detection_records (
    id SERIAL PRIMARY KEY,
    
    -- Detection context
    source_type VARCHAR(100) NOT NULL, -- 'document', 'api_request', 'database_field', 'log_entry'
    source_id VARCHAR(255),
    source_name VARCHAR(500),
    
    -- Detection details
    pii_type VARCHAR(100) NOT NULL, -- 'ssn', 'credit_card', 'email', 'phone', 'passport', 'driver_license'
    pii_category VARCHAR(100), -- 'financial', 'personal', 'health', 'government'
    detected_value TEXT, -- Encrypted/hashed
    masked_value TEXT, -- Redacted version for display
    
    -- Location
    location_details JSONB DEFAULT '{}'::jsonb, -- Line number, column, xpath, etc.
    context_snippet TEXT, -- Surrounding text for context
    
    -- Risk assessment
    risk_level VARCHAR(50) DEFAULT 'medium',
    confidence_score DOUBLE PRECISION,
    false_positive BOOLEAN DEFAULT FALSE,
    
    -- Processing
    detection_method VARCHAR(100), -- 'pattern', 'ml_model', 'rule_based'
    processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'reviewed', 'remediated', 'ignored'
    remediation_action VARCHAR(100), -- 'redacted', 'encrypted', 'deleted', 'none'
    
    -- Metadata
    detected_by VARCHAR(255),
    reviewed_by VARCHAR(255),
    review_notes TEXT,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PII Retention Policies table
CREATE TABLE IF NOT EXISTS pii_retention_policies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    
    -- Policy scope
    applies_to VARCHAR(100) NOT NULL, -- 'all', 'specific_types', 'specific_sources'
    pii_types JSONB DEFAULT '[]'::jsonb,
    source_types JSONB DEFAULT '[]'::jsonb,
    
    -- Retention rules
    retention_days INTEGER NOT NULL,
    grace_period_days INTEGER DEFAULT 30,
    
    -- Actions
    action_on_expiry VARCHAR(100) DEFAULT 'anonymize', -- 'delete', 'anonymize', 'archive'
    notification_days_before INTEGER DEFAULT 7,
    require_approval BOOLEAN DEFAULT TRUE,
    
    -- Exceptions
    exception_rules JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- PII Audit Logs table
CREATE TABLE IF NOT EXISTS pii_audit_logs (
    id SERIAL PRIMARY KEY,
    
    -- Action details
    action VARCHAR(100) NOT NULL, -- 'accessed', 'modified', 'deleted', 'exported', 'shared'
    action_result VARCHAR(50), -- 'success', 'failure', 'partial'
    
    -- Subject
    pii_record_id INTEGER REFERENCES pii_detection_records(id),
    data_subject_id VARCHAR(255), -- ID of person whose PII was accessed
    
    -- Actor
    user_id VARCHAR(255),
    user_role VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Context
    reason TEXT,
    legal_basis VARCHAR(100), -- 'consent', 'legitimate_interest', 'legal_obligation'
    access_context JSONB DEFAULT '{}'::jsonb,
    
    -- Compliance
    policy_id INTEGER REFERENCES pii_retention_policies(id),
    compliant BOOLEAN DEFAULT TRUE,
    violation_details TEXT,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PII Deletion Requests table
CREATE TABLE IF NOT EXISTS pii_deletion_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Request details
    data_subject_id VARCHAR(255),
    data_subject_email VARCHAR(255),
    request_type VARCHAR(100), -- 'deletion', 'correction', 'access', 'portability'
    
    -- Scope
    scope VARCHAR(100) DEFAULT 'all', -- 'all', 'specific_types', 'specific_timeframe'
    pii_types JSONB DEFAULT '[]'::jsonb,
    date_from TIMESTAMP WITHOUT TIME ZONE,
    date_to TIMESTAMP WITHOUT TIME ZONE,
    
    -- Processing
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'rejected'
    verification_status VARCHAR(50), -- 'unverified', 'verified', 'failed'
    verification_method VARCHAR(100),
    
    -- Results
    records_found INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    processing_notes TEXT,
    rejection_reason TEXT,
    
    -- Metadata
    requested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    processed_by VARCHAR(255)
);

-- PII Compliance Reports table
CREATE TABLE IF NOT EXISTS pii_compliance_reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Report details
    report_type VARCHAR(100), -- 'gdpr_audit', 'ccpa_disclosure', 'breach_notification'
    period_start TIMESTAMP WITHOUT TIME ZONE,
    period_end TIMESTAMP WITHOUT TIME ZONE,
    
    -- Statistics
    total_pii_records INTEGER DEFAULT 0,
    records_by_type JSONB DEFAULT '{}'::jsonb,
    records_by_risk JSONB DEFAULT '{}'::jsonb,
    
    -- Compliance metrics
    compliance_score DOUBLE PRECISION,
    violations_count INTEGER DEFAULT 0,
    remediation_count INTEGER DEFAULT 0,
    
    -- Report data
    summary TEXT,
    detailed_findings JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    
    -- Files
    report_file_path VARCHAR(500),
    report_format VARCHAR(50), -- 'pdf', 'json', 'csv'
    
    -- Metadata
    generated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(255),
    approved_by VARCHAR(255),
    approval_date TIMESTAMP WITHOUT TIME ZONE
);

-- =============================================
-- FILE MANAGEMENT TABLES
-- =============================================

-- File Assets table
CREATE TABLE IF NOT EXISTS file_assets (
    id SERIAL PRIMARY KEY,
    file_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    
    -- File information
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    file_extension VARCHAR(50),
    mime_type VARCHAR(255),
    
    -- Storage details
    storage_path VARCHAR(1000) NOT NULL,
    storage_type VARCHAR(50) DEFAULT 'local', -- 'local', 's3', 'azure', 'gcp'
    bucket_name VARCHAR(255),
    
    -- File metadata
    file_size BIGINT,
    checksum VARCHAR(255), -- SHA256 hash
    
    -- Encryption
    is_encrypted BOOLEAN DEFAULT FALSE,
    encryption_method VARCHAR(100),
    encryption_key_id VARCHAR(255),
    
    -- Classification
    classification VARCHAR(50) DEFAULT 'internal', -- 'public', 'internal', 'confidential', 'restricted'
    contains_pii BOOLEAN DEFAULT FALSE,
    pii_types JSONB DEFAULT '[]'::jsonb,
    
    -- Ownership
    owner_id VARCHAR(255),
    owner_type VARCHAR(50), -- 'user', 'system', 'organization'
    
    -- Versioning
    version INTEGER DEFAULT 1,
    parent_file_id UUID,
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP WITHOUT TIME ZONE,
    expires_at TIMESTAMP WITHOUT TIME ZONE
);

-- File Permissions table
CREATE TABLE IF NOT EXISTS file_permissions (
    id SERIAL PRIMARY KEY,
    file_id UUID REFERENCES file_assets(file_id) ON DELETE CASCADE,
    
    -- Permission target
    grantee_id VARCHAR(255) NOT NULL,
    grantee_type VARCHAR(50), -- 'user', 'group', 'role', 'public'
    
    -- Permission details
    permission_type VARCHAR(50), -- 'read', 'write', 'delete', 'share'
    can_read BOOLEAN DEFAULT FALSE,
    can_write BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_share BOOLEAN DEFAULT FALSE,
    
    -- Access control
    access_level VARCHAR(50) DEFAULT 'viewer', -- 'owner', 'editor', 'viewer'
    
    -- Time restrictions
    valid_from TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITHOUT TIME ZONE,
    
    -- Sharing details
    shared_by VARCHAR(255),
    share_link VARCHAR(500),
    link_password_hash VARCHAR(255),
    max_downloads INTEGER,
    download_count INTEGER DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_file_permission UNIQUE(file_id, grantee_id, grantee_type)
);

-- File Upload Sessions table
CREATE TABLE IF NOT EXISTS file_upload_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    
    -- Upload details
    file_id UUID,
    filename VARCHAR(500),
    file_size BIGINT,
    
    -- Chunked upload support
    total_chunks INTEGER DEFAULT 1,
    uploaded_chunks INTEGER DEFAULT 0,
    chunk_size INTEGER,
    
    -- Progress tracking
    bytes_uploaded BIGINT DEFAULT 0,
    upload_status VARCHAR(50) DEFAULT 'initiated', -- 'initiated', 'uploading', 'completed', 'failed', 'cancelled'
    
    -- Validation
    expected_checksum VARCHAR(255),
    validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB DEFAULT '[]'::jsonb,
    
    -- User context
    user_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Metadata
    upload_metadata JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    expires_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Compliance indexes
CREATE INDEX IF NOT EXISTS idx_compliance_profiles_enabled ON compliance_profiles(enabled);
CREATE INDEX IF NOT EXISTS idx_custom_rules_profile ON custom_rules(profile_id);
CREATE INDEX IF NOT EXISTS idx_compliance_events_profile ON compliance_events(profile_id);
CREATE INDEX IF NOT EXISTS idx_compliance_events_created ON compliance_events(created_at);

-- PII audit indexes
CREATE INDEX IF NOT EXISTS idx_pii_detection_source ON pii_detection_records(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_pii_detection_type ON pii_detection_records(pii_type);
CREATE INDEX IF NOT EXISTS idx_pii_detection_status ON pii_detection_records(processing_status);
CREATE INDEX IF NOT EXISTS idx_pii_audit_logs_record ON pii_audit_logs(pii_record_id);
CREATE INDEX IF NOT EXISTS idx_pii_audit_logs_user ON pii_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_pii_deletion_status ON pii_deletion_requests(status);

-- File management indexes
CREATE INDEX IF NOT EXISTS idx_file_assets_owner ON file_assets(owner_id);
CREATE INDEX IF NOT EXISTS idx_file_assets_classification ON file_assets(classification);
CREATE INDEX IF NOT EXISTS idx_file_permissions_file ON file_permissions(file_id);
CREATE INDEX IF NOT EXISTS idx_file_permissions_grantee ON file_permissions(grantee_id);
CREATE INDEX IF NOT EXISTS idx_file_upload_sessions_status ON file_upload_sessions(upload_status);
CREATE INDEX IF NOT EXISTS idx_file_upload_sessions_user ON file_upload_sessions(user_id);

-- =============================================
-- GRANT PERMISSIONS
-- =============================================

-- Grant all permissions to app_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Also grant to postgres for completeness
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- =============================================
-- UPDATE TRIGGERS
-- =============================================

-- Create update triggers for new tables that have updated_at columns
CREATE TRIGGER update_compliance_profiles_updated_at
    BEFORE UPDATE ON compliance_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_custom_rules_updated_at
    BEFORE UPDATE ON custom_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profile_pattern_mappings_updated_at
    BEFORE UPDATE ON profile_pattern_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profile_templates_updated_at
    BEFORE UPDATE ON profile_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pii_detection_records_updated_at
    BEFORE UPDATE ON pii_detection_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pii_retention_policies_updated_at
    BEFORE UPDATE ON pii_retention_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_assets_updated_at
    BEFORE UPDATE ON file_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_permissions_updated_at
    BEFORE UPDATE ON file_permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_upload_sessions_updated_at
    BEFORE UPDATE ON file_upload_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migration complete
SELECT 'Migration 001_add_missing_tables completed successfully' AS status;