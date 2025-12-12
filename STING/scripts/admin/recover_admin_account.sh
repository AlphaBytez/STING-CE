#!/bin/bash

# STING Admin Account Recovery Script
# Fixes common admin account issues

echo " STING Admin Account Recovery"
echo "==============================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

KRATOS_ADMIN_URL="https://localhost:8443"
ADMIN_EMAIL="admin@sting.local"

# Function to show usage
show_usage() {
    echo "Usage: $0 [action-number]"
    echo
    echo "Available actions:"
    echo "1. Clear force_password_change flags"
    echo "2. Create missing UserSettings record"
    echo "3. Reset admin password"
    echo "4. Create new admin identity"
    echo "5. Clear all admin sessions"
    echo "6. Full admin reset (nuclear option)"
    echo
    echo "Run without arguments to see diagnostic info first"
}

# Function to get admin identity
get_admin_identity() {
    curl -s -k -X GET "$KRATOS_ADMIN_URL/admin/identities" -H "Accept: application/json" 2>/dev/null | jq -r ".[] | select(.traits.email==\"$ADMIN_EMAIL\")"
}

# Function to clear force_password_change flags
clear_force_password_change() {
    echo -e "${BLUE} Clearing force_password_change flags...${NC}"
    
    # Get admin identity
    ADMIN_IDENTITY=$(get_admin_identity)
    if [ -z "$ADMIN_IDENTITY" ] || [ "$ADMIN_IDENTITY" = "null" ]; then
        echo -e "${RED}[-] Admin identity not found${NC}"
        return 1
    fi
    
    ADMIN_ID=$(echo "$ADMIN_IDENTITY" | jq -r '.id')
    echo "   Admin ID: $ADMIN_ID"
    
    # Clear Kratos traits
    CURRENT_TRAITS=$(echo "$ADMIN_IDENTITY" | jq '.traits')
    UPDATED_TRAITS=$(echo "$CURRENT_TRAITS" | jq 'del(.force_password_change)')
    
    UPDATE_PAYLOAD=$(echo "$ADMIN_IDENTITY" | jq --argjson traits "$UPDATED_TRAITS" '.traits = $traits')
    
    echo "   Updating Kratos identity..."
    UPDATE_RESPONSE=$(curl -s -k -X PUT "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$UPDATE_PAYLOAD" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[+] Kratos traits updated${NC}"
    else
        echo -e "${RED}[-] Failed to update Kratos traits${NC}"
    fi
    
    # Clear Flask UserSettings
    echo "   Clearing Flask UserSettings..."
    FLASK_RESULT=$(docker exec sting-ce-app python -c "
from app import create_app
from app.models.user_settings import UserSettings
from app import db

app = create_app()
with app.app_context():
    admin_setting = UserSettings.query.filter_by(email='$ADMIN_EMAIL').first()
    if admin_setting:
        admin_setting.force_password_change = False
        db.session.commit()
        print('[+] UserSettings updated')
    else:
        print('[!]  No UserSettings found')
" 2>/dev/null)
    
    echo "   $FLASK_RESULT"
    echo -e "${GREEN}[+] force_password_change flags cleared${NC}"
}

# Function to create UserSettings record
create_user_settings() {
    echo -e "${BLUE} Creating UserSettings record...${NC}"
    
    FLASK_RESULT=$(docker exec sting-ce-app python -c "
from app import create_app
from app.models.user_settings import UserSettings
from app import db

app = create_app()
with app.app_context():
    existing = UserSettings.query.filter_by(email='$ADMIN_EMAIL').first()
    if existing:
        print('[!]  UserSettings already exists')
        print(f'   force_password_change: {existing.force_password_change}')
    else:
        new_settings = UserSettings(
            email='$ADMIN_EMAIL',
            role='admin',
            force_password_change=False
        )
        db.session.add(new_settings)
        db.session.commit()
        print('[+] UserSettings record created')
" 2>/dev/null)
    
    echo "   $FLASK_RESULT"
}

# Function to reset admin password
reset_admin_password() {
    echo -e "${BLUE} Resetting admin password...${NC}"
    
    # Generate new password
    NEW_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
    echo "   New password: $NEW_PASSWORD"
    
    # Get admin identity
    ADMIN_IDENTITY=$(get_admin_identity)
    if [ -z "$ADMIN_IDENTITY" ] || [ "$ADMIN_IDENTITY" = "null" ]; then
        echo -e "${RED}[-] Admin identity not found${NC}"
        return 1
    fi
    
    ADMIN_ID=$(echo "$ADMIN_IDENTITY" | jq -r '.id')
    
    # Update password via Kratos admin API
    PASSWORD_PAYLOAD=$(jq -n --arg password "$NEW_PASSWORD" '{
        "password": $password
    }')
    
    echo "   Updating password in Kratos..."
    UPDATE_RESPONSE=$(curl -s -k -X PUT "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID/credentials/password" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$PASSWORD_PAYLOAD" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[+] Password updated in Kratos${NC}"
        
        # Save to password file
        ADMIN_PASSWORD_FILE="$HOME/.sting-ce/admin_password.txt"
        echo "$NEW_PASSWORD" > "$ADMIN_PASSWORD_FILE"
        echo "   Saved to: $ADMIN_PASSWORD_FILE"
        
        # Clear any problematic flags
        clear_force_password_change
        
        echo -e "${GREEN}[+] Admin password reset complete${NC}"
        echo -e "${YELLOW}📋 New credentials:${NC}"
        echo "   Email: $ADMIN_EMAIL"
        echo "   Password: $NEW_PASSWORD"
    else
        echo -e "${RED}[-] Failed to update password${NC}"
    fi
}

# Function to create new admin identity
create_admin_identity() {
    echo -e "${BLUE} Creating new admin identity...${NC}"
    
    # Check if admin already exists
    EXISTING_ADMIN=$(get_admin_identity)
    if [ -n "$EXISTING_ADMIN" ] && [ "$EXISTING_ADMIN" != "null" ]; then
        echo -e "${YELLOW}[!]  Admin identity already exists${NC}"
        echo "   Use action 6 (Full reset) to recreate"
        return 1
    fi
    
    # Generate password
    NEW_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
    
    # Create identity payload
    IDENTITY_PAYLOAD=$(jq -n --arg email "$ADMIN_EMAIL" --arg password "$NEW_PASSWORD" '{
        "schema_id": "default",
        "traits": {
            "email": $email,
            "role": "admin"
        },
        "credentials": {
            "password": {
                "config": {
                    "password": $password
                }
            }
        },
        "state": "active"
    }')
    
    echo "   Creating identity in Kratos..."
    CREATE_RESPONSE=$(curl -s -k -X POST "$KRATOS_ADMIN_URL/admin/identities" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$IDENTITY_PAYLOAD" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        ADMIN_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
        echo -e "${GREEN}[+] Admin identity created${NC}"
        echo "   ID: $ADMIN_ID"
        
        # Save password
        ADMIN_PASSWORD_FILE="$HOME/.sting-ce/admin_password.txt"
        echo "$NEW_PASSWORD" > "$ADMIN_PASSWORD_FILE"
        echo "   Password saved to: $ADMIN_PASSWORD_FILE"
        
        # Create UserSettings
        create_user_settings
        
        echo -e "${GREEN}[+] New admin account ready${NC}"
        echo -e "${YELLOW}📋 Credentials:${NC}"
        echo "   Email: $ADMIN_EMAIL"
        echo "   Password: $NEW_PASSWORD"
    else
        echo -e "${RED}[-] Failed to create admin identity${NC}"
        echo "Response: $CREATE_RESPONSE"
    fi
}

# Function to clear admin sessions
clear_admin_sessions() {
    echo -e "${BLUE} Clearing admin sessions...${NC}"
    
    ADMIN_IDENTITY=$(get_admin_identity)
    if [ -z "$ADMIN_IDENTITY" ] || [ "$ADMIN_IDENTITY" = "null" ]; then
        echo -e "${RED}[-] Admin identity not found${NC}"
        return 1
    fi
    
    ADMIN_ID=$(echo "$ADMIN_IDENTITY" | jq -r '.id')
    
    echo "   Deleting all sessions for admin..."
    DELETE_RESPONSE=$(curl -s -k -X DELETE "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID/sessions" \
        -H "Accept: application/json" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[+] Admin sessions cleared${NC}"
    else
        echo -e "${RED}[-] Failed to clear sessions${NC}"
    fi
}

# Function for full admin reset
full_admin_reset() {
    echo -e "${RED}🚨 NUCLEAR OPTION: Full Admin Reset${NC}"
    echo "This will completely delete and recreate the admin account"
    echo
    read -p "Are you sure? (type 'YES' to confirm): " CONFIRM
    
    if [ "$CONFIRM" != "YES" ]; then
        echo "Aborted"
        return 1
    fi
    
    # Get existing admin
    ADMIN_IDENTITY=$(get_admin_identity)
    if [ -n "$ADMIN_IDENTITY" ] && [ "$ADMIN_IDENTITY" != "null" ]; then
        ADMIN_ID=$(echo "$ADMIN_IDENTITY" | jq -r '.id')
        echo "   Deleting existing admin identity..."
        
        curl -s -k -X DELETE "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID" 2>/dev/null
        echo -e "${GREEN}[+] Existing admin deleted${NC}"
    fi
    
    # Clear UserSettings
    echo "   Clearing UserSettings..."
    docker exec sting-ce-app python -c "
from app import create_app
from app.models.user_settings import UserSettings
from app import db

app = create_app()
with app.app_context():
    admin_setting = UserSettings.query.filter_by(email='$ADMIN_EMAIL').first()
    if admin_setting:
        db.session.delete(admin_setting)
        db.session.commit()
        print('[+] UserSettings cleared')
    else:
        print('[*]  No UserSettings to clear')
" 2>/dev/null
    
    # Create fresh admin
    echo "   Creating fresh admin identity..."
    create_admin_identity
    
    echo -e "${GREEN}[+] Full admin reset complete${NC}"
}

# Main logic
if [ $# -eq 0 ]; then
    echo "No action specified. Running diagnostic first..."
    echo
    ./scripts/diagnose_admin_status.sh
    echo
    show_usage
    exit 0
fi

ACTION=$1

case $ACTION in
    1)
        clear_force_password_change
        ;;
    2)
        create_user_settings
        ;;
    3)
        reset_admin_password
        ;;
    4)
        create_admin_identity
        ;;
    5)
        clear_admin_sessions
        ;;
    6)
        full_admin_reset
        ;;
    *)
        echo "Invalid action: $ACTION"
        show_usage
        exit 1
        ;;
esac

echo
echo -e "${BLUE} Running post-recovery diagnostic...${NC}"
echo
./scripts/diagnose_admin_status.sh