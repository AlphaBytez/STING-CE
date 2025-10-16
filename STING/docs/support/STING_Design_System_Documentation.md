# STING Design System Documentation

## Overview

STING employs a sophisticated dark-themed design system with glass morphism effects, creating a modern, premium enterprise application experience. The design philosophy centers around the bee metaphor, with STING yellow as the primary accent color against dark slate backgrounds.

## Core Design Principles

### 1. **Glass Morphism & Transparency**
- Extensive use of backdrop filters for depth and layering
- Multiple transparency levels for visual hierarchy
- Blur effects ranging from 16px to 50px for different components
- Saturation boosts (140%-220%) to enhance vibrancy through glass

### 2. **Dark Theme Foundation**
- Primary background: Slate-800 (#1e293b)
- Card backgrounds: Slate-700 (#334155) with transparency
- Light sidebar: Slate-200 (#e2e8f0) - perfect contrast for bee logo
- Excellent readability with light text on dark backgrounds

### 3. **Floating Design Language**
- Cards appear to float above the background
- Multiple elevation levels with sophisticated shadow systems
- Hover effects that lift elements with transform and scale
- Atmospheric vignette effects for depth perception

## Color Palette

### Primary Colors
```css
/* STING Yellow - Primary Brand Color */
--color-primary: #eab308;
--color-primary-hover: #d97706;
--color-primary-active: #b45309;

/* Background Colors */
--color-bg-layout: #1e293b;      /* Main background (slate-800) */
--color-bg-container: #334155;   /* Cards & panels (slate-700) */
--color-bg-elevated: #475569;    /* Modals & dropdowns (slate-600) */
--color-bg-spotlight: #e2e8f0;   /* Sidebar (slate-200) */
```

### Text Colors
```css
--color-text: #f1f5f9;           /* Primary text (slate-100) */
--color-text-secondary: #cbd5e1;  /* Muted text (slate-300) */
--color-text-tertiary: #94a3b8;  /* Labels (slate-400) */
--color-text-quaternary: #64748b; /* Disabled (slate-500) */
```

### Semantic Colors
```css
--color-success: #10b981;    /* Emerald-500 */
--color-error: #ef4444;      /* Red-500 */
--color-warning: #f59e0b;    /* Amber-500 */
--color-info: #06b6d4;       /* Cyan-500 (matches bee wings) */
```

## Typography

### Font System
- **Primary Font**: Inter
- **Monospace**: System mono fonts
- **Font Sizes**: 14px base, scaling from xs (12px) to 4xl (36px)
- **Line Heights**: Optimized for readability
- **Font Weights**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

### Hierarchy
```css
/* Headings */
h1: 32px, weight 600
h2: 24px, weight 600
h3: 20px, weight 600
h4: 16px, weight 600
h5: 14px, weight 600

/* Body Text */
body: 14px, weight 400
small: 12px, weight 400
```

## Glass Morphism System

### Glass Variants

#### 1. **Subtle Glass** (25% opacity)
```css
background: rgba(45, 55, 72, 0.25);
backdrop-filter: blur(24px) saturate(150%) brightness(103%);
```

#### 2. **Medium Glass** (35% opacity)
```css
background: rgba(45, 55, 72, 0.35);
backdrop-filter: blur(32px) saturate(170%) brightness(105%);
```

#### 3. **Strong Glass** (45% opacity)
```css
background: rgba(45, 55, 72, 0.45);
backdrop-filter: blur(40px) saturate(190%) brightness(107%);
```

#### 4. **Ultra Glass** (60% opacity)
```css
background: rgba(55, 65, 81, 0.5);
backdrop-filter: blur(40px) saturate(220%) brightness(115%) contrast(105%);
```

### Special Glass Effects

#### Dashboard Cards
- Heavy glass effect with 65% opacity
- Extreme shadow depth (6 layers)
- Atmospheric vignette on hover
- Border glow with STING yellow on interaction

#### Pollen Basket Glass
- Named after bee's pollen-carrying structure
- 60% opacity with heavy blur (35px)
- Dramatic shadow cascade
- Enhanced hover state with yellow border accent

## Elevation & Shadow System

### Elevation Levels

#### Level 1 - Surface
```css
box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 
            0 1px 2px -1px rgba(0, 0, 0, 0.1);
```

#### Level 2 - Raised
```css
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
            0 2px 4px -2px rgba(0, 0, 0, 0.1);
```

#### Level 3 - Elevated
```css
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 
            0 4px 6px -4px rgba(0, 0, 0, 0.1);
```

#### Level 4 - Floating
```css
box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 
            0 8px 10px -6px rgba(0, 0, 0, 0.1);
```

#### Dashboard Card (Extreme)
```css
/* 6-layer shadow system for maximum depth */
box-shadow: 
  0 50px 100px rgba(0, 0, 0, 0.4),
  0 25px 50px rgba(0, 0, 0, 0.3),
  0 12px 24px rgba(0, 0, 0, 0.2),
  0 6px 12px rgba(0, 0, 0, 0.15),
  0 3px 6px rgba(0, 0, 0, 0.1),
  0 1px 3px rgba(0, 0, 0, 0.05);
```

## Animation & Interactions

### Transition Timing
```css
/* Standard cubic-bezier for smooth, natural movement */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Hover Effects
1. **Lift Animation**: `translateY(-4px)` to `translateY(-12px)`
2. **Scale Enhancement**: `scale(1.01)` to `scale(1.025)`
3. **Glass Intensification**: Increased blur and saturation
4. **Border Glow**: Yellow accent appears on hover
5. **Shadow Expansion**: Shadows grow dramatically

### Special Animations
- **Fade In Up**: Elements appear with upward motion
- **Fade In Scale**: Elements scale up on appearance
- **Polish Shine**: Sliding highlight effect on hover
- **Atmospheric Vignette**: Radial gradient shadow expands

## Component Patterns

### Floating Navigation
- Fixed position with `translateY(-50%)`
- Compact vertical nav with icon + label
- Active state: Yellow background with black text
- Badge positioning optimized for vertical layout

### Floating Action Buttons (FAB)
- Primary: 56px circular, STING yellow
- Secondary: 48px circular, slate background
- Fixed bottom-right positioning
- Elevated shadow with color tint

### Card Styles
1. **Standard Glass Card**: Default for most content
2. **Dashboard Card**: Maximum elevation and glass effect
3. **Stats Card**: Enhanced hover with metrics display
4. **Activity Card**: Subtle glass for timeline items
5. **Modal Card**: Strong glass with high opacity

## Responsive Design

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Mobile Optimizations
- Reduced blur intensity for performance
- Removed atmospheric vignettes
- Smaller navigation and FAB sizes
- Simplified shadow systems

## Implementation Guidelines

### Using Glass Effects
```css
/* Basic glass card */
.my-component {
  @extend .sting-glass-card;
  @extend .sting-glass-default;
  @extend .sting-elevation-medium;
  @extend .sting-glass-hoverable;
}
```

### Consistent Spacing
- Use rem units for scalability
- Standard padding: 1rem, 1.5rem, 2rem
- Card padding: 1.5rem
- Section spacing: 2rem

### Dark Theme Compliance
- Always use theme color variables
- Ensure sufficient contrast (WCAG AA)
- Test glass effects on various backgrounds
- Provide fallbacks for backdrop-filter

## Accessibility Considerations

1. **Color Contrast**: All text meets WCAG AA standards
2. **Focus States**: Yellow outline with proper visibility
3. **Motion**: Respects prefers-reduced-motion
4. **Glass Readability**: Sufficient opacity for text clarity

## Performance Optimization

1. **Backdrop Filter**: Use sparingly on mobile
2. **Shadow Layers**: Reduce on low-end devices
3. **Animations**: GPU-accelerated transforms only
4. **Glass Stacking**: Limit nested glass effects

## Future Enhancements

### Planned for Teaser Site
1. **Hero Section**: Ultra glass with animated particles
2. **Feature Cards**: Hexagonal design (honeycomb pattern)
3. **Pricing Tiers**: Glass cards with elevation hierarchy
4. **Contact Form**: Floating glass modal
5. **Navigation**: Sticky glass header with blur

### Design Tokens
Consider implementing CSS custom properties for:
- All color values
- Blur intensities
- Shadow definitions
- Animation timings
- Border radii

## Conclusion

The STING design system creates a cohesive, modern interface that reinforces the brand identity through consistent use of glass morphism, the signature yellow accent, and bee-inspired metaphors. The dark theme provides excellent contrast while the floating design language creates depth and hierarchy throughout the application.