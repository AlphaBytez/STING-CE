import React from 'react';
import { Card } from 'antd';
import { clsx } from 'clsx';

/**
 * STING V2 Glass Morphism Card Component
 * 
 * Provides consistent glass-like appearance across all pages
 * with stacked glass effect, transparency, and shadows
 */

const GlassCard = ({ 
  children, 
  className, 
  variant = 'default',
  hoverable = true,
  elevation = 'medium',
  ...props 
}) => {
  // Define consistent glass variants
  const variantClasses = {
    default: 'sting-glass-default',
    subtle: 'sting-glass-subtle',
    strong: 'sting-glass-strong',
    ultra: 'sting-glass-ultra',
  };

  // Define elevation levels
  const elevationClasses = {
    low: 'sting-elevation-low',
    medium: 'sting-elevation-medium',
    high: 'sting-elevation-high',
    floating: 'sting-elevation-floating',
  };

  const cardClasses = clsx(
    'sting-glass-card',
    variantClasses[variant],
    elevationClasses[elevation],
    {
      'sting-glass-hoverable': hoverable,
    },
    className
  );

  return (
    <Card className={cardClasses} {...props}>
      {children}
    </Card>
  );
};

// Export variants for direct use
export const GlassCardSubtle = (props) => <GlassCard variant="subtle" {...props} />;
export const GlassCardStrong = (props) => <GlassCard variant="strong" {...props} />;
export const GlassCardUltra = (props) => <GlassCard variant="ultra" {...props} />;

export default GlassCard;