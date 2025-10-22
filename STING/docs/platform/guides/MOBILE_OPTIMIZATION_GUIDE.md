# STING Mobile Optimization Guide

## Overview
This guide provides best practices and implementation patterns for ensuring STING works seamlessly across all device sizes, with a focus on mobile optimization.

## Mobile-First Principles

### 1. **Viewport Considerations**
- Design for minimum viewport of 320px (iPhone SE)
- Test at common breakpoints: 320px, 375px, 414px, 768px, 1024px
- Use responsive units (rem, %, vw/vh) instead of fixed pixels

### 2. **Touch Targets**
- Minimum touch target size: 44x44px (iOS) / 48x48px (Android)
- Add appropriate spacing between interactive elements
- Use `touch-action: manipulation` to prevent double-tap delays

### 3. **Performance**
- Lazy load heavy components
- Minimize bundle size for mobile networks
- Use CSS transforms for animations (GPU accelerated)

## Component Guidelines

### Modals
Use the `ResponsiveModal` component instead of fixed-width modals:

```jsx
import ResponsiveModal from '@/components/common/ResponsiveModal';

// Bad: Fixed width
<div className="max-w-4xl">

// Good: Responsive sizing
<ResponsiveModal size="lg" isOpen={open} onClose={handleClose}>
  {content}
</ResponsiveModal>
```

### Tables
Use `ResponsiveTable` for horizontal scrolling or `ResponsiveTableContainer` for card-based mobile view:

```jsx
import ResponsiveTable, { ResponsiveTableContainer } from '@/components/common/ResponsiveTable';

// Horizontal scroll approach
<ResponsiveTable>
  <table>{/* table content */}</table>
</ResponsiveTable>

// Card-based approach (recommended for complex data)
<ResponsiveTableContainer
  headers={['Name', 'Status', 'Actions']}
  data={items}
  renderCell={(item, header) => item[header.toLowerCase()]}
/>
```

### Grid Layouts
Always provide mobile breakpoints:

```jsx
// Bad: Desktop-only grid
<div className="grid grid-cols-4 gap-4">

// Good: Responsive grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
```

### Navigation
- Use collapsible sidebars on mobile
- Consider bottom navigation for primary actions
- Implement hamburger menu for secondary navigation

## CSS Utilities

Import mobile utilities in your components:

```css
@import '@/styles/mobile-utilities.css';
```

### Available Classes:
- `.touch-target` - Ensures minimum touch size
- `.mobile-hidden` - Hide on mobile only
- `.mobile-only` - Show on mobile only
- `.mobile-padding` - Responsive padding
- `.mobile-card` - Responsive card styling
- `.mobile-truncate` - Text truncation with ellipsis
- `.horizontal-scroll` - Touch-friendly horizontal scrolling

## Testing Checklist

### Before Release:
- [ ] Test on real devices (not just browser DevTools)
- [ ] Check all interactive elements are touch-friendly
- [ ] Verify modals don't overflow viewport
- [ ] Ensure forms are usable with virtual keyboards
- [ ] Test landscape orientation
- [ ] Check performance on 3G network
- [ ] Verify text is readable without zooming

### Common Issues to Check:
1. **Fixed positioning** - Can cause issues with virtual keyboards
2. **Hover states** - Don't rely on hover for functionality
3. **Small fonts** - Minimum 16px to prevent iOS zoom
4. **Horizontal overflow** - Always test with narrow viewports
5. **Z-index conflicts** - Mobile browsers handle differently

## Implementation Priority

### Phase 1 - Critical (Current Sprint)
1. Fix modal overflows on HoneyPotPage
2. Make tables horizontally scrollable
3. Fix Bee Chat grains visibility
4. Ensure authentication pages work on mobile

### Phase 2 - Important
1. Optimize complex grid layouts
2. Add touch gestures (swipe to close, pull to refresh)
3. Implement responsive images
4. Add loading skeletons for slow connections

### Phase 3 - Enhancement
1. PWA features (offline support, install prompt)
2. Native-like animations
3. Advanced touch interactions
4. Accessibility improvements

## Code Examples

### Responsive Flex Layout
```jsx
// Stacks on mobile, side-by-side on desktop
<div className="flex flex-col md:flex-row gap-4">
  <div className="flex-1">Content A</div>
  <div className="flex-1">Content B</div>
</div>
```

### Mobile-First Media Queries
```css
/* Mobile first approach */
.component {
  /* Mobile styles (default) */
  padding: 1rem;
}

@media (min-width: 768px) {
  .component {
    /* Tablet and up */
    padding: 2rem;
  }
}

@media (min-width: 1024px) {
  .component {
    /* Desktop and up */
    padding: 3rem;
  }
}
```

### Safe Area Insets (for notched devices)
```css
.bottom-bar {
  padding-bottom: env(safe-area-inset-bottom, 1rem);
}
```

## Resources

- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [Material Design - Mobile Guidelines](https://material.io/design/layout/understanding-layout.html)
- [iOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/ios)
- [Android Design Guidelines](https://developer.android.com/design)

## Testing Tools

1. **Browser DevTools** - Initial testing
2. **Responsively App** - Multi-viewport testing
3. **BrowserStack** - Real device testing
4. **Lighthouse** - Performance auditing
5. **axe DevTools** - Accessibility testing

## Contribution Guidelines

When submitting PRs:
1. Include mobile screenshots in PR description
2. List tested viewport sizes
3. Note any mobile-specific changes
4. Update this guide if adding new patterns