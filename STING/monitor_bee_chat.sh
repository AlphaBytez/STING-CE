#!/bin/bash

echo "Monitoring Bee Chat logs..."
echo "=========================="
echo "Try sending a message in Bee Chat now..."
echo ""

# Monitor backend logs
echo "Backend logs:"
docker logs sting-ce-app -f 2>&1 | grep -E "external-ai|bee|chat|ERROR|error" &
BACKEND_PID=$!

# Monitor external-ai logs
echo -e "\nExternal AI logs:"
docker logs sting-ce-external-ai -f 2>&1 | grep -E "bee|chat|ERROR|error|POST" &
EXTERNAL_PID=$!

# Wait for user to stop
echo -e "\nPress Ctrl+C to stop monitoring..."
trap "kill $BACKEND_PID $EXTERNAL_PID 2>/dev/null; exit" INT
wait