#!/bin/bash

echo "Testing STING registration paths..."

# Test proxy connection to Kratos (through frontend proxy)
echo "Testing frontend proxy to Kratos..."
curl -k -i "https://localhost:3000/self-service/registration/browser" 

# Test direct connection to Kratos
echo -e "\n\nTesting direct connection to Kratos..."
curl -k -i "https://localhost:4433/self-service/registration/browser"

# Test Kratos health
echo -e "\n\nTesting Kratos health..."
curl -k -i "https://localhost:4433/health/ready"

echo -e "\n\nAll tests completed."