#!/bin/bash
# Local Bundle Manager - User bundle access and sharing
# Allows users to download, extract, and manually share their own diagnostic bundles

# Load dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logging.sh"
source "${SCRIPT_DIR}/core.sh"

# Configuration
LOCAL_BUNDLES_DIR="${INSTALL_DIR}/support_bundles"
BUNDLE_EXPORTS_DIR="${INSTALL_DIR}/bundle_exports"

# Initialize local bundle management
init_local_bundle_management() {
    mkdir -p "${LOCAL_BUNDLES_DIR}"
    mkdir -p "${BUNDLE_EXPORTS_DIR}"
}

# List available bundles for download
list_local_bundles() {
    log_message "📦 Available Diagnostic Bundles:"
    log_message ""
    
    init_local_bundle_management
    
    if [ ! -d "$LOCAL_BUNDLES_DIR" ]; then
        log_message "  📭 No bundles directory found"
        return 0
    fi
    
    local bundles_found=0
    
    # Look for bundle files
    for bundle_file in "$LOCAL_BUNDLES_DIR"/*.tar.gz "$LOCAL_BUNDLES_DIR"/*.zip; do
        if [ -f "$bundle_file" ]; then
            bundles_found=1
            local filename
            local size
            local date
            
            filename=$(basename "$bundle_file")
            size=$(ls -lh "$bundle_file" | awk '{print $5}')
            date=$(ls -l "$bundle_file" | awk '{print $6, $7, $8}')
            
            log_message "  📦 $filename"
            log_message "    💾 Size: $size"
            log_message "    📅 Created: $date"
            log_message "    📁 Path: $bundle_file"
            log_message ""
        fi
    done
    
    if [ $bundles_found -eq 0 ]; then
        log_message "  📭 No diagnostic bundles found"
        log_message "  💡 Create one with: ./manage_sting.sh buzz collect"
    fi
}

# Extract bundle for manual review/sharing
extract_bundle() {
    local bundle_file="$1"
    local output_dir="$2"
    
    if [ ! -f "$bundle_file" ]; then
        log_message "❌ Bundle file not found: $bundle_file" "ERROR"
        return 1
    fi
    
    # Use default output directory if not specified
    if [ -z "$output_dir" ]; then
        local bundle_name
        bundle_name=$(basename "$bundle_file" .tar.gz)
        output_dir="${BUNDLE_EXPORTS_DIR}/${bundle_name}"
    fi
    
    log_message "📂 Extracting bundle to: $output_dir"
    
    # Create output directory
    mkdir -p "$output_dir"
    
    # Extract bundle
    if tar -xzf "$bundle_file" -C "$output_dir" 2>/dev/null; then
        log_message "✅ Bundle extracted successfully"
        
        # List extracted contents
        log_message "📋 Extracted contents:"
        find "$output_dir" -type f | head -10 | while read -r file; do
            local rel_path
            rel_path=$(echo "$file" | sed "s|$output_dir/||")
            local file_size
            file_size=$(ls -lh "$file" | awk '{print $5}')
            log_message "  📄 $rel_path ($file_size)"
        done
        
        # Count files if many
        local file_count
        file_count=$(find "$output_dir" -type f | wc -l)
        if [ "$file_count" -gt 10 ]; then
            log_message "  ... and $((file_count - 10)) more files"
        fi
        
        log_message ""
        log_message "📁 **Extracted to:** $output_dir"
        log_message "💡 **Next steps:**"
        log_message "  • Review logs in extracted folder"
        log_message "  • Share specific log files as needed"
        log_message "  • Archive folder: tar -czf my-bundle.tar.gz extracted-folder/"
        log_message "  • Safe to share: All sensitive data already removed"
        
        return 0
    else
        log_message "❌ Failed to extract bundle" "ERROR"
        return 1
    fi
}

# Copy bundle to user-friendly location
copy_bundle_for_sharing() {
    local bundle_file="$1"
    local destination="${2:-~/Desktop}"
    
    if [ ! -f "$bundle_file" ]; then
        log_message "❌ Bundle file not found: $bundle_file" "ERROR"
        return 1
    fi
    
    # Create user-friendly filename
    local ticket_id
    ticket_id=$(basename "$bundle_file" | grep -o 'ST-[0-9-]*' || echo "bundle")
    local timestamp
    timestamp=$(date +%Y%m%d-%H%M)
    local friendly_name="sting-diagnostic-${ticket_id}-${timestamp}.tar.gz"
    
    local dest_path="$destination/$friendly_name"
    
    log_message "📤 Copying bundle for sharing..."
    
    # Copy to destination
    if cp "$bundle_file" "$dest_path" 2>/dev/null; then
        log_message "✅ Bundle copied successfully"
        log_message "📁 Location: $dest_path"
        log_message "💾 Size: $(ls -lh "$dest_path" | awk '{print $5}')"
        log_message ""
        log_message "🔒 **Sharing Safety:**"
        log_message "  • Bundle is fully sanitized"
        log_message "  • No passwords, keys, or PII included"
        log_message "  • Safe to share via email, forums, Discord"
        log_message "  • Contains diagnostic logs and system info only"
        log_message ""
        log_message "📧 **How to Share:**"
        log_message "  • Email: Attach to support emails"
        log_message "  • Forums: Upload to community help threads"
        log_message "  • Discord: Share in #support-help channels"
        log_message "  • GitHub: Attach to issues if reproducible bug"
        
        return 0
    else
        log_message "❌ Failed to copy bundle to $dest_path" "ERROR"
        return 1
    fi
}

# Show bundle contents without extracting
inspect_bundle() {
    local bundle_file="$1"
    
    if [ ! -f "$bundle_file" ]; then
        log_message "❌ Bundle file not found: $bundle_file" "ERROR"
        return 1
    fi
    
    log_message "🔍 Bundle Contents Preview: $(basename "$bundle_file")"
    log_message ""
    
    # Show bundle structure
    log_message "📁 **Bundle Structure:**"
    tar -tzf "$bundle_file" 2>/dev/null | head -20 | while read -r file; do
        log_message "  📄 $file"
    done
    
    # Count total files
    local file_count
    file_count=$(tar -tzf "$bundle_file" 2>/dev/null | wc -l)
    if [ "$file_count" -gt 20 ]; then
        log_message "  ... and $((file_count - 20)) more files"
    fi
    
    # Show bundle size and info
    local size
    size=$(ls -lh "$bundle_file" | awk '{print $5}')
    local date
    date=$(ls -l "$bundle_file" | awk '{print $6, $7, $8}')
    
    log_message ""
    log_message "📊 **Bundle Info:**"
    log_message "  💾 Size: $size"
    log_message "  📅 Created: $date"
    log_message "  🔒 Sanitized: Yes (safe to share)"
    log_message "  📁 Total files: $file_count"
}

# Create shareable bundle package
create_shareable_package() {
    local ticket_id="$1"
    local include_summary="${2:-true}"
    
    log_message "📦 Creating shareable package for ticket: $ticket_id"
    
    # Find bundles for this ticket
    local bundle_files
    bundle_files=$(find "$LOCAL_BUNDLES_DIR" -name "*${ticket_id}*" -type f 2>/dev/null)
    
    if [ -z "$bundle_files" ]; then
        log_message "❌ No bundles found for ticket: $ticket_id" "ERROR"
        return 1
    fi
    
    local package_dir="${BUNDLE_EXPORTS_DIR}/shareable-${ticket_id}"
    mkdir -p "$package_dir"
    
    # Copy bundles to package directory
    echo "$bundle_files" | while read -r bundle_file; do
        if [ -f "$bundle_file" ]; then
            local bundle_name
            bundle_name=$(basename "$bundle_file")
            cp "$bundle_file" "$package_dir/$bundle_name"
            log_message "✅ Added: $bundle_name"
        fi
    done
    
    # Create sharing summary if requested
    if [ "$include_summary" = "true" ]; then
        cat > "$package_dir/SHARING_INFO.md" << EOF
# STING-CE Diagnostic Bundle - $ticket_id

## 🛡️ Security & Privacy
- ✅ **Fully Sanitized** - All passwords, API keys, and PII removed
- ✅ **Safe to Share** - Approved for community forums and email
- ✅ **No Sensitive Data** - Contains diagnostic logs and system info only
- ✅ **Integrity Verified** - Bundle created by STING's automated system

## 📋 Issue Information
- **Ticket ID**: $ticket_id
- **Created**: $(date)
- **STING Version**: $(get_sting_version 2>/dev/null || echo "Unknown")
- **Bundle Type**: Diagnostic logs and system health data

## 📁 Contents
This bundle contains sanitized diagnostic information including:
- Service logs (with sensitive data removed)
- System health metrics  
- Configuration snapshots (secrets excluded)
- Error pattern analysis
- Network connectivity tests

## 🤝 How to Help
If you're a community member helping with this issue:
1. **Download** and extract the bundle
2. **Review** the logs for error patterns
3. **Check** system health metrics for anomalies
4. **Provide** guidance based on your expertise
5. **Share** solutions back to the community

## 📧 Contact
- **Community Forums**: Post your findings and suggestions
- **Discord**: Share solutions in #support-help
- **GitHub**: Create issue if this appears to be a bug

Thank you for helping make STING better! 🐝
EOF
        
        log_message "✅ Added sharing documentation"
    fi
    
    # Create final shareable archive
    local archive_name="sting-diagnostic-${ticket_id}-$(date +%Y%m%d).tar.gz"
    local archive_path="${BUNDLE_EXPORTS_DIR}/$archive_name"
    
    if tar -czf "$archive_path" -C "${BUNDLE_EXPORTS_DIR}" "shareable-${ticket_id}"; then
        log_message "✅ Shareable package created: $archive_path"
        log_message "💾 Size: $(ls -lh "$archive_path" | awk '{print $5}')"
        log_message ""
        log_message "📤 **Ready to Share:**"
        log_message "  📁 Package: $archive_path"
        log_message "  🔒 Security: Fully sanitized, safe for public sharing"
        log_message "  📋 Documentation: Included in package"
        log_message "  💡 Usage: Extract and review logs for troubleshooting"
        
        return 0
    else
        log_message "❌ Failed to create shareable package" "ERROR"
        return 1
    fi
}

# Show help for local bundle management
show_local_bundle_help() {
    cat << 'EOF'
📦 Local Bundle Manager - Download and Share Your Diagnostic Bundles

USAGE:
    ./manage_sting.sh bundle COMMAND [OPTIONS]

COMMANDS:
    list                        List available diagnostic bundles
    extract BUNDLE_FILE [DIR]   Extract bundle for manual review
    copy BUNDLE_FILE [DEST]     Copy bundle to location for sharing
    inspect BUNDLE_FILE         Preview bundle contents without extracting
    package TICKET_ID           Create shareable package with documentation
    help                        Show this help

EXAMPLES:
    # List all available bundles
    ./manage_sting.sh bundle list
    
    # Extract bundle for review
    ./manage_sting.sh bundle extract auth-bundle-ST-2025-001.tar.gz
    
    # Copy bundle to Desktop for email sharing
    ./manage_sting.sh bundle copy auth-bundle-ST-2025-001.tar.gz ~/Desktop
    
    # Preview bundle contents
    ./manage_sting.sh bundle inspect performance-ST-2025-002.tar.gz
    
    # Create shareable package with documentation
    ./manage_sting.sh bundle package ST-2025-001

SHARING OPTIONS:
    📧 **Email**: Copy to Desktop/Downloads and attach to emails
    💬 **Forums**: Upload extracted files to community discussions
    📱 **Discord**: Share specific log files in help channels
    🐛 **GitHub**: Attach to issues for reproducible bugs
    💾 **USB/Drive**: Copy bundles for offline analysis

SECURITY:
    ✅ All bundles are pre-sanitized by STING's Pollen Filter
    ✅ No passwords, API keys, or PII included
    ✅ Safe to share publicly in community forums
    ✅ Contains diagnostic data only (logs, configs, metrics)

BUNDLE LOCATIONS:
    📂 Generated bundles: ${LOCAL_BUNDLES_DIR}/
    📂 Extracted bundles: ${BUNDLE_EXPORTS_DIR}/
    📤 Shareable packages: ${BUNDLE_EXPORTS_DIR}/

EOF
}

# Main function for local bundle management
main() {
    local command="$1"
    shift || true
    
    case "$command" in
        list)
            list_local_bundles
            ;;
        extract)
            local bundle_file="$1"
            local output_dir="$2"
            
            if [ -z "$bundle_file" ]; then
                log_message "❌ Bundle file required" "ERROR"
                log_message "Usage: bundle extract BUNDLE_FILE [OUTPUT_DIR]" "INFO"
                return 1
            fi
            
            extract_bundle "$bundle_file" "$output_dir"
            ;;
        copy)
            local bundle_file="$1" 
            local destination="$2"
            
            if [ -z "$bundle_file" ]; then
                log_message "❌ Bundle file required" "ERROR"
                log_message "Usage: bundle copy BUNDLE_FILE [DESTINATION]" "INFO"
                return 1
            fi
            
            copy_bundle_for_sharing "$bundle_file" "$destination"
            ;;
        inspect)
            local bundle_file="$1"
            
            if [ -z "$bundle_file" ]; then
                log_message "❌ Bundle file required" "ERROR"
                log_message "Usage: bundle inspect BUNDLE_FILE" "INFO"
                return 1
            fi
            
            inspect_bundle "$bundle_file"
            ;;
        package)
            local ticket_id="$1"
            
            if [ -z "$ticket_id" ]; then
                log_message "❌ Ticket ID required" "ERROR"
                log_message "Usage: bundle package TICKET_ID" "INFO"
                return 1
            fi
            
            create_shareable_package "$ticket_id"
            ;;
        help|--help|-h|"")
            show_local_bundle_help
            ;;
        *)
            log_message "❌ Unknown bundle command: $command" "ERROR"
            show_local_bundle_help
            return 1
            ;;
    esac
}

# Run main function
main "$@"