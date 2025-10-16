#!/bin/sh
set -e

# Run database migrations
kratos migrate sql -e --yes

# Start Kratos server with specific configuration
kratos serve --dev --config /etc/config/kratos/kratos.yml