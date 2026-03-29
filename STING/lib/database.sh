#!/bin/bash
# database.sh — Database management utilities for STING-CE
# Provides migration tracking, application, and status reporting.

# ============================================================================
# Migration Tracking
# ============================================================================

MIGRATION_DB="sting_app"
MIGRATION_USER="postgres"
MIGRATION_CONTAINER="sting-ce-db"

# Ensure the schema_migrations tracking table exists
ensure_migration_tracking() {
    docker exec -i "$MIGRATION_CONTAINER" psql -U "$MIGRATION_USER" -d "$MIGRATION_DB" -q <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    checksum VARCHAR(64)
);
SQL
}

# Check if a migration has already been applied successfully
is_migration_applied() {
    local version="$1"
    local result
    result=$(docker exec "$MIGRATION_CONTAINER" psql -U "$MIGRATION_USER" -d "$MIGRATION_DB" -tAc \
        "SELECT COUNT(*) FROM schema_migrations WHERE version = '$version' AND success = true;" 2>/dev/null)
    [ "$result" = "1" ]
}

# Record a migration as applied
record_migration() {
    local version="$1"
    local filename="$2"
    local success="$3"
    local checksum="$4"
    
    docker exec -i "$MIGRATION_CONTAINER" psql -U "$MIGRATION_USER" -d "$MIGRATION_DB" -q <<SQL
INSERT INTO schema_migrations (version, filename, applied_at, success, checksum)
VALUES ('$version', '$filename', NOW(), $success, '$checksum')
ON CONFLICT (version) DO UPDATE SET
    applied_at = NOW(),
    success = $success,
    checksum = '$checksum';
SQL
}

# Compute checksum for a migration file
migration_checksum() {
    local file="$1"
    sha256sum "$file" 2>/dev/null | cut -d' ' -f1
}

# ============================================================================
# Migration Application
# ============================================================================

# Apply a single SQL migration file
apply_single_sql_migration() {
    local migration_file="$1"
    local output
    
    output=$(docker exec -i "$MIGRATION_CONTAINER" psql -U "$MIGRATION_USER" -d "$MIGRATION_DB" < "$migration_file" 2>&1)
    local rc=$?
    
    # Filter errors: "already exists" / "does not exist, skipping" are benign in idempotent migrations
    local real_errors
    real_errors=$(echo "$output" | grep -i "^ERROR:" | grep -viE "already exists|does not exist, skipping|duplicate key value" || true)
    
    if [ $rc -ne 0 ] && [ -n "$real_errors" ]; then
        echo "$output"
        return 1
    fi
    
    # Show notices (useful feedback from IF NOT EXISTS patterns)
    if echo "$output" | grep -qi "NOTICE:"; then
        echo "$output" | grep -i "NOTICE:" | sed 's/^/    /'
    fi
    
    # Warn about benign errors but don't fail
    local benign_errors
    benign_errors=$(echo "$output" | grep -i "^ERROR:" | grep -iE "already exists|does not exist, skipping|duplicate key value" || true)
    if [ -n "$benign_errors" ]; then
        local count
        count=$(echo "$benign_errors" | wc -l)
        echo "    ℹ️  $count pre-existing object(s) skipped"
    fi
    
    # Check for real errors even on rc=0 (psql can return 0 with errors in multi-statement files)
    if [ -n "$real_errors" ]; then
        echo "$output"
        return 1
    fi
    
    return 0
}

# Apply a single shell migration
apply_single_sh_migration() {
    local migration_file="$1"
    bash "$migration_file" 2>&1
    return $?
}

# Apply a single Python migration
apply_single_py_migration() {
    local migration_file="$1"
    local temp_migration="/tmp/$(basename "$migration_file")"
    
    if docker cp "$migration_file" "$MIGRATION_CONTAINER:$temp_migration" >/dev/null 2>&1; then
        local output
        output=$(docker exec "$MIGRATION_CONTAINER" python3 "$temp_migration" 2>&1)
        local rc=$?
        docker exec "$MIGRATION_CONTAINER" rm -f "$temp_migration" >/dev/null 2>&1 || true
        [ $rc -ne 0 ] && echo "$output"
        return $rc
    else
        echo "Failed to copy migration file to container"
        return 1
    fi
}

# ============================================================================
# Main Commands
# ============================================================================

# Run all pending database migrations
run_database_migrations() {
    local force_all=false
    local dry_run=false
    local force_version=""
    
    # Parse flags
    while [ $# -gt 0 ]; do
        case "$1" in
            --all)      force_all=true ;;
            --dry-run)  dry_run=true ;;
            --force)    shift; force_version="$1" ;;
            *)          break ;;
        esac
        shift
    done
    
    local migrations_dir="${INSTALL_DIR:-${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}/database/migrations"
    
    if [ ! -d "$migrations_dir" ]; then
        log_message "No migrations directory found at $migrations_dir" "ERROR"
        return 1
    fi
    
    # Ensure db container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${MIGRATION_CONTAINER}$"; then
        log_message "Database container is not running. Start services first: msting start db" "ERROR"
        return 1
    fi
    
    # Ensure tracking table exists
    ensure_migration_tracking
    
    # Collect migration files sorted by version number
    local migration_files=()
    while IFS= read -r file; do
        migration_files+=("$file")
    done < <(find "$migrations_dir" -maxdepth 1 \( -name "*.sql" -o -name "*.sh" -o -name "*.py" \) | sort -t'/' -k$(echo "$migrations_dir" | tr -cd '/' | wc -c | xargs -I{} expr {} + 2) -V)
    
    if [ ${#migration_files[@]} -eq 0 ]; then
        log_message "No migration files found" "WARNING"
        return 0
    fi
    
    log_message "Found ${#migration_files[@]} migration file(s) in $migrations_dir"
    
    local applied_count=0
    local skipped_count=0
    local failed_count=0
    
    for migration_file in "${migration_files[@]}"; do
        local filename
        filename=$(basename "$migration_file")
        local version
        version=$(echo "$filename" | grep -oP '^\d+' || echo "$filename")
        local checksum
        checksum=$(migration_checksum "$migration_file")
        
        # Check if this specific version was requested with --force
        if [ -n "$force_version" ] && [ "$version" != "$force_version" ] && [ "$filename" != "$force_version" ]; then
            continue
        fi
        
        # Skip already-applied migrations (unless --all or --force)
        if ! $force_all && [ -z "$force_version" ] && is_migration_applied "$version"; then
            ((skipped_count++))
            if $dry_run; then
                log_message "  ✓ $filename (already applied)" "INFO"
            fi
            continue
        fi
        
        if $dry_run; then
            log_message "  ⏳ $filename (PENDING — would apply)" "INFO"
            ((applied_count++))
            continue
        fi
        
        # Apply the migration based on file type
        log_message "Applying: $filename"
        local output=""
        local rc=0
        
        case "$filename" in
            *.sql)
                output=$(apply_single_sql_migration "$migration_file")
                rc=$?
                ;;
            *.sh)
                output=$(apply_single_sh_migration "$migration_file")
                rc=$?
                ;;
            *.py)
                output=$(apply_single_py_migration "$migration_file")
                rc=$?
                ;;
        esac
        
        if [ $rc -eq 0 ]; then
            record_migration "$version" "$filename" "true" "$checksum"
            log_message "  [+] $filename" "SUCCESS"
            [ -n "$output" ] && echo "$output"
            ((applied_count++))
        else
            record_migration "$version" "$filename" "false" "$checksum"
            log_message "  [-] $filename FAILED" "ERROR"
            [ -n "$output" ] && echo "$output"
            ((failed_count++))
        fi
    done
    
    echo ""
    if $dry_run; then
        log_message "Dry run complete: $applied_count pending, $skipped_count already applied"
    else
        log_message "Migration summary: $applied_count applied, $skipped_count skipped, $failed_count failed"
    fi
    
    [ $failed_count -gt 0 ] && return 1
    return 0
}

# Show migration status
show_migration_status() {
    local migrations_dir="${INSTALL_DIR:-${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}/database/migrations"
    
    # Ensure db container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${MIGRATION_CONTAINER}$"; then
        log_message "Database container is not running" "ERROR"
        return 1
    fi
    
    ensure_migration_tracking
    
    echo ""
    echo "  Database Migration Status"
    echo "  ════════════════════════════════════════════════════════════════"
    
    # Collect migration files
    local migration_files=()
    if [ -d "$migrations_dir" ]; then
        while IFS= read -r file; do
            migration_files+=("$file")
        done < <(find "$migrations_dir" -maxdepth 1 \( -name "*.sql" -o -name "*.sh" -o -name "*.py" \) | sort -t'/' -k$(echo "$migrations_dir" | tr -cd '/' | wc -c | xargs -I{} expr {} + 2) -V)
    fi
    
    local pending=0
    local applied=0
    local failed=0
    
    for migration_file in "${migration_files[@]}"; do
        local filename
        filename=$(basename "$migration_file")
        local version
        version=$(echo "$filename" | grep -oP '^\d+' || echo "$filename")
        
        # Check tracking table
        local status_row
        status_row=$(docker exec "$MIGRATION_CONTAINER" psql -U "$MIGRATION_USER" -d "$MIGRATION_DB" -tAc \
            "SELECT success, to_char(applied_at, 'YYYY-MM-DD HH24:MI') FROM schema_migrations WHERE version = '$version';" 2>/dev/null)
        
        if [ -n "$status_row" ]; then
            local success
            success=$(echo "$status_row" | cut -d'|' -f1)
            local applied_at
            applied_at=$(echo "$status_row" | cut -d'|' -f2)
            if [ "$success" = "t" ]; then
                echo "  ✅ $filename  (applied $applied_at)"
                ((applied++))
            else
                echo "  ❌ $filename  (FAILED $applied_at)"
                ((failed++))
            fi
        else
            echo "  ⏳ $filename  (pending)"
            ((pending++))
        fi
    done
    
    echo "  ════════════════════════════════════════════════════════════════"
    echo "  Total: ${#migration_files[@]}  |  Applied: $applied  |  Pending: $pending  |  Failed: $failed"
    echo ""
    
    return 0
}
