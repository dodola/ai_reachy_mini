#!/bin/bash

# build_sidecar_unix.sh
# Script to build the uv-trampoline sidecar for Unix systems (macOS/Linux)

set -e

DST_DIR="src-tauri/binaries"
mkdir -p "$DST_DIR"

# Get Rust target triplet
# Use TARGET_TRIPLET from environment if provided (for cross-compilation in CI)
# Otherwise, detect from rustc
if [ -n "$TARGET_TRIPLET" ]; then
    TRIPLET="$TARGET_TRIPLET"
    echo "🔍 Using TARGET_TRIPLET from environment: $TRIPLET"
else
    TRIPLET=$(rustc -Vv | grep "host:" | awk '{print $2}')
    echo "🔍 Detected target triplet: $TRIPLET"
fi

cd uv-wrapper

# Build uv-trampoline
echo "🔨 Building uv-trampoline..."
if [ -n "$TARGET_TRIPLET" ]; then
    cargo build --release --bin uv-trampoline --target "$TARGET_TRIPLET"
    cp "target/$TARGET_TRIPLET/release/uv-trampoline" "../$DST_DIR/uv-trampoline-$TRIPLET"
else
    cargo build --release --bin uv-trampoline
    cp "target/release/uv-trampoline" "../$DST_DIR/uv-trampoline-$TRIPLET"
fi

# Make it executable
chmod +x "../$DST_DIR/uv-trampoline-$TRIPLET"

cd ..

echo "✅ Sidecar build complete!"
echo "   Location: $DST_DIR"
