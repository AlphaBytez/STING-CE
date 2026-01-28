import React from 'react';
import { Badge, Tooltip } from 'antd';
import { ToolOutlined } from '@ant-design/icons';

/**
 * FeatureInProgress component - Shows visual indicators for features under development
 * @param {string} type - Type of indicator ('badge', 'tooltip', 'overlay')
 * @param {string} message - Custom message to display
 * @param {ReactNode} children - Child components to wrap
 * @param {boolean} disabled - Whether to disable the wrapped component
 * @param {string} placement - Tooltip placement
 */
const FeatureInProgress = ({ 
  type = 'badge', 
  message = 'Feature in Development', 
  children, 
  disabled = false,
  placement = 'right'
}) => {
  const defaultMessage = '🚧 This feature is currently under development and will be available in a future release.';
  const tooltipMessage = message === 'Feature in Development' ? defaultMessage : message;

  switch (type) {
    case 'badge':
      return (
        <Tooltip title={tooltipMessage} placement={placement}>
          <div style={{ position: 'relative', opacity: disabled ? 0.6 : 1 }}>
            <Badge 
              count="DEV" 
              size="small" 
              style={{ 
                backgroundColor: '#faad14', 
                color: '#000',
                fontSize: '8px',
                height: '16px',
                lineHeight: '16px',
                minWidth: '24px'
              }}
            >
              {children}
            </Badge>
          </div>
        </Tooltip>
      );

    case 'tooltip':
      return (
        <Tooltip title={tooltipMessage} placement={placement}>
          <div style={{ opacity: disabled ? 0.6 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}>
            {children}
          </div>
        </Tooltip>
      );

    case 'overlay':
      return (
        <div style={{ position: 'relative' }}>
          {children}
          <div 
            style={{
              position: 'absolute',
              bottom: '-2px',
              right: '-2px',
              width: '6px',
              height: '6px',
              background: '#faad14',
              borderRadius: '50%',
              zIndex: 10,
              boxShadow: '0 0 0 1px rgba(0,0,0,0.3)'
            }}
          />
          {disabled && (
            <div 
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.1)',
                borderRadius: '4px',
                zIndex: 5
              }}
            />
          )}
        </div>
      );

    default:
      return children;
  }
};

export default FeatureInProgress;