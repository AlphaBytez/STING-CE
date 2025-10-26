#!/bin/bash
# Script to run Hugo server for the teaser site

TEASER_SITE_DIR="../sting-teaser-site"

if [ ! -d "$TEASER_SITE_DIR" ]; then
    echo "Error: Teaser site directory not found at $TEASER_SITE_DIR"
    exit 1
fi

echo "Starting Hugo server for STING teaser site..."
echo "The site will be available at http://localhost:1313"
echo "Press Ctrl+C to stop the server"
echo ""

cd "$TEASER_SITE_DIR" && hugo server -D --bind 0.0.0.0 --port 1313