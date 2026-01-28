import React, { useMemo } from 'react';
import { Box, Chip } from '@mui/material';
import { Shield as ShieldIcon } from '@mui/icons-material';
import PIIHighlight from './PIIHighlight';

/**
 * MessageWithPII Component
 *
 * Renders a message with PII highlights and optional protection badge.
 * Parses pii_annotations to insert PIIHighlight components at correct positions.
 *
 * @param {string} message - The message text (already deserialized)
 * @param {object} piiProtection - PII protection metadata from API
 * @param {object} preferences - User visual indicator preferences
 * @param {boolean} showBadge - Whether to show protection badge
 */
const MessageWithPII = ({ message, piiProtection, preferences = {}, showBadge = true }) => {
  // Check if PII protection is active and has annotations
  const hasPII = piiProtection?.protection_active &&
                 piiProtection?.pii_annotations?.length > 0;

  // Parse message and insert PII highlights
  const renderedMessage = useMemo(() => {
    if (!hasPII || !preferences.enabled) {
      // No PII or visual indicators disabled - return plain text
      return <span style={{ whiteSpace: 'pre-wrap' }}>{message}</span>;
    }

    const annotations = piiProtection.pii_annotations;

    // Sort annotations by position (ascending)
    const sortedAnnotations = [...annotations].sort(
      (a, b) => a.deserialized_position.start - b.deserialized_position.start
    );

    // Build array of text segments and PII highlights
    const segments = [];
    let lastIndex = 0;

    sortedAnnotations.forEach((annotation, idx) => {
      const { start, end } = annotation.deserialized_position;

      // Add text before this PII
      if (start > lastIndex) {
        segments.push({
          type: 'text',
          content: message.substring(lastIndex, start),
          key: `text-${idx}`
        });
      }

      // Add PII highlight
      segments.push({
        type: 'pii',
        content: message.substring(start, end),
        metadata: annotation,
        key: `pii-${idx}`
      });

      lastIndex = end;
    });

    // Add remaining text after last PII
    if (lastIndex < message.length) {
      segments.push({
        type: 'text',
        content: message.substring(lastIndex),
        key: `text-end`
      });
    }

    // Render segments
    return (
      <span style={{ whiteSpace: 'pre-wrap' }}>
        {segments.map(segment => {
          if (segment.type === 'text') {
            return <span key={segment.key}>{segment.content}</span>;
          } else {
            return (
              <PIIHighlight
                key={segment.key}
                text={segment.content}
                piiMetadata={segment.metadata}
                preferences={preferences}
              />
            );
          }
        })}
      </span>
    );
  }, [message, hasPII, piiProtection, preferences]);

  // Get badge color based on protection quality
  const getBadgeColor = () => {
    switch (piiProtection?.protection_quality) {
      case 'complete':
        return 'success';
      case 'partial':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  // Get protection mode label
  const getProtectionModeLabel = () => {
    const mode = piiProtection?.protection_mode;
    const modeLabels = {
      'local': 'Local',
      'trusted': 'Trusted Network',
      'report': 'Report Mode',
      'external': 'Cloud Protected'
    };
    return modeLabels[mode] || 'Protected';
  };

  return (
    <Box sx={{ position: 'relative', width: '100%' }}>
      {/* Protection Badge */}
      {hasPII && showBadge && preferences.show_protection_badge && (
        <Chip
          icon={<ShieldIcon />}
          label={`${piiProtection.items_protected} ${getProtectionModeLabel()}`}
          size="small"
          color={getBadgeColor()}
          sx={{
            position: preferences.badge_position === 'corner' ? 'absolute' : 'relative',
            top: preferences.badge_position === 'corner' ? 8 : 'auto',
            right: preferences.badge_position === 'corner' ? 8 : 'auto',
            mb: preferences.badge_position === 'inline' ? 1 : 0,
            fontSize: '0.75rem'
          }}
        />
      )}

      {/* Message Content */}
      <Box sx={{ mt: (hasPII && showBadge && preferences.badge_position === 'corner') ? 2 : 0 }}>
        {renderedMessage}
      </Box>
    </Box>
  );
};

export default MessageWithPII;
