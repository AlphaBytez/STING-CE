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
- Primary background: #161922 - Dark greenish-gray for sophisticated depth
- Card backgrounds: #1a1f2e - Slightly lighter with transparency
- Header areas: #475569 - Medium grey (slate-600) for subtle separation
- Glass sidebar: Dark transparent glass with 40% opacity over background
- Excellent readability with enhanced glass effects

### 3. **Floating Design Language**
- Cards appear to float above the background
- Multiple elevation levels with sophisticated shadow systems
- Hover effects that lift elements with transform and scale
- Atmospheric vignette effects for depth perception

## Color Palette

### Primary Brand Colors
```css
/* STING Yellow - Primary Brand Color */
--color-primary: #eab308;         /* Primary yellow (amber-500) */
--color-primary-hover: #d97706;   /* Darker yellow for hover (amber-600) */
--color-primary-active: #b45309;  /* Even darker for active (amber-700) */
--color-primary-light: #fbbf24;   /* Light yellow variant (amber-400) */
--color-primary-pale: #fcd34d;    /* Very light yellow (amber-300) */
--color-primary-ghost: #fde68a;   /* Pale yellow for accents (amber-200) */
```

### Background Colors
```css
/* Dark Backgrounds */
--color-bg-layout: #161922;       /* Main background - dark greenish-gray */
--color-bg-container: #1a1f2e;    /* Cards & panels - slightly lighter */
--color-bg-elevated: #2a3142;     /* Modals & dropdowns - elevated surfaces */
--color-bg-header: #475569;       /* Headers - medium grey (slate-600) */
--color-bg-input: #2d3748;        /* Form inputs (gray-800) */
--color-bg-header: #282c34;       /* App header */

/* Light Backgrounds */
--color-bg-spotlight: #e2e8f0;    /* Sidebar (slate-200) */
--color-bg-light-hover: #f8fafc;  /* Light hover state (slate-50) */
```

### Text Colors
```css
--color-text: #f1f5f9;            /* Primary text (slate-100) */
--color-text-secondary: #cbd5e1;   /* Muted text (slate-300) */
--color-text-tertiary: #94a3b8;   /* Labels & captions (slate-400) */
--color-text-quaternary: #64748b; /* Disabled text (slate-500) */
--color-text-prose: #e5e7eb;      /* Long-form text (gray-200) */
--color-text-inverse: #000000;    /* Black text on yellow */
```

### Border Colors
```css
--color-border: #475569;          /* Standard borders (slate-600) */
--color-border-subtle: #374151;   /* Subtle borders (gray-700) */
--color-border-glass: rgba(100, 116, 139, 0.3);  /* Glass card borders */
--color-border-dark: rgba(75, 85, 99, 0.5);      /* Dark table borders */
```

### Semantic Colors
```css
/* Success - Warm Jade (harmonizes with yellow, less bright) */
--color-success: #5d9b63;         /* Warm jade - balanced warm green */
--color-success-hover: #4a7a4f;   /* Darker warm jade for hover */
--color-success-light: #7ab57f;   /* Lighter warm jade */
--color-success-dark: #3d6640;    /* Dark warm jade */
--color-success-bg: rgba(93, 155, 99, 0.1);  /* Transparent success bg */

/* Error - Warm Red */
--color-error: #ef4444;           /* Red-500 */
--color-error-hover: #dc2626;     /* Red-600 */
--color-error-light: #f87171;     /* Red-400 */
--color-error-dark: #b91c1c;      /* Red-700 */
--color-error-bg: rgba(239, 68, 68, 0.1);     /* Transparent error bg */

/* Warning - Amber (matches primary) */
--color-warning: #f59e0b;         /* Amber-500 */
--color-warning-hover: #d97706;   /* Amber-600 */
--color-warning-light: #fbbf24;   /* Amber-400 */
--color-warning-dark: #b45309;    /* Amber-700 */
--color-warning-bg: rgba(245, 158, 11, 0.1);  /* Transparent warning bg */

/* Info - Cool Cyan */
--color-info: #06b6d4;            /* Cyan-500 */
--color-info-hover: #0891b2;      /* Cyan-600 */
--color-info-light: #22d3ee;      /* Cyan-400 */
--color-info-dark: #0e7490;       /* Cyan-700 */
--color-info-bg: rgba(6, 182, 212, 0.1);      /* Transparent info bg */
```

### Glass Effect Colors
```css
/* Glass Background Colors with Opacity */
--color-glass-subtle: rgba(45, 55, 72, 0.25);
--color-glass-medium: rgba(45, 55, 72, 0.35);
--color-glass-strong: rgba(45, 55, 72, 0.45);
--color-glass-ultra: rgba(55, 65, 81, 0.5);
--color-glass-heavy: rgba(51, 65, 85, 0.65);

/* Light Glass Variants */
--color-glass-light-subtle: rgba(226, 232, 240, 0.25);
--color-glass-light-medium: rgba(226, 232, 240, 0.35);
```

### Special Purpose Colors
```css
/* Authentication & Forms */
--color-auth-bg: #3498db;         /* Blue primary (Ory theme) */
--color-auth-hover: #2980b9;      /* Blue hover (Ory theme) */
--color-link: #ecc94b;            /* Yellow links (Ory theme) */

/* Shadow Tints */
--color-shadow-yellow: rgba(234, 179, 8, 0.2);   /* Yellow glow */
--color-shadow-dark: rgba(0, 0, 0, 0.4);         /* Deep shadows */
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

#### Floating Navigation Sidebar
- Dark glass effect with 40% opacity (rgba(30, 41, 59, 0.4))
- 16px blur with 180% saturation and 110% brightness
- Subtle white border (10% opacity)
- Deep shadow with optional yellow glow
- Hover states with yellow-tinted glass (15% opacity)

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
- Fixed position with `translateY(-50%)` for vertical centering
- Dark glass background with 40% opacity for transparency
- Enhanced glassmorphism with backdrop-filter effects
- Active state: Yellow background with black text
- Hover state: Yellow-tinted glass (15% opacity)
- Deep shadows with optional yellow glow effect
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

/* Floating navigation glass sidebar */
.floating-nav {
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(16px) saturate(180%) brightness(110%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 0 80px rgba(234, 179, 8, 0.05); /* Optional yellow glow */
}
```

### Color Usage Rules

#### 1. **Primary Actions**
- Use STING yellow (`--color-primary`) for primary buttons and CTAs
- Ensure black text (`--color-text-inverse`) on yellow backgrounds
- Apply hover state with darker yellow (`--color-primary-hover`)

#### 2. **Success States**
- Use warm jade green (`--color-success`) instead of generic emerald
- Apply transparent backgrounds (`--color-success-bg`) for success messages
- Ensure sufficient contrast on dark backgrounds

#### 3. **Glass Components**
- Layer glass effects with appropriate opacity levels
- Use `--color-glass-subtle` for minimal depth
- Use `--color-glass-heavy` for prominent cards
- Always include border colors for definition

#### 4. **Text Hierarchy**
- Primary content: `--color-text`
- Secondary information: `--color-text-secondary`
- Labels and metadata: `--color-text-tertiary`
- Disabled states: `--color-text-quaternary`

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

### Component-Specific Rules

#### Buttons
```css
/* Primary Button */
background: var(--color-primary);
color: var(--color-text-inverse);
hover: var(--color-primary-hover);

/* Secondary Button */
background: var(--color-bg-elevated);
color: var(--color-text);
border: 1px solid var(--color-border);

/* Success Button */
background: var(--color-success);
color: var(--color-text-inverse);
hover: var(--color-success-hover);
```

#### Forms
```css
/* Input Fields */
background: var(--color-bg-input);
border: 1px solid var(--color-border);
color: var(--color-text);

/* Focus State */
border-color: var(--color-primary);
box-shadow: 0 0 0 3px var(--color-shadow-yellow);
```

#### Cards
```css
/* Standard Card */
background: var(--color-glass-medium);
border: 1px solid var(--color-border-glass);
backdrop-filter: blur(24px) saturate(150%);

/* Elevated Card */
background: var(--color-glass-strong);
box-shadow: var(--elevation-level-3);
```

## UI Patterns & Rules

### Layout Structure
1. **Navigation**: Fixed left sidebar (200px) with vertical icon+label layout
2. **Content Area**: Flexible main content with max-width constraints
3. **Floating Elements**: FABs positioned bottom-right with proper z-index
4. **Modals**: Centered with glass overlay backdrop

### Interactive States
```css
/* Default State */
opacity: 1;
transform: translateY(0);

/* Hover State */
transform: translateY(-4px) scale(1.01);
box-shadow: enhanced;
border-color: var(--color-primary);

/* Active State */
transform: translateY(-2px) scale(0.98);
background: darker variant;

/* Disabled State */
opacity: 0.5;
cursor: not-allowed;
pointer-events: none;
```

### Component Sizing
- **Buttons**: Height 40px (standard), 48px (large), 32px (small)
- **Inputs**: Height 40px with 12px horizontal padding
- **Cards**: Min-height based on content, standard padding 24px
- **Icons**: 20px (standard), 24px (large), 16px (small)

### Z-Index Hierarchy
```css
--z-index-base: 0;
--z-index-dropdown: 10;
--z-index-sticky: 20;
--z-index-fixed: 30;
--z-index-modal-backdrop: 40;
--z-index-modal: 50;
--z-index-popover: 60;
--z-index-tooltip: 70;
```

### Responsive Behavior
- **Mobile (<768px)**: Stack layouts, full-width components, simplified glass
- **Tablet (768-1024px)**: Flexible grid, reduced spacing
- **Desktop (>1024px)**: Full experience with all effects

### Animation Timing
```css
/* Micro-interactions (hover, focus) */
transition: all 0.2s ease-out;

/* Page transitions */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Complex animations */
animation-duration: 0.6s;
animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
```

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

## Color Palette Updates & Recommendations

### Key Changes from Latest Updates
1. **Enhanced Glassmorphism**: Floating navigation now features dark transparent glass (40% opacity) with sophisticated backdrop filters
2. **Background Color Refinement**: Main background updated to #161922 (dark greenish-gray) for better depth
3. **Warm Jade Success Color**: Replaced generic emerald (#10b981) with warm jade (#5d9b63) for better harmony
4. **Header Differentiation**: Medium grey headers (#475569) provide subtle separation from dark backgrounds

### Recommendations for Implementation
1. **Update All Success States**: Replace all instances of `#10b981`, `#059669`, and `#48bb78` with the new warm jade palette
2. **Standardize Color Usage**: Use CSS variables instead of hard-coded Tailwind classes where possible
3. **Test Contrast**: Verify all new color combinations meet WCAG AA standards, especially the warm jade on dark backgrounds
4. **Create Utility Classes**: Define `.bg-success`, `.text-success`, etc. using the new color variables

### Color Harmony Principles
- **Warm Palette**: Stay within warm color temperatures (yellows, warm greens, warm reds)
- **Consistent Saturation**: Match the vibrancy of the STING yellow across semantic colors
- **Glass Compatibility**: Ensure all colors work well through glass effects with various backdrop filters

## Recent Design Evolution

### Glass Sidebar Implementation
The floating navigation sidebar now features an enhanced glassmorphism effect that creates visual depth while maintaining functionality:
- **Transparency**: 40% opacity allows background visibility
- **Blur Effect**: 16px blur creates frosted glass appearance
- **Saturation Boost**: 180% saturation enhances colors through the glass
- **Subtle Glow**: Optional yellow accent glow for brand reinforcement

### Color Refinements
- **Background**: Shifted from pure black to #161922 for warmer tone
- **Success States**: Warm jade (#5d9b63) replaced bright lime for sophistication
- **Headers**: Medium grey (#475569) provides hierarchy without harsh contrast

## Conclusion

The STING design system creates a cohesive, modern interface that reinforces the brand identity through sophisticated glass morphism effects, the signature yellow accent, and bee-inspired metaphors. The latest updates enhance the dark theme with transparent glass elements and a refined color palette that balances warmth, sophistication, and excellent readability.