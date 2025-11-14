#!/bin/bash
# Startup script for knowledge service

echo "Starting Knowledge Service..."

# Wait for database to be ready
echo "Waiting for database..."
# Only set DATABASE_URL if not already provided
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://postgres:postgres@db:5432/sting_app"
fi
for i in {1..30}; do
    if python -c "from database import engine; engine.connect()" 2>/dev/null; then
        echo "✅ Database is ready"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

# Check if we need to run migration (only if there's existing data)
if [ -d "/tmp/sting_uploads" ] && [ "$(ls -A /tmp/sting_uploads 2>/dev/null)" ]; then
    echo "Found existing data in /tmp/sting_uploads, checking for migration..."
    # Check if the directories contain actual document files (not just empty dirs)
    has_files=false
    for dir in /tmp/sting_uploads/*/; do
        if [ -d "$dir" ] && [ "$(ls -A "$dir" 2>/dev/null | grep -v '\.json$' | head -1)" ]; then
            has_files=true
            break
        fi
    done
    
    if [ "$has_files" = true ]; then
        echo "Running data migration..."
        python migrate_to_db.py
    else
        echo "No files to migrate, proceeding with initialization..."
    fi
else
    echo "No existing data found, proceeding with fresh initialization..."
fi

# Run unified initialization
echo "Running initialization..."
python -c "from initialization import run_initialization; run_initialization()"

# Start the application with database support
echo "Starting application..."
python app.py