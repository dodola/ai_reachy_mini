#!/bin/bash

# Project cleanup script
# Removes all build files and artifacts

set -e

echo "🧹 Cleaning project..."

# Build directories to remove
DIRS_TO_CLEAN=(
  "dist"                          # Frontend Vite build
  "src-tauri/target"              # Rust Tauri build
  "src-tauri/gen"                 # Tauri generated files
  "src-tauri/binaries"            # Sidecar (Python venv, uv, cpython)
  "uv-wrapper/target"            # Rust uv-wrapper build
  "scripts/__pycache__"          # Python cache
  "test-updates"                  # Test update files
)

# Platform-specific app data directories
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "mingw"* || "$OSTYPE" == "cygwin"* ]]; then
  APP_DATA_DIRS=(
    "$LOCALAPPDATA/Reachy Mini Control"
    "$LOCALAPPDATA/com.pollen-robotics.reachy-mini"
    "$LOCALAPPDATA/com.reachy-mini-daemon-app"
  )
else
  APP_DATA_DIRS=(
    "$HOME/Library/Application Support/com.pollen-robotics.reachy-mini"
  )
fi

# Temporary files to remove
FILES_TO_CLEAN=(
  "*.log"                         # Log files
  "daemon-develop-test.log"       # Specific log file
)

# Remove directories
for dir in "${DIRS_TO_CLEAN[@]}"; do
  if [ -d "$dir" ] || [ -f "$dir" ]; then
    echo "  ❌ Removing $dir"
    rm -rf "$dir"
  else
    echo "  ⏭️  $dir does not exist (already clean)"
  fi
done

# Remove files
for pattern in "${FILES_TO_CLEAN[@]}"; do
  if ls $pattern 1> /dev/null 2>&1; then
    echo "  ❌ Removing $pattern"
    rm -f $pattern
  fi
done

# Remove app data directories
for app_dir in "${APP_DATA_DIRS[@]}"; do
  if [ -d "$app_dir" ]; then
    echo "  ❌ Removing app data: $app_dir"
    rm -rf "$app_dir"
  else
    echo "  ⏭️  $app_dir does not exist (already clean)"
  fi
done

echo "✅ Cleanup complete!"
echo ""
echo "💡 To reinstall dependencies: yarn install"
echo "💡 To rebuild: yarn build"

