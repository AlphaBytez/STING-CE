#!/bin/bash
# STING Management Script - Example of New Verbose Structure
# This is a preview of how the refactored script will look

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"

# Platform detection and environment setup (kept in main for visibility)
if [[ "$(uname)" == "Darwin" ]]; then
    echo "Detected macOS platform"
    export INSTALL_DIR="$HOME/.sting-ce"
    export LOG_DIR="$HOME/.sting-ce/logs"
    export CONFIG_DIR="$HOME/.sting-ce/conf"
    export STING_USER="$USER"
    export STING_GROUP="staff"
else
    echo "Detected Linux platform"
    export INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
    export LOG_DIR="${INSTALL_DIR}/logs"
    export CONFIG_DIR="${INSTALL_DIR}/conf"
    export STING_USER="${SUDO_USER:-$USER}"
    export STING_GROUP="$(id -gn ${SUDO_USER:-$USER})"
fi

# Source core modules that are always needed
source "${LIB_DIR}/core.sh"
source "${LIB_DIR}/logging.sh"

# Initialize logging
init_logging

# Main command dispatcher - verbose and human-readable
main() {
    local command="$1"
    shift
    
    case "$command" in
        start|--start|-s)
            echo "======================================"
            echo "Starting STING Services"
            echo "======================================"
            
            # Load required modules for this operation
            source "${LIB_DIR}/environment.sh"
            source "${LIB_DIR}/services.sh"
            
            # Clear description of what's happening
            echo "Loading environment variables..."
            source_service_envs
            
            if [ -n "$1" ]; then
                echo "Starting specific service: $1"
                start_service "$1"
            else
                echo "Starting all STING services..."
                echo "This includes: database, authentication, backend API, frontend, and LLM gateway"
                start_all_services
            fi
            ;;
            
        stop|--stop|-t)
            echo "======================================"
            echo "Stopping STING Services"
            echo "======================================"
            
            source "${LIB_DIR}/services.sh"
            
            if [ -n "$1" ]; then
                echo "Stopping specific service: $1"
                stop_service "$1"
            else
                echo "Stopping all STING services..."
                stop_all_services
            fi
            ;;
            
        install|--install|-i)
            echo "======================================"
            echo "STING Installation"
            echo "======================================"
            echo
            echo "This will install the STING platform with:"
            echo "  - Database (PostgreSQL)"
            echo "  - Authentication (Ory Kratos)"
            echo "  - Backend API"
            echo "  - Frontend (React)"
            echo "  - LLM Gateway and Model Services"
            echo
            
            source "${LIB_DIR}/installation.sh"
            source "${LIB_DIR}/configuration.sh"
            
            echo "Checking system dependencies..."
            check_and_install_dependencies || exit 1
            
            echo "Setting up configuration..."
            generate_initial_configuration
            
            echo "Installing STING..."
            install_msting "$@"
            ;;
            
        status|--status)
            echo "======================================"
            echo "STING Service Status"
            echo "======================================"
            
            source "${LIB_DIR}/services.sh"
            source "${LIB_DIR}/health.sh"
            
            echo "Checking service health..."
            # This would call various health check functions
            ;;
            
        help|--help|-h|"")
            echo "======================================"
            echo "STING Management Script v${SCRIPT_VERSION}"
            echo "======================================"
            echo
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  start, -s     Start STING services"
            echo "  stop, -t      Stop STING services"
            echo "  restart, -r   Restart STING services"
            echo "  status        Show service status"
            echo "  install, -i   Install STING"
            echo "  uninstall     Remove STING installation"
            echo "  backup        Create backup"
            echo "  restore       Restore from backup"
            echo "  logs          View logs"
            echo "  help, -h      Show this help"
            echo
            echo "Examples:"
            echo "  $0 start              # Start all services"
            echo "  $0 start frontend     # Start only frontend"
            echo "  $0 logs -f            # Follow logs"
            echo "  $0 backup             # Create backup"
            ;;
            
        *)
            echo "Unknown command: $command"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"