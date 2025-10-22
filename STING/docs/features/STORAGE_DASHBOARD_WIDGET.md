# Storage Dashboard Widget

## Overview

The Storage Dashboard Widget provides real-time visualization of Honey Reserve storage usage across the STING platform. It displays comprehensive storage statistics, breakdown by category, growth trends, and cleanup opportunities directly in the main dashboard.

## Features

### ✅ Implemented
- **Real-time Storage Metrics**: Live data from `/api/storage/usage` endpoint
- **Visual Progress Bars**: Color-coded usage indicators
- **Storage Breakdown**: Documents, honey jars, embeddings, temp files
- **Top Storage Consumers**: Largest honey jars by size
- **Growth Projections**: Monthly growth rate and capacity planning
- **Cleanup Opportunities**: Identify reclaimable storage space
- **Responsive Design**: Works on desktop and mobile
- **Fallback Data**: Graceful handling when API unavailable

### 📊 Metrics Displayed

#### Primary Storage Usage
- **Total Usage**: Current storage consumption vs. quota
- **Usage Percentage**: Visual progress bar with color coding
- **Available Space**: Remaining storage capacity
- **Growth Rate**: Monthly storage consumption trend

#### Storage Breakdown
- **Documents**: User-uploaded files and content
- **Honey Jars**: Knowledge base containers and metadata
- **Embeddings**: AI/ML vector data for search
- **Temp Files**: Temporary uploads (auto-cleaned after 48hrs)
- **System**: Platform overhead and caches

#### Top Consumers
- **Honey Jar Rankings**: Largest storage consumers
- **Document Counts**: Files per honey jar
- **Last Accessed**: Usage recency indicators
- **Size Distribution**: Percentage of total storage

### 🎨 Visual Design

The widget follows STING's signature dark theme:
- **Background**: Slate with glass morphism effect
- **Accent Color**: Blue for storage-related elements  
- **Progress Bars**: Color-coded (Green → Yellow → Orange → Red)
- **Icons**: Lucide icons for visual clarity
- **Grid Layout**: Organized information display

#### Color Coding
- 🟢 **Green (0-50%)**: Healthy storage usage
- 🟡 **Yellow (50-75%)**: Moderate usage, monitoring recommended  
- 🟠 **Orange (75-90%)**: High usage, consider cleanup
- 🔴 **Red (90-100%)**: Critical usage, immediate action needed

### 🔧 Technical Implementation

#### Frontend Component
```javascript
// Location: /frontend/src/components/dashboard/StorageWidget.jsx
import StorageWidget from './dashboard/StorageWidget';

// Usage in dashboard
<StorageWidget className="mb-6" />
```

#### Backend API
```python
# Location: /app/routes/storage_routes.py
GET /api/storage/usage

# Response format
{
    "totalQuota": 5368709120,
    "totalUsed": 1288490188,
    "breakdown": {
        "documents": 524288000,
        "honeyJars": 314572800,
        "embeddings": 209715200,
        "tempFiles": 104857600,
        "system": 134217728
    },
    "byHoneyJar": [...],
    "trends": {
        "growthRate": 12.5,
        "projectedFull": "8 months",
        "cleanupOpportunities": 157286400
    }
}
```

### 📈 Data Sources

#### Real-time Calculations
- **Database Queries**: Document sizes, honey jar counts
- **File System**: Actual disk usage via `shutil.disk_usage()`
- **Honey Reserve**: Encrypted storage statistics
- **Growth Analysis**: Historical usage patterns

#### Fallback Data
When API unavailable, displays cached/mock data:
- Prevents widget from failing completely
- Shows "Cache Mode" indicator
- Maintains user experience during outages

### 🚨 Alert System

#### Storage Warnings
- **80%+ Usage**: Yellow warning with recommendation
- **90%+ Usage**: Red critical alert with immediate action required
- **Cleanup Available**: Green notification showing reclaimable space

#### Alert Content
```javascript
// High usage warning
{
  type: 'warning',
  message: 'Storage usage is high. Consider cleanup or quota increase.',
  icon: 'AlertTriangle',
  threshold: 80
}
```

### 🧹 Cleanup Integration

#### Cleanup Opportunities
- **Temp Files**: Files older than 48 hours
- **Deleted Documents**: Soft-deleted content ready for purging
- **Orphaned Files**: Files without database references
- **Cache Data**: Expired embeddings and processed data

#### Quick Actions
- **View Details**: Navigate to full storage management page
- **Cleanup Files**: Trigger automated cleanup processes
- **Usage History**: View historical storage trends

### 🔧 Configuration

#### Environment Variables
```env
# Storage paths and limits
STORAGE_PATH=/opt/sting-ce/storage
DEFAULT_USER_QUOTA=1073741824  # 1GB per user
MAX_FILE_SIZE=104857600        # 100MB max upload

# Cleanup settings
TEMP_FILE_RETENTION_HOURS=48
DELETED_FILE_RETENTION_DAYS=7
```

#### Admin Configuration
- **User Quotas**: Adjustable per user or global defaults
- **Cleanup Schedules**: Automated maintenance windows
- **Alert Thresholds**: Customizable warning levels
- **Retention Policies**: File lifecycle management

### 📱 Responsive Behavior

#### Desktop (> 1024px)
- Full grid layout with all metrics
- Detailed breakdown tables
- Complete honey jar listings
- All action buttons visible

#### Tablet (768px - 1024px)
- Condensed grid layout
- Essential metrics prioritized
- Scrollable sections for details
- Touch-optimized buttons

#### Mobile (< 768px)
- Single column layout
- Priority metrics only
- Collapsible sections
- Thumb-friendly interactions

### 🔍 Monitoring & Analytics

#### Usage Tracking
- **Widget Load Times**: Performance monitoring
- **API Response Times**: Backend performance  
- **Error Rates**: Failed data loads
- **User Interactions**: Button clicks and navigation

#### Business Intelligence
- **Storage Growth Trends**: Capacity planning
- **User Behavior**: Most accessed honey jars
- **Cleanup Effectiveness**: Reclaimed space tracking
- **Cost Optimization**: Storage efficiency metrics

### 🚀 Future Enhancements

#### Planned Features
- **Storage Forecasting**: AI-powered usage predictions
- **Cost Analysis**: Storage expense tracking
- **Data Lifecycle**: Automated archival policies
- **Multi-tenant**: Per-team storage quotas
- **Real-time Updates**: WebSocket live data

#### Advanced Visualizations
- **Historical Charts**: Storage usage over time
- **Heat Maps**: Usage patterns by time/user
- **Comparison Views**: Team vs. individual usage
- **Export Reports**: PDF/CSV storage analytics

### 📝 Integration Points

#### Dashboard Integration
```javascript
// Added to ModernDashboard.jsx
<div className="space-y-6">
  <ExperienceMetric ... />
  <StorageWidget />  // ← New storage widget
  <ActivityTimeline ... />
</div>
```

#### Admin Panel Integration
- Links to detailed storage management
- Bulk cleanup operations
- User quota management
- System storage alerts

### 🛠️ Development

#### Local Testing
```bash
# View storage API directly
curl -k -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
     https://localhost:5050/api/storage/usage

# Test widget rendering
npm run dev  # Start frontend development server
```

#### Debug Mode
- Enable detailed console logging
- Show API response times
- Display fallback data sources
- Highlight performance bottlenecks

### 📊 Performance Considerations

#### Optimization Strategies
- **Caching**: Store storage calculations for 5-minute intervals
- **Lazy Loading**: Load detailed data on demand
- **Debouncing**: Limit API calls during rapid navigation
- **Compression**: Minimize API response sizes

#### Loading States
- **Skeleton UI**: Placeholder content while loading
- **Progressive Loading**: Show cached data first, then live data
- **Error Boundaries**: Graceful failure handling
- **Retry Logic**: Automatic API call retries