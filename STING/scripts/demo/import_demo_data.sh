#!/bin/bash
# STING Demo Data Importer
# Loads sample honey jar data for demonstrations

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}📥 STING Demo Data Importer${NC}"
echo -e "${YELLOW}Loading sample threat intelligence data...${NC}\n"

# Configuration
API_BASE="http://localhost:5050/api"
KNOWLEDGE_API="http://localhost:8090"

# Function to check service availability
check_service() {
    local service_url=$1
    local service_name=$2
    
    if curl -s -f "$service_url/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $service_name is available${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $service_name is not available${NC}"
        return 1
    fi
}

# Check services
echo "Checking services..."
check_service "$API_BASE" "STING API"
check_service "$KNOWLEDGE_API" "Knowledge Service"

# Create demo honey jars
echo -e "\n${YELLOW}Creating demo honey jars...${NC}"

# SSH Honey Jar
curl -s -X POST "$API_BASE/honey jars" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Production SSH Server",
        "type": "ssh",
        "description": "Simulated production SSH server honey jar",
        "configuration": {
            "port": 2222,
            "banner": "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5",
            "allow_root": false
        }
    }' > /dev/null && echo -e "${GREEN}✓ Created SSH honey jar${NC}"

# Web Application Honey Jar
curl -s -X POST "$API_BASE/honey jars" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Corporate Web Portal",
        "type": "web",
        "description": "Simulated corporate web application",
        "configuration": {
            "port": 8080,
            "applications": ["wordpress", "phpmyadmin", "webmail"],
            "vulnerabilities": ["sql_injection", "xss", "file_upload"]
        }
    }' > /dev/null && echo -e "${GREEN}✓ Created Web honey jar${NC}"

# Database Honey Jar
curl -s -X POST "$API_BASE/honey jars" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Customer Database",
        "type": "database",
        "description": "Simulated MySQL database server",
        "configuration": {
            "port": 3307,
            "version": "MySQL 8.0.32",
            "databases": ["customers", "products", "analytics"]
        }
    }' > /dev/null && echo -e "${GREEN}✓ Created Database honey jar${NC}"

# Import threat intelligence to knowledge base
echo -e "\n${YELLOW}Importing threat intelligence...${NC}"

# Create threat intelligence knowledge base
curl -s -X POST "$KNOWLEDGE_API/honey-pots" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Global Threat Intelligence",
        "description": "Curated threat intelligence from multiple sources",
        "type": "public",
        "tags": ["threats", "iocs", "malware", "campaigns"]
    }' > /dev/null && echo -e "${GREEN}✓ Created threat intelligence knowledge base${NC}"

# Sample threat data
cat > /tmp/demo_threats.json << EOF
{
    "threats": [
        {
            "type": "botnet",
            "name": "Mirai Variant X",
            "description": "New Mirai botnet variant targeting IoT devices",
            "iocs": ["192.168.1.100", "malware.evil.com", "5d41402abc4b2a76b9719d911017c592"],
            "first_seen": "2024-01-15",
            "severity": "high"
        },
        {
            "type": "apt",
            "name": "APT28 Campaign",
            "description": "Sophisticated spear-phishing campaign",
            "iocs": ["apt28.state-actor.com", "10.0.0.50"],
            "first_seen": "2024-02-01",
            "severity": "critical"
        },
        {
            "type": "ransomware",
            "name": "LockBit 3.0",
            "description": "Ransomware-as-a-Service operation",
            "iocs": ["lockbit3.onion", "45.89.125.34"],
            "first_seen": "2024-01-20",
            "severity": "critical"
        }
    ]
}
EOF

# Import historical attack data
echo -e "\n${YELLOW}Generating historical attack data...${NC}"

# Generate 7 days of historical data
for days_ago in {7..1}; do
    date=$(date -u -d "$days_ago days ago" +"%Y-%m-%d")
    echo -e "Generating data for $date..."
    
    # SSH attacks
    for i in {1..50}; do
        timestamp="${date}T$(printf "%02d" $((RANDOM % 24))):$(printf "%02d" $((RANDOM % 60))):$(printf "%02d" $((RANDOM % 60)))Z"
        ip="$((RANDOM % 256)).$((RANDOM % 256)).$((RANDOM % 256)).$((RANDOM % 256))"
        
        curl -s -X POST "$API_BASE/events" \
            -H "Content-Type: application/json" \
            -d "{
                \"honey jar_id\": \"ssh-001\",
                \"timestamp\": \"$timestamp\",
                \"event_type\": \"authentication_failure\",
                \"source_ip\": \"$ip\",
                \"details\": {
                    \"username\": \"root\",
                    \"method\": \"password\"
                }
            }" > /dev/null 2>&1 || true
    done
    
    # Web attacks
    for i in {1..30}; do
        timestamp="${date}T$(printf "%02d" $((RANDOM % 24))):$(printf "%02d" $((RANDOM % 60))):$(printf "%02d" $((RANDOM % 60)))Z"
        ip="$((RANDOM % 256)).$((RANDOM % 256)).$((RANDOM % 256)).$((RANDOM % 256))"
        
        curl -s -X POST "$API_BASE/events" \
            -H "Content-Type: application/json" \
            -d "{
                \"honey jar_id\": \"web-001\",
                \"timestamp\": \"$timestamp\",
                \"event_type\": \"suspicious_request\",
                \"source_ip\": \"$ip\",
                \"details\": {
                    \"path\": \"/admin/config.php\",
                    \"method\": \"GET\",
                    \"user_agent\": \"Mozilla/5.0 (bot)\"
                }
            }" > /dev/null 2>&1 || true
    done
done

echo -e "${GREEN}✓ Generated 7 days of historical data${NC}"

# Create sample security reports
echo -e "\n${YELLOW}Creating sample reports...${NC}"

cat > /tmp/security_report.md << EOF
# Weekly Security Report
Generated: $(date)

## Executive Summary
- Total attacks detected: 523
- Unique source IPs: 187
- Critical threats: 3
- High priority actions: 5

## Top Attack Vectors
1. SSH Brute Force (45%)
2. Web Application Scans (30%)
3. SQL Injection Attempts (15%)
4. Port Scans (10%)

## Recommendations
1. Implement rate limiting on SSH
2. Deploy WAF rules for common web attacks
3. Enable anomaly detection for database access
4. Configure automated IP blocking for repeat offenders
EOF

echo -e "${GREEN}✓ Created sample security report${NC}"

# Final summary
echo -e "\n${GREEN}✅ Demo data import complete!${NC}"
echo -e "\nLoaded:"
echo -e "  • 3 honey jars (SSH, Web, Database)"
echo -e "  • 7 days of historical attack data"
echo -e "  • Threat intelligence database"
echo -e "  • Sample security reports"
echo -e "\n${YELLOW}Your demo environment is ready! 🎯${NC}"