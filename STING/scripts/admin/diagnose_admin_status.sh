#!/bin/bash

# STING Admin Account Diagnostic Script
# Checks current admin account status and identifies issues

echo "🔍 STING Admin Account Diagnostic"
echo "================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if services are running
echo -e "${BLUE}📋 Checking Service Status${NC}"
echo "----------------------------"
if ! docker ps | grep -q "sting-ce-kratos"; then
    echo -e "${RED}❌ Kratos service is not running${NC}"
    echo "   Run: ./manage_sting.sh start kratos"
    exit 1
else
    echo -e "${GREEN}✅ Kratos service is running${NC}"
fi

if ! docker ps | grep -q "sting-ce-app"; then
    echo -e "${RED}❌ App service is not running${NC}"
    echo "   Run: ./manage_sting.sh start app"
    exit 1
else
    echo -e "${GREEN}✅ App service is running${NC}"
fi

echo

# Check admin password file
echo -e "${BLUE}🔑 Checking Admin Credentials${NC}"
echo "------------------------------"
ADMIN_PASSWORD_FILE="$HOME/.sting-ce/admin_password.txt"
if [ -f "$ADMIN_PASSWORD_FILE" ]; then
    echo -e "${GREEN}✅ Admin password file exists${NC}"
    echo "   Location: $ADMIN_PASSWORD_FILE"
    echo "   Password: $(cat $ADMIN_PASSWORD_FILE)"
else
    echo -e "${RED}❌ Admin password file missing${NC}"
    echo "   Expected: $ADMIN_PASSWORD_FILE"
fi

echo

# Check Kratos identities
echo -e "${BLUE}👤 Checking Kratos Identities${NC}"
echo "------------------------------"
KRATOS_ADMIN_URL="https://localhost:8443"
IDENTITIES_RESPONSE=$(curl -s -k -X GET "$KRATOS_ADMIN_URL/admin/identities" -H "Accept: application/json" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$IDENTITIES_RESPONSE" ]; then
    echo -e "${RED}❌ Failed to connect to Kratos admin API${NC}"
    echo "   URL: $KRATOS_ADMIN_URL/admin/identities"
    echo "   Check if Kratos is running and accessible"
    exit 1
fi

# Parse admin identity
ADMIN_IDENTITY=$(echo "$IDENTITIES_RESPONSE" | jq -r '.[] | select(.traits.email=="admin@sting.local")')

if [ "$ADMIN_IDENTITY" = "null" ] || [ -z "$ADMIN_IDENTITY" ]; then
    echo -e "${RED}❌ Admin identity not found in Kratos${NC}"
    echo "   Expected email: admin@sting.local"
    echo
    echo -e "${YELLOW}📊 All identities found:${NC}"
    echo "$IDENTITIES_RESPONSE" | jq -r '.[] | .traits.email // "no-email"'
else
    echo -e "${GREEN}✅ Admin identity found${NC}"
    
    # Extract key information
    ADMIN_ID=$(echo "$ADMIN_IDENTITY" | jq -r '.id')
    ADMIN_EMAIL=$(echo "$ADMIN_IDENTITY" | jq -r '.traits.email')
    ADMIN_STATE=$(echo "$ADMIN_IDENTITY" | jq -r '.state')
    ADMIN_CREATED=$(echo "$ADMIN_IDENTITY" | jq -r '.created_at')
    
    echo "   ID: $ADMIN_ID"
    echo "   Email: $ADMIN_EMAIL"
    echo "   State: $ADMIN_STATE"
    echo "   Created: $ADMIN_CREATED"
    
    # Check for problematic traits
    echo
    echo -e "${BLUE}🔍 Admin Traits Analysis${NC}"
    echo "------------------------"
    
    TRAITS=$(echo "$ADMIN_IDENTITY" | jq '.traits')
    echo "$TRAITS" | jq .
    
    # Check specific problematic fields
    FORCE_PASSWORD_CHANGE=$(echo "$TRAITS" | jq -r '.force_password_change // false')
    ROLE=$(echo "$TRAITS" | jq -r '.role // "not-set"')
    
    echo
    if [ "$FORCE_PASSWORD_CHANGE" = "true" ]; then
        echo -e "${RED}❌ force_password_change is TRUE - This causes login loops${NC}"
    else
        echo -e "${GREEN}✅ force_password_change is FALSE or not set${NC}"
    fi
    
    if [ "$ROLE" = "admin" ]; then
        echo -e "${GREEN}✅ Role is set to admin${NC}"
    else
        echo -e "${YELLOW}⚠️  Role is: $ROLE (should be 'admin')${NC}"
    fi
fi

echo

# Check for active sessions
echo -e "${BLUE}🔐 Checking Active Sessions${NC}"
echo "----------------------------"
if [ -n "$ADMIN_ID" ]; then
    SESSIONS_RESPONSE=$(curl -s -k -X GET "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID/sessions" -H "Accept: application/json" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$SESSIONS_RESPONSE" ]; then
        SESSION_COUNT=$(echo "$SESSIONS_RESPONSE" | jq length 2>/dev/null || echo "0")
        echo "   Active sessions: $SESSION_COUNT"
        
        if [ "$SESSION_COUNT" -gt 0 ]; then
            echo "$SESSIONS_RESPONSE" | jq -r '.[] | "   Session: \(.id) (expires: \(.expires_at))"'
        fi
    else
        echo -e "${YELLOW}⚠️  Could not retrieve session information${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No admin ID available to check sessions${NC}"
fi

echo

# Check Flask database for UserSettings
echo -e "${BLUE}🗄️ Checking Flask UserSettings Database${NC}"
echo "---------------------------------------"
USER_SETTINGS_CHECK=$(docker exec sting-ce-app python -c "
try:
    from app import create_app
    from app.models.user_settings import UserSettings
    app = create_app()
    with app.app_context():
        admin_setting = UserSettings.query.filter_by(email='admin@sting.local').first()
        if admin_setting:
            print(f'UserSettings found: force_password_change={admin_setting.force_password_change}')
        else:
            print('No UserSettings found for admin')
except Exception as e:
    print(f'Error: {e}')
" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "   $USER_SETTINGS_CHECK"
else
    echo -e "${YELLOW}⚠️  Could not check Flask UserSettings database${NC}"
fi

echo

# Check WebAuthn/TOTP methods
echo -e "${BLUE}🔐 Checking Authentication Methods${NC}"
echo "-----------------------------------"
if [ -n "$ADMIN_ID" ]; then
    # Check for WebAuthn credentials
    WEBAUTHN_CREDS=$(curl -s -k -X GET "$KRATOS_ADMIN_URL/admin/identities/$ADMIN_ID/credentials" -H "Accept: application/json" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$WEBAUTHN_CREDS" ]; then
        echo -e "${GREEN}✅ Retrieved credential information${NC}"
        
        # Check for TOTP
        TOTP_EXISTS=$(echo "$WEBAUTHN_CREDS" | jq -r 'has("totp")')
        if [ "$TOTP_EXISTS" = "true" ]; then
            echo -e "${GREEN}✅ TOTP is configured${NC}"
        else
            echo -e "${RED}❌ TOTP is NOT configured${NC}"
        fi
        
        # Check for WebAuthn
        WEBAUTHN_EXISTS=$(echo "$WEBAUTHN_CREDS" | jq -r 'has("webauthn")')
        if [ "$WEBAUTHN_EXISTS" = "true" ]; then
            echo -e "${GREEN}✅ WebAuthn/Passkeys are configured${NC}"
        else
            echo -e "${YELLOW}⚠️  WebAuthn/Passkeys are NOT configured${NC}"
        fi
        
        # Check for password
        PASSWORD_EXISTS=$(echo "$WEBAUTHN_CREDS" | jq -r 'has("password")')
        if [ "$PASSWORD_EXISTS" = "true" ]; then
            echo -e "${GREEN}✅ Password authentication is configured${NC}"
        else
            echo -e "${RED}❌ Password authentication is NOT configured${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Could not retrieve credential information${NC}"
    fi
fi

echo

# Summary and Recommendations
echo -e "${BLUE}📋 Summary & Recommendations${NC}"
echo "=============================="

if [ -n "$ADMIN_IDENTITY" ]; then
    if [ "$FORCE_PASSWORD_CHANGE" = "true" ]; then
        echo -e "${RED}🚨 CRITICAL ISSUE: Admin account has force_password_change=true${NC}"
        echo "   This causes login redirect loops"
        echo "   SOLUTION: Run admin recovery script"
    elif [ "$USER_SETTINGS_CHECK" = *"force_password_change=True"* ]; then
        echo -e "${RED}🚨 CRITICAL ISSUE: UserSettings has force_password_change=True${NC}"
        echo "   This causes login redirect loops"
        echo "   SOLUTION: Clear UserSettings force_password_change flag"
    else
        echo -e "${GREEN}✅ Admin account appears to be in good state${NC}"
        echo "   Try logging in with credentials from $ADMIN_PASSWORD_FILE"
    fi
    
    if [ "$USER_SETTINGS_CHECK" = *"No UserSettings found"* ]; then
        echo -e "${YELLOW}⚠️  UserSettings record missing for admin${NC}"
        echo "   This might cause issues with V2 authentication system"
        echo "   SOLUTION: Create UserSettings record"
    fi
else
    echo -e "${RED}🚨 CRITICAL ISSUE: No admin identity found${NC}"
    echo "   Admin account needs to be created"
    echo "   SOLUTION: Run admin creation script"
fi

echo
echo -e "${BLUE}🔧 Available Recovery Actions:${NC}"
echo "1. Clear force_password_change flags"
echo "2. Create missing UserSettings record" 
echo "3. Reset admin password"
echo "4. Create new admin identity"
echo "5. Clear all admin sessions"
echo
echo "Run: ./scripts/recover_admin_account.sh [action-number]"