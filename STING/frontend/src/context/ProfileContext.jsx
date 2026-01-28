import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
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
  const [profilePictureLoading, setProfilePictureLoading] = useState(false);
  const [profileData, setProfileData] = useState({});

  // Fetch profile picture from Vault API
  const fetchProfilePicture = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setProfilePictureLoading(true);
    try {
      const response = await fetch('/api/files/profile/picture', {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        // Convert blob to data URL for display
        const blob = await response.blob();
        const reader = new FileReader();
        reader.onloadend = () => {
          setProfilePicture(reader.result);
          console.log('[ProfileContext] Loaded profile picture from Vault');
        };
        reader.readAsDataURL(blob);
      } else if (response.status === 404) {
        // No profile picture set - this is normal
        setProfilePicture(null);
        console.log('[ProfileContext] No profile picture found (normal for new users)');
      } else {
        console.warn('[ProfileContext] Failed to fetch profile picture:', response.status);
        setProfilePicture(null);
      }
    } catch (error) {
      console.error('[ProfileContext] Error fetching profile picture:', error);
      setProfilePicture(null);
    } finally {
      setProfilePictureLoading(false);
    }
  }, [isAuthenticated]);

  // Load profile picture from Vault when authenticated
  useEffect(() => {
    if (isAuthenticated && identity?.traits?.email) {
      fetchProfilePicture();
      
      // Also load other profile data from localStorage for non-picture fields
      const userProfileKey = `userProfile_${identity.traits.email}`;
      const savedProfile = localStorage.getItem(userProfileKey);
      
      if (savedProfile) {
        try {
          const parsed = JSON.parse(savedProfile);
          // Don't overwrite profilePicture from localStorage - we get it from Vault
          const { profilePicture: _, ...restProfile } = parsed;
          setProfileData(restProfile);
          console.log('[ProfileContext] Loaded profile data for user:', identity.traits.email);
        } catch (error) {
          console.error('[ProfileContext] Error parsing saved profile:', error);
        }
      }
    }
  }, [isAuthenticated, identity, fetchProfilePicture]);

  // Upload profile picture to Vault
  const uploadProfilePicture = async (file) => {
    if (!isAuthenticated) {
      console.warn('[ProfileContext] Cannot upload: not authenticated');
      return { success: false, error: 'Not authenticated' };
    }
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/files/profile/picture', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        // Refresh the profile picture display
        await fetchProfilePicture();
        console.log('[ProfileContext] Profile picture uploaded to Vault');
        return { success: true, ...result };
      } else {
        const error = await response.json();
        console.error('[ProfileContext] Upload failed:', error);
        return { success: false, error: error.error || 'Upload failed' };
      }
    } catch (error) {
      console.error('[ProfileContext] Error uploading profile picture:', error);
      return { success: false, error: error.message };
    }
  };

  // Update profile picture from base64/data URL (converts to file and uploads)
  const updateProfilePicture = async (imageData) => {
    if (!imageData) {
      console.warn('[ProfileContext] No image data provided');
      return { success: false, error: 'No image data' };
    }
    
    try {
      // Convert data URL to Blob
      const response = await fetch(imageData);
      const blob = await response.blob();
      
      // Create a File object
      const file = new File([blob], 'profile-picture.jpg', { type: blob.type || 'image/jpeg' });
      
      // Upload to Vault
      return await uploadProfilePicture(file);
    } catch (error) {
      console.error('[ProfileContext] Error converting and uploading:', error);
      return { success: false, error: error.message };
    }
  };

  // Update profile data (non-picture fields)
  const updateProfileData = (data) => {
    if (!identity?.traits?.email) {
      console.warn('[ProfileContext] Cannot save profile data: no user email');
      return;
    }
    
    // Don't store profilePicture in localStorage - it goes to Vault
    const { profilePicture: _, ...dataWithoutPicture } = data;
    setProfileData(dataWithoutPicture);
    
    // Save non-picture data with user-specific key
    const userProfileKey = `userProfile_${identity.traits.email}`;
    localStorage.setItem(userProfileKey, JSON.stringify(dataWithoutPicture));
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

  // Refresh profile picture (useful after upload)
  const refreshProfilePicture = () => {
    fetchProfilePicture();
  };

  const value = {
    profilePicture,
    profilePictureLoading,
    profileData,
    uploadProfilePicture,
    updateProfilePicture,
    updateProfileData,
    getDisplayName,
    getInitials,
    refreshProfilePicture,
  };

  return (
    <ProfileContext.Provider value={value}>
      {children}
    </ProfileContext.Provider>
  );
};