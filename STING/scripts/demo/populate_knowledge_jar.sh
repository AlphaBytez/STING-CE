#!/bin/bash

# Populate General Knowledge Honey Jar with Documentation
# This script copies key documentation into the knowledge jar for better Bee Chat context

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW} Populating General Knowledge Honey Jar...${NC}"

# Source directory
DOCS_DIR="/Users/captain-wolf/Documents/GitHub/STING-CE/STING/docs"

# Create temporary directory for processing
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Key documentation to include
echo -e "${GREEN}📚 Collecting essential documentation...${NC}"

# Architecture and technical docs
cp "$DOCS_DIR/ARCHITECTURE.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/API_REFERENCE.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/STING_TECHNICAL_WHITEPAPER.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/TECHNOLOGY_STACK.md" "$TEMP_DIR/" 2>/dev/null || true

# Feature documentation
cp "$DOCS_DIR/features/HONEY_JAR_TECHNICAL_REFERENCE.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/features/HONEY_JAR_USER_GUIDE.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/features/PII_DETECTION_SYSTEM.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/features/REPORT_GENERATION_EXPLAINED.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/features/PASSWORDLESS_AUTHENTICATION.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/features/BEE_CHAT_MESSAGING_ARCHITECTURE.md" "$TEMP_DIR/" 2>/dev/null || true

# Admin and user guides
cp "$DOCS_DIR/ADMIN_GUIDE.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/INSTALLATION.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/COMMON_ERRORS_AND_FIXES.md" "$TEMP_DIR/" 2>/dev/null || true

# Business and product docs
cp "$DOCS_DIR/BUSINESS_OVERVIEW.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$DOCS_DIR/PRODUCT_ARCHITECTURE.md" "$TEMP_DIR/" 2>/dev/null || true

# Copy architecture subdirectory
if [ -d "$DOCS_DIR/architecture" ]; then
    cp -r "$DOCS_DIR/architecture" "$TEMP_DIR/" 2>/dev/null || true
fi

# Create a manifest file
echo -e "${GREEN}📝 Creating manifest...${NC}"
cat > "$TEMP_DIR/MANIFEST.md" << EOF
# STING Documentation Manifest

This honey jar contains essential STING documentation for Bee Chat context.

## Included Documentation

### Core Architecture
- ARCHITECTURE.md - System architecture overview
- STING_TECHNICAL_WHITEPAPER.md - Technical specifications
- TECHNOLOGY_STACK.md - Technology stack details
- API_REFERENCE.md - API documentation

### Features
- Honey Jar system documentation
- PII Detection system guide
- Report generation documentation
- Passwordless authentication guide
- Bee Chat architecture

### Administration
- Admin guide
- Installation instructions
- Common errors and fixes

### Business
- Business overview
- Product architecture

Generated: $(date)
EOF

# Count files
FILE_COUNT=$(find "$TEMP_DIR" -type f -name "*.md" | wc -l)
echo -e "${GREEN}[+] Collected $FILE_COUNT documentation files${NC}"

# Now we need to upload these to the knowledge jar
# This would typically involve calling the knowledge service API
echo -e "${YELLOW}📤 Uploading to General Knowledge honey jar...${NC}"

# Create a tar archive for upload
tar -czf "$TEMP_DIR/sting_docs.tar.gz" -C "$TEMP_DIR" .

# Call the knowledge service API to upload
# Note: This assumes the knowledge service is running and accessible
KNOWLEDGE_URL="http://localhost:5000/api/knowledge"
JAR_ID="general"  # The general knowledge jar

# Check if knowledge service is accessible
if curl -s -o /dev/null -w "%{http_code}" "$KNOWLEDGE_URL/health" | grep -q "200"; then
    echo -e "${GREEN}[+] Knowledge service is accessible${NC}"
    
    # Upload documents (this is a placeholder - actual API may differ)
    for file in "$TEMP_DIR"/*.md; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "Uploading $filename..."
            
            # Create JSON payload
            content=$(cat "$file" | jq -Rs .)
            json_payload=$(cat <<EOF
{
  "jar_id": "$JAR_ID",
  "filename": "$filename",
  "content": $content,
  "metadata": {
    "type": "documentation",
    "source": "STING docs",
    "uploaded_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
}
EOF
)
            
            # Upload to knowledge service
            curl -X POST "$KNOWLEDGE_URL/documents" \
                -H "Content-Type: application/json" \
                -d "$json_payload" \
                -s -o /dev/null || true
        fi
    done
    
    echo -e "${GREEN}[+] Documentation uploaded to General Knowledge honey jar${NC}"
else
    echo -e "${YELLOW}[!]  Knowledge service not accessible. Manual upload required.${NC}"
    echo -e "${YELLOW}   Archive saved at: $TEMP_DIR/sting_docs.tar.gz${NC}"
    
    # Copy archive to a persistent location
    cp "$TEMP_DIR/sting_docs.tar.gz" "/tmp/sting_docs_for_knowledge.tar.gz"
    echo -e "${YELLOW}   Archive copied to: /tmp/sting_docs_for_knowledge.tar.gz${NC}"
fi

echo -e "${GREEN} Knowledge jar population complete!${NC}"