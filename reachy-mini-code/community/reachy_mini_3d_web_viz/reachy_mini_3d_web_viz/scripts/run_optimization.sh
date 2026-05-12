#!/bin/bash
# Run mesh optimization with Blender
# Requires: Blender installed and available in PATH (or specify full path)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Starting mesh optimization..."
echo "Working directory: $(pwd)"
echo ""

# Try common Blender paths
if command -v blender &> /dev/null; then
    BLENDER_CMD="blender"
elif [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER_CMD="/Applications/Blender.app/Contents/MacOS/Blender"
else
    echo "ERROR: Blender not found!"
    echo "Please install Blender or add it to your PATH"
    echo ""
    echo "macOS: brew install --cask blender"
    echo "Or download from: https://www.blender.org/download/"
    exit 1
fi

echo "Using Blender: $BLENDER_CMD"
echo ""

$BLENDER_CMD --background --python scripts/optimize_meshes.py

echo ""
echo "Next steps:"
echo "1. Update your URDF to reference meshes_optimized/*.glb"
echo "2. Run: python scripts/update_urdf.py"
