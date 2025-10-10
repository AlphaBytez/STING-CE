#!/bin/bash
# STING Management Script - Logging Module
# This module enhances the bootstrap logging with additional functionality

# If bootstrap.sh was loaded, log_message already exists and works
# This module just adds enhanced logging features

# Enhanced log file location setup with organized structure
setup_enhanced_logging() {
    # Set up proper log directories if we have permissions
    if [ -w "$INSTALL_DIR" ] || [ -w "$(dirname "$INSTALL_DIR")" ]; then
        local log_dir="${INSTALL_DIR}/logs"
        mkdir -p "$log_dir" 2>/dev/null || true
        mkdir -p "$log_dir/commands" 2>/dev/null || true
        mkdir -p "$log_dir/docker" 2>/dev/null || true
        mkdir -p "$log_dir/verbose" 2>/dev/null || true

        if [ -w "$log_dir" ]; then
            export LOG_FILE="${log_dir}/manage_sting.log"
            export LOG_COMMANDS_DIR="${log_dir}/commands"
            export LOG_DOCKER_DIR="${log_dir}/docker"
            export LOG_VERBOSE_DIR="${log_dir}/verbose"

            # Only log this once
            if [ -z "$ENHANCED_LOGGING_ENABLED" ]; then
                log_message "Enhanced logging enabled: $LOG_FILE"
                export ENHANCED_LOGGING_ENABLED=1
            fi
        fi
    fi
}

# Verbosity level control
# VERBOSITY_LEVEL: quiet, default, verbose
export VERBOSITY_LEVEL="${VERBOSITY_LEVEL:-default}"

# Setup verbosity level based on flags
setup_verbosity_level() {
    case "$1" in
        -q|--quiet)
            export VERBOSITY_LEVEL="quiet"
            ;;
        -v|--verbose)
            export VERBOSITY_LEVEL="verbose"
            ;;
        *)
            export VERBOSITY_LEVEL="default"
            ;;
    esac
}

# Enhanced log message function that respects verbosity
log_message_verbose() {
    local message="$1"
    local level="${2:-INFO}"
    local force_show="${3:-false}"

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Color codes
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local NC='\033[0m' # No Color

    # Set color based on level
    local color=""
    case "$level" in
        ERROR) color="$RED" ;;
        SUCCESS) color="$GREEN" ;;
        WARNING) color="$YELLOW" ;;
    esac

    # Always log to file
    if [ -w "$LOG_FILE" ] || [ -w "$(dirname "$LOG_FILE")" ]; then
        echo "${timestamp} - [${level}] ${message}" >> "$LOG_FILE" 2>/dev/null
    fi

    # Control console output based on verbosity
    case "$VERBOSITY_LEVEL" in
        quiet)
            # Only show errors and forced messages
            if [[ "$level" == "ERROR" ]] || [[ "$force_show" == "true" ]]; then
                if [ -n "$color" ]; then
                    echo -e "${color}${timestamp} - ${message}${NC}"
                else
                    echo "${timestamp} - ${message}"
                fi
            fi
            ;;
        verbose)
            # Show everything
            if [ -n "$color" ]; then
                echo -e "${color}${timestamp} - ${message}${NC}"
            else
                echo "${timestamp} - ${message}"
            fi
            ;;
        default)
            # Show essential info (errors, warnings, success, forced)
            if [[ "$level" =~ ^(ERROR|WARNING|SUCCESS)$ ]] || [[ "$force_show" == "true" ]]; then
                if [ -n "$color" ]; then
                    echo -e "${color}${timestamp} - ${message}${NC}"
                else
                    echo "${timestamp} - ${message}"
                fi
            fi
            ;;
    esac
}

# Progress indicator for long operations
show_progress() {
    local current=$1
    local total=$2
    local operation=${3:-"Processing"}
    
    local percent=$((current * 100 / total))
    local bar_length=20
    local filled_length=$((percent * bar_length / 100))
    
    printf "\r${operation}: ["
    for ((i=0; i<filled_length; i++)); do printf "="; done
    for ((i=filled_length; i<bar_length; i++)); do printf " "; done
    printf "] %d%%" "$percent"
    
    if [ "$current" -eq "$total" ]; then
        echo ""  # New line when complete
    fi
}

# Log with different levels
log_error() {
    log_message "$1" "ERROR"
}

log_warning() {
    log_message "$1" "WARNING"
}

log_success() {
    log_message "$1" "SUCCESS"
}

log_info() {
    log_message "$1" "INFO"
}

# Log command execution
log_command() {
    local cmd="$1"
    log_message "Executing: $cmd"
    eval "$cmd"
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log_success "Command completed successfully"
    else
        log_error "Command failed with exit code: $exit_code"
    fi
    return $exit_code
}

# Execute command with logging and verbosity control
execute_with_logging() {
    local cmd="$1"
    local operation_name="${2:-Command}"
    local log_file_prefix="${3:-general}"

    local timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    local log_file="${LOG_COMMANDS_DIR}/${log_file_prefix}_${timestamp}.log"

    # Show operation start in essential info mode
    case "$VERBOSITY_LEVEL" in
        quiet)
            # Show minimal progress indicator
            printf "%s... " "$operation_name"
            ;;
        default)
            log_message "🔄 $operation_name..." "INFO" true
            ;;
        verbose)
            log_message "🔄 $operation_name..." "INFO" true
            log_message "Executing: $cmd" "INFO" true
            ;;
    esac

    # Execute command with output control
    local exit_code=0
    if [[ "$VERBOSITY_LEVEL" == "verbose" ]]; then
        # Verbose mode: show everything on console and log
        eval "$cmd" 2>&1 | tee "$log_file"
        exit_code=${PIPESTATUS[0]}
    else
        # Default/quiet mode: redirect to log file, show progress
        eval "$cmd" > "$log_file" 2>&1 &
        local cmd_pid=$!

        # Show progress while command runs
        while kill -0 "$cmd_pid" 2>/dev/null; do
            case "$VERBOSITY_LEVEL" in
                quiet)
                    printf "."
                    ;;
                default)
                    printf "."
                    ;;
            esac
            sleep 1
        done
        wait "$cmd_pid"
        exit_code=$?
    fi

    # Show completion status
    case "$VERBOSITY_LEVEL" in
        quiet)
            if [ $exit_code -eq 0 ]; then
                echo " ✅"
            else
                echo " ❌"
                # Show error in quiet mode
                log_message "❌ $operation_name failed (exit code: $exit_code)" "ERROR" true
                log_message "📄 Full log: $log_file" "ERROR" true
            fi
            ;;
        default|verbose)
            if [ $exit_code -eq 0 ]; then
                log_message "✅ $operation_name completed successfully" "SUCCESS" true
            else
                log_message "❌ $operation_name failed (exit code: $exit_code)" "ERROR" true
                log_message "📄 Full log: $log_file" "ERROR" true
            fi
            ;;
    esac

    return $exit_code
}

# Enhanced progress indicator with emojis
show_build_progress() {
    local operation="$1"
    local duration="${2:-0}"

    case "$VERBOSITY_LEVEL" in
        quiet)
            printf "%s... " "$operation"
            ;;
        default)
            if [ "$duration" -gt 0 ]; then
                log_message "🔨 $operation... (estimated ${duration}s)" "INFO" true
            else
                log_message "🔨 $operation..." "INFO" true
            fi
            ;;
        verbose)
            log_message "🔨 Starting $operation..." "INFO" true
            ;;
    esac
}

# Set up enhanced logging if possible
setup_enhanced_logging

# Module loaded (silent)