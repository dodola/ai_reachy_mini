#!/usr/bin/env bash
# Validate the ongoing style migration.
# Usage:
#   ./scripts/validate-style-migration.sh            # full report
#   ./scripts/validate-style-migration.sh --quick    # skip typecheck
#   ./scripts/validate-style-migration.sh <path>...  # scope to specific paths
#
# Meant to be run by every agent before and after touching any bucket. Exits
# non-zero if typecheck fails or if a hardcoded accent color is reintroduced.

set -u
set -o pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$APP_DIR"

QUICK=0
PATHS=()
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    -h | --help)
      grep -E '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) PATHS+=("$arg") ;;
  esac
done

# Default scope = everything under src/.
if [ ${#PATHS[@]} -eq 0 ]; then
  SCOPE=("src")
else
  SCOPE=("${PATHS[@]}")
fi

fail=0
warn=0

section() {
  printf "\n${BOLD}${CYAN}==> %s${RESET}\n" "$1"
}

ok() {
  printf "${GREEN}✓${RESET} %s\n" "$1"
}

bad() {
  printf "${RED}✗${RESET} %s\n" "$1"
  fail=1
}

warn() {
  printf "${YELLOW}!${RESET} %s\n" "$1"
  warn=$((warn + 1))
}

# ----------------------------------------------------------------------------
# 1. Typecheck
# ----------------------------------------------------------------------------
if [ $QUICK -eq 0 ]; then
  section "npm run typecheck"
  if npm run --silent typecheck; then
    ok "typecheck green"
  else
    bad "typecheck failed"
  fi
fi

# ----------------------------------------------------------------------------
# 2. Hardcoded accent colors (must stay at 0)
# ----------------------------------------------------------------------------
section "hardcoded accent colors (must be empty)"
# Exclude the style foundation. Only check source files.
accent_hits=$(grep -rnE --include='*.ts' --include='*.tsx' \
  "#FF9500|rgba\(255,\s*149" "${SCOPE[@]}" \
  | grep -vE "/styles/" || true)
if [ -z "$accent_hits" ]; then
  ok "no '#FF9500' / 'rgba(255, 149, …)' in app code"
else
  bad "hardcoded accent color found:"
  echo "$accent_hits"
fi

# ----------------------------------------------------------------------------
# 3. Remaining darkMode ternary debt
# ----------------------------------------------------------------------------
section "remaining 'darkMode ?' ternaries (fewer is better)"
counts=$(grep -rc --include='*.ts' --include='*.tsx' \
  "darkMode ?" "${SCOPE[@]}" 2>/dev/null \
  | grep -v ':0$' \
  | grep -vE "/styles/|/main\.tsx" \
  | sort -t: -k2 -rn || true)
if [ -z "$counts" ]; then
  ok "no darkMode ternary left in scope"
else
  printf "%s\n" "$counts"
  total=$(echo "$counts" | awk -F: '{ s += $2 } END { print s+0 }')
  printf "${BOLD}total:${RESET} %s ternaries across %s files\n" \
    "$total" "$(echo "$counts" | wc -l | tr -d ' ')"
  warn "remaining debt - see MIGRATION_STATUS.md for bucket ownership"
fi

# ----------------------------------------------------------------------------
# 4. TODO(style-migration) comments
# ----------------------------------------------------------------------------
section "TODO(style-migration) markers"
todos=$(grep -rn --include='*.ts' --include='*.tsx' \
  "TODO(style-migration" "${SCOPE[@]}" 2>/dev/null || true)
if [ -z "$todos" ]; then
  ok "no TODO(style-migration) left in scope"
else
  echo "$todos"
  warn "unresolved TODOs (expected for deferred cases - see MIGRATION_STATUS.md)"
fi

# ----------------------------------------------------------------------------
# 5. `palette.isDark` alias sanity check
# ----------------------------------------------------------------------------
section "stray 'const darkMode = palette.isDark' aliases (should be empty)"
aliases=$(grep -rnE --include='*.ts' --include='*.tsx' \
  "const\s+darkMode\s*=\s*palette\.isDark" "${SCOPE[@]}" \
  2>/dev/null || true)
if [ -z "$aliases" ]; then
  ok "no leftover 'const darkMode = palette.isDark' alias"
else
  echo "$aliases"
  warn "alias leftover - finish migrating that file's body before removing it"
fi

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
section "summary"
if [ $fail -ne 0 ]; then
  printf "${RED}FAIL${RESET} - fix the blockers above.\n"
  exit 1
fi
if [ $warn -ne 0 ]; then
  printf "${YELLOW}OK with %s warning(s)${RESET} - typecheck green, no accent regression.\n" "$warn"
  exit 0
fi
printf "${GREEN}ALL CLEAR${RESET} - migration is fully green in scope.\n"
