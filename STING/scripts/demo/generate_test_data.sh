#!/bin/bash
#
# Containerized Test Data Generation Script for STING
# Generates enterprise-scale synthetic test data using Docker
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker/test-data-generator"
OUTPUT_DIR="$SCRIPT_DIR/../test_data_output"

# Default parameters (can be overridden)
NUM_PATIENTS=${NUM_PATIENTS:-1000}
NUM_LEGAL_DOCS=${NUM_LEGAL_DOCS:-500}  
NUM_FINANCIAL_RECORDS=${NUM_FINANCIAL_RECORDS:-1000}

echo -e "${BLUE}🎯 STING Containerized Test Data Generation${NC}"
echo "=================================================="

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --patients)
            NUM_PATIENTS="$2"
            shift 2
            ;;
        --legal-docs)
            NUM_LEGAL_DOCS="$2"
            shift 2
            ;;
        --financial-records)
            NUM_FINANCIAL_RECORDS="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --patients NUM          Number of synthetic patients (default: 1000)"
            echo "  --legal-docs NUM        Number of legal documents (default: 500)" 
            echo "  --financial-records NUM Number of financial records (default: 1000)"
            echo "  --output-dir DIR        Output directory (default: ../test_data_output)"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Generate with defaults"
            echo "  $0 --patients 5000 --legal-docs 1000 # Large dataset"
            echo "  $0 --patients 100                    # Quick test"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}📊 Generation Parameters:${NC}"
echo "   Patients: $NUM_PATIENTS"
echo "   Legal Documents: $NUM_LEGAL_DOCS"
echo "   Financial Records: $NUM_FINANCIAL_RECORDS"
echo "   Output Directory: $OUTPUT_DIR"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    echo "Please install Docker and try again"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

echo -e "${GREEN}✅ Docker is available${NC}"

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${YELLOW}📁 Created output directory: $OUTPUT_DIR${NC}"

# Navigate to Docker directory
cd "$DOCKER_DIR"

# Create output directory for mounting
mkdir -p output

echo -e "${YELLOW}🔨 Building test data generator container...${NC}"
docker build -t sting-test-data-generator . 

echo -e "${YELLOW}🚀 Starting test data generation...${NC}"
echo "This may take 5-15 minutes depending on dataset size..."
echo ""

# Run the container with environment variables
docker run --rm \
    -e NUM_PATIENTS="$NUM_PATIENTS" \
    -e NUM_LEGAL_DOCS="$NUM_LEGAL_DOCS" \
    -e NUM_FINANCIAL_RECORDS="$NUM_FINANCIAL_RECORDS" \
    -v "$OUTPUT_DIR:/data/output" \
    --name sting-test-data-generator \
    sting-test-data-generator

# Check if generation was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 Test data generation completed successfully!${NC}"
    echo "=================================================="
    
    # Display summary if available
    if [ -f "$OUTPUT_DIR/generation_summary.json" ]; then
        echo -e "${BLUE}📊 Generation Summary:${NC}"
        
        # Extract key stats using simple tools (no jq dependency)
        if command -v python3 &> /dev/null; then
            python3 -c "
import json
with open('$OUTPUT_DIR/generation_summary.json', 'r') as f:
    data = json.load(f)
    
print(f'   🏥 Medical Files: {data[\"datasets\"][\"medical\"][\"files_generated\"]}')
print(f'   ⚖️  Legal Files: {data[\"datasets\"][\"legal\"][\"files_generated\"]}') 
print(f'   💳 Financial Files: {data[\"datasets\"][\"financial\"][\"files_generated\"]}')
print(f'   🔍 Total PII Elements: {data[\"total_estimated_pii\"]:,}')
print(f'   📅 Generated: {data[\"generated_at\"][:19]}')
"
        else
            echo "   📋 Check $OUTPUT_DIR/generation_summary.json for detailed stats"
        fi
    fi
    
    echo ""
    echo -e "${BLUE}📁 Data Location:${NC} $OUTPUT_DIR"
    echo -e "${BLUE}🎯 Ready for:${NC}"
    echo "   • Enterprise PII detection testing"
    echo "   • Medical/Legal/Financial demo scenarios"  
    echo "   • Performance benchmarking at scale"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "   1. Run STING PII detection on generated data"
    echo "   2. Use for compliance demos (HIPAA/GDPR/PCI-DSS)"
    echo "   3. Performance test with 10K+ records"
    
else
    echo ""
    echo -e "${RED}❌ Test data generation failed${NC}"
    echo "Check the Docker logs for details"
    exit 1
fi

# Cleanup
echo ""
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
rm -rf "$DOCKER_DIR/output" 2>/dev/null || true

echo -e "${GREEN}✅ Test data generation script completed!${NC}"