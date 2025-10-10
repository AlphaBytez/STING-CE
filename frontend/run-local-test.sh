#!/bin/bash
# Run the frontend locally for testing

cd "$(dirname "$0")"
echo "Starting local development server for testing..."

# Create a timestamp to see if we're getting fresh changes
TIMESTAMP=$(date)
echo "// Test timestamp: $TIMESTAMP" >> src/components/TestDashboard.jsx

# Start the React dev server
npm run start