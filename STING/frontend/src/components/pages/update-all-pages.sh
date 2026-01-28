#!/bin/bash

# Script to update all pages with GlassCard import and usage

# List of page files to update
pages=(
  "TeamsPage.jsx"
  "AnalyticsPage.jsx"
  "HoneyJarPage.jsx"
  "HiveManagerPage.jsx"
  "SwarmOrchestrationPage.jsx"
  "MarketplacePage.jsx"
)

# Add GlassCard import to each file
for page in "${pages[@]}"; do
  echo "Updating $page..."
  
  # Add import after the first import line
  sed -i '' '2i\
import GlassCard from '"'"'../common/GlassCard'"'"';
' "$page"
  
  # Replace standard-card divs with GlassCard
  sed -i '' 's/<div className="standard-card/<GlassCard variant="default" elevation="medium" className="/g' "$page"
  sed -i '' 's/<div className="standard-card-light/<GlassCard variant="subtle" elevation="low" className="/g' "$page"
  sed -i '' 's/<div className="standard-card-solid/<GlassCard variant="strong" elevation="high" className="/g' "$page"
  
  # Replace dynamic-card divs with GlassCard
  sed -i '' 's/<div className="dynamic-card/<GlassCard variant="default" elevation="medium" className="/g' "$page"
  sed -i '' 's/<div className="dynamic-card-subtle/<GlassCard variant="subtle" elevation="low" className="/g' "$page"
  
  # Replace dashboard-card divs with GlassCard
  sed -i '' 's/<div className="dashboard-card/<GlassCard elevation="high" className="/g' "$page"
  
  # Update closing divs that were cards
  # This is tricky - we need to manually review and update
  echo "  - Added import and replaced card divs"
done

echo "Done! Please manually review and update closing </div> tags to </GlassCard>"