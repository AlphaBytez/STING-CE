# STING Frontend

The frontend interface for STING (Security Threat Intelligence Next Generation) built with React and modern UI libraries.

## Features

- **Modern React Application** - Built with Create React App and functional components
- **STING V2 Theme** - Custom dark theme with floating design elements and glass morphism effects
- **Authentication** - Integrated with Ory Kratos for secure user management and WebAuthn support
- **Responsive Design** - Mobile-first approach with responsive layouts
- **Real-time Chat** - Interactive chat interface with AI capabilities
- **Dashboard Analytics** - Comprehensive security analytics and monitoring
- **Team Management** - Collaborative tools for security teams

## Tech Stack

### Core Framework
- **React** (18.x) - JavaScript library for building user interfaces
- **React Router** - Declarative routing for React applications
- **Create React App (CRACO)** - Build tooling and configuration

### UI Framework & Design System
- **Ant Design** (5.x) - Enterprise-class UI design language and React components
  - Provides comprehensive set of high-quality React components
  - Built-in design tokens and theming system
  - Accessibility features and internationalization support
- **Tailwind CSS** - Utility-first CSS framework for custom styling
- **Lucide React** - Beautiful & consistent icon library

### Authentication & Security
- **Ory Kratos** - Open source identity and user management system
- **WebAuthn** - Passwordless authentication with passkeys and biometrics
- **Axios** - HTTP client for API communication

### State Management & Context
- **React Context API** - Theme management and application state
- **Custom Hooks** - Reusable logic for authentication and UI state

## Design System

### STING V2 Theme
The application uses a custom design system built on top of Ant Design:

- **Color Palette**: Dark theme with STING yellow (#eab308) accents
- **Typography**: Inter font family for modern readability
- **Glass Morphism**: Semi-transparent elements with backdrop blur effects
- **Floating Design**: Modern floating navigation and action buttons
- **Elevation System**: Consistent shadow and depth hierarchy

### Key Theme Features
- **Responsive Breakpoints** - Mobile-first design approach
- **Dark Mode Optimized** - High contrast for security monitoring environments
- **Accessibility Compliant** - WCAG guidelines adherence
- **Animation System** - Smooth transitions and micro-interactions

## Project Structure

```
src/
├── components/          # React components
│   ├── auth/           # Authentication components
│   ├── chat/           # Chat interface components
│   ├── dashboard/      # Dashboard widgets
│   ├── layout/         # Layout components
│   ├── pages/          # Page components
│   └── user/           # User management components
├── context/            # React Context providers
├── theme/              # Theme configuration and styles
│   ├── stingTheme.js   # Ant Design theme configuration
│   ├── floating-design.css # Floating UI utilities
│   └── *.css           # Additional stylesheets
├── auth/               # Authentication logic
└── utils/              # Utility functions
```

## Development

### Prerequisites
- Node.js (16.x or higher)
- npm or yarn

### Installation
```bash
npm install
```

### Development Server
```bash
npm start
```

### Building for Production
```bash
npm run build
```

## Open Source Credits & Acknowledgements

This project is built upon the excellent work of many open source projects. We are grateful to the maintainers and contributors of:

### Core Dependencies
- **[React](https://reactjs.org/)** - Meta (Facebook) - MIT License
  - The foundational library powering our user interface
- **[Ant Design](https://ant.design/)** - Ant Design Team - MIT License
  - Comprehensive React UI library providing our design system foundation
  - Enterprise-grade components with built-in accessibility and theming
- **[React Router](https://reactrouter.com/)** - Remix Software - MIT License
  - Client-side routing and navigation

### UI & Styling
- **[Tailwind CSS](https://tailwindcss.com/)** - Tailwind Labs - MIT License
  - Utility-first CSS framework for custom styling
- **[Lucide React](https://lucide.dev/)** - Lucide Contributors - ISC License
  - Beautiful icon library with consistent design
- **[React Intl](https://formatjs.io/docs/react-intl/)** - FormatJS - BSD-3-Clause License
  - Internationalization library

### Build Tools & Configuration
- **[Create React App](https://create-react-app.dev/)** - Meta (Facebook) - MIT License
  - Build tooling and development environment
- **[CRACO](https://craco.js.org/)** - CRACO Team - MIT License
  - Create React App Configuration Override

### Authentication & Security
- **[Ory Kratos](https://www.ory.sh/kratos/)** - Ory Corp - Apache License 2.0
  - Modern identity and user management system
- **[Axios](https://axios-http.com/)** - Matt Zabriskie - MIT License
  - Promise-based HTTP client

### Development Dependencies
- **[ESLint](https://eslint.org/)** - ESLint Team - MIT License
- **[Prettier](https://prettier.io/)** - Prettier Team - MIT License

## Theme Configuration

The STING V2 theme is configured in `/src/theme/stingTheme.js` and leverages Ant Design's theming system:

```javascript
import { stingTheme } from './theme/stingTheme';

// Applied via ConfigProvider in App.js
<ConfigProvider theme={stingTheme}>
  {/* Application components */}
</ConfigProvider>
```

### Floating Design Elements
Custom CSS utilities in `/src/theme/floating-design.css` provide:
- Glass morphism effects with backdrop blur
- Floating navigation with smooth animations
- Elevation shadows and hover effects
- Responsive design for mobile devices

## License

This project incorporates various open source libraries, each with their own licenses. Please see individual package licenses for details. The STING application code follows the project's main license.

## Contributing

When contributing to the frontend:
1. Follow the established component patterns
2. Use Ant Design components when possible for consistency
3. Maintain the STING theme design tokens
4. Ensure mobile responsiveness
5. Add proper TypeScript types for new features
6. Update this README when adding new dependencies

## Support

For questions about the UI framework choices or theme implementation, please refer to:
- [Ant Design Documentation](https://ant.design/docs/react/introduce)
- [React Documentation](https://reactjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)