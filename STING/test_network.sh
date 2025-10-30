#!/bin/bash
# Quick DNS check for STING-CE installation
# Run this before installing to verify DNS is working

echo "🔍 Quick DNS Check for STING-CE"
echo "================================"
echo ""

# Test hosts
hosts=("pypi.org" "raw.githubusercontent.com" "google.com")
all_pass=true

for host in "${hosts[@]}"; do
    echo -n "Testing $host... "
    if nslookup "$host" &>/dev/null || ping -c 1 -W 2 "$host" &>/dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
        all_pass=false
    fi
done

echo ""
if [ "$all_pass" = true ]; then
    echo "✅ All DNS tests passed!"
    echo ""
    echo "Your system DNS is working correctly."
    echo "STING installation should work without issues."
    echo ""
    echo "Note: STING automatically configures Docker BuildKit DNS"
    echo "      via buildkitd.toml for additional reliability."
else
    echo "❌ DNS resolution is not working correctly!"
    echo ""
    echo "This will cause STING installation to fail."
    echo ""
    echo "Quick fix options:"
    echo ""
    echo "  1. Run the DNS fix script:"
    echo "     ./STING/fix_dns.sh"
    echo ""
    echo "  2. Manual fix (WSL):"
    echo "     sudo nano /etc/resolv.conf"
    echo "     Add: nameserver 8.8.8.8"
    echo ""
    echo "  3. See full guide:"
    echo "     cat STING/DNS_TROUBLESHOOTING.md"
    echo ""
fi

exit 0
