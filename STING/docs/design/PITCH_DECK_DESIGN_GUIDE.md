# STING Pitch Deck Design Guide
## Visual Theme Based on Current UI

## 🎨 Core Design Language

### Color Palette
Based on your UI's sophisticated dark theme with yellow accents:

```css
/* Primary Colors */
--sting-dark-bg: #0a0e1b        /* Deep navy background */
--sting-darker: #161922          /* Card backgrounds */
--sting-panel: #1a1f2e          /* Panel backgrounds */

/* Accent Colors */
--sting-yellow: #fbbf24          /* Primary yellow (bee theme) */
--sting-amber: #f59e0b           /* Darker amber for hover */
--sting-honey: #fcd34d           /* Light honey color */

/* Status Colors */
--sting-success: #10b981         /* Emerald green */
--sting-warning: #f59e0b         /* Amber */
--sting-error: #ef4444           /* Red */
--sting-info: #3b82f6            /* Blue */

/* Text Colors */
--text-primary: #f3f4f6          /* Almost white */
--text-secondary: #9ca3af        /* Muted gray */
--text-accent: #fbbf24           /* Yellow for emphasis */
```

### Typography Hierarchy
Matching your UI's clean, modern typography:

```
Headings:
- H1: 48-56pt, Bold, White (#f3f4f6)
- H2: 36-40pt, Semibold, White
- H3: 28-32pt, Medium, Light gray (#e5e7eb)

Body:
- Large: 18-20pt, Regular, Light gray
- Normal: 16pt, Regular, Gray (#9ca3af)
- Small: 14pt, Regular, Muted gray

Font Family:
- Primary: Inter, -apple-system, system-ui
- Monospace: 'Fira Code', 'Courier New' (for technical content)
```

## 🏗️ Slide Layout Principles

### Glass Morphism Effect
Your UI uses subtle glass morphism - apply to pitch deck:

```css
/* Glass Card Effect */
.slide-card {
  background: rgba(26, 31, 46, 0.8);  /* Semi-transparent */
  backdrop-filter: blur(10px);
  border: 1px solid rgba(251, 191, 36, 0.1);  /* Subtle yellow border */
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

### Grid System
Based on your dashboard's clean grid:
- **12-column grid** with generous gutters
- **Card-based layouts** with consistent spacing
- **16px base spacing unit** (multiples: 8, 16, 24, 32, 48)

## 🐝 Visual Elements

### Bee-Themed Iconography
Consistent with your hexagon/honeycomb patterns:

```
Icons to Use:
- 🟡 Yellow hexagons for bullet points
- 🔶 Honeycomb patterns for backgrounds
- 🐝 Bee icon for feature highlights
- ⬡ Hexagon shapes for diagrams
- 📊 Chart icons with yellow accents
```

### Background Patterns
Subtle patterns from your UI:
1. **Hexagonal mesh** - Very faint (5% opacity)
2. **Gradient overlays** - Dark blue to black
3. **Glow effects** - Yellow glow for emphasis
4. **Particle effects** - Floating dots (like pollen)

## 📊 Chart & Graph Styling

### Data Visualization Colors
```javascript
const chartColors = {
  primary: '#fbbf24',    // Yellow
  secondary: '#f59e0b',  // Amber
  tertiary: '#10b981',   // Green
  quaternary: '#3b82f6', // Blue
  negative: '#ef4444',   // Red
  neutral: '#6b7280'     // Gray
}
```

### Chart Styling Rules
- **Dark backgrounds** for all charts
- **Yellow as primary data color**
- **Thin lines** (2px max)
- **Subtle grid lines** (10% opacity)
- **Rounded corners** on bars
- **Glow effects** on hover

## 🎯 Slide Templates

### Title Slide Template
```
┌─────────────────────────────────────┐
│  ░░░░░░░ (Hexagon pattern 5% opacity)│
│                                      │
│     [STING LOGO - Yellow]            │
│                                      │
│     MAIN TITLE (56pt, White)         │
│     Subtitle (24pt, Gray)            │
│                                      │
│     ━━━━━━━━━━━━━━━━━━              │
│     Tagline (18pt, Yellow)           │
│                                      │
│  ░░░░░░░ (Bottom gradient fade)      │
└─────────────────────────────────────┘
```

### Content Slide Template
```
┌─────────────────────────────────────┐
│  Section Title (40pt, Yellow)        │
│  ─────────────────                  │
│                                      │
│  ┌─────────────────────────────┐   │
│  │  Glass Card Background       │   │
│  │                              │   │
│  │  • Point 1 (hexagon bullet)  │   │
│  │  • Point 2                   │   │
│  │  • Point 3                   │   │
│  └─────────────────────────────┘   │
│                                      │
│  [Visual/Chart Area]                 │
│                                      │
└─────────────────────────────────────┘
```

### Comparison Slide Template
```
┌─────────────────────────────────────┐
│  "Traditional vs STING" (40pt)       │
│                                      │
│  ┌──────────┐     ┌──────────┐     │
│  │   OLD    │ VS  │  STING   │     │
│  │  (Red)   │     │ (Yellow) │     │
│  │          │     │          │     │
│  │    ❌    │     │    ✅    │     │
│  └──────────┘     └──────────┘     │
└─────────────────────────────────────┘
```

## ✨ Animation Guidelines

### Transition Effects
Matching your UI's smooth animations:
- **Fade in/up**: 0.3s ease-out
- **Slide from right**: For new sections
- **Scale up**: For emphasis (1.0 to 1.05)
- **Glow pulse**: For CTAs (yellow glow)

### Motion Principles
1. **Subtle is better** - No dramatic effects
2. **Consistent timing** - 0.3s for most transitions
3. **Purpose-driven** - Animate to guide attention
4. **Progressive disclosure** - Build complex ideas step by step

## 🎪 Specific Slide Styling

### For Market Opportunity Slides
- Use **red accents** for problems/costs
- Use **yellow highlights** for opportunities
- Dark cards with subtle borders
- Animated number counters

### For Architecture Slides
- **Monospace font** for technical diagrams
- **Dotted lines** for data flow
- **Yellow highlights** for STING components
- **Red X** for competitor limitations
- **Green checkmarks** for STING advantages

### For ROI Slides
- **Green upward arrows** for savings
- **Calculator-style numbers** (monospace)
- **Progress bars** in yellow
- **Comparison tables** with alternating row colors

## 💡 Design Do's and Don'ts

### Do's ✅
- Use plenty of **dark space** (not white space)
- Keep **yellow as hero color**
- Use **glass effects** for depth
- Add **subtle animations**
- Include **hexagonal elements**
- Use **high contrast** for readability

### Don'ts ❌
- Don't use pure black (#000)
- Don't use more than 3 colors per slide
- Don't overuse animations
- Don't use thin fonts (min: Regular weight)
- Don't forget breathing room

## 🖼️ Image Treatment

### Photo Styling
- **Darken images** by 30-40%
- Add **yellow color overlay** at 10% opacity
- Use **rounded corners** (12px)
- Apply **subtle shadow**

### Illustration Style
- **Flat design** with depth
- **Limited color palette**
- **Geometric shapes** (hexagons, circles)
- **Yellow accents** throughout

## 📱 Export Settings

### For Screen Presentation
- **16:9 aspect ratio**
- **1920x1080 minimum**
- **RGB color mode**
- **PNG for graphics**

### For Print (if needed)
- **CMYK conversion**
- **300 DPI**
- **PDF/X-1a format**
- **Embedded fonts**

## 🎯 Quick Style Reference

```css
/* Quick Copy-Paste Styles */
.slide-background {
  background: linear-gradient(135deg, #0a0e1b 0%, #161922 100%);
}

.hero-text {
  color: #f3f4f6;
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.accent-text {
  color: #fbbf24;
  text-shadow: 0 0 20px rgba(251, 191, 36, 0.5);
}

.glass-panel {
  background: rgba(26, 31, 46, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(251, 191, 36, 0.15);
  border-radius: 12px;
}

.cta-button {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #0a0e1b;
  font-weight: 600;
  padding: 16px 32px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(251, 191, 36, 0.3);
}
```

## 🚀 AI Platform Prompts

When using AI platforms to create slides, use these prompts:

### For Gamma.app or Tome:
"Create a pitch deck with a dark navy background (#0a0e1b), yellow accent color (#fbbf24), glass morphism effects, hexagonal patterns at 5% opacity, modern sans-serif fonts, high contrast text, subtle animations, and a sophisticated tech aesthetic similar to a modern dashboard UI."

### For Canva or Pitch:
"Tech/SaaS template, dark mode, yellow accent color, minimal design, glass effect cards, hexagon patterns, professional enterprise style"

---

*This design guide ensures your pitch deck maintains the sophisticated, modern aesthetic of your STING UI while being memorable and professional.*