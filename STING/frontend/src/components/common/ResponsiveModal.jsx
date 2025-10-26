import React from 'react';
import { X } from 'lucide-react';

/**
 * ResponsiveModal - A mobile-friendly modal component
 * 
 * Features:
 * - Viewport-based sizing on mobile
 * - Smooth transitions
 * - Scrollable content area
 * - Touch-friendly close button
 * - Backdrop click to close
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {Function} props.onClose - Function to call when closing
 * @param {string} props.title - Modal title
 * @param {ReactNode} props.children - Modal content
 * @param {string} props.size - Size variant: 'sm', 'md', 'lg', 'xl', 'full'
 * @param {boolean} props.showCloseButton - Whether to show the close button
 * @param {string} props.className - Additional CSS classes
 */
const ResponsiveModal = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  size = 'md',
  showCloseButton = true,
  className = ''
}) => {
  if (!isOpen) return null;

  // Size mappings with mobile-first approach
  const sizeClasses = {
    sm: 'w-full max-w-sm md:max-w-sm',
    md: 'w-full max-w-full md:max-w-md lg:max-w-lg',
    lg: 'w-full max-w-full md:max-w-2xl lg:max-w-4xl',
    xl: 'w-full max-w-full md:max-w-4xl lg:max-w-6xl',
    full: 'w-full h-full md:max-w-7xl md:h-auto'
  };

  const modalSizeClass = sizeClasses[size] || sizeClasses.md;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal positioning wrapper */}
      <div className="flex min-h-screen items-end sm:items-center justify-center p-0 sm:p-4">
        {/* Modal content */}
        <div 
          className={`
            relative transform overflow-hidden rounded-t-2xl sm:rounded-2xl 
            bg-gray-800 border border-gray-600 shadow-2xl 
            transition-all duration-300 ease-out
            ${modalSizeClass} ${className}
            max-h-[90vh] sm:max-h-[85vh] flex flex-col
          `}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          {(title || showCloseButton) && (
            <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-600">
              {title && (
                <h3 className="text-lg sm:text-xl font-semibold text-white pr-4">
                  {title}
                </h3>
              )}
              {showCloseButton && (
                <button
                  onClick={onClose}
                  className="ml-auto text-gray-400 hover:text-white transition-colors p-2 
                           hover:bg-gray-700 rounded-lg touch-manipulation"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5 sm:w-6 sm:h-6" />
                </button>
              )}
            </div>
          )}
          
          {/* Content - Scrollable */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

// Convenience components for common modal patterns
export const ResponsiveModalFooter = ({ children, className = '' }) => (
  <div className={`
    flex flex-col sm:flex-row gap-3 justify-end 
    pt-4 mt-4 border-t border-gray-600 
    ${className}
  `}>
    {children}
  </div>
);

export const ResponsiveModalButton = ({ children, onClick, variant = 'primary', className = '' }) => {
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    cancel: 'bg-gray-700 hover:bg-gray-600 text-gray-300'
  };

  return (
    <button
      onClick={onClick}
      className={`
        px-4 py-2 rounded-lg font-medium transition-colors
        min-h-[44px] touch-manipulation
        ${variants[variant] || variants.primary}
        ${className}
      `}
    >
      {children}
    </button>
  );
};

export default ResponsiveModal;