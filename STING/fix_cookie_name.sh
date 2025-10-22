#!/bin/bash
# Revert cookie name back to ory_kratos_session (with underscore)

echo "Reverting cookie name back to ory_kratos_session..."

# Update Python files
find app -name "*.py" -type f -exec sed -i 's/ory_kratos_session/ory_kratos_session/g' {} \;

# Update environment file
sed -i 's/SESSION_COOKIE_NAME="ory_kratos_session"/SESSION_COOKIE_NAME="ory_kratos_session"/g' env/kratos.env

echo "Cookie name reverted successfully"
echo "Files updated:"
grep -r "ory_kratos_session" app --include="*.py" | wc -l
echo "occurrences found"