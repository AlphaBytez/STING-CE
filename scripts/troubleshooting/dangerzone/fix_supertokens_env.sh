#!/bin/bash

# Script to permanently fix deprecated supertokens.env file issues
# This script:
# 1. Removes the supertokens.env file
# 2. Prevents it from being recreated by modifying config_loader.py
# 3. Adds a simple safeguard to ensure future updates don't reintroduce the issue

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting SuperTokens Environment Fix${NC}"

# Determine home directory and configuration paths
HOME_DIR="$HOME"
STING_ENV_DIR="$HOME_DIR/.sting-ce/env"
STING_CONF_DIR="$HOME_DIR/.sting-ce/conf"
SUPERTOKENS_ENV_FILE="$STING_ENV_DIR/supertokens.env"

# Project root directory detection
PROJECT_ROOT=""
for dir in \
  "/Users/captain-wolf/Documents/GitHub/STING-CE/STING" \
  "${HOME_DIR}/STING-CE/STING" \
  "${HOME_DIR}/STING" \
  "${HOME_DIR}/Documents/STING-CE/STING" \
  "/opt/sting"; do
  if [ -d "$dir" ]; then
    PROJECT_ROOT="$dir"
    break
  fi
done

if [ -z "$PROJECT_ROOT" ]; then
  echo -e "${RED}Could not find STING project directory. Will only remove env file but cannot update config loader.${NC}"
fi

# 1. Find and remove ALL supertokens.env files
echo -e "${YELLOW}Searching for ALL supertokens.env files in the system...${NC}"

# Define potential locations
LOCATIONS=(
    "$HOME/.sting-ce/env"
    "$HOME/.sting-ce/conf"
    "/Users/captain-wolf/Documents/GitHub/STING-CE/STING/conf"
    "/Users/captain-wolf/Documents/GitHub/STING-CE/STING/env"
    "/opt/sting/conf"
    "/opt/sting/env"
    "/app/conf"
    "/app/env"
)

# Find and remove all instances
FOUND=0
for DIR in "${LOCATIONS[@]}"; do
    if [ -d "$DIR" ]; then
        ST_FILE="$DIR/supertokens.env"
        if [ -f "$ST_FILE" ]; then
            echo -e "${YELLOW}Found deprecated supertokens.env at: $ST_FILE${NC}"
            rm -f "$ST_FILE"
            echo -e "${GREEN}Successfully removed $ST_FILE${NC}"
            FOUND=1
        fi
    fi
done

if [ $FOUND -eq 0 ]; then
    echo -e "${GREEN}No supertokens.env files found in known locations.${NC}"
fi

# Use find to locate any remaining supertokens.env files in home directory
echo -e "${YELLOW}Deep scanning for any other supertokens.env files...${NC}"
FOUND_FILES=$(find $HOME -name "supertokens.env" -type f 2>/dev/null)

if [ -n "$FOUND_FILES" ]; then
    echo -e "${YELLOW}Found additional supertokens.env files:${NC}"
    echo "$FOUND_FILES"
    echo -e "${YELLOW}Removing all found files...${NC}"
    
    while IFS= read -r file; do
        rm -f "$file"
        echo -e "${GREEN}Removed: $file${NC}"
    done <<< "$FOUND_FILES"
else
    echo -e "${GREEN}No additional supertokens.env files found.${NC}"
fi

# 2. Add a guard file to prevent recreation
echo -e "${YELLOW}Creating a guard file to prevent supertokens.env from being recreated...${NC}"
touch "$STING_ENV_DIR/.no_supertokens"
echo "# This file prevents the creation of supertokens.env" > "$STING_ENV_DIR/.no_supertokens"
echo "# SuperTokens is no longer used in STING" >> "$STING_ENV_DIR/.no_supertokens"
echo "# Created: $(date)" >> "$STING_ENV_DIR/.no_supertokens"

# 3. Check for any other references to supertokens.env in config files
for conf_file in "$STING_CONF_DIR/config.yml" "$STING_CONF_DIR/config.yml.default"; do
    if [ -f "$conf_file" ]; then
        echo -e "${YELLOW}Checking $conf_file for SuperTokens references...${NC}"
        
        # Make a backup of the config file
        cp "$conf_file" "$conf_file.bak.$(date +%Y%m%d%H%M%S)"
        
        # Check if there's a supertokens section and comment it out
        if grep -q "supertokens:" "$conf_file"; then
            echo -e "${YELLOW}Found SuperTokens configuration. Will comment it out.${NC}"
            
            # Create a temporary file with the SuperTokens section commented out
            awk '
            BEGIN { in_supertokens = 0 }
            /^[[:space:]]*security:/ { security_found = 1 }
            /^[[:space:]]*supertokens:/ && security_found { 
                in_supertokens = 1;
                print "  # DEPRECATED - supertokens is no longer used";
                print "  # " $0;
                next;
            }
            in_supertokens && /^[[:space:]]/ {
                print "  # " $0;
                next;
            }
            in_supertokens && !/^[[:space:]]/ {
                in_supertokens = 0;
                security_found = 0;
            }
            { print }
            ' "$conf_file" > "$conf_file.new"
            
            # Replace the original file with the modified version
            mv "$conf_file.new" "$conf_file"
            echo -e "${GREEN}Config file updated. SuperTokens configuration has been commented out.${NC}"
        else
            echo -e "${GREEN}No SuperTokens configuration found in $conf_file. No changes needed.${NC}"
        fi
    fi
done

# 4. Update the config_loader.py to permanently disable supertokens.env generation
if [ -n "$PROJECT_ROOT" ]; then
    CONFIG_LOADER="$PROJECT_ROOT/conf/config_loader.py"
    
    if [ -f "$CONFIG_LOADER" ]; then
        echo -e "${YELLOW}Updating config_loader.py to permanently disable supertokens.env generation...${NC}"
        
        # Create a backup
        cp "$CONFIG_LOADER" "$CONFIG_LOADER.bak.$(date +%Y%m%d%H%M%S)"
        
        # Add checks for .no_supertokens file and remove any supertokens.env generation
        # This is a more robust solution that adds a runtime check as well
        
        # Check if the runtime guard hasn't been added yet
        if ! grep -q "# SUPERTOKENS GUARD BEGIN" "$CONFIG_LOADER"; then
            # Find the generate_env_file method and add our guard at the start
            awk '
            /def generate_env_file\(self, env_path: Optional\[str\] = None, service_specific: bool = True\) -> None:/ {
                print $0;
                print "        # SUPERTOKENS GUARD BEGIN";
                print "        # Check for guard file that prevents supertokens.env generation";
                print "        if os.path.exists(os.path.join(self.env_dir, \".no_supertokens\")):";
                print "            # Remove supertokens.env if it exists to prevent errors";
                print "            st_env_file = os.path.join(self.env_dir, \"supertokens.env\")";
                print "            if os.path.exists(st_env_file):";
                print "                try:";
                print "                    os.remove(st_env_file)";
                print "                    logger.info(\"Removed deprecated supertokens.env file\")";
                print "                except Exception as e:";
                print "                    logger.warning(f\"Failed to remove supertokens.env: {e}\")";
                print "        # SUPERTOKENS GUARD END";
                next;
            }
            { print }
            ' "$CONFIG_LOADER" > "$CONFIG_LOADER.new"
            
            mv "$CONFIG_LOADER.new" "$CONFIG_LOADER"
        fi
        
        # Also update the service_configs dictionary to remove the supertokens.env entry
        # We've already done this, but making sure it's really gone
        sed -i'.tmp' -e "s/'supertokens.env'.*:.*{.*}/# 'supertokens.env': {} # Removed permanently/g" "$CONFIG_LOADER"
        rm -f "$CONFIG_LOADER.tmp"
        
        echo -e "${GREEN}Config loader updated to permanently disable supertokens.env generation.${NC}"
    else
        echo -e "${RED}Could not find config_loader.py at $CONFIG_LOADER${NC}"
    fi
else
    echo -e "${YELLOW}Project root not found. Cannot update config_loader.py directly.${NC}"
fi

echo -e "${GREEN}Fix complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Restart your services: ./manage_sting.sh restart"
echo -e "2. Try running 'msting update frontend' again"
echo -e "3. You should no longer see any errors related to supertokens.env"

echo -e "\n${GREEN}The supertokens.env file has been removed and will no longer be created.${NC}"