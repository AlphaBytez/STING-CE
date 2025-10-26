import React, { createContext, useContext, useState, useEffect } from 'react';
import { useKratos } from '../auth/KratosProvider';

const ProfileContext = createContext();

export const useProfile = () => {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfile must be used within a ProfileProvider');
  }
  return context;
};

export const ProfileProvider = ({ children }) => {
  const { identity, isAuthenticated } = useKratos();
  const [profilePicture, setProfilePicture] = useState(null);
  const [profileData, setProfileData] = useState({});

  // Load profile data from localStorage on mount and when authentication changes
  useEffect(() => {
    if (isAuthenticated && identity?.traits?.email) {
      // Create a user-specific key for profile data
      const userProfileKey = `userProfile_${identity.traits.email}`;
      const savedProfile = localStorage.getItem(userProfileKey);
      
      if (savedProfile) {
        try {
          const parsed = JSON.parse(savedProfile);
          setProfileData(parsed);
          setProfilePicture(parsed.profilePicture);
          console.log('[ProfileContext] Loaded profile for user:', identity.traits.email);
        } catch (error) {
          console.error('[ProfileContext] Error parsing saved profile:', error);
        }
      } else {
        // Also check for legacy profile data
        const legacyProfile = localStorage.getItem('userProfile');
        if (legacyProfile) {
          try {
            const parsed = JSON.parse(legacyProfile);
            // Migrate to user-specific key
            localStorage.setItem(userProfileKey, legacyProfile);
            localStorage.removeItem('userProfile');
            setProfileData(parsed);
            setProfilePicture(parsed.profilePicture);
            console.log('[ProfileContext] Migrated legacy profile to user-specific key');
          } catch (error) {
            console.error('[ProfileContext] Error migrating legacy profile:', error);
          }
        }
      }
    }
  }, [isAuthenticated, identity]);

  // Update profile picture
  const updateProfilePicture = (imageData) => {
    if (!identity?.traits?.email) {
      console.warn('[ProfileContext] Cannot save profile picture: no user email');
      return;
    }
    
    setProfilePicture(imageData);
    const updatedProfile = { ...profileData, profilePicture: imageData };
    setProfileData(updatedProfile);
    
    // Save with user-specific key
    const userProfileKey = `userProfile_${identity.traits.email}`;
    localStorage.setItem(userProfileKey, JSON.stringify(updatedProfile));
    console.log('[ProfileContext] Saved profile picture for user:', identity.traits.email);
  };

  // Update profile data
  const updateProfileData = (data) => {
    if (!identity?.traits?.email) {
      console.warn('[ProfileContext] Cannot save profile data: no user email');
      return;
    }
    
    setProfileData(data);
    setProfilePicture(data.profilePicture);
    
    // Save with user-specific key
    const userProfileKey = `userProfile_${identity.traits.email}`;
    localStorage.setItem(userProfileKey, JSON.stringify(data));
    console.log('[ProfileContext] Saved profile data for user:', identity.traits.email);
  };

  // Get display name
  const getDisplayName = () => {
    if (profileData.displayName) return profileData.displayName;
    if (profileData.firstName || profileData.lastName) {
      return `${profileData.firstName || ''} ${profileData.lastName || ''}`.trim();
    }
    return identity?.traits?.email?.split('@')[0] || 'User';
  };

  // Get initials for avatar
  const getInitials = () => {
    const firstName = profileData.firstName || identity?.traits?.name?.first || '';
    const lastName = profileData.lastName || identity?.traits?.name?.last || '';
    const email = identity?.traits?.email || '';
    
    if (firstName && lastName) {
      return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
    }
    if (firstName) {
      return firstName.charAt(0).toUpperCase();
    }
    if (email) {
      return email.charAt(0).toUpperCase();
    }
    return 'U';
  };

  const value = {
    profilePicture,
    profileData,
    updateProfilePicture,
    updateProfileData,
    getDisplayName,
    getInitials,
  };

  return (
    <ProfileContext.Provider value={value}>
      {children}
    </ProfileContext.Provider>
  );
};