# STING V2 Glass Theme Design System

## Overview
The STING V2 theme uses a consistent glass morphism design inspired by stacked glass, transparency, and shadows. All cards throughout the application now use the same base color scheme with varying levels of transparency and blur.

## Color Palette
- **Base Color**: `slate-700` (rgb(51, 65, 85))
- **Border Color**: `slate-500` with transparency
- **Text Color**: `slate-100` (#f1f5f9)
- **Accent Color**: STING Yellow (#eab308)

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
<GlassCard>
```

```jsx
// Before
<Card className="grains-glass">

// After
<GlassCard variant="ultra">
```

## Design Principles

1. **Consistency**: All cards use the same base slate-700 color
2. **Hierarchy**: Use variants and elevation to create visual hierarchy
3. **Readability**: Text is always light (#f1f5f9) on dark glass
4. **Interactivity**: Hover effects increase opacity and add yellow border
5. **Performance**: Backdrop filters are optimized for smooth rendering

## Best Practices

1. **Statistics/Metrics**: Use `elevation="high"` for importance
2. **Content Cards**: Use default variant with `elevation="medium"`
3. **Nested Cards**: Use `variant="subtle"` to avoid too much opacity
4. **CTAs**: Use `variant="strong"` for cards with important actions
5. **Mobile**: Glass effects automatically reduce on smaller screens

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

## Troubleshooting

### Cards appear too dark/light
- Check that you're using the correct variant
- Ensure no inline styles are overriding the glass effect
- Verify the parent container has appropriate background

### Hover effects not working
- Add `hoverable={true}` prop (default)
- Check for CSS conflicts

### Performance issues
- Glass effects are automatically reduced on mobile
- Consider using `variant="subtle"` for better performance
- Limit the number of `elevation="floating"` cards