// Batch update script to add GlassCard to all pages
const fs = require('fs');
const path = require('path');

const filesToUpdate = [
  { path: './AnalyticsPage.jsx', hasStatsCard: true },
  { path: './HoneyJarPage.jsx', hasStatsCard: false },
  { path: './HiveManagerPage.jsx', hasStatsCard: false },
  { path: './SwarmOrchestrationPage.jsx', hasStatsCard: false },
  { path: './MarketplacePage.jsx', hasStatsCard: false },
  { path: '../user/UserSettings.jsx', hasStatsCard: false },
  { path: '../settings/BeeSettings.jsx', hasStatsCard: false }
];

filesToUpdate.forEach(file => {
  const filePath = path.join(__dirname, file.path);
  
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    
    // Add GlassCard import after first import
    if (!content.includes('GlassCard')) {
      content = content.replace(
        /import React[^;]+;/,
        "$&\nimport GlassCard from '../common/GlassCard';"
      );
    }
    
    // Replace card divs with GlassCard components
    // Standard cards
    content = content.replace(
      /<div className="standard-card([^"]*)">/g,
      '<GlassCard elevation="medium" className="$1">'
    );
    
    // Standard card light
    content = content.replace(
      /<div className="standard-card-light([^"]*)">/g,
      '<GlassCard variant="subtle" elevation="low" className="$1">'
    );
    
    // Standard card solid
    content = content.replace(
      /<div className="standard-card-solid([^"]*)">/g,
      '<GlassCard variant="strong" elevation="high" className="$1">'
    );
    
    // Dynamic cards
    content = content.replace(
      /<div className="dynamic-card([^"]*)">/g,
      '<GlassCard elevation="medium" className="$1">'
    );
    
    // Dynamic card subtle
    content = content.replace(
      /<div className="dynamic-card-subtle([^"]*)">/g,
      '<GlassCard variant="subtle" elevation="low" className="$1">'
    );
    
    // Dashboard cards
    content = content.replace(
      /<div className="dashboard-card([^"]*)">/g,
      '<GlassCard elevation="high" className="$1">'
    );
    
    // Glass cards
    content = content.replace(
      /<div className="glass-card([^"]*)">/g,
      '<GlassCard className="$1">'
    );
    
    // Write back
    fs.writeFileSync(filePath, content);
    console.log(`✅ Updated ${file.path}`);
    
  } catch (error) {
    console.error(`❌ Error updating ${file.path}:`, error.message);
  }
});

console.log('\n⚠️  Note: You need to manually update the closing </div> tags to </GlassCard>');
console.log('Search for GlassCard components and ensure their closing tags match.');