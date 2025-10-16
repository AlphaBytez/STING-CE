# STING CE Theme Development Guide

This guide helps developers create consistent, comprehensive themes for STING CE using the provided template system.

## Quick Start

1. **Copy the Template**
   ```bash
   cp THEME_TEMPLATE.css your-theme-name.css
   ```

2. **Replace Placeholders**
   - Find and replace all `[THEME-NAME]` with your theme's data-theme attribute
   - Example: `[THEME-NAME]` → `cyberpunk-neon`

3. **Define Your Color Palette**
   - Update all CSS variables in the `:root` section
   - Use a consistent color system (consider tools like Coolors.co or Adobe Color)

4. **Test Systematically**
   - Use the provided checklist at the bottom of the template
   - Test each major UI component category

## Theme Architecture

### 1. CSS Variable System
All themes use a standardized variable system for consistency:

```css
:root[data-theme="your-theme"] {
  /* Primary colors - your brand identity */
  --primary-color: #your-color;
  --primary-hover: #hover-variant;
  
  /* Background hierarchy */
  --bg-primary: #main-background;
  --bg-secondary: #surface-background;
  --bg-elevated: #raised-surfaces;
  
  /* Text hierarchy */
  --text-primary: #main-text;
  --text-secondary: #secondary-text;
  --text-tertiary: #subtle-text;
}
```

### 2. Component Categories

The template covers these major component categories:

| Category | Components | Priority |
|----------|------------|----------|
| **Navigation** | Floating nav, sidebar, breadcrumbs | High |
| **Authentication** | Login, register, TOTP, password change | High |
| **Dashboard** | Cards, widgets, metrics, charts | High |
| **Forms** | Inputs, buttons, selects, validation | High |
| **Tables & Lists** | Data tables, navigation lists | Medium |
| **Modals & Overlays** | Dialogs, tooltips, notifications | Medium |
| **Chat Interface** | Bee Chat components, message bubbles | Medium |
| **Admin Panel** | User management, system settings | Medium |
| **Settings** | Theme switcher, preferences | Medium |
| **Honey Jars** | Knowledge base, document upload | Medium |
| **Reports** | Charts, data visualization | Low |
| **Mobile** | Responsive behavior, touch targets | High |
| **Accessibility** | Focus states, high contrast, reduced motion | High |

## Theme Types & Examples

### Glass Morphism Themes
**Characteristics**: Transparency, blur effects, subtle borders
**Examples**: Modern Glass Premium (default), Sting Glass Theme
**Key Features**:
- `backdrop-filter: blur()`
- Semi-transparent backgrounds (rgba with opacity)
- Subtle borders and shadows
- Smooth transitions and hover effects
- Uses slate-700 (rgb(51, 65, 85)) as base color

### Performance Themes  
**Characteristics**: Minimal animations, simple styling, fast rendering
**Examples**: Minimal Performance, Retro Performance, Modern Lite
**Key Features**:
- `animation: none !important;`
- `transition: none !important;`
- Solid colors instead of gradients
- No backdrop filters or blur effects
- Minimal shadows and effects
- Hardware acceleration optimizations

### Retro/Terminal Themes
**Characteristics**: Monospace fonts, green-on-black, CRT styling
**Examples**: Retro Theme, Retro Performance
**Key Features**:
- Monospace font families (JetBrains Mono, Courier New)
- High contrast terminal colors (#00ff41 green, #ffffff white on #000000 black)
- Terminal-style borders and sharp edges
- Traditional fixed sidebar instead of floating navigation
- STING yellow (#fbbf24) for primary actions

### Modern Themes
**Characteristics**: Clean design, subtle animations, contemporary colors
**Examples**: Modern Lite Theme, Modern Typography
**Key Features**:
- Clean geometric shapes with rounded borders
- STING brand colors (yellow #fbbf24 primary)
- Subtle gradients and shadows
- Smooth micro-interactions
- Contemporary dark slate color palettes

## Development Workflow

### 1. Planning Phase
- [ ] Define your theme's visual identity
- [ ] Choose a color palette (5-8 core colors)
- [ ] Decide on typography (font stack, sizes, weights)
- [ ] Plan special effects (glass, neon, shadows, etc.)
- [ ] Consider performance implications

### 2. Implementation Phase
- [ ] Set up base colors and variables
- [ ] Implement navigation systems (both floating and sidebar)
- [ ] Style authentication flows
- [ ] Implement form elements and buttons
- [ ] Add dashboard components
- [ ] Style data tables and lists
- [ ] Implement modals and overlays
- [ ] Add special effects and animations

### 3. Testing Phase
- [ ] Test all authentication flows
- [ ] Test admin panel functionality
- [ ] Test responsive behavior on mobile
- [ ] Test accessibility with keyboard navigation
- [ ] Test performance with large datasets
- [ ] Cross-browser testing

### 4. Polish Phase
- [ ] Fine-tune spacing and proportions
- [ ] Optimize animations and transitions
- [ ] Add loading states and micro-interactions
- [ ] Document theme-specific features
- [ ] Create theme preview screenshots

## Theme Registration

After creating your theme, register it in the theme system:

1. **Add to Theme List** (`ThemeSettings.jsx`):
   ```javascript
   const availableThemes = [
     // ... existing themes
     {
       id: 'your-theme-name',
       name: 'Your Theme Display Name',
       description: 'Brief description of your theme',
       category: 'modern|retro|performance|glass',
       preview: '/theme/your-theme-preview.png'
     }
   ];
   ```

2. **Import CSS** (in main CSS import file):
   ```css
   @import 'your-theme-name.css';
   ```

3. **Add Preview Image**:
   - Create a 400x300px preview image
   - Place in `/frontend/public/theme/`
   - Show key UI elements (header, sidebar, cards)

## Best Practices

### Color Systems
- **Use HSL for easier variations**: `hsl(210, 100%, 50%)`
- **Maintain 4.5:1 contrast ratio** for accessibility
- **Test in both light and dark environments**
- **Consider colorblind users** (use tools like Stark plugin)

### Performance
- **Minimize blur effects** on lower-end devices
- **Use `will-change` sparingly** and remove after animations
- **Prefer `transform` over changing layout properties**
- **Test on mobile devices** for performance

### Consistency
- **Use the variable system** instead of hardcoded colors
- **Follow established patterns** from existing themes
- **Test all interactive states** (hover, focus, active, disabled)
- **Maintain consistent spacing** using the spacing scale

### Accessibility
- **Always provide focus indicators**
- **Support high contrast mode**: `@media (prefers-contrast: high)`
- **Support reduced motion**: `@media (prefers-reduced-motion: reduce)`
- **Test with screen readers**
- **Ensure touch targets are at least 44x44px**

## Testing Checklist

### Component Testing
- [ ] **Authentication**: Login, register, TOTP setup, password change
- [ ] **Navigation**: Floating nav, sidebar, breadcrumbs, mobile menu
- [ ] **Dashboard**: All widget types, system health, metrics
- [ ] **Forms**: All input types, validation states, buttons
- [ ] **Tables**: Data tables, sortable headers, row actions
- [ ] **Modals**: All dialog types, tooltips, notifications
- [ ] **Settings**: Theme switcher, all settings pages
- [ ] **Admin Panel**: User management, all admin tabs
- [ ] **Chat**: Message bubbles, input area, typing indicators
- [ ] **Honey Jars**: Grid view, cards, upload areas

### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (if on macOS)
- [ ] Edge (latest)

### Device Testing
- [ ] Desktop (1920x1080+)
- [ ] Laptop (1366x768)
- [ ] Tablet (iPad, Android tablet)
- [ ] Mobile (iPhone, Android phone)

### Accessibility Testing
- [ ] Keyboard navigation (Tab, Enter, Space, Escape)
- [ ] Screen reader compatibility (VoiceOver, NVDA)
- [ ] High contrast mode
- [ ] Reduced motion preference
- [ ] Color contrast ratios
- [ ] Focus indicators visibility

## Common Pitfalls

1. **Forgetting Mobile**: Always test responsive behavior early
2. **Inconsistent Spacing**: Use the spacing scale variables consistently
3. **Poor Contrast**: Check text readability in all color combinations
4. **Missing Focus States**: Every interactive element needs focus styling
5. **Overusing Animations**: Performance themes should minimize animations
6. **Hard-coded Colors**: Always use CSS variables for maintainability
7. **Ignoring Dark Mode**: Consider how your theme works in dark environments
8. **Missing States**: Test hover, focus, active, and disabled states
9. **Inconsistent Icons**: Maintain consistent icon sizes across components
10. **Performance Issues**: Test with large datasets and slow devices

## Theme Examples

### Minimal Example (Performance Focus)
```css
:root[data-theme="ultra-minimal"] {
  --primary-color: #2563eb;
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --text-primary: #1e293b;
  --border-primary: #e2e8f0;
  --transition-fast: none; /* No animations */
}

/* Remove all animations */
[data-theme="ultra-minimal"] * {
  animation: none !important;
  transition: none !important;
}
```

### Glass Example (Visual Focus)
```css
:root[data-theme="frosted-glass"] {
  --primary-color: #6366f1;
  --bg-primary: rgba(15, 23, 42, 0.8);
  --bg-elevated: rgba(30, 41, 59, 0.9);
  --glass-blur: blur(20px);
}

[data-theme="frosted-glass"] .glass-effect {
  backdrop-filter: var(--glass-blur);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
```

### Retro/Terminal Example
```css
:root[data-theme="cyber-terminal"] {
  /* Terminal colors */
  --primary-color: #fbbf24;        /* STING yellow */
  --secondary-color: #00ff41;      /* Terminal green */
  
  /* Terminal backgrounds */
  --bg-primary: #000000;           /* Pure black */
  --bg-secondary: #0a0a0a;         /* Very dark */
  --bg-tertiary: #1a1a1a;          /* Panels */
  
  /* Terminal text */
  --text-primary: #ffffff;         /* Pure white */
  --text-secondary: #00ff41;       /* Terminal green */
  --text-muted: #888888;
  --text-inverse: #000000;
  
  /* Borders */
  --border-primary: #006600;       /* Dark green */
  --border-bright: #00ff41;        /* Bright green */
  
  /* Typography */
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
  
  /* Performance */
  --transition: none;              /* No animations for performance */
  --radius: 0;                     /* Sharp terminal edges */
}

/* Remove all effects for terminal authenticity and performance */
[data-theme="cyber-terminal"] * {
  animation: none !important;
  transition: none !important;
  backdrop-filter: none !important;
  filter: none !important;
  text-shadow: none !important;
  box-shadow: none !important;
}

/* Terminal styling */
[data-theme="cyber-terminal"] {
  font-family: var(--font-mono);
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* Use fixed sidebar for retro themes */
[data-theme="cyber-terminal"] .floating-nav {
  display: none !important;
}

[data-theme="cyber-terminal"] .w-56 {
  position: fixed !important;
  background: var(--bg-secondary) !important;
  border-right: 2px solid var(--border-bright) !important;
}

/* Terminal buttons */
[data-theme="cyber-terminal"] button {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  font-family: var(--font-mono);
}

[data-theme="cyber-terminal"] button:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-bright);
}

/* Primary actions use STING yellow */
[data-theme="cyber-terminal"] .ant-btn-primary {
  background: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  color: var(--text-inverse) !important;
}
```

## Resources

- **Color Tools**: [Coolors.co](https://coolors.co), [Adobe Color](https://color.adobe.com)
- **Accessibility**: [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- **CSS Variables**: [MDN CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- **Glass Effects**: [CSS Tricks Glass Morphism](https://css-tricks.com/glassmorphism/)
- **Performance**: [Web.dev Performance](https://web.dev/performance/)

## Contributing

When contributing themes to STING CE:

1. Follow this template structure
2. Include comprehensive testing
3. Provide preview screenshots
4. Document any special features
5. Ensure accessibility compliance
6. Test across multiple devices and browsers

## Need Help?

- Check existing themes for reference patterns
- Use the browser dev tools to inspect current styling
- Test early and often across different components
- Ask for feedback from other developers
- Consider performance implications of visual effects

---

*Remember: A great theme is not just visually appealing, but also accessible, performant, and consistent across all components.*