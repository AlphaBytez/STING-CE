# Custom Promtail with health check dependencies
FROM grafana/promtail:3.3.0

# Install necessary tools for health checks and troubleshooting
# Using root user to install packages, then switch back to promtail user
USER root

# Install curl and other utilities for health checks (Debian-based)
# Remove problematic backports repository and install packages
RUN sed -i '/bullseye-backports/d' /etc/apt/sources.list 2>/dev/null || true && \
    apt-get update && \
    apt-get install -y curl wget netcat-openbsd procps && \
    rm -rf /var/lib/apt/lists/*

# Keep using root for now (can be improved later)
# Note: The base image might not have a promtail user
# USER promtail

# Health check to ensure Promtail is responding
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#     CMD curl -f http://localhost:9080/ready || exit 1

# Use the same command as the base image
CMD ["/usr/bin/promtail", "-config.file=/etc/promtail/promtail.yml"]