import React, { useState } from 'react';
import { Tooltip, Chip, Box, Typography } from '@mui/material';
import {
  Shield as ShieldIcon,
  Email as EmailIcon,
  Person as PersonIcon,
  Phone as PhoneIcon,
  CreditCard as CreditCardIcon,
  Home as HomeIcon,
  MedicalServices as MedicalIcon,
  VpnKey as KeyIcon
} from '@mui/icons-material';

/**
 * PIIHighlight Component
 *
 * Displays protected PII with visual indicators:
 * - Dotted underline in risk-based color
 * - Tooltip showing PII type, risk level, and protection info
 * - Accessible keyboard navigation
 * - Screen reader announcements
 *
 * @param {string} text - The deserialized PII text to display
 * @param {object} piiMetadata - Metadata about the protected PII
 * @param {object} preferences - User visual indicator preferences
 */
const PIIHighlight = ({ text, piiMetadata, preferences = {} }) => {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  // Default preferences
  const defaultPrefs = {
    colors: {
      low_risk: '#2196F3',
      medium_risk: '#ff9800',
      high_risk: '#ef5350'
    },
    underline_style: 'dotted',
    underline_thickness: 2,
    tooltips: {
      enabled: true,
      show_pii_type: true,
      show_risk_level: true,
      show_protection_icon: true,
      delay_ms: 200
    },
    accessibility: {
      screen_reader_announcements: true,
      keyboard_navigation: true
    }
  };

  const prefs = { ...defaultPrefs, ...preferences };

  // Get color based on risk level
  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'high':
        return prefs.colors.high_risk;
      case 'medium':
        return prefs.colors.medium_risk;
      case 'low':
      default:
        return prefs.colors.low_risk;
    }
  };

  // Get icon based on PII type
  const getPIIIcon = (piiType) => {
    const iconProps = { fontSize: 'small', sx: { mr: 0.5 } };
    switch (piiType) {
      case 'email':
        return <EmailIcon {...iconProps} />;
      case 'person_name':
      case 'name':
        return <PersonIcon {...iconProps} />;
      case 'phone':
        return <PhoneIcon {...iconProps} />;
      case 'credit_card':
        return <CreditCardIcon {...iconProps} />;
      case 'address':
        return <HomeIcon {...iconProps} />;
      case 'medical_record':
        return <MedicalIcon {...iconProps} />;
      case 'ssn':
      case 'bank_account':
      default:
        return <KeyIcon {...iconProps} />;
    }
  };

  // Format PII type for display
  const formatPIIType = (piiType) => {
    const typeMap = {
      'person_name': 'Name',
      'email': 'Email Address',
      'phone': 'Phone Number',
      'ssn': 'Social Security Number',
      'credit_card': 'Credit Card',
      'bank_account': 'Bank Account',
      'address': 'Physical Address',
      'ip_address': 'IP Address',
      'medical_record': 'Medical Record',
      'account_number': 'Account Number',
      'date_of_birth': 'Date of Birth',
      'drivers_license': 'Driver\'s License',
      'passport': 'Passport Number'
    };
    return typeMap[piiType] || piiType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Get risk level color and label
  const getRiskChip = (riskLevel) => {
    const config = {
      low: { label: 'Low Risk', color: 'info' },
      medium: { label: 'Medium Risk', color: 'warning' },
      high: { label: 'High Risk', color: 'error' }
    };
    const { label, color } = config[riskLevel] || config.low;
    return <Chip label={label} size="small" color={color} sx={{ ml: 1 }} />;
  };

  if (!prefs.tooltips.enabled) {
    // No tooltip, just render text
    return <span>{text}</span>;
  }

  const riskColor = getRiskColor(piiMetadata.risk_level);

  // Build tooltip content
  const tooltipContent = (
    <Box sx={{ p: 0.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
        {prefs.tooltips.show_protection_icon && <ShieldIcon fontSize="small" sx={{ mr: 0.5 }} />}
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          Protected Information
        </Typography>
      </Box>

      {prefs.tooltips.show_pii_type && (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
          {getPIIIcon(piiMetadata.pii_type)}
          <Typography variant="body2">
            {formatPIIType(piiMetadata.pii_type)}
          </Typography>
        </Box>
      )}

      {prefs.tooltips.show_risk_level && (
        <Box sx={{ mt: 1 }}>
          {getRiskChip(piiMetadata.risk_level)}
        </Box>
      )}

      <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.8 }}>
        Source: {piiMetadata.source || 'cache'}
      </Typography>

      {piiMetadata.confidence && (
        <Typography variant="caption" sx={{ display: 'block', opacity: 0.8 }}>
          Confidence: {Math.round(piiMetadata.confidence * 100)}%
        </Typography>
      )}
    </Box>
  );

  // Screen reader text
  const ariaLabel = prefs.accessibility.screen_reader_announcements
    ? `Protected ${formatPIIType(piiMetadata.pii_type)}: ${text}, ${piiMetadata.risk_level} risk`
    : text;

  return (
    <Tooltip
      title={tooltipContent}
      open={tooltipOpen}
      onOpen={() => setTooltipOpen(true)}
      onClose={() => setTooltipOpen(false)}
      enterDelay={prefs.tooltips.delay_ms}
      arrow
      componentsProps={{
        tooltip: {
          sx: {
            bgcolor: 'background.paper',
            color: 'text.primary',
            border: '1px solid',
            borderColor: 'divider',
            boxShadow: 3
          }
        }
      }}
    >
      <span
        role="mark"
        aria-label={ariaLabel}
        tabIndex={prefs.accessibility.keyboard_navigation ? 0 : -1}
        onFocus={() => prefs.accessibility.keyboard_navigation && setTooltipOpen(true)}
        onBlur={() => prefs.accessibility.keyboard_navigation && setTooltipOpen(false)}
        style={{
          borderBottom: `${prefs.underline_thickness}px ${prefs.underline_style} ${riskColor}`,
          cursor: 'help',
          outline: 'none',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = `${riskColor}15`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
        {text}
      </span>
    </Tooltip>
  );
};

export default PIIHighlight;
