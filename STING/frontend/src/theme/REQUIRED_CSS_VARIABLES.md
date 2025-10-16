# Required CSS Variables for STING CE Themes

## Core Variables (Used by Components)

All themes MUST define these CSS variables for components to display correctly:

```css
/* Component CSS Variables (--color-* pattern) */
--color-primary: /* Your primary brand color */
--color-primary-hover: /* Primary hover state */
--color-text: /* Main text color */
--color-text-secondary: /* Secondary text color */
--color-text-inverse: /* Text on colored backgrounds */
--color-bg: /* Main background */
--color-bg-elevated: /* Elevated surfaces like cards */
--color-border: /* Border color */
--radius-lg: /* Border radius for components */

/* Additional Theme Variables */
--bg-primary: /* Main background */
--bg-secondary: /* Secondary background */
--bg-tertiary: /* Tertiary background */
--text-primary: /* Primary text */
--text-secondary: /* Secondary text */
--border-primary: /* Primary border */
--success-color: /* Success state */
--warning-color: /* Warning state */
--error-color: /* Error state */
--info-color: /* Info state */
```

## Mapping Guide

### For Dark Themes (Retro, Modern, Glass)
```css
--color-primary: #fbbf24; /* STING yellow */
--color-primary-hover: #f59e0b;
--color-text: #f1f5f9; /* Light text */
--color-text-secondary: #94a3b8;
--color-text-inverse: #0f172a; /* Dark text on yellow */
--color-bg: #0f172a; /* Dark background */
--color-bg-elevated: #1e293b; /* Slightly lighter */
--color-border: rgba(148, 163, 184, 0.2);
--radius-lg: 8px; /* or 0 for retro themes */
```

### For Terminal Themes (Retro, Retro-Performance)
```css
--color-primary: #fbbf24; /* STING yellow */
--color-primary-hover: #f59e0b;
--color-text: #ffffff; /* White or #00ff41 for green */
--color-text-secondary: #00cc33;
--color-text-inverse: #000000;
--color-bg: #000000; /* Pure black */
--color-bg-elevated: #1a1a1a;
--color-border: #006600; /* Terminal green */
--radius-lg: 0; /* Sharp edges */
```

## Implementation Checklist

- [ ] Add all --color-* variables to theme
- [ ] Map existing theme variables to component variables
- [ ] Test PreferenceSettings page
- [ ] Test all form inputs and selects
- [ ] Verify button hover states
- [ ] Check border and background colors