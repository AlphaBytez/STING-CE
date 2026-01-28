import React from 'react';
import { Shield } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const PasskeySettingsTest = () => {
  const { themeColors } = useTheme();

  return (
    <div className="dashboard-card">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Passkey Management (Test)</h2>
        </div>
        <p className="text-gray-300">This is a test component to isolate the Box error.</p>
      </div>
    </div>
  );
};

export default PasskeySettingsTest;