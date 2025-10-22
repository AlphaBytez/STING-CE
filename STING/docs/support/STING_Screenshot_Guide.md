# STING Teaser Site - Screenshot Guide

## Overview
This guide provides a direct list of all screenshots needed for the STING teaser website, with recommended filenames and placement instructions.

## Screenshot Requirements

### 1. Main Pipeline Dashboard
**Filename:** `pipeline-dashboard.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- The main dashboard showing the document processing pipeline
- Include drag & drop interface for document upload
- Show processing status indicators (Ingesting → Processing → Packaging → Ready)
- Display real-time metrics (documents processed, PII redacted, embeddings created)
- Ensure the Honey Jar creation button is visible
- Use dark theme with yellow (#eab308) accents

### 2. Bee AI Chat Interface
**Filename:** `bee-chat-interface.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Active conversation with the Bee AI assistant
- Show the floating chat bubble with bee icon
- Include a query about sensitive data with PII automatically redacted
- Display the glass morphism chat interface
- Show at least 2-3 message exchanges

### 3. Honey Jar Creation Modal
**Filename:** `honey-pot-creation.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- The Honey Jar creation dialog
- Show encryption options and access controls
- Include pricing settings for marketplace
- Display the hexagonal design elements
- Show fields filled with example data

### 4. Nectar Flow Dashboard
**Filename:** `nectar-flow-dashboard.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Real-time monitoring graphs and charts
- Processing queue visualization with active jobs
- Resource utilization meters (CPU, Memory, Storage)
- Audit log preview with recent activities
- Use dark background with contrasting data visualizations

### 5. Security Dashboard
**Filename:** `security-dashboard.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Real-time threat detection panel with green "All Secure" status
- Audit log viewer with recent actions (user logins, document access, API calls)
- PII scrambling in action - before/after view of redacted content
- Compliance checklist showing HIPAA, GDPR, SOX indicators
- Access control matrix with role permissions
- **Note:** Blur any real usernames/emails

### 6. Knowledge Marketplace
**Filename:** `knowledge-marketplace.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Grid view of available Honey Pots with hexagonal cards
- Categories sidebar (Legal, Medical, Financial, Technical)
- Show pricing ranges ($50-$5000), ratings (4.8+ stars), and download counts
- Featured/trending Honey Pots section at top
- Your earnings dashboard if available
- Use variety in the displayed Honey Pots

### 7. Setup & Configuration
**Filename:** `setup-wizard.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Clean setup interface with step indicators
- Model selection screen (Phi-3, DeepSeek, TinyLlama options)
- Hardware detection showing GPU/Metal acceleration
- Success screen with "STING is ready" message
- **Alternative:** Terminal showing successful Docker deployment with STING ASCII art logo

### 8. Mobile Responsive View (Optional)
**Filename:** `mobile-responsive.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- STING running on tablet/phone view
- Floating navigation in mobile view
- Touch-friendly interface elements
- Responsive dashboard layout

### 9. Team Collaboration View (Optional)
**Filename:** `team-collaboration.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Multiple users in a shared workspace
- Swarm networking visualization
- Real-time collaboration indicators
- Chat/activity feed

### 10. API Documentation (Optional)
**Filename:** `api-documentation.png`  
**Location:** `/sting-teaser-site/static/images/screenshots/`  
**What to capture:**
- Clean API docs with code examples
- Interactive API explorer
- SDK showcase with multiple languages

## Implementation Instructions

1. **Create directory structure:**
   ```bash
   mkdir -p sting-teaser-site/static/images/screenshots
   ```

2. **Place screenshots in the directory with exact filenames listed above**

3. **Update the markdown content to reference images:**
   Replace placeholder divs with:
   ```markdown
   ![Screenshot Description](/images/screenshots/filename.png)
   ```

4. **Optimize images before uploading:**
   - Use PNG format for best quality
   - Aim for 1920x1080 resolution or similar
   - Compress using tools like TinyPNG
   - Keep file sizes under 500KB each

## Color & Style Guidelines

- **Background:** Use the darkest theme available (#0f1419 or similar)
- **Accent Color:** STING Yellow (#eab308)
- **Glass Effects:** Enable any transparency/blur effects
- **Data:** Use realistic but anonymized data
- **Status Indicators:** Show mostly green/positive states
- **Charts:** Use vibrant colors that contrast with dark background

## Tips for Best Results

1. **Consistency:** Keep the same zoom level and window size across screenshots
2. **Content:** Fill interfaces with realistic data, avoid empty states
3. **Privacy:** Blur or replace any real email addresses, names, or sensitive data
4. **Highlighting:** Use the yellow accent color to draw attention to key features
5. **Context:** Show enough UI to understand the feature without overwhelming detail