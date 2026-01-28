import React from 'react';
import { Shield, Lock, Key, AlertTriangle } from 'lucide-react';

/**
 * TierBadge Component
 *
 * Displays a visual indicator for the authentication tier requirement
 * Used throughout the application to show users what level of security is needed
 */
const TierBadge = ({
  tier,
  operation,
  size = 'sm',
  showIcon = true,
  showDescription = false,
  className = ''
}) => {
  const getTierConfig = (tier) => {
    switch (tier) {
      case 1:
        return {
          label: 'Tier 1',
          description: 'Public access',
          color: 'bg-green-500',
          textColor: 'text-green-100',
          borderColor: 'border-green-400',
          icon: Shield,
          requirements: 'No authentication required'
        };
      case 2:
        return {
          label: 'Tier 2',
          description: 'Basic operations',
          color: 'bg-amber-600',
          textColor: 'text-amber-100',
          borderColor: 'border-amber-500',
          icon: Key,
          requirements: 'Any authentication method (email, passkey, TOTP)'
        };
      case 3:
        return {
          label: 'Tier 3',
          description: 'Sensitive operations',
          color: 'bg-orange-500',
          textColor: 'text-orange-100',
          borderColor: 'border-orange-400',
          icon: Lock,
          requirements: 'Secure authentication (passkey or TOTP only)'
        };
      case 4:
        return {
          label: 'Tier 4',
          description: 'Critical operations',
          color: 'bg-red-500',
          textColor: 'text-red-100',
          borderColor: 'border-red-400',
          icon: AlertTriangle,
          requirements: 'Dual-factor authentication (passkey/TOTP + email)'
        };
      default:
        return {
          label: 'Unknown',
          description: 'Unknown tier',
          color: 'bg-gray-500',
          textColor: 'text-gray-100',
          borderColor: 'border-gray-400',
          icon: Shield,
          requirements: 'Unknown requirements'
        };
    }
  };

  const getSizeClasses = (size) => {
    switch (size) {
      case 'xs':
        return 'px-1.5 py-0.5 text-xs';
      case 'sm':
        return 'px-2 py-1 text-xs';
      case 'md':
        return 'px-3 py-1.5 text-sm';
      case 'lg':
        return 'px-4 py-2 text-base';
      default:
        return 'px-2 py-1 text-xs';
    }
  };

  const config = getTierConfig(tier);
  const sizeClasses = getSizeClasses(size);
  const IconComponent = config.icon;

  const badgeContent = (
    <span className={`
      inline-flex items-center gap-1.5 rounded-full font-medium border
      ${config.color} ${config.textColor} ${config.borderColor}
      ${sizeClasses} ${className}
    `}>
      {showIcon && <IconComponent className="w-3 h-3" />}
      <span>{config.label}</span>
      {operation && (
        <span className="opacity-80">• {operation}</span>
      )}
    </span>
  );

  if (showDescription) {
    return (
      <div className="space-y-1">
        {badgeContent}
        <div className="text-xs text-gray-400">
          <div className="font-medium">{config.description}</div>
          <div>{config.requirements}</div>
        </div>
      </div>
    );
  }

  return badgeContent;
};

/**
 * TierIndicator Component
 *
 * A more detailed component showing tier information with tooltips
 */
export const TierIndicator = ({
  tier,
  operation,
  description,
  className = '',
  compact = false
}) => {
  const config = getTierConfig(tier);
  const IconComponent = config.icon;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <TierBadge tier={tier} size="sm" />
        {operation && <span className="text-sm text-gray-300">{operation}</span>}
      </div>
    );
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 border border-slate-700 ${className}`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${config.color}`}>
          <IconComponent className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-white">{config.label} Security</h4>
            <TierBadge tier={tier} showIcon={false} size="xs" />
          </div>
          <p className="text-sm text-gray-300 mb-2">{config.description}</p>
          {operation && (
            <p className="text-sm text-gray-400 mb-2">
              <span className="font-medium">Operation:</span> {operation}
            </p>
          )}
          {description && (
            <p className="text-sm text-gray-400 mb-2">{description}</p>
          )}
          <div className="text-xs text-gray-500">
            <span className="font-medium">Requirements:</span> {config.requirements}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Helper function to get tier configuration
 * Exported for use in other components
 */
export const getTierConfig = (tier) => {
  const badge = new TierBadge({});
  return badge.getTierConfig ? badge.getTierConfig(tier) : null;
};

/**
 * OperationTierMap
 *
 * Defines the tier requirements for common operations
 * This helps maintain consistency across the application
 */
export const OPERATION_TIERS = {
  // Tier 1 - Public
  VIEW_PUBLIC_CONTENT: 1,
  HEALTH_CHECK: 1,

  // Tier 2 - Basic operations
  VIEW_API_KEYS: 2,
  UPLOAD_FILE: 2,
  VIEW_DOCUMENTS: 2,
  CREATE_BASIC_CONTENT: 2,

  // Tier 3 - Sensitive operations
  CREATE_API_KEY: 3,
  DELETE_FILE: 3,
  MODIFY_SETTINGS: 3,
  VIEW_AUDIT_LOGS: 3,
  DELETE_API_KEY: 3,
  GENERATE_RECOVERY_CODES: 3,

  // Tier 4 - Critical operations
  BULK_DELETE_FILES: 4,
  REVOKE_RECOVERY_CODES: 4,
  ADMIN_USER_MANAGEMENT: 4,
  SYSTEM_CONFIGURATION: 4,
  DELETE_ACCOUNT: 4
};

/**
 * Helper component to show tier requirement for a specific operation
 */
export const OperationTier = ({ operation, ...props }) => {
  const tier = OPERATION_TIERS[operation];
  if (!tier) {
    console.warn(`Unknown operation: ${operation}`);
    return null;
  }

  return <TierBadge tier={tier} operation={operation} {...props} />;
};

export default TierBadge;