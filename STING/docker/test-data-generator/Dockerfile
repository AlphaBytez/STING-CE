# STING Test Data Generator Container
# Generates enterprise-scale synthetic test data for PII detection demos

FROM openjdk:17-jdk-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    wget \
    unzip \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install pandas faker

# Set working directory
WORKDIR /app

# Create output directory
RUN mkdir -p /data/output/{medical,legal,financial}

# Clone and setup Synthea
RUN git clone https://github.com/synthetichealth/synthea.git /app/synthea
WORKDIR /app/synthea

# Make Synthea executable
RUN chmod +x run_synthea

# Copy scripts
COPY generate_test_data.py /app/
COPY pii_tester.py /app/

# Set back to app directory
WORKDIR /app

# Default command
CMD ["python3", "generate_test_data.py"]