# 📋 PII Retention Requirements by Compliance Framework

*Reference guide for configurable PII retention periods in STING*

## Compliance Framework Retention Requirements

### HIPAA (Healthcare)
- **Medical Records**: 6 years minimum (varies by state)
- **Adult Medical Records**: 6-10 years after last treatment
- **Minor Medical Records**: Until age of majority + 6-10 years  
- **Mental Health Records**: 7 years in most states
- **Diagnostic Images**: 5-7 years
- **Lab Results**: 2-7 years depending on type
- **Prescription Records**: 5 years (DEA requirement)

**STING Default**: 7 years (2,555 days)

### GDPR (European Privacy)
- **Personal Data**: No specific retention period - must be "adequate, relevant and limited"
- **Employment Records**: 6 years after employment ends
- **Financial Records**: 6 years for tax purposes
- **Marketing Data**: Must be deleted when purpose fulfilled
- **Consent Records**: 7 years after consent withdrawn

**STING Default**: 3 years (1,095 days) with deletion upon request

### PCI-DSS (Payment Card Industry)
- **Cardholder Data**: Delete immediately after authorization (unless business need)
- **Transaction Logs**: 1 year minimum
- **Audit Logs**: 1 year minimum  
- **Security Testing Records**: 3 years
- **Vulnerability Scan Results**: 4 years

**STING Default**: 1 year (365 days) with immediate deletion option

### Attorney-Client Privilege (Legal)
- **Client Files**: Varies by jurisdiction (5-10 years typical)
- **Trust Account Records**: 7 years in most states
- **Case Files**: 7-10 years after case closure
- **Settlement Records**: 10 years
- **Conflict Records**: Permanent or very long retention

**STING Default**: 10 years (3,650 days)

### CCPA (California Privacy)
- **Personal Information**: No specific retention period
- **Consumer Requests**: 24 months  
- **Business Records**: Follow existing business requirements
- **Opt-out Records**: Duration of business relationship + 2 years

**STING Default**: 2 years (730 days)

### FERPA (Educational)
- **Student Educational Records**: Varies (3-7 years typical)
- **Grade Records**: Permanent for transcripts, 5 years for gradebooks
- **Disciplinary Records**: 7 years
- **Special Education Records**: 5 years after graduation/departure

**STING Default**: 5 years (1,825 days)

## Risk-Based Retention Categories

### High Risk PII (Immediate Deletion Priority)
- Social Security Numbers
- Credit Card Numbers  
- Bank Account Numbers
- Medical Record Numbers
- Settlement Amounts

**Retention**: Shortest applicable compliance requirement

### Medium Risk PII (Standard Retention)
- Names in context
- Case Numbers
- Employee IDs
- Phone Numbers
- Addresses

**Retention**: Standard compliance framework requirement

### Low Risk PII (Extended Retention OK)
- Email addresses (business context)
- General contact information
- Public record references

**Retention**: Longest applicable compliance requirement

## Configuration Mapping

```yaml
pii_retention:
  compliance_frameworks:
    hipaa:
      default_retention_days: 2555  # 7 years
      pii_specific:
        medical_record_number: 2555
        prescription_info: 1825      # 5 years (DEA requirement)
        lab_result: 1825            # 5 years
        
    gdpr:
      default_retention_days: 1095  # 3 years
      deletion_on_request: true
      pii_specific:
        person_name: 2190           # 6 years (employment)
        email_address: 1095         # 3 years
        
    pci_dss:
      default_retention_days: 365   # 1 year
      immediate_deletion: true      # For cardholder data
      pii_specific:
        credit_card: 0              # Immediate deletion
        bank_account: 365           # 1 year for logs
        
    attorney_client:
      default_retention_days: 3650  # 10 years
      pii_specific:
        case_number: 3650
        settlement_amount: 3650
        trust_account: 2555         # 7 years
```

## Implementation Notes

### Cascade Deletion Rules
1. **Document Deletion**: When document is deleted, all associated PII records deleted
2. **User Deletion**: All PII records for user deleted (except legal hold)
3. **Compliance Request**: Immediate deletion overrides retention periods
4. **Legal Hold**: Prevents deletion until hold released

### Grace Periods
- **GDPR Right to Erasure**: 30 days maximum response time
- **HIPAA Amendment Requests**: 60 days for response
- **Business Continuity**: 90-day grace period for active matters

### Audit Requirements
- **Deletion Logs**: Must maintain record of what was deleted and when
- **Retention Justification**: Document business/legal reason for retention
- **Access Logs**: Track who accessed PII and when
- **Export Logs**: Record when PII was exported or shared

---

*Retention requirements as of January 2025 - consult legal counsel for specific compliance needs*