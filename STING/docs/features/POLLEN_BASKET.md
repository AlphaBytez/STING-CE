# 🧺 Pollen Basket - Personalized Quick Actions

**"Collect, organize, and pollinate your workflow"**

The Pollen Basket is STING's floating action suite that provides users with a customizable collection of quick actions, seamlessly integrated into the Bee Chat experience. Like a bee's pollen basket, users gather the tools they need most and organize them for efficient access.

## 🌻 Core Concept

The Pollen Basket transforms the traditional floating action button paradigm into a nature-inspired, bee-themed experience:

- **Pollen Grains**: Individual quick actions that users can collect and arrange
- **Nectar Flow**: Real-time monitoring of hive activity and processing queues
- **Cross-Pollination**: Actions that bridge different STING features seamlessly
- **Seasonal Updates**: New pollen types (actions) released regularly

## 🐝 Available Pollen Grains

### Document & Knowledge Actions
- **🌺 Gather Nectar** - Upload files for analysis and knowledge extraction
- **🏗️ Build Comb** - Create new honeycomb knowledge structures (Honey Pots)
- **🔍 Forage Knowledge** - Search across the hive for stored information

### Monitoring & Administration
- **⏰ Hive Status** - Monitor nectar flow and processing queues
- **👑 Queen's Chamber** - Access Bee settings (role-based permissions)
- **🍯 Harvest Honey** - Export conversations and knowledge

## 🛠️ Technical Implementation

### Component Architecture
```javascript
// Core structure
const PollenBasket = ({ 
  onFileUpload, 
  onCreateHoneyJar, 
  onSearchKnowledge, 
  onExportChat 
}) => {
  // Customizable pollen grain configuration
  const pollenGrains = [
    {
      id: 'nectar-upload',
      pollenType: 'document',
      label: 'Gather Nectar',
      action: () => fileInputRef.current?.click(),
      // ... configuration
    }
  ];
}
```

### Pollen Grain Properties
Each pollen grain includes:
- **ID**: Unique identifier for customization
- **Pollen Type**: Category for filtering and organization
- **Label**: User-friendly name with bee terminology
- **Icon**: Visual representation
- **Color**: Theme-consistent styling
- **Action**: Callback function
- **Tooltip**: Contextual help text
- **Badge**: Dynamic status indicators

## 🎨 Design Philosophy

### Visual Language
- **Amber/Honey Colors**: Primary action colors using amber-500/600
- **Basket Icon**: 🧺 represents the collection metaphor
- **Glass Morphism**: Consistent with STING's floating design system
- **Smooth Animations**: Staggered reveals with 0.1s delays

### Interaction Patterns
- **Expandable Collection**: Basket opens to reveal organized pollen grains
- **Contextual Feedback**: Actions provide immediate visual and textual feedback
- **Progressive Disclosure**: Advanced features revealed based on user role
- **Persistent State**: User preferences stored for future sessions

## 🔐 Role-Based Access

### Permission Levels
```javascript
// Super Admin (👑)
- Full Queen's Chamber access
- All pollen grains available
- Customization privileges

// Admin (🔍)  
- Read-only Queen's Chamber
- Core pollen grains
- Limited customization

// User
- Essential pollen grains
- No admin features
- Basic customization
```

## 📊 Nectar Flow Monitoring

The Hive Status pollen grain provides real-time insights:

### Metrics Displayed
- **Position in Hive**: Queue position for processing
- **Nectar Collection**: Estimated processing time
- **Active Workers**: Current processing threads
- **Honey Harvested**: Completed tasks today
- **Hive Activity**: Overall system load (Low/Medium/High)

### Visual Indicators
- **Progress Bar**: Amber-colored nectar collection progress
- **Color-Coded Status**: Activity levels with appropriate colors
- **Live Updates**: Real-time data refresh without page reload

## 🚀 Future Customization Features

### Planned Enhancements
1. **Drag & Drop Arrangement**: Users can reorder pollen grains
2. **Custom Pollen Grains**: Create personal quick actions
3. **Seasonal Collections**: Themed pollen sets for different workflows
4. **Sharing Baskets**: Export/import pollen configurations
5. **Automation Triggers**: Connect actions to workflow conditions

### Extensibility Points
```javascript
// User preference schema
const userBasketConfig = {
  pollenOrder: ['nectar-upload', 'forager', 'hive-monitor'],
  hiddenPollen: ['queen-chamber'],
  customPollen: [
    {
      id: 'user-custom-1',
      label: 'My Custom Action',
      // ... configuration
    }
  ],
  theme: 'spring' // spring, summer, autumn, winter
};
```

## 🔧 Integration Points

### STING Ecosystem Connections
- **Honey Jar System**: Direct creation and search integration
- **Bee Chat**: Seamless conversation context preservation
- **Authentication**: Kratos role-based permission system
- **Knowledge Service**: Real-time search and indexing
- **Analytics**: Usage tracking for pollen grain popularity

### API Endpoints
```bash
# User preferences
GET/POST /api/users/pollen-basket-config

# Nectar flow status
GET /api/hive/nectar-flow

# Custom pollen grains
POST /api/users/custom-pollen
```

## 📈 Usage Analytics

### Tracked Metrics
- **Pollen Grain Popularity**: Most used actions
- **Session Duration**: Time spent with basket open
- **Conversion Rates**: Actions leading to completed workflows
- **Customization Adoption**: Users creating custom pollen
- **Cross-Pollination**: Actions used in sequence

## 🎯 Success Metrics

### User Experience Goals
- **Reduced Click Distance**: 50% fewer clicks to common actions
- **Improved Workflow Efficiency**: 30% faster task completion
- **Higher Feature Discovery**: 40% increase in feature adoption
- **Customization Engagement**: 25% of users create custom pollen

## 🐛 Known Limitations

### Current Constraints
- **Fixed Position**: Bottom-right placement only
- **Limited Themes**: Single bee theme available
- **Static Configuration**: No real-time pollen updates
- **Mobile Optimization**: Requires responsive improvements

### Planned Resolutions
- Mobile-first responsive design
- Multiple positioning options
- Dynamic pollen grain loading
- Theme customization system

## 📝 Contributing

### Adding New Pollen Grains
1. Define pollen grain configuration in `pollenGrains` array
2. Implement action callback function
3. Add appropriate role-based permissions
4. Update documentation and tooltips
5. Add analytics tracking

### Theming Guidelines
- Use bee/nature terminology consistently
- Maintain amber/honey color palette
- Provide meaningful metaphors for technical actions
- Ensure accessibility with proper ARIA labels

---

*The Pollen Basket represents STING's commitment to user-centric design, where powerful functionality meets delightful, nature-inspired interaction patterns.*