# HoneyPotPage Modal Fix Example

## Current Issue
The modal uses `max-w-4xl` which is too wide for mobile devices, causing horizontal overflow.

## Fix Implementation

### Option 1: Quick Fix (Minimal Changes)
Replace the fixed width with responsive classes:

```jsx
// Before (line 798):
<div className="standard-card-solid rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">

// After:
<div className="standard-card-solid rounded-t-2xl sm:rounded-2xl shadow-2xl w-full sm:max-w-md md:max-w-2xl lg:max-w-4xl max-h-[90vh] overflow-hidden">
```

### Option 2: Use ResponsiveModal Component (Recommended)

```jsx
// Import at top of file
import ResponsiveModal from '@/components/common/ResponsiveModal';

// Replace entire modal section (lines 796-900+):
<ResponsiveModal
  isOpen={showDetails && selectedHoneyJar}
  onClose={() => setShowDetails(false)}
  size="lg"
  title={
    <div className="flex items-center gap-3">
      <Database className="w-6 h-6 text-yellow-400" />
      <span>{selectedHoneyJar.name}</span>
    </div>
  }
>
  {/* Modal content - same as before but without the wrapper divs */}
  <div className="space-y-6">
    {/* Stats Grid - make it responsive */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* stat cards */}
    </div>
    
    {/* Other content sections */}
  </div>
</ResponsiveModal>
```

### Additional Mobile Optimizations for This Page

1. **Filter Grid** (around line 200):
```jsx
// Before:
<div className="grid grid-cols-4 gap-4">

// After:
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-4">
```

2. **Card Grid** (main content):
```jsx
// Before:
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">

// After:
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
```

3. **Action Buttons in Cards**:
Make them stack on mobile:
```jsx
// Before:
<div className="flex justify-between items-center mt-4">

// After:
<div className="flex flex-col sm:flex-row gap-2 sm:justify-between items-stretch sm:items-center mt-4">
```

## Testing Notes
- Test at 320px width (iPhone SE)
- Ensure modal is scrollable on mobile
- Check that close button is easily tappable
- Verify grid layouts stack properly