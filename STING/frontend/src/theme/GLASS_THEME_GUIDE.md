# STING CE Glass Theme Design System

## Overview
The STING CE glass morphism theme system provides consistent transparency effects across all UI components. All glass cards use standardized opacity levels, blur effects, and the official STING color palette for brand consistency.

## STING Brand Color Palette
- **Base Glass Color**: `slate-700` (rgb(51, 65, 85)) - The foundation for all glass effects
- **Border Color**: `slate-500` with transparency (rgba(100, 116, 139, 0.3))
- **Text Color**: `slate-100` (#f1f5f9) - High contrast on dark glass
- **Primary Accent**: STING Yellow (#fbbf24) - Brand color for actions and highlights
- **Secondary Accent**: STING Yellow Hover (#f59e0b) - Interactive states
- **Background Hierarchy**:
  - Primary: #0f172a (main background)
  - Secondary: #1e293b (surface background) 
  - Tertiary: #334155 (elevated surfaces)

## Using the GlassCard Component

### Basic Usage
```jsx
import GlassCard from './components/common/GlassCard';

// Default glass card
<GlassCard>
  Your content here
</GlassCard>
```

### Variants
```jsx
// Subtle - More transparent (50% opacity)
<GlassCard variant="subtle">
  Layered or secondary content
</GlassCard>

// Default - Standard glass (70% opacity)
<GlassCard variant="default">
  Main content
</GlassCard>

// Strong - Less transparent (85% opacity)
<GlassCard variant="strong">
  Important or focused content
</GlassCard>

// Ultra - Maximum glass effect (60% opacity)
<GlassCard variant="ultra">
  Hero or featured content
</GlassCard>
```

### Elevation Levels
```jsx
// Low elevation - Subtle shadow
<GlassCard elevation="low">
  Inline or embedded content
</GlassCard>

// Medium elevation - Standard shadow
<GlassCard elevation="medium">
  Regular cards
</GlassCard>

// High elevation - Prominent shadow
<GlassCard elevation="high">
  Important cards or stats
</GlassCard>

// Floating elevation - Maximum shadow
<GlassCard elevation="floating">
  Modals or overlays
</GlassCard>
```

### Combining Props
```jsx
// Statistics card
<GlassCard variant="default" elevation="high">
  <Statistic title="Users" value={1234} />
</GlassCard>

// Activity card
<GlassCard variant="subtle" elevation="low">
  <Timeline items={activities} />
</GlassCard>

// Modal-like card
<GlassCard variant="strong" elevation="floating">
  <Form>...</Form>
</GlassCard>
```

## CSS Classes (for custom components)

### Base Classes
- `.sting-glass-card` - Base glass morphism styles
- `.sting-glass-default` - Default variant (70% opacity)
- `.sting-glass-subtle` - Subtle variant (50% opacity)
- `.sting-glass-strong` - Strong variant (85% opacity)
- `.sting-glass-ultra` - Ultra variant (60% opacity)

### Elevation Classes
- `.sting-elevation-low` - Minimal shadow
- `.sting-elevation-medium` - Standard shadow
- `.sting-elevation-high` - Prominent shadow
- `.sting-elevation-floating` - Maximum shadow

### Special Purpose Classes
- `.sting-stat-card` - For statistics cards
- `.sting-activity-card` - For timeline/activity cards
- `.sting-modal-card` - For modal-like cards

## Migration Guide

### Old Classes → New Component
```jsx
// Before
<Card className="dashboard-card atmospheric-vignette">

// After
<GlassCard elevation="high">
```

```jsx
// Before
<Card className="glass-card">

// After
<GlassCard variant="default" elevation="medium">
```

```jsx
// Before
<Card className="grains-glass">

// After
<GlassCard variant="ultra" elevation="floating">
```

### Theme Updates (January 2025)

#### Navigation System Changes
```jsx
// OLD: Fixed sidebar for all themes
<Sidebar fixed={true} />

// NEW: Dynamic navigation based on theme type
{showFloatingNav && <FloatingNavigation />}
{showTraditionalSidebar && <Sidebar />}
```

#### Color System Updates
```css
/* OLD: Mixed accent colors */
.primary-button { background: #3b82f6; } /* Blue */

/* NEW: Consistent STING branding */
.primary-button { background: #fbbf24; } /* STING Yellow */
```

#### Logo Positioning
```jsx
// OLD: Logo in both header and sidebar
<Header><Logo /></Header>
<Sidebar><Logo /></Sidebar>

// NEW: Logo only in header
<Header><Logo /></Header>
<Sidebar>{/* No logo */}</Sidebar>
```

## Design Principles

1. **Brand Consistency**: All cards use the same base slate-700 color with STING yellow (#fbbf24) accents
2. **Visual Hierarchy**: Use variants and elevation levels to create clear content hierarchy
3. **Readability**: Text is always light (#f1f5f9) on dark glass backgrounds for optimal contrast
4. **Interactive Feedback**: Hover effects increase opacity and add STING yellow borders
5. **Performance**: Backdrop filters automatically reduce on mobile devices
6. **Accessibility**: All color combinations meet WCAG contrast requirements

## Best Practices

1. **Statistics/Metrics**: Use `elevation="high"` for dashboard metrics and KPIs
2. **Content Cards**: Use default variant with `elevation="medium"` for general content
3. **Nested Cards**: Use `variant="subtle"` to avoid visual overwhelm with layered content
4. **Call-to-Actions**: Use `variant="strong"` for cards containing important actions
5. **Navigation Context**: Glass themes use floating navigation, not fixed sidebars
6. **STING Branding**: Ensure yellow (#fbbf24) is used for all primary buttons and highlights
7. **Mobile Optimization**: Glass effects automatically reduce on smaller screens for performance
8. **Brand Consistency**: Never use blue or purple accents - stick to STING yellow and slate colors

## Examples by Page Type

### Dashboard
```jsx
// Stats cards
<GlassCard elevation="high">
  <Statistic ... />
</GlassCard>

// Activity timeline
<GlassCard variant="subtle" elevation="medium">
  <Timeline ... />
</GlassCard>
```

### Forms
```jsx
// Form container
<GlassCard variant="strong" elevation="medium">
  <Form ... />
</GlassCard>
```

### Lists/Tables
```jsx
// Table container
<GlassCard elevation="low">
  <Table ... />
</GlassCard>
```

## Navigation System for Glass Themes

Glass morphism themes use **floating navigation** instead of traditional sidebars:

```css
/* Glass themes show floating nav */
[data-theme="modern-glass"] .floating-nav {
  display: flex !important;
}

/* Glass themes hide traditional sidebar */
[data-theme="modern-glass"] .w-56 {
  display: none !important;
}
```

### Why Floating Navigation?
1. **Visual Cohesion**: Matches the glass morphism aesthetic
2. **Screen Real Estate**: Maximizes content area
3. **Modern UX**: Contemporary interaction patterns
4. **Brand Identity**: Distinguishes from retro terminal themes

## Recent Theme Improvements (2025)

### Standardized Color Palette
- All themes now use consistent STING brand colors
- Yellow (#fbbf24) is the primary brand color across all themes
- Removed blue theme bleeding and inconsistent accent colors

### Logo Standardization
- Removed duplicate logos from sidebars
- Logo and title only appear in main header
- Consistent branding across floating and fixed navigation

### Performance Optimizations
- Glass effects automatically reduce on mobile devices
- Backdrop filters optimized for smooth 60fps animations
- Improved CSS specificity to prevent theme conflicts

## Troubleshooting

### Cards appear too dark/light
- Verify you're using the correct opacity variant (subtle/default/strong)
- Check that no inline styles are overriding the glass background
- Ensure parent container uses proper dark background (#0f172a or #1e293b)

### Wrong navigation showing
- Glass themes should show floating navigation, not fixed sidebar
- Check theme detection logic in MainInterface component
- Verify CSS specificity for navigation display rules

### STING colors not showing
- Primary buttons should use yellow (#fbbf24), not blue or other colors
- Check for theme bleeding from other stylesheets
- Ensure CSS variables are properly scoped to theme data attribute

### Performance issues
- Glass effects automatically reduce on mobile for better performance
- Consider using `variant="subtle"` for heavy content areas
- Limit the number of `elevation="floating"` cards per page
- Test on lower-end devices to verify smooth animations