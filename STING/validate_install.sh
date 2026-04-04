#!/usr/bin/env bash
#
# STING-CE Install Validation Script
#
# Validates the build pipeline without performing a full installation.
# Checks that all Dockerfiles, configs, frontend imports, and service
# dependencies are intact and buildable.
#
# Usage:
#   ./validate_install.sh              # Run all checks
#   ./validate_install.sh --quick      # Skip Docker builds (file checks only)
#   ./validate_install.sh --build-only # Only run Docker build checks
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
FAIL=0
WARN=0
ERRORS=()

pass() { ((PASS++)); echo -e "  ${GREEN}✓${NC} $1"; }
fail() { ((FAIL++)); ERRORS+=("$1"); echo -e "  ${RED}✗${NC} $1"; }
warn() { ((WARN++)); echo -e "  ${YELLOW}⚠${NC} $1"; }
section() { echo -e "\n${CYAN}${BOLD}[$1]${NC}"; }

# Parse arguments
SKIP_BUILDS=false
BUILD_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --quick) SKIP_BUILDS=true ;;
    --build-only) BUILD_ONLY=true ;;
    --help|-h)
      echo "Usage: $0 [--quick|--build-only]"
      echo "  --quick      Skip Docker builds (file checks only)"
      echo "  --build-only Only run Docker build checks"
      exit 0
      ;;
  esac
done

echo -e "${BOLD}STING-CE Install Validation${NC}"
echo "========================================"

# ─── FILE EXISTENCE CHECKS ───────────────────────────────────────────

if [ "$BUILD_ONLY" = false ]; then

section "Core Installer Files"
for f in install_sting.sh manage_sting.sh lib/bootstrap.sh lib/installation.sh lib/services.sh; do
  [ -f "$f" ] && pass "$f" || fail "$f missing"
done

section "Docker Compose Files"
for f in docker-compose.yml; do
  [ -f "$f" ] && pass "$f" || fail "$f missing"
done

section "Dockerfiles Referenced by docker-compose.yml"
declare -A DOCKERFILE_MAP=(
  ["vault/Dockerfile-vault"]="vault"
  ["Dockerfile.utils"]="utils"
  ["database/Dockerfile-postgres"]="database"
  ["app/Dockerfile.app"]="app"
  ["Dockerfile.minimal-worker"]="report-worker"
  ["Dockerfile.report-bee"]="report-bee"
  ["frontend/Dockerfile.react-nginx"]="frontend"
  ["knowledge_service/Dockerfile"]="knowledge"
  ["chatbot/Dockerfile"]="chatbot"
  ["messaging_service/Dockerfile"]="messaging"
  ["external_ai_service/Dockerfile"]="external-ai"
  ["public_bee/Dockerfile"]="public-bee"
  ["demo_ai_service/Dockerfile"]="demo-ai"
)

for dockerfile in "${!DOCKERFILE_MAP[@]}"; do
  service="${DOCKERFILE_MAP[$dockerfile]}"
  [ -f "$dockerfile" ] && pass "$dockerfile ($service)" || fail "$dockerfile ($service) missing"
done

section "Dockerfile COPY/CMD Targets"

# Check that files referenced by COPY/CMD in Dockerfiles actually exist
check_dockerfile_refs() {
  local dockerfile="$1"
  local context="$2"
  local svc="$3"

  # Extract COPY source files (skip --from= stages and . or ./ copies)
  while IFS= read -r src; do
    [ -z "$src" ] && continue
    local full_path="${context}/${src}"
    if [ -e "$full_path" ] || compgen -G "$full_path" > /dev/null 2>&1; then
      pass "$svc: $src"
    else
      fail "$svc: $src not found (referenced in $dockerfile)"
    fi
  done < <(grep '^COPY' "$dockerfile" 2>/dev/null | grep -v '\-\-from=' | awk '{print $2}' | grep -v '^\.\(/\)\?$' | sort -u)
}

check_dockerfile_refs "frontend/Dockerfile.react-nginx" "frontend" "frontend"
check_dockerfile_refs "knowledge_service/Dockerfile" "knowledge_service" "knowledge"
check_dockerfile_refs "knowledge_service/Dockerfile.minimal" "knowledge_service" "knowledge-minimal"
check_dockerfile_refs "chatbot/Dockerfile" "." "chatbot"

# Verify kratos Dockerfiles reference existing config files
section "Kratos Dockerfile Config References"
for kdf in kratos/Dockerfile.kratos kratos/Dockerfile.passkeys; do
  [ ! -f "$kdf" ] && continue
  while IFS= read -r src; do
    [ -z "$src" ] && continue
    if [ -f "kratos/$src" ]; then
      pass "$kdf: $src"
    else
      fail "$kdf: $src not found in kratos/"
    fi
  done < <(grep '^COPY' "$kdf" | awk '{print $2}' | sort -u)
done

section "Frontend Import Integrity"
# Check that all JS/JSX imports resolve to existing files
FRONTEND_BROKEN=0
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  import_path=$(echo "$line" | grep -oP "from ['\"]([^'\"]+)['\"]" | sed "s/from ['\"]//;s/['\"]//")
  
  [ -z "$import_path" ] && continue
  # Skip node_modules imports
  [[ "$import_path" != .* ]] && continue
  
  dir=$(dirname "$file")
  resolved="${dir}/${import_path}"
  
  found=false
  for ext in "" ".js" ".jsx" ".ts" ".tsx"; do
    if [ -f "${resolved}${ext}" ]; then
      found=true
      break
    fi
  done
  # Check index files
  if [ "$found" = false ] && [ -d "$resolved" ]; then
    for ext in ".js" ".jsx" ".ts" ".tsx"; do
      if [ -f "${resolved}/index${ext}" ]; then
        found=true
        break
      fi
    done
  fi
  
  if [ "$found" = false ]; then
    fail "Broken import in $(basename "$file"): $import_path"
    ((FRONTEND_BROKEN++))
  fi
done < <(grep -rn "from ['\"]\./" frontend/src/ --include='*.js' --include='*.jsx' --include='*.tsx' 2>/dev/null | grep -v node_modules | grep -v '\.css' | grep -v '\.svg' | grep -v '\.png' | grep -v '\.webp')

[ "$FRONTEND_BROKEN" -eq 0 ] && pass "All local frontend imports resolve"

section "Configuration Integrity"
# Check config.yml doesn't reference deleted services
if grep -q '^profile_service:' conf/config.yml 2>/dev/null; then
  fail "conf/config.yml still has profile_service block (service deleted)"
else
  pass "No dead service blocks in config.yml"
fi

# Check config_loader.py doesn't call deleted service processors
if grep -q '_process_profile_service_config' conf/config_loader.py 2>/dev/null; then
  fail "config_loader.py still references profile_service processor"
else
  pass "No dead service processors in config_loader.py"
fi

# Check file_operations.sh doesn't reference deleted dirs
if grep -q '"authentication"' lib/file_operations.sh 2>/dev/null; then
  fail "file_operations.sh references deleted authentication/ directory"
else
  pass "No dead directory references in file_operations.sh"
fi

section "Docker Compose Service Validation"
# Verify env_file entries reference expected paths
env_file_count=$(grep -c 'env_file' docker-compose.yml 2>/dev/null || echo 0)
if [ "$env_file_count" -gt 0 ]; then
  pass "Docker Compose has $env_file_count env_file sections (generated at install time)"
else
  warn "No env_file references found in docker-compose.yml"
fi

fi # end BUILD_ONLY check

# ─── DOCKER BUILD CHECKS ─────────────────────────────────────────────

if [ "$SKIP_BUILDS" = false ]; then

section "Docker Build Validation"

# Test critical service builds using --check (syntax only) or actual build
build_test() {
  local name="$1"
  local context="$2"
  local dockerfile="$3"
  local target="${4:-}"
  
  local target_flag=""
  [ -n "$target" ] && target_flag="--target $target"
  
  echo -ne "  Building ${CYAN}${name}${NC}... "
  if docker build -f "$dockerfile" $target_flag --quiet "$context" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
  else
    echo -e "${RED}✗${NC}"
    # Show error details
    docker build -f "$dockerfile" $target_flag "$context" 2>&1 | tail -5 | sed 's/^/    /'
    fail "$name Docker build failed"
  fi
}

build_test "frontend" "frontend" "frontend/Dockerfile.react-nginx" "builder"
build_test "app" "." "app/Dockerfile.app"
build_test "knowledge" "knowledge_service" "knowledge_service/Dockerfile"
build_test "chatbot" "chatbot" "chatbot/Dockerfile"
build_test "report-worker" "." "Dockerfile.minimal-worker"

fi # end SKIP_BUILDS check

# ─── SUMMARY ─────────────────────────────────────────────────────────

echo ""
echo "========================================"
echo -e "${BOLD}Validation Summary${NC}"
echo "========================================"
echo -e "  ${GREEN}Passed:${NC}  $PASS"
echo -e "  ${RED}Failed:${NC}  $FAIL"
echo -e "  ${YELLOW}Warnings:${NC} $WARN"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo -e "${RED}${BOLD}FAILURES:${NC}"
  for err in "${ERRORS[@]}"; do
    echo -e "  ${RED}✗${NC} $err"
  done
  echo ""
  echo -e "${RED}Validation FAILED — fix the above issues before installing.${NC}"
  exit 1
else
  echo ""
  echo -e "${GREEN}${BOLD}All checks passed — install pipeline is valid.${NC}"
  exit 0
fi
