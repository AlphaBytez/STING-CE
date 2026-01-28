#!/bin/sh
echo "Starting Kratos migration..."
kratos migrate sql -e --yes
echo "Starting Kratos server..."
kratos serve --dev --config /etc/config/kratos/kratos.yml