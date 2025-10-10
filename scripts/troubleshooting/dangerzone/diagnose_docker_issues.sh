#!/usr/bin/env bash
# diagnose_docker_issues.sh

log_message() {
    echo "[INFO] $1"
}

diagnose_docker_issues() {
    log_message "Diagnosing Docker issues..."

    log_message "Current running containers:"
    docker ps

    log_message "All containers (including stopped):"
    docker ps -a

    log_message "Docker images:"
    docker images

    log_message "Docker networks:"
    docker network ls

    log_message "Docker volumes:"
    docker volume ls

    if command -v docker-compose &> /dev/null; then
        log_message "Docker Compose projects:"
        docker-compose ps
    fi

    if docker info | grep -q "Swarm: active"; then
        log_message "Docker Swarm services:"
        docker service ls
    fi

    log_message "Docker processes:"
    ps aux | grep docker

    log_message "Docker daemon status:"
    sudo systemctl status docker

    log_message "Recent Docker logs:"
    sudo journalctl -u docker -n 50

    log_message "Diagnosis complete. Please review the output for any issues."
}

diagnose_docker_issues
