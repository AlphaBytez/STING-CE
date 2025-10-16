-- PII Audit Tables Migration
-- Creates tables for PII detection audit logging and compliance retention
-- Run this migration to add PII audit capabilities to STING

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- PII Detection Records Table
-- Stores metadata about detected PII without storing actual values
CREATE TABLE pii_detection_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    detection_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Source information
    document_id VARCHAR(100),
    honey_jar_id VARCHAR(100),
    user_id VARCHAR(100) NOT NULL,
    
    -- Detection metadata
    pii_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('high', 'medium', 'low')),
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    
    -- Position and context (hashed for security)
    start_position INTEGER NOT NULL,
    end_position INTEGER NOT NULL,
    context_hash VARCHAR(64),
    value_hash VARCHAR(64),
    
    -- Compliance and retention
    compliance_frameworks JSONB,
    detection_mode VARCHAR(20) NOT NULL CHECK (detection_mode IN ('general', 'medical', 'legal', 'financial')),
    
    -- Timestamps
    detected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE
);

-- Indexes for pii_detection_records
CREATE INDEX idx_pii_user_detected ON pii_detection_records (user_id, detected_at);
CREATE INDEX idx_pii_type_risk ON pii_detection_records (pii_type, risk_level);
CREATE INDEX idx_pii_expires ON pii_detection_records (expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_pii_compliance ON pii_detection_records USING GIN (compliance_frameworks);
CREATE INDEX idx_pii_honey_jar ON pii_detection_records (honey_jar_id) WHERE honey_jar_id IS NOT NULL;
CREATE INDEX idx_pii_deleted ON pii_detection_records (deleted_at) WHERE deleted_at IS NOT NULL;

-- PII Retention Policies Table
-- Configurable retention policies for different PII types and compliance frameworks
CREATE TABLE pii_retention_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Policy identification
    policy_name VARCHAR(100) UNIQUE NOT NULL,
    compliance_framework VARCHAR(50) NOT NULL,
    pii_type VARCHAR(50), -- NULL for default framework policy
    
    -- Retention settings
    retention_days INTEGER NOT NULL CHECK (retention_days >= 0),
    auto_deletion_enabled BOOLEAN DEFAULT TRUE,
    grace_period_days INTEGER DEFAULT 30 CHECK (grace_period_days >= 0),
    immediate_deletion_on_request BOOLEAN DEFAULT FALSE,
    
    -- Policy metadata
    description TEXT,
    legal_basis TEXT,
    created_by VARCHAR(100) NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    effective_date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    UNIQUE(compliance_framework, pii_type)
);

-- Indexes for pii_retention_policies
CREATE INDEX idx_retention_framework_type ON pii_retention_policies (compliance_framework, pii_type);
CREATE INDEX idx_retention_active ON pii_retention_policies (active, effective_date);

-- PII Audit Log Table
-- Comprehensive audit log for all PII-related operations
CREATE TABLE pii_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event information
    event_type VARCHAR(50) NOT NULL,
    event_description TEXT,
    
    -- Related records
    detection_record_id UUID REFERENCES pii_detection_records(id) ON DELETE SET NULL,
    
    -- User and system context
    user_id VARCHAR(100),
    system_component VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    
    -- Event metadata
    event_data JSONB,
    compliance_impact VARCHAR(20) CHECK (compliance_impact IN ('high', 'medium', 'low', 'none')),
    
    -- Timestamps
    event_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for pii_audit_logs
CREATE INDEX idx_audit_event_time ON pii_audit_logs (event_type, event_timestamp);
CREATE INDEX idx_audit_user ON pii_audit_logs (user_id, event_timestamp) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_detection ON pii_audit_logs (detection_record_id) WHERE detection_record_id IS NOT NULL;
CREATE INDEX idx_audit_compliance ON pii_audit_logs (compliance_impact, event_timestamp) WHERE compliance_impact IS NOT NULL;

-- PII Deletion Requests Table
-- Tracks deletion requests for GDPR/CCPA compliance
CREATE TABLE pii_deletion_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request information
    request_type VARCHAR(30) NOT NULL CHECK (request_type IN ('gdpr_erasure', 'ccpa_deletion', 'manual')),
    requester_email VARCHAR(255) NOT NULL,
    user_id VARCHAR(100),
    
    -- Request details
    reason TEXT,
    scope VARCHAR(50) NOT NULL CHECK (scope IN ('all_data', 'specific_types', 'date_range')),
    specific_pii_types JSONB,
    date_range_start TIMESTAMP WITHOUT TIME ZONE,
    date_range_end TIMESTAMP WITHOUT TIME ZONE,
    
    -- Processing status
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'rejected')),
    processed_at TIMESTAMP WITHOUT TIME ZONE,
    processed_by VARCHAR(100),
    
    -- Results
    records_deleted INTEGER DEFAULT 0,
    deletion_report JSONB,
    
    -- Timestamps
    requested_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    deadline_at TIMESTAMP WITHOUT TIME ZONE,
    
    -- Verification
    verification_token VARCHAR(100),
    verified_at TIMESTAMP WITHOUT TIME ZONE
);

-- Indexes for pii_deletion_requests
CREATE INDEX idx_deletion_status ON pii_deletion_requests (status, requested_at);
CREATE INDEX idx_deletion_deadline ON pii_deletion_requests (deadline_at) WHERE deadline_at IS NOT NULL;
CREATE INDEX idx_deletion_user ON pii_deletion_requests (user_id) WHERE user_id IS NOT NULL;

-- PII Compliance Reports Table
-- Periodic compliance reports for audit purposes
CREATE TABLE pii_compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Report metadata
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('weekly', 'monthly', 'quarterly', 'annual', 'ad_hoc')),
    compliance_framework VARCHAR(50) NOT NULL,
    reporting_period_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    reporting_period_end TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    
    -- Report content
    total_detections INTEGER DEFAULT 0,
    high_risk_detections INTEGER DEFAULT 0,
    records_deleted INTEGER DEFAULT 0,
    deletion_requests_processed INTEGER DEFAULT 0,
    
    -- Detailed statistics
    statistics JSONB,
    compliance_violations JSONB,
    
    -- Report file
    report_file_path VARCHAR(500),
    report_file_hash VARCHAR(64),
    
    -- Generation info
    generated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    generated_by VARCHAR(100) NOT NULL,
    generation_time_seconds INTEGER,
    
    -- Constraints
    CHECK (reporting_period_end > reporting_period_start)
);

-- Indexes for pii_compliance_reports
CREATE INDEX idx_compliance_framework_period ON pii_compliance_reports (compliance_framework, reporting_period_start);
CREATE INDEX idx_compliance_generated ON pii_compliance_reports (generated_at);

-- Create update trigger function for timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add update triggers to tables with updated_at columns
CREATE TRIGGER update_pii_detection_records_updated_at 
    BEFORE UPDATE ON pii_detection_records 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pii_retention_policies_updated_at 
    BEFORE UPDATE ON pii_retention_policies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default retention policies based on compliance frameworks
INSERT INTO pii_retention_policies (policy_name, compliance_framework, pii_type, retention_days, description, legal_basis, created_by) VALUES
-- HIPAA Policies
('HIPAA Default', 'hipaa', NULL, 2555, 'Default HIPAA retention - 7 years', 'HIPAA medical records retention requirements', 'system'),
('HIPAA Prescription Records', 'hipaa', 'prescription_info', 1825, 'DEA prescription records - 5 years', 'DEA prescription record requirements', 'system'),
('HIPAA Lab Results', 'hipaa', 'lab_result', 1825, 'Laboratory results - 5 years', 'HIPAA laboratory record requirements', 'system'),

-- GDPR Policies  
('GDPR Default', 'gdpr', NULL, 1095, 'Default GDPR retention - 3 years', 'GDPR data minimization principle', 'system'),
('GDPR Employment Records', 'gdpr', 'person_name', 2190, 'Employment context names - 6 years', 'GDPR employment record retention', 'system'),

-- PCI-DSS Policies
('PCI-DSS Default', 'pci_dss', NULL, 365, 'Default PCI-DSS retention - 1 year', 'PCI-DSS audit log requirements', 'system'),
('PCI-DSS Credit Cards', 'pci_dss', 'credit_card', 0, 'Immediate credit card deletion', 'PCI-DSS cardholder data protection', 'system'),

-- Attorney-Client Policies
('Attorney-Client Default', 'attorney_client', NULL, 3650, 'Default legal retention - 10 years', 'State bar ethical requirements', 'system'),
('Attorney-Client Trust Accounts', 'attorney_client', 'trust_account', 2555, 'Trust account records - 7 years', 'State bar trust account rules', 'system'),

-- CCPA Policies
('CCPA Default', 'ccpa', NULL, 730, 'Default CCPA retention - 2 years', 'CCPA business relationship duration', 'system');

-- Create function to calculate expiration dates
CREATE OR REPLACE FUNCTION calculate_pii_expiration(
    p_compliance_frameworks JSONB,
    p_pii_type VARCHAR(50),
    p_detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
) RETURNS TIMESTAMP WITHOUT TIME ZONE AS $$
DECLARE
    framework TEXT;
    min_retention_days INTEGER := NULL;
    policy_retention INTEGER;
BEGIN
    -- Loop through each compliance framework
    FOR framework IN SELECT jsonb_array_elements_text(p_compliance_frameworks)
    LOOP
        -- Try to find specific policy first
        SELECT retention_days INTO policy_retention
        FROM pii_retention_policies
        WHERE compliance_framework = framework 
        AND pii_type = p_pii_type 
        AND active = TRUE;
        
        -- If no specific policy, use default for framework
        IF policy_retention IS NULL THEN
            SELECT retention_days INTO policy_retention
            FROM pii_retention_policies
            WHERE compliance_framework = framework 
            AND pii_type IS NULL 
            AND active = TRUE;
        END IF;
        
        -- Keep the shortest retention period (most restrictive)
        IF policy_retention IS NOT NULL THEN
            IF min_retention_days IS NULL OR policy_retention < min_retention_days THEN
                min_retention_days := policy_retention;
            END IF;
        END IF;
    END LOOP;
    
    -- Default to 3 years if no policy found
    IF min_retention_days IS NULL THEN
        min_retention_days := 1095;
    END IF;
    
    RETURN p_detected_at + (min_retention_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Create cleanup function for expired records
CREATE OR REPLACE FUNCTION cleanup_expired_pii_records() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    record_id UUID;
BEGIN
    -- Find and soft-delete expired records (with grace period)
    FOR record_id IN 
        SELECT id FROM pii_detection_records 
        WHERE deleted_at IS NULL 
        AND expires_at IS NOT NULL 
        AND expires_at + INTERVAL '30 days' <= NOW()  -- Default 30-day grace period
    LOOP
        -- Soft delete the record
        UPDATE pii_detection_records 
        SET deleted_at = NOW() 
        WHERE id = record_id;
        
        -- Log the deletion
        INSERT INTO pii_audit_logs (
            event_type, 
            event_description, 
            detection_record_id, 
            system_component, 
            compliance_impact
        ) VALUES (
            'retention_deletion',
            'Automatic retention policy deletion',
            record_id,
            'cleanup_function',
            'low'
        );
        
        deleted_count := deleted_count + 1;
    END LOOP;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE pii_detection_records IS 'Audit records for PII detections - stores metadata without actual PII values';
COMMENT ON TABLE pii_retention_policies IS 'Configurable retention policies for different compliance frameworks';
COMMENT ON TABLE pii_audit_logs IS 'Comprehensive audit log for all PII-related operations';
COMMENT ON TABLE pii_deletion_requests IS 'GDPR/CCPA deletion requests and processing status';
COMMENT ON TABLE pii_compliance_reports IS 'Periodic compliance reports for audit purposes';

COMMENT ON FUNCTION calculate_pii_expiration IS 'Calculates expiration date based on compliance frameworks and PII type';
COMMENT ON FUNCTION cleanup_expired_pii_records IS 'Cleans up expired PII records according to retention policies';

-- Grant permissions (adjust as needed for your STING setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sting_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sting_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO sting_app_user;

-- Migration completed
SELECT 'PII Audit Tables Migration Completed Successfully' as status;