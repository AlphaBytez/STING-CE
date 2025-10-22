#!/bin/bash

# Load environment variables
source ${INSTALL_DIR}/conf/load_config.sh

# Function to initialize the database
initialize_database() {
    echo "Initializing the database..."
    # Use environment variable substitution for secure password handling
    envsubst < ${INSTALL_DIR}/conf/init_db.sql > /tmp/init_db_with_env.sql
    # Run the SQL script using psql
    psql -h db -U "${KC_DB_USERNAME}" -f /tmp/init_db_with_env.sql
}

# Check if the database is already initialized
if psql -h db -U "${KC_DB_USERNAME}" -d "${KC_DB}" -c '\dt' | grep -q 'No relations'; then
    initialize_database
else
    echo "Database is already initialized."
fi

# Check the APP_ENV variable to determine how to run the app
if [ "$APP_ENV" = "production" ]; then
    echo "Running in production mode"
    exec gunicorn --bind 0.0.0.0:5050 --workers 4 app.run:app
else
    echo "Running in development mode"
    exec python -m flask run --host=0.0.0.0 --port=5050
fi
