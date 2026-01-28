import React, { useState, useEffect } from 'react';
import { ChevronUp } from 'lucide-react';

const ScrollToTopButton = ({ 
  threshold = 400,
  className = '',
  showText = false 
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      if (window.pageYOffset > threshold) {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    };

    window.addEventListener('scroll', toggleVisibility);

    return () => window.removeEventListener('scroll', toggleVisibility);
  }, [threshold]);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  if (!isVisible) {
    return null;
  }

  return (
    <button
      onClick={scrollToTop}
      className={`fixed bottom-6 left-6 z-50 floating-button rounded-full p-3 transition-all duration-300 hover:scale-110 shadow-lg bg-yellow-500 hover:bg-yellow-600 text-black border-yellow-500 hover:border-yellow-600 ${className}`}
      title="Scroll to top"
      aria-label="Scroll to top"
    >
      <ChevronUp className="w-6 h-6" />
      {showText && (
        <span className="ml-2 text-sm font-medium hidden sm:inline">
          Top
        </span>
      )}
    </button>
  );
};

export default ScrollToTopButton;