#!/usr/bin/env bash
#
# Mailpit Lifecycle Manager - OS-aware mailpit start/stop handling
#
# This script handles platform-specific issues with mailpit, particularly
# the WSL2 port binding issue with wslrelay.exe holding ports after container stops.
#

set -euo pipefail

# Source platform helper for OS detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ANSI color codes (check if already defined by platform_helper)
if [[ -z "${RED:-}" ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m' # No Color
fi

source "${SCRIPT_DIR}/platform_helper.sh" 2>/dev/null || true

# Mailpit default ports
readonly MAILPIT_SMTP_PORT=1025
readonly MAILPIT_WEB_PORT=8025
readonly MAILPIT_CONTAINER_NAME="${MAILPIT_CONTAINER_NAME:-sting-ce-mailpit}"

# Logging functions
log_info() {
    echo -e "${BLUE}[MAILPIT]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[MAILPIT]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[MAILPIT]${NC} $*"
}

log_error() {
    echo -e "${RED}[MAILPIT]${NC} $*"
}

#
# Check if port is in use
#
is_port_in_use() {
    local port="$1"

    # Try different methods based on available commands
    if command -v lsof &> /dev/null; then
        lsof -i :"$port" &> /dev/null
        return $?
    elif command -v ss &> /dev/null; then
        ss -tlnp | grep -q ":${port}"
        return $?
    elif command -v netstat &> /dev/null; then
        netstat -tlnp 2>/dev/null | grep -q ":${port}"
        return $?
    else
        # Fallback - assume port is available
        return 1
    fi
}

#
# Get process ID using a port (Linux/WSL)
#
get_port_pid() {
    local port="$1"

    if command -v lsof &> /dev/null; then
        lsof -ti :"$port" 2>/dev/null || echo ""
    elif command -v ss &> /dev/null; then
        ss -tlnp | grep ":${port}" | grep -oP 'pid=\K[0-9]+' | head -1 || echo ""
    else
        echo ""
    fi
}

#
# Kill Windows wslrelay process holding a port (WSL2 specific)
#
kill_wsl_relay_port() {
    local port="$1"

    log_info "Checking for Windows wslrelay processes on port $port..."

    # Use PowerShell to find and kill wslrelay holding the port
    if command -v powershell.exe &> /dev/null; then
        local wsl_pids
        wsl_pids=$(powershell.exe -Command "Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess" 2>/dev/null || echo "")

        if [[ -n "$wsl_pids" ]]; then
            log_info "Found Windows process(es) using port $port: $wsl_pids"

            # Get process name to verify it's wslrelay
            local process_name
            process_name=$(powershell.exe -Command "Get-Process -Id $wsl_pids -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName" 2>/dev/null || echo "")

            if [[ "$process_name" == *"wslrelay"* ]]; then
                log_warning "Killing wslrelay.exe process $wsl_pids on port $port..."
                powershell.exe -Command "Stop-Process -Id $wsl_pids -Force" 2>/dev/null || true
                sleep 1
                log_success "Killed wslrelay process"
                return 0
            else
                log_warning "Port $port is held by '$process_name' (not wslrelay) - manual intervention may be needed"
                return 1
            fi
        else
            log_info "No Windows processes found on port $port"
        fi
    fi

    return 0
}

#
# Clean up Linux/WSL zombie processes on mailpit ports
#
cleanup_zombie_processes() {
    log_info "Checking for zombie processes on mailpit ports..."

    local cleaned=0

    for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
        if is_port_in_use "$port"; then
            log_warning "Port $port is in use"

            local pid
            pid=$(get_port_pid "$port")

            if [[ -n "$pid" ]]; then
                # Check if it's a docker-proxy process
                local process_name
                process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")

                if [[ "$process_name" == "docker-proxy" ]] || [[ "$process_name" == "mailpit" ]]; then
                    log_warning "Found zombie $process_name (PID: $pid) on port $port - killing..."
                    sudo kill -9 "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
                    sleep 1
                    ((cleaned++))
                else
                    log_warning "Port $port held by '$process_name' (PID: $pid) - not a known mailpit process"
                fi
            fi
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        log_success "Cleaned up $cleaned zombie process(es)"
    else
        log_info "No zombie processes found"
    fi
}

#
# WSL2-specific pre-start cleanup
#
wsl2_pre_start_cleanup() {
    log_info "Running WSL2-specific pre-start cleanup..."

    # Step 1: Clean up zombie Linux processes
    cleanup_zombie_processes

    # Step 2: Clean up Windows wslrelay processes
    for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
        if is_port_in_use "$port"; then
            kill_wsl_relay_port "$port"
        fi
    done

    # Step 3: Verify ports are clear
    local ports_clear=true
    for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
        if is_port_in_use "$port"; then
            log_error "Port $port still in use after cleanup!"
            ports_clear=false
        fi
    done

    if $ports_clear; then
        log_success "All mailpit ports are clear"
        return 0
    else
        log_error "Some ports are still in use - manual intervention required"
        log_info "Try: wsl --shutdown (from Windows) or restart Docker"
        return 1
    fi
}

#
# Pre-start hook - cleanup before starting mailpit
#
pre_start() {
    local platform
    platform=$(detect_platform 2>/dev/null || echo "unknown")

    log_info "Pre-start cleanup (Platform: $platform)..."

    case "$platform" in
        wsl2)
            wsl2_pre_start_cleanup
            return $?
            ;;
        linux|macos)
            # On native Linux/macOS, just clean up any zombie processes
            cleanup_zombie_processes
            return $?
            ;;
        *)
            log_warning "Unknown platform '$platform' - skipping cleanup"
            return 0
            ;;
    esac
}

#
# Post-stop hook - cleanup after stopping mailpit
#
post_stop() {
    local platform
    platform=$(detect_platform 2>/dev/null || echo "unknown")

    log_info "Post-stop cleanup (Platform: $platform)..."

    # Wait a moment for Docker to cleanup
    sleep 2

    case "$platform" in
        wsl2)
            # WSL2: aggressively clean up wslrelay
            log_info "Cleaning up Windows wslrelay processes..."
            for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
                kill_wsl_relay_port "$port" 2>/dev/null || true
            done
            ;;
        linux|macos)
            # Native platforms: check for lingering processes
            cleanup_zombie_processes
            ;;
        *)
            log_info "No post-stop cleanup needed for platform: $platform"
            ;;
    esac

    log_success "Post-stop cleanup complete"
}

#
# Check mailpit health
#
check_health() {
    log_info "Checking mailpit health..."

    if docker ps --filter "name=${MAILPIT_CONTAINER_NAME}" --filter "status=running" | grep -q "$MAILPIT_CONTAINER_NAME"; then
        log_success "Mailpit container is running"

        # Check if ports are responding
        if nc -z localhost $MAILPIT_SMTP_PORT 2>/dev/null; then
            log_success "SMTP port $MAILPIT_SMTP_PORT is responding"
        else
            log_warning "SMTP port $MAILPIT_SMTP_PORT is not responding"
        fi

        if nc -z localhost $MAILPIT_WEB_PORT 2>/dev/null; then
            log_success "Web UI port $MAILPIT_WEB_PORT is responding"
        else
            log_warning "Web UI port $MAILPIT_WEB_PORT is not responding"
        fi

        return 0
    else
        log_error "Mailpit container is not running"
        return 1
    fi
}

#
# Force restart mailpit with cleanup
#
force_restart() {
    log_info "Force restarting mailpit..."

    # Stop if running
    if docker ps -a --filter "name=${MAILPIT_CONTAINER_NAME}" | grep -q "$MAILPIT_CONTAINER_NAME"; then
        log_info "Stopping existing mailpit container..."
        docker stop "$MAILPIT_CONTAINER_NAME" 2>/dev/null || true
        docker rm "$MAILPIT_CONTAINER_NAME" 2>/dev/null || true
    fi

    # Run post-stop cleanup
    post_stop

    # Run pre-start cleanup
    if ! pre_start; then
        log_error "Pre-start cleanup failed - cannot restart mailpit"
        return 1
    fi

    # Start mailpit
    log_info "Starting mailpit container..."

    # Determine INSTALL_DIR
    local install_dir="${INSTALL_DIR:-$(pwd)}"

    cd "$install_dir" || return 1

    if INSTALL_DIR="$install_dir" docker compose up -d mailpit 2>&1; then
        log_success "Mailpit started successfully"
        sleep 3
        check_health
        return $?
    else
        log_error "Failed to start mailpit"
        return 1
    fi
}

#
# Display port status
#
port_status() {
    log_info "Mailpit port status:"
    echo ""

    for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
        if is_port_in_use "$port"; then
            local pid
            pid=$(get_port_pid "$port")

            local process_name=""
            if [[ -n "$pid" ]]; then
                process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            fi

            echo "  Port $port: ${RED}IN USE${NC} (PID: $pid, Process: $process_name)"
        else
            echo "  Port $port: ${GREEN}AVAILABLE${NC}"
        fi
    done

    echo ""

    # WSL2: also check Windows side
    local platform
    platform=$(detect_platform 2>/dev/null || echo "unknown")

    if [[ "$platform" == "wsl2" ]] && command -v powershell.exe &> /dev/null; then
        log_info "Windows port status (via wslrelay):"
        echo ""

        for port in $MAILPIT_SMTP_PORT $MAILPIT_WEB_PORT; do
            local wsl_pids
            wsl_pids=$(powershell.exe -Command "Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess" 2>/dev/null | tr -d '\r' || echo "")

            if [[ -n "$wsl_pids" ]]; then
                local process_name
                process_name=$(powershell.exe -Command "Get-Process -Id $wsl_pids -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName" 2>/dev/null | tr -d '\r' || echo "unknown")
                echo "  Port $port: ${RED}HELD BY WINDOWS${NC} (PID: $wsl_pids, Process: $process_name)"
            else
                echo "  Port $port: ${GREEN}FREE ON WINDOWS${NC}"
            fi
        done

        echo ""
    fi
}

#
# Main command handler
#
main() {
    local command="${1:-help}"

    case "$command" in
        pre-start)
            pre_start
            ;;
        post-stop)
            post_stop
            ;;
        health|check)
            check_health
            ;;
        restart|force-restart)
            force_restart
            ;;
        status|ports)
            port_status
            ;;
        cleanup)
            cleanup_zombie_processes
            ;;
        help|--help|-h)
            cat <<EOF
Usage: $0 <command>

Mailpit Lifecycle Manager - OS-aware mailpit management

Commands:
  pre-start       Run pre-start cleanup (clean zombie processes/ports)
  post-stop       Run post-stop cleanup (release held ports)
  health|check    Check mailpit container health
  restart         Force restart mailpit with full cleanup
  status|ports    Show current port usage status
  cleanup         Clean up zombie processes on mailpit ports
  help            Show this help message

Environment Variables:
  MAILPIT_CONTAINER_NAME    Name of mailpit container (default: sting-ce-mailpit)

Examples:
  # Clean up before starting mailpit
  $0 pre-start && docker compose up -d mailpit

  # Check mailpit health
  $0 health

  # Check port status
  $0 status

  # Force restart with cleanup
  $0 restart

Platform-Specific Notes:
  WSL2: Automatically handles wslrelay.exe port binding issues
  Linux/macOS: Cleans up zombie docker-proxy processes

EOF
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Run '$0 help' for usage"
            exit 1
            ;;
    esac
}

# Run main if executed (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
