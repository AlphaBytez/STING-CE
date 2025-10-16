#!/bin/bash
# development.sh - Development tools and utilities

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"
source "${SCRIPT_DIR}/docker.sh"

# Run tests in development container
run_tests() {
    log_message "Running tests in development container..."
    run_in_dev_container "pytest"
}

# Run linting checks
run_linting() {
    log_message "Running linting checks in development container..."
    run_in_dev_container "black . && flake8"
}

# Build the project
build_project() {
    log_message "Building project in development container..."
    ensure_dev_container
    run_in_dev_container "python setup.py build"
}

# Clean up development environment
cleanup_development() {
    log_message "Performing development cleanup..."
    
    # Stop all containers first
    log_message "Stopping containers..."
    docker compose down -v || true
    
    # Remove containers and images
    log_message "Removing containers and images..."
    if docker ps -a --filter "name=sting" -q | grep -q .; then
        docker rm -f $(docker ps -a --filter "name=sting" -q)
    fi
    if docker images 'sting-ce_*' -q | grep -q .; then
        docker rmi -f $(docker images 'sting-ce_*' -q)
    fi
    
    # Clean up auth data
    if [ -d "${INSTALL_DIR}/authentication/data" ]; then
        rm -rf "${INSTALL_DIR}/authentication/data"
    fi

    # Clean Vault data if needed
    if docker volume ls | grep -q "vault-data"; then
        docker volume rm vault-data vault-logs vault-file
        log_message "Cleaned Vault volumes"
    fi

    # Clean build cache
    log_message "Cleaning build cache..."
    docker builder prune -f -a

    # Clean environment files but preserve configuration
    log_message "Cleaning temporary files..."
    find "${INSTALL_DIR}" -name "*.tmp" -type f -delete
    find "${INSTALL_DIR}" -name "*.log" -type f -delete
    find "${INSTALL_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

    read -p "Would you like to start a fresh rebuild? (y/N): " rebuild
    if [[ $rebuild == [yY] || $rebuild == [yY][eE][sS] ]]; then
        log_message "Rebuilding images..."
        # Note: manage_services is from services.sh - we'll handle this differently
        docker compose build --no-cache
    else
        log_message "Development cleanup completed. You can now rebuild with: sudo msting -b --no-cache"
        return 0
    fi
}

# Reset development environment (quick version)
reset_development() {
    log_message "Performing quick development reset..."
    
    # Stop services
    docker compose down -v
    
    # Remove containers and images but preserve volumes
    docker compose rm -f  # Fixed typo from original
    
    # Remove only sting images
    if docker images 'sting-ce_*' -q | grep -q .; then
        docker rmi -f $(docker images 'sting-ce_*' -q)
    fi
    
    # Clean just the build cache for sting
    docker builder prune -f --filter until=24h
    
    log_message "Development reset completed."
    log_message "You can now rebuild with: sudo msting -b --no-cache"
}

# Helper function: Run development server
run_dev_server() {
    log_message "Starting development server..."
    ensure_dev_container
    run_in_dev_container "python manage.py runserver 0.0.0.0:8000"
}

# Helper function: Run database migrations
run_migrations() {
    log_message "Running database migrations..."
    ensure_dev_container
    run_in_dev_container "python manage.py migrate"
}

# Helper function: Create database migrations
create_migration() {
    local app_name="$1"
    local migration_name="$2"
    
    if [ -z "$app_name" ] || [ -z "$migration_name" ]; then
        log_message "Usage: create_migration <app_name> <migration_name>" "ERROR"
        return 1
    fi
    
    log_message "Creating migration for $app_name: $migration_name"
    ensure_dev_container
    run_in_dev_container "python manage.py makemigrations $app_name --name $migration_name"
}

# Helper function: Run shell in development container
run_dev_shell() {
    log_message "Starting development shell..."
    ensure_dev_container
    docker compose exec dev bash
}

# Helper function: Run Python shell in development container
run_python_shell() {
    log_message "Starting Python shell..."
    ensure_dev_container
    run_in_dev_container "python manage.py shell"
}

# Helper function: Install Python requirements
install_requirements() {
    local requirements_file="${1:-requirements.txt}"
    log_message "Installing requirements from $requirements_file..."
    ensure_dev_container
    run_in_dev_container "pip install -r $requirements_file"
}

# Helper function: Generate requirements file
generate_requirements() {
    log_message "Generating requirements.txt..."
    ensure_dev_container
    run_in_dev_container "pip freeze > requirements.txt"
}

# Helper function: Run code formatting
format_code() {
    log_message "Formatting code..."
    ensure_dev_container
    run_in_dev_container "black . && isort ."
}

# Helper function: Run security checks
run_security_checks() {
    log_message "Running security checks..."
    ensure_dev_container
    run_in_dev_container "bandit -r . && safety check"
}

# Helper function: Generate code coverage report
run_coverage() {
    log_message "Running tests with coverage..."
    ensure_dev_container
    run_in_dev_container "pytest --cov=. --cov-report=html --cov-report=term"
}

# Helper function: Run type checking
run_type_checks() {
    log_message "Running type checks..."
    ensure_dev_container
    run_in_dev_container "mypy ."
}

# Helper function: Clean Python cache files
clean_python_cache() {
    log_message "Cleaning Python cache files..."
    find "${INSTALL_DIR}" -type f -name "*.pyc" -delete
    find "${INSTALL_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find "${INSTALL_DIR}" -type f -name ".coverage" -delete
    find "${INSTALL_DIR}" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
    find "${INSTALL_DIR}" -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null
    log_message "Python cache cleaned"
}

# Helper function: Update all dependencies
update_dependencies() {
    log_message "Updating all dependencies..."
    
    # Update Python dependencies
    ensure_dev_container
    run_in_dev_container "pip install --upgrade pip setuptools wheel"
    run_in_dev_container "pip install --upgrade -r requirements.txt"
    
    # Update frontend dependencies
    if [ -d "${INSTALL_DIR}/frontend" ]; then
        log_message "Updating frontend dependencies..."
        cd "${INSTALL_DIR}/frontend" || return 1
        npm update
        npm audit fix
    fi
    
    log_message "Dependencies updated"
}