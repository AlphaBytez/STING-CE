import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  MessageSquare, 
  Settings, 
  Users, 
  Activity, 
  BarChart, 
  FileText,
  Package,
  Globe,
  ShoppingBag,
  Search,
  SearchX,
  Scan,
  Eye,
  Target,
  Zap
} from 'lucide-react';
import { useUnifiedAuth } from '../../auth/UnifiedAuthProvider';
import { loadNavigationConfig, lucideIconMap } from '../../config/navigationConfig';

const Sidebar = ({ colorScheme }) => {
  const location = useLocation();
  const { user } = useUnifiedAuth();
  const [navConfig, setNavConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);

  // Load navigation configuration using database-backed config
  useEffect(() => {
    const loadConfig = async () => {
      setConfigLoading(true);
      try {
        // Try to load from database first, fallback to localStorage
        const config = await loadNavigationConfig(isAdmin, true);
        setNavConfig(config);
      } catch (error) {
        console.warn('Sidebar: Failed to load navigation config from database, using localStorage:', error);
        try {
          const fallbackConfig = await loadNavigationConfig(isAdmin, false);
          setNavConfig(fallbackConfig);
        } catch (fallbackError) {
          console.error('Sidebar: Failed to load navigation config:', fallbackError);
        }
      } finally {
        setConfigLoading(false);
      }
    };

    loadConfig();

    // Listen for navigation config updates
    const handleNavConfigUpdate = (event) => {
      setNavConfig(event.detail);
    };

    window.addEventListener('navigation-config-updated', handleNavConfigUpdate);
    
    return () => {
      window.removeEventListener('navigation-config-updated', handleNavConfigUpdate);
    };
  }, [isAdmin]);

  // Check if user is admin
  // Enhanced admin detection with email-based fallback for admin@sting.local
  const isAdmin = user && user.role === 'admin' ||
                  user && user.email === 'admin@sting.local' ||  // Email-based admin detection
                  localStorage.getItem('temp-admin-override') === 'true' ||
                  // Check if any admin profile exists in localStorage (flexible email)
                  Object.keys(localStorage).some(key => key.startsWith('userProfile_') && 
                    localStorage.getItem(key)?.includes('"role":"admin"')) ||
                  window.location.pathname.includes('/admin');

  // Auto-set admin override for admin@sting.local users
  React.useEffect(() => {
    if (user && user.email === 'admin@sting.local') {
      localStorage.setItem('temp-admin-override', 'true');
    }
  }, [user]);

  // Build menu items from configuration
  const menuItems = [];
  
  if (navConfig) {
    // Add persistent items
    const persistentItems = navConfig.persistent ? navConfig.persistent.filter(item => 
      item.enabled && (!item.adminOnly || isAdmin)
    ) : [];
    
    // Add scrollable items
    const scrollableItems = navConfig.scrollable ? navConfig.scrollable.filter(item => 
      item.enabled && (!item.adminOnly || isAdmin)
    ) : [];
    
    // Combine items
    [...persistentItems, ...scrollableItems].forEach(item => {
      const IconComponent = lucideIconMap[item.icon] || BarChart;
      menuItems.push({
        path: item.path,
        name: item.name,
        icon: IconComponent,
        badge: item.badge
      });
    });
  }

  const colors = {
    dark: {
      sidebar: 'bg-slate-700',
      text: 'text-gray-100',
      hover: 'hover:text-white hover:bg-slate-600',
    },
    light: {
      sidebar: 'bg-white',
      text: 'text-gray-800',
      hover: 'hover:text-gray-900 hover:bg-gray-50',
    },
    yellow: {
      sidebar: 'bg-amber-500',
      text: 'text-gray-900',
      hover: 'hover:text-gray-900 hover:bg-amber-400',
    },
  };

  const currentColors = colors[colorScheme];

  return (
    <div className={`w-56 ${currentColors.sidebar} shadow-lg rounded-r-3xl p-5 flex flex-col`}>
      {/* Logo and title removed - using floating nav approach */}

      <nav className="flex-grow">
        <ul>
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                 className={`flex items-center py-3 px-3 mb-2 rounded-lg ${currentColors.text} ${
                   location.pathname === item.path
                     ? 'bg-amber-600 text-white'
                     : currentColors.hover
                 } transition-colors duration-200`}
               >
                 {React.createElement(item.icon, { className: "mr-3 w-5 h-5 flex-shrink-0" })}
                 <span className="flex-1">{item.name}</span>
                 {item.badge && (
                   <span className="bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full ml-2">
                     {item.badge}
                   </span>
                 )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;