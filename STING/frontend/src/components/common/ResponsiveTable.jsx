import React from 'react';

/**
 * ResponsiveTable - A mobile-friendly table wrapper
 * 
 * Features:
 * - Horizontal scrolling on mobile
 * - Sticky headers
 * - Touch-friendly scrolling
 * - Shadow indicators for scroll position
 * 
 * @param {Object} props
 * @param {ReactNode} props.children - Table content
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.stickyHeader - Whether to make the header sticky
 */
const ResponsiveTable = ({ children, className = '', stickyHeader = true }) => {
  const [showLeftShadow, setShowLeftShadow] = React.useState(false);
  const [showRightShadow, setShowRightShadow] = React.useState(true);
  const scrollRef = React.useRef(null);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setShowLeftShadow(scrollLeft > 0);
    setShowRightShadow(scrollLeft < scrollWidth - clientWidth - 1);
  };

  React.useEffect(() => {
    const scrollElement = scrollRef.current;
    if (scrollElement) {
      handleScroll(); // Initial check
      scrollElement.addEventListener('scroll', handleScroll);
      return () => scrollElement.removeEventListener('scroll', handleScroll);
    }
  }, []);

  return (
    <div className={`relative ${className}`}>
      {/* Left shadow indicator */}
      <div 
        className={`
          absolute left-0 top-0 bottom-0 w-8 
          bg-gradient-to-r from-gray-800 to-transparent 
          pointer-events-none z-10 transition-opacity duration-200
          ${showLeftShadow ? 'opacity-100' : 'opacity-0'}
        `} 
      />
      
      {/* Right shadow indicator */}
      <div 
        className={`
          absolute right-0 top-0 bottom-0 w-8 
          bg-gradient-to-l from-gray-800 to-transparent 
          pointer-events-none z-10 transition-opacity duration-200
          ${showRightShadow ? 'opacity-100' : 'opacity-0'}
        `} 
      />
      
      {/* Scrollable container */}
      <div 
        ref={scrollRef}
        className="overflow-x-auto overflow-y-visible -mx-4 px-4 sm:mx-0 sm:px-0"
        style={{ WebkitOverflowScrolling: 'touch' }}
      >
        <div className="inline-block min-w-full align-middle">
          {React.cloneElement(children, {
            className: `${children.props.className || ''} ${stickyHeader ? 'sticky-header' : ''}`
          })}
        </div>
      </div>
      
      <style jsx>{`
        .sticky-header thead th {
          position: sticky;
          top: 0;
          background-color: rgb(31, 41, 55);
          z-index: 10;
        }
      `}</style>
    </div>
  );
};

/**
 * ResponsiveTableContainer - Alternative card-based layout for mobile
 * Transforms table rows into stacked cards on small screens
 */
export const ResponsiveTableContainer = ({ headers, data, renderCell, className = '' }) => {
  return (
    <>
      {/* Desktop table view */}
      <div className="hidden md:block">
        <ResponsiveTable className={className}>
          <table className="min-w-full divide-y divide-gray-600">
            <thead>
              <tr>
                {headers.map((header, index) => (
                  <th
                    key={index}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {data.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {headers.map((header, cellIndex) => (
                    <td key={cellIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {renderCell(row, header, cellIndex)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </ResponsiveTable>
      </div>
      
      {/* Mobile card view */}
      <div className="md:hidden space-y-4">
        {data.map((row, rowIndex) => (
          <div 
            key={rowIndex} 
            className="bg-gray-700 rounded-lg p-4 space-y-2 border border-gray-600"
          >
            {headers.map((header, cellIndex) => (
              <div key={cellIndex} className="flex justify-between items-start">
                <span className="text-xs font-medium text-gray-400 uppercase">
                  {header}:
                </span>
                <span className="text-sm text-gray-200 text-right ml-2">
                  {renderCell(row, header, cellIndex)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
};

export default ResponsiveTable;