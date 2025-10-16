import React from 'react';
import { IntlProvider } from 'react-intl';
import { ConfigProvider } from 'antd';
import AuthenticationWrapper from './auth/AuthenticationWrapper';
import { ThemeProvider as NewThemeProvider } from './components/theme/ThemeManager';
import { ThemeProvider as LegacyThemeProvider } from './context/ThemeContext';
import { RoleProvider } from './components/user/RoleContext';
import { NotificationProvider } from './context/NotificationContext';

// Import custom themes
import './theme/ory-theme.css';
import './theme/modern-typography.css';
import './theme/floating-design.css';
// Import mobile utilities
import './styles/mobile-utilities.css';
// Import base styles
import './index.css';

function App() {
  return (
    // Wrap the app with IntlProvider for internationalization
    <IntlProvider locale="en" defaultLocale="en">
      {/* Wrap the app with Ant Design ConfigProvider with default theme */}
      <ConfigProvider>
        {/* Wrap with NewThemeProvider for CSS-based theming */}
        <NewThemeProvider>
          {/* Wrap with LegacyThemeProvider for backwards compatibility */}
          <LegacyThemeProvider>
            {/* Wrap the app with NotificationProvider for global notifications */}
            <NotificationProvider>
              {/* Wrap the app with RoleProvider for role-based access control */}
              <RoleProvider>
                {/* Use the new authentication wrapper instead of direct AppRoutes */}
                <AuthenticationWrapper />
              </RoleProvider>
            </NotificationProvider>
          </LegacyThemeProvider>
        </NewThemeProvider>
      </ConfigProvider>
    </IntlProvider>
  );
}

export default App;
