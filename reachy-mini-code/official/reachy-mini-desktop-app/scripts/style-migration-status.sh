#!/usr/bin/env bash
# Print a per-bucket status of the style migration.
# Usage: ./scripts/style-migration-status.sh

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$APP_DIR"

BOLD=$'\033[1m'
CYAN=$'\033[0;36m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
DIM=$'\033[2m'
RESET=$'\033[0m'

count_ternaries() {
  local total=0
  for f in "$@"; do
    if [ -f "$f" ]; then
      local c
      c=$(grep "darkMode ?" "$f" 2>/dev/null | wc -l | tr -d ' ')
      total=$((total + c))
    fi
  done
  echo "$total"
}

status_line() {
  local label="$1"
  local count="$2"
  if [ "$count" -eq 0 ]; then
    printf "  ${GREEN}✓${RESET} %-55s ${GREEN}done${RESET}\n" "$label"
  else
    printf "  ${YELLOW}●${RESET} %-55s ${YELLOW}%3d${RESET} ternaries\n" "$label" "$count"
  fi
}

bucket() {
  local title="$1"
  shift
  local total=0
  printf "\n${BOLD}${CYAN}%s${RESET}\n" "$title"
  for f in "$@"; do
    local c
    c=$(count_ternaries "$f")
    status_line "$f" "$c"
    total=$((total + c))
  done
  printf "  ${DIM}subtotal: %d${RESET}\n" "$total"
  GRAND_TOTAL=$((GRAND_TOTAL + total))
}

GRAND_TOTAL=0

bucket "Bucket 1 - LogConsole" \
  src/components/LogConsole/index.tsx \
  src/components/LogConsole/LogItem.tsx

bucket "Bucket 2 - Application store" \
  src/views/active-robot/application-store/discover/Section.tsx \
  src/views/active-robot/application-store/installed/InstalledAppsSection.tsx \
  src/views/active-robot/application-store/installation/Overlay.tsx \
  src/views/active-robot/application-store/discover/Modal.tsx \
  src/views/active-robot/application-store/discover/components/SearchBar.tsx \
  src/views/active-robot/application-store/discover/components/AppCard.tsx

bucket "Bucket 3 - Finding robot + setup" \
  src/views/finding-robot/FindingRobotView.tsx \
  src/views/setup-choice/SetupChoiceView.tsx \
  src/views/first-time-wifi-setup/FirstTimeWifiSetupView.tsx \
  src/views/first-time-wifi-setup/steps/Step2ConnectHotspot.tsx \
  src/views/first-time-wifi-setup/steps/Step1PowerOn.tsx \
  src/views/permissions-required/PermissionsRequiredView.tsx \
  src/views/bluetooth-support/BluetoothSupportView.tsx \
  src/views/starting/StartupView.tsx \
  src/views/starting/StartingView.tsx \
  src/views/closing/ClosingView.tsx

bucket "Bucket 4 - Active robot shell + right panel" \
  src/views/active-robot/ActiveRobotView.tsx \
  src/views/active-robot/right-panel/EmbeddedAppView.tsx \
  src/views/active-robot/right-panel/RightPanel.tsx \
  src/views/active-robot/camera/CameraFeed.tsx \
  src/views/active-robot/audio/AudioControls.tsx \
  src/views/active-robot/audio/DoAIndicator.tsx \
  src/views/update/UpdateView.tsx

bucket "Bucket 5 - Controller + sliders" \
  src/views/active-robot/controller/Controller.tsx \
  src/views/active-robot/controller/components/Joystick2D.tsx \
  src/views/active-robot/controller/components/SimpleSlider.tsx \
  src/views/active-robot/controller/components/CircularSlider.tsx \
  src/views/active-robot/controller/components/VerticalSlider.tsx

bucket "Bucket 6 - Shared components + cleanup" \
  src/components/FPSMeter.tsx \
  src/components/FullscreenOverlay.tsx \
  src/components/DevPlayground.tsx \
  src/components/viewer3d/Scene.tsx \
  src/components/viewer3d/Viewer3D.tsx \
  src/components/AppTopBar.tsx \
  src/components/Toast/Toast.tsx

# Out of scope (informational).
printf "\n${BOLD}${CYAN}Out of scope (explicitly deferred)${RESET}\n"
oos=$(count_ternaries src/utils/viewer3d/applyRobotMaterials.ts)
status_line "src/utils/viewer3d/applyRobotMaterials.ts" "$oos"

# Orphan check.
all_in_buckets=$(cat <<EOF
src/components/LogConsole/index.tsx
src/components/LogConsole/LogItem.tsx
src/views/active-robot/application-store/discover/Section.tsx
src/views/active-robot/application-store/installed/InstalledAppsSection.tsx
src/views/active-robot/application-store/installation/Overlay.tsx
src/views/active-robot/application-store/discover/Modal.tsx
src/views/active-robot/application-store/discover/components/SearchBar.tsx
src/views/active-robot/application-store/discover/components/AppCard.tsx
src/views/finding-robot/FindingRobotView.tsx
src/views/setup-choice/SetupChoiceView.tsx
src/views/first-time-wifi-setup/FirstTimeWifiSetupView.tsx
src/views/first-time-wifi-setup/steps/Step2ConnectHotspot.tsx
src/views/first-time-wifi-setup/steps/Step1PowerOn.tsx
src/views/permissions-required/PermissionsRequiredView.tsx
src/views/bluetooth-support/BluetoothSupportView.tsx
src/views/starting/StartupView.tsx
src/views/starting/StartingView.tsx
src/views/closing/ClosingView.tsx
src/views/active-robot/ActiveRobotView.tsx
src/views/active-robot/right-panel/EmbeddedAppView.tsx
src/views/active-robot/right-panel/RightPanel.tsx
src/views/active-robot/camera/CameraFeed.tsx
src/views/active-robot/audio/AudioControls.tsx
src/views/active-robot/audio/DoAIndicator.tsx
src/views/update/UpdateView.tsx
src/views/active-robot/controller/Controller.tsx
src/views/active-robot/controller/components/Joystick2D.tsx
src/views/active-robot/controller/components/SimpleSlider.tsx
src/views/active-robot/controller/components/CircularSlider.tsx
src/views/active-robot/controller/components/VerticalSlider.tsx
src/components/FPSMeter.tsx
src/components/FullscreenOverlay.tsx
src/components/DevPlayground.tsx
src/components/viewer3d/Scene.tsx
src/components/viewer3d/Viewer3D.tsx
src/components/AppTopBar.tsx
src/components/Toast/Toast.tsx
src/utils/viewer3d/applyRobotMaterials.ts
EOF
)

orphans=$(
  grep -rlE --include='*.ts' --include='*.tsx' "darkMode \?" src 2>/dev/null \
    | grep -vE "styles/|main\.tsx" \
    | sort -u \
    | while read -r f; do
        if ! echo "$all_in_buckets" | grep -qx "$f"; then
          echo "$f"
        fi
      done
)

if [ -n "$orphans" ]; then
  printf "\n${BOLD}${YELLOW}Orphan files (have ternaries but no bucket!)${RESET}\n"
  echo "$orphans" | sed 's/^/  /'
fi

# Grand summary.
printf "\n${BOLD}Grand total (in-scope buckets only): %s ternaries remaining${RESET}\n" "$GRAND_TOTAL"
if [ "$GRAND_TOTAL" -eq 0 ]; then
  printf "${GREEN}All in-scope buckets are done.${RESET}\n"
fi
