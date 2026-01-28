#!/bin/bash
# Clear all Kratos sessions to fix CSRF issues after restart

echo " Clearing all Kratos sessions..."

# Get all identities
IDENTITIES=$(curl -sk https://localhost:4434/admin/identities | jq -r '.[] | .id' 2>/dev/null)

if [ -z "$IDENTITIES" ]; then
    echo "[-] Failed to get identities. Make sure Kratos is running."
    exit 1
fi

COUNT=0
for ID in $IDENTITIES; do
    # Delete all sessions for this identity
    curl -sk -X DELETE "https://localhost:4434/admin/identities/$ID/sessions"
    if [ $? -eq 0 ]; then
        ((COUNT++))
        echo "[+] Cleared sessions for identity: $ID"
    fi
done

echo ""
echo "[+] Cleared sessions for $COUNT identities"
echo ""
echo "[!]  All users need to:"
echo "1. Clear browser cookies for localhost"
echo "2. Login again"
echo ""
echo "To clear cookies in Chrome/Edge:"
echo "- Press F12 → Application → Storage → Clear site data"
echo ""