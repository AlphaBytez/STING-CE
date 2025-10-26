import React, { useState, useEffect } from 'react';
import { User, Mail, Shield, Key } from 'lucide-react';
// Removed SuperTokens; use Ory Kratos to fetch session

const UserProfile = () => {
  const [profile, setProfile] = useState({
    email: '',
    role: '',
    name: '',
    avatar: null,
    joinDate: '',
    lastActive: '',
  });
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const loadProfile = async () => {
      const kratosUrl = process.env.REACT_APP_KRATOS_PUBLIC_URL || 'https://localhost:4433';
      try {
        const res = await fetch(`${kratosUrl}/sessions/whoami`, { credentials: 'include' });
        if (!res.ok) {
          throw new Error('Not authenticated');
        }
        const data = await res.json();
        const traits = data.identity.traits || {};
        setProfile({
          email: traits.email || '',
          role: traits.role || 'user',
          name: traits.name || traits.email?.split('@')[0] || 'User',
          joinDate: new Date().toLocaleDateString(),
          lastActive: new Date().toLocaleDateString(),
        });
      } catch (err) {
        console.error('Failed to load profile:', err);
      }
    };
    loadProfile();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In a real app, you'd make an API call to update the profile
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setIsEditing(false);
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">User Profile</h2>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg hover:bg-yellow-500"
          >
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
            <Mail className="w-6 h-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Email</p>
              <p className="font-medium">{profile.email}</p>
            </div>
          </div>

          <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
            <Shield className="w-6 h-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Role</p>
              {isEditing ? (
                <select
                  value={profile.role}
                  onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                  className="border rounded px-2 py-1"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="moderator">Moderator</option>
                </select>
              ) : (
                <p className="font-medium capitalize">{profile.role}</p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
            <User className="w-6 h-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Name</p>
              {isEditing ? (
                <input
                  type="text"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="border rounded px-2 py-1"
                />
              ) : (
                <p className="font-medium">{profile.name}</p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
            <Key className="w-6 h-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Two-Factor Authentication</p>
              <button className="text-yellow-600 hover:text-yellow-700">
                Enable 2FA
              </button>
            </div>
          </div>
        </div>

        {isEditing && (
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg hover:bg-yellow-500 disabled:opacity-50"
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}

        <div className="mt-6 border-t pt-6">
          <h3 className="text-lg font-semibold mb-4">Account Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Join Date</p>
              <p>{profile.joinDate}</p>
            </div>
            <div>
              <p className="text-gray-600">Last Active</p>
              <p>{profile.lastActive}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;