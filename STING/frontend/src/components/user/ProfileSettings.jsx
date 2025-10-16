import React, { useState, useRef, useEffect } from 'react';
import { User, Camera, Upload, Save, X } from 'lucide-react';
import { useKratos } from '../../auth/KratosProvider';
import { useProfile } from '../../context/ProfileContext';
import { resilientGet, resilientPut, fallbackGenerators } from '../../utils/resilientApiClient';
import { handleAuthError } from '../../utils/tieredAuth';

const ProfileSettings = () => {
  const { identity } = useKratos();
  const { profileData, updateProfileData, profilePicture } = useProfile();
  const fileInputRef = useRef(null);
  
  const [profile, setProfile] = useState({
    firstName: '',
    lastName: '',
    displayName: '',
    bio: '',
    location: '',
    website: '',
    profilePicture: null
  });
  
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);

  // Initialize profile data
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        // Create fallback profile data from available sources
        const fallbackProfile = {
          firstName: profileData.firstName || identity?.traits?.name?.first || '',
          lastName: profileData.lastName || identity?.traits?.name?.last || '',
          displayName: profileData.displayName || identity?.traits?.displayName || '',
          bio: profileData.bio || identity?.traits?.bio || '',
          location: profileData.location || identity?.traits?.location || '',
          website: profileData.website || identity?.traits?.website || '',
          profilePicture: profilePicture || identity?.traits?.profilePicture || null
        };
        
        // Fetch the latest profile data from backend with resilient fallback
        const data = await resilientGet(
          '/api/users/profile',
          fallbackProfile,
          { timeout: 5000 }
        );
        
        const profileFromBackend = {
          firstName: data.firstName || data.first_name || fallbackProfile.firstName,
          lastName: data.lastName || data.last_name || fallbackProfile.lastName,
          displayName: data.displayName || data.display_name || fallbackProfile.displayName,
          bio: data.bio || fallbackProfile.bio,
          location: data.location || fallbackProfile.location,
          website: data.website || fallbackProfile.website,
          profilePicture: data.profilePicture || data.profile_picture || fallbackProfile.profilePicture
        };
        
        setProfile(profileFromBackend);
        setPreviewImage(profileFromBackend.profilePicture);
        
        // Update context as well
        updateProfileData(profileFromBackend);
        
      } catch (error) {
        console.error('Error fetching profile:', error);
        // Use Kratos identity as final fallback
        const finalFallback = {
          firstName: identity?.traits?.name?.first || 'Demo',
          lastName: identity?.traits?.name?.last || 'User',
          displayName: identity?.traits?.displayName || 'Demo User',
          bio: identity?.traits?.bio || '',
          location: identity?.traits?.location || '',
          website: identity?.traits?.website || '',
          profilePicture: identity?.traits?.profilePicture || null
        };
        setProfile(finalFallback);
        setPreviewImage(finalFallback.profilePicture);
      }
    };
    
    fetchProfile();
  }, []);

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('Image size must be less than 5MB');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const imageData = e.target.result;
        setPreviewImage(imageData);
        setProfile(prev => ({ ...prev, profilePicture: imageData }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const profilePayload = {
        firstName: profile.firstName,
        lastName: profile.lastName,
        displayName: profile.displayName,
        bio: profile.bio,
        location: profile.location,
        website: profile.website,
        profilePicture: profile.profilePicture
      };

      // Use resilient PUT call with longer timeout for profile updates
      const result = await resilientPut(
        '/api/users/profile',
        profilePayload,
        { timeout: 10000 } // 10 second timeout for profile saves
      );

      // Update the profile context
      updateProfileData(profile);

      // Check if Kratos sync was successful
      if (result.kratos_sync_success) {
        console.log('Profile successfully synced with Kratos');
      } else if (result.kratos_sync_success === false) {
        console.warn('Profile updated locally but Kratos sync failed');
      }

      setIsEditing(false);
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Error saving profile:', error);

      // Check if this is a tiered auth error and redirect if needed
      const handled = handleAuthError(error, 'UPDATE_PROFILE', window.location.pathname);

      if (!handled) {
        // Not a tiered auth error, show generic message
        alert('Failed to save profile. Please check your connection and try again.');
      }
      // If handled = true, user was redirected to security upgrade
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original values
    const originalProfile = {
      firstName: profileData.firstName || identity?.traits?.name?.first || '',
      lastName: profileData.lastName || identity?.traits?.name?.last || '',
      displayName: profileData.displayName || identity?.traits?.displayName || '',
      bio: profileData.bio || identity?.traits?.bio || '',
      location: profileData.location || identity?.traits?.location || '',
      website: profileData.website || identity?.traits?.website || '',
      profilePicture: profilePicture || identity?.traits?.profilePicture || null
    };
    setProfile(originalProfile);
    setPreviewImage(originalProfile.profilePicture);
    setIsEditing(false);
  };

  const getInitials = () => {
    const first = profile.firstName || identity?.traits?.name?.first || '';
    const last = profile.lastName || identity?.traits?.name?.last || '';
    return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || 'U';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-white">Profile Settings</h3>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="floating-button bg-yellow-500 hover:bg-yellow-600 text-black px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <User className="w-4 h-4" />
            Edit Profile
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              className="floating-button bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="floating-button bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      {/* Profile Picture Section */}
      <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-6">
        <h4 className="text-lg font-medium text-white mb-4">Profile Picture</h4>
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="w-24 h-24 rounded-full overflow-hidden bg-gray-600 flex items-center justify-center">
              {previewImage ? (
                <img 
                  src={previewImage} 
                  alt="Profile" 
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-2xl font-bold text-gray-300">{getInitials()}</span>
              )}
            </div>
            {isEditing && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="absolute -bottom-2 -right-2 bg-yellow-500 hover:bg-yellow-600 text-black p-2 rounded-full shadow-lg transition-colors"
              >
                <Camera className="w-4 h-4" />
              </button>
            )}
          </div>
          <div>
            <p className="text-white font-medium">
              {profile.displayName || `${profile.firstName} ${profile.lastName}`.trim() || 'Your Name'}
            </p>
            <p className="text-gray-400 text-sm">{identity?.traits?.email}</p>
            {isEditing && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="mt-2 text-yellow-400 hover:text-yellow-300 text-sm flex items-center gap-1"
              >
                <Upload className="w-3 h-3" />
                Upload new picture
              </button>
            )}
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
        />
      </div>

      {/* Basic Information */}
      <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-6">
        <h4 className="text-lg font-medium text-white mb-4">Basic Information</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">First Name</label>
            {isEditing ? (
              <input
                type="text"
                value={profile.firstName}
                onChange={(e) => setProfile(prev => ({ ...prev, firstName: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                placeholder="Enter your first name"
              />
            ) : (
              <p className="text-white py-2">{profile.firstName || 'Not set'}</p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Last Name</label>
            {isEditing ? (
              <input
                type="text"
                value={profile.lastName}
                onChange={(e) => setProfile(prev => ({ ...prev, lastName: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                placeholder="Enter your last name"
              />
            ) : (
              <p className="text-white py-2">{profile.lastName || 'Not set'}</p>
            )}
          </div>
          
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">Display Name</label>
            {isEditing ? (
              <input
                type="text"
                value={profile.displayName}
                onChange={(e) => setProfile(prev => ({ ...prev, displayName: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                placeholder="How you'd like to be displayed"
              />
            ) : (
              <p className="text-white py-2">{profile.displayName || 'Not set'}</p>
            )}
          </div>
        </div>
      </div>

      {/* Additional Information */}
      <div className="dynamic-card-subtle bg-gray-700 rounded-xl p-6">
        <h4 className="text-lg font-medium text-white mb-4">Additional Information</h4>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Bio</label>
            {isEditing ? (
              <textarea
                value={profile.bio}
                onChange={(e) => setProfile(prev => ({ ...prev, bio: e.target.value }))}
                rows={3}
                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                placeholder="Tell us about yourself..."
              />
            ) : (
              <p className="text-white py-2">{profile.bio || 'No bio added'}</p>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Location</label>
              {isEditing ? (
                <input
                  type="text"
                  value={profile.location}
                  onChange={(e) => setProfile(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="City, Country"
                />
              ) : (
                <p className="text-white py-2">{profile.location || 'Not set'}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Website</label>
              {isEditing ? (
                <input
                  type="url"
                  value={profile.website}
                  onChange={(e) => setProfile(prev => ({ ...prev, website: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="https://yourwebsite.com"
                />
              ) : (
                <p className="text-white py-2">
                  {profile.website ? (
                    <a href={profile.website} target="_blank" rel="noopener noreferrer" className="text-yellow-400 hover:text-yellow-300">
                      {profile.website}
                    </a>
                  ) : (
                    'Not set'
                  )}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileSettings;