import React, { useState } from 'react';
import { User, Settings, LogOut, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useProfile } from '../../context/ProfileContext';
import { useKratos } from '../../auth/KratosProvider';
import BeeProfileAvatar from '../icons/BeeProfileAvatar';
import SimpleHiveAvatar from '../icons/SimpleHiveAvatar';

const ProfileAvatar = () => {
  const navigate = useNavigate();
  const { logout, identity } = useKratos();
  const { profilePicture, getDisplayName, getInitials } = useProfile();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const handleLogout = () => {
    console.log('ProfileAvatar: Logout button clicked - calling logout()');
    // The logout function will handle the redirect
    logout();
  };

  const goToSettings = () => {
    navigate('/dashboard/settings');
    setIsDropdownOpen(false);
  };

  const goToProfile = () => {
    navigate('/dashboard/profile');
    setIsDropdownOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-700 transition-colors"
      >
        {/* Profile Picture with Bee Theme */}
        {/* Option 1: Honeycomb hexagon style (current) */}
        <BeeProfileAvatar 
          size={32}
          initials={getInitials()}
          profileImageUrl={profilePicture}
          variant="honeycomb"  // Try: 'honeycomb', 'circle', or 'hexagon'
          className="hover:scale-110 transition-transform duration-200"
        />
        
        {/* Option 2: Simple circular style - uncomment to use */}
        {/* <SimpleHiveAvatar 
          size={32}
          initials={getInitials()}
          profileImageUrl={profilePicture}
          isOnline={true}
          className="hover:scale-110 transition-transform duration-200"
        /> */}
        
        {/* Name and Email */}
        <div className="hidden md:block text-left">
          <p className="text-sm font-medium text-white">{getDisplayName()}</p>
          <p className="text-xs text-gray-400">{identity?.traits?.email}</p>
        </div>
        
        {/* Dropdown Arrow */}
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isDropdownOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsDropdownOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 mt-2 w-56 bg-gray-800 rounded-lg shadow-xl border border-gray-700 z-20">
            <div className="p-3 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <BeeProfileAvatar 
                  size={40}
                  initials={getInitials()}
                  profileImageUrl={profilePicture}
                  variant="honeycomb"
                  isOnline={true}
                />
                <div>
                  <p className="text-sm font-medium text-white">{getDisplayName()}</p>
                  <p className="text-xs text-gray-400">{identity?.traits?.email}</p>
                </div>
              </div>
            </div>
            
            <div className="py-2">
              <button
                onClick={goToProfile}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
              >
                <User className="w-4 h-4" />
                View Profile
              </button>
              
              <button
                onClick={goToSettings}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
            </div>
            
            <div className="border-t border-gray-700 py-2">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-gray-700 hover:text-red-300 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ProfileAvatar;