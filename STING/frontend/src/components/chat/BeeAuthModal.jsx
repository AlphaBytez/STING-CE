import React from 'react';
import { Modal, Box, Typography, Button, Alert, Chip } from '@mui/material';
import { Shield, Fingerprint, Key, Mail } from 'lucide-react';
import TierBadge from '../common/TierBadge';
import { storeOperationContext } from '../../utils/tieredAuth';

/**
 * BeeAuthModal - Authentication prompt for Bee-initiated operations
 *
 * This modal appears when Bee needs the user to authenticate for sensitive operations
 * like generating reports, accessing secure data, or performing privileged actions.
 *
 * @param {boolean} open - Whether the modal is visible
 * @param {string} operation - The operation being performed (e.g., "generate report")
 * @param {number} tier - Security tier required (2, 3, or 4)
 * @param {object} context - Additional context to preserve (e.g., reportId, data)
 * @param {function} onCancel - Callback when user cancels
 */
const BeeAuthModal = ({
  open,
  operation = 'complete this action',
  tier = 2,
  context = {},
  onCancel
}) => {

  const handleAuthenticate = () => {
    // Store operation context for return flow
    storeOperationContext(`BEE_${operation.toUpperCase().replace(/\s+/g, '_')}`, context);

    // Redirect to security-upgrade with return URL
    const currentUrl = window.location.pathname + window.location.search;
    const separator = currentUrl.includes('?') ? '&' : '?';
    const redirectUrl = `/security-upgrade?reason=${encodeURIComponent(operation)}&tier=${tier}&return_to=${encodeURIComponent(currentUrl + separator + 'bee_auth=complete')}`;

    window.location.href = redirectUrl;
  };

  const getTierDescription = (tier) => {
    switch (tier) {
      case 2:
        return 'Touch ID, passkey, or authenticator app';
      case 3:
        return 'Two authentication factors';
      case 4:
        return 'All authentication methods';
      default:
        return 'Authentication required';
    }
  };

  const getTierIcon = (tier) => {
    switch (tier) {
      case 2:
        return <Fingerprint className="w-6 h-6" />;
      case 3:
        return <Key className="w-6 h-6" />;
      case 4:
        return <Shield className="w-6 h-6" />;
      default:
        return <Shield className="w-6 h-6" />;
    }
  };

  return (
    <Modal
      open={open}
      onClose={onCancel}
      aria-labelledby="bee-auth-modal-title"
      aria-describedby="bee-auth-modal-description"
    >
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: { xs: '90%', sm: 500 },
          bgcolor: 'rgba(30, 41, 59, 0.98)',
          border: '1px solid rgba(251, 191, 36, 0.3)',
          borderRadius: 2,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
          p: 4,
          backdropFilter: 'blur(10px)',
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-xl">
            {getTierIcon(tier)}
          </div>
          <div className="flex-1">
            <Typography
              id="bee-auth-modal-title"
              variant="h6"
              component="h2"
              sx={{ color: 'white', fontWeight: 600 }}
            >
              🐝 Bee needs your confirmation
            </Typography>
          </div>
          <TierBadge tier={tier} size="sm" />
        </div>

        {/* Description */}
        <Alert
          severity="info"
          icon={<Shield className="w-5 h-5" />}
          sx={{
            mb: 3,
            bgcolor: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: 'rgb(191, 219, 254)',
            '& .MuiAlert-icon': {
              color: 'rgb(96, 165, 250)'
            }
          }}
        >
          <Typography
            id="bee-auth-modal-description"
            sx={{ fontSize: '0.95rem', mb: 1 }}
          >
            To <strong>{operation}</strong>, please authenticate with:
          </Typography>
          <Typography sx={{ fontSize: '0.875rem', color: 'rgb(147, 197, 253)' }}>
            {getTierDescription(tier)}
          </Typography>
        </Alert>

        {/* Available Methods */}
        <Box sx={{ mb: 3, p: 2, bgcolor: 'rgba(55, 65, 81, 0.5)', borderRadius: 1 }}>
          <Typography
            variant="subtitle2"
            sx={{ color: 'rgb(156, 163, 175)', mb: 2, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}
          >
            Available Methods
          </Typography>
          <div className="flex flex-wrap gap-2">
            <Chip
              icon={<Fingerprint className="w-4 h-4" />}
              label="Touch ID / Passkey"
              size="small"
              sx={{
                bgcolor: 'rgba(34, 197, 94, 0.2)',
                color: 'rgb(134, 239, 172)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
              }}
            />
            <Chip
              icon={<Key className="w-4 h-4" />}
              label="Authenticator App"
              size="small"
              sx={{
                bgcolor: 'rgba(59, 130, 246, 0.2)',
                color: 'rgb(147, 197, 253)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
              }}
            />
            <Chip
              icon={<Mail className="w-4 h-4" />}
              label="Email Code"
              size="small"
              sx={{
                bgcolor: 'rgba(168, 85, 247, 0.2)',
                color: 'rgb(216, 180, 254)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
              }}
            />
          </div>
        </Box>

        {/* Why is this needed? */}
        <Box sx={{ mb: 3, p: 2, bgcolor: 'rgba(251, 191, 36, 0.1)', borderRadius: 1, border: '1px solid rgba(251, 191, 36, 0.2)' }}>
          <Typography
            variant="subtitle2"
            sx={{ color: 'rgb(252, 211, 77)', mb: 1, fontWeight: 600, fontSize: '0.875rem' }}
          >
            Why is this needed?
          </Typography>
          <Typography sx={{ color: 'rgb(253, 230, 138)', fontSize: '0.8rem', lineHeight: 1.6 }}>
            STING uses progressive security. Sensitive operations initiated by Bee require
            you to confirm your identity to ensure your data stays protected.
          </Typography>
        </Box>

        {/* Action Buttons */}
        <div className="flex gap-3 mt-4">
          <Button
            fullWidth
            variant="outlined"
            onClick={onCancel}
            sx={{
              color: 'rgb(156, 163, 175)',
              borderColor: 'rgb(75, 85, 99)',
              '&:hover': {
                borderColor: 'rgb(107, 114, 128)',
                bgcolor: 'rgba(75, 85, 99, 0.1)',
              }
            }}
          >
            Cancel
          </Button>
          <Button
            fullWidth
            variant="contained"
            onClick={handleAuthenticate}
            startIcon={getTierIcon(tier)}
            sx={{
              bgcolor: 'rgb(251, 191, 36)',
              color: 'rgb(0, 0, 0)',
              fontWeight: 600,
              '&:hover': {
                bgcolor: 'rgb(245, 158, 11)',
              }
            }}
          >
            Authenticate
          </Button>
        </div>

        {/* Helper Text */}
        <Typography
          sx={{
            mt: 3,
            fontSize: '0.75rem',
            color: 'rgb(107, 114, 128)',
            textAlign: 'center',
            fontStyle: 'italic'
          }}
        >
          You'll be redirected to the authentication page and returned to Bee Chat afterward.
        </Typography>
      </Box>
    </Modal>
  );
};

export default BeeAuthModal;
